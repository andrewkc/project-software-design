"""Public marketplace, customer accounts and reserved test purchases.

The browser never decides that a payment succeeded. Inventory changes only in
the transaction that verifies/records an approved payment, through the shared
``sales_service`` primitive also used by the /sales paid-purchase flow.
"""

import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
import psycopg
from fastapi import APIRouter, Body, Depends, Header, Query
from psycopg.rows import dict_row

from config import (
    ALLOW_SIMULATED_PAYMENT,
    DSN,
    MERCADOPAGO_ACCESS_TOKEN,
    MERCADOPAGO_WEBHOOK_SECRET,
)
from sales_service import approve_reserved_order, parsed_uuid, positive_int, release_expired
from security import create_token, fail, hash_password, identity_from_header, require, verify_password

router = APIRouter(prefix="/customer")
MP_API = "https://api.mercadopago.com"
RESERVATION_SECONDS = 600


def customer(who=Depends(identity_from_header)):
    if who.get("rol") != "cliente":
        fail(403, "Esta operación es para compradores")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT id FROM Cliente WHERE id = %s AND estado = 'activo'", (who["id"],)
        ).fetchone()
    if not row:
        fail(401, "La cuenta no está activa")
    return who


def _order(conn, order_id, customer_id, lock=False):
    suffix = " FOR UPDATE OF c" if lock else ""
    row = conn.execute("""SELECT c.*, b.nombre AS bodega_nombre, b.direccion AS bodega_direccion
                          FROM Compra c JOIN Bodega b ON b.id = c.id_bodega
                          WHERE c.id = %s AND c.id_cliente = %s""" + suffix,
                       (order_id, customer_id)).fetchone()
    if not row:
        fail(404, "Pedido no encontrado")
    return row


def _order_payload(conn, row):
    lines = conn.execute("""SELECT d.id_oferta, d.id_producto, p.nombre, p.icono,
                           d.cantidad, d.precio_unitario, d.subtotal
                           FROM DetalleCompra d JOIN Producto p ON p.id = d.id_producto
                           WHERE d.id_compra = %s ORDER BY d.id""", (row["id"],)).fetchall()
    payment = conn.execute(
        """SELECT estado, id_transaccion_externa FROM Pago
           WHERE id_compra = %s ORDER BY id DESC LIMIT 1""", (row["id"],)
    ).fetchone()
    return {
        "id": row["id"],
        "store_id": row["id_bodega"],
        "store_name": row["bodega_nombre"],
        "pickup_address": row["bodega_direccion"],
        "state": row["estado"],
        "total": str(row["total"]),
        "reservation_until": row["reserva_hasta"].isoformat() if row["reserva_hasta"] else None,
        "paid_at": row["fecha_pago"].isoformat() if row["fecha_pago"] else None,
        "payment_mode": "MERCADOPAGO_TEST" if MERCADOPAGO_ACCESS_TOKEN else "LOCAL_SIMULATION",
        "payment_started": bool(payment and payment["id_transaccion_externa"]),
        "lines": [
            {
                "offer_id": line["id_oferta"],
                "product_id": line["id_producto"],
                "product_name": line["nombre"],
                "icon": line["icono"],
                "quantity": line["cantidad"],
                "unit_price": str(line["precio_unitario"]),
                "amount": str(line["subtotal"]),
            }
            for line in lines
        ],
    }


@router.post("/auth/register")
def register(body: dict = Body(...)):
    require(body, "nombres", "apellidos", "correo", "password")
    email = str(body["correo"]).strip().lower()
    if len(str(body["password"])) < 8 or "@" not in email:
        fail(400, "Correo o contraseña inválidos (mínimo 8 caracteres)")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if conn.execute("SELECT 1 FROM Cliente WHERE lower(correo) = %s", (email,)).fetchone():
            fail(409, "Ya existe una cuenta con ese correo")
        row = conn.execute("""INSERT INTO Cliente(nombres, apellidos, correo, password)
                              VALUES (%s, %s, %s, %s) RETURNING id, nombres, apellidos, correo""",
                           (str(body["nombres"]).strip(), str(body["apellidos"]).strip(), email,
                            hash_password(str(body["password"])))).fetchone()
    return {"token": create_token(row["id"], "cliente"), "profile": row}


