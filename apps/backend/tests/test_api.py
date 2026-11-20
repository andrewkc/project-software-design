import os
import tempfile

os.environ["BODEGA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "bodega-test.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def signup_jefe(client, email="jefe@test.com"):
    response = client.post("/auth/signup", json={
        "nombres": "Ana",
        "apellidos": "Perez",
        "email": email,
        "password": "clave-segura-123",
        "store": "Bodega Central",
    })
    assert response.status_code == 201
    return response.json()["token"]


def test_signup_login_and_me(client):
    token = signup_jefe(client)
    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["role"] == "jefe"

    login = client.post("/auth/login", json={"email": "jefe@test.com", "password": "clave-segura-123"})
    assert login.status_code == 200
    assert login.json()["profile"]["name"] == "Ana Perez"


def test_employee_creation_and_revocation(client):
    jefe_token = signup_jefe(client, "jefe-emp@test.com")
    created = client.post("/profiles/employees", headers=auth(jefe_token), json={
        "nombres": "Juan",
        "apellidos": "Lopez",
        "email": "juan@test.com",
        "password": "clave-empleado-1",
    })
    assert created.status_code == 201
    employee = created.json()

    product = client.post("/products", headers=auth(jefe_token), json={
        "name": "Leche", "category": "Lácteos", "stock": 4, "unit": "unid.", "price": 5,
    })
    assert product.status_code == 201
    product_id = product.json()["id"]

    revoked = client.post(f"/profiles/employees/{employee['id']}/revoke", headers=auth(jefe_token))
    assert revoked.status_code == 200
    assert revoked.json()["activo"] is False

    products = client.get("/products", headers=auth(jefe_token)).json()
    assert next(item for item in products if item["id"] == product_id)["bloqueado"] is True

    login = client.post("/auth/login", json={"email": "juan@test.com", "password": "clave-empleado-1"})
    assert login.status_code == 403


def test_exit_rejects_insufficient_stock_without_changing_it(client):
    token = signup_jefe(client, "jefe-stock@test.com")
    product = client.post("/products", headers=auth(token), json={
        "name": "Arroz", "category": "Abarrotes", "stock": 2, "unit": "kg", "price": 4,
    }).json()
    products = client.get("/products", headers=auth(token)).json()
    assert next(item for item in products if item["id"] == product["id"])["stock"] == 2

    # El lote inicial se consulta con SQL directo porque la API no expone lotes todavía.
    from app.db import connect
    with connect() as conn:
        lot_id = conn.execute("SELECT id FROM lots WHERE product_id = ?", (product["id"],)).fetchone()["id"]

    response = client.post("/movements", headers=auth(token), json={
        "tipo": "salida",
        "motivo": "Venta",
        "items": [{"productoId": product["id"], "loteId": lot_id, "cantidad": 9}],
    })
    assert response.status_code == 400
    products = client.get("/products", headers=auth(token)).json()
    assert next(item for item in products if item["id"] == product["id"])["stock"] == 2
