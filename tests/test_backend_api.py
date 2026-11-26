"""HTTP integration tests for the BodeSmart API.

Start the backend and set DATABASE_URL (used only to clean up the rows
created by the tests) before running:

    python -m pytest tests/test_backend_api.py -v

Environment:
    API_BASE_URL        default http://127.0.0.1:8000
    TEST_JEFE_EMAIL     default kelvin.andrei.cc@gmail.com
    TEST_JEFE_PASSWORD  default Kelvin123456
    DATABASE_URL        same DSN used by the backend; enables cleanup

Do not commit real credentials. The defaults are the prototype seed values.
"""

import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
JEFE_EMAIL = os.getenv("TEST_JEFE_EMAIL", "kelvin.andrei.cc@gmail.com")
JEFE_PASSWORD = os.getenv("TEST_JEFE_PASSWORD", "Kelvin123456")
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=API_BASE, timeout=30) as http:
        try:
            http.get("/health")
        except httpx.ConnectError:
            pytest.fail(f"No se puede conectar con el backend en {API_BASE}. Arranca uvicorn antes de correr las pruebas.")
        yield http


@pytest.fixture
def jefe_headers(client):
    response = client.post("/auth/login", json={"correo": JEFE_EMAIL, "password": JEFE_PASSWORD})
    assert response.status_code == 200, f"Login del jefe falló: {response.status_code} {response.text}"
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def created():
    state = {"product_ids": [], "employee_emails": [], "jefe_emails": [], "bodegas": [], "categories": []}
    yield state
    if not DATABASE_URL:
        return
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        for product_id in state["product_ids"]:
            conn.execute("DELETE FROM ProductosBodega WHERE id_producto = %s", (product_id,))
            conn.execute("DELETE FROM Producto WHERE id = %s", (product_id,))
        for email in state["employee_emails"]:
            conn.execute("DELETE FROM Empleado WHERE lower(correo) = lower(%s)", (email,))
        for email in state["jefe_emails"]:
            conn.execute("DELETE FROM Jefe WHERE lower(correo) = lower(%s)", (email,))
        for name in state["bodegas"]:
            conn.execute("DELETE FROM Bodega WHERE nombre = %s", (name,))
        for name in state["categories"]:
            conn.execute("DELETE FROM Categoria WHERE nombre = %s", (name,))


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me(client, jefe_headers):
    response = client.get("/auth/me", headers=jefe_headers)
    assert response.status_code == 200
    perfil = response.json()
    assert perfil["rol"] == "jefe"
    assert perfil["correo"].lower() == JEFE_EMAIL.lower()


