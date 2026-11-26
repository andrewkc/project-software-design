from datetime import datetime, timezone

import psycopg
from fastapi import APIRouter, Depends
from psycopg.rows import dict_row

from ai import AIUnavailable, generate_recommendations
from config import DSN, GEMINI_MODEL
from database import bodega_id_for, product_response
from security import fail, identity_from_header

router = APIRouter()

AVISO = (
    "Sugerencias informativas, no validadas. La IA no aprueba cambios, no genera "
    "compras ni modifica inventario: el jefe decide."
)


@router.post("/recommendations/generate")
def generate_price_recommendations(who: dict = Depends(identity_from_header)):
    if who["rol"] != "jefe":
        fail(403, "Solo el jefe puede pedir recomendaciones")

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
               WHERE pb.id_bodega = %s AND pb.estado <> 'inactivo'
               ORDER BY p.id DESC""",
            (bodega_id,),
        ).fetchall()

    products = [product_response(row) for row in rows]
    try:
        recommendations = generate_recommendations(products)
    except AIUnavailable as error:
        fail(503, str(error))

    return {
        "generadas_en": datetime.now(timezone.utc).isoformat(),
        "modelo": GEMINI_MODEL,
        "recomendaciones": recommendations,
        "aviso": AVISO,
    }
