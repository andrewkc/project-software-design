import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from ai import AIUnavailable
from config import DSN, GEMINI_ALLOWED_MODELS, GEMINI_MODEL
from database import bodega_id_for, list_categories
from registration_ai import MediaValidationError, ModelNotAllowed, extract_product_draft
from security import fail, identity_from_header

router = APIRouter()

AVISO = (
    "La asistencia solo propone datos revisables. No guarda productos, no crea "
    "movimientos ni modifica stock: nada se aplica hasta que confirmes el formulario."
)


@router.get("/ai/models")
def ai_models(who: dict = Depends(identity_from_header)):
    """Allowlisted Gemini ids for the UI. The key never leaves the backend."""
    return {
        "default": GEMINI_MODEL,
        "modelos": [
            {"id": model, "label": model, "activo": model == GEMINI_MODEL}
            for model in GEMINI_ALLOWED_MODELS
        ],
        "nota": "La disponibilidad y la cuota dependen del proveedor.",
    }


@router.post("/products/extract")
def extract_product(body: dict = Body(...), who: dict = Depends(identity_from_header)):
    # Both roles can register products (RN-02). The draft is read-only: no
    # warehouse data is sent to the provider and no row is written here.
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if bodega_id_for(conn, who) is None:
            fail(401, "La cuenta ya no tiene acceso")
        categorias = list_categories(conn)

    try:
        result = extract_product_draft(
            body.get("modo"),
            body.get("data"),
            body.get("mime_type"),
            body.get("codigo"),
            body.get("duracion"),
            categorias=categorias,
            modelo=body.get("modelo"),
        )
    except MediaValidationError as error:
        fail(400, str(error))
    except ModelNotAllowed as error:
        fail(400, str(error))
    except AIUnavailable as error:
        fail(503, str(error))

    return {**result, "modelo": result.get("proveedor", GEMINI_MODEL), "aviso": AVISO}
