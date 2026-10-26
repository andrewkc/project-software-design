import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.db import close_old_connections
from django.utils import timezone

from core import services
from core.models import InventoryMovement, Lot, MovementLine, Offer, OfferLimit, PriceChange, Product, User


pytestmark = pytest.mark.django_db


def key():
    return str(uuid.uuid4())


def inbound_data(product, **changes):
    today = timezone.localdate()
    data = {"product_id": str(product.id), "code": "NEW-01", "received_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=10)).isoformat(), "quantity": 750,
            "total_cost": "15.00", "idempotency_key": key()}
    data.update(changes)
    return data


def sale_data(product, qty=250, **changes):
    data = {"product_id": str(product.id), "quantity": qty, "idempotency_key": key()}
    data.update(changes)
    return data


def change_data(lot, **changes):
    data = {"lot_id": str(lot.id), "quantity": 100, "reason": "Deterioro confirmado", "idempotency_key": key()}
    data.update(changes)
    return data


def assert_error(code, function, *args):
    with pytest.raises(services.DomainError) as error:
        function(*args)
    assert error.value.code == code


def test_create_product_owner(owner):
    product = services.create_product(owner, {"code": "NEW", "name": "Producto", "category": "Fruta", "unit": "G",
                                               "sale_step": 250, "reference_price": "4.50", "storage_conditions": "Frío"})
    assert product.store_id == owner.store_id and product.reference_price == Decimal("4.50")


@pytest.mark.parametrize("role", [User.Role.EMPLOYEE, User.Role.CUSTOMER, User.Role.ADMIN])
def test_create_product_forbidden_for_other_roles(owner, employee, customer, role):
    actor = employee if role == User.Role.EMPLOYEE else customer
    if role == User.Role.ADMIN:
        actor = User.objects.create_user(email="admin2@example.test", password="SecurePass123!", name="Admin", role=role)
    assert_error("FORBIDDEN", services.create_product, actor,
                 {"code": "NEW", "name": "P", "category": "X", "unit": "G", "sale_step": 1,
                  "reference_price": "1.00", "storage_conditions": "X"})


@pytest.mark.parametrize("field,value,code", [
    ("unit", "KG", "INVALID_UNIT"), ("sale_step", 0, "INVALID_QUANTITY"),
    ("sale_step", "1.5", "INVALID_QUANTITY"), ("reference_price", "NaN", "INVALID_MONEY"),
    ("reference_price", "2.999", "INVALID_MONEY"), ("name", "", "INVALID_TEXT"),
])
def test_create_product_rejects_bad_input(owner, field, value, code):
    data = {"code": "NEW", "name": "P", "category": "X", "unit": "G", "sale_step": 1,
            "reference_price": "1.00", "storage_conditions": "X"}
    data[field] = value
    assert_error(code, services.create_product, owner, data)


def test_inbound_creates_lot_movement_and_draft_offer(owner, product):
    lot, movement = services.create_inbound(owner, inbound_data(product))
    assert lot.physical_qty == lot.received_qty == 750 and lot.reserved_qty == 0
    assert movement.kind == InventoryMovement.Kind.INBOUND
    assert movement.lines.get().physical_delta == 750
    assert lot.offer.state == Offer.State.DRAFT


def test_inbound_idempotent(owner, product):
    data = inbound_data(product)
    first = services.create_inbound(owner, data)
    second = services.create_inbound(owner, data)
    assert first[0].id == second[0].id and first[1].id == second[1].id
    assert Lot.objects.filter(product=product).count() == 1


def test_inbound_same_key_different_body_rejected(owner, product):
    data = inbound_data(product)
    services.create_inbound(owner, data)
    assert_error("IDEMPOTENCY_CONFLICT", services.create_inbound, owner, {**data, "quantity": 500})


def test_inbound_cross_store_rejected(owner, other_store):
    other = Product.objects.create(store=other_store, code="B", name="B", category="X", unit="G",
                                   sale_step=100, reference_price=Decimal("2"), storage_conditions="X")
    assert_error("NOT_FOUND", services.create_inbound, owner, inbound_data(other))


def test_employee_cannot_receive(employee, product):
    assert_error("FORBIDDEN", services.create_inbound, employee, inbound_data(product))


@pytest.mark.parametrize("changes,code", [
    ({"quantity": 0}, "INVALID_QUANTITY"), ({"quantity": -1}, "INVALID_QUANTITY"),
    ({"total_cost": "-1"}, "INVALID_MONEY"), ({"expiry_date": "nonsense"}, "INVALID_DATE"),
])
def test_inbound_bad_values_do_not_create_lot(owner, product, changes, code):
    assert_error(code, services.create_inbound, owner, inbound_data(product, **changes))
    assert not Lot.objects.filter(product=product).exists()


