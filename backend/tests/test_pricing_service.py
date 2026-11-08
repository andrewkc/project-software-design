"""Integration checks for owner review, stale snapshots and store isolation."""

import json
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.test import Client
from django.test import override_settings
from django.utils import timezone

from core import ml_train, pricing_service, services
from core.models import (AnalysisRun, Lot, MLModel, Offer, OfferLimit,
                         PriceChange, Product, Recommendation, StorePricingPolicy, User)


pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def model_stub():
    bundle, report = ml_train.train_model(42)
    return bundle, {**report, "artifact": "test-model.joblib",
                    "artifact_sha256": "a" * 64,
                    "trained_at_utc": timezone.now().isoformat()}


@pytest.fixture
def prepared(owner, product, monkeypatch, model_stub):
    monkeypatch.setattr(pricing_service, "_load_model", lambda: model_stub)
    StorePricingPolicy.objects.create(store=owner.store, version=1,
                                      mode=StorePricingPolicy.Mode.REVIEW,
                                      starts_at=timezone.now(), created_by=owner)
    Product.objects.filter(pk=product.pk).update(created_at=timezone.now() - timedelta(days=10))
    product.refresh_from_db()
    today = timezone.localdate()
    expiry = today + timedelta(days=7)
    lot = Lot.objects.create(product=product, code="ML-01", received_date=today,
                             expiry_date=expiry,
                             sales_close_at=datetime.combine(expiry - timedelta(days=1),
                                                               time(20), ZoneInfo("America/Lima")),
                             total_cost=Decimal("100.00"), received_qty=5000,
                             physical_qty=5000)
    offer = Offer.objects.create(lot=lot, state=Offer.State.PUBLISHED,
                                 original_price=Decimal("10.00"),
                                 current_price=Decimal("10.00"))
    limit = OfferLimit.objects.create(offer=offer, version=1,
                                      max_discount_pct=Decimal("30"),
                                      minimum_price=Decimal("7.00"),
                                      below_cost_authorized=False,
                                      authorized_by=owner, starts_at=timezone.now())
    return owner, product, lot, offer, limit


def force_discount(monkeypatch):
    monkeypatch.setattr(pricing_service.ml_pricing, "recommend_price",
                        lambda *args, **kwargs: {
                            "status": "PENDING", "reason": "TARGET_COVERAGE",
                            "current_price": "10.00", "proposed_price": "8.50",
                            "current_coverage": .6, "proposed_coverage": .9})


def test_analysis_is_idempotent_and_records_model_and_history(prepared):
    owner, _, _, offer, _ = prepared
    first = pricing_service.analyze_store(owner)
    second = pricing_service.analyze_store(owner)
    assert first.id == second.id
    assert AnalysisRun.objects.count() == 1
    rec = Recommendation.objects.get(run=first)
    assert rec.offer_id == offer.id
    assert rec.snapshot["history_source"] == "confirmed_local_and_web_sales"
    assert rec.snapshot["features"]["lag7_days"] == 7
    assert rec.current_price == offer.current_price
    assert MLModel.objects.count() == 1


def test_approval_changes_price_once_with_audit(prepared, monkeypatch):
    owner, _, _, offer, _ = prepared
    force_discount(monkeypatch)
    run = pricing_service.analyze_store(owner)
    rec = Recommendation.objects.get(run=run)
    assert rec.state == "PENDING"
    result = pricing_service.decide(owner, rec.id, "APPROVE")
    offer.refresh_from_db()
    assert result.state == "APPLIED"
    assert offer.current_price == Decimal("8.50") and offer.version == 2
    change = PriceChange.objects.get(recommendation=rec)
    assert change.old_price == Decimal("10.00") and change.new_price == Decimal("8.50")
    assert change.origin == "REVIEW" and change.actor_id == owner.id
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "APPLIED"
    assert PriceChange.objects.count() == 1


def test_reject_does_not_change_price(prepared, monkeypatch):
    owner, _, _, offer, _ = prepared
    force_discount(monkeypatch)
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    assert pricing_service.decide(owner, rec.id, "REJECT").state == "REJECTED"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("10.00")
    assert PriceChange.objects.count() == 0
    with pytest.raises(services.DomainError) as error:
        pricing_service.decide(owner, rec.id, "APPROVE")
    assert error.value.code == "DECISION_CONFLICT"


