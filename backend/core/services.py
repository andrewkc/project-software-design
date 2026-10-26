"""Transactional store operations. Views never edit stock or prices directly."""

import hashlib
import json
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from .models import (
    InventoryMovement, Lot, MovementLine, Offer, OfferLimit, PriceChange,
    Product, User,
)


LIMA = ZoneInfo("America/Lima")
CENT = Decimal("0.01")


class DomainError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def require_staff(actor, owner_only=False):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise DomainError("AUTH_REQUIRED", "Inicia sesión", 401)
    allowed = (User.Role.OWNER,) if owner_only else (User.Role.OWNER, User.Role.EMPLOYEE)
    if actor.role not in allowed or not actor.store_id or not actor.store.active:
        raise DomainError("FORBIDDEN", "No tienes permiso para esta operación", 403)


def positive_int(value, field, multiple=None):
    if isinstance(value, bool):
        raise DomainError("INVALID_QUANTITY", f"{field} debe ser entero positivo")
    try:
        text = str(value)
        if not text.isdigit():
            raise ValueError
        result = int(text)
    except (TypeError, ValueError):
        raise DomainError("INVALID_QUANTITY", f"{field} debe ser entero positivo") from None
    if result <= 0 or result > 9_000_000_000_000_000_000:
        raise DomainError("INVALID_QUANTITY", f"{field} fuera de rango")
    if multiple and result % multiple:
        raise DomainError("INVALID_STEP", f"{field} debe ser múltiplo de {multiple}")
    return result


def signed_int(value, field):
    if isinstance(value, bool):
        raise DomainError("INVALID_QUANTITY", f"{field} debe ser entero distinto de cero")
    try:
        text = str(value)
        if text.startswith("-"):
            digits = text[1:]
        else:
            digits = text
        if not digits.isdigit():
            raise ValueError
        result = int(text)
    except (TypeError, ValueError):
        raise DomainError("INVALID_QUANTITY", f"{field} debe ser entero distinto de cero") from None
    if result == 0 or abs(result) > 9_000_000_000_000_000_000:
        raise DomainError("INVALID_QUANTITY", f"{field} fuera de rango")
    return result