def test_inbound_six_day_duration_rejected(owner, product):
    today = timezone.localdate()
    assert_error("SHORT_LIFETIME", services.create_inbound, owner,
                 inbound_data(product, expiry_date=(today + timedelta(days=6)).isoformat()))


def test_inbound_duplicate_code_rolls_back(owner, product):
    services.create_inbound(owner, inbound_data(product))
    assert_error("INVALID_DATA", services.create_inbound, owner, inbound_data(product))
    assert InventoryMovement.objects.filter(kind="INBOUND", store=owner.store).count() == 1


def test_sale_employee_decrements_lot(employee, product, lot):
    movement = services.sell_local(employee, sale_data(product, 500))
    lot.refresh_from_db()
    assert lot.physical_qty == 750 and movement.lines.get().physical_delta == -500
    assert services.movement_result(movement)["total"] == "20.00"


def test_sale_uses_published_price(employee, product, lot, offer):
    movement = services.sell_local(employee, sale_data(product, 250))
    assert movement.lines.get().step_price_snapshot == Decimal("9.00")
    assert movement.lines.get().amount == Decimal("9.00")


def test_sale_allocates_earliest_lot_first(owner, product, lot):
    later = Lot.objects.create(product=product, code="LATER", received_date=lot.received_date,
                               expiry_date=lot.expiry_date + timedelta(days=5), sales_close_at=lot.sales_close_at + timedelta(days=5),
                               total_cost=Decimal("50"), received_qty=500, physical_qty=500)
    movement = services.sell_local(owner, sale_data(product, 1500))
    lot.refresh_from_db()
    later.refresh_from_db()
    assert lot.physical_qty == 0 and later.physical_qty == 250
    assert list(movement.lines.order_by("lot__sales_close_at").values_list("physical_delta", flat=True)) == [-1250, -250]


def test_sale_preserves_each_lot_price_snapshot(owner, product, lot, offer):
    later = Lot.objects.create(product=product, code="LATER", received_date=lot.received_date,
                               expiry_date=lot.expiry_date + timedelta(days=5), sales_close_at=lot.sales_close_at + timedelta(days=5),
                               total_cost=Decimal("10"), received_qty=250, physical_qty=250)
    Offer.objects.create(lot=later, state=Offer.State.PUBLISHED,
                         original_price=Decimal("10"), current_price=Decimal("8"))
    movement = services.sell_local(owner, sale_data(product, 1500))
    amounts = list(movement.lines.order_by("lot__sales_close_at").values_list("amount", flat=True))
    assert amounts == [Decimal("45.00"), Decimal("8.00")]
    offer.current_price = Decimal("7.00")
    offer.save(update_fields=["current_price"])
    assert services.movement_result(movement)["total"] == "53.00"


def test_sale_insufficient_stock_rolls_back(employee, product, lot):
    assert_error("INSUFFICIENT_STOCK", services.sell_local, employee, sale_data(product, 1500))
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and not InventoryMovement.objects.filter(kind="LOCAL_SALE").exists()


@pytest.mark.parametrize("qty", [0, -250, 13, 300, 1.5])
def test_sale_invalid_quantity(employee, product, lot, qty):
    code = "INVALID_STEP" if qty in (13, 300) else "INVALID_QUANTITY"
    assert_error(code, services.sell_local, employee, sale_data(product, qty))


def test_sale_does_not_consume_reserved(employee, product, lot):
    lot.reserved_qty = 1000
    lot.save(update_fields=["reserved_qty"])
    assert_error("INSUFFICIENT_STOCK", services.sell_local, employee, sale_data(product, 500))
    assert services.sell_local(employee, sale_data(product, 250)).lines.get().physical_delta == -250
    lot.refresh_from_db()
    assert lot.physical_qty == lot.reserved_qty == 1000


def test_sale_skips_closed_lot(employee, product, lot):
    lot.sales_close_at = timezone.now() - timedelta(seconds=1)
    lot.save(update_fields=["sales_close_at"])
    assert_error("INSUFFICIENT_STOCK", services.sell_local, employee, sale_data(product, 250))


def test_sale_inactive_product_rejected(employee, product, lot):
    product.active = False
    product.save(update_fields=["active"])
    assert_error("INACTIVE_PRODUCT", services.sell_local, employee, sale_data(product, 250))


def test_sale_idempotent(employee, product, lot):
    data = sale_data(product, 250)
    first = services.sell_local(employee, data)
    second = services.sell_local(employee, data)
    lot.refresh_from_db()
    assert first.id == second.id and lot.physical_qty == 1000


def test_sale_idempotency_conflict(employee, product, lot):
    data = sale_data(product, 250)
    services.sell_local(employee, data)
    assert_error("IDEMPOTENCY_CONFLICT", services.sell_local, employee, {**data, "quantity": 500})


