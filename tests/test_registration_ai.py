"""Unit and static checks for assisted product registration (REG-IA).

Run from the repository root with the backend venv:
    apps\\backend\\.venv\\Scripts\\python -m pytest tests/test_registration_ai.py -v

No API key, server or database is required: the provider call is mocked.
"""

import base64
import io
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
FRONTEND_SRC = ROOT / "apps" / "operations-web" / "src"

sys.path.insert(0, str(BACKEND))
import registration_ai as registration  # noqa: E402


@pytest.fixture
def image_data():
    raw = b"imagen-sintetica-de-prueba"
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def test_photo_request_is_multimodal_and_restricted(image_data):
    body = registration._request_body("photo", b"imagen", "image/jpeg")

    assert body["model"] == registration.GEMINI_MODEL
    assert body["store"] is False
    assert "tools" not in body
    assert body["input"][0]["type"] == "text"
    assert body["input"][1] == {
        "type": "image",
        "data": base64.b64encode(b"imagen").decode("ascii"),
        "mime_type": "image/jpeg",
    }
    properties = body["response_format"]["schema"]["properties"]
    assert set(properties) == {"nombre", "icono", "categoria", "unidad", "cantidad"}
    assert "precio_venta" not in properties
    assert "fecha_vencimiento" not in properties


def test_request_body_uses_selected_allowlisted_model():
    alternates = [model for model in registration.GEMINI_ALLOWED_MODELS if model != registration.GEMINI_MODEL]
    assert alternates, "La allowlist debe incluir al menos un modelo alterno para el selector."
    body = registration._request_body("photo", b"imagen", "image/jpeg", modelo=alternates[0])

    assert body["model"] == alternates[0]
    assert body["model"] != registration.GEMINI_MODEL


def test_resolve_model_rejects_unknown_model():
    with pytest.raises(registration.ModelNotAllowed, match="Modelo de IA no permitido"):
        registration.resolve_model("gemini-fuera-de-lista")

    assert registration.resolve_model(None) == registration.GEMINI_MODEL
    assert registration.resolve_model("  ") == registration.GEMINI_MODEL


def test_extract_reports_the_selected_model(image_data, monkeypatch):
    alternate = next(
        model for model in registration.GEMINI_ALLOWED_MODELS if model != registration.GEMINI_MODEL
    )
    seen = {}

    class FakeResponse:
        def __enter__(self):
            payload = {"output_text": json.dumps({"nombre": "Mandarina sintética"})}
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        assert request.get_header("x-goog-api-key")
        return FakeResponse()

    monkeypatch.setattr(registration, "GEMINI_API_KEY", "AIzaMODELOPRUEBA")
    monkeypatch.setattr(registration.urllib.request, "urlopen", fake_urlopen)

    result = registration.extract_product_draft("photo", image_data, "image/jpeg", modelo=alternate)

    assert seen["body"]["model"] == alternate
    assert result["proveedor"] == alternate
    assert result["campos"]["nombre"] == "Mandarina sintética"


def test_barcode_uses_open_food_facts_without_google_search():
    source = (BACKEND / "registration_ai.py").read_text(encoding="utf-8")

    assert "google_search" not in source
    assert "world.openfoodfacts.org/api/v2/product" in source
    assert "barcode" not in registration.PROMPTS


def test_voice_request_uses_audio_block_and_all_dictated_fields():
    body = registration._request_body("voice", b"audio", "audio/webm", ["Panadería"])

    assert body["input"][1]["type"] == "audio"
    assert body["input"][1]["mime_type"] == "audio/webm"
    assert "tools" not in body
    assert "Panadería" in body["input"][0]["text"]
    properties = body["response_format"]["schema"]["properties"]
    assert set(properties) == {
        "nombre", "icono", "categoria", "unidad", "cantidad",
        "precio_venta", "fecha_vencimiento", "codigo_barras",
    }
    prompt = body["input"][0]["text"]
    assert "no los estimes" in prompt
    assert "vida útil" in prompt

    photo = registration._request_body("photo", b"imagen", "image/jpeg", ["Panadería"])
    assert "Panadería" in photo["input"][0]["text"]
    assert "precio_venta" not in photo["response_format"]["schema"]["properties"]


