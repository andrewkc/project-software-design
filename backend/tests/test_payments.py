import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from core import commerce, payments, services
from core.models import InventoryMovement, Lot, Order, PaymentAttempt

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def sqlite_without_postgres_advisory_lock():
    from django.db import connection
    if connection.vendor == "sqlite":
        with patch.object(services, "_lock_idempotency_key"):
            yield
    else:
        yield


def create(customer, offer):
    return commerce.create_order(customer, {"idempotency_key": str(uuid.uuid4()),
        "lines": [{"offer_id": str(offer.id), "base_quantity": 500}]})


def provider_order(order, status="created", **changes):
    result = {"id": "ORDTST123", "external_reference": str(order.id),
        "total_amount": str(order.total), "currency": "PEN",
        "total_paid_amount": str(order.total) if status == "processed" else "0.00",
        "checkout_url": "https://www.mercadopago.com.pe/checkout/v1/redirect?order_id=ORDTST123",
        "status": status, "status_detail": "accredited" if status == "processed" else status,
        "integration_data": {"application_id": "demo-app"}, "user_id": "demo-seller"}
    result.update(changes)
    return result


def start(customer, offer):
    order = create(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order)):
        checkout = payments.begin_checkout(customer, order.id)
    assert checkout["checkout_url"].startswith("https://www.mercadopago.com.pe/")
    return order


def assert_error(code, action):
    with pytest.raises(services.DomainError) as exc:
        action()
    assert exc.value.code == code


def test_checkout_and_accredit_once(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order, "processed")):
        assert payments.verify_checkout(customer, order.id).state == Order.State.PAID
        assert payments.verify_checkout(customer, order.id).state == Order.State.PAID
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (750, 0)
    assert InventoryMovement.objects.filter(order=order).count() == 1
    assert PaymentAttempt.objects.get(order=order).state == PaymentAttempt.State.APPROVED


def test_pending_payment_keeps_stock_reserved(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order)):
        assert payments.verify_checkout(customer, order.id).state == Order.State.PENDING
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)


@pytest.mark.parametrize("changes", [
    {"external_reference": "another"}, {"total_amount": "1.00"},
    {"currency": "USD"}, {"total_paid_amount": "1.00"},
    {"id": "ORDLIVE123"}, {"integration_data": {"application_id": "other"}},
    {"user_id": "other"},
])
def test_tampered_provider_response_never_sells(customer, offer, lot, settings, changes):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order, "processed", **changes)):
        assert_error("PAYMENT_NOT_TEST" if changes.get("id") else "PAYMENT_MISMATCH",
                     lambda: payments.verify_checkout(customer, order.id))
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)
    assert not InventoryMovement.objects.filter(order=order).exists()


def test_rejected_payment_releases_reservation(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order, "failed")):
        assert payments.verify_checkout(customer, order.id).state == Order.State.FAILED
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 0)


def test_late_approval_needs_review_without_stock_decrement(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
    commerce.expire_order(order.id)
    with patch.object(payments, "_request", return_value=provider_order(order, "processed")):
        assert payments.verify_checkout(customer, order.id).state == Order.State.PAYMENT_REVIEW
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 0)
    assert not InventoryMovement.objects.filter(order=order).exists()


def test_other_customer_cannot_open_or_verify(customer, offer, settings):
    from core.models import User
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    other = User.objects.create_user(email="other-payment@example.test", password="SecurePass123!",
                                     name="Other", role=User.Role.CUSTOMER)
    assert_error("NOT_FOUND", lambda: payments.begin_checkout(other, order.id))
    assert_error("NOT_FOUND", lambda: payments.verify_checkout(other, order.id))