def test_waste_owner_decrements_arbitrary_quantity(owner, lot):
    movement = services.waste(owner, change_data(lot, quantity=13))
    lot.refresh_from_db()
    assert lot.physical_qty == 1237 and movement.lines.get().physical_delta == -13


def test_waste_employee_forbidden(employee, lot):
    assert_error("FORBIDDEN", services.waste, employee, change_data(lot))


def test_waste_requires_reason(owner, lot):
    assert_error("INVALID_TEXT", services.waste, owner, change_data(lot, reason=" "))


def test_waste_cannot_consume_reservation(owner, lot):
    lot.reserved_qty = 1200
    lot.save(update_fields=["reserved_qty"])
    assert_error("INSUFFICIENT_STOCK", services.waste, owner, change_data(lot, quantity=100))


def test_waste_idempotent(owner, lot):
    data = change_data(lot, quantity=100)
    first, second = services.waste(owner, data), services.waste(owner, data)
    lot.refresh_from_db()
    assert first.id == second.id and lot.physical_qty == 1150


@pytest.mark.parametrize("delta,expected", [(100, 1350), (-100, 1150)])
def test_adjust_positive_and_negative(owner, lot, delta, expected):
    movement = services.adjust(owner, {"lot_id": str(lot.id), "delta": delta,
                                        "reason": "Conteo físico", "idempotency_key": key()})
    lot.refresh_from_db()
    assert lot.physical_qty == expected and movement.lines.get().physical_delta == delta


def test_adjust_zero_rejected(owner, lot):
    assert_error("INVALID_QUANTITY", services.adjust, owner,
                 {"lot_id": str(lot.id), "delta": 0, "reason": "Conteo", "idempotency_key": key()})


def test_adjust_cannot_drop_below_reserved(owner, lot):
    lot.reserved_qty = 1000
    lot.save(update_fields=["reserved_qty"])
    assert_error("INSUFFICIENT_STOCK", services.adjust, owner,
                 {"lot_id": str(lot.id), "delta": -251, "reason": "Conteo", "idempotency_key": key()})


def test_adjust_employee_forbidden(employee, lot):
    assert_error("FORBIDDEN", services.adjust, employee,
                 {"lot_id": str(lot.id), "delta": 10, "reason": "Conteo", "idempotency_key": key()})


def test_cross_store_lot_is_hidden(owner, other_store, lot):
    other_owner = User.objects.create_user(email="otherowner@example.test", password="SecurePass123!",
                                           name="Otro", role=User.Role.OWNER, store=other_store)
    assert_error("NOT_FOUND", services.waste, other_owner, change_data(lot))


def test_publish_and_pause_offer(owner, lot):
    offer = Offer.objects.create(lot=lot, original_price=Decimal("10"), current_price=Decimal("10"))
    published = services.publish_offer(owner, offer.id)
    assert published.state == Offer.State.PUBLISHED and published.version == 2
    paused = services.pause_offer(owner, offer.id)
    assert paused.state == Offer.State.PAUSED and paused.version == 3


def test_publish_closed_offer_rejected(owner, offer, lot):
    lot.sales_close_at = timezone.now() - timedelta(minutes=1)
    lot.save(update_fields=["sales_close_at"])
    assert_error("LOT_CLOSED", services.publish_offer, owner, offer.id)


def test_publish_without_step_rejected(owner, offer, lot):
    lot.physical_qty = 249
    lot.save(update_fields=["physical_qty"])
    offer.state = Offer.State.PAUSED
    offer.save(update_fields=["state"])
    assert_error("INSUFFICIENT_STOCK", services.publish_offer, owner, offer.id)


def test_employee_cannot_publish(employee, offer):
    assert_error("FORBIDDEN", services.publish_offer, employee, offer.id)


def test_offer_other_store_hidden(owner, other_store, offer):
    other_owner = User.objects.create_user(email="otherowner@example.test", password="SecurePass123!",
                                           name="Otro", role=User.Role.OWNER, store=other_store)
    assert_error("NOT_FOUND", services.publish_offer, other_owner, offer.id)


def test_limit_versioning_and_floor(owner, offer):
    first = services.set_offer_limit(owner, offer.id, {"max_discount_pct": "30", "minimum_price": "7.00", "below_cost_authorized": False})
    second = services.set_offer_limit(owner, offer.id, {"max_discount_pct": "20", "minimum_price": "8.00", "below_cost_authorized": False})
    first.refresh_from_db()
    assert first.ends_at is not None and second.version == 2 and services.price_floor(offer, second) == Decimal("8.00")


def test_limit_below_cost_requires_explicit_permission(owner, offer):
    assert_error("BELOW_COST_NEEDS_APPROVAL", services.set_offer_limit, owner, offer.id,
                 {"max_discount_pct": "60", "minimum_price": "3.00", "below_cost_authorized": False})
    limit = services.set_offer_limit(owner, offer.id,
                                     {"max_discount_pct": "60", "minimum_price": "3.00", "below_cost_authorized": True})
    assert limit.below_cost_authorized and services.price_floor(offer, limit) == Decimal("4.00")


