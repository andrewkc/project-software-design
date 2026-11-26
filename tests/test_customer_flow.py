"""Customer checkout integration checks on an explicitly selected test database.

Run from the repository root with both variables pointing to the same
disposable local database:

    DATABASE_URL=postgresql://.../bodesmart_test ^
    BODESMART_TEST_DATABASE_URL=postgresql://.../bodesmart_test ^
    python -m pytest tests/test_customer_flow.py -v

Without the explicit opt-in the module is skipped, so the default test run
never touches a developer's real database.
"""

import hashlib
import hmac
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
import sys  # noqa: E402

sys.path.insert(0, str(BACKEND))

test_dsn = os.getenv("BODESMART_TEST_DATABASE_URL")
if not test_dsn or test_dsn != os.getenv("DATABASE_URL"):
    pytest.skip("Selecciona explícitamente una base local de pruebas", allow_module_level=True)

from main import app  # noqa: E402
from routers import customer  # noqa: E402


@pytest.fixture
def scenario():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:10]
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        store = conn.execute(
            "INSERT INTO Bodega(nombre,direccion) VALUES (%s,'Dirección de prueba') RETURNING id",
            (f"Tienda {suffix}",),
        ).fetchone()["id"]
        other_store = conn.execute(
            "INSERT INTO Bodega(nombre,direccion) VALUES (%s,'Otra dirección') RETURNING id",
            (f"Otra {suffix}",),
        ).fetchone()["id"]
        products, offers = [], []
        for store_id in (store, other_store):
            product = conn.execute(
                "INSERT INTO Producto(nombre,categoria,icono,unidad_medida) "
                "VALUES (%s,'Prueba','🍎','unid.') RETURNING id",
                (f"Producto {suffix}",),
            ).fetchone()["id"]
            conn.execute(
                """INSERT INTO ProductosBodega(
                       id_producto, id_bodega, stock, precio_venta, fecha_vencimiento, estado)
                   VALUES (%s, %s, 4, 5.00, %s, 'activo')""",
                (product, store_id, date.today() + timedelta(days=12)),
            )
            offer = conn.execute(
                """INSERT INTO Oferta(id_producto, id_bodega, precio_original, precio_oferta,
                                      fecha_inicio, fecha_fin, estado, es_generada)
                   VALUES (%s, %s, 5.00, 3.50, now() - interval '1 day',
                           now() + interval '20 days', 'activo', FALSE) RETURNING id""",
                (product, store_id),
            ).fetchone()["id"]
            products.append(product)
            offers.append(offer)

    users = []

    def signup():
        email = f"buyer-{uuid.uuid4().hex}@example.test"
        response = client.post("/customer/auth/register", json={
            "nombres": "Test", "apellidos": "Buyer", "correo": email, "password": "TestPass123!",
        })
        assert response.status_code == 200, response.text
        users.append(response.json()["profile"]["id"])
        return {"Authorization": "Bearer " + response.json()["token"]}

    headers = signup()
    data = {
        "client": client, "store": store, "other_store": other_store,
        "products": products, "offers": offers, "headers": headers, "signup": signup,
    }
    yield data
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        for user_id in users:
            ids = [row["id"] for row in conn.execute(
                "SELECT id FROM Compra WHERE id_cliente = %s", (user_id,)
            ).fetchall()]
            if ids:
                conn.execute("DELETE FROM ReservaCompra WHERE id_compra = ANY(%s)", (ids,))
                conn.execute("DELETE FROM Pago WHERE id_compra = ANY(%s)", (ids,))
                conn.execute("DELETE FROM DetalleCompra WHERE id_compra = ANY(%s)", (ids,))
                conn.execute("DELETE FROM Compra WHERE id = ANY(%s)", (ids,))
            conn.execute("DELETE FROM Cliente WHERE id = %s", (user_id,))
        # Include generated rows created by /customer/offers reads.
        conn.execute("DELETE FROM Oferta WHERE id_producto = ANY(%s)", (products,))
        conn.execute("DELETE FROM ProductosBodega WHERE id_producto = ANY(%s)", (products,))
        conn.execute("DELETE FROM Producto WHERE id = ANY(%s)", (products,))
        conn.execute("DELETE FROM Bodega WHERE id IN (%s, %s)", (store, other_store))


def order_data(s, lines=None, key=None):
    return {
        "idempotency_key": key or str(uuid.uuid4()),
        "lines": lines if lines is not None else [{"offer_id": s["offers"][0], "quantity": 1}],
    }


def test_public_offers_show_correct_store_and_price(scenario):
    s = scenario
    rows = s["client"].get("/customer/offers", params={"store_id": s["store"]}).json()
    row = next(row for row in rows if row["id"] == s["offers"][0])
    assert row["store_id"] == s["store"] and row["available"] == 4
    assert Decimal(row["current_price"]) == Decimal("3.50")


