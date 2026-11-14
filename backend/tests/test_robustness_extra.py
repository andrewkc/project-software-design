import json
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from core import commerce, services
from core.models import InventoryMovement, Lot, Offer, Order, PaymentAttempt, Product, Store, User

pytestmark = pytest.mark.django_db


def valid(offer, quantity=250, key=None):
    return {"idempotency_key": key or str(uuid.uuid4()),
            "lines": [{"offer_id": str(offer.id), "base_quantity": quantity}]}


def rejects_without_changes(customer, offer, lot, data, code):
    with pytest.raises(services.DomainError) as exc:
        commerce.create_order(customer, data)
    assert exc.value.code == code
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 0)
    assert not Order.objects.exists()
    assert not PaymentAttempt.objects.exists()


@pytest.mark.parametrize("shape", ["empty", "missing", "object", "text", "number", "too_many"])
def test_invalid_order_envelope_cannot_reserve(customer, offer, lot, shape):
    lines = {"empty": [], "missing": None, "object": {}, "text": "one", "number": 0,
             "too_many": valid(offer)["lines"] * 21}[shape]
    rejects_without_changes(customer, offer, lot,
        {"idempotency_key": str(uuid.uuid4()), "lines": lines}, "INVALID_LINES")


@pytest.mark.parametrize("shape,code", [
    ("null", "INVALID_LINES"), ("empty", "INVALID_ID"),
    ("bad_offer", "INVALID_ID"), ("unknown_offer", "OFFER_UNAVAILABLE"),
    ("missing_qty", "INVALID_QUANTITY"), ("null_qty", "INVALID_QUANTITY"),
    ("bool_qty", "INVALID_QUANTITY"), ("decimal_text_qty", "INVALID_QUANTITY"),
])
def test_invalid_order_line_cannot_reserve(customer, offer, lot, shape, code):
    line = {"null": None, "empty": {},
        "bad_offer": {"offer_id": "not-a-uuid", "base_quantity": 250},
        "unknown_offer": {"offer_id": str(uuid.uuid4()), "base_quantity": 250},
        "missing_qty": {"offer_id": str(offer.id)},
        "null_qty": {"offer_id": str(offer.id), "base_quantity": None},
        "bool_qty": {"offer_id": str(offer.id), "base_quantity": True},
        "decimal_text_qty": {"offer_id": str(offer.id), "base_quantity": "250.0"}}[shape]
    rejects_without_changes(customer, offer, lot,
        {"idempotency_key": str(uuid.uuid4()), "lines": [line]}, code)


@pytest.mark.parametrize("quantity,code", [
    (0, "INVALID_QUANTITY"), (-1, "INVALID_QUANTITY"),
    (1, "INVALID_STEP"), (251, "INVALID_STEP"),
    (1500, "INSUFFICIENT_STOCK"), (9_000_000_000_000_000_001, "INVALID_QUANTITY"),
])
def test_bad_quantities_never_create_order(customer, offer, lot, quantity, code):
    rejects_without_changes(customer, offer, lot, valid(offer, quantity), code)


@pytest.mark.parametrize("key", [None, "", "not-a-uuid", True])
def test_invalid_idempotency_key_cannot_create_order(customer, offer, lot, key):
    data = valid(offer)
    data["idempotency_key"] = key
    rejects_without_changes(customer, offer, lot, data, "INVALID_ID")


@pytest.mark.parametrize("identity,code", [
    ("anonymous", "AUTH_REQUIRED"), ("owner", "FORBIDDEN"),
    ("employee", "FORBIDDEN"), ("inactive", "AUTH_REQUIRED"),
])
def test_only_active_customer_can_reserve(request, customer, owner, employee, offer, identity, code):
    if identity == "inactive":
        customer.is_active = False
        customer.save(update_fields=["is_active"])
        actor = customer
    else:
        actor = {"anonymous": None, "owner": owner, "employee": employee}[identity]
    with pytest.raises(services.DomainError) as exc:
        commerce.create_order(actor, valid(offer))
    assert exc.value.code == code
    assert not Order.objects.exists()


@pytest.mark.parametrize("change", ["paused", "lot_inactive", "product_inactive", "store_inactive", "closed"])
def test_unsellable_offer_never_enters_catalog(customer, offer, lot, product, store, change):
    if change == "paused":
        Offer.objects.filter(pk=offer.pk).update(state=Offer.State.PAUSED)
    elif change == "lot_inactive":
        Lot.objects.filter(pk=lot.pk).update(active=False)
    elif change == "product_inactive":
        Product.objects.filter(pk=product.pk).update(active=False)
    elif change == "store_inactive":
        Store.objects.filter(pk=store.pk).update(active=False)
    else:
        Lot.objects.filter(pk=lot.pk).update(sales_close_at=timezone.now() - timedelta(seconds=1))
    assert commerce.public_offers() == []
    with pytest.raises(services.DomainError) as exc:
        commerce.create_order(customer, valid(offer))
    assert exc.value.code == "OFFER_UNAVAILABLE"
    assert not Order.objects.exists()


