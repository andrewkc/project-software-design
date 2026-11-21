"""Boundary and permission checks for the demo's account administration."""

import uuid

import pytest
from rest_framework.test import APIClient

from core import accounts, services
from core.models import AuditEvent, Store, StorePricingPolicy, User


@pytest.fixture
def platform_admin(db):
    return User.objects.create_superuser(email="admin@example.test", password="StrongAdmin123!", name="Admin")


BAD_STORE_CREATE = [
    None, [], "store", 1, {}, {"name": "A"}, {"address": "A"},
    {"name": "", "address": "Calle"}, {"name": "  ", "address": "Calle"},
    {"name": 42, "address": "Calle"}, {"name": True, "address": "Calle"},
    {"name": "A" * 151, "address": "Calle"}, {"name": "A", "address": ""},
    {"name": "A", "address": 10}, {"name": "A", "address": "X" * 501},
    {"name": "A", "address": "Calle", "opening_hours": 42},
    {"name": "A", "address": "Calle", "opening_hours": "X" * 121},
    {"name": "A", "address": "Calle", "active": True},
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", BAD_STORE_CREATE)
def test_bad_store_creation_has_no_side_effects(platform_admin, payload):
    with pytest.raises(services.DomainError):
        accounts.create_store(platform_admin, payload)
    assert Store.objects.count() == AuditEvent.objects.count() == 0


BAD_STORE_UPDATE = [
    {}, None, [], "bad", {"name": ""}, {"name": "  "}, {"name": 9},
    {"name": "X" * 151}, {"address": ""}, {"address": []},
    {"address": "X" * 501}, {"opening_hours": ""},
    {"opening_hours": "X" * 121}, {"active": 1}, {"active": "false"},
    {"active": None}, {"id": str(uuid.uuid4())}, {"password": "x"},
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", BAD_STORE_UPDATE)
def test_bad_store_update_preserves_store(platform_admin, store, payload):
    before = accounts.store_payload(store)
    with pytest.raises(services.DomainError):
        accounts.update_store(platform_admin, store.id, payload)
    store.refresh_from_db()
    assert accounts.store_payload(store) == before
    assert not AuditEvent.objects.exists()


def bad_user_payloads(store_id):
    good = {"email": "new@example.test", "name": "Nuevo", "password": "LongPass123!",
            "role": "EMPLOYEE", "store_id": str(store_id)}
    mutations = [
        {"email": None}, {"email": ""}, {"email": "  "}, {"email": 5},
        {"email": "bad"}, {"email": "x" * 250 + "@x.com"},
        {"name": None}, {"name": ""}, {"name": "  "}, {"name": 8},
        {"name": "n" * 121}, {"password": None}, {"password": ""},
        {"password": "123"}, {"password": "123456789012"},
        {"password": 42}, {"role": None}, {"role": "ROOT"},
        {"role": "owner"}, {"role": 7}, {"store_id": None},
        {"store_id": ""}, {"store_id": "not-a-uuid"},
        {"store_id": str(uuid.UUID(int=0))},
        {"role": "CUSTOMER"}, {"role": "ADMIN"},
        {"is_superuser": True}, {"is_staff": True},
    ]
    return [dict(good, **change) for change in mutations]


@pytest.mark.django_db
@pytest.mark.parametrize("case", range(28))
def test_bad_account_creation_never_creates_user(platform_admin, store, case):
    payload = bad_user_payloads(store.id)[case]
    with pytest.raises(services.DomainError):
        accounts.create_user(platform_admin, payload)
    assert User.objects.count() == 1
    assert not AuditEvent.objects.exists()


BAD_USER_UPDATE = [
    None, [], "bad", {}, {"name": ""}, {"name": "  "},
    {"name": 5}, {"name": "X" * 121}, {"active": None},
    {"active": 1}, {"active": 0}, {"active": "yes"},
    {"role": "ADMIN"}, {"store_id": str(uuid.uuid4())},
    {"password": "new"}, {"is_superuser": True},
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", BAD_USER_UPDATE)
def test_bad_user_update_preserves_account(platform_admin, employee, payload):
    before = accounts.user_payload(employee)
    with pytest.raises(services.DomainError):
        accounts.update_user(platform_admin, employee.id, payload)
    employee.refresh_from_db()
    assert accounts.user_payload(employee) == before
    assert not AuditEvent.objects.exists()


ADMIN_ROUTES = [
    ("get", "/api/v1/admin/stores", None),
    ("post", "/api/v1/admin/stores", {"name": "X", "address": "Y"}),
    ("patch", "/api/v1/admin/stores/00000000-0000-0000-0000-000000000000", {"active": False}),
    ("get", "/api/v1/admin/users", None),
    ("post", "/api/v1/admin/users", {"role": "CUSTOMER"}),
    ("patch", "/api/v1/admin/users/00000000-0000-0000-0000-000000000000", {"active": False}),
]


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["OWNER", "EMPLOYEE", "CUSTOMER"])
@pytest.mark.parametrize("method,path,payload", ADMIN_ROUTES)
def test_admin_routes_reject_other_roles(role, method, path, payload, owner, employee, customer):
    actor = {"OWNER": owner, "EMPLOYEE": employee, "CUSTOMER": customer}[role]
    client = APIClient()
    client.force_authenticate(actor)
    response = getattr(client, method)(path, payload, format="json") if payload is not None else getattr(client, method)(path)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["EMPLOYEE", "CUSTOMER", "ADMIN"])
@pytest.mark.parametrize("method,path,payload", [
    ("get", "/api/v1/store/staff", None),
    ("post", "/api/v1/store/staff", {"email": "x@example.test", "name": "X", "password": "StrongPass123!"}),
])
def test_staff_management_rejects_nonowners(role, method, path, payload, platform_admin, employee, customer):
    actor = {"EMPLOYEE": employee, "CUSTOMER": customer, "ADMIN": platform_admin}[role]
    client = APIClient()
    client.force_authenticate(actor)
    response = getattr(client, method)(path, payload, format="json") if payload is not None else getattr(client, method)(path)
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_creates_store_owner_employee_and_policy(platform_admin):
    store = accounts.create_store(platform_admin, {"name": "Nueva", "address": "Calle 1"})
    owner = accounts.create_user(platform_admin, {"email": "owner2@example.test", "name": "Dueño",
                                 "password": "StrongPass123!", "role": "OWNER", "store_id": str(store.id)})
    assert StorePricingPolicy.objects.get(store=store).created_by == owner
    staff = accounts.create_user(owner, {"email": "staff2@example.test", "name": "Staff",
                                         "password": "StrongPass123!"}, staff_only=True)
    assert staff.store == store and staff.role == "EMPLOYEE"
    assert [u.id for u in accounts.list_staff(owner)] == [staff.id]
    assert AuditEvent.objects.count() == 3


@pytest.mark.django_db
def test_owner_cannot_modify_another_stores_employee(owner, other_store):
    foreign = User.objects.create_user(email="foreign@example.test", password="StrongPass123!",
                                       name="Ajeno", role="EMPLOYEE", store=other_store)
    with pytest.raises(services.DomainError) as error:
        accounts.update_user(owner, foreign.id, {"active": False}, staff_only=True)
    assert error.value.status == 404
    foreign.refresh_from_db()
    assert foreign.is_active


@pytest.mark.django_db
def test_last_admin_and_active_owner_are_protected(platform_admin, owner):
    for actor in (platform_admin, owner):
        with pytest.raises(services.DomainError):
            accounts.update_user(platform_admin, actor.id, {"active": False})
        actor.refresh_from_db()
        assert actor.is_active


@pytest.mark.django_db
def test_store_with_reservation_cannot_be_deactivated(platform_admin, store, order, offer, lot):
    from core.models import OrderLine, Reservation
    line = OrderLine.objects.create(order=order, offer=offer, base_qty=250, step_snapshot=250,
                                    step_price_snapshot=offer.current_price, amount=offer.current_price,
                                    expiry_snapshot=lot.expiry_date, offer_version=offer.version)
    Reservation.objects.create(line=line, lot=lot, base_qty=250, expires_at=order.reservation_until)
    with pytest.raises(services.DomainError) as error:
        accounts.update_store(platform_admin, store.id, {"active": False})
    assert error.value.code == "ACTIVE_RESERVATIONS"


@pytest.mark.django_db
def test_deactivation_keeps_history_and_audit(platform_admin, store, employee):
    accounts.update_user(platform_admin, employee.id, {"active": False})
    employee.refresh_from_db()
    assert not employee.is_active and employee.store == store
    event = AuditEvent.objects.get()
    assert event.before["active"] and not event.after["active"]
    assert "password" not in str(event.after)
