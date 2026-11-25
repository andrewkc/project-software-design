import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import bodega_id_for, fetch_product, normalize_date, product_response
from security import fail, identity_from_header, require

router = APIRouter()


@router.get("/products")
def list_products(who: dict = Depends(identity_from_header)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        if bodega_id is None:
            fail(401, "La cuenta ya no tiene acceso")
        rows = conn.execute(
            """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad_medida,
                      pb.stock, pb.precio_venta, pb.fecha_vencimiento, pb.estado,
                      pb.creado_por, pb.bloqueado, pb.bloqueado_por
               FROM Producto p
               JOIN ProductosBodega pb ON pb.id_producto = p.id
               WHERE pb.id_bodega = %s
               ORDER BY p.id DESC""",
            (bodega_id,),
        ).fetchall()
    return [product_response(row) for row in rows]


@router.post("/products")
def create_product(body: dict = Body(...), who: dict = Depends(identity_from_header)):
    require(body, "nombre", "stock")
    if int(body["stock"]) < 0:
        fail(400, "El stock no puede ser negativo")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        if bodega_id is None:
            fail(401, "La cuenta ya no tiene acceso")
        producto = conn.execute(
            """INSERT INTO Producto (icono, nombre, categoria, unidad_medida)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (body.get("icono") or "📦", body["nombre"], body.get("categoria"), body.get("unidad_medida")),
        ).fetchone()
        conn.execute(
            """INSERT INTO ProductosBodega
               (id_producto, id_bodega, stock, precio_venta, fecha_vencimiento, estado, creado_por, bloqueado)
               VALUES (%s, %s, %s, %s, %s, 'activo', %s, FALSE)""",
            (
                producto["id"], bodega_id, int(body["stock"]),
                float(body.get("precio_venta") or 0), normalize_date(body.get("fecha_vencimiento")),
                who["id"],
            ),
        )
        row = fetch_product(conn, bodega_id, producto["id"])
    return product_response(row)


@router.patch("/products/{product_id}")
def update_product(product_id: int, body: dict = Body(...), who: dict = Depends(identity_from_header)):
    allowed = {"nombre", "categoria", "unidad_medida", "stock", "precio_venta", "fecha_vencimiento", "estado", "bloqueado"}
    changes = {key: value for key, value in body.items() if key in allowed}
    if not changes:
        fail(400, "No hay campos editables")

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        if bodega_id is None:
            fail(401, "La cuenta ya no tiene acceso")
        row = fetch_product(conn, bodega_id, product_id)
        if not row:
            fail(404, "Producto no encontrado")

        if who["rol"] == "empleado":
            if row["estado"] == "inactivo" or row["bloqueado"]:
                fail(403, "Esta fila no se puede editar")
            if row["creado_por"] != who["id"]:
                fail(403, "Solo puedes editar los productos que creaste")
            if "estado" in changes or "bloqueado" in changes:
                fail(403, "Solo el jefe puede bloquear o desactivar productos")
        elif "bloqueado" in changes:
            changes["bloqueado_por"] = who["id"] if changes["bloqueado"] else None

        catalog = {key: changes[key] for key in ("nombre", "categoria", "unidad_medida") if key in changes}
        inventory = {key: changes[key] for key in ("stock", "precio_venta", "fecha_vencimiento", "estado", "bloqueado", "bloqueado_por") if key in changes}
        if "fecha_vencimiento" in inventory:
            inventory["fecha_vencimiento"] = normalize_date(inventory["fecha_vencimiento"])
        if "stock" in inventory and int(inventory["stock"]) < 0:
            fail(400, "El stock no puede ser negativo")
        if "precio_venta" in inventory:
            inventory["precio_venta"] = float(inventory["precio_venta"])

        if catalog:
            assignments = ", ".join(f"{key} = %s" for key in catalog)
            conn.execute(f"UPDATE Producto SET {assignments} WHERE id = %s", (*catalog.values(), product_id))
        if inventory:
            assignments = ", ".join(f"{key} = %s" for key in inventory)
            conn.execute(
                f"UPDATE ProductosBodega SET {assignments} WHERE id_producto = %s AND id_bodega = %s",
                (*inventory.values(), product_id, bodega_id),
            )
        row = fetch_product(conn, bodega_id, product_id)
    return product_response(row)
