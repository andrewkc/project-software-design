import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    InventoryMovement, Lot, MovementLine, Offer, OfferLimit, OrderLine,
    PaymentAttempt, PaymentEvent, PriceChange, Product, Reservation,
    StorePricingPolicy, User,
)


pytestmark = pytest.mark.django_db


def test_product_code_unique_within_store(product):
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(store=product.store, code=product.code, name="Otro", category="X",
                               unit="G", sale_step=100, reference_price=Decimal("1.00"), storage_conditions="X")


def test_same_code_different_store_allowed(product, other_store):
    copy = Product.objects.create(store=other_store, code=product.code, name="Otro", category="X",
                                  unit="G", sale_step=100, reference_price=Decimal("1.00"), storage_conditions="X")
    assert copy.id != product.id


@pytest.mark.parametrize("field,value", [("sale_step", 0), ("reference_price", Decimal("0")), ("reference_price", Decimal("-1"))])
def test_product_invalid_numeric_rejected_by_db(product, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(**{field: value})


def test_lot_code_unique_per_product(lot):
    lot.pk = uuid.uuid4()
    with pytest.raises(IntegrityError), transaction.atomic():
        lot.save(force_insert=True)


@pytest.mark.parametrize("field,value", [
    ("received_qty", 0), ("physical_qty", -1), ("reserved_qty", -1),
    ("reserved_qty", 1251), ("total_cost", Decimal("-0.01")),
])
def test_lot_invalid_numeric_rejected_by_db(lot, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        Lot.objects.filter(pk=lot.pk).update(**{field: value})


def test_lot_six_day_duration_rejected_by_model(lot):
    lot.received_date = lot.expiry_date - timedelta(days=6)
    with pytest.raises(ValidationError):
        lot.full_clean()


def test_lot_six_day_duration_rejected_by_db(lot):
    with pytest.raises(IntegrityError), transaction.atomic():
        Lot.objects.filter(pk=lot.pk).update(received_date=lot.expiry_date - timedelta(days=6))


def test_lot_exactly_seven_days_accepted(lot):
    lot.received_date = lot.expiry_date - timedelta(days=7)
    lot.full_clean()
    lot.save(update_fields=["received_date"])
    assert Lot.objects.get(pk=lot.pk).expiry_date - lot.received_date == timedelta(days=7)


def test_lot_close_cannot_be_on_expiry_day(lot):
    lot.sales_close_at = lot.sales_close_at + timedelta(days=1)
    with pytest.raises(ValidationError):
        lot.full_clean()


def test_two_lots_same_product_vary_quantity_and_expiry(lot):
    second = Lot.objects.create(product=lot.product, code="ALM-02", received_date=lot.received_date,
                                expiry_date=lot.expiry_date + timedelta(days=3), sales_close_at=lot.sales_close_at + timedelta(days=3),
                                total_cost=Decimal("20"), received_qty=500, physical_qty=500)
    assert second.received_qty != lot.received_qty
    assert second.expiry_date != lot.expiry_date


def test_available_quantity(lot):
    lot.reserved_qty = 250
    assert lot.available_qty == 1000


@pytest.mark.parametrize("field,value", [("current_price", Decimal("0")), ("current_price", Decimal("11.00")), ("original_price", Decimal("0")), ("version", 0)])
def test_offer_invalid_values_rejected_by_db(offer, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        Offer.objects.filter(pk=offer.pk).update(**{field: value})


def test_offer_only_once_per_lot(offer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Offer.objects.create(lot=offer.lot, original_price=Decimal("10"), current_price=Decimal("9"))


def test_order_only_customer(owner, store):
    from core.models import Order
    bad = Order(customer=owner, store=store, total=Decimal("10"), reservation_until=timezone.now(),
                idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    with pytest.raises(ValidationError):
        bad.full_clean()


def test_order_currency_pen_only(order):
    order.currency = "USD"
    with pytest.raises(ValidationError):
        order.full_clean()


def test_order_total_positive_db(order):
    with pytest.raises(IntegrityError), transaction.atomic():
        type(order).objects.filter(pk=order.pk).update(total=0)


def test_order_idempotency_unique(order, customer, store):
    from core.models import Order
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(customer=customer, store=store, total=Decimal("1"), reservation_until=timezone.now(),
                             idempotency_key=order.idempotency_key, request_hash="b" * 64)


def make_line(order, offer, qty=500, amount=Decimal("18.00")):
    return OrderLine(order=order, offer=offer, base_qty=qty, step_snapshot=250,
                     step_price_snapshot=Decimal("9.00"), amount=amount,
                     expiry_snapshot=offer.lot.expiry_date, offer_version=1)


def test_orderline_valid_steps(order, offer):
    line = make_line(order, offer)
    line.full_clean()
    line.save()
    assert line.base_qty == 500


@pytest.mark.parametrize("qty", [13, 300, 0])
def test_orderline_bad_steps_rejected(order, offer, qty):
    line = make_line(order, offer, qty=qty)
    with pytest.raises(ValidationError):
        line.full_clean()


def test_orderline_wrong_amount_rejected(order, offer):
    with pytest.raises(ValidationError):
        make_line(order, offer, amount=Decimal("17.99")).full_clean()


def test_orderline_other_store_rejected(order, other_store, lot):
    other_product = Product.objects.create(store=other_store, code="ALM", name="Otro", category="X", unit="G",
                                           sale_step=250, reference_price=Decimal("9"), storage_conditions="X")
    other_lot = Lot.objects.create(product=other_product, code="B", received_date=lot.received_date,
                                   expiry_date=lot.expiry_date, sales_close_at=lot.sales_close_at,
                                   total_cost=Decimal("5"), received_qty=1000, physical_qty=1000)
    other_offer = Offer.objects.create(lot=other_lot, original_price=Decimal("9"), current_price=Decimal("9"))
    with pytest.raises(ValidationError):
        make_line(order, other_offer).full_clean()


def test_reservation_must_match_line_quantity(order, offer):
    line = make_line(order, offer)
    line.save()
    reservation = Reservation(line=line, lot=offer.lot, base_qty=250, expires_at=timezone.now())
    with pytest.raises(ValidationError):
        reservation.full_clean()


def test_reservation_must_match_lot(order, offer, lot):
    line = make_line(order, offer)
    line.save()
    other_lot = Lot.objects.create(product=lot.product, code="OTHER", received_date=lot.received_date,
                                   expiry_date=lot.expiry_date, sales_close_at=lot.sales_close_at,
                                   total_cost=Decimal("5"), received_qty=500, physical_qty=500)
    with pytest.raises(ValidationError):
        Reservation(line=line, lot=other_lot, base_qty=500, expires_at=timezone.now()).full_clean()


def test_payment_amount_must_match_order(order):
    attempt = PaymentAttempt(order=order, amount=Decimal("17"), currency="PEN", provider_key=uuid.uuid4())
    with pytest.raises(ValidationError):
        attempt.full_clean()


def test_payment_event_unique(order):
    attempt = PaymentAttempt.objects.create(order=order, amount=order.total, currency="PEN", provider_key=uuid.uuid4())
    PaymentEvent.objects.create(attempt=attempt, provider="MP", external_event_id="event-1", resource_id="order-1")
    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentEvent.objects.create(attempt=attempt, provider="MP", external_event_id="event-1", resource_id="order-1")


def test_movement_requires_reason_for_waste(owner, store):
    movement = InventoryMovement(store=store, actor=owner, kind=InventoryMovement.Kind.WASTE,
                                 idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    with pytest.raises(ValidationError):
        movement.full_clean()


def test_movement_actor_same_store(owner, other_store):
    movement = InventoryMovement(store=other_store, actor=owner, kind=InventoryMovement.Kind.INBOUND,
                                 idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    with pytest.raises(ValidationError):
        movement.full_clean()


def test_web_sale_requires_order(owner, store):
    movement = InventoryMovement(store=store, actor=owner, kind=InventoryMovement.Kind.WEB_SALE,
                                 idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    with pytest.raises(ValidationError):
        movement.full_clean()


@pytest.mark.parametrize("kind,delta", [("INBOUND", -1), ("LOCAL_SALE", 1), ("WASTE", 1)])
def test_movement_line_sign(owner, store, lot, kind, delta):
    movement = InventoryMovement.objects.create(store=store, actor=owner, kind=kind,
                                                reason="Merma" if kind == "WASTE" else "",
                                                idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    line = MovementLine(movement=movement, lot=lot, physical_delta=delta)
    with pytest.raises(ValidationError):
        line.full_clean()


def test_movement_line_zero_delta_db(owner, store, lot):
    movement = InventoryMovement.objects.create(store=store, actor=owner, kind="INBOUND",
                                                idempotency_key=uuid.uuid4(), request_hash="a" * 64)
    with pytest.raises(IntegrityError), transaction.atomic():
        MovementLine.objects.create(movement=movement, lot=lot, physical_delta=0)


def test_policy_only_owner(employee, store):
    policy = StorePricingPolicy(store=store, version=1, created_by=employee, starts_at=timezone.now())
    with pytest.raises(ValidationError):
        policy.full_clean()


def test_only_one_current_policy(owner, store):
    StorePricingPolicy.objects.create(store=store, version=1, created_by=owner, starts_at=timezone.now())
    with pytest.raises(IntegrityError), transaction.atomic():
        StorePricingPolicy.objects.create(store=store, version=2, created_by=owner, starts_at=timezone.now())


def test_offer_limit_only_owner(employee, offer):
    limit = OfferLimit(offer=offer, version=1, max_discount_pct=Decimal("30"), minimum_price=Decimal("7"),
                       authorized_by=employee, starts_at=timezone.now())
    with pytest.raises(ValidationError):
        limit.full_clean()


@pytest.mark.parametrize("field,value", [("max_discount_pct", Decimal("100")), ("max_discount_pct", Decimal("-1")), ("minimum_price", Decimal("0"))])
def test_offer_limit_bounds_db(owner, offer, field, value):
    limit = OfferLimit.objects.create(offer=offer, version=1, max_discount_pct=Decimal("30"),
                                      minimum_price=Decimal("7"), authorized_by=owner, starts_at=timezone.now())
    with pytest.raises(IntegrityError), transaction.atomic():
        OfferLimit.objects.filter(pk=limit.pk).update(**{field: value})


def test_price_change_cannot_raise(owner, offer):
    with pytest.raises(IntegrityError), transaction.atomic():
        PriceChange.objects.create(offer=offer, old_price=Decimal("9"), new_price=Decimal("10"),
                                   origin="MANUAL", actor=owner, reason="bad", limit_version=1)
