"""Boundary and rollback checks across the phase 1 schema and phase 2 services."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core import services
from core.models import InventoryMovement, Lot, MovementLine, OfferLimit, PriceChange, User


pytestmark = pytest.mark.django_db


def key():
    return str(uuid.uuid4())


def sale(product, quantity, idem=None):
    return {"product_id": str(product.id), "quantity": quantity, "idempotency_key": idem or key()}


def inbound(product, **updates):
    today = timezone.localdate()
    data = {"product_id": str(product.id), "code": "EDGE-01", "received_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=7)).isoformat(), "quantity": 500,
            "total_cost": "0.00", "idempotency_key": key()}
    data.update(updates)
    return data


def fails(code, operation, *args):
    with pytest.raises(services.DomainError) as error:
        operation(*args)
    assert error.value.code == code


def test_user_password_is_hashed_and_verifiable(owner):
    owner.refresh_from_db()
    assert owner.password != "SecurePass123!"
    assert owner.check_password("SecurePass123!")
    assert not owner.check_password("wrong")


@pytest.mark.parametrize("field,value", [("physical_qty", -1), ("reserved_qty", 1251),
                                           ("received_qty", 0), ("total_cost", Decimal("-0.01"))])
def test_database_rejects_invalid_lot_update_without_modifying_row(lot, field, value):
    before = getattr(lot, field)
    with pytest.raises(IntegrityError), transaction.atomic():
        Lot.objects.filter(pk=lot.pk).update(**{field: value})
    lot.refresh_from_db()
    assert getattr(lot, field) == before


def test_exactly_seven_day_inbound_with_zero_cost_is_recorded(owner, product):
    lot, movement = services.create_inbound(owner, inbound(product))
    assert lot.expiry_date - lot.received_date == timedelta(days=7)
    assert lot.total_cost == Decimal("0.00")
    assert lot.physical_qty == movement.lines.get().physical_delta == 500
    assert lot.offer.current_price == product.reference_price


@pytest.mark.parametrize("quantity", [True, False, "1.0", "-1", 9_000_000_000_000_000_001])
def test_inbound_rejects_non_integer_or_out_of_range_quantity_without_side_effects(owner, product, quantity):
    fails("INVALID_QUANTITY", services.create_inbound, owner, inbound(product, quantity=quantity))
    assert not Lot.objects.filter(product=product).exists()
    assert not InventoryMovement.objects.filter(store=owner.store).exists()


def test_inbound_duplicate_code_does_not_leave_orphan_movement_or_offer(owner, product):
    services.create_inbound(owner, inbound(product))
    fails("INVALID_DATA", services.create_inbound, owner, inbound(product))
    assert Lot.objects.filter(product=product).count() == 1
    assert InventoryMovement.objects.filter(store=owner.store).count() == 1
    assert MovementLine.objects.filter(lot__product=product).count() == 1


def test_sale_spanning_lots_rolls_back_if_combined_stock_is_short(owner, product, lot):
    later = Lot.objects.create(product=product, code="EDGE-02", received_date=lot.received_date,
                               expiry_date=lot.expiry_date + timedelta(days=1),
                               sales_close_at=lot.sales_close_at + timedelta(days=1),
                               total_cost=Decimal("5.00"), received_qty=500, physical_qty=500)
    fails("INSUFFICIENT_STOCK", services.sell_local, owner, sale(product, 2000))
    lot.refresh_from_db()
    later.refresh_from_db()
    assert (lot.physical_qty, later.physical_qty) == (1250, 500)
    assert InventoryMovement.objects.filter(kind="LOCAL_SALE").count() == 0


def test_sale_ignores_unsellable_remainder_and_uses_next_lot(owner, product, lot):
    lot.physical_qty = 249
    lot.save(update_fields=["physical_qty"])
    later = Lot.objects.create(product=product, code="EDGE-02", received_date=lot.received_date,
                               expiry_date=lot.expiry_date + timedelta(days=1),
                               sales_close_at=lot.sales_close_at + timedelta(days=1),
                               total_cost=Decimal("5.00"), received_qty=500, physical_qty=500)
    movement = services.sell_local(owner, sale(product, 250))
    lot.refresh_from_db()
    later.refresh_from_db()
    assert lot.physical_qty == 249 and later.physical_qty == 250
    assert list(movement.lines.values_list("lot_id", flat=True)) == [later.id]


def test_idempotency_key_cannot_be_reused_for_different_operation(owner, product, lot):
    idem = key()
    services.sell_local(owner, sale(product, 250, idem))
    fails("IDEMPOTENCY_CONFLICT", services.waste, owner,
          {"lot_id": str(lot.id), "quantity": 10, "reason": "Merma", "idempotency_key": idem})
    lot.refresh_from_db()
    assert lot.physical_qty == 1000 and InventoryMovement.objects.count() == 1


def test_retry_after_failed_sale_can_use_same_key(owner, product, lot):
    idem = key()
    fails("INSUFFICIENT_STOCK", services.sell_local, owner, sale(product, 1500, idem))
    movement = services.sell_local(owner, sale(product, 250, idem))
    assert movement.lines.get().physical_delta == -250
    assert InventoryMovement.objects.filter(idempotency_key=idem).count() == 1


def test_waste_conflicting_retry_does_not_decrement_twice(owner, lot):
    data = {"lot_id": str(lot.id), "quantity": 10, "reason": "Merma", "idempotency_key": key()}
    services.waste(owner, data)
    fails("IDEMPOTENCY_CONFLICT", services.waste, owner, {**data, "quantity": 11})
    lot.refresh_from_db()
    assert lot.physical_qty == 1240 and InventoryMovement.objects.count() == 1


def test_adjust_to_zero_and_restock_from_zero(owner, lot):
    services.adjust(owner, {"lot_id": str(lot.id), "delta": -1250, "reason": "Conteo",
                            "idempotency_key": key()})
    lot.refresh_from_db()
    assert lot.physical_qty == 0
    services.adjust(owner, {"lot_id": str(lot.id), "delta": 3, "reason": "Conteo",
                            "idempotency_key": key()})
    lot.refresh_from_db()
    assert lot.physical_qty == 3
    assert sum(MovementLine.objects.filter(lot=lot).values_list("physical_delta", flat=True)) == -1247


@pytest.mark.parametrize("disable", ["user", "store"])
def test_inactive_staff_or_store_cannot_sell(employee, product, lot, disable):
    target = employee if disable == "user" else employee.store
    if disable == "store":
        target.active = False
        target.save(update_fields=["active"])
    else:
        target.is_active = False
        target.save(update_fields=["is_active"])
    fails("AUTH_REQUIRED" if disable == "user" else "FORBIDDEN", services.sell_local,
          employee, sale(product, 250))
    lot.refresh_from_db()
    assert lot.physical_qty == 1250


def test_rejected_limit_preserves_active_version_and_price(owner, offer):
    old = services.set_offer_limit(owner, offer.id,
                                   {"max_discount_pct": "30", "minimum_price": "7.00", "below_cost_authorized": False})
    fails("LIMIT_ABOVE_CURRENT", services.set_offer_limit, owner, offer.id,
          {"max_discount_pct": "5", "minimum_price": "9.50", "below_cost_authorized": False})
    old.refresh_from_db()
    offer.refresh_from_db()
    assert old.ends_at is None and OfferLimit.objects.filter(offer=offer).count() == 1
    assert offer.current_price == Decimal("9.00")


def test_price_exactly_on_floor_succeeds_and_one_cent_below_rolls_back(owner, offer):
    services.set_offer_limit(owner, offer.id,
                             {"max_discount_pct": "30", "minimum_price": "7.00", "below_cost_authorized": False})
    services.change_price(owner, offer.id, {"new_price": "7.00", "reason": "Prueba de límite"})
    fails("BELOW_FLOOR", services.change_price, owner, offer.id,
          {"new_price": "6.99", "reason": "Prueba de límite"})
    offer.refresh_from_db()
    assert offer.current_price == Decimal("7.00") and PriceChange.objects.filter(offer=offer).count() == 1


def test_rejected_price_change_does_not_pause_automation(owner, offer):
    services.set_offer_limit(owner, offer.id,
                             {"max_discount_pct": "30", "minimum_price": "7.00", "below_cost_authorized": False})
    fails("INVALID_TEXT", services.change_price, owner, offer.id,
          {"new_price": "8.50", "reason": " "})
    offer.refresh_from_db()
    assert offer.current_price == Decimal("9.00") and not offer.automation_paused
    assert PriceChange.objects.filter(offer=offer).count() == 0

