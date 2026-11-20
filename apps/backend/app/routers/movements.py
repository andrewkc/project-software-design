import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_connection, now_iso
from ..dependencies import get_current_profile, get_jefe_profile
from ..mappers import movement_out
from ..schemas import MovementIn, MovementOut

router = APIRouter(prefix="/movements", tags=["movements"])


def parse_expiry(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La fecha de vencimiento no es válida.")


def get_product_for_movement(conn, product_id: str, store: str):
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None or product["store"] != store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado en tu bodega.")
    return product


@router.get("", response_model=list[MovementOut])
def list_movements(jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    rows = conn.execute(
        "SELECT * FROM movements WHERE store = ? ORDER BY fecha_hora DESC",
        (jefe["store"],),
    ).fetchall()
    result = []
    for row in rows:
        details = [dict(item) for item in conn.execute(
            "SELECT producto_id, lote_id, cantidad, importe_unitario, subtotal FROM movement_details WHERE movimiento_id = ?",
            (row["id"],),
        ).fetchall()]
        result.append(movement_out(dict(row), details))
    return result


@router.post("", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
def create_movement(payload: MovementIn, profile: dict = Depends(get_current_profile), conn=Depends(get_connection)):
    """RF-04 a RF-08 / RN-03 a RN-06.

    Valida todo antes de escribir. La transacción evita salidas parciales
    y descuentos duplicados (RN-04).
    """
    prepared = []
    total = 0.0 if payload.tipo == "salida" else None

    for item in payload.items:
        product = get_product_for_movement(conn, item.productoId, profile["store"])
        if not product["activo"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{product['name']} está desactivado.")

        lot = None
        if item.loteId:
            lot = conn.execute("SELECT * FROM lots WHERE id = ? AND product_id = ?", (item.loteId, product["id"])).fetchone()
            if lot is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El lote no corresponde al producto.")

        if payload.tipo == "salida":
            if lot is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las salidas requieren un lote (RN-03).")
            if item.cantidad > lot["cantidad_disponible"] or item.cantidad > product["stock"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stock insuficiente para {product['name']} (RN-04).")
            expires = parse_expiry(lot["fecha_vencimiento"])
            if expires is not None and expires < date.today():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{product['name']} está vencido; registra una merma (RN-06).")
            unit_price = item.importeUnitario if item.importeUnitario is not None else product["price"]
            subtotal = item.cantidad * unit_price
            total += subtotal
        else:
            unit_price = item.costoUnitario if item.costoUnitario is not None else 0
            subtotal = None

        prepared.append({
            "product": product,
            "lot": lot,
            "lot_id": lot["id"] if lot else None,
            "item": item,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })

    movement_id = str(uuid.uuid4())
    with conn:
        for entry in prepared:
            product = entry["product"]
            item = entry["item"]

            if payload.tipo == "salida":
                conn.execute(
                    "UPDATE lots SET cantidad_disponible = cantidad_disponible - ? WHERE id = ?",
                    (item.cantidad, entry["lot_id"]),
                )
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item.cantidad, product["id"]),
                )
            else:
                lot_id = entry["lot_id"] or str(uuid.uuid4())
                entry["lot_id"] = lot_id
                if entry["lot"]:
                    conn.execute(
                        "UPDATE lots SET cantidad_disponible = cantidad_disponible + ? WHERE id = ?",
                        (item.cantidad, lot_id),
                    )
                else:
                    conn.execute(
                        """INSERT INTO lots
                           (id, product_id, store, codigo, fecha_ingreso, fecha_vencimiento, cantidad_disponible, costo_unitario)
                           VALUES (?, ?, ?, ?, date('now'), ?, ?, ?)""",
                        (
                            lot_id,
                            product["id"],
                            profile["store"],
                            item.codigoLote or f"LOTE-{uuid.uuid4().hex[:8]}",
                            item.fechaVencimiento,
                            item.cantidad,
                            item.costoUnitario or 0,
                        ),
                    )
                conn.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (item.cantidad, product["id"]),
                )

        conn.execute(
            """INSERT INTO movements
               (id, store, fecha_hora, tipo, motivo, total, responsable_id, responsable_nombre)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                movement_id,
                profile["store"],
                now_iso(),
                payload.tipo,
                payload.motivo.strip(),
                total,
                profile["id"],
                profile["name"],
            ),
        )
        for entry in prepared:
            conn.execute(
                """INSERT INTO movement_details
                   (id, movimiento_id, producto_id, lote_id, cantidad, importe_unitario, subtotal)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    movement_id,
                    entry["product"]["id"],
                    entry["lot_id"],
                    entry["item"].cantidad,
                    entry["unit_price"],
                    entry["subtotal"],
                ),
            )

        created = conn.execute("SELECT * FROM movements WHERE id = ?", (movement_id,)).fetchone()
        details = [dict(item) for item in conn.execute(
            "SELECT producto_id, lote_id, cantidad, importe_unitario, subtotal FROM movement_details WHERE movimiento_id = ?",
            (movement_id,),
        ).fetchall()]
    return movement_out(dict(created), details)
