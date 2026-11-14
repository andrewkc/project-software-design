"""Public catalog and local checkout simulation; provider adapter arrives in phase 4."""

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import services
from .models import (InventoryMovement, Lot, MovementLine, Offer, Order, OrderLine,
                     PaymentAttempt, Reservation, Store, User)


def require_customer(actor):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise services.DomainError("AUTH_REQUIRED", "Inicia sesión", 401)
    if actor.role != User.Role.CUSTOMER:
        raise services.DomainError("FORBIDDEN", "Esta operación es para compradores", 403)


def public_offers(store_id=None):
    now = timezone.now()
    query = Offer.objects.select_related("lot__product__store").filter(
        state=Offer.State.PUBLISHED, lot__active=True, lot__product__active=True,
        lot__product__store__active=True, lot__sales_close_at__gt=now,
        lot__expiry_date__gt=timezone.localdate(),
    )
    if store_id:
        query = query.filter(lot__product__store_id=services.parse_uuid(store_id, "store_id"))
    return [offer for offer in query.order_by("lot__sales_close_at", "id")
            if offer.lot.available_qty >= offer.lot.product.sale_step]


def offer_payload(offer):
    product, lot, store = offer.lot.product, offer.lot, offer.lot.product.store
    return {"id": str(offer.id), "store_id": str(store.id), "store_name": store.name,
            "store_address": store.address, "opening_hours": store.opening_hours,
            "product_name": product.name, "category": product.category,
            "description": product.description, "storage_conditions": product.storage_conditions,
            "unit": product.unit, "sale_step": product.sale_step,
            "lot_code": lot.code, "expiry_date": lot.expiry_date.isoformat(),
            "sales_close_at": lot.sales_close_at.isoformat(),
            "available_steps": lot.available_qty // product.sale_step,
            "original_price": str(offer.original_price), "current_price": str(offer.current_price)}


def order_payload(order):
    attempt = order.payment_attempts.order_by("-created_at").first()
    payment_mode = attempt.provider if attempt else ("MERCADOPAGO_TEST" if settings.MERCADOPAGO_ACCESS_TOKEN else "LOCAL_SIMULATION")
    lines = order.lines.select_related("offer__lot__product").order_by("id")
    return {"id": str(order.id), "store_id": str(order.store_id), "store_name": order.store.name,
            "state": order.state, "currency": order.currency, "total": str(order.total),
            "reservation_until": order.reservation_until.isoformat(),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "payment_mode": payment_mode,
            "payment_started": bool(attempt and attempt.provider == "MERCADOPAGO_TEST" and attempt.response_summary.get("provider_order_id")),
            "payment_state": attempt.state if attempt else None,
            "pickup_address": order.store.address,
            "lines": [{"offer_id": str(line.offer_id), "product_name": line.offer.lot.product.name,
                       "base_quantity": line.base_qty, "step": line.step_snapshot,
                       "price_per_step": str(line.step_price_snapshot), "amount": str(line.amount),
                       "expiry_date": line.expiry_snapshot.isoformat()} for line in lines]}


