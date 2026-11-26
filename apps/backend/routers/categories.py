import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import bodega_id_for, ensure_category, list_categories, normalize_category
from security import fail, identity_from_header

router = APIRouter()


@router.get("/categories")
def get_categories(who: dict = Depends(identity_from_header)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if bodega_id_for(conn, who) is None:
            fail(401, "La cuenta ya no tiene acceso")
        return list_categories(conn)


@router.post("/categories")
def create_category(body: dict = Body(...), who: dict = Depends(identity_from_header)):
    raw = normalize_category(body.get("nombre"))
    if not raw:
        fail(400, "Escribe un nombre de categoría válido")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if bodega_id_for(conn, who) is None:
            fail(401, "La cuenta ya no tiene acceso")
        nombre = ensure_category(conn, raw)
    return {"nombre": nombre}
