"""Malformed inputs must not sell stock, create accounts or bypass checkout checks."""

import json
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from core import commerce, payments, services
from core.models import InventoryMovement, Order, PaymentAttempt, User


pytestmark = pytest.mark.django_db


def order_data(offer, quantity=250, key=None):
    return {"idempotency_key": key or str(uuid.uuid4()),
            "lines": [{"offer_id": str(offer.id), "base_quantity": quantity}]}


def payment_result(order, **changes):
    result = {"id": "ORDTST123456", "external_reference": str(order.id),
              "total_amount": str(order.total), "currency": "PEN",
              "total_paid_amount": str(order.total), "status": "processed",
              "status_detail": "accredited", "user_id": "demo-seller",
              "integration_data": {"application_id": "demo-app"},
              "checkout_url": "https://www.mercadopago.com.pe/checkout/v1/redirect?order_id=ORDTST123456"}
    result.update(changes)
    return result


BAD_QUANTITIES = [
    None, "", " ", "abc", "dos", "2e2", "-250", "-1", "0", 0,
    0.0, 0.5, 250.5, True, False, [], {}, [250], {"qty": 250}, "∞",
    "NaN", "1_000", "0250.0", " 250 ", 9_000_000_000_000_000_001,
]


@pytest.mark.parametrize("quantity", BAD_QUANTITIES, ids=lambda value: repr(value)[:40])
def test_bad_order_quantity_never_reserves_or_creates_order(customer, offer, lot, quantity):
    with pytest.raises(services.DomainError):
        commerce.create_order(customer, order_data(offer, quantity))
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0
    assert not Order.objects.exists()


BAD_LINES = [
    None, [], {}, "", "lines", 0, True, [None], [""], [[]], [{}],
    [{"offer_id": "", "base_quantity": 250}],
    [{"offer_id": str(uuid.uuid4()), "base_quantity": 250}],
    [1, 2], [{"offer_id": None, "base_quantity": 250}],
    tuple([{"offer_id": str(uuid.uuid4()), "base_quantity": 250}]),
]


@pytest.mark.parametrize("lines", BAD_LINES, ids=lambda value: repr(value)[:45])
def test_bad_order_lines_leave_stock_untouched(customer, offer, lot, lines):
    with pytest.raises(services.DomainError):
        commerce.create_order(customer, {"idempotency_key": str(uuid.uuid4()),
                                         "lines": lines})
    lot.refresh_from_db()
    assert lot.reserved_qty == 0 and lot.physical_qty == 1250
    assert not Order.objects.exists()


BAD_KEYS = [None, "", " ", "not-a-uuid", 0, 1, True, [], {},
            "00000000-0000-0000-0000-00000000000z"]


@pytest.mark.parametrize("key", BAD_KEYS, ids=lambda value: repr(value)[:40])
def test_bad_order_key_never_creates_reservation(customer, offer, lot, key):
    with pytest.raises(services.DomainError):
        commerce.create_order(customer, order_data(offer, key=key) if key else
                              {"idempotency_key": key, "lines": order_data(offer)["lines"]})
    lot.refresh_from_db()
    assert lot.reserved_qty == 0 and not Order.objects.exists()


CHECKOUT_CHANGES = [
    {"id": None}, {"id": ""}, {"id": "ORDLIVE123"},
    {"external_reference": None}, {"external_reference": "different-order"},
    {"total_amount": None}, {"total_amount": "0"},
    {"total_amount": "NaN"}, {"total_amount": "Infinity"},
    {"total_amount": "999999.99"}, {"currency": None}, {"currency": "USD"},
    {"checkout_url": None}, {"checkout_url": ""},
    {"checkout_url": "http://mercadopago.com.pe/pay"},
    {"checkout_url": "https://mercadopago.com.pe.evil.test/pay"},
    {"checkout_url": "https://[::1"},
    {"integration_data": []},
]


@pytest.mark.parametrize("changes", CHECKOUT_CHANGES, ids=lambda value: repr(value)[:60])
def test_bad_checkout_response_never_creates_sale(customer, offer, lot, settings, changes):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = commerce.create_order(customer, order_data(offer, 500))
    with patch.object(payments, "_request", return_value=payment_result(order, **changes)):
        with pytest.raises(services.DomainError):
            payments.begin_checkout(customer, order.id)
    lot.refresh_from_db()
    attempt = PaymentAttempt.objects.get(order=order)
    assert attempt.state == PaymentAttempt.State.CREATED
    assert not attempt.response_summary
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)
    assert not InventoryMovement.objects.filter(order=order).exists()


