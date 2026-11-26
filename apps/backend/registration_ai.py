"""Gemini adapter for assisted product registration (REG-IA).

The key lives only in the backend. This adapter validates the uploaded media,
asks Gemini for a restricted draft and sanitizes every returned field. It never
writes to the database, approves the product or changes stock.
"""

import base64
import binascii
import json
import math
import urllib.error
import urllib.request
from datetime import date
from urllib.parse import quote, urlencode, urlparse

from ai import AIUnavailable
from config import (
    GEMINI_ALLOWED_MODELS,
    GEMINI_API_KEY,
    GEMINI_API_URL,
    GEMINI_MODEL,
    OPEN_FOOD_FACTS_API_URL,
    OPEN_FOOD_FACTS_USER_AGENT,
)

MODOS = {"photo", "voice", "barcode"}
MIME_IMAGEN = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MIME_AUDIO = {"audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav", "audio/x-wav", "audio/3gpp"}
MAX_IMAGEN_BYTES = 8 * 1024 * 1024
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SEGUNDOS = 60

CATEGORIAS = (
    "Abarrotes", "Lácteos", "Frutas", "Bebidas", "Limpieza",
    "Snacks", "Conservas", "Cuidado personal", "Otros",
)
UNIDADES = ("unid.", "kg", "paq.", "caja", "litro")
ICONOS = frozenset(
    "📦 🥛 🍎 🍏 🍊 🍋 🍌 🍇 🍓 🍉 🍍 🥝 🍑 🍐 🍒 🫐 🥑 🥥 🥭 🍈 🫒 🌰 🍠 🥜 🍿 "
    "🥚 🍞 🥐 🥖 🥪 🥨 🧀 🧈 🍖 🥩 🍗 🐟 🦐 🍤 🍣 🥓 🍔 🌭 🍕 🌮 🍟 🍝 🍜 🍚 🍛 "
    "🥫 🫙 "
    "🍲 🥗 🥦 🥕 🍅 🥬 🥒 🌽 🫑 🥔 🧅 🧄 🌶️ 🫚 🌿 🍯 🧂 🍫 🍬 🍪 🍩 🧁 🍰 🍦 "
    "🍽️ 🥄 🍴 🔪 ☕ 🍵 🧃 🥤 🫖 💧 🧊 🍺 🍷 🧴 🧼 🧽 🧻 🧹 🪣 🧺 🛒 🏷️ 🧯 💡 🔦 "
    "🪥 🧾 ⚖️ 🧰 🔧 🐾 🦴 🌱 🪴 🎁 ✏️ 📚 🧸 ⚽ 🎲 💻 📱 🔋 💊 🩹 🧪 🚿 🛁".split()
)

OPEN_FOOD_FACTS_FIELDS = "code,product_name,product_name_es,generic_name,brands,quantity,categories,categories_tags,url"
CATEGORY_KEYWORDS = (
    ("Lácteos", ("lácteo", "lacteo", "leche", "yogur", "yogurt", "queso", "mantequilla", "dairy", "milk", "cheese")),
    ("Frutas", ("fruta", "fruit", "manzana", "apple", "plátano", "platano", "banana", "naranja", "orange", "uva", "grape")),
    ("Bebidas", ("bebida", "beverage", "drink", "agua", "water", "jugo", "juice", "refresco", "soda", "café", "cafe", "coffee", "té", "tea")),
    ("Limpieza", ("limpieza", "cleaning", "detergente", "detergent", "jabón", "jabon", "soap", "limpiador", "cleaner")),
    ("Abarrotes", ("abarrote", "cereal", "arroz", "rice", "pasta", "pan", "bread", "harina", "flour", "azúcar", "azucar", "sugar", "aceite", "oil", "frijol", "bean", "lenteja", "lentil", "galleta", "snack", "chocolate")),
)
ICONO_POR_CATEGORIA = {
    "Lácteos": "🥛",
    "Frutas": "🍎",
    "Bebidas": "🥤",
    "Limpieza": "🧼",
    "Abarrotes": "📦",
}

SYSTEM_INSTRUCTION = (
    "Eres un asistente de registro de productos para una bodega. Solo propones "
    "campos preliminares; no guardas, no apruebas ni modificas inventario. No "
    "inventes datos que no aparezcan en la multimedia o en una fuente pública. "
    "Si no puedes identificar el producto, devuelve el objeto con los campos "
    "que puedas justificar y omite el resto. Devuelve únicamente el JSON pedido."
)

