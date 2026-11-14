"""CU-01: the platform administrator manages owner, employee and customer accounts."""

import json

import pytest
from django.test import Client

from core.models import AuditEvent, User


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


# --- Crear y editar -------------------------------------------------------


def post_json(client, path, data):
    return client.post(path, data=json.dumps(data), content_type="application/json")


def patch_json(client, path, data):
    return client.patch(path, data=json.dumps(data), content_type="application/json")


def new_owner_data(store, **changes):
    return {"name": "Jefa nueva", "email": "Jefa@Example.test", "role": "OWNER",
            "store_id": str(store.id), "password": "OtraClaveSegura123!", **changes}


def test_admin_creates_owner_for_store(admin, store):
    response = post_json(client_for(admin), "/api/v1/admin/users", new_owner_data(store))
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jefa@example.test" and body["role"] == "OWNER"
    assert body["store_name"] == store.name and body["is_active"] is True
    created = User.objects.get(email="jefa@example.test")
    assert created.check_password("OtraClaveSegura123!")


def test_create_is_audited_without_password(admin, store):
    response = post_json(client_for(admin), "/api/v1/admin/users", new_owner_data(store))
    event = AuditEvent.objects.get(entity="User", entity_id=response.json()["id"])
    assert event.action == "USER_CREATED" and event.actor == admin and event.before is None
    assert "password" not in json.dumps(event.after)


def test_admin_creates_customer_ignoring_store(admin, store):
    data = new_owner_data(store, role="CUSTOMER", email="cli@example.test")
    response = post_json(client_for(admin), "/api/v1/admin/users", data)
    assert response.status_code == 201 and response.json()["store_id"] is None


def test_create_owner_without_store_rejected(admin):
    data = {"name": "Sin bodega", "email": "x@example.test", "role": "EMPLOYEE", "password": "OtraClaveSegura123!"}
    response = post_json(client_for(admin), "/api/v1/admin/users", data)
    assert response.status_code == 422
    assert not User.objects.filter(email="x@example.test").exists()


def test_create_second_active_owner_rejected(admin, owner, store):
    response = post_json(client_for(admin), "/api/v1/admin/users", new_owner_data(store))
    assert response.status_code in (409, 422)
    assert User.objects.filter(role="OWNER", store=store).count() == 1


@pytest.mark.parametrize("password", ["", "123", "password"])
def test_create_rejects_weak_password(admin, store, password):
    response = post_json(client_for(admin), "/api/v1/admin/users", new_owner_data(store, password=password))
    assert response.status_code == 422 and response.json()["error"]["code"] == "INVALID_PASSWORD"


def test_create_rejects_duplicate_email(admin, store, customer):
    data = new_owner_data(store, email=customer.email.upper())
    response = post_json(client_for(admin), "/api/v1/admin/users", data)
    assert response.status_code in (409, 422)


def test_create_rejects_unknown_role(admin, store):
    response = post_json(client_for(admin), "/api/v1/admin/users", new_owner_data(store, role="ROOT"))
    assert response.status_code == 422


def test_create_forbidden_for_owner(owner, store):
    data = new_owner_data(store, role="EMPLOYEE", email="e2@example.test")
    assert post_json(client_for(owner), "/api/v1/admin/users", data).status_code == 403


def test_admin_updates_profile_fields(admin, employee, other_store):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{employee.id}",
                          {"name": "Empleada movida", "store_id": str(other_store.id)})
    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.name == "Empleada movida" and employee.store_id == other_store.id


def test_update_is_audited_with_before_and_after(admin, employee):
    patch_json(client_for(admin), f"/api/v1/admin/users/{employee.id}", {"name": "Otro nombre"})
    event = AuditEvent.objects.get(action="USER_UPDATED", entity_id=employee.id)
    assert event.before["name"] == "Empleado" and event.after["name"] == "Otro nombre"


def test_update_promotes_employee_to_owner_of_free_store(admin, employee):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{employee.id}", {"role": "OWNER"})
    assert response.status_code == 200 and response.json()["role"] == "OWNER"


def test_update_to_customer_drops_store(admin, employee):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{employee.id}", {"role": "CUSTOMER"})
    assert response.status_code == 200 and response.json()["store_id"] is None


def test_admin_deactivates_and_reactivates(admin, customer):
    client = client_for(admin)
    assert patch_json(client, f"/api/v1/admin/users/{customer.id}", {"is_active": False}).json()["is_active"] is False
    assert patch_json(client, f"/api/v1/admin/users/{customer.id}", {"is_active": True}).json()["is_active"] is True


def test_admin_resets_password(admin, customer):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{customer.id}", {"password": "ClaveRenovada2026!"})
    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.check_password("ClaveRenovada2026!")


def test_update_rejects_weak_password(admin, customer):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{customer.id}", {"password": "123"})
    assert response.status_code == 422
    customer.refresh_from_db()
    assert customer.check_password("SecurePass123!")


def test_update_rejects_duplicate_email(admin, customer, employee):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{customer.id}", {"email": employee.email})
    assert response.status_code in (409, 422)


def test_update_unknown_user_is_404(admin):
    response = patch_json(client_for(admin), "/api/v1/admin/users/00000000-0000-0000-0000-000000000000", {"name": "X"})
    assert response.status_code == 404


def test_admin_cannot_deactivate_or_demote_self(admin):
    client = client_for(admin)
    assert patch_json(client, f"/api/v1/admin/users/{admin.id}", {"is_active": False}).status_code == 422
    assert patch_json(client, f"/api/v1/admin/users/{admin.id}", {"role": "CUSTOMER"}).status_code == 422
    admin.refresh_from_db()
    assert admin.is_active and admin.role == "ADMIN"


def test_admin_can_edit_own_name(admin):
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{admin.id}", {"name": "Admin renombrado"})
    assert response.status_code == 200


def test_demoting_superuser_admin_clears_platform_flags(admin):
    other = User.objects.create_superuser(email="root@example.test", password="LongPassword!1", name="Root")
    response = patch_json(client_for(admin), f"/api/v1/admin/users/{other.id}", {"role": "CUSTOMER"})
    assert response.status_code == 200
    other.refresh_from_db()
    assert not other.is_superuser and not other.is_staff