VERIFY_CHANGES = [
    {"id": None}, {"id": "ORDLIVE999"},
    {"external_reference": None}, {"external_reference": "wrong"},
    {"total_amount": None}, {"total_amount": "0"},
    {"total_amount": "Infinity"}, {"currency": None}, {"currency": "USD"},
    {"total_paid_amount": None}, {"total_paid_amount": "0"},
    {"total_paid_amount": "NaN"}, {"total_paid_amount": "Infinity"},
    {"user_id": "different-seller"}, {"integration_data": []},
    {"integration_data": None},
]


@pytest.mark.parametrize("changes", VERIFY_CHANGES, ids=lambda value: repr(value)[:60])
def test_bad_payment_verification_never_consumes_stock(customer, offer, lot, settings, changes):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = commerce.create_order(customer, order_data(offer, 500))
    with patch.object(payments, "_request", return_value=payment_result(order)):
        payments.begin_checkout(customer, order.id)
    with patch.object(payments, "_request", return_value=payment_result(order, **changes)):
        with pytest.raises(services.DomainError):
            payments.verify_checkout(customer, order.id)
    lot.refresh_from_db()
    order.refresh_from_db()
    assert order.state == Order.State.PENDING
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)
    assert not InventoryMovement.objects.filter(order=order).exists()


BAD_SALE_QUANTITIES = [None, "", " ", "abc", "1e3", "-250", "0", 0,
                       0.0, 0.25, 250.5, True, False, [], {}, [250],
                       "NaN", 9_000_000_000_000_000_001]


@pytest.mark.parametrize("quantity", BAD_SALE_QUANTITIES, ids=lambda value: repr(value)[:40])
def test_bad_local_sale_does_not_move_inventory(employee, product, lot, quantity):
    with pytest.raises(services.DomainError):
        services.sell_local(employee, {"product_id": str(product.id),
            "quantity": quantity, "idempotency_key": str(uuid.uuid4())})
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0
    assert not InventoryMovement.objects.exists()


BAD_DECISIONS = [None, "", "approve", "APPROVED", "YES", 1, True, [], {}, "REJECTED"]


@pytest.mark.parametrize("decision", BAD_DECISIONS, ids=lambda value: repr(value)[:40])
def test_random_payment_decision_cannot_change_order(customer, offer, lot, decision):
    order = commerce.create_order(customer, order_data(offer))
    with pytest.raises(services.DomainError):
        commerce.simulate_payment(customer, order.id, decision)
    lot.refresh_from_db()
    order.refresh_from_db()
    assert order.state == Order.State.PENDING
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 250)
    assert not PaymentAttempt.objects.filter(order=order).exists()


BAD_QUESTIONS = [None, "", " ", "\n\t", 1, 0, True, False, [], {}, ["ofertas"], "x" * 1001]


@pytest.mark.parametrize("question", BAD_QUESTIONS, ids=lambda value: repr(value)[:40])
def test_bad_chat_input_is_rejected_without_moving_stock(offer, lot, question):
    response = Client().post("/api/v1/chat", data=json.dumps({"question": question}),
                             content_type="application/json")
    assert response.status_code == 422
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0


BAD_REGISTRATIONS = [
    {"email": None}, {"email": ""}, {"email": "not-an-email"},
    {"email": "bad@"}, {"email": []}, {"name": None},
    {"name": ""}, {"name": " "}, {"name": 123},
    {"name": []}, {"password": None}, {"password": "123"},
]


@pytest.mark.parametrize("changes", BAD_REGISTRATIONS, ids=lambda value: repr(value)[:50])
def test_bad_registration_never_creates_account(db, changes):
    body = {"email": "attacker@example.test", "name": "Cliente",
            "password": "SecureDemoPassword123!"}
    body.update(changes)
    response = Client().post("/api/v1/auth/register", data=json.dumps(body),
                             content_type="application/json")
    assert 400 <= response.status_code < 500
    assert not User.objects.filter(email="attacker@example.test").exists()


