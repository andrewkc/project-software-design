"""Unit and static checks for advisory Gemini recommendations.

Run from the repository root with the backend venv:
    apps\\backend\\.venv\\Scripts\\python -m pytest tests/test_ai_recommendations.py -v

No API key, server or database is required: the provider call is not executed.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
FRONTEND_SRC = ROOT / "apps" / "operations-web" / "src"

sys.path.insert(0, str(BACKEND))
import ai  # noqa: E402


@pytest.fixture
def products():
    return [
        {
            "id": 1,
            "nombre": "Yogurt natural",
            "icono": "🥛",
            "categoria": "Lácteos",
            "stock": 2,
            "precio_venta": 8.0,
            "fecha_vencimiento": "2026-11-28",
            "estado": "activo",
        },
        {
            "id": 2,
            "nombre": "Arroz extra",
            "icono": "🍚",
            "categoria": "Abarrotes",
            "stock": 20,
            "precio_venta": 4.5,
            "fecha_vencimiento": None,
            "estado": "activo",
        },
    ]


def test_sanitize_keeps_only_consistent_suggestions(products):
    items = [
        {"id_producto": 1, "tipo": "descuento", "precio_sugerido": 6.5, "justificacion": "Vence pronto."},
        {"id_producto": 2, "tipo": "aumento", "precio_sugerido": 5.0, "justificacion": "Stock alto."},
        {"id_producto": 2, "tipo": "reposicion", "cantidad_sugerida": 3, "justificacion": "Reponer referencia."},
        {"id_producto": 1, "tipo": "descuento", "precio_sugerido": 9.0, "justificacion": "Precio mayor."},
        {"id_producto": 2, "tipo": "aumento", "precio_sugerido": 4.0, "justificacion": "Precio menor."},
        {"id_producto": 2, "tipo": "reposicion", "cantidad_sugerida": 0, "justificacion": "Cero."},
        {"id_producto": 99, "tipo": "descuento", "precio_sugerido": 1.0, "justificacion": "Otra bodega."},
        {"id_producto": 1, "tipo": "inventado", "precio_sugerido": 1.0, "justificacion": "Tipo inválido."},
        {"id_producto": 1, "tipo": "descuento", "precio_sugerido": 1.0, "justificacion": "   "},
    ]

    result = ai._sanitize(items, products)

    assert [item["tipo"] for item in result] == ["descuento", "aumento", "reposicion"]
    assert result[0]["precio_actual"] == 8.0
    assert result[0]["precio_sugerido"] == 6.5
    assert result[0]["icono"] == "🥛"
    assert result[1]["precio_sugerido"] == 5.0
    assert result[1]["icono"] == "🍚"
    assert result[2]["stock_actual"] == 20
    assert result[2]["cantidad_sugerida"] == 3


def test_sanitize_caps_the_number_of_suggestions(products):
    items = [
        {
            "id_producto": 2,
            "tipo": "reposicion",
            "cantidad_sugerida": index + 1,
            "justificacion": f"Referencia {index}.",
        }
        for index in range(20)
    ]
    assert len(ai._sanitize(items, products)) == ai.MAX_RECOMENDACIONES


def test_request_body_sends_only_available_product_fields(products):
    body = ai._request_body(products)
    payload = json.loads(body["input"])

    assert body["model"] == ai.GEMINI_MODEL
    assert body["store"] is False
    assert body["response_format"]["mime_type"] == "application/json"
    assert set(payload[0]) == {
        "id_producto",
        "nombre",
        "categoria",
        "stock",
        "precio_venta",
        "fecha_vencimiento",
        "estado",
    }
    assert "costo" not in body["input"].lower()
    assert "margen" not in body["input"].lower()
    assert "historial" not in body["input"].lower()


def test_extract_text_accepts_rest_and_wrapped_responses():
    rest = {"steps": [{"content": [{"type": "text", "text": '{"recomendaciones": []}'}]}]}
    wrapped = {"interaction": {"output_text": '{"recomendaciones": []}'}}

    assert json.loads(ai._extract_text(rest)) == {"recomendaciones": []}
    assert json.loads(ai._extract_text(wrapped)) == {"recomendaciones": []}


def test_missing_api_key_fails_closed(products, monkeypatch):
    monkeypatch.setattr(ai, "GEMINI_API_KEY", "")
    with pytest.raises(ai.AIUnavailable, match="no está configurada"):
        ai.generate_recommendations(products)


def test_provider_error_includes_redacted_detail(products, monkeypatch):
    body = b'{"error":{"message":"Modelo no disponible para API key AIzaSECRETO"}}'

    def fake_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            503,
            "Service Unavailable",
            {},
            io.BytesIO(body),
        )

    monkeypatch.setattr(ai, "GEMINI_API_KEY", "AIzaSECRETO")
    monkeypatch.setattr(ai.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(ai.AIUnavailable) as caught:
        ai.generate_recommendations(products)

    message = str(caught.value)
    assert "503" in message
    assert "Modelo no disponible" in message
    assert "AIzaSECRETO" not in message
    assert "***" in message


def test_provider_key_crossing_truncation_limit_is_redacted(products, monkeypatch):
    key = "AIzaCLAVE"
    body = json.dumps({"error": {"message": "x" * 274 + key}}).encode()

    def fake_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            503,
            "Service Unavailable",
            {},
            io.BytesIO(body),
        )

    monkeypatch.setattr(ai, "GEMINI_API_KEY", key)
    monkeypatch.setattr(ai.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(ai.AIUnavailable) as caught:
        ai.generate_recommendations(products)

    message = str(caught.value)
    assert key not in message
    assert "***" in message


def test_ai_adapter_has_no_database_writes():
    source = (BACKEND / "ai.py").read_text(encoding="utf-8")
    assert "psycopg" not in source
    assert "INSERT" not in source.upper()
    assert "UPDATE" not in source.upper()
    assert "DELETE" not in source.upper()


def test_recommendations_ui_keeps_state_and_shows_product_icon():
    app = (FRONTEND_SRC / "App.jsx").read_text(encoding="utf-8")
    page = (FRONTEND_SRC / "features" / "recommendations" / "RecommendationsPage.jsx").read_text(encoding="utf-8")
    styles = (FRONTEND_SRC / "styles.css").read_text(encoding="utf-8")

    assert "const [recommendations, setRecommendations] = useState" in app
    assert "recommendations={recommendations}" in app
    assert "onRecommendationsChange={setRecommendations}" in app
    assert "Volver a generar recomendaciones" in page
    assert "button-soft" in page
    assert ".button-soft" in styles
    assert "item.icono" in page
    assert ".recommendation-icon" in styles


def test_frontend_never_reads_the_gemini_key():
    files = [*FRONTEND_SRC.rglob("*.js"), *FRONTEND_SRC.rglob("*.jsx")]
    offenders = [
        str(path.relative_to(ROOT))
        for path in files
        if "GEMINI_API_KEY" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"La clave no debe llegar al navegador: {offenders}"