def test_media_validation_rejects_unsupported_types_and_large_files(image_data):
    with pytest.raises(registration.MediaValidationError, match="audio"):
        registration._validate_mode("voice", image_data, "image/jpeg", None)

    with pytest.raises(registration.MediaValidationError, match="60 segundos"):
        registration._validate_mode("voice", "data:audio/webm;base64,YQ==", "audio/webm", 90)

    with pytest.raises(registration.MediaValidationError, match="Modo"):
        registration._validate_mode("unknown", image_data, "image/jpeg", None)


def test_decode_media_accepts_data_url_and_plain_base64(image_data):
    raw, mime = registration._decode_media(image_data, None)
    assert raw == b"imagen-sintetica-de-prueba"
    assert mime == "image/jpeg"

    raw, mime = registration._decode_media(base64.b64encode(b"audio").decode("ascii"), "audio/webm;codecs=opus")
    assert raw == b"audio"
    assert mime == "audio/webm"


def test_sanitize_photo_keeps_only_observable_fields():
    data = {
        "nombre": "  Yogurt   natural  ",
        "icono": "🥛",
        "categoria": "Lácteos",
        "unidad": "unid.",
        "cantidad": 6,
        "precio_venta": 8.5,
        "fecha_vencimiento": "2999-01-01",
        "codigo_barras": "7750182003412",
    }

    assert registration._sanitize(data, "photo") == {
        "nombre": "Yogurt natural",
        "icono": "🥛",
        "categoria": "Lácteos",
        "unidad": "unid.",
        "cantidad": 6,
    }


def test_sanitize_voice_transcribes_every_dictated_field():
    data = {
        "nombre": "  Yogurt   natural  ",
        "icono": "🥛",
        "categoria": "Lácteos",
        "unidad": "unid.",
        "cantidad": 6,
        "precio_venta": "8.50",
        "fecha_vencimiento": "2999-01-01",
        "codigo_barras": "7750-182-003412",
    }

    assert registration._sanitize(data, "voice") == {
        "nombre": "Yogurt natural",
        "icono": "🥛",
        "categoria": "Lácteos",
        "unidad": "unid.",
        "cantidad": 6,
        "precio_venta": 8.5,
        "fecha_vencimiento": "2999-01-01",
        "codigo_barras": "7750182003412",
    }


def test_sanitize_accepts_persisted_categories_outside_base_list():
    data = {"nombre": "Pan artesanal", "categoria": "Panadería casera"}

    result = registration._sanitize(data, "voice", ["Bebidas", "Panadería casera"])

    assert result == {"nombre": "Pan artesanal", "categoria": "Panadería casera"}
    assert registration._sanitize(data, "voice") == {"nombre": "Pan artesanal"}


def test_sanitize_barcode_keeps_optional_public_fields_only():
    data = {
        "nombre": "Yogurt natural",
        "icono": "🥛",
        "categoria": "lácteos",
        "unidad": "unid.",
        "cantidad": 6,
        "codigo_barras": "7750-182-003412",
        "precio_venta": "8.50",
        "fecha_vencimiento": "2999-01-01",
        "fuente": "https://ejemplo.com/producto",
    }

    result = registration._sanitize(data, "barcode")

    assert result["categoria"] == "Lácteos"
    assert result["codigo_barras"] == "7750182003412"
    assert result["precio_venta"] == 8.5
    assert result["fecha_vencimiento"] == "2999-01-01"
    assert result["fuente"] == "https://ejemplo.com/producto"
    assert "cantidad" not in result


def test_sanitize_barcode_drops_price_and_expiration_without_public_source():
    data = {
        "nombre": "Yogurt natural",
        "precio_venta": 8.5,
        "fecha_vencimiento": "2999-01-01",
    }

    assert registration._sanitize(data, "barcode") == {"nombre": "Yogurt natural"}
    # In Voz the dictation itself is the source; these values are transcribed,
    # not estimated by the assistant (RN-13).
    assert registration._sanitize(data, "voice") == {
        "nombre": "Yogurt natural",
        "precio_venta": 8.5,
        "fecha_vencimiento": "2999-01-01",
    }


def test_sanitize_drops_invalid_values():
    result = registration._sanitize(
        {
            "nombre": "   ",
            "icono": "🚀",
            "categoria": "Inexistente",
            "unidad": "tonelada",
            "cantidad": -2,
            "codigo_barras": "abc",
            "precio_venta": -1,
            "fecha_vencimiento": "2020-01-01",
            "fuente": "javascript:alert(1)",
        },
        "barcode",
    )

    assert result == {}