def test_simulation_cannot_override_started_checkout(customer, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    assert_error("PAYMENT_ALREADY_STARTED", lambda: commerce.simulate_payment(customer, order.id, "APPROVE"))


def test_checkout_retry_keeps_one_attempt(customer, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    with patch.object(payments, "_request") as request:
        payments.begin_checkout(customer, order.id)
    request.assert_not_called()
    assert PaymentAttempt.objects.filter(order=order).count() == 1


def test_local_simulation_still_approves_without_external_attempt(customer, offer, lot):
    order = create(customer, offer)
    assert commerce.simulate_payment(customer, order.id, "APPROVE").state == Order.State.PAID
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (750, 0)


def test_frontend_origin_can_log_in(customer):
    import json
    from django.test import Client
    client = Client(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post("/api/v1/auth/login",
        data=json.dumps({"email": customer.email, "password": "SecurePass123!"}),
        content_type="application/json", HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


@pytest.mark.parametrize("changes,code", [
    ({"id": "ORDLIVE123"}, "PAYMENT_NOT_TEST"),
    ({"checkout_url": "https://mercadopago.com.pe.evil.example/pay"}, "PAYMENT_PROVIDER_INVALID"),
    ({"external_reference": "another-order"}, "PAYMENT_MISMATCH"),
    ({"currency": "USD"}, "PAYMENT_MISMATCH"),
])
def test_checkout_rejects_unsafe_provider_creation(customer, offer, lot, settings, changes, code):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = create(customer, offer)
    with patch.object(payments, "_request", return_value=provider_order(order, **changes)):
        assert_error(code, lambda: payments.begin_checkout(customer, order.id))
    lot.refresh_from_db()
    attempt = PaymentAttempt.objects.get(order=order)
    assert attempt.state == PaymentAttempt.State.CREATED
    assert not attempt.response_summary
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)
    assert not InventoryMovement.objects.filter(order=order).exists()


def test_missing_token_creates_no_payment_attempt(customer, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = ""
    order = create(customer, offer)
    assert_error("PAYMENT_NOT_CONFIGURED", lambda: payments.begin_checkout(customer, order.id))
    assert not PaymentAttempt.objects.filter(order=order).exists()


def test_provider_outage_retry_reuses_idempotency_key(customer, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = create(customer, offer)
    keys = []
    def request(method, path, payload=None, key=None):
        keys.append(key)
        if len(keys) == 1:
            raise services.DomainError("PAYMENT_PROVIDER_UNAVAILABLE", "Unavailable", 503)
        return provider_order(order)
    with patch.object(payments, "_request", side_effect=request):
        assert_error("PAYMENT_PROVIDER_UNAVAILABLE", lambda: payments.begin_checkout(customer, order.id))
        payments.begin_checkout(customer, order.id)
    assert keys[0] == keys[1]
    assert PaymentAttempt.objects.filter(order=order).count() == 1


def test_verify_without_checkout_does_not_contact_provider(customer, offer):
    order = create(customer, offer)
    with patch.object(payments, "_request") as request:
        assert_error("PAYMENT_NOT_STARTED", lambda: payments.verify_checkout(customer, order.id))
    request.assert_not_called()


def test_store_owner_cannot_start_customer_payment(customer, owner, offer, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = create(customer, offer)
    assert_error("FORBIDDEN", lambda: payments.begin_checkout(owner, order.id))
    assert PaymentAttempt.objects.filter(order=order).count() == 0


def test_processed_without_accreditation_keeps_stock(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = start(customer, offer)
    response = provider_order(order, "processed", status_detail="partially_refunded")
    with patch.object(payments, "_request", return_value=response):
        assert payments.verify_checkout(customer, order.id).state == Order.State.PENDING
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 500)


def test_reservation_expiring_during_provider_request_never_exposes_checkout(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-placeholder"
    order = create(customer, offer)
    def expire(*args, **kwargs):
        Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
        return provider_order(order)
    with patch.object(payments, "_request", side_effect=expire):
        assert_error("ORDER_FINALIZED", lambda: payments.begin_checkout(customer, order.id))
    assert not PaymentAttempt.objects.get(order=order).response_summary
    commerce.expire_order(order.id)
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (1250, 0)
