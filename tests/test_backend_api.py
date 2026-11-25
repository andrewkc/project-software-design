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
import uuid

import httpx
import pytest

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
JEFE_EMAIL = os.getenv("TEST_JEFE_EMAIL", "kelvin.andrei.cc@gmail.com")
JEFE_PASSWORD = os.getenv("TEST_JEFE_PASSWORD", "Kelvin123456")
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=API_BASE, timeout=15) as http:
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
    state = {"product_ids": [], "employee_emails": [], "jefe_emails": [], "bodegas": []}
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


def test_profiles_list_as_jefe(client, jefe_headers):
    response = client.get("/profiles", headers=jefe_headers)
    assert response.status_code == 200
    assert any(profile["rol"] == "jefe" for profile in response.json())


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
