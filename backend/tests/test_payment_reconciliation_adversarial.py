"""Adversarial checks for signed test webhooks and background reconciliation."""

import hashlib
import hmac
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core import commerce, payments, services
from core.models import InventoryMovement, Job, Order, PaymentAttempt, PaymentEvent

pytestmark = pytest.mark.django_db
SECRET = "test-signature-secret"
EXTERNAL = "ORDTST123"


@pytest.fixture
def payment_case(customer, offer, lot, settings):
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
    settings.MERCADOPAGO_WEBHOOK_SECRET = SECRET
    order = commerce.create_order(customer, {"idempotency_key": str(uuid.uuid4()),
        "lines": [{"offer_id": str(offer.id), "base_quantity": 500}]})
    attempt = PaymentAttempt.objects.create(order=order, provider=payments.PROVIDER,
        state=PaymentAttempt.State.PENDING, amount=order.total, currency="PEN",
        external_reference=str(order.id), provider_key=uuid.uuid4(),
        response_summary={"provider_order_id": EXTERNAL, "application_id": "app", "user_id": "seller"})
    return order, attempt, lot


def signed(data_id=EXTERNAL, request_id="request-123", ts="1770000000", digest=None):
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};".encode()
    signature = digest if digest is not None else hmac.new(SECRET.encode(), manifest, hashlib.sha256).hexdigest()
    return {"X-Request-Id": request_id, "X-Signature": f"ts={ts},v1={signature}"}


def payload(**changes):
    body = {"id": "event-123", "type": "order", "live_mode": False,
            "action": "order.processed", "data": {"id": EXTERNAL}}
    body.update(changes)
    return body


def provider(order, **changes):
    result = {"id": EXTERNAL, "external_reference": str(order.id), "total_amount": str(order.total),
              "currency": "PEN", "total_paid_amount": str(order.total), "status": "processed",
              "status_detail": "accredited", "integration_data": {"application_id": "app"},
              "user_id": "seller"}
    result.update(changes)
    return result


BAD_SIGNATURES = (
    [("ts", value) for value in ["", "a", "-1", "1.2", "1 2", "1;2", "x" * 17, "０", "1\n2", "1/2"]]
    + [("digest", value) for value in ["", "x", "0" * 63, "0" * 65, "g" * 64,
        "a" * 64, "f" * 64, "1" * 64, "2" * 64, "-" * 64]]
    + [("request_id", value) for value in ["", "x" * 151, None, 9, True]]
    + [("data_id", value) for value in ["", "ORDLIVE1", "/v1/orders/x", "ORDTST/1", "ORDTST" * 40]]
)


@pytest.mark.parametrize("field,value", BAD_SIGNATURES)
def test_invalid_signature_never_queues_payment(payment_case, field, value):
    settings = {"data_id": EXTERNAL, "request_id": "request-123", "ts": "1770000000"}
    if field == "digest":
        headers = signed(digest=value)
    else:
        settings[field] = value
        headers = signed(**settings)
    with pytest.raises(services.DomainError):
        payments.accept_webhook(payload(), headers, settings["data_id"])
    assert not PaymentEvent.objects.exists() and not Job.objects.exists()


BAD_BODIES = [
    None, [], "order", 42, {}, {"id": "event-123"},
    payload(type="payment"), payload(type="ORDER"), payload(type=""), payload(type=None),
    payload(live_mode=True), payload(live_mode=None), payload(live_mode=0),
    payload(live_mode="false"), payload(live_mode=[]),
    payload(data=None), payload(data={}), payload(data=[]), payload(data="ORDTST123"),
    payload(data={"id": "ORDLIVE123"}), payload(data={"id": None}),
    payload(id=None), payload(id=""), payload(id=True), payload(id=[]),
    payload(id={}), payload(id="x" * 151),
]


@pytest.mark.parametrize("body", BAD_BODIES)
def test_signed_bad_body_cannot_queue_payment(payment_case, body):
    with pytest.raises(services.DomainError):
        payments.accept_webhook(body, signed(), EXTERNAL)
    assert not PaymentEvent.objects.exists() and not Job.objects.exists()


