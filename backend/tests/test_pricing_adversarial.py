"""Additional failure-seeking checks; no production code is changed here."""

import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_CEILING
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from django.db import close_old_connections
from django.utils import timezone

from core import ml_pricing, ml_train, pricing_service, services
from core.models import (AnalysisRun, Lot, Offer, OfferLimit, PriceChange,
                         Product, Recommendation, StorePricingPolicy)


def test_randomized_price_bounds_and_coverage_never_escape_limits():
    rng = random.Random(20261105)
    for _ in range(250):
        original_cents = rng.randint(200, 10000)
        original = Decimal(original_cents) / 100
        floor_cents = rng.randint(max(1, original_cents * 7 // 10), original_cents)
        current_cents = rng.randint(floor_cents, original_cents)
        floor = Decimal(floor_cents) / 100
        current = Decimal(current_cents) / 100
        steps = rng.randint(1, 60)
        features = {"store_id": "S1", "category": "Fruta", "price_ratio": float(current / original),
                    "current_price": float(current), "days_to_close": rng.randint(0, 8),
                    "stock_steps": steps, "weekday": rng.randint(0, 6),
                    "lot_age_days": rng.randint(0, 8), "lag7_sales_sum": 14,
                    "lag7_days": 7, "lag14_sales_sum": 28, "lag14_days": 14}
        result = ml_pricing.recommend_price(
            lambda rows: [2.5 * row["price_ratio"] ** -1.2 for row in rows],
            features, original_price=original, current_price=current,
            floor=floor, available_steps=steps)
        proposed = Decimal(result["proposed_price"])
        assert floor <= proposed <= current <= original
        assert proposed.as_tuple().exponent >= -2
        assert result["status"] == ("PENDING" if proposed < current else "KEEP")
        if "current_coverage" in result:
            assert 0 <= result["current_coverage"] <= 1
            assert 0 <= result["proposed_coverage"] <= 1


@pytest.fixture(scope="module")
def model_stub():
    bundle, report = ml_train.train_model(42)
    return bundle, {**report, "artifact": "adversarial.joblib",
                    "artifact_sha256": "b" * 64,
                    "trained_at_utc": timezone.now().isoformat()}


@pytest.fixture
def prepared(owner, product, monkeypatch, model_stub):
    monkeypatch.setattr(pricing_service, "_load_model", lambda: model_stub)
    monkeypatch.setattr(pricing_service.ml_pricing, "recommend_price",
                        lambda *args, **kwargs: {"status": "PENDING", "reason": "TARGET_COVERAGE",
                                                 "current_price": "10.00", "proposed_price": "8.50",
                                                 "current_coverage": .6, "proposed_coverage": .9})
    StorePricingPolicy.objects.create(store=owner.store, version=1,
                                      mode=StorePricingPolicy.Mode.REVIEW,
                                      starts_at=timezone.now(), created_by=owner)
    Product.objects.filter(pk=product.pk).update(created_at=timezone.now() - timedelta(days=10))
    product.refresh_from_db()
    today = timezone.localdate()
    expiry = today + timedelta(days=7)
    lot = Lot.objects.create(product=product, code="ADV-01", received_date=today,
                             expiry_date=expiry,
                             sales_close_at=datetime.combine(expiry - timedelta(days=1),
                                                               time(20), ZoneInfo("America/Lima")),
                             total_cost=Decimal("50"), received_qty=5000, physical_qty=5000)
    offer = Offer.objects.create(lot=lot, state=Offer.State.PUBLISHED,
                                 original_price=Decimal("10"), current_price=Decimal("10"))
    OfferLimit.objects.create(offer=offer, version=1,
                              max_discount_pct=Decimal("30"), minimum_price=Decimal("7"),
                              authorized_by=owner, starts_at=timezone.now())
    return owner, lot, offer


@pytest.mark.django_db
def test_manual_price_change_invalidates_old_recommendation(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    services.change_price(owner, offer.id, {"new_price": "9.50", "reason": "Cambio manual"})
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "STALE"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("9.50")
    assert PriceChange.objects.count() == 1


@pytest.mark.django_db
def test_policy_version_change_invalidates_old_recommendation(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    old = StorePricingPolicy.objects.get(store=owner.store, ends_at__isnull=True)
    old.ends_at = timezone.now()
    old.save(update_fields=["ends_at"])
    StorePricingPolicy.objects.create(store=owner.store, version=2,
                                      mode=StorePricingPolicy.Mode.REVIEW,
                                      starts_at=timezone.now(), created_by=owner)
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "STALE"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("10")


@pytest.mark.django_db
def test_stock_change_creates_new_analysis_snapshot(prepared):
    owner, lot, _ = prepared
    first = pricing_service.analyze_store(owner)
    lot.physical_qty -= 250
    lot.save(update_fields=["physical_qty"])
    second = pricing_service.analyze_store(owner)
    assert second.id != first.id
    assert AnalysisRun.objects.count() == 2


@pytest.mark.django_db
def test_invalid_decision_does_not_change_price(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    with pytest.raises(services.DomainError) as error:
        pricing_service.decide(owner, rec.id, "DELETE")
    assert error.value.code == "INVALID_DECISION"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("10")
    assert PriceChange.objects.count() == 0


@pytest.mark.django_db
def test_approval_at_effective_floor_is_allowed(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    rec.proposed_price = Decimal("7")
    rec.save(update_fields=["proposed_price"])
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "APPLIED"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("7")


@pytest.mark.django_db
def test_below_floor_recommendation_is_rejected_as_stale(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    rec.proposed_price = Decimal("6.99")
    rec.save(update_fields=["proposed_price"])
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "STALE"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("10")
    assert PriceChange.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_approvals_create_one_price_change(prepared):
    owner, _, offer = prepared
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))

    def approve(_):
        close_old_connections()
        try:
            return pricing_service.decide(owner, rec.id, "APPROVE").state
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        states = list(pool.map(approve, range(2)))
    offer.refresh_from_db()
    assert states == ["APPLIED", "APPLIED"]
    assert offer.current_price == Decimal("8.50")
    assert PriceChange.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_identical_analyses_return_same_run(prepared, monkeypatch):
    owner, _, _ = prepared
    original = pricing_service._snapshot_key
    barrier = Barrier(2)

    def synchronized_key(*args):
        key = original(*args)
        barrier.wait(timeout=5)
        return key

    monkeypatch.setattr(pricing_service, "_snapshot_key", synchronized_key)

    def analyze(_):
        close_old_connections()
        try:
            return pricing_service.analyze_store(owner).id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(analyze, range(2)))
    assert outcomes[0] == outcomes[1]
    assert AnalysisRun.objects.count() == 1
