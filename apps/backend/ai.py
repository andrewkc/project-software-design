"""Gemini adapter for decision-support recommendations.

The API key lives only in the backend. The model is advisory: it never writes
to the database, approves a suggestion, creates a purchase or changes stock.
"""

import json
import urllib.error
import urllib.request

from config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL

MAX_RECOMENDACIONES = 8
TIPOS_PERMITIDOS = {"descuento", "aumento", "reposicion"}

SYSTEM_INSTRUCTION = (
    "Eres un asistente de apoyo para el jefe de una bodega. Propón decisiones "
    "informativas, no aprobadas. Usa únicamente los datos que se te entregan: "
    "nombre, categoría, stock, precio de venta, fecha de vencimiento y estado. "
    "No hay datos de costo, margen, historial de ventas ni predicción de vida "
    "útil: no los inventes ni los menciones como si existieran. Un descuento "
    "debe ser un precio positivo menor al actual. Un aumento debe ser un precio "
    "positivo mayor al actual. Una reposición es solo una cantidad positiva de "
    "referencia: no genera compras ni modifica stock. Justifica cada propuesta "
    "en una frase breve citando los campos usados. Devuelve como máximo "
    f"{MAX_RECOMENDACIONES} propuestas y solo para productos con estado activo."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "recomendaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id_producto": {"type": "integer"},
                    "tipo": {"type": "string", "enum": sorted(TIPOS_PERMITIDOS)},
                    "precio_sugerido": {"type": "number"},
                    "cantidad_sugerida": {"type": "integer"},
                    "justificacion": {"type": "string"},
                },
                "required": ["id_producto", "tipo", "justificacion"],
            },
        }
    },
    "required": ["recomendaciones"],
}


class AIUnavailable(Exception):
    """The suggestion service could not produce a usable response."""


def _prompt(products):
    resumen = [
        {
            "id_producto": row["id"],
            "nombre": row["nombre"],
            "categoria": row["categoria"],
            "stock": row["stock"],
            "precio_venta": row["precio_venta"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "estado": row["estado"],
        }
        for row in products
    ]
    return (
        "Productos de la bodega (JSON):\n"
        + json.dumps(resumen, ensure_ascii=False)
        + "\nDevuelve solo el objeto JSON solicitado. No incluyas texto adicional."
    )


def _request_body(products):
    return {
        "model": GEMINI_MODEL,
        "input": _prompt(products),
        "system_instruction": SYSTEM_INSTRUCTION,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": RESPONSE_SCHEMA,
        },
        # Inventory-derived prompts are not stored by the provider.
        "store": False,
    }


def _extract_text(payload):
    # REST returns the interaction object at the top level; some SDK-shaped
    # responses wrap it under "interaction" and expose "output_text".
    if not isinstance(payload, dict):
        raise AIUnavailable("Respuesta inesperada del proveedor de IA")
    interaction = payload.get("interaction", payload)
    if not isinstance(interaction, dict):
        raise AIUnavailable("Respuesta inesperada del proveedor de IA")

    output = interaction.get("output_text")
    if isinstance(output, str) and output.strip():
        return output
    for step in reversed(interaction.get("steps") or []):
        for part in step.get("content") or []:
            text = part.get("text") if isinstance(part, dict) else None
            if isinstance(text, str) and text.strip():
                return text
    # Structured responses may already be the requested object.
    if "recomendaciones" in interaction:
        return json.dumps(interaction, ensure_ascii=False)
    raise AIUnavailable("El proveedor de IA no devolvió texto utilizable")


def _sanitize(items, products):
    by_id = {row["id"]: row for row in products}
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        try:
            product_id = int(item.get("id_producto"))
        except (TypeError, ValueError):
            continue
        product = by_id.get(product_id)
        if not product or item.get("tipo") not in TIPOS_PERMITIDOS:
            continue
        justification = str(item.get("justificacion") or "").strip()[:400]
        if not justification:
            continue

        recommendation = {
            "id_producto": product_id,
            "nombre": product["nombre"],
            "icono": product.get("icono") or "📦",
            "tipo": item["tipo"],
            "justificacion": justification,
        }
        if item["tipo"] in ("descuento", "aumento"):
            try:
                price = float(item.get("precio_sugerido"))
                current = float(product["precio_venta"])
            except (TypeError, ValueError):
                continue
            if price <= 0 or (
                item["tipo"] == "descuento" and price >= current
            ) or (
                item["tipo"] == "aumento" and price <= current
            ):
                continue
            recommendation["precio_actual"] = current
            recommendation["precio_sugerido"] = round(price, 2)
        else:
            try:
                quantity = int(item.get("cantidad_sugerida"))
            except (TypeError, ValueError):
                continue
            if quantity <= 0:
                continue
            recommendation["stock_actual"] = product["stock"]
            recommendation["cantidad_sugerida"] = quantity

        result.append(recommendation)
        if len(result) >= MAX_RECOMENDACIONES:
            break
    return result


def generate_recommendations(products):
    """Return sanitized suggestions, or raise AIUnavailable."""
    if not GEMINI_API_KEY:
        raise AIUnavailable("La IA no está configurada en el servidor")
    if not products:
        return []

    request = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(_request_body(products)).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)
        data = json.loads(_extract_text(payload))
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", "replace").strip()
        except (OSError, ValueError):
            pass
        if GEMINI_API_KEY and GEMINI_API_KEY in detail:
            detail = detail.replace(GEMINI_API_KEY, "***")
        detail = detail[:300]
        message = f"El proveedor de IA devolvió {error.code}"
        if detail:
            message += f": {detail}"
        raise AIUnavailable(message) from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise AIUnavailable("No se pudo contactar al proveedor de IA") from error

    items = data.get("recomendaciones") if isinstance(data, dict) else None
    return _sanitize(items, products)