@pytest.mark.parametrize("discount", ["-1", "100", "NaN", "10.999"])
def test_limit_bad_discount(owner, offer, discount):
    assert_error("INVALID_DISCOUNT", services.set_offer_limit, owner, offer.id,
                 {"max_discount_pct": discount, "minimum_price": "7", "below_cost_authorized": False})


def test_limit_employee_forbidden(employee, offer):
    assert_error("FORBIDDEN", services.set_offer_limit, employee, offer.id,
                 {"max_discount_pct": "30", "minimum_price": "7", "below_cost_authorized": False})


def test_manual_price_change_pauses_automation(owner, offer):
    services.set_offer_limit(owner, offer.id, {"max_discount_pct": "30", "minimum_price": "7", "below_cost_authorized": False})
    change = services.change_price(owner, offer.id, {"new_price": "8.50", "reason": "Oferta manual"})
    offer.refresh_from_db()
    assert change.old_price == Decimal("9.00") and change.new_price == Decimal("8.50")
    assert offer.current_price == Decimal("8.50") and offer.automation_paused and offer.version == 2


def test_manual_price_cannot_increase(owner, offer):
    services.set_offer_limit(owner, offer.id, {"max_discount_pct": "30", "minimum_price": "7", "below_cost_authorized": False})
    assert_error("PRICE_INCREASE", services.change_price, owner, offer.id,
                 {"new_price": "9.01", "reason": "bad"})


def test_manual_price_cannot_cross_floor(owner, offer):
    services.set_offer_limit(owner, offer.id, {"max_discount_pct": "30", "minimum_price": "7", "below_cost_authorized": False})
    assert_error("BELOW_FLOOR", services.change_price, owner, offer.id,
                 {"new_price": "6.99", "reason": "bad"})
    assert PriceChange.objects.count() == 0


def test_manual_price_requires_limit(owner, offer):
    assert_error("LIMIT_REQUIRED", services.change_price, owner, offer.id,
                 {"new_price": "8.00", "reason": "Oferta"})


def test_manual_price_employee_forbidden(employee, offer):
    assert_error("FORBIDDEN", services.change_price, employee, offer.id,
                 {"new_price": "8", "reason": "Oferta"})


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_sales_cannot_oversell():
    from core.models import Store
    store = Store.objects.create(name="Concurrente", address="Calle")
    employee = User.objects.create_user(email="thread@example.test", password="SecurePass123!", name="Empleado",
                                         role=User.Role.EMPLOYEE, store=store)
    product = Product.objects.create(store=store, code="ONE", name="Uno", category="X", unit="UNIT",
                                      sale_step=1, reference_price=Decimal("5"), storage_conditions="X")
    today = timezone.localdate()
    expiry = today + timedelta(days=8)
    lot = Lot.objects.create(product=product, code="ONE-01", received_date=today, expiry_date=expiry,
                              sales_close_at=datetime.combine(expiry - timedelta(days=1), time(23, 59, 59), ZoneInfo("America/Lima")),
                              total_cost=Decimal("2"), received_qty=1, physical_qty=1)

    def attempt(_):
        close_old_connections()
        try:
            return services.sell_local(employee, sale_data(product, 1)).id
        except services.DomainError as error:
            return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    lot.refresh_from_db()
    assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
    assert "INSUFFICIENT_STOCK" in outcomes
    assert lot.physical_qty == 0 and InventoryMovement.objects.filter(kind="LOCAL_SALE").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_retry_same_key_creates_one_sale():
    from core.models import Store
    store = Store.objects.create(name="Reintento", address="Calle")
    employee = User.objects.create_user(email="retry@example.test", password="SecurePass123!", name="Empleado",
                                         role=User.Role.EMPLOYEE, store=store)
    product = Product.objects.create(store=store, code="TWO", name="Dos", category="X", unit="UNIT",
                                      sale_step=1, reference_price=Decimal("5"), storage_conditions="X")
    today = timezone.localdate()
    expiry = today + timedelta(days=8)
    lot = Lot.objects.create(product=product, code="TWO-01", received_date=today, expiry_date=expiry,
                              sales_close_at=datetime.combine(expiry - timedelta(days=1), time(23, 59, 59), ZoneInfo("America/Lima")),
                              total_cost=Decimal("4"), received_qty=2, physical_qty=2)
    same_data = sale_data(product, 1)

    def attempt(_):
        close_old_connections()
        try:
            return services.sell_local(employee, same_data).id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    lot.refresh_from_db()
    assert outcomes[0] == outcomes[1]
    assert lot.physical_qty == 1 and InventoryMovement.objects.filter(kind="LOCAL_SALE").count() == 1