def _hash(lines):
    return hashlib.sha256(json.dumps(lines, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _parse_lines(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 20:
        raise services.DomainError("INVALID_LINES", "Agrega entre 1 y 20 ofertas")
    lines = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            raise services.DomainError("INVALID_LINES", "Línea de pedido inválida")
        offer_id = services.parse_uuid(item.get("offer_id"), "offer_id")
        qty = services.positive_int(item.get("base_quantity"), "base_quantity")
        if offer_id in seen:
            raise services.DomainError("DUPLICATE_OFFER", "No repitas una oferta")
        seen.add(offer_id)
        lines.append({"offer_id": str(offer_id), "base_quantity": qty})
    return sorted(lines, key=lambda line: line["offer_id"])


@transaction.atomic
def create_order(actor, data):
    require_customer(actor)
    key = services.parse_uuid(data.get("idempotency_key"), "idempotency_key")
    lines = _parse_lines(data.get("lines"))
    fingerprint = _hash(lines)
    services._lock_idempotency_key(key)
    old = Order.objects.filter(idempotency_key=key).first()
    if old:
        if old.customer_id != actor.id or old.request_hash != fingerprint:
            raise services.DomainError("IDEMPOTENCY_CONFLICT", "La clave ya se usó con otros datos", 409)
        return old

    ids = [line["offer_id"] for line in lines]
    offers = {str(offer.id): offer for offer in Offer.objects.select_for_update().select_related(
        "lot__product__store").filter(id__in=ids).order_by("id")}
    if len(offers) != len(lines):
        raise services.DomainError("OFFER_UNAVAILABLE", "Oferta no disponible", 409)
    lots = {str(lot.id): lot for lot in Lot.objects.select_for_update().filter(
        id__in=[offer.lot_id for offer in offers.values()]).order_by("id")}
    now = timezone.now()
    store_ids = {offer.lot.product.store_id for offer in offers.values()}
    if len(store_ids) != 1:
        raise services.DomainError("MIXED_STORES", "El pedido debe ser de una sola bodega")
    total = Decimal("0.00")
    expiry = now + timedelta(minutes=10)
    details = []
    for item in lines:
        offer = offers[item["offer_id"]]
        lot = lots[str(offer.lot_id)]
        product = offer.lot.product
        qty = item["base_quantity"]
        if (offer.state != Offer.State.PUBLISHED or not lot.active or not product.active or
                not product.store.active or lot.sales_close_at <= now or
                lot.expiry_date <= timezone.localdate()):
            raise services.DomainError("OFFER_UNAVAILABLE", "Oferta no disponible", 409)
        if qty % product.sale_step:
            raise services.DomainError("INVALID_STEP", "Cantidad fuera del paso de venta")
        if qty > lot.available_qty:
            raise services.DomainError("INSUFFICIENT_STOCK", "No hay stock disponible", 409)
        amount = Decimal(qty // product.sale_step) * offer.current_price
        total += amount
        expiry = min(expiry, lot.sales_close_at)
        details.append((offer, lot, qty, amount))
    if expiry <= now or total >= Decimal("1000000000000"):
        raise services.DomainError("OFFER_UNAVAILABLE", "Oferta no disponible", 409)
    order = Order.objects.create(customer=actor, store_id=next(iter(store_ids)),
                                 total=total, reservation_until=expiry,
                                 idempotency_key=key, request_hash=fingerprint)
    for offer, lot, qty, amount in details:
        product = offer.lot.product
        line = OrderLine.objects.create(order=order, offer=offer, base_qty=qty,
                                        step_snapshot=product.sale_step,
                                        step_price_snapshot=offer.current_price, amount=amount,
                                        expiry_snapshot=lot.expiry_date, offer_version=offer.version)
        Reservation.objects.create(line=line, lot=lot, base_qty=qty, expires_at=expiry)
        lot.reserved_qty += qty
        lot.save(update_fields=["reserved_qty", "updated_at"])
    return order


def get_order(actor, order_id):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise services.DomainError("AUTH_REQUIRED", "Inicia sesión", 401)
    order = Order.objects.select_related("store").filter(pk=services.parse_uuid(order_id, "order_id")).first()
    if not order or not (actor.role == User.Role.CUSTOMER and order.customer_id == actor.id or
                         actor.role in (User.Role.OWNER, User.Role.EMPLOYEE) and actor.store_id == order.store_id):
        raise services.DomainError("NOT_FOUND", "Pedido no encontrado", 404)
    return order


def _release(order, state):
    reservations = list(Reservation.objects.select_related("lot").filter(
        line__order=order, state=Reservation.State.ACTIVE).order_by("lot_id"))
    lots = {lot.id: lot for lot in Lot.objects.select_for_update().filter(
        id__in=[item.lot_id for item in reservations]).order_by("id")}
    now = timezone.now()
    for item in reservations:
        lot = lots[item.lot_id]
        lot.reserved_qty -= item.base_qty
        lot.save(update_fields=["reserved_qty", "updated_at"])
        item.state, item.closed_at = Reservation.State.RELEASED, now
        item.save(update_fields=["state", "closed_at", "updated_at"])
    order.state = state
    order.save(update_fields=["state", "updated_at"])


@transaction.atomic
def expire_order(order_id):
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.state == Order.State.PENDING and order.reservation_until <= timezone.now():
        _release(order, Order.State.EXPIRED)
    return order


def expire_due_orders(limit=100):
    ids = list(Order.objects.filter(state=Order.State.PENDING,
                                    reservation_until__lte=timezone.now()).order_by(
        "reservation_until").values_list("id", flat=True)[:limit])
    for order_id in ids:
        expire_order(order_id)


@transaction.atomic
def simulate_payment(actor, order_id, decision):
    require_customer(actor)
    if decision not in ("APPROVE", "REJECT"):
        raise services.DomainError("INVALID_DECISION", "Elige aprobar o rechazar la simulación")
    order = get_order(actor, order_id)
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.state in (Order.State.PAID, Order.State.FAILED):
        if (order.state == Order.State.PAID) != (decision == "APPROVE"):
            raise services.DomainError("ORDER_FINALIZED", "El pedido ya tiene un resultado", 409)
        return order
    if order.state != Order.State.PENDING:
        raise services.DomainError("ORDER_FINALIZED", "El pedido ya no está pendiente", 409)
    if order.reservation_until <= timezone.now():
        _release(order, Order.State.EXPIRED)
        return order
    if order.payment_attempts.exclude(provider="LOCAL_SIMULATION").exists():
        raise services.DomainError("PAYMENT_ALREADY_STARTED", "Este pedido usa Mercado Pago", 409)
    attempt = PaymentAttempt.objects.create(order=order, provider="LOCAL_SIMULATION",
                                            state=PaymentAttempt.State.CREATED, amount=order.total,
                                            provider_key=uuid.uuid4())
    if decision == "REJECT":
        _release(order, Order.State.FAILED)
        attempt.state = PaymentAttempt.State.REJECTED
        attempt.save(update_fields=["state", "updated_at"])
        return order
    return _approve_order(order, attempt)


def _approve_order(order, attempt):
    reservations = list(Reservation.objects.select_related("line__offer__lot__product").filter(
        line__order=order, state=Reservation.State.ACTIVE).order_by("lot_id"))
    lots = {lot.id: lot for lot in Lot.objects.select_for_update().filter(
        id__in=[item.lot_id for item in reservations]).order_by("id")}
    if len(reservations) != order.lines.count():
        raise services.DomainError("RESERVATION_MISSING", "Reserva incompleta", 409)
    movement = InventoryMovement.objects.create(store=order.store, actor=None,
        kind=InventoryMovement.Kind.WEB_SALE, state=InventoryMovement.State.CONFIRMED,
        order=order, confirmed_at=timezone.now(), idempotency_key=uuid.uuid4(),
        request_hash=order.request_hash)
    for item in reservations:
        lot = lots[item.lot_id]
        if lot.physical_qty < item.base_qty or lot.reserved_qty < item.base_qty:
            raise services.DomainError("RESERVATION_MISSING", "Reserva inconsistente", 409)
        line = item.line
        MovementLine.objects.create(movement=movement, lot=lot, physical_delta=-item.base_qty,
                                    step_price_snapshot=line.step_price_snapshot, amount=line.amount,
                                    snapshot={"unit": lot.product.unit, "step": line.step_snapshot,
                                              "price": str(line.step_price_snapshot)})
        lot.physical_qty -= item.base_qty
        lot.reserved_qty -= item.base_qty
        lot.save(update_fields=["physical_qty", "reserved_qty", "updated_at"])
        item.state, item.closed_at = Reservation.State.CONSUMED, timezone.now()
        item.save(update_fields=["state", "closed_at", "updated_at"])
    order.state, order.paid_at = Order.State.PAID, timezone.now()
    order.save(update_fields=["state", "paid_at", "updated_at"])
    attempt.state, attempt.approved_at = PaymentAttempt.State.APPROVED, order.paid_at
    attempt.save(update_fields=["state", "approved_at", "updated_at"])
    return order


@transaction.atomic
def approve_external_payment(order_id, attempt_id):
    order = Order.objects.select_for_update().get(pk=order_id)
    attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id, order=order, provider="MERCADOPAGO_TEST")
    if order.state in (Order.State.PAID, Order.State.PAYMENT_REVIEW):
        return order
    if order.state != Order.State.PENDING or order.reservation_until <= timezone.now():
        if order.state == Order.State.PENDING:
            _release(order, Order.State.PAYMENT_REVIEW)
        else:
            order.state = Order.State.PAYMENT_REVIEW
            order.save(update_fields=["state", "updated_at"])
        attempt.state = PaymentAttempt.State.APPROVED
        attempt.approved_at = timezone.now()
        attempt.save(update_fields=["state", "approved_at", "updated_at"])
        return order
    return _approve_order(order, attempt)


@transaction.atomic
def reject_external_payment(order_id, attempt_id):
    order = Order.objects.select_for_update().get(pk=order_id)
    attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id, order=order, provider="MERCADOPAGO_TEST")
    if order.state == Order.State.PENDING:
        _release(order, Order.State.FAILED)
    if order.state in (Order.State.FAILED, Order.State.EXPIRED):
        attempt.state = PaymentAttempt.State.REJECTED
        attempt.save(update_fields=["state", "updated_at"])
    return order
