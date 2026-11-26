"""Transactional paid purchases shared by the sales API and the demo seed.

A sale exists only when ``Compra.estado = 'pagado'``. That is the single point
where stock is reduced: the same transaction writes the purchase, its details,
a consumed reservation and the payment trace. Reservations and unpaid orders
never decrement stock and are never shown as sales.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

from security import fail, hash_password

DEMO_CLIENT_EMAIL = "cliente.demo@bodesmart.local"
DEMO_CLIENT_NAME = "Cliente Demo"
DEMO_CLIENT_PASSWORD = "DemoCliente2026!"

# Synthetic purchases for the local prototype. They are keyed so a restart
# never decrements stock twice. All selected products are active with a future
# expiry (or none) in seed.sql, so the sale validation accepts them.
DEMO_SALES = (
    (uuid.UUID("11111111-1111-4111-8111-111111111111"), ((13, 4, None),)),
    (uuid.UUID("22222222-2222-4222-8222-222222222222"), ((20, 3, None), (7, 5, None))),
    (uuid.UUID("33333333-3333-4333-8333-333333333333"), ((4, 6, None), (8, 2, None))),
)


def positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        fail(400, f"{name} debe ser un entero positivo")
    return value


def parsed_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        fail(400, "Clave de compra inválida")


def release_expired(conn):
    """Keep the customer checkout state machine consistent with open orders."""
    conn.execute(
        """UPDATE Compra SET estado = 'expirado'
           WHERE estado = 'pendiente' AND reserva_hasta <= now()"""
    )
    conn.execute(
        """UPDATE ReservaCompra SET estado = 'liberada'
           WHERE estado = 'activa'
             AND id_compra IN (SELECT id FROM Compra WHERE estado = 'expirado')"""
    )


def sale_response(conn, row) -> dict:
    lines = conn.execute(
        """SELECT d.id, d.id_producto, d.id_oferta, d.cantidad, d.precio_unitario,
                  d.subtotal, p.nombre, p.icono, p.unidad_medida
           FROM DetalleCompra d JOIN Producto p ON p.id = d.id_producto
           WHERE d.id_compra = %s ORDER BY d.id""",
        (row["id"],),
    ).fetchall()
    client = conn.execute(
        "SELECT nombres, apellidos FROM Cliente WHERE id = %s", (row["id_cliente"],)
    ).fetchone()
    payment = conn.execute(
        """SELECT metodo_pago, estado FROM Pago
           WHERE id_compra = %s ORDER BY id DESC LIMIT 1""",
        (row["id"],),
    ).fetchone()
    client_name = ""
    if client:
        client_name = f"{client['nombres']} {client['apellidos']}".strip()
    paid_at = row["fecha_pago"] or row["fecha_compra"]
    return {
        "id": row["id"],
        "estado": row["estado"],
        "cliente": client_name or f"Cliente #{row['id_cliente']}",
        "clienteId": row["id_cliente"],
        "bodegaId": row["id_bodega"],
        "fechaCompra": row["fecha_compra"].isoformat() if row["fecha_compra"] else None,
        "fechaPago": paid_at.isoformat() if paid_at else None,
        "total": str(row["total"]),
        "metodoPago": payment["metodo_pago"] if payment else None,
        "lineas": [
            {
                "id": line["id"],
                "productoId": line["id_producto"],
                "ofertaId": line["id_oferta"],
                "nombre": line["nombre"],
                "icono": line["icono"] or "📦",
                "unidad": line["unidad_medida"] or "unid.",
                "cantidad": line["cantidad"],
                "precioUnitario": str(line["precio_unitario"]),
                "subtotal": str(line["subtotal"]),
            }
            for line in lines
        ],
    }


def _request_hash(normalized) -> str:
    payload = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def decrement_stock_once(conn, items):
    """Apply the single stock-decrement rule shared by every paid flow.

    ``items`` is an iterable of ``(product_id, bodega_id, quantity, error)``.
    The conditional UPDATE plus the caller's transaction guarantee that no
    unpaid, rejected or expired order can reduce inventory and that a paid
    order reduces it exactly once.
    """
    for product_id, bodega_id, quantity, error in items:
        updated = conn.execute(
            """UPDATE ProductosBodega SET stock = stock - %s
               WHERE id_producto = %s AND id_bodega = %s AND stock >= %s
               RETURNING stock""",
            (quantity, product_id, bodega_id, quantity),
        ).fetchone()
        if not updated:
            fail(409, error)


def approve_reserved_order(conn, order):
    """Turn one reserved purchase into a paid sale, decrementing stock once.

    The caller owns the transaction and must pass a row locked with
    ``FOR UPDATE OF c``. This is the customer-checkout counterpart of
    ``create_paid_sale``: both funnel stock changes through
    ``decrement_stock_once`` and write a consumed reservation.
    """
    if order["estado"] == "pagado":
        return
    if order["estado"] != "pendiente":
        fail(409, "La reserva ya no admite pago")
    deadline = order["reserva_hasta"]
    if deadline is None:
        fail(409, "La reserva venció; no se descontó inventario")
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= datetime.now(timezone.utc):
        fail(409, "La reserva venció; no se descontó inventario")

    reservations = conn.execute(
        """SELECT id_producto, id_bodega, cantidad FROM ReservaCompra
           WHERE id_compra = %s AND estado = 'activa' ORDER BY id_producto""",
        (order["id"],),
    ).fetchall()
    if not reservations:
        fail(409, "El pedido no tiene reserva activa")

    decrement_stock_once(conn, [
        (item["id_producto"], item["id_bodega"], item["cantidad"],
         "Inventario insuficiente para confirmar el pago")
        for item in reservations
    ])
    conn.execute(
        "UPDATE ReservaCompra SET estado = 'consumida' WHERE id_compra = %s",
        (order["id"],),
    )
    conn.execute(
        """UPDATE Compra SET estado = 'pagado', fecha_pago = now(),
                             reserva_hasta = NULL WHERE id = %s""",
        (order["id"],),
    )


def create_paid_sale(conn, *, id_cliente, bodega_id, lineas, idempotency_key=None):
    """Create one paid purchase and reduce stock exactly once.

    The caller owns the psycopg transaction. Any validation error raises, so
    the context manager rolls back every stock update made before the error.
    """
    id_cliente = positive_int(id_cliente, "id_cliente")
    bodega_id = positive_int(bodega_id, "id_bodega")
    if not isinstance(lineas, list) or not 1 <= len(lineas) <= 20:
        fail(400, "Agrega entre 1 y 20 productos")
    normalized = []
    seen = set()
    for item in lineas:
        if not isinstance(item, dict):
            fail(400, "Producto inválido")
        product_id = positive_int(item.get("id_producto"), "id_producto")
        quantity = positive_int(item.get("cantidad"), "cantidad")
        offer_id = item.get("id_oferta")
        if offer_id is not None:
            offer_id = positive_int(offer_id, "id_oferta")
        if product_id in seen:
            fail(400, "No repitas un producto")
        seen.add(product_id)
        normalized.append((product_id, quantity, offer_id or 0))
    normalized.sort()
    fingerprint = _request_hash(normalized)

    key = parsed_uuid(idempotency_key) if idempotency_key else None
    release_expired(conn)
    if key is not None:
        lock_id = int.from_bytes(hashlib.sha256(key.bytes).digest()[:8], "big", signed=True)
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))
        previous = conn.execute(
            "SELECT id, id_cliente, request_hash FROM Compra WHERE idempotency_key = %s",
            (key,),
        ).fetchone()
        if previous:
            if previous["id_cliente"] != id_cliente or previous["request_hash"] != fingerprint:
                fail(409, "Clave de compra ya usada con otros datos")
            row = conn.execute("SELECT * FROM Compra WHERE id = %s", (previous["id"],)).fetchone()
            return sale_response(conn, row)

    client = conn.execute(
        "SELECT id FROM Cliente WHERE id = %s AND estado = 'activo'", (id_cliente,)
    ).fetchone()
    if not client:
        fail(404, "Cliente no encontrado o inactivo")

    clock = conn.execute(
        "SELECT now()::timestamp AS local_now, CURRENT_DATE AS local_date"
    ).fetchone()
    selected = []
    total = Decimal("0.00")
    for product_id, quantity, offer_id in normalized:
        product = conn.execute(
            """SELECT p.id, p.nombre, p.icono, p.unidad_medida, pb.stock,
                      pb.precio_venta, pb.fecha_vencimiento, pb.estado
               FROM Producto p JOIN ProductosBodega pb ON pb.id_producto = p.id
               WHERE p.id = %s AND pb.id_bodega = %s
               FOR UPDATE OF pb""",
            (product_id, bodega_id),
        ).fetchone()
        if not product:
            fail(404, "Producto no disponible en la bodega")
        if product["estado"] != "activo":
            fail(409, "El producto no está activo")
        if product["fecha_vencimiento"] is not None and product["fecha_vencimiento"] <= clock["local_date"]:
            fail(409, "No se vende un producto vencido")
        if product["stock"] < quantity:
            fail(409, "Stock insuficiente para la venta")

        price = product["precio_venta"]
        if offer_id:
            offer = conn.execute(
                """SELECT id, precio_oferta, estado, fecha_inicio, fecha_fin
                   FROM Oferta
                   WHERE id = %s AND id_producto = %s AND id_bodega = %s""",
                (offer_id, product_id, bodega_id),
            ).fetchone()
            if (not offer or offer["estado"] != "activo"
                    or offer["fecha_inicio"] > clock["local_now"]
                    or offer["fecha_fin"] <= clock["local_now"]):
                fail(409, "La oferta no está vigente para este producto")
            price = offer["precio_oferta"]
        try:
            unit_price = Decimal(str(price))
        except (InvalidOperation, TypeError, ValueError):
            fail(409, "Precio de venta inválido")
        if unit_price <= 0:
            fail(409, "El precio de venta debe ser positivo")
        subtotal = unit_price * quantity
        total += subtotal
        selected.append((product_id, offer_id or None, quantity, unit_price, subtotal))
    if total <= 0:
        fail(400, "El importe debe ser positivo")

    purchase = conn.execute(
        """INSERT INTO Compra(id_cliente, id_bodega, total, estado, fecha_pago,
                              reserva_hasta, idempotency_key, request_hash)
           VALUES (%s, %s, %s, 'pagado', now(), NULL, %s, %s)
           RETURNING id""",
        (id_cliente, bodega_id, total, key, fingerprint),
    ).fetchone()
    purchase_id = purchase["id"]
    decrement_stock_once(conn, [
        (product_id, bodega_id, quantity, "Inventario insuficiente para confirmar la compra")
        for product_id, offer_id, quantity, unit_price, subtotal in selected
    ])
    for product_id, offer_id, quantity, unit_price, subtotal in selected:
        conn.execute(
            """INSERT INTO DetalleCompra(id_compra, id_producto, id_oferta,
                                          cantidad, precio_unitario, subtotal)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (purchase_id, product_id, offer_id, quantity, unit_price, subtotal),
        )
        conn.execute(
            """INSERT INTO ReservaCompra(id_compra, id_producto, id_bodega, cantidad, estado)
               VALUES (%s, %s, %s, %s, 'consumida')""",
            (purchase_id, product_id, bodega_id, quantity),
        )
    conn.execute(
        """INSERT INTO Pago(id_compra, metodo_pago, monto, estado, fecha_pago)
           VALUES (%s, 'LOCAL_SIMULATION', %s, 'aprobado', now())""",
        (purchase_id, total),
    )
    row = conn.execute("SELECT * FROM Compra WHERE id = %s", (purchase_id,)).fetchone()
    return sale_response(conn, row)


