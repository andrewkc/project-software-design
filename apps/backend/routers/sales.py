"""Read-only sales history for operations plus the transactional sale contract.

Only paid purchases are exposed. The same helper creates them and reduces
stock in one database transaction, so history and inventory cannot disagree.
"""

import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import bodega_id_for
from sales_service import create_paid_sale, release_expired, sale_response
from security import fail, identity_from_header, require

router = APIRouter()


def operations_user(who: dict = Depends(identity_from_header)) -> dict:
    if who.get("rol") not in ("jefe", "empleado"):
        fail(403, "Esta sección es para el personal de la bodega")
    return who


@router.get("/sales")
def list_sales(who: dict = Depends(operations_user)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        if bodega_id is None:
            fail(401, "La cuenta ya no tiene acceso")
        release_expired(conn)
        rows = conn.execute(
            """SELECT c.* FROM Compra c
               WHERE c.id_bodega = %s AND c.estado = 'pagado'
               ORDER BY COALESCE(c.fecha_pago, c.fecha_compra) DESC, c.id DESC""",
            (bodega_id,),
        ).fetchall()
        return [sale_response(conn, row) for row in rows]


@router.post("/sales")
def create_sale(body: dict = Body(...), who: dict = Depends(operations_user)):
    """Register a paid purchase on behalf of an existing ``cliente``.

    customer-web will call this same atomic contract when it is implemented;
    it never asks the browser to subtract stock by itself.
    """
    require(body, "id_cliente", "lineas")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        if bodega_id is None:
            fail(401, "La cuenta ya no tiene acceso")
        return create_paid_sale(
            conn,
            id_cliente=body["id_cliente"],
            bodega_id=bodega_id,
            lineas=body["lineas"],
            idempotency_key=body.get("idempotency_key"),
        )
