"""Mercado Pago Checkout Pro Orders, test environment only."""

import json
import uuid
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import commerce, services
from .models import Order, PaymentAttempt

API_BASE = "https://api.mercadopago.com"
PROVIDER = "MERCADOPAGO_TEST"


def enabled():
    return bool(settings.MERCADOPAGO_ACCESS_TOKEN)


def _request(method, path, payload=None, key=None):
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise services.DomainError("PAYMENT_NOT_CONFIGURED", "Falta la credencial de prueba", 503)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if key:
        headers["X-Idempotency-Key"] = str(key)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urlopen(Request(API_BASE + path, data=body, headers=headers, method=method), timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise services.DomainError("PAYMENT_PROVIDER_UNAVAILABLE", "No se pudo consultar Mercado Pago", 503) from error
    if not isinstance(result, dict):
        raise services.DomainError("PAYMENT_PROVIDER_INVALID", "Respuesta de pago inválida", 503)
    return result


def _amount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _test_order(result, order, require_url=False):
    external_id = result.get("id")
    if not isinstance(external_id, str) or not external_id.startswith("ORDTST"):
        raise services.DomainError("PAYMENT_NOT_TEST", "La respuesta no corresponde a una order de prueba", 503)
    if result.get("external_reference") != str(order.id):
        raise services.DomainError("PAYMENT_MISMATCH", "Referencia de pago distinta", 409)
    if _amount(result.get("total_amount")) != order.total or result.get("currency") != "PEN":
        raise services.DomainError("PAYMENT_MISMATCH", "Importe o moneda distintos", 409)
    if require_url:
        url = result.get("checkout_url")
        parsed = urlparse(url) if isinstance(url, str) else None
        host = parsed.hostname if parsed else None
        if not parsed or parsed.scheme != "https" or not host or not (
            host == "mercadopago.com.pe" or host.endswith(".mercadopago.com.pe")
            or host == "mercadopago.com" or host.endswith(".mercadopago.com")
        ):
            raise services.DomainError("PAYMENT_PROVIDER_INVALID", "URL de pago inválida", 503)
    return external_id


def begin_checkout(actor, order_id):
    commerce.require_customer(actor)
    if not enabled():
        raise services.DomainError("PAYMENT_NOT_CONFIGURED", "Falta la credencial de prueba", 503)
    with transaction.atomic():
        order = commerce.get_order(actor, order_id)
        order = Order.objects.select_for_update().select_related("customer").get(pk=order.pk)
        if order.state != Order.State.PENDING or order.reservation_until <= timezone.now():
            raise services.DomainError("ORDER_FINALIZED", "El pedido ya no admite pago", 409)
        if order.payment_attempts.exclude(provider=PROVIDER).exists():
            raise services.DomainError("PAYMENT_ALREADY_STARTED", "El pedido ya tiene otro pago", 409)
        attempt = PaymentAttempt.objects.select_for_update().filter(order=order, provider=PROVIDER).first()
        if attempt and attempt.response_summary.get("checkout_url"):
            return {"order_id": str(order.id), "checkout_url": attempt.response_summary["checkout_url"]}
        if attempt is None:
            attempt = PaymentAttempt.objects.create(order=order, provider=PROVIDER, amount=order.total,
                currency=order.currency, external_reference=str(order.id), provider_key=uuid.uuid4())
        items = [{"title": line.offer.lot.product.name, "quantity": line.base_qty // line.step_snapshot,
                  "unit_price": str(line.step_price_snapshot)} for line in order.lines.select_related(
                      "offer__lot__product").order_by("id")]
        payload = {"type": "online", "processing_mode": "manual", "capture_mode": "automatic",
                   "total_amount": str(order.total), "external_reference": str(order.id),
                   "payer": {"email": order.customer.email}, "items": items}
    result = _request("POST", "/v1/orders", payload, attempt.provider_key)
    external_id = _test_order(result, order, require_url=True)
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.state != Order.State.PENDING or order.reservation_until <= timezone.now():
            raise services.DomainError("ORDER_FINALIZED", "La reserva ya venció", 409)
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.response_summary.get("provider_order_id") not in (None, external_id):
            raise services.DomainError("PAYMENT_MISMATCH", "Intento de pago inconsistente", 409)
        attempt.state = PaymentAttempt.State.PENDING
        attempt.response_summary = {"provider_order_id": external_id,
                                    "checkout_url": result["checkout_url"],
                                    "application_id": (result.get("integration_data") or {}).get("application_id"),
                                    "user_id": result.get("user_id")}
        attempt.save(update_fields=["state", "response_summary", "updated_at"])
    return {"order_id": str(order.id), "checkout_url": result["checkout_url"]}


def verify_checkout(actor, order_id):
    commerce.require_customer(actor)
    order = commerce.get_order(actor, order_id)
    attempt = order.payment_attempts.filter(provider=PROVIDER).first()
    if not attempt or not attempt.response_summary.get("provider_order_id"):
        raise services.DomainError("PAYMENT_NOT_STARTED", "Primero inicia el pago de prueba", 409)
    if order.state == Order.State.PAID:
        return order
    external_id = attempt.response_summary["provider_order_id"]
    result = _request("GET", "/v1/orders/" + external_id)
    if _test_order(result, order) != external_id:
        raise services.DomainError("PAYMENT_MISMATCH", "Order de pago distinta", 409)
    if (result.get("integration_data") or {}).get("application_id") != attempt.response_summary.get("application_id") or result.get("user_id") != attempt.response_summary.get("user_id"):
        raise services.DomainError("PAYMENT_MISMATCH", "Cuenta o aplicación de pago distinta", 409)
    if result.get("status") == "processed" and result.get("status_detail") == "accredited":
        if _amount(result.get("total_paid_amount")) != order.total:
            raise services.DomainError("PAYMENT_MISMATCH", "Pago acreditado por importe distinto", 409)
        return commerce.approve_external_payment(order.id, attempt.id)
    if result.get("status") in ("failed", "canceled", "cancelled", "expired"):
        return commerce.reject_external_payment(order.id, attempt.id)
    return commerce.get_order(actor, order.id)
