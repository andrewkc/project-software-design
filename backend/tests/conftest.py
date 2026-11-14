from datetime import datetime, timedelta, time
from decimal import Decimal
from zoneinfo import ZoneInfo
import uuid

import pytest
from django.utils import timezone

from core.models import Lot, Offer, Order, Product, Store, User


@pytest.fixture
def store(db):
    return Store.objects.create(name="Tienda A", address="Calle A")


@pytest.fixture
def other_store(db):
    return Store.objects.create(name="Tienda B", address="Calle B")


@pytest.fixture
def owner(store):
    return User.objects.create_user(email="owner@example.test", password="SecurePass123!", name="Dueño", role=User.Role.OWNER, store=store)


@pytest.fixture
def employee(store):
    return User.objects.create_user(email="employee@example.test", password="SecurePass123!", name="Empleado", role=User.Role.EMPLOYEE, store=store)


@pytest.fixture
def admin(db):
    return User.objects.create_user(email="admin@example.test", password="SecurePass123!", name="Admin", role=User.Role.ADMIN, is_staff=True)


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="customer@example.test", password="SecurePass123!", name="Cliente", role=User.Role.CUSTOMER)


@pytest.fixture
def product(store):
    return Product.objects.create(store=store, code="ALM", name="Almendras", category="Frutos secos", unit="G",
                                  sale_step=250, reference_price=Decimal("10.00"), storage_conditions="Seco")


@pytest.fixture
def lot(product):
    today = timezone.localdate()
    expiry = today + timedelta(days=12)
    return Lot.objects.create(product=product, code="ALM-01", received_date=expiry - timedelta(days=20),
                              expiry_date=expiry,
                              sales_close_at=datetime.combine(expiry - timedelta(days=1), time(23, 59, 59), ZoneInfo("America/Lima")),
                              total_cost=Decimal("25.00"), received_qty=1250, physical_qty=1250)


@pytest.fixture
def offer(lot):
    return Offer.objects.create(lot=lot, state=Offer.State.PUBLISHED,
                                original_price=Decimal("10.00"), current_price=Decimal("9.00"))


@pytest.fixture
def order(customer, store):
    return Order.objects.create(customer=customer, store=store, total=Decimal("18.00"),
                                reservation_until=timezone.now() + timedelta(minutes=10),
                                idempotency_key=uuid.uuid4(), request_hash="a" * 64)