def test_barcode_finds_product_in_open_food_facts(image_data, monkeypatch):
    product = {
        "code": "7750182003412",
        "product_name_es": "Yogurt natural",
        "categories": "Milk and yogurt products",
        "quantity": "1 L",
        "url": "https://world.openfoodfacts.org/product/7750182003412",
    }
    payload = {"status": 1, "product": product}

    class FakeResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        assert "world.openfoodfacts.org/api/v2/product/7750182003412" in request.full_url
        assert request.get_header("User-agent")
        assert timeout == 15
        return FakeResponse()

    monkeypatch.setattr(registration, "GEMINI_API_KEY", "")
    monkeypatch.setattr(registration.urllib.request, "urlopen", fake_urlopen)

    result = registration.extract_product_draft("barcode", image_data, "image/jpeg", "775-0182-003412")

    assert result["modo"] == "barcode"
    assert result["proveedor"] == "Open Food Facts"
    assert result["campos"] == {
        "nombre": "Yogurt natural",
        "icono": "🥛",
        "categoria": "Lácteos",
        "unidad": "litro",
        "codigo_barras": "7750182003412",
        "fuente": "https://world.openfoodfacts.org/product/7750182003412",
    }
    assert "precio_venta" not in result["campos"]
    assert "fecha_vencimiento" not in result["campos"]
    assert "cantidad" not in result["campos"]
    assert "revisa" in result["mensaje"]


def test_barcode_not_found_asks_for_manual_registration(image_data, monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps({"status": 0, "status_verbose": "product not found"}).encode("utf-8"))

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(registration.urllib.request, "urlopen", lambda _request, timeout: FakeResponse())

    result = registration.extract_product_draft("barcode", image_data, "image/jpeg", "7750182003412")

    assert result["campos"] == {"codigo_barras": "7750182003412"}
    assert result["mensaje"] == "No se encontró en la base de datos. Regístralo manualmente."


def test_barcode_without_digits_fails_closed(image_data):
    with pytest.raises(registration.MediaValidationError, match="escríbelo manualmente"):
        registration.extract_product_draft("barcode", image_data, "image/jpeg", "")


def test_missing_key_fails_closed(image_data, monkeypatch):
    monkeypatch.setattr(registration, "GEMINI_API_KEY", "")
    with pytest.raises(registration.AIUnavailable, match="no está configurada"):
        registration.extract_product_draft("photo", image_data, "image/jpeg")


