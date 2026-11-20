import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_connection, now_iso
from ..dependencies import get_current_profile, get_jefe_profile
from ..mappers import product_out
from ..permissions import can_edit_product
from ..schemas import ProductIn, ProductOut, ProductPatch

router = APIRouter(prefix="/products", tags=["products"])

PATCH_FIELDS = {
    "name": "name",
    "category": "category",
    "icon": "icon",
    "stock": "stock",
    "unit": "unit",
    "price": "price",
    "expires": "expires",
}


def get_product(conn, product_id: str, store: str):
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None or row["store"] != store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado en tu bodega.")
    return row


@router.get("", response_model=list[ProductOut])
def list_products(profile: dict = Depends(get_current_profile), conn=Depends(get_connection)):
    rows = conn.execute("SELECT * FROM products WHERE store = ? ORDER BY creado_en DESC", (profile["store"],)).fetchall()
    return [product_out(row) for row in rows]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductIn, profile: dict = Depends(get_current_profile), conn=Depends(get_connection)):
    product_id = str(uuid.uuid4())
    with conn:
        conn.execute(
            """INSERT INTO products
               (id, store, name, category, icon, stock, unit, price, expires,
                creado_por, bloqueado, activo, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
            (
                product_id,
                profile["store"],
                payload.name.strip(),
                payload.category.strip(),
                payload.icon.strip() or "📦",
                payload.stock,
                payload.unit.strip(),
                payload.price,
                payload.expires,
                profile["id"],
                now_iso(),
            ),
        )
        # EN-03: el stock inicial queda respaldado por un lote (EN-04).
        conn.execute(
            """INSERT INTO lots
               (id, product_id, store, codigo, fecha_ingreso, cantidad_disponible, costo_unitario)
               VALUES (?, ?, ?, 'INICIAL', date('now'), ?, 0)""",
            (str(uuid.uuid4()), product_id, profile["store"], payload.stock),
        )
        created = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return product_out(created)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: str, payload: ProductPatch, profile: dict = Depends(get_current_profile), conn=Depends(get_connection)):
    product = get_product(conn, product_id, profile["store"])
    if not can_edit_product(dict(product), profile):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes editar esta fila.")

    changes = payload.model_dump(exclude_unset=True)
    previous_stock = product["stock"]
    new_stock = changes.get("stock", previous_stock)

    with conn:
        for field, column in PATCH_FIELDS.items():
            if field in changes:
                value = changes[field]
                if isinstance(value, str):
                    value = value.strip()
                conn.execute(f"UPDATE products SET {column} = ? WHERE id = ?", (value, product_id))

        # ADR-001 / RF-18: toda edición directa de stock deja un movimiento de ajuste.
        if new_stock != previous_stock:
            movement_id = str(uuid.uuid4())
            difference = new_stock - previous_stock
            conn.execute(
                """INSERT INTO movements
                   (id, store, fecha_hora, tipo, motivo, responsable_id, responsable_nombre,
                    producto_id, stock_anterior, stock_nuevo, diferencia)
                   VALUES (?, ?, ?, 'ajuste', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    movement_id,
                    profile["store"],
                    now_iso(),
                    "Edición directa de stock",
                    profile["id"],
                    profile["name"],
                    product_id,
                    previous_stock,
                    new_stock,
                    difference,
                ),
            )
            # El lote del ajuste sigue pendiente (pregunta abierta 11).
            conn.execute(
                """INSERT INTO movement_details
                   (id, movimiento_id, producto_id, lote_id, cantidad)
                   VALUES (?, ?, ?, NULL, ?)""",
                (str(uuid.uuid4()), movement_id, product_id, abs(difference)),
            )
        updated = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return product_out(updated)


@router.post("/{product_id}/lock", response_model=ProductOut)
def toggle_lock(product_id: str, jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    product = get_product(conn, product_id, jefe["store"])
    locked = not bool(product["bloqueado"])
    with conn:
        conn.execute(
            "UPDATE products SET bloqueado = ?, bloqueado_por = ? WHERE id = ?",
            (int(locked), jefe["id"] if locked else None, product_id),
        )
        updated = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return product_out(updated)


@router.post("/{product_id}/deactivate", response_model=ProductOut)
def toggle_active(product_id: str, jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    product = get_product(conn, product_id, jefe["store"])
    active = not bool(product["activo"])
    with conn:
        conn.execute("UPDATE products SET activo = ? WHERE id = ?", (int(active), product_id))
        updated = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return product_out(updated)