def test_stock_change_makes_old_recommendation_stale(prepared, monkeypatch):
    owner, _, lot, offer, _ = prepared
    force_discount(monkeypatch)
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    lot.reserved_qty = 250
    lot.save(update_fields=["reserved_qty"])
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "STALE"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("10.00")
    assert PriceChange.objects.count() == 0


def test_limit_change_makes_old_recommendation_stale(prepared, monkeypatch):
    owner, _, _, _, _ = prepared
    force_discount(monkeypatch)
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    services.set_offer_limit(owner, rec.offer_id,
                             {"max_discount_pct": "20", "minimum_price": "8.00",
                              "below_cost_authorized": False})
    assert pricing_service.decide(owner, rec.id, "APPROVE").state == "STALE"
    assert PriceChange.objects.count() == 0


def test_employee_and_other_store_cannot_analyze_or_decide(prepared, employee, other_store, monkeypatch):
    owner, _, _, _, _ = prepared
    force_discount(monkeypatch)
    rec = Recommendation.objects.get(run=pricing_service.analyze_store(owner))
    for action in (lambda: pricing_service.analyze_store(employee),
                   lambda: pricing_service.list_recommendations(employee),
                   lambda: pricing_service.decide(employee, rec.id, "APPROVE")):
        with pytest.raises(services.DomainError) as error:
            action()
        assert error.value.code == "FORBIDDEN"
    other_owner = User.objects.create_user(email="other-price@example.test",
        password="SecurePass123!", name="Otro", role=User.Role.OWNER, store=other_store)
    with pytest.raises(services.DomainError) as error:
        pricing_service.decide(other_owner, rec.id, "APPROVE")
    assert error.value.code == "NOT_FOUND"


def test_owner_api_lists_and_decides_without_exposing_cost(prepared, monkeypatch):
    owner, _, _, offer, _ = prepared
    force_discount(monkeypatch)
    client = Client()
    client.force_login(owner)
    response = client.post("/api/v1/store/analysis", data="{}", content_type="application/json")
    assert response.status_code == 200
    item = response.json()["recommendations"][0]
    assert item["state"] == "PENDING" and "cost" not in json.dumps(item)
    assert client.get("/api/v1/store/recommendations").json()[0]["id"] == item["id"]
    decision = client.post(f"/api/v1/store/recommendations/{item['id']}/decision",
                           data=json.dumps({"decision": "APPROVE"}),
                           content_type="application/json")
    assert decision.status_code == 200 and decision.json()["state"] == "APPLIED"
    offer.refresh_from_db()
    assert offer.current_price == Decimal("8.50")


def test_employee_api_cannot_read_recommendations(employee):
    client = Client()
    client.force_login(employee)
    assert client.get("/api/v1/store/recommendations").status_code == 403
    assert client.post("/api/v1/store/analysis", data="{}",
                       content_type="application/json").status_code == 403


@override_settings(DEBUG=True)
def test_simulated_history_requires_demo_store_and_explicit_boolean(prepared):
    owner, _, _, _, _ = prepared
    with pytest.raises(services.DomainError) as error:
        pricing_service.analyze_store(owner, demo_history=True)
    assert error.value.code == "DEMO_HISTORY_UNAVAILABLE"
    with pytest.raises(services.DomainError) as error:
        pricing_service.analyze_store(owner, demo_history="true")
    assert error.value.code == "INVALID_FLAG"


@override_settings(DEBUG=True)
def test_seeded_demo_can_show_labeled_actionable_suggestion(db, monkeypatch, model_stub):
    monkeypatch.setenv("DESSOF_DEMO_PASSWORD", "TemporaryDemoPass123!")
    call_command("seed_demo", verbosity=0)
    monkeypatch.setattr(pricing_service, "_load_model", lambda: model_stub)
    owner = User.objects.get(email="dueno.1@demo.example")
    normal = pricing_service.analyze_store(owner)
    assert not Recommendation.objects.filter(run=normal, state="PENDING").exists()
    simulated = pricing_service.analyze_store(owner, demo_history=True)
    pending = Recommendation.objects.filter(run=simulated, state="PENDING")
    assert pending.exists()
    assert all(item.snapshot["history_source"] == "synthetic_demo_history" for item in pending)
    assert all("historial simulado" in item.explanation for item in pending)
    client = Client()
    client.force_login(owner)
    response = client.post("/api/v1/store/analysis",
                           data=json.dumps({"demo_history": True}),
                           content_type="application/json")
    assert response.status_code == 200
    assert any(item["state"] == "PENDING" and
               item["history_source"] == "synthetic_demo_history"
               for item in response.json()["recommendations"])