PROMPTS = {
    "photo": (
        "Observa la imagen del producto o su etiqueta. Devuelve solo: nombre, "
        "icono, categoria, cantidad y unidad. La cantidad es el stock inicial "
        "que se ve o se puede contar en la imagen; si no es observable, omítela. "
        "No devuelvas precio de venta, fecha de vencimiento ni código de barras. "
        "Usa una categoría y unidad de las listas permitidas."
    ),
    "voice": (
        "Escucha el dictado y transcribe a campos: nombre, icono, categoria, "
        "cantidad, unidad, precio_venta, fecha_vencimiento y codigo_barras. "
        "La cantidad es el stock inicial dictado; si no se menciona, omítela. "
        "El precio y la fecha solo se devuelven si el usuario los dicta "
        "explícitamente: no los inventes, no los estimes y no deduzcas la vida "
        "útil del producto. La fecha debe estar en ISO AAAA-MM-DD. El código de "
        "barras solo se devuelve si se dictan sus dígitos. Usa una categoría y "
        "una unidad de las listas permitidas y omite todo lo que no se dijo."
    ),
}


class MediaValidationError(ValueError):
    """The uploaded media or request fields are outside the prototype limits."""


class ModelNotAllowed(ValueError):
    """The requested model is not in the backend allowlist."""


def resolve_model(modelo=None):
    """Return an allowlisted Gemini id; empty means the configured default."""
    if modelo is None or (isinstance(modelo, str) and not modelo.strip()):
        return GEMINI_MODEL
    candidate = str(modelo).strip()
    if candidate not in GEMINI_ALLOWED_MODELS:
        raise ModelNotAllowed(
            "Modelo de IA no permitido. Opciones: " + ", ".join(GEMINI_ALLOWED_MODELS)
        )
    return candidate


def _mime_base(value):
    return str(value or "").split(";", 1)[0].strip().lower()


def _decode_media(data, mime_type):
    if not isinstance(data, str) or not data.strip():
        raise MediaValidationError("Falta el archivo para analizar")

    declared = ""
    encoded = data.strip()
    if encoded.lower().startswith("data:"):
        if "," not in encoded:
            raise MediaValidationError("El archivo no tiene un formato válido")
        header, encoded = encoded.split(",", 1)
        declared = _mime_base(header[5:])
        if mime_type and _mime_base(mime_type) != declared:
            raise MediaValidationError("El tipo de archivo declarado no coincide con el archivo")
        mime_type = declared
    mime_type = _mime_base(mime_type)
    if not mime_type:
        raise MediaValidationError("No se pudo determinar el tipo de archivo")

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise MediaValidationError("El archivo no viene en base64 válido") from None
    if not raw:
        raise MediaValidationError("El archivo está vacío")
    return raw, mime_type


def _validate_mode(modo, data, mime_type, duracion):
    if modo not in MODOS:
        raise MediaValidationError("Modo de registro no reconocido")
    raw, mime_type = _decode_media(data, mime_type)
    if modo == "voice":
        if mime_type not in MIME_AUDIO:
            raise MediaValidationError("La voz debe ser un archivo de audio permitido")
        if len(raw) > MAX_AUDIO_BYTES:
            raise MediaValidationError("El audio supera el límite de 8 MB")
        if duracion is not None:
            try:
                seconds = float(duracion)
            except (TypeError, ValueError):
                raise MediaValidationError("La duración del audio no es válida") from None
            if not math.isfinite(seconds) or seconds <= 0 or seconds > MAX_AUDIO_SEGUNDOS:
                raise MediaValidationError("La grabación debe durar entre 1 y 60 segundos")
    else:
        if mime_type not in MIME_IMAGEN:
            raise MediaValidationError("La imagen debe ser PNG, JPEG, WEBP, HEIC o HEIF")
        if len(raw) > MAX_IMAGEN_BYTES:
            raise MediaValidationError("La imagen supera el límite de 8 MB")
    return raw, mime_type


def _schema(modo):
    properties = {
        "nombre": {"type": "string"},
        "icono": {"type": "string"},
        "categoria": {"type": "string"},
        "unidad": {"type": "string"},
        "cantidad": {"type": "integer"},
    }
    if modo == "voice":
        properties.update(
            {
                "precio_venta": {"type": "number"},
                "fecha_vencimiento": {"type": "string"},
                "codigo_barras": {"type": "string"},
            }
        )
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }


