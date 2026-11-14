"""CU-01: the platform administrator manages owner, employee and customer accounts."""

import pytest
from django.test import Client

from core.models import User


pytestmark = pytest.mark.django_db


def client_for(user):
    client = Client()
    client.force_login(user)
    return client


def test_users_list_requires_login():
    assert Client().get("/api/v1/admin/users").status_code in (401, 403)


@pytest.mark.parametrize("role_fixture", ["owner", "employee", "customer"])
def test_users_list_forbidden_for_non_admin(request, role_fixture):
    user = request.getfixturevalue(role_fixture)
    response = client_for(user).get("/api/v1/admin/users")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_inactive_admin_cannot_list(admin):
    client = client_for(admin)
    admin.is_active = False
    admin.save(update_fields=["is_active"])
    assert client.get("/api/v1/admin/users").status_code in (401, 403)


def test_admin_lists_every_profile_with_store(admin, owner, employee, customer, store):
    response = client_for(admin).get("/api/v1/admin/users")
    assert response.status_code == 200
    rows = {row["email"]: row for row in response.json()}
    assert set(rows) == {admin.email, owner.email, employee.email, customer.email}
    assert rows[owner.email]["role"] == "OWNER"
    assert rows[owner.email]["store_id"] == str(store.id)
    assert rows[owner.email]["store_name"] == store.name
    assert rows[customer.email]["store_name"] is None
    assert rows[employee.email]["is_active"] is True
    assert {"created_at", "last_login"} <= set(rows[owner.email])


def test_users_list_never_exposes_passwords(admin, owner):
    body = client_for(admin).get("/api/v1/admin/users").content.decode()
    assert "password" not in body and owner.password not in body


def test_admin_lists_stores_including_inactive(admin, store, other_store):
    other_store.active = False
    other_store.save(update_fields=["active"])
    response = client_for(admin).get("/api/v1/admin/stores")
    assert response.status_code == 200
    assert {(row["name"], row["active"]) for row in response.json()} == {("Tienda A", True), ("Tienda B", False)}


def test_stores_admin_list_forbidden_for_owner(owner):
    assert client_for(owner).get("/api/v1/admin/stores").status_code == 403