@router.post("/auth/login")
def login(body: dict = Body(...)):
    require(body, "correo", "password")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT * FROM Cliente WHERE lower(correo) = lower(%s)",
            (str(body["correo"]).strip(),),
        ).fetchone()
    if not row or not verify_password(str(body["password"]), row["password"]):
        fail(401, "Correo o contraseña incorrectos")
    if row["estado"] != "activo":
        fail(403, "La cuenta no está activa")
    return {
        "token": create_token(row["id"], "cliente"),
        "profile": {key: row[key] for key in ("id", "nombres", "apellidos", "correo", "telefono")},
    }


@router.get("/auth/me")
def me(who=Depends(customer)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return conn.execute(
            "SELECT id, nombres, apellidos, correo, telefono FROM Cliente WHERE id = %s",
            (who["id"],),
        ).fetchone()


@router.get("/stores")
def stores():
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, nombre, direccion FROM Bodega ORDER BY id").fetchall()


@router.get("/offers")
def offers(store_id: int | None = None):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        release_expired(conn)
        rows = conn.execute("""SELECT o.id, o.id_bodega AS store_id, b.nombre AS store_name,
                       b.direccion AS store_address, p.id AS product_id, p.nombre AS product_name,
                       p.categoria AS category, p.icono AS icon, p.unidad_medida AS unit,
                       pb.fecha_vencimiento AS expiry_date, pb.stock,
                       COALESCE(o.precio_original, pb.precio_venta) AS original_price,
                       o.precio_oferta AS current_price,
                       COALESCE((SELECT sum(r.cantidad) FROM ReservaCompra r
                         WHERE r.id_producto = p.id AND r.id_bodega = b.id AND r.estado = 'activa'), 0) AS reserved
                       FROM Oferta o JOIN Bodega b ON b.id = o.id_bodega
                       JOIN Producto p ON p.id = o.id_producto
                       JOIN ProductosBodega pb ON pb.id_producto = p.id AND pb.id_bodega = b.id
                       WHERE o.estado = 'activo' AND o.fecha_inicio <= now() AND o.fecha_fin > now()
                         AND pb.estado = 'activo' AND pb.fecha_vencimiento > CURRENT_DATE
                         AND o.precio_oferta > 0 AND (%s::int IS NULL OR b.id = %s)
                       ORDER BY pb.fecha_vencimiento, o.id""", (store_id, store_id)).fetchall()
    return [
        {
            "id": row["id"],
            "store_id": row["store_id"],
            "store_name": row["store_name"],
            "store_address": row["store_address"],
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "category": row["category"],
            "icon": row["icon"],
            "unit": row["unit"],
            "expiry_date": row["expiry_date"].isoformat(),
            "original_price": str(row["original_price"]),
            "current_price": str(row["current_price"]),
            "available": max(0, row["stock"] - row["reserved"]),
        }
        for row in rows if row["stock"] > row["reserved"]
    ]


@router.get("/orders")
def list_orders(who=Depends(customer)):
    """All customer orders, including pending and rejected ones.

    Hiding non-paid orders made it impossible to resume a reservation or to
    understand why stock did not change; every state is traceable here.
    """
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        release_expired(conn)
        rows = conn.execute("""SELECT c.*, b.nombre AS bodega_nombre, b.direccion AS bodega_direccion
                               FROM Compra c JOIN Bodega b ON b.id = c.id_bodega
                               WHERE c.id_cliente = %s
                               ORDER BY c.id DESC""", (who["id"],)).fetchall()
        return [_order_payload(conn, row) for row in rows]


@router.post("/orders")
def create_order(body: dict = Body(...), who=Depends(customer)):
    key = parsed_uuid(body.get("idempotency_key"))
    lines = body.get("lines")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 20:
        fail(400, "Agrega entre 1 y 20 productos")
    normalized = []
    seen = set()
    for item in lines:
        if not isinstance(item, dict):
            fail(400, "Producto inválido")
        offer_id = positive_int(item.get("offer_id"), "offer_id")
        quantity = positive_int(item.get("quantity"), "quantity")
        if offer_id in seen:
            fail(400, "No repitas una oferta")
        seen.add(offer_id)
        normalized.append((offer_id, quantity))
    normalized.sort()
    fingerprint = hashlib.sha256(
        json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        release_expired(conn)
        lock_id = int.from_bytes(hashlib.sha256(key.bytes).digest()[:8], "big", signed=True)
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))
        previous = conn.execute(
            "SELECT id, id_cliente, request_hash FROM Compra WHERE idempotency_key = %s", (key,)
        ).fetchone()
        if previous:
            if previous["id_cliente"] != who["id"] or previous["request_hash"] != fingerprint:
                fail(409, "Clave de pedido ya usada con otros datos")
            return _order_payload(conn, _order(conn, previous["id"], who["id"]))
        ids = [item[0] for item in normalized]
        rows = conn.execute("""SELECT o.id, o.id_bodega, o.id_producto, o.precio_oferta, o.estado,
                            o.fecha_inicio, o.fecha_fin, pb.stock, pb.estado AS stock_estado,
                            pb.fecha_vencimiento,
                            COALESCE((SELECT sum(r.cantidad) FROM ReservaCompra r
                              WHERE r.id_producto = o.id_producto AND r.id_bodega = o.id_bodega
                                AND r.estado = 'activa'), 0) AS reservado
                            FROM Oferta o JOIN ProductosBodega pb ON pb.id_producto = o.id_producto
                              AND pb.id_bodega = o.id_bodega
                            WHERE o.id = ANY(%s) ORDER BY o.id FOR UPDATE OF pb""", (ids,)).fetchall()
        found = {row["id"]: row for row in rows}
        if len(found) != len(ids) or len({row["id_bodega"] for row in rows}) != 1:
            fail(400, "El pedido debe contener ofertas de una sola bodega")
        clock = conn.execute(
            "SELECT now()::timestamp AS local_now, CURRENT_DATE AS local_date"
        ).fetchone()
        now = clock["local_now"]
        total = Decimal("0.00")
        deadline = datetime.now(timezone.utc).timestamp() + RESERVATION_SECONDS
        details = []
        requested_by_product = {}
        for offer_id, quantity in normalized:
            row = found[offer_id]
            product_key = (row["id_producto"], row["id_bodega"])
            requested_by_product[product_key] = requested_by_product.get(product_key, 0) + quantity
            if (row["estado"] != "activo" or row["stock_estado"] != "activo"
                    or row["fecha_inicio"] > now or row["fecha_fin"] <= now
                    or row["fecha_vencimiento"] is None
                    or row["fecha_vencimiento"] <= clock["local_date"]
                    or row["stock"] - row["reservado"] < requested_by_product[product_key]
                    or row["precio_oferta"] <= 0):
                fail(409, "Oferta sin disponibilidad suficiente")
            if requested_by_product[product_key] != quantity:
                fail(400, "Un producto solo puede aparecer una vez por pedido")
            total += row["precio_oferta"] * quantity
            details.append((row, quantity))
        if total <= 0:
            fail(400, "El importe debe ser positivo")
        order = conn.execute("""INSERT INTO Compra(id_cliente, id_bodega, total, estado,
                                                   reserva_hasta, idempotency_key, request_hash)
                                VALUES (%s, %s, %s, 'pendiente', to_timestamp(%s), %s, %s)
                                RETURNING id""",
                             (who["id"], rows[0]["id_bodega"], total, deadline,
                              key, fingerprint)).fetchone()
        for row, quantity in details:
            conn.execute("""INSERT INTO DetalleCompra(id_compra, id_producto, id_oferta,
                                                      cantidad, precio_unitario, subtotal)
                            VALUES (%s, %s, %s, %s, %s, %s)""",
                         (order["id"], row["id_producto"], row["id"], quantity,
                          row["precio_oferta"], row["precio_oferta"] * quantity))
            conn.execute("""INSERT INTO ReservaCompra(id_compra, id_producto, id_bodega, cantidad)
                            VALUES (%s, %s, %s, %s)""",
                         (order["id"], row["id_producto"], row["id_bodega"], quantity))
        return _order_payload(conn, _order(conn, order["id"], who["id"]))