def _request_body(modo, raw, mime_type, categorias=None, modelo=None):
    media_type = "audio" if modo == "voice" else "image"
    prompt = PROMPTS[modo]
    if categorias:
        prompt += " Categorías disponibles: " + ", ".join(categorias) + "."
    body = {
        "model": modelo or GEMINI_MODEL,
        "input": [
            {"type": "text", "text": prompt},
            {
                "type": media_type,
                "data": base64.b64encode(raw).decode("ascii"),
                "mime_type": mime_type,
            },
        ],
        "system_instruction": SYSTEM_INSTRUCTION,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": _schema(modo),
        },
        # Drafts with customer-provided media must not be retained by the provider.
        "store": False,
    }
    return body


def _extract_text(payload):
    if not isinstance(payload, dict):
        raise AIUnavailable("Respuesta inesperada del proveedor de IA")
    interaction = payload.get("interaction", payload)
    if not isinstance(interaction, dict):
        raise AIUnavailable("Respuesta inesperada del proveedor de IA")

    output = interaction.get("output_text")
    if isinstance(output, str) and output.strip():
        return output.strip()
    containers = list(interaction.get("steps") or [])
    containers.extend(interaction.get("output") or [])
    for container in reversed(containers):
        for part in container.get("content") or []:
            text = part.get("text") if isinstance(part, dict) else None
            if isinstance(text, str) and text.strip():
                return text.strip()
    if any(key in interaction for key in ("nombre", "icono", "categoria", "campos")):
        return json.dumps(interaction, ensure_ascii=False)
    raise AIUnavailable("El proveedor de IA no devolvió texto utilizable")


def _parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    data = json.loads(cleaned)
    if isinstance(data, dict) and isinstance(data.get("campos"), dict):
        data = data["campos"]
    return data if isinstance(data, dict) else {}


def _first_source(payload):
    interaction = payload.get("interaction", payload) if isinstance(payload, dict) else {}
    if not isinstance(interaction, dict):
        return ""
    containers = list(interaction.get("steps") or [])
    containers.extend(interaction.get("output") or [])
    for container in containers:
        for part in container.get("content") or []:
            for annotation in (part.get("annotations") or []) if isinstance(part, dict) else []:
                url = str(annotation.get("url") or "").strip() if isinstance(annotation, dict) else ""
                if _safe_url(url):
                    return url[:300]
    return ""


def _safe_url(value):
    url = str(value or "").strip()
    if len(url) > 300:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url


def _clean_text(value, limit=120):
    text = " ".join(str(value or "").split())
    return text[:limit] if text else ""


def _normalize_digits(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[:14] if 8 <= len(digits) <= 14 else ""


def _category_from_text(text):
    value = " ".join(str(text or "").split()).casefold()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in value for keyword in keywords):
            return category
    return ""


def _unit_from_quantity(value):
    text = " ".join(str(value or "").split()).casefold()
    if not text:
        return ""
    if "kg" in text:
        return "kg"
    if "litro" in text or "litros" in text or " l" in text or text.startswith("l"):
        return "litro"
    if "caja" in text:
        return "caja"
    if "paq" in text or "pack" in text:
        return "paq."
    if "unid" in text or "ud" in text or "pieza" in text:
        return "unid."
    return ""


def _lookup_open_food_facts(code):
    base = OPEN_FOOD_FACTS_API_URL.rstrip("/")
    query = urlencode({"fields": OPEN_FOOD_FACTS_FIELDS})
    url = f"{base}/{quote(code, safe='')}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": OPEN_FOOD_FACTS_USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {}
        raise AIUnavailable("No se pudo consultar la base de datos de productos; regístralo manualmente.") from error
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise AIUnavailable("No se pudo consultar la base de datos de productos; regístralo manualmente.") from None
    if not isinstance(payload, dict) or payload.get("status") != 1:
        return {}
    product = payload.get("product")
    return product if isinstance(product, dict) else {}


def _fields_from_open_food_facts(product, code):
    product_code = _normalize_digits(product.get("code")) or code
    fields = {"codigo_barras": product_code}

    nombre = _clean_text(
        product.get("product_name_es") or product.get("product_name") or product.get("generic_name")
    )
    if nombre:
        fields["nombre"] = nombre

    tags = product.get("categories_tags")
    tags_text = " ".join(tags) if isinstance(tags, list) else str(tags or "")
    categoria = _category_from_text(" ".join((nombre, str(product.get("categories") or ""), tags_text)))
    if categoria:
        fields["categoria"] = categoria
        fields["icono"] = ICONO_POR_CATEGORIA[categoria]

    unidad = _unit_from_quantity(product.get("quantity"))
    if unidad:
        fields["unidad"] = unidad

    source = _safe_url(product.get("url")) or _safe_url(
        f"https://world.openfoodfacts.org/product/{product_code}"
    )
    if source:
        fields["fuente"] = source
    return fields