@pytest.mark.parametrize("lines", [
    [], [{"offer_id": 1, "quantity": 0}], [{"offer_id": 1, "quantity": -1}],
    [{"offer_id": 1, "quantity": "2"}], [{"offer_id": 1, "quantity": True}],
])
def test_bad_cart_cannot_create_order(scenario, lines):
    response = scenario["client"].post(
        "/customer/orders", json=order_data(scenario, lines), headers=scenario["headers"]
    )
    assert response.status_code == 400


def test_mixed_stores_rejected(scenario):
    s = scenario
    response = s["client"].post("/customer/orders", json=order_data(s, [
        {"offer_id": s["offers"][0], "quantity": 1},
        {"offer_id": s["offers"][1], "quantity": 1},
    ]), headers=s["headers"])
    assert response.status_code == 400


def test_duplicate_offer_rejected(scenario):
    s = scenario
    response = s["client"].post("/customer/orders", json=order_data(s, [
        {"offer_id": s["offers"][0], "quantity": 1},
        {"offer_id": s["offers"][0], "quantity": 1},
    ]), headers=s["headers"])
    assert response.status_code == 400


def test_oversell_and_reservation_visibility(scenario):
    s = scenario
    response = s["client"].post("/customer/orders", json=order_data(s, [
        {"offer_id": s["offers"][0], "quantity": 4},
    ]), headers=s["headers"])
    assert response.status_code == 200, response.text
    rows = s["client"].get("/customer/offers", params={"store_id": s["store"]}).json()
    assert all(row["id"] != s["offers"][0] for row in rows)
    second = s["client"].post("/customer/orders", json=order_data(s), headers=s["signup"]())
    assert second.status_code == 409


def test_idempotency_and_key_conflict(scenario):
    s = scenario
    data = order_data(s)
    first = s["client"].post("/customer/orders", json=data, headers=s["headers"])
    again = s["client"].post("/customer/orders", json=data, headers=s["headers"])
    assert first.status_code == again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    data["lines"][0]["quantity"] = 2
    assert s["client"].post("/customer/orders", json=data, headers=s["headers"]).status_code == 409


def test_payment_decrements_exactly_once(scenario):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        before = conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"]
    paid = s["client"].post(f"/customer/orders/{order['id']}/simulate-payment", headers=s["headers"])
    again = s["client"].post(f"/customer/orders/{order['id']}/simulate-payment", headers=s["headers"])
    assert paid.status_code == again.status_code == 200
    assert paid.json()["state"] == again.json()["state"] == "pagado"
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        after = conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"]
    assert before - after == 1


def test_history_shows_pending_and_paid_orders(scenario):
    s = scenario
    pending = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    assert pending["state"] == "pendiente"
    history = s["client"].get("/customer/orders", headers=s["headers"]).json()
    assert [item["id"] for item in history] == [pending["id"]]
    assert history[0]["state"] == "pendiente"
    assert history[0]["reservation_until"] is not None
    paid = s["client"].post(
        f"/customer/orders/{pending['id']}/simulate-payment", headers=s["headers"]
    )
    assert paid.status_code == 200
    history = s["client"].get("/customer/orders", headers=s["headers"]).json()
    assert [item["id"] for item in history] == [pending["id"]]
    assert history[0]["state"] == "pagado"
    assert history[0]["reservation_until"] is None


def test_expiry_releases_stock_and_prevents_payment(scenario):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    with psycopg.connect(test_dsn) as conn:
        conn.execute(
            "UPDATE Compra SET reserva_hasta = now() - interval '1 minute' WHERE id = %s",
            (order["id"],),
        )
    current = s["client"].get(f"/customer/orders/{order['id']}", headers=s["headers"])
    assert current.json()["state"] == "expirado"
    assert s["client"].post(
        f"/customer/orders/{order['id']}/simulate-payment", headers=s["headers"]
    ).status_code == 409
    rows = s["client"].get("/customer/offers", params={"store_id": s["store"]}).json()
    assert next(row for row in rows if row["id"] == s["offers"][0])["available"] == 4


def test_another_customer_cannot_view_or_pay_order(scenario):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    stranger = s["signup"]()
    assert s["client"].get(f"/customer/orders/{order['id']}", headers=stranger).status_code == 404
    assert s["client"].post(
        f"/customer/orders/{order['id']}/simulate-payment", headers=stranger
    ).status_code == 404
    assert s["client"].post("/customer/orders", json=order_data(s), headers={}).status_code == 401


def _provider_result(order, **overrides):
    result = {
        "id": "ORDTST123", "external_reference": str(order["id"]), "currency": "PEN",
        "total_amount": order["total"], "total_paid_amount": order["total"],
        "checkout_url": "https://www.mercadopago.com.pe/test",
        "status": "processed", "status_detail": "accredited",
        "integration_data": {"application_id": "app-test"}, "user_id": "seller-test",
    }
    result.update(overrides)
    return result