@router.get("/orders/{order_id}")
def get_order(order_id: int, who=Depends(customer)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        release_expired(conn)
        return _order_payload(conn, _order(conn, order_id, who["id"]))


@router.post("/orders/{order_id}/simulate-payment")
def simulate_payment(order_id: int, who=Depends(customer)):
    if not ALLOW_SIMULATED_PAYMENT:
        fail(403, "Pago simulado desactivado")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        order = _order(conn, order_id, who["id"], lock=True)
        if conn.execute(
            """SELECT 1 FROM Pago WHERE id_compra = %s AND metodo_pago = 'MERCADOPAGO_TEST'""",
            (order_id,),
        ).fetchone():
            fail(409, "Este pedido ya inició un pago externo")
        approve_reserved_order(conn, order)
        conn.execute("""INSERT INTO Pago(id_compra, metodo_pago, monto, estado, fecha_pago)
                        SELECT %s, 'LOCAL_SIMULATION', %s, 'aprobado', now()
                        WHERE NOT EXISTS(SELECT 1 FROM Pago WHERE id_compra = %s)""",
                     (order_id, order["total"], order_id))
        return _order_payload(conn, _order(conn, order_id, who["id"]))


def _mp_request(method, path, payload=None, key=None):
    if not MERCADOPAGO_ACCESS_TOKEN:
        fail(503, "Mercado Pago de prueba no está configurado")
    headers = {"Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}", "Content-Type": "application/json"}
    if key:
        headers["X-Idempotency-Key"] = str(key)
    try:
        with httpx.Client(timeout=12) as client:
            response = client.request(method, MP_API + path, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError):
        fail(503, "No se pudo consultar Mercado Pago")
    if not isinstance(result, dict):
        fail(503, "Respuesta de pago inválida")
    return result


def _validate_mp(result, order, external_id=None):
    try:
        valid_amount = Decimal(str(result.get("total_amount"))) == order["total"]
    except (InvalidOperation, TypeError):
        valid_amount = False
    oid = result.get("id")
    integration = result.get("integration_data") or {}
    if (not isinstance(integration, dict) or not integration.get("application_id")
            or not result.get("user_id") or not isinstance(oid, str)
            or not re.fullmatch(r"ORDTST[A-Za-z0-9_-]{1,120}", oid)
            or (external_id and oid != external_id)
            or result.get("external_reference") != str(order["id"])
            or result.get("currency") != "PEN" or not valid_amount):
        fail(409, "La respuesta de pago no coincide con el pedido de prueba")
    return oid


@router.post("/orders/{order_id}/checkout")
def checkout(order_id: int, who=Depends(customer)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        order = _order(conn, order_id, who["id"], lock=True)
        deadline = order["reserva_hasta"]
        if deadline is None:
            fail(409, "La reserva ya no admite pago")
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if order["estado"] != "pendiente" or deadline <= datetime.now(timezone.utc):
            fail(409, "La reserva ya no admite pago")
        payment = conn.execute(
            "SELECT * FROM Pago WHERE id_compra = %s ORDER BY id DESC LIMIT 1 FOR UPDATE", (order_id,)
        ).fetchone()
        if payment and payment["metodo_pago"] != "MERCADOPAGO_TEST":
            fail(409, "El pedido ya tiene otro método de pago")
        if payment and payment["id_transaccion_externa"]:
            return {"checkout_url": payment["checkout_url"]}
        if not payment:
            payment = conn.execute("""INSERT INTO Pago(id_compra, metodo_pago, monto, estado, clave_proveedor)
                                      VALUES (%s, 'MERCADOPAGO_TEST', %s, 'pendiente', %s)
                                      RETURNING *""",
                                   (order_id, order["total"], uuid.uuid4())).fetchone()
        lines = conn.execute("""SELECT d.cantidad, d.precio_unitario, p.nombre FROM DetalleCompra d
                                JOIN Producto p ON p.id = d.id_producto WHERE d.id_compra = %s""",
                             (order_id,)).fetchall()
        customer_row = conn.execute(
            "SELECT correo FROM Cliente WHERE id = %s", (who["id"],)
        ).fetchone()
    payload = {
        "type": "online", "processing_mode": "manual", "capture_mode": "automatic",
        "total_amount": str(order["total"]), "external_reference": str(order_id),
        "payer": {"email": customer_row["correo"]},
        "items": [
            {"title": line["nombre"], "quantity": line["cantidad"],
             "unit_price": str(line["precio_unitario"])}
            for line in lines
        ],
    }
    result = _mp_request("POST", "/v1/orders", payload, payment["clave_proveedor"])
    external_id = _validate_mp(result, order)
    url = result.get("checkout_url")
    parsed = urlparse(url) if isinstance(url, str) else None
    host = parsed.hostname if parsed else None
    if not parsed or parsed.scheme != "https" or not host or not (
            host == "mercadopago.com.pe" or host.endswith(".mercadopago.com.pe")
            or host == "mercadopago.com" or host.endswith(".mercadopago.com")):
        fail(503, "URL de pago de prueba inválida")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        locked = _order(conn, order_id, who["id"], lock=True)
        deadline = locked["reserva_hasta"]
        if deadline is None:
            fail(409, "La reserva venció antes de abrir el pago")
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if locked["estado"] != "pendiente" or deadline <= datetime.now(timezone.utc):
            fail(409, "La reserva venció antes de abrir el pago")
        conn.execute("""UPDATE Pago SET id_transaccion_externa = %s, checkout_url = %s,
                        proveedor_app_id = %s, proveedor_user_id = %s WHERE id = %s""",
                     (external_id, url, str(result["integration_data"]["application_id"]),
                      str(result["user_id"]), payment["id"]))
    return {"checkout_url": url}


@router.post("/orders/{order_id}/verify-payment")
def verify_payment(order_id: int, who=Depends(customer)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        order = _order(conn, order_id, who["id"])
        payment = conn.execute("""SELECT * FROM Pago WHERE id_compra = %s
                                  AND metodo_pago = 'MERCADOPAGO_TEST'""", (order_id,)).fetchone()
        if not payment or not payment["id_transaccion_externa"]:
            fail(409, "Primero inicia el pago de prueba")
        if order["estado"] == "pagado":
            return _order_payload(conn, order)
    result = _mp_request("GET", "/v1/orders/" + payment["id_transaccion_externa"])
    _validate_mp(result, order, payment["id_transaccion_externa"])
    if (str(result["integration_data"]["application_id"]) != payment["proveedor_app_id"]
            or str(result["user_id"]) != payment["proveedor_user_id"]):
        fail(409, "La cuenta de pago no coincide con el intento inicial")
    if result.get("status") == "processed" and result.get("status_detail") == "accredited":
        try:
            amount_ok = Decimal(str(result.get("total_paid_amount"))) == order["total"]
        except (InvalidOperation, TypeError):
            amount_ok = False
        if not amount_ok:
            fail(409, "Importe acreditado distinto")
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            locked = _order(conn, order_id, who["id"], lock=True)
            if locked["estado"] != "pagado":
                reservations = conn.execute("""SELECT r.id_producto, r.id_bodega, r.cantidad, pb.stock
                    FROM ReservaCompra r JOIN ProductosBodega pb ON pb.id_producto = r.id_producto
                    AND pb.id_bodega = r.id_bodega WHERE r.id_compra = %s
                    ORDER BY r.id_producto FOR UPDATE OF pb""", (order_id,)).fetchall()
                deadline = locked["reserva_hasta"]
                if deadline is None:
                    deadline = datetime.min.replace(tzinfo=timezone.utc)
                elif deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if (locked["estado"] != "pendiente" or deadline <= datetime.now(timezone.utc)
                        or not reservations
                        or any(r["stock"] < r["cantidad"] or r["cantidad"] <= 0 for r in reservations)):
                    conn.execute(
                        "UPDATE ReservaCompra SET estado = 'liberada' WHERE id_compra = %s AND estado = 'activa'",
                        (order_id,),
                    )
                    conn.execute(
                        "UPDATE Compra SET estado = 'pago_en_revision' WHERE id = %s", (order_id,)
                    )
                    conn.execute("UPDATE Pago SET estado = 'en_revision' WHERE id = %s", (payment["id"],))
                    return _order_payload(conn, _order(conn, order_id, who["id"]))
            approve_reserved_order(conn, locked)
            conn.execute(
                "UPDATE Pago SET estado = 'aprobado', fecha_pago = now() WHERE id = %s",
                (payment["id"],),
            )
            return _order_payload(conn, _order(conn, order_id, who["id"]))
    if result.get("status") in ("failed", "canceled", "cancelled", "expired"):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            locked = _order(conn, order_id, who["id"], lock=True)
            if locked["estado"] == "pendiente":
                conn.execute(
                    "UPDATE ReservaCompra SET estado = 'liberada' WHERE id_compra = %s AND estado = 'activa'",
                    (order_id,),
                )
                conn.execute("UPDATE Compra SET estado = 'rechazado' WHERE id = %s", (order_id,))
            conn.execute("UPDATE Pago SET estado = 'rechazado' WHERE id = %s", (payment["id"],))
            return _order_payload(conn, _order(conn, order_id, who["id"]))
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return _order_payload(conn, _order(conn, order_id, who["id"]))


@router.post("/payments/webhook")
def payment_webhook(
    body: dict = Body(...),
    data_id: str | None = Query(default=None, alias="data.id"),
    x_signature: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
):
    """Accept only signed test notifications; verify the payment at the provider."""
    if not MERCADOPAGO_WEBHOOK_SECRET:
        fail(503, "Webhook de prueba no configurado")
    if (not data_id or not re.fullmatch(r"ORDTST[A-Za-z0-9_-]{1,120}", data_id)
            or not x_request_id or not 1 <= len(x_request_id) <= 150
            or body.get("type") != "order" or body.get("live_mode") is not False
            or not isinstance(body.get("data"), dict)
            or body["data"].get("id") != data_id):
        fail(401, "Notificación de prueba inválida")
    parts = dict(
        part.strip().split("=", 1) for part in (x_signature or "").split(",") if "=" in part
    )
    ts, digest = parts.get("ts", ""), parts.get("v1", "")
    if not re.fullmatch(r"[0-9]{1,16}", ts) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        fail(401, "Firma inválida")
    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};".encode()
    expected = hmac.new(MERCADOPAGO_WEBHOOK_SECRET.encode(), manifest, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest.lower()):
        fail(401, "Firma inválida")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute("""SELECT p.id_compra, c.id_cliente FROM Pago p
                              JOIN Compra c ON c.id = p.id_compra
                              WHERE p.id_transaccion_externa = %s
                                AND p.metodo_pago = 'MERCADOPAGO_TEST'""", (data_id,)).fetchone()
    if row:
        verify_payment(row["id_compra"], who={"id": row["id_cliente"], "rol": "cliente"})
    return {"received": True}