TAMPERED_PROVIDER = [
    {"id": "ORDLIVE123"}, {"id": "ORDTST/123"}, {"id": ""},
    {"external_reference": "another"}, {"external_reference": None},
    {"total_amount": "0"}, {"total_amount": "-1"}, {"total_amount": "nan"},
    {"total_amount": "1e100"}, {"currency": "USD"}, {"currency": None},
    {"total_paid_amount": "0"}, {"total_paid_amount": "1"},
    {"total_paid_amount": "NaN"}, {"integration_data": {}},
    {"integration_data": None}, {"integration_data": {"application_id": "other"}},
    {"user_id": "other"}, {"user_id": None}, {"user_id": ""},
    {"status": "failed"}, {"status": "canceled"}, {"status": "created"},
    {"status_detail": "pending"}, {"status_detail": "rejected"},
]


@pytest.mark.parametrize("changes", TAMPERED_PROVIDER)
def test_untrusted_provider_response_never_sells(payment_case, changes):
    order, attempt, lot = payment_case
    with patch.object(payments, "_request", return_value=provider(order, **changes)):
        try:
            payments.reconcile_attempt(attempt)
        except services.DomainError:
            pass
    lot.refresh_from_db()
    assert lot.physical_qty == 1250
    assert not InventoryMovement.objects.filter(order=order).exists()


@pytest.mark.parametrize("state", ["created", "pending", "processing", "in_process", "action_required",
    "canceling", "refunding", "unknown", "approved", "authorized", "partially_paid", "waiting",
    "disputed", "charged_back", "expired_pending"])
def test_worker_keeps_unapproved_stock_reserved(payment_case, state):
    order, _, lot = payment_case
    with patch.object(payments, "_request", return_value=provider(order, status=state, status_detail=state)):
        payments.run_reconciliation()
    order.refresh_from_db()
    lot.refresh_from_db()
    assert order.state == Order.State.PENDING
    assert lot.physical_qty == 1250 and lot.reserved_qty == 500


def test_valid_signed_event_is_idempotent_and_worker_sells_once(payment_case):
    order, _, lot = payment_case
    first = payments.accept_webhook(payload(), signed(), EXTERNAL)
    second = payments.accept_webhook(payload(), signed(), EXTERNAL)
    assert first == second == {"received": True}
    assert PaymentEvent.objects.count() == Job.objects.count() == 1
    with patch.object(payments, "_request", return_value=provider(order)):
        payments.run_reconciliation()
        payments.run_reconciliation()
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (750, 0)
    assert InventoryMovement.objects.filter(order=order).count() == 1
    assert PaymentEvent.objects.get().state == "PROCESSED"


def test_late_paid_after_expiry_goes_to_review_without_stock_sale(payment_case):
    order, _, lot = payment_case
    Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
    with patch.object(payments, "_request", return_value=provider(order)):
        payments.run_reconciliation()
    order.refresh_from_db()
    lot.refresh_from_db()
    assert order.state == Order.State.PAYMENT_REVIEW
    assert lot.physical_qty == 1250 and lot.reserved_qty == 0
    assert not InventoryMovement.objects.filter(order=order).exists()


def test_webhook_endpoint_rejects_unsigned_request(payment_case):
    response = APIClient().post("/api/v1/payments/webhook?data.id=ORDTST123", payload(), format="json")
    assert response.status_code == 401
    assert not Job.objects.exists()


def test_unknown_signed_order_does_not_touch_inventory(payment_case):
    order, _, lot = payment_case
    unknown = "ORDTST999"
    accepted = payments.accept_webhook(payload(data={"id": unknown}), signed(data_id=unknown), unknown)
    assert accepted["received"]
    assert not PaymentEvent.objects.exists()
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and order.state == Order.State.PENDING


def test_missing_secret_fails_closed(payment_case, settings):
    settings.MERCADOPAGO_WEBHOOK_SECRET = ""
    with pytest.raises(services.DomainError) as error:
        payments.accept_webhook(payload(), signed(), EXTERNAL)
    assert error.value.status == 503
    assert not Job.objects.exists()