@pytest.mark.parametrize("operation,quantity,code", [
    ("sale", 0, "INVALID_QUANTITY"), ("sale", 1, "INVALID_STEP"),
    ("sale", 1500, "INSUFFICIENT_STOCK"),
    ("waste", 0, "INVALID_QUANTITY"), ("waste", 1500, "INSUFFICIENT_STOCK"),
    ("adjust", 0, "INVALID_QUANTITY"), ("adjust", -1500, "INSUFFICIENT_STOCK"),
])
def test_invalid_stock_mutation_never_changes_lot(owner, employee, product, lot, operation, quantity, code):
    key = str(uuid.uuid4())
    if operation == "sale":
        action = lambda: services.sell_local(employee, {"idempotency_key": key,
            "product_id": str(product.id), "quantity": quantity})
    elif operation == "waste":
        action = lambda: services.waste(owner, {"idempotency_key": key,
            "lot_id": str(lot.id), "quantity": quantity, "reason": "prueba"})
    else:
        action = lambda: services.adjust(owner, {"idempotency_key": key,
            "lot_id": str(lot.id), "delta": quantity, "reason": "prueba"})
    with pytest.raises(services.DomainError) as exc:
        action()
    assert exc.value.code == code
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 0)
    assert not InventoryMovement.objects.exists()


@pytest.mark.parametrize("change,code", [
    ("short_life", "SHORT_LIFETIME"), ("zero_quantity", "INVALID_QUANTITY"),
    ("bad_date", "INVALID_DATE"),
])
def test_bad_inbound_does_not_create_lot(owner, product, change, code):
    today = timezone.localdate()
    data = {"idempotency_key": str(uuid.uuid4()), "product_id": str(product.id),
        "code": "BAD-INBOUND", "received_date": str(today),
        "expiry_date": str(today + timedelta(days=10)), "quantity": 250, "total_cost": "10.00"}
    if change == "short_life":
        data["expiry_date"] = str(today + timedelta(days=6))
    elif change == "zero_quantity":
        data["quantity"] = 0
    else:
        data["received_date"] = "13/11/2026"
    with pytest.raises(services.DomainError) as exc:
        services.create_inbound(owner, data)
    assert exc.value.code == code
    assert not Lot.objects.exists()
    assert not InventoryMovement.objects.exists()


def test_http_empty_order_is_rejected_without_side_effects(customer, offer, lot):
    client = Client()
    client.force_login(customer)
    response = client.post("/api/v1/orders", data=json.dumps({
        "idempotency_key": str(uuid.uuid4()), "lines": []}), content_type="application/json")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_LINES"
    lot.refresh_from_db()
    assert lot.reserved_qty == 0 and not Order.objects.exists()


def test_forged_browser_origin_cannot_create_order(customer, offer, lot):
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post("/api/v1/orders", data=json.dumps(valid(offer)),
        content_type="application/json", HTTP_ORIGIN="https://evil.example",
        HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 403
    lot.refresh_from_db()
    assert lot.reserved_qty == 0 and not Order.objects.exists()


def test_same_key_with_changed_quantity_does_not_double_reserve(customer, offer, lot):
    key = str(uuid.uuid4())
    commerce.create_order(customer, valid(offer, 250, key))
    with pytest.raises(services.DomainError) as exc:
        commerce.create_order(customer, valid(offer, 500, key))
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    lot.refresh_from_db()
    assert lot.reserved_qty == 250 and Order.objects.count() == 1


def test_another_customer_cannot_take_over_order_key(customer, offer, lot):
    other = User.objects.create_user(email="adversary@example.test", password="SecurePass123!",
                                     name="Adversary", role=User.Role.CUSTOMER)
    key = str(uuid.uuid4())
    commerce.create_order(customer, valid(offer, 250, key))
    with pytest.raises(services.DomainError) as exc:
        commerce.create_order(other, valid(offer, 250, key))
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    lot.refresh_from_db()
    assert lot.reserved_qty == 250 and Order.objects.count() == 1


def test_waste_cannot_consume_reserved_stock(customer, owner, offer, lot):
    commerce.create_order(customer, valid(offer, 1000))
    with pytest.raises(services.DomainError) as exc:
        services.waste(owner, {"idempotency_key": str(uuid.uuid4()),
            "lot_id": str(lot.id), "quantity": 500, "reason": "prueba"})
    assert exc.value.code == "INSUFFICIENT_STOCK"
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 1000)
    assert not InventoryMovement.objects.exists()


def test_order_response_never_exposes_payment_token(customer, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "secret-marker-for-test"
    order = commerce.create_order(customer, valid(offer))
    payload = commerce.order_payload(order)
    assert payload["payment_mode"] == "MERCADOPAGO_TEST"
    assert payload["payment_started"] is False
    assert "secret-marker-for-test" not in json.dumps(payload)
