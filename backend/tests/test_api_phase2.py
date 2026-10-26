import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from core.models import InventoryMovement, Lot, Offer, Product, User


pytestmark = pytest.mark.django_db


def post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def inbound_payload(product):
    today = timezone.localdate()
    return {"product_id": str(product.id), "code": "API-LOT", "received_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=10)).isoformat(), "quantity": 500,
            "total_cost": "10.00", "idempotency_key": str(uuid.uuid4())}


def test_products_requires_authentication():
    assert Client().get("/api/v1/store/products").status_code in (401, 403)


def test_owner_gets_only_own_products(owner, product, other_store):
    Product.objects.create(store=other_store, code="B", name="Secreto", category="X", unit="G",
                           sale_step=100, reference_price=Decimal("1"), storage_conditions="X")
    client = Client()
    client.force_login(owner)
    body = client.get("/api/v1/store/products").json()
    assert len(body) == 1 and body[0]["id"] == str(product.id)


def test_customer_cannot_read_internal_products(customer, product):
    client = Client()
    client.force_login(customer)
    assert client.get("/api/v1/store/products").status_code == 403


def test_employee_cannot_create_product(employee):
    client = Client()
    client.force_login(employee)
    response = post(client, "/api/v1/store/products", {"code": "X", "name": "X", "category": "X",
                                                    "unit": "G", "sale_step": 100, "reference_price": "1",
                                                    "storage_conditions": "X"})
    assert response.status_code == 403 and Product.objects.count() == 0


def test_owner_create_product_then_inbound(owner):
    client = Client()
    client.force_login(owner)
    response = post(client, "/api/v1/store/products", {"code": "X", "name": "Producto X", "category": "Fruta",
                                                    "unit": "G", "sale_step": 250, "reference_price": "4.50",
                                                    "storage_conditions": "Frío"})
    assert response.status_code == 201
    product = Product.objects.get(pk=response.json()["id"])
    inbound = post(client, "/api/v1/store/inbounds", inbound_payload(product))
    assert inbound.status_code == 201
    assert inbound.json()["lot"]["physical_qty"] == 500
    assert inbound.json()["movement"]["kind"] == "INBOUND"
    assert len(client.get("/api/v1/store/lots").json()) == 1


def test_inbound_duplicate_code_returns_conflict(owner, product):
    client = Client()
    client.force_login(owner)
    first = inbound_payload(product)
    assert post(client, "/api/v1/store/inbounds", first).status_code == 201
    second = {**first, "idempotency_key": str(uuid.uuid4())}
    response = post(client, "/api/v1/store/inbounds", second)
    assert response.status_code == 422 and Lot.objects.count() == 1


def test_employee_lots_hide_cost(employee, lot):
    client = Client()
    client.force_login(employee)
    body = client.get("/api/v1/store/lots").content.decode()
    assert "total_cost" not in body and "available_qty" in body


def test_owner_lots_show_cost(owner, lot):
    client = Client()
    client.force_login(owner)
    assert client.get("/api/v1/store/lots").json()[0]["total_cost"] == "25.00"


def test_employee_sale_through_api(employee, product, lot):
    client = Client()
    client.force_login(employee)
    response = post(client, "/api/v1/store/local-sales", {"product_id": str(product.id), "quantity": 250,
                                                        "idempotency_key": str(uuid.uuid4())})
    assert response.status_code == 201 and response.json()["total"] == "10.00"
    lot.refresh_from_db()
    assert lot.physical_qty == 1000


def test_employee_waste_and_adjustment_forbidden(employee, lot):
    client = Client()
    client.force_login(employee)
    base = {"lot_id": str(lot.id), "reason": "Conteo", "idempotency_key": str(uuid.uuid4())}
    assert post(client, "/api/v1/store/waste", {**base, "quantity": 10}).status_code == 403
    assert post(client, "/api/v1/store/adjustments", {**base, "delta": -10}).status_code == 403
    lot.refresh_from_db()
    assert lot.physical_qty == 1250


def test_owner_waste_then_adjustment(owner, lot):
    client = Client()
    client.force_login(owner)
    waste = post(client, "/api/v1/store/waste", {"lot_id": str(lot.id), "quantity": 10,
                                                 "reason": "Deterioro", "idempotency_key": str(uuid.uuid4())})
    adjust = post(client, "/api/v1/store/adjustments", {"lot_id": str(lot.id), "delta": 3,
                                                          "reason": "Conteo", "idempotency_key": str(uuid.uuid4())})
    lot.refresh_from_db()
    assert waste.status_code == adjust.status_code == 201 and lot.physical_qty == 1243
    assert len(client.get("/api/v1/store/movements").json()) == 2


def test_offer_limit_and_manual_price_api(owner, offer):
    client = Client()
    client.force_login(owner)
    path = f"/api/v1/store/offers/{offer.id}"
    limit = post(client, path + "/limits", {"max_discount_pct": "30", "minimum_price": "7.00",
                                              "below_cost_authorized": False})
    price = post(client, path + "/price", {"new_price": "8.00", "reason": "Descuento manual"})
    assert limit.status_code == price.status_code == 200
    offer.refresh_from_db()
    assert offer.current_price == Decimal("8.00") and offer.automation_paused
    assert client.get("/api/v1/store/offers").json()[0]["limit"]["effective_floor"] == "7.00"


def test_employee_offers_hide_limit_and_cost(employee, offer, owner):
    client = Client()
    client.force_login(employee)
    body = client.get("/api/v1/store/offers").content.decode()
    assert "current_price" in body and "effective_floor" not in body and "total_cost" not in body
    path = f"/api/v1/store/offers/{offer.id}"
    assert post(client, path + "/pause", {}).status_code == 403
    assert post(client, path + "/price", {"new_price": "8", "reason": "X"}).status_code == 403


def test_other_store_offer_is_not_found(owner, other_store, offer):
    other_owner = User.objects.create_user(email="apiother@example.test", password="SecurePass123!",
                                           name="Otro", role=User.Role.OWNER, store=other_store)
    client = Client()
    client.force_login(other_owner)
    assert post(client, f"/api/v1/store/offers/{offer.id}/pause", {}).status_code == 404


def test_csrf_blocks_authenticated_mutation(owner, product):
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)
    response = post(client, "/api/v1/store/local-sales", {"product_id": str(product.id), "quantity": 250,
                                                        "idempotency_key": str(uuid.uuid4())})
    assert response.status_code == 403
    assert InventoryMovement.objects.count() == 0


def test_malformed_uuid_returns_422(owner):
    client = Client()
    client.force_login(owner)
    response = post(client, "/api/v1/store/local-sales", {"product_id": "not-a-uuid", "quantity": 1,
                                                        "idempotency_key": str(uuid.uuid4())})
    assert response.status_code == 422 and response.json()["error"]["code"] == "INVALID_ID"