def money(value, field, zero_allowed=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise DomainError("INVALID_MONEY", f"{field} no es un importe válido") from None
    if not result.is_finite() or result.as_tuple().exponent < -2 or result >= Decimal("1000000000000"):
        raise DomainError("INVALID_MONEY", f"{field} debe tener máximo dos decimales")
    if result < 0 or (not zero_allowed and result == 0):
        raise DomainError("INVALID_MONEY", f"{field} debe ser positivo")
    return result.quantize(CENT)


def required_text(value, field, max_length=150):
    text = str(value or "").strip()
    if not text or len(text) > max_length:
        raise DomainError("INVALID_TEXT", f"{field} es obligatorio y debe tener máximo {max_length} caracteres")
    return text


def parse_date(value, field):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise DomainError("INVALID_DATE", f"{field} debe tener formato YYYY-MM-DD") from None


def parse_uuid(value, field):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise DomainError("INVALID_ID", f"{field} no es válido") from None


def _model_save(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise DomainError("INVALID_DATA", "; ".join(error.messages)) from error
    instance.save()
    return instance


def _product(actor, product_id, lock=False):
    query = Product.objects.filter(pk=parse_uuid(product_id, "product_id"), store_id=actor.store_id)
    if lock:
        query = query.select_for_update()
    product = query.first()
    if not product:
        raise DomainError("NOT_FOUND", "Producto no encontrado", 404)
    return product


def _lot(actor, lot_id, lock=False):
    query = Lot.objects.select_related("product").filter(pk=parse_uuid(lot_id, "lot_id"), product__store_id=actor.store_id)
    if lock:
        query = query.select_for_update()
    lot = query.first()
    if not lot:
        raise DomainError("NOT_FOUND", "Lote no encontrado", 404)
    return lot


def _offer(actor, offer_id, lock=False):
    query = Offer.objects.select_related("lot__product").filter(pk=parse_uuid(offer_id, "offer_id"), lot__product__store_id=actor.store_id)
    if lock:
        query = query.select_for_update()
    offer = query.first()
    if not offer:
        raise DomainError("NOT_FOUND", "Oferta no encontrada", 404)
    return offer


def _fingerprint(kind, payload):
    return hashlib.sha256(json.dumps({"kind": kind, "payload": payload}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _existing_movement(actor, key, fingerprint):
    old = InventoryMovement.objects.filter(idempotency_key=key).first()
    if not old:
        return None
    if old.store_id != actor.store_id or old.request_hash != fingerprint:
        raise DomainError("IDEMPOTENCY_CONFLICT", "La clave ya se usó con otros datos", 409)
    return old


def _lock_idempotency_key(key):
    # PostgreSQL transaction-scoped lock serializes two first uses of the same key.
    lock_id = key.int & ((1 << 63) - 1)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


def _movement(actor, kind, key, fingerprint, reason="", order=None):
    return InventoryMovement.objects.create(
        store_id=actor.store_id, actor=actor, kind=kind,
        state=InventoryMovement.State.CONFIRMED, confirmed_at=timezone.now(),
        idempotency_key=key, request_hash=fingerprint, reason=reason, order=order,
    )


def movement_result(movement):
    lines = list(movement.lines.select_related("lot__product").order_by("lot__sales_close_at", "lot_id"))
    return {
        "id": str(movement.id), "kind": movement.kind, "state": movement.state,
        "reason": movement.reason, "confirmed_at": movement.confirmed_at.isoformat() if movement.confirmed_at else None,
        "actor_id": str(movement.actor_id) if movement.actor_id else None,
        "total": str(sum((line.amount or Decimal("0.00") for line in lines), Decimal("0.00"))),
        "lines": [{"lot_id": str(line.lot_id), "product_id": str(line.lot.product_id),
                   "delta": line.physical_delta, "amount": str(line.amount) if line.amount is not None else None}
                  for line in lines],
    }


@transaction.atomic
def create_product(actor, data):
    require_staff(actor, owner_only=True)
    unit = data.get("unit")
    if unit not in (Product.Unit.GRAM, Product.Unit.UNIT):
        raise DomainError("INVALID_UNIT", "Unidad debe ser G o UNIT")
    product = Product(
        store_id=actor.store_id,
        code=required_text(data.get("code"), "Código", 40),
        name=required_text(data.get("name"), "Nombre"),
        category=required_text(data.get("category"), "Categoría", 80),
        unit=unit,
        sale_step=positive_int(data.get("sale_step"), "Paso"),
        reference_price=money(data.get("reference_price"), "Precio"),
        storage_conditions=required_text(data.get("storage_conditions"), "Conservación", 1000),
        description=str(data.get("description") or "")[:2000],
    )
    return _model_save(product)


@transaction.atomic
def create_inbound(actor, data):
    require_staff(actor, owner_only=True)
    key = parse_uuid(data.get("idempotency_key"), "idempotency_key")
    product_id = parse_uuid(data.get("product_id"), "product_id")
    code = required_text(data.get("code"), "Código de lote", 80)
    received_date = parse_date(data.get("received_date"), "received_date")
    expiry_date = parse_date(data.get("expiry_date"), "expiry_date")
    qty = positive_int(data.get("quantity"), "Cantidad")
    cost = money(data.get("total_cost"), "Costo total", zero_allowed=True)
    payload = {"product_id": str(product_id), "code": code, "received_date": received_date.isoformat(),
               "expiry_date": expiry_date.isoformat(), "quantity": qty, "total_cost": str(cost)}
    fingerprint = _fingerprint("INBOUND", payload)
    _lock_idempotency_key(key)
    existing = _existing_movement(actor, key, fingerprint)
    if existing:
        return existing.lines.select_related("lot").first().lot, existing
    product = _product(actor, product_id, lock=True)
    if not product.active or not product.store.active:
        raise DomainError("INACTIVE_PRODUCT", "Producto o tienda inactiva", 409)
    if expiry_date - received_date < timedelta(days=7):
        raise DomainError("SHORT_LIFETIME", "El lote debe durar al menos siete días")
    close = datetime.combine(expiry_date - timedelta(days=1), time(23, 59, 59), LIMA)
    lot = _model_save(Lot(product=product, code=code, received_date=received_date, expiry_date=expiry_date,
                          sales_close_at=close, total_cost=cost, received_qty=qty, physical_qty=0))
    movement = _movement(actor, InventoryMovement.Kind.INBOUND, key, fingerprint)
    MovementLine.objects.create(movement=movement, lot=lot, physical_delta=qty,
                                snapshot={"unit": product.unit, "step": product.sale_step})
    lot.physical_qty = qty
    lot.save(update_fields=["physical_qty", "updated_at"])
    _model_save(Offer(lot=lot, state=Offer.State.DRAFT, original_price=product.reference_price,
                      current_price=product.reference_price))
    return lot, movement


def _sale_lots(actor, product, now):
    return list(Lot.objects.select_for_update().filter(product=product, active=True, sales_close_at__gt=now,
                                                       physical_qty__gt=0).order_by("sales_close_at", "id"))


@transaction.atomic
def sell_local(actor, data):
    require_staff(actor)
    key = parse_uuid(data.get("idempotency_key"), "idempotency_key")
    product_id = parse_uuid(data.get("product_id"), "product_id")
    qty = positive_int(data.get("quantity"), "Cantidad")
    payload = {"product_id": str(product_id), "quantity": qty}
    fingerprint = _fingerprint("LOCAL_SALE", payload)
    _lock_idempotency_key(key)
    existing = _existing_movement(actor, key, fingerprint)
    if existing:
        return existing
    product = _product(actor, product_id, lock=True)
    if not product.active:
        raise DomainError("INACTIVE_PRODUCT", "Producto inactivo", 409)
    if qty % product.sale_step:
        raise DomainError("INVALID_STEP", "Cantidad fuera del paso de venta")
    now = timezone.now()
    allocations = []
    remaining = qty
    for lot in _sale_lots(actor, product, now):
        available_steps = (lot.physical_qty - lot.reserved_qty) // product.sale_step
        taken = min(remaining, available_steps * product.sale_step)
        if not taken:
            continue
        offer = Offer.objects.filter(lot=lot, state=Offer.State.PUBLISHED).first()
        price = offer.current_price if offer else product.reference_price
        allocations.append((lot, taken, price))
        remaining -= taken
        if remaining == 0:
            break
    if remaining:
        raise DomainError("INSUFFICIENT_STOCK", "No hay stock apto suficiente", 409)
    movement = _movement(actor, InventoryMovement.Kind.LOCAL_SALE, key, fingerprint)
    for lot, taken, price in allocations:
        amount = Decimal(taken // product.sale_step) * price
        MovementLine.objects.create(movement=movement, lot=lot, physical_delta=-taken,
                                    step_price_snapshot=price, amount=amount,
                                    snapshot={"unit": product.unit, "step": product.sale_step, "price": str(price)})
        lot.physical_qty -= taken
        lot.save(update_fields=["physical_qty", "updated_at"])
    return movement


@transaction.atomic
def waste(actor, data):
    return _change_stock(actor, data, InventoryMovement.Kind.WASTE)


@transaction.atomic
def adjust(actor, data):
    return _change_stock(actor, data, InventoryMovement.Kind.ADJUSTMENT)


def _change_stock(actor, data, kind):
    require_staff(actor, owner_only=True)
    key = parse_uuid(data.get("idempotency_key"), "idempotency_key")
    lot_id = parse_uuid(data.get("lot_id"), "lot_id")
    reason = required_text(data.get("reason"), "Motivo", 1000)
    delta = -positive_int(data.get("quantity"), "Cantidad") if kind == InventoryMovement.Kind.WASTE else signed_int(data.get("delta"), "Delta")
    payload = {"lot_id": str(lot_id), "delta": delta, "reason": reason}
    fingerprint = _fingerprint(kind, payload)
    _lock_idempotency_key(key)
    existing = _existing_movement(actor, key, fingerprint)
    if existing:
        return existing
    lot = _lot(actor, lot_id, lock=True)
    new_physical = lot.physical_qty + delta
    if new_physical < lot.reserved_qty:
        raise DomainError("INSUFFICIENT_STOCK", "El ajuste afectaría stock reservado o dejaría saldo negativo", 409)
    movement = _movement(actor, kind, key, fingerprint, reason=reason)
    MovementLine.objects.create(movement=movement, lot=lot, physical_delta=delta,
                                snapshot={"before": lot.physical_qty, "reserved": lot.reserved_qty})
    lot.physical_qty = new_physical
    lot.save(update_fields=["physical_qty", "updated_at"])
    return movement


def cost_per_step(offer):
    lot = offer.lot
    raw = lot.total_cost * Decimal(lot.product.sale_step) / Decimal(lot.received_qty)
    return raw.quantize(CENT, rounding=ROUND_CEILING)


def price_floor(offer, limit):
    discount_floor = (offer.original_price * (Decimal("1") - limit.max_discount_pct / Decimal("100"))).quantize(CENT, rounding=ROUND_CEILING)
    floors = [limit.minimum_price, discount_floor]
    if not limit.below_cost_authorized:
        floors.append(cost_per_step(offer))
    return max(floors)


@transaction.atomic
def publish_offer(actor, offer_id):
    require_staff(actor, owner_only=True)
    offer = _offer(actor, offer_id, lock=True)
    if not offer.lot.active or not offer.lot.product.active or offer.lot.sales_close_at <= timezone.now():
        raise DomainError("LOT_CLOSED", "Lote no apto para publicación", 409)
    if offer.lot.available_qty < offer.lot.product.sale_step:
        raise DomainError("INSUFFICIENT_STOCK", "Lote sin un paso de venta disponible", 409)
    if offer.state != Offer.State.PUBLISHED:
        offer.state = Offer.State.PUBLISHED
        offer.version += 1
        offer.save(update_fields=["state", "version", "updated_at"])
    return offer


@transaction.atomic
def pause_offer(actor, offer_id):
    require_staff(actor, owner_only=True)
    offer = _offer(actor, offer_id, lock=True)
    if offer.state == Offer.State.PUBLISHED:
        offer.state = Offer.State.PAUSED
        offer.version += 1
        offer.save(update_fields=["state", "version", "updated_at"])
    return offer


@transaction.atomic
def set_offer_limit(actor, offer_id, data):
    require_staff(actor, owner_only=True)
    offer = _offer(actor, offer_id, lock=True)
    try:
        max_discount = Decimal(str(data.get("max_discount_pct")))
    except (InvalidOperation, TypeError):
        raise DomainError("INVALID_DISCOUNT", "Descuento máximo inválido") from None
    if not max_discount.is_finite() or max_discount.as_tuple().exponent < -2 or not (0 <= max_discount < 100):
        raise DomainError("INVALID_DISCOUNT", "Descuento debe estar entre 0 y 100, sin llegar a 100")
    minimum = money(data.get("minimum_price"), "Precio mínimo")
    below_cost = data.get("below_cost_authorized")
    if not isinstance(below_cost, bool):
        raise DomainError("INVALID_FLAG", "La autorización bajo costo debe ser explícita")
    if minimum < cost_per_step(offer) and not below_cost:
        raise DomainError("BELOW_COST_NEEDS_APPROVAL", "El dueño debe autorizar expresamente un mínimo bajo costo")
    current = OfferLimit.objects.select_for_update().filter(offer=offer, ends_at__isnull=True).first()
    version = current.version + 1 if current else 1
    candidate = OfferLimit(offer=offer, version=version, max_discount_pct=max_discount,
                           minimum_price=minimum, below_cost_authorized=below_cost,
                           authorized_by=actor, starts_at=timezone.now())
    if price_floor(offer, candidate) > offer.current_price:
        raise DomainError("LIMIT_ABOVE_CURRENT", "Los nuevos límites exceden el precio actual", 409)
    if current:
        current.ends_at = timezone.now()
        current.save(update_fields=["ends_at", "updated_at"])
    return _model_save(candidate)


@transaction.atomic
def change_price(actor, offer_id, data):
    require_staff(actor, owner_only=True)
    offer = _offer(actor, offer_id, lock=True)
    new_price = money(data.get("new_price"), "Nuevo precio")
    reason = required_text(data.get("reason"), "Motivo", 1000)
    if new_price > offer.current_price:
        raise DomainError("PRICE_INCREASE", "El descuento no puede subir el precio", 409)
    if new_price == offer.current_price:
        raise DomainError("NO_PRICE_CHANGE", "El precio no cambió")
    limit = OfferLimit.objects.filter(offer=offer, ends_at__isnull=True).first()
    if not limit:
        raise DomainError("LIMIT_REQUIRED", "Configura límites antes de bajar el precio", 409)
    floor = price_floor(offer, limit)
    if new_price < floor:
        raise DomainError("BELOW_FLOOR", f"El precio mínimo permitido es {floor}", 409)
    change = PriceChange.objects.create(offer=offer, old_price=offer.current_price, new_price=new_price,
                                        origin="MANUAL", actor=actor, reason=reason, limit_version=limit.version)
    offer.current_price = new_price
    offer.version += 1
    offer.automation_paused = True
    offer.save(update_fields=["current_price", "version", "automation_paused", "updated_at"])
    return change