def ensure_demo_sales(conn):
    """Seed three synthetic paid purchases without touching real customer data."""
    client = conn.execute(
        "SELECT id FROM Cliente WHERE lower(correo) = lower(%s)", (DEMO_CLIENT_EMAIL,)
    ).fetchone()
    if client:
        client_id = client["id"]
        # This is a reserved synthetic account, not a real customer.
        conn.execute("UPDATE Cliente SET estado = 'activo' WHERE id = %s", (client_id,))
    else:
        client_id = conn.execute(
            """INSERT INTO Cliente(nombres, apellidos, correo, password, estado)
               VALUES (%s, %s, %s, %s, 'activo') RETURNING id""",
            (DEMO_CLIENT_NAME.split()[0], DEMO_CLIENT_NAME.split()[1],
             DEMO_CLIENT_EMAIL, hash_password(DEMO_CLIENT_PASSWORD)),
        ).fetchone()["id"]

    for key, products in DEMO_SALES:
        if conn.execute("SELECT 1 FROM Compra WHERE idempotency_key = %s", (key,)).fetchone():
            continue
        lines = [
            {"id_producto": product_id, "cantidad": quantity, "id_oferta": offer_id}
            for product_id, quantity, offer_id in products
        ]
        try:
            # Savepoint: if a demo product was edited or removed, discard any
            # partial write and keep the rest of the seed (and the stock) intact.
            with conn.transaction():
                create_paid_sale(
                    conn,
                    id_cliente=client_id,
                    bodega_id=1,
                    lineas=lines,
                    idempotency_key=str(key),
                )
        except HTTPException:
            # The prototype must still start; the empty state explains the gap.
            continue