def test_external_payment_mismatch_does_not_change_stock(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(order, total_amount="0.01"))
    response = s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"])
    assert response.status_code == 409
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        assert conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"] == 4


def test_external_payment_is_verified_server_side(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(order))
    opened = s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"])
    assert opened.status_code == 200, opened.text
    verified = s["client"].post(f"/customer/orders/{order['id']}/verify-payment", headers=s["headers"])
    again = s["client"].post(f"/customer/orders/{order['id']}/verify-payment", headers=s["headers"])
    assert verified.status_code == again.status_code == 200
    assert verified.json()["state"] == "pagado"
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        assert conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"] == 3


def test_external_payment_rejected_releases_reservation(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    state = {"status": "created"}

    def provider(*args, **kwargs):
        return _provider_result(order, status=state["status"], status_detail=None)

    monkeypatch.setattr(customer, "_mp_request", provider)
    assert s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"]).status_code == 200
    state["status"] = "failed"
    rejected = s["client"].post(f"/customer/orders/{order['id']}/verify-payment", headers=s["headers"])
    assert rejected.status_code == 200 and rejected.json()["state"] == "rechazado"
    rows = s["client"].get("/customer/offers", params={"store_id": s["store"]}).json()
    assert next(row for row in rows if row["id"] == s["offers"][0])["available"] == 4


def test_late_external_accreditation_requires_review_without_stock_change(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(order))
    assert s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"]).status_code == 200
    with psycopg.connect(test_dsn) as conn:
        conn.execute(
            "UPDATE Compra SET reserva_hasta = now() - interval '1 minute' WHERE id = %s",
            (order["id"],),
        )
    reviewed = s["client"].post(f"/customer/orders/{order['id']}/verify-payment", headers=s["headers"])
    assert reviewed.status_code == 200 and reviewed.json()["state"] == "pago_en_revision"
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        assert conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"] == 4


def test_external_checkout_rejects_untrusted_redirect(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(
        order, checkout_url="https://mercadopago.com.pe.evil.test/pay"
    ))
    assert s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"]).status_code == 503


def test_external_payment_rejects_different_provider_account(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    state = {"user_id": "seller-test"}
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(order, user_id=state["user_id"]))
    assert s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"]).status_code == 200
    state["user_id"] = "different-seller"
    assert s["client"].post(
        f"/customer/orders/{order['id']}/verify-payment", headers=s["headers"]
    ).status_code == 409
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        assert conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"] == 4


def test_webhook_rejects_missing_or_wrong_signature(scenario, monkeypatch):
    monkeypatch.setattr(customer, "MERCADOPAGO_WEBHOOK_SECRET", "secret-test")
    body = {"type": "order", "live_mode": False, "data": {"id": "ORDTST123"}}
    response = scenario["client"].post(
        "/customer/payments/webhook?data.id=ORDTST123", json=body,
        headers={"X-Request-Id": "req1", "X-Signature": "ts=123,v1=" + "0" * 64},
    )
    assert response.status_code == 401
    body["live_mode"] = True
    assert scenario["client"].post(
        "/customer/payments/webhook?data.id=ORDTST123", json=body
    ).status_code == 401


def test_signed_webhook_reconciles_payment_once(scenario, monkeypatch):
    s = scenario
    order = s["client"].post("/customer/orders", json=order_data(s), headers=s["headers"]).json()
    monkeypatch.setattr(customer, "MERCADOPAGO_ACCESS_TOKEN", "TEST-ONLY")
    monkeypatch.setattr(customer, "MERCADOPAGO_WEBHOOK_SECRET", "secret-test")
    monkeypatch.setattr(customer, "_mp_request", lambda *args, **kwargs: _provider_result(
        order, id="ORDTSTWEB123"
    ))
    assert s["client"].post(f"/customer/orders/{order['id']}/checkout", headers=s["headers"]).status_code == 200
    data_id, request_id, ts = "ORDTSTWEB123", "request-web-1", "1234567890"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};".encode()
    signature = hmac.new(b"secret-test", manifest, hashlib.sha256).hexdigest()
    body = {"type": "order", "live_mode": False, "data": {"id": data_id}}
    headers = {"X-Request-Id": request_id, "X-Signature": f"ts={ts},v1={signature}"}
    first = s["client"].post(f"/customer/payments/webhook?data.id={data_id}", json=body, headers=headers)
    again = s["client"].post(f"/customer/payments/webhook?data.id={data_id}", json=body, headers=headers)
    assert first.status_code == again.status_code == 200
    assert s["client"].get(
        f"/customer/orders/{order['id']}", headers=s["headers"]
    ).json()["state"] == "pagado"
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        assert conn.execute(
            "SELECT stock FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s",
            (s["products"][0], s["store"]),
        ).fetchone()["stock"] == 3