def test_provider_error_is_redacted(image_data, monkeypatch):
    body = b'{"error":{"message":"Fallo con clave AIzaSECRETO"}}'

    def fake_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            registration.GEMINI_API_URL, 503, "Service Unavailable", {}, io.BytesIO(body)
        )

    monkeypatch.setattr(registration, "GEMINI_API_KEY", "AIzaSECRETO")
    monkeypatch.setattr(registration.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(registration.AIUnavailable) as caught:
        registration.extract_product_draft("photo", image_data, "image/jpeg")

    message = str(caught.value)
    assert "503" in message
    assert "Fallo con clave" in message
    assert "AIzaSECRETO" not in message
    assert "***" in message


def test_key_crossing_truncation_limit_is_redacted(image_data, monkeypatch):
    key = "AIzaCLAVE"
    body = json.dumps({"error": {"message": "x" * 274 + key}}).encode()

    def fake_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            registration.GEMINI_API_URL, 503, "Service Unavailable", {}, io.BytesIO(body)
        )

    monkeypatch.setattr(registration, "GEMINI_API_KEY", key)
    monkeypatch.setattr(registration.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(registration.AIUnavailable) as caught:
        registration.extract_product_draft("photo", image_data, "image/jpeg")

    message = str(caught.value)
    assert key not in message
    assert "***" in message


def test_shared_endpoint_default_supports_inline_media():
    config_source = (BACKEND / "config.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "https://generativelanguage.googleapis.com/v1beta/interactions" in config_source
    assert "https://generativelanguage.googleapis.com/v1beta/interactions" in compose


def test_adapter_has_no_database_writes():
    source = (BACKEND / "registration_ai.py").read_text(encoding="utf-8")
    assert "psycopg" not in source
    assert "INSERT" not in source.upper()
    assert "UPDATE" not in source.upper()
    assert "DELETE" not in source.upper()


def test_voice_drops_invalid_dictated_values():
    result = registration._sanitize(
        {
            "nombre": "   ",
            "precio_venta": -1,
            "fecha_vencimiento": "2020-01-01",
            "codigo_barras": "abc",
        },
        "voice",
    )

    assert result == {}


def test_frontend_and_backend_icon_catalogs_match():
    modal = (FRONTEND_SRC / "features" / "products" / "ProductModal.jsx").read_text(encoding="utf-8")
    frontend_icons = set(re.findall(r'emoji: "([^"]+)"', modal))

    assert len(frontend_icons) > 100
    assert frontend_icons == set(registration.ICONOS)


def test_barcode_button_alternates_between_photo_and_camera():
    modal = (FRONTEND_SRC / "features" / "products" / "ProductModal.jsx").read_text(encoding="utf-8")

    assert "if (!cameraReady || !videoRef.current)" in modal
    assert "await restartCamera()" in modal
    assert 'cameraReady ? "Usar imagen del código" : "Encender cámara"' in modal
    assert "BarcodeDetector" in modal


def test_frontend_uses_real_capture_and_editable_draft():
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")
    modal = (FRONTEND_SRC / "features" / "products" / "ProductModal.jsx").read_text(encoding="utf-8")
    page = (FRONTEND_SRC / "features" / "register" / "RegisterPage.jsx").read_text(encoding="utf-8")
    hook = (FRONTEND_SRC / "features" / "products" / "useProductDraft.js").read_text(encoding="utf-8")

    assert 'extractProduct: (payload) => request("/products/extract"' in api
    assert "MediaRecorder" in modal
    assert "readAsDataURL" in modal
    assert "google_search" not in modal
    assert "defaultValue=" not in modal
    assert "Yogurt natural" not in modal
    assert "onSubmit(value)" in modal
    assert "applyFields(result.campos" in hook
    assert "Open Food Facts" in hook
    assert "handleMedia(\"barcode\"" in page
    assert "Open Food Facts" in page
    assert "handleMedia(\"voice\"" in page
    assert "Agregar nueva categoría" in modal
    assert "onCreateCategory" in modal
    assert "precio_venta: \"price\"" in hook
    assert "fecha_vencimiento: \"expires\"" in hook


def test_model_selector_is_allowlisted_and_key_free():
    config_source = (BACKEND / "config.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    router = (BACKEND / "routers" / "registration.py").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")
    hook = (FRONTEND_SRC / "features" / "products" / "useProductDraft.js").read_text(encoding="utf-8")
    picker = (FRONTEND_SRC / "features" / "products" / "AiModelPicker.jsx").read_text(encoding="utf-8")
    page = (FRONTEND_SRC / "features" / "register" / "RegisterPage.jsx").read_text(encoding="utf-8")
    modal = (FRONTEND_SRC / "features" / "products" / "ProductModal.jsx").read_text(encoding="utf-8")

    assert "GEMINI_ALLOWED_MODELS" in config_source
    assert "GEMINI_ALLOWED_MODELS" in compose
    assert '@router.get("/ai/models")' in router
    assert 'modelo=body.get("modelo")' in router
    assert "listAiModels" in api
    assert 'request("/ai/models")' in api
    assert "aiModel" in hook
    assert "...(modelo ? { modelo } : {})" in hook
    assert "Solo modelos permitidos por el servidor" in picker
    assert "AiModelPicker" in page
    assert "AiModelPicker" in modal
    assert "GEMINI_API_KEY" not in picker
    assert "generativelanguage.googleapis.com" not in picker


def test_categories_are_persisted_and_exposed_to_the_ui():
    schema = (ROOT / "apps" / "database" / "database.sql").read_text(encoding="utf-8")
    seed = (ROOT / "apps" / "database" / "seed.sql").read_text(encoding="utf-8")
    database = (BACKEND / "database.py").read_text(encoding="utf-8")
    products = (BACKEND / "routers" / "products.py").read_text(encoding="utf-8")
    main = (BACKEND / "main.py").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")

    assert "CREATE TABLE Categoria" in schema
    assert "INSERT INTO Categoria (nombre) VALUES" in seed
    assert "CREATE TABLE IF NOT EXISTS Categoria" in database
    assert "SELECT DISTINCT ON (clave) nombre" in database
    assert "ensure_category" in products
    assert "categories.router" in main
    assert "listCategories" in api
    assert "createCategory" in api


def test_frontend_never_reads_the_gemini_key():
    offenders = [
        str(path.relative_to(ROOT))
        for path in FRONTEND_SRC.rglob("*")
        if path.suffix in (".js", ".jsx") and "GEMINI_API_KEY" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"La clave no debe llegar al navegador: {offenders}"
