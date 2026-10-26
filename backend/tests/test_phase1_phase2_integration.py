"""Real HTTP/session + seeded data + inventory ledger on PostgreSQL."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db.models import Sum
from django.test import Client
from django.utils import timezone

from core.models import InventoryMovement, Lot, MovementLine, Offer, Product, Store, User


pytestmark = pytest.mark.django_db


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setenv("DESSOF_DEMO_PASSWORD", "StrongDemoPass123!")
    call_command("seed_demo", verbosity=0)
    return {
        "store1": Store.objects.get(name="Mercado Verde"),
        "store2": Store.objects.get(name="Dulce y Fresco"),
        "owner1": User.objects.get(email="dueno.1@demo.example"),
        "employee1": User.objects.get(email="empleado.1@demo.example"),
        "employee2": User.objects.get(email="empleado.2@demo.example"),
    }


def login(email):
    client = Client(enforce_csrf_checks=True)
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post("/api/v1/auth/login", data=json.dumps({"email": email, "password": "StrongDemoPass123!"}),
                           content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 200
    return client


def post(client, path, data):
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client.post(path, data=json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=csrf)


def new_key():
    return str(uuid.uuid4())


def test_seeded_owner_login_reads_only_own_store(demo):
    client = login("dueno.1@demo.example")
    assert client.get("/api/v1/auth/me").json()["store_id"] == str(demo["store1"].id)
    products = client.get("/api/v1/store/products").json()
    lots = client.get("/api/v1/store/lots").json()
    offers = client.get("/api/v1/store/offers").json()
    assert len(products) == 4 and len(lots) == 5 and len(offers) == 5
    assert all("total_cost" in item for item in lots)
    assert {item["code"] for item in products} == {"ALM", "PAS", "FRE", "MAN"}


def test_seeded_employee_sale_updates_owner_view_and_ledger(demo):
    employee = login("empleado.1@demo.example")
    owner = login("dueno.1@demo.example")
    product = Product.objects.get(store=demo["store1"], code="ALM")
    first_lot = product.lots.get(code="ALM-01")
    before = first_lot.physical_qty
    response = post(employee, "/api/v1/store/local-sales", {"product_id": str(product.id),
                    "quantity": 500, "idempotency_key": new_key()})
    assert response.status_code == 201 and response.json()["total"] == "20.00"
    assert response.json()["actor_id"] == str(demo["employee1"].id)
    first_lot.refresh_from_db()
    assert first_lot.physical_qty == before - 500
    assert next(item for item in owner.get("/api/v1/store/lots").json() if item["id"] == str(first_lot.id))["physical_qty"] == before - 500
    assert MovementLine.objects.filter(lot=first_lot).aggregate(total=Sum("physical_delta"))["total"] == first_lot.physical_qty
    assert all(lot.physical_qty == MovementLine.objects.filter(lot=lot).aggregate(total=Sum("physical_delta"))["total"] for lot in Lot.objects.all())


def test_new_product_inbound_sale_waste_adjust_end_to_end(demo):
    owner = login("dueno.1@demo.example")
    employee = login("empleado.1@demo.example")
    product = post(owner, "/api/v1/store/products", {"code": "HIG", "name": "Higos", "category": "Frutas",
                    "unit": "G", "sale_step": 250, "reference_price": "5.00", "storage_conditions": "Frío"})
    assert product.status_code == 201
    today = timezone.localdate()
    receipt = post(owner, "/api/v1/store/inbounds", {"product_id": product.json()["id"], "code": "HIG-01",
                    "received_date": today.isoformat(), "expiry_date": (today + timedelta(days=8)).isoformat(),
                    "quantity": 1000, "total_cost": "8.00", "idempotency_key": new_key()})
    assert receipt.status_code == 201
    lot_id = receipt.json()["lot"]["id"]
    sale = post(employee, "/api/v1/store/local-sales", {"product_id": product.json()["id"],
                "quantity": 500, "idempotency_key": new_key()})
    waste = post(owner, "/api/v1/store/waste", {"lot_id": lot_id, "quantity": 100,
                 "reason": "Daño físico", "idempotency_key": new_key()})
    adjustment = post(owner, "/api/v1/store/adjustments", {"lot_id": lot_id, "delta": -25,
                      "reason": "Conteo", "idempotency_key": new_key()})
    assert [r.status_code for r in (sale, waste, adjustment)] == [201, 201, 201]
    lot = Lot.objects.get(pk=lot_id)
    assert lot.physical_qty == 375
    assert MovementLine.objects.filter(lot=lot).aggregate(total=Sum("physical_delta"))["total"] == 375
    assert [m["kind"] for m in owner.get("/api/v1/store/movements").json()[:3]] == ["ADJUSTMENT", "WASTE", "LOCAL_SALE"]


def test_price_decision_affects_new_sales_not_old_snapshots(demo):
    owner = login("dueno.1@demo.example")
    employee = login("empleado.1@demo.example")
    offer = Offer.objects.get(lot__product__store=demo["store1"], lot__code="ALM-01")
    price_path = f"/api/v1/store/offers/{offer.id}/price"
    assert post(owner, price_path, {"new_price": "9.00", "reason": "Primera rebaja"}).status_code == 200
    product_id = str(offer.lot.product_id)
    first = post(employee, "/api/v1/store/local-sales", {"product_id": product_id, "quantity": 250,
                 "idempotency_key": new_key()})
    assert first.status_code == 201 and first.json()["total"] == "9.00"
    assert post(owner, price_path, {"new_price": "8.00", "reason": "Segunda rebaja"}).status_code == 200
    second = post(employee, "/api/v1/store/local-sales", {"product_id": product_id, "quantity": 250,
                  "idempotency_key": new_key()})
    assert second.status_code == 201 and second.json()["total"] == "8.00"
    first_id = first.json()["id"]
    first_movement = InventoryMovement.objects.get(pk=first_id)
    assert first_movement.lines.get().step_price_snapshot == Decimal("9.00")
    assert first_movement.lines.get().amount == Decimal("9.00")


def test_second_store_cannot_access_or_sell_first_store_stock(demo):
    first_product = Product.objects.get(store=demo["store1"], code="ALM")
    first_lot = first_product.lots.get(code="ALM-01")
    before = first_lot.physical_qty
    client = login("empleado.2@demo.example")
    assert {item["code"] for item in client.get("/api/v1/store/products").json()} == {"PAT", "NUE", "ARA", "UVA"}
    response = post(client, "/api/v1/store/local-sales", {"product_id": str(first_product.id),
                    "quantity": 250, "idempotency_key": new_key()})
    assert response.status_code == 404
    first_lot.refresh_from_db()
    assert first_lot.physical_qty == before


def test_seeded_employee_sees_no_cost_or_price_policy(demo):
    client = login("empleado.1@demo.example")
    lots = client.get("/api/v1/store/lots").content.decode()
    offers = client.get("/api/v1/store/offers").content.decode()
    assert "total_cost" not in lots and "minimum_price" not in offers and "effective_floor" not in offers
    assert post(client, "/api/v1/store/adjustments", {"lot_id": str(Lot.objects.first().id),
           "delta": -1, "reason": "Intento", "idempotency_key": new_key()}).status_code == 403
