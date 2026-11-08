"""Owner-reviewed price suggestions for live offers; no automatic application."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import ml_data, ml_pricing, ml_train, services
from .models import (AnalysisRun, InventoryMovement, Lot, MLModel, MovementLine,
                     Offer, OfferLimit, PriceChange, Recommendation,
                     StorePricingPolicy)


MODEL_ROOT = Path(__file__).resolve().parents[1] / "media" / "ml_models"
LIMA = ZoneInfo("America/Lima")
STORE_CODES = {"Mercado Verde": "S1", "Dulce y Fresco": "S2"}
DEMO_STORES = {"Mercado Verde", "Dulce y Fresco", "Despensa Cercana"}
CATEGORIES = {"Fruta": "Fruta", "Frutas": "Fruta", "Frutos secos": "Frutos secos"}


def _owner(actor):
    services.require_staff(actor, owner_only=True)


def _load_model():
    artifact = MODEL_ROOT / "demand-seed-42.joblib"
    report = MODEL_ROOT / "demand-seed-42.json"
    try:
        return ml_train.load_trained(artifact, report)
    except (OSError, ValueError) as error:
        raise services.DomainError("MODEL_UNAVAILABLE", "Modelo local no disponible o incompatible", 503) from error


def _sales_history(product, today, now):
    """Only confirmed sales before the analysis instant; zero-sales days count."""
    start = datetime.combine(today - timedelta(days=14), time.min, LIMA)
    lines = MovementLine.objects.select_related("movement").filter(
        lot__product=product, physical_delta__lt=0,
        movement__kind__in=(InventoryMovement.Kind.LOCAL_SALE,
                            InventoryMovement.Kind.WEB_SALE),
        movement__state=InventoryMovement.State.CONFIRMED,
        movement__confirmed_at__gte=start, movement__confirmed_at__lt=now)
    by_day = defaultdict(int)
    for line in lines:
        day = timezone.localtime(line.movement.confirmed_at, LIMA).date()
        by_day[day] += (-line.physical_delta) // product.sale_step
    history_days = max(0, (today - timezone.localtime(product.created_at, LIMA).date()).days)
    lag7_days = min(7, history_days)
    lag14_days = min(14, history_days)
    return (sum(by_day[today - timedelta(days=offset)] for offset in range(1, lag7_days + 1)),
            lag7_days,
            sum(by_day[today - timedelta(days=offset)] for offset in range(1, lag14_days + 1)),
            lag14_days)


def _demo_history(product):
    """Independent synthetic seed, never inserted into operational sales."""
    rows, _, _, _ = ml_data.generate(seed=45)
    matching = [row for row in rows if row["split"] == "test" and
                row["product_id"].endswith(f"-{product.code}")]
    if len(matching) < 14:
        return None
    return (sum(row["observed_sales_steps"] for row in matching[-7:]), 7,
            sum(row["observed_sales_steps"] for row in matching[-14:]), 14)


def _first_day_fraction(now, close):
    local_now = timezone.localtime(now, LIMA)
    local_close = timezone.localtime(close, LIMA)
    opening = datetime.combine(local_now.date(), time(8), LIMA)
    closing = datetime.combine(local_now.date(), time(20), LIMA)
    if local_close.date() == local_now.date():
        closing = min(closing, local_close)
    start = max(opening, local_now)
    return max(0.0, min(1.0, (closing - start).total_seconds() / (12 * 3600)))


def _snapshot_key(store_id, day, offers, policy_version, model_sha, last_movement,
                  demo_history):
    values = [(str(offer.id), offer.version, str(offer.current_price),
               offer.lot.physical_qty, offer.lot.reserved_qty,
               getattr(offer, "current_limit_version", None)) for offer in offers]
    payload = [values, policy_version, model_sha, last_movement, demo_history]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
    return f"{store_id}:{day}:{digest}"


def _recommend(offer, limit, bundle, now, demo_history=False):
    lot = offer.lot
    product = lot.product
    today = timezone.localtime(now, LIMA).date()
    close_day = timezone.localtime(lot.sales_close_at, LIMA).date()
    available_steps = lot.available_qty // product.sale_step
    floor = services.price_floor(offer, limit)
    snapshot = {"lot_id": str(lot.id), "physical_qty": lot.physical_qty,
                "reserved_qty": lot.reserved_qty, "available_steps": available_steps,
                "sales_close_at": lot.sales_close_at.isoformat(),
                "history_source": "confirmed_local_and_web_sales"}
    keep = {"status": "KEEP", "proposed_price": str(offer.current_price),
            "current_price": str(offer.current_price), "available_steps": available_steps}
    if not lot.active or not product.active or offer.state != Offer.State.PUBLISHED or lot.sales_close_at <= now:
        return snapshot, {**keep, "reason": "OFFER_INACTIVE"}
    if not limit or floor > offer.current_price:
        return snapshot, {**keep, "reason": "LIMIT_UNAVAILABLE"}
    category = CATEGORIES.get(product.category)
    if not category:
        return snapshot, {**keep, "reason": "CATEGORY_OUTSIDE_TRAINING"}
    age = (today - lot.received_date).days
    if age < 0 or age > 8:
        return snapshot, {**keep, "reason": "LOT_AGE_OUTSIDE_TRAINING"}
    lag7, lag7_days, lag14, lag14_days = _sales_history(product, today, now)
    if demo_history and lag7_days < 3:
        simulated = _demo_history(product)
        if simulated:
            lag7, lag7_days, lag14, lag14_days = simulated
            snapshot["history_source"] = "synthetic_demo_history"
    product_stock = sum(max(0, item.available_qty) // product.sale_step
                        for item in Lot.objects.filter(product=product, active=True,
                                                       sales_close_at__gt=now))
    features = {"store_id": STORE_CODES.get(product.store.name, "UNSEEN_STORE"),
                "category": category,
                "price_ratio": float(offer.current_price / offer.original_price),
                "current_price": float(offer.current_price),
                "days_to_close": (close_day - today).days,
                "stock_steps": product_stock, "weekday": today.weekday(),
                "lot_age_days": age, "lag7_sales_sum": lag7,
                "lag7_days": lag7_days, "lag14_sales_sum": lag14,
                "lag14_days": lag14_days}
    snapshot["features"] = features
    return snapshot, ml_pricing.recommend_price(
        lambda cases: ml_train.predict(bundle, cases), features,
        original_price=offer.original_price, current_price=offer.current_price,
        floor=floor, available_steps=available_steps,
        first_day_fraction=_first_day_fraction(now, lot.sales_close_at))


@transaction.atomic
def analyze_store(actor, demo_history=False):
    """Produce idempotent recommendations. All price changes require owner review."""
    _owner(actor)
    if not isinstance(demo_history, bool):
        raise services.DomainError("INVALID_FLAG", "Indica explícitamente si usas historial de demo")
    if demo_history and (not settings.DEBUG or actor.store.name not in DEMO_STORES):
        raise services.DomainError("DEMO_HISTORY_UNAVAILABLE",
                                   "El historial simulado solo está disponible en bodegas demo locales", 403)
    bundle, report = _load_model()
    now = timezone.now()
    today = timezone.localtime(now, LIMA).date()
    policy = StorePricingPolicy.objects.filter(store_id=actor.store_id,
                                                ends_at__isnull=True).first()
    if not policy:
        raise services.DomainError("POLICY_REQUIRED", "Configura la política de precios", 409)
    offers = list(Offer.objects.select_related("lot__product__store").filter(
        lot__product__store_id=actor.store_id, state=Offer.State.PUBLISHED,
        lot__sales_close_at__gt=now).order_by("id")[:500])
    limits = {item.offer_id: item for item in OfferLimit.objects.filter(
        offer__in=offers, ends_at__isnull=True)}
    for offer in offers:
        offer.current_limit_version = limits.get(offer.id).version if limits.get(offer.id) else None
    last_movement = InventoryMovement.objects.filter(
        store_id=actor.store_id, state=InventoryMovement.State.CONFIRMED
    ).order_by("-confirmed_at", "-created_at").values_list("id", flat=True).first()
    key = _snapshot_key(actor.store_id, today, offers, policy.version,
                        report["artifact_sha256"], str(last_movement), demo_history)
    existing = AnalysisRun.objects.filter(deduplication_key=key).first()
    if existing:
        return existing
    model, _ = MLModel.objects.get_or_create(
        version=f"demand-{report['artifact_sha256'][:16]}",
        defaults={"artifact_path": str(MODEL_ROOT / report["artifact"]),
                  "sha256": report["artifact_sha256"], "state": report["state"],
                  "features_version": report["features_version"],
                  "dataset_version": report["dataset_version"],
                  "metrics": report["evaluation"],
                  "configuration": report["model_parameters"],
                  "trained_at": datetime.fromisoformat(report["trained_at_utc"])})
    run = AnalysisRun.objects.create(store_id=actor.store_id, model=model,
                                     origin="MANUAL", state="DONE",
                                     target_date=today, deduplication_key=key)
    for offer in offers:
        limit = limits.get(offer.id)
        if not limit:
            snapshot = {"available_steps": offer.lot.available_qty // offer.lot.product.sale_step,
                        "history_source": "confirmed_local_and_web_sales",
                        "physical_qty": offer.lot.physical_qty,
                        "reserved_qty": offer.lot.reserved_qty}
            prediction = {"status": "KEEP", "reason": "LIMIT_UNAVAILABLE",
                          "current_price": str(offer.current_price),
                          "proposed_price": str(offer.current_price)}
        else:
            snapshot, prediction = _recommend(offer, limit, bundle, now,
                                              demo_history=demo_history)
        Recommendation.objects.create(
            run=run, offer=offer, offer_version=offer.version,
            policy_version=policy.version, limit_version=limit.version if limit else 0,
            current_price=offer.current_price,
            proposed_price=Decimal(prediction["proposed_price"]),
            snapshot=snapshot, predictions=prediction,
            explanation=(f"{prediction['reason']}: estimación experimental con "
                         f"{'historial simulado' if snapshot['history_source'] == 'synthetic_demo_history' else 'ventas registradas'}; "
                         "requiere revisión del dueño."),
            state=prediction["status"])
    return run


def list_recommendations(actor):
    _owner(actor)
    return list(Recommendation.objects.select_related("offer__lot__product", "run__model")
                .filter(run__store_id=actor.store_id).order_by("-created_at")[:100])


@transaction.atomic
def decide(actor, recommendation_id, decision):
    _owner(actor)
    if decision not in ("APPROVE", "REJECT"):
        raise services.DomainError("INVALID_DECISION", "Decisión inválida")
    recommendation = Recommendation.objects.select_for_update().filter(
        id=recommendation_id, run__store_id=actor.store_id).first()
    if not recommendation:
        raise services.DomainError("NOT_FOUND", "Recomendación no encontrada", 404)
    resulting_state = "APPLIED" if decision == "APPROVE" else "REJECTED"
    if recommendation.state == resulting_state:
        return recommendation
    if recommendation.state != "PENDING":
        raise services.DomainError("DECISION_CONFLICT", "Recomendación ya no está pendiente", 409)
    if decision == "REJECT":
        recommendation.state = "REJECTED"
        recommendation.decided_by = actor
        recommendation.decided_at = timezone.now()
        recommendation.save(update_fields=["state", "decided_by", "decided_at", "updated_at"])
        return recommendation
    offer = Offer.objects.select_for_update().get(pk=recommendation.offer_id)
    lot = Lot.objects.select_for_update().get(pk=offer.lot_id)
    policy = StorePricingPolicy.objects.select_for_update().filter(
        store_id=actor.store_id, ends_at__isnull=True).first()
    limit = OfferLimit.objects.select_for_update().filter(
        offer_id=offer.id, ends_at__isnull=True).first()
    stale = (offer.version != recommendation.offer_version or
             offer.current_price != recommendation.current_price or
             offer.state != Offer.State.PUBLISHED or
             offer.automation_paused or lot.sales_close_at <= timezone.now() or
             not lot.active or lot.available_qty < lot.product.sale_step or
             lot.physical_qty != recommendation.snapshot.get("physical_qty") or
             lot.reserved_qty != recommendation.snapshot.get("reserved_qty") or
             not policy or policy.version != recommendation.policy_version or
             not limit or limit.version != recommendation.limit_version)
    if stale or not services.price_floor(offer, limit) <= recommendation.proposed_price < offer.current_price:
        recommendation.state = "STALE"
        recommendation.save(update_fields=["state", "updated_at"])
        return recommendation
    PriceChange.objects.create(
        offer=offer, recommendation=recommendation,
        old_price=offer.current_price, new_price=recommendation.proposed_price,
        origin="REVIEW", actor=actor,
        reason="Recomendación experimental aprobada por el dueño",
        limit_version=limit.version,
        model_version=recommendation.run.model.version)
    offer.current_price = recommendation.proposed_price
    offer.version += 1
    offer.save(update_fields=["current_price", "version", "updated_at"])
    recommendation.state = "APPLIED"
    recommendation.decided_by = actor
    recommendation.decided_at = timezone.now()
    recommendation.save(update_fields=["state", "decided_by", "decided_at", "updated_at"])
    return recommendation