def _add_price_and_expiration(data, result):
    try:
        price = float(data.get("precio_venta"))
    except (TypeError, ValueError):
        price = 0
    if math.isfinite(price) and 0 < price <= 1000000:
        result["precio_venta"] = round(price, 2)

    expiration = str(data.get("fecha_vencimiento") or "").strip()
    try:
        parsed_date = date.fromisoformat(expiration)
    except ValueError:
        parsed_date = None
    if parsed_date and parsed_date >= date.today():
        result["fecha_vencimiento"] = expiration


def _sanitize(data, modo, categorias=None):
    if not isinstance(data, dict):
        return {}
    result = {}

    nombre = _clean_text(data.get("nombre"))
    if nombre:
        result["nombre"] = nombre

    icono = data.get("icono")
    if isinstance(icono, str) and icono.strip() in ICONOS:
        result["icono"] = icono.strip()

    allowed = list(CATEGORIAS)
    allowed.extend(str(item).strip() for item in (categorias or []) if str(item).strip())
    categoria = str(data.get("categoria") or "").strip()
    match = next((item for item in allowed if item.casefold() == categoria.casefold()), None)
    if match:
        result["categoria"] = match

    unidad = str(data.get("unidad") or "").strip()
    match = next((item for item in UNIDADES if item.casefold() == unidad.casefold()), None)
    if match:
        result["unidad"] = match

    if modo in ("photo", "voice"):
        quantity = data.get("cantidad")
        if not isinstance(quantity, bool):
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                quantity = 0
            if 0 < quantity <= 100000:
                result["cantidad"] = quantity

    if modo in ("barcode", "voice"):
        digits = "".join(character for character in str(data.get("codigo_barras") or "") if character.isdigit())
        if 8 <= len(digits) <= 14:
            result["codigo_barras"] = digits

    if modo == "barcode":
        source = _safe_url(data.get("fuente"))
        if source:
            result["fuente"] = source
        # RN-13: in Código only a public source may back price and expiration.
        if source:
            _add_price_and_expiration(data, result)
    elif modo == "voice":
        # RN-13: in Voz the dictation itself is the source; Gemini transcribes,
        # it never estimates a price or a shelf life.
        _add_price_and_expiration(data, result)

    return result


def _redact(detail):
    if GEMINI_API_KEY and GEMINI_API_KEY in detail:
        detail = detail.replace(GEMINI_API_KEY, "***")
    return detail[:300]


def extract_product_draft(modo, data, mime_type=None, codigo=None, duracion=None, categorias=None, modelo=None):
    """Validate media and return a sanitized editable draft.

    Photo and voice use Gemini. Barcode resolves the digits already processed by
    the browser against Open Food Facts: it never calls Google Search and never
    guesses a product from the digits alone.
    """
    raw, mime_type = _validate_mode(modo, data, mime_type, duracion)
    if modo in ("photo", "voice"):
        modelo = resolve_model(modelo)

    if modo == "barcode":
        code = _normalize_digits(codigo)
        if not code:
            raise MediaValidationError(
                "No se pudo leer el código de barras; escríbelo manualmente o sube una imagen legible."
            )
        product = _lookup_open_food_facts(code)
        if not product:
            return {
                "modo": modo,
                "campos": {"codigo_barras": code},
                "mensaje": "No se encontró en la base de datos. Regístralo manualmente.",
                "proveedor": "Open Food Facts",
            }
        fields = _sanitize(_fields_from_open_food_facts(product, code), modo, categorias)
        return {
            "modo": modo,
            "campos": fields,
            "mensaje": "Datos obtenidos de Open Food Facts; revisa y corrige antes de guardar.",
            "proveedor": "Open Food Facts",
        }

    if not GEMINI_API_KEY:
        raise AIUnavailable("La IA no está configurada en el servidor")

    request = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(_request_body(modo, raw, mime_type, categorias, modelo)).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", "replace").strip()
        except (OSError, ValueError):
            pass
        message = f"El proveedor de IA devolvió {error.code}"
        detail = _redact(detail)
        if detail:
            message += f": {detail}"
        raise AIUnavailable(message) from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise AIUnavailable("No se pudo contactar al proveedor de IA") from error

    fields = _sanitize(_parse_json(_extract_text(payload)), modo, categorias)
    mensaje = (
        "Datos preliminares obtenidos; revisa y corrige antes de guardar."
        if fields
        else "No pudimos identificar datos útiles. Completa el formulario manualmente."
    )
    return {"modo": modo, "campos": fields, "mensaje": mensaje, "proveedor": modelo}