TOP_LEVEL_CASES = [
    ("/api/v1/orders", [], "customer"),
    ("/api/v1/orders", "oops", "customer"),
    ("/api/v1/store/local-sales", [], "owner"),
    ("/api/v1/store/inbounds", [], "owner"),
    ("/api/v1/auth/register", [], None),
    ("/api/v1/auth/login", [], None),
    ("/api/v1/chat", [], None),
    ("/api/v1/store/analysis", [], "owner"),
    ("/api/v1/store/pricing-policy", [], "owner"),
]


@pytest.mark.parametrize("path,body,role", TOP_LEVEL_CASES)
def test_random_top_level_json_is_4xx_not_server_error(customer, owner, path, body, role):
    client = Client()
    if role == "customer":
        client.force_login(customer)
    elif role == "owner":
        client.force_login(owner)
    response = client.post(path, data=json.dumps(body), content_type="application/json")
    assert 400 <= response.status_code < 500


def secure_post(client, path, body, token):
    return client.post(path, data=json.dumps(body), content_type="application/json",
                       HTTP_X_CSRFTOKEN=token)


@pytest.mark.parametrize("quantity", [250, 500, 750, 1000, 1250])
def test_complete_http_checkout_approves_once_for_each_quantity(customer, offer, lot,
                                                                 settings, quantity):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    created = secure_post(client, "/api/v1/orders", order_data(offer, quantity), token)
    assert created.status_code == 201
    order = Order.objects.get(pk=created.json()["id"])
    assert order.total == quantity // 250 * offer.current_price
    with patch.object(payments, "_request", return_value=payment_result(order)):
        opened = secure_post(client, f"/api/v1/orders/{order.id}/checkout", {}, token)
    assert opened.status_code == 200
    assert opened.json()["checkout_url"].startswith("https://www.mercadopago.com.pe/")
    with patch.object(payments, "_request", return_value=payment_result(order)):
        paid = secure_post(client, f"/api/v1/orders/{order.id}/verify-payment", {}, token)
        again = secure_post(client, f"/api/v1/orders/{order.id}/verify-payment", {}, token)
    assert paid.status_code == again.status_code == 200
    assert paid.json()["state"] == again.json()["state"] == "PAID"
    assert client.get(f"/api/v1/orders/{order.id}").json()["state"] == "PAID"
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 - quantity and lot.reserved_qty == 0
    assert InventoryMovement.objects.filter(order=order).count() == 1


@pytest.mark.parametrize("quantity", [250, 500, 750, 1000, 1250])
def test_complete_http_rejection_releases_each_quantity(customer, offer, lot,
                                                        settings, quantity):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    created = secure_post(client, "/api/v1/orders", order_data(offer, quantity), token)
    order = Order.objects.get(pk=created.json()["id"])
    with patch.object(payments, "_request", return_value=payment_result(order)):
        assert secure_post(client, f"/api/v1/orders/{order.id}/checkout", {}, token).status_code == 200
    with patch.object(payments, "_request", return_value=payment_result(
            order, status="failed", status_detail="failed", total_paid_amount="0")):
        rejected = secure_post(client, f"/api/v1/orders/{order.id}/verify-payment", {}, token)
    assert rejected.status_code == 200 and rejected.json()["state"] == "FAILED"
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0
    assert not InventoryMovement.objects.filter(order=order).exists()


@pytest.mark.parametrize("quantity", [250, 500, 1250])
def test_late_approved_payment_does_not_sell_without_reservation(customer, offer, lot,
                                                                 settings, quantity):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    created = secure_post(client, "/api/v1/orders", order_data(offer, quantity), token)
    order = Order.objects.get(pk=created.json()["id"])
    with patch.object(payments, "_request", return_value=payment_result(order)):
        assert secure_post(client, f"/api/v1/orders/{order.id}/checkout", {}, token).status_code == 200
    Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
    with patch.object(payments, "_request", return_value=payment_result(order)):
        late = secure_post(client, f"/api/v1/orders/{order.id}/verify-payment", {}, token)
    assert late.status_code == 200 and late.json()["state"] == "PAYMENT_REVIEW"
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0
    assert not InventoryMovement.objects.filter(order=order).exists()
