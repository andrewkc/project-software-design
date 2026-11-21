"""Mercado Pago Checkout Pro Orders, test environment only."""

import json
import hashlib
import hmac
import re
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import commerce, services
from .models import Job, Order, PaymentAttempt, PaymentEvent

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
    if not isinstance(result, dict):
        raise services.DomainError("PAYMENT_PROVIDER_INVALID", "Respuesta de pago inválida", 503)
    external_id = result.get("id")
    if not isinstance(external_id, str) or not external_id.startswith("ORDTST"):
        raise services.DomainError("PAYMENT_NOT_TEST", "La respuesta no corresponde a una order de prueba", 503)
    if result.get("external_reference") != str(order.id):
        raise services.DomainError("PAYMENT_MISMATCH", "Referencia de pago distinta", 409)
    if _amount(result.get("total_amount")) != order.total or result.get("currency") != "PEN":
        raise services.DomainError("PAYMENT_MISMATCH", "Importe o moneda distintos", 409)
    integration = result.get("integration_data")
    if (not isinstance(integration, dict) or
            not isinstance(integration.get("application_id"), str) or
            not integration["application_id"] or
            not isinstance(result.get("user_id"), str) or not result["user_id"]):
        raise services.DomainError("PAYMENT_PROVIDER_INVALID", "Identidad del proveedor inválida", 503)
    if require_url:
        url = result.get("checkout_url")
        try:
            parsed = urlparse(url) if isinstance(url, str) else None
            host = parsed.hostname if parsed else None
        except ValueError:
            parsed = host = None
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
    return reconcile_attempt(attempt)


def reconcile_attempt(attempt):
    """Read the provider's current state; never trust a browser return or webhook body."""
    order = attempt.order
    external_id = attempt.response_summary.get("provider_order_id")
    if not isinstance(external_id, str) or not re.fullmatch(r"ORDTST[A-Za-z0-9_-]{1,120}", external_id):
        raise services.DomainError("PAYMENT_PROVIDER_INVALID", "Identificador externo inválido", 503)
    if order.state == Order.State.PAID:
        return order
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
    order.refresh_from_db()
    return order


def _verified_webhook(headers, data_id):
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        raise services.DomainError("WEBHOOK_NOT_CONFIGURED", "Firma de notificaciones no configurada", 503)
    signature = headers.get("X-Signature", "")
    request_id = headers.get("X-Request-Id", "")
    if (not isinstance(data_id, str) or not re.fullmatch(r"ORDTST[A-Za-z0-9_-]{1,120}", data_id)
            or not isinstance(request_id, str) or not 1 <= len(request_id) <= 150):
        raise services.DomainError("INVALID_WEBHOOK", "Notificación inválida", 401)
    parts = dict(part.split("=", 1) for part in signature.split(",") if "=" in part)
    ts, digest = parts.get("ts", ""), parts.get("v1", "")
    if not re.fullmatch(r"[0-9]{1,16}", ts) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise services.DomainError("INVALID_WEBHOOK", "Firma inválida", 401)
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};".encode()
    expected = hmac.new(secret.encode(), manifest, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest.lower()):
        raise services.DomainError("INVALID_WEBHOOK", "Firma inválida", 401)


@transaction.atomic
def accept_webhook(data, headers, query_id):
    """Persist a signed test notification; the worker fetches the real order."""
    _verified_webhook(headers, query_id)
    if not isinstance(data, dict) or data.get("type") != "order" or data.get("live_mode") is not False:
        raise services.DomainError("INVALID_WEBHOOK", "Solo se aceptan orders de prueba", 400)
    nested = data.get("data")
    if not isinstance(nested, dict) or nested.get("id") != query_id:
        raise services.DomainError("INVALID_WEBHOOK", "Recurso de pago distinto", 400)
    event_id = data.get("id")
    if isinstance(event_id, bool) or not isinstance(event_id, (int, str)) or not 1 <= len(str(event_id)) <= 150:
        raise services.DomainError("INVALID_WEBHOOK", "ID de evento inválido", 400)
    attempt = PaymentAttempt.objects.filter(provider=PROVIDER,
        response_summary__provider_order_id=query_id).select_related("order").first()
    if not attempt:
        return {"received": True}
    event, created = PaymentEvent.objects.get_or_create(provider=PROVIDER,
        external_event_id=str(event_id), defaults={"attempt": attempt, "resource_id": query_id,
        "payload_summary": {"type": "order", "action": str(data.get("action", ""))[:80]}})
    if event.resource_id != query_id or event.attempt_id != attempt.id:
        raise services.DomainError("WEBHOOK_CONFLICT", "Evento asociado a otra order", 409)
    if created:
        Job.objects.create(kind="RECONCILE_PAYMENT", key=f"mp-event:{event.id}",
                           payload={"event_id": str(event.id)}, available_at=timezone.now())
    return {"received": True}


def run_reconciliation(limit=100):
    """Process signed events, then poll pending test orders and expire old reserves."""
    limit = max(1, min(int(limit), 100))
    now = timezone.now()
    due = Q(state="PENDING", available_at__lte=now) | Q(state="RUNNING", lease_until__lte=now)
    job_ids = list(Job.objects.filter(due, kind="RECONCILE_PAYMENT").order_by(
        "available_at", "id").values_list("id", flat=True)[:limit])
    processed = 0
    for job_id in job_ids:
        with transaction.atomic():
            job = Job.objects.select_for_update().filter(due, pk=job_id).first()
            if not job:
                continue
            job.state, job.attempts = "RUNNING", job.attempts + 1
            job.lease_until = timezone.now() + timedelta(minutes=2)
            job.save(update_fields=["state", "attempts", "lease_until", "updated_at"])
        event = PaymentEvent.objects.select_related("attempt__order").get(pk=job.payload["event_id"])
        try:
            reconcile_attempt(event.attempt)
        except services.DomainError as error:
            job.error_code = error.code
            job.state = "ERROR" if job.attempts >= 5 or error.code in ("PAYMENT_MISMATCH", "PAYMENT_PROVIDER_INVALID") else "PENDING"
            job.available_at = timezone.now() + timedelta(minutes=min(job.attempts, 5))
            event.error_code = error.code
            event.save(update_fields=["error_code", "updated_at"])
        else:
            event.state = "PROCESSED"
            event.save(update_fields=["state", "updated_at"])
            job.state = "DONE"
            processed += 1
        job.lease_until = None
        job.save(update_fields=["state", "error_code", "available_at", "lease_until", "updated_at"])
    # Orders with lost webhooks are still checked. The bounded pass avoids an
    # unbounded provider scan, and the provider state remains the only authority.
    attempts = PaymentAttempt.objects.select_related("order").filter(
        provider=PROVIDER, state__in=[PaymentAttempt.State.CREATED, PaymentAttempt.State.PENDING],
        order__state__in=[Order.State.PENDING, Order.State.EXPIRED]).order_by("created_at")[:limit]
    for attempt in attempts:
        if not attempt.response_summary.get("provider_order_id"):
            continue
        try:
            reconcile_attempt(attempt)
            processed += 1
        except services.DomainError:
            continue
    commerce.expire_due_orders(limit)
    return processed