def test_login_rejects_wrong_password(client):
    response = client.post("/auth/login", json={"correo": JEFE_EMAIL, "password": "clave-incorrecta"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_products_list(client, jefe_headers):
    response = client.get("/products", headers=jefe_headers)
    assert response.status_code == 200
    products = response.json()
    assert products, "El seed debería cargar productos en la bodega"
    required = {"id", "nombre", "stock", "precio_venta", "estado", "creado_por", "bloqueado"}
    assert required.issubset(products[0])


def test_categories_can_grow_and_are_reused(client, jefe_headers, created):
    suffix = uuid.uuid4().hex[:8]
    name = f"Categoría test {suffix}"
    created["categories"].append(name)

    response = client.post("/categories", headers=jefe_headers, json={"nombre": f"  {name}  "})
    assert response.status_code == 200, response.text
    assert response.json()["nombre"] == name

    listed = client.get("/categories", headers=jefe_headers)
    assert listed.status_code == 200
    assert name in listed.json()

    repeated = client.post("/categories", headers=jefe_headers, json={"nombre": name.lower()})
    assert repeated.status_code == 200
    assert repeated.json()["nombre"] == name

    product = client.post("/products", headers=jefe_headers, json={
        "nombre": f"Producto categoría {suffix}",
        "categoria": name,
        "stock": 2,
    })
    assert product.status_code == 200, product.text
    created["product_ids"].append(product.json()["id"])
    assert product.json()["categoria"] == name


def test_profiles_list_as_jefe(client, jefe_headers):
    response = client.get("/profiles", headers=jefe_headers)
    assert response.status_code == 200
    assert any(profile["rol"] == "jefe" for profile in response.json())


def test_ai_models_are_allowlisted_and_key_free(client, jefe_headers):
    response = client.get("/ai/models", headers=jefe_headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["default"]
    assert any(model["activo"] and model["id"] == data["default"] for model in data["modelos"])
    assert all(set(model) == {"id", "label", "activo"} for model in data["modelos"])
    assert "clave" not in data
    assert "key" not in data


def test_extract_rejects_model_outside_allowlist(client, jefe_headers):
    response = client.post("/products/extract", headers=jefe_headers, json={
        "modo": "photo",
        "data": "aW1hZ2VuLXNpbnRldGljYQ==",
        "mime_type": "image/jpeg",
        "modelo": "gemini-fuera-de-lista",
    })
    assert response.status_code == 400, response.text
    assert "no permitido" in response.json()["detail"]


def test_signup(client, created):
    suffix = uuid.uuid4().hex[:8]
    email = f"jefe.test.{suffix}@example.com"
    store = f"Bodega test {suffix}"
    response = client.post("/auth/signup", json={
        "nombres": "Jefe",
        "apellidos": "Prueba",
        "correo": email,
        "password": "ClaveJefe123",
        "nombre_bodega": store,
    })
    assert response.status_code == 200, response.text
    assert response.json()["perfil"]["rol"] == "jefe"
    assert response.json()["token"]
    created["jefe_emails"].append(email)
    created["bodegas"].append(store)


def test_create_and_patch_product(client, jefe_headers, created):
    suffix = uuid.uuid4().hex[:8]
    response = client.post("/products", headers=jefe_headers, json={
        "nombre": f"Producto test {suffix}",
        "categoria": "Abarrotes",
        "icono": "🧪",
        "unidad_medida": "unid.",
        "stock": 7,
        "precio_venta": 3.5,
        "fecha_vencimiento": None,
    })
    assert response.status_code == 200, response.text
    product = response.json()
    created["product_ids"].append(product["id"])
    assert product["stock"] == 7

    patched = client.patch(
        f"/products/{product['id']}",
        headers=jefe_headers,
        json={"stock": 9, "precio_venta": 4.25},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["stock"] == 9
    assert body["precio_venta"] == 4.25


def test_employee_permissions_and_revoke(client, jefe_headers, created):
    suffix = uuid.uuid4().hex[:8]
    email = f"empleado.test.{suffix}@example.com"
    password = "ClaveEmpleado123"
    new_password = "ClaveNueva123"

    response = client.post("/profiles/employees", headers=jefe_headers, json={
        "nombres": "Empleado",
        "apellidos": "Prueba",
        "correo": email,
        "password": password,
    })
    assert response.status_code == 200, response.text
    employee_id = response.json()["id"]
    created["employee_emails"].append(email)

    login = client.post("/auth/login", json={"correo": email, "password": password})
    assert login.status_code == 200, login.text
    employee_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    assert client.get("/profiles", headers=employee_headers).status_code == 403

    own = client.post("/products", headers=employee_headers, json={
        "nombre": f"Prueba empleado {suffix}",
        "stock": 2,
    })
    assert own.status_code == 200, own.text
    product_id = own.json()["id"]
    created["product_ids"].append(product_id)

    listed = client.get("/products", headers=employee_headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == product_id for item in listed.json())

    edited = client.patch(f"/products/{product_id}", headers=employee_headers, json={"stock": 3})
    assert edited.status_code == 200, edited.text

    locked = client.patch(f"/products/{product_id}", headers=jefe_headers, json={"bloqueado": True})
    assert locked.status_code == 200, locked.text
    assert locked.json()["bloqueado"] is True
    denied = client.patch(f"/products/{product_id}", headers=employee_headers, json={"stock": 4})
    assert denied.status_code == 403

    invalid_extract = client.post("/products/extract", headers=employee_headers, json={
        "modo": "photo",
        "data": "data:application/pdf;base64,Zg==",
        "mime_type": "application/pdf",
    })
    assert invalid_extract.status_code == 400, invalid_extract.text

    changed = client.post("/auth/change-password", headers=employee_headers, json={
        "password_actual": password,
        "password_nueva": new_password,
    })
    assert changed.status_code == 200, changed.text
    assert client.post("/auth/login", json={"correo": email, "password": new_password}).status_code == 200

    revoked = client.post(f"/profiles/employees/{employee_id}/revoke", headers=jefe_headers)
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["activo"] is False
    assert client.post("/auth/login", json={"correo": email, "password": new_password}).status_code == 403


def test_recommendations_are_jefe_only(client, jefe_headers, created):
    suffix = uuid.uuid4().hex[:8]
    email = f"empleado.ia.{suffix}@example.com"
    password = "ClaveEmpleado123"
    response = client.post("/profiles/employees", headers=jefe_headers, json={
        "nombres": "Empleado",
        "apellidos": "IA",
        "correo": email,
        "password": password,
    })
    assert response.status_code == 200, response.text
    created["employee_emails"].append(email)

    login = client.post("/auth/login", json={"correo": email, "password": password})
    assert login.status_code == 200, login.text
    employee_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    denied = client.post("/recommendations/generate", headers=employee_headers)
    assert denied.status_code == 403
    assert "jefe" in denied.json()["detail"]


def test_recommendations_do_not_mutate_products(client, jefe_headers):
    before = client.get("/products", headers=jefe_headers).json()
    response = client.post("/recommendations/generate", headers=jefe_headers)
    after = client.get("/products", headers=jefe_headers).json()

    assert after == before, "Generar recomendaciones no debe cambiar precios ni stock"


def test_sales_history_contains_only_paid_purchases(client, jefe_headers):
    response = client.get("/sales", headers=jefe_headers)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert rows, "El backend debe sembrar las tres compras demo pagadas"
    for row in rows:
        assert row["estado"] == "pagado"
        assert row["cliente"]
        assert row["fechaPago"]
        assert row["lineas"]
        for line in row["lineas"]:
            assert line["cantidad"] > 0
            assert float(line["precioUnitario"]) > 0


def test_sales_reject_unauthenticated_and_client_role(client):
    assert client.get("/sales").status_code == 401
    backend = str(Path(__file__).resolve().parents[1] / "apps" / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from security import create_token  # noqa: E402

    buyer_headers = {"Authorization": f"Bearer {create_token(1, 'cliente')}"}
    assert client.get("/sales", headers=buyer_headers).status_code == 403
    assert client.post("/sales", headers=buyer_headers, json={}).status_code == 403


def test_employee_can_read_sales(client, jefe_headers, created):
    suffix = uuid.uuid4().hex[:8]
    email = f"empleado.ventas.{suffix}@example.com"
    password = "ClaveEmpleado123"
    created["employee_emails"].append(email)
    response = client.post("/profiles/employees", headers=jefe_headers, json={
        "nombres": "Empleado",
        "apellidos": "Ventas",
        "correo": email,
        "password": password,
    })
    assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"correo": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    listed = client.get("/sales", headers=headers)
    assert listed.status_code == 200, listed.text
    assert isinstance(listed.json(), list)


def test_sale_over_available_stock_is_rejected_without_mutating(client, jefe_headers):
    before = client.get("/products", headers=jefe_headers).json()
    sales = client.get("/sales", headers=jefe_headers).json()
    client_id = sales[0]["clienteId"]
    # Arroz extra: activo, vencimiento futuro y stock sembrado suficiente para
    # que el único motivo del rechazo sea la cantidad.
    product_id = 4
    assert any(item["id"] == product_id for item in before)
    response = client.post("/sales", headers=jefe_headers, json={
        "id_cliente": client_id,
        "lineas": [{"id_producto": product_id, "cantidad": 1_000_000}],
    })
    assert response.status_code == 409, response.text
    after = client.get("/products", headers=jefe_headers).json()
    assert after == before, "Una venta rechazada no debe descontar stock ni crear la compra"
    if response.status_code == 503 and "no está configurada" in response.text:
        pytest.skip("GEMINI_API_KEY no configurada; el inventario sigue disponible")

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"generadas_en", "modelo", "recomendaciones", "aviso"}
    assert "no genera" in body["aviso"]
    assert "no modifica inventario" in body["aviso"]

    known = {product["id"]: product for product in before}
    for item in body["recomendaciones"]:
        assert item["id_producto"] in known
        assert item["icono"]
        assert item["tipo"] in {"descuento", "aumento", "reposicion"}
        assert item["justificacion"]
        if item["tipo"] == "reposicion":
            assert item["cantidad_sugerida"] > 0
        else:
            current = known[item["id_producto"]]["precio_venta"]
            assert item["precio_sugerido"] > 0
            if item["tipo"] == "descuento":
                assert item["precio_sugerido"] < current
            else:
                assert item["precio_sugerido"] > current


def test_registered_extraction_rejects_invalid_media_without_mutating(client, jefe_headers):
    before = client.get("/products", headers=jefe_headers).json()
    response = client.post("/products/extract", headers=jefe_headers, json={
        "modo": "photo",
        "data": "data:application/pdf;base64,Zg==",
        "mime_type": "application/pdf",
    })
    after = client.get("/products", headers=jefe_headers).json()

    assert response.status_code == 400, response.text
    assert after == before, "La extracción inválida no debe crear ni modificar productos"
