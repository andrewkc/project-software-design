"""Opt-in automation must never cross store, consent or evaluation boundaries."""

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from core import pricing_service, services
from core.models import AnalysisRun, OfferLimit, PriceChange, Recommendation, StorePricingPolicy


pytestmark = pytest.mark.django_db


@pytest.fixture
def ready(owner, offer, product, monkeypatch):
    owner.store.name = "Mercado Verde"
    owner.store.save(update_fields=["name"])
    policy = StorePricingPolicy.objects.create(store=owner.store, version=1,
        mode=StorePricingPolicy.Mode.REVIEW, starts_at=timezone.now(), created_by=owner)
    OfferLimit.objects.create(offer=offer, version=1, max_discount_pct=Decimal("30"),
        minimum_price=Decimal("7.00"), authorized_by=owner, starts_at=timezone.now())
    today = timezone.localdate()
    lot = offer.lot
    lot.received_date = today
    lot.expiry_date = today + timedelta(days=7)
    lot.sales_close_at = timezone.now() + timedelta(days=6)
    lot.save(update_fields=["received_date", "expiry_date", "sales_close_at"])
    report = {"artifact": "demo.joblib", "artifact_sha256": "a" * 64,
        "state": "EXPERIMENTAL", "features_version": "test",
        "dataset_version": "test", "evaluation": {}, "model_parameters": {},
        "trained_at_utc": timezone.now().isoformat()}
    monkeypatch.setattr(pricing_service, "_load_model", lambda: (object(), report))
    monkeypatch.setattr(pricing_service, "_demo_model_validated", lambda value: True)
    monkeypatch.setattr(pricing_service, "_demo_history", lambda value: (7, 7, 14, 14))
    monkeypatch.setattr(pricing_service.ml_pricing, "recommend_price", lambda *args, **kwargs: {
        "status": "PENDING", "reason": "TARGET_COVERAGE", "current_price": "9.00",
        "proposed_price": "8.50", "current_coverage": 0.6,
        "proposed_coverage": 0.9})
    return owner, offer, policy


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_owner_must_explicitly_confirm_automatic_mode(ready):
    owner, _, policy = ready
    with pytest.raises(services.DomainError) as error:
        pricing_service.set_policy_mode(owner, "AUTOMATIC")
    assert error.value.code == "CONFIRMATION_REQUIRED"
    policy.refresh_from_db()
    assert policy.mode == "REVIEW" and policy.ends_at is None


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=False)
def test_automatic_mode_refuses_deployment_without_demo_flag(ready):
    owner, _, _ = ready
    with pytest.raises(services.DomainError) as error:
        pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    assert error.value.code == "DEMO_AUTOMATIC_UNAVAILABLE"


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_only_demo_store_can_activate(owner, offer, monkeypatch):
    StorePricingPolicy.objects.create(store=owner.store, version=1,
        mode="REVIEW", starts_at=timezone.now(), created_by=owner)
    with pytest.raises(services.DomainError) as error:
        pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    assert error.value.code == "DEMO_AUTOMATIC_UNAVAILABLE"


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_model_evaluation_and_limits_gate_activation(ready, monkeypatch):
    owner, offer, _ = ready
    monkeypatch.setattr(pricing_service, "_demo_model_validated", lambda value: False)
    with pytest.raises(services.DomainError) as error:
        pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    assert error.value.code == "MODEL_NOT_DEMO_VALIDATED"
    monkeypatch.setattr(pricing_service, "_demo_model_validated", lambda value: True)
    OfferLimit.objects.filter(offer=offer).delete()
    with pytest.raises(services.DomainError) as error:
        pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    assert error.value.code == "LIMIT_REQUIRED"


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_owner_can_activate_and_return_to_review(ready):
    owner, _, old = ready
    automatic = pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    assert automatic.mode == "AUTOMATIC" and automatic.version == 2
    old.refresh_from_db()
    assert old.ends_at is not None
    assert pricing_service.set_policy_mode(owner, "AUTOMATIC", True).id == automatic.id
    review = pricing_service.set_policy_mode(owner, "REVIEW")
    assert review.mode == "REVIEW" and review.version == 3


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_daily_job_applies_once_with_system_audit(ready):
    owner, offer, _ = ready
    pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    first = pricing_service.run_automatic_pricing()
    assert first["applied"] == 1
    offer.refresh_from_db()
    assert offer.current_price == Decimal("8.50")
    change = PriceChange.objects.get(offer=offer)
    assert change.origin == "AUTOMATIC" and change.actor_id is None
    assert Recommendation.objects.get(run__origin="DAILY").decided_by_id is None
    pricing_service.run_automatic_pricing()
    assert PriceChange.objects.filter(offer=offer).count() == 1
    assert AnalysisRun.objects.filter(origin="DAILY").count() == 1


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_disabled_policy_does_not_apply_automatically(ready):
    owner, offer, _ = ready
    pricing_service.set_policy_mode(owner, "AUTOMATIC", True)
    pricing_service.set_policy_mode(owner, "REVIEW")
    assert pricing_service.run_automatic_pricing()["applied"] == 0
    offer.refresh_from_db()
    assert offer.current_price == Decimal("9.00")


@override_settings(DEMO_ALLOW_SYNTHETIC_HISTORY=True)
def test_policy_api_is_owner_only_and_does_not_auto_activate(ready, employee):
    owner, _, _ = ready
    client = Client()
    client.force_login(employee)
    assert client.get("/api/v1/store/pricing-policy").status_code == 403
    client.force_login(owner)
    assert client.get("/api/v1/store/pricing-policy").json()["mode"] == "REVIEW"
    response = client.post("/api/v1/store/pricing-policy",
        data=json.dumps({"mode": "AUTOMATIC"}), content_type="application/json")
    assert response.status_code == 422
    response = client.post("/api/v1/store/pricing-policy",
        data=json.dumps({"mode": "AUTOMATIC", "confirm_demo_synthetic": True}),
        content_type="application/json")
    assert response.status_code == 200 and response.json()["mode"] == "AUTOMATIC"


def test_evaluation_requires_matching_model_and_all_safe_seeds(tmp_path, monkeypatch):
    monkeypatch.setattr(pricing_service, "MODEL_ROOT", tmp_path)
    report = {"artifact_sha256": "a" * 64}
    evaluation = {"status": "OFFLINE_SYNTHETIC_EVALUATION_ONLY",
        "model_sha256": "a" * 64, "all_scenarios_safe": True,
        "expected_unsold_no_worse": True,
        "scenarios": [{"seed": seed, "scenarios": 10, "price_violations": 0,
                       "model_expected_unsold_no_worse_than_hold": True}
                      for seed in range(42, 48)]}
    path = tmp_path / "pricing-evaluation.json"
    path.write_text(json.dumps(evaluation), encoding="utf-8")
    assert pricing_service._demo_model_validated(report)
    with patch.dict(evaluation, {"model_sha256": "b" * 64}):
        path.write_text(json.dumps(evaluation), encoding="utf-8")
        assert not pricing_service._demo_model_validated(report)
    evaluation["model_sha256"] = "a" * 64
    evaluation["scenarios"][0]["seed"] = 43
    path.write_text(json.dumps(evaluation), encoding="utf-8")
    assert not pricing_service._demo_model_validated(report)
