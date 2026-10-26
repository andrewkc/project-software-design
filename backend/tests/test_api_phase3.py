import json
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from core.models import InventoryMovement, Lot, Order, User


pytestmark = pytest.mark.django_db


def post(client, path, body, csrf=False):
    headers = {}
    if csrf:
        headers["HTTP_X_CSRFTOKEN"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client.post(path, data=json.dumps(body), content_type="application/json", **headers)


def test_public_catalog_hides_internal_cost_and_unpublished(offer):
    response = Client().get("/api/v1/offers")
    assert response.status_code == 200
    item = response.json()[0]
    assert item["id"] == str(offer.id)
    assert "total_cost" not in json.dumps(item)
    offer.state = "PAUSED"
    offer.save(update_fields=["state"])
    assert Client().get("/api/v1/offers").json() == []


def test_public_offer_unknown_is_404():
    assert Client().get(f"/api/v1/offers/{uuid.uuid4()}").status_code == 404


def test_public_catalog_releases_expired_reservation(customer, offer, lot):
    client = Client()
    client.force_login(customer)
    created = post(client, "/api/v1/orders", {"idempotency_key": str(uuid.uuid4()),
        "lines": [{"offer_id": str(offer.id), "base_quantity": 1250}]})
    assert created.status_code == 201
    assert Client().get("/api/v1/offers").json() == []
    Order.objects.filter(pk=created.json()["id"]).update(
        reservation_until=timezone.now() - timedelta(seconds=1))
    assert Client().get("/api/v1/offers").json()[0]["available_steps"] == 5
    lot.refresh_from_db()
    assert lot.reserved_qty == 0


def test_register_customer_then_login_with_csrf():
    client = Client(enforce_csrf_checks=True)
    body = {"email": "newbuyer@example.test", "name": "Comprador", "password": "SecureDemoPassword123!"}
    assert post(client, "/api/v1/auth/register", body).status_code == 403
    response = post(client, "/api/v1/auth/register", body, csrf=True)
    assert response.status_code == 201
    assert response.json()["role"] == User.Role.CUSTOMER
    assert post(client, "/api/v1/auth/login", {"email": body["email"],
        "password": body["password"]}, csrf=True).status_code == 200
    assert client.get("/api/v1/auth/me").json()["email"] == body["email"]


def test_register_rejects_weak_password():
    response = post(Client(), "/api/v1/auth/register",
                    {"email": "newbuyer@example.test", "name": "Comprador", "password": "123"})
    assert response.status_code == 422 and not User.objects.filter(email="newbuyer@example.test").exists()


def test_end_to_end_http_purchase_and_inventory(customer, offer, lot):
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer)
    payload = {"idempotency_key": str(uuid.uuid4()),
               "lines": [{"offer_id": str(offer.id), "base_quantity": 500}]}
    assert post(client, "/api/v1/orders", payload).status_code == 403
    created = post(client, "/api/v1/orders", payload, csrf=True)
    assert created.status_code == 201 and created.json()["total"] == "18.00"
    order_id = created.json()["id"]
    assert post(client, "/api/v1/orders", payload, csrf=True).json()["id"] == order_id
    assert client.get("/api/v1/orders").json()[0]["state"] == "PENDING"
    paid = post(client, f"/api/v1/orders/{order_id}/simulate-payment", {"decision": "APPROVE"}, csrf=True)
    assert paid.status_code == 200 and paid.json()["state"] == "PAID"
    assert client.get(f"/api/v1/orders/{order_id}").json()["state"] == "PAID"
    lot.refresh_from_db()
    assert (lot.physical_qty, lot.reserved_qty) == (750, 0)
    assert InventoryMovement.objects.filter(order_id=order_id, kind="WEB_SALE").count() == 1


def test_order_api_requires_customer(owner, offer):
    client = Client()
    client.force_login(owner)
    response = post(client, "/api/v1/orders", {"idempotency_key": str(uuid.uuid4()),
        "lines": [{"offer_id": str(offer.id), "base_quantity": 250}]})
    assert response.status_code == 403 and not Order.objects.exists()


def test_order_other_customer_is_hidden(customer, offer):
    client = Client()
    client.force_login(customer)
    created = post(client, "/api/v1/orders", {"idempotency_key": str(uuid.uuid4()),
        "lines": [{"offer_id": str(offer.id), "base_quantity": 250}]})
    other = User.objects.create_user(email="otherbuyer@example.test", password="SecurePass123!",
                                     name="Otro", role=User.Role.CUSTOMER)
    client.force_login(other)
    assert client.get(f"/api/v1/orders/{created.json()['id']}").status_code == 404


def test_local_chat_public_only_sees_public_offers(offer, lot):
    response = post(Client(), "/api/v1/chat", {"question": "¿Qué ofertas hay?"})
    assert response.status_code == 200 and response.json()["mode"] == "LOCAL_DEMO"
    assert "Almendras" in response.json()["answer"]
    assert "25.00" not in response.json()["answer"]


def test_local_chat_employee_stock_only_own_store(employee, lot, other_store):
    from core.models import Product
    Product.objects.create(store=other_store, code="SECRET", name="Secreto", category="X",
                           unit="UNIT", sale_step=1, reference_price=1, storage_conditions="X")
    client = Client()
    client.force_login(employee)
    response = post(client, "/api/v1/chat", {"question": "¿Qué stock tengo?"})
    assert response.status_code == 200
    assert "Almendras" in response.json()["answer"] and "Secreto" not in response.json()["answer"]
    assert "25.00" not in response.json()["answer"]


def test_local_chat_rejects_empty_and_long_question():
    for question in ("", "a" * 1001):
        assert post(Client(), "/api/v1/chat", {"question": question}).status_code == 422
