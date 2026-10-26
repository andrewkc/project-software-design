import json

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client

from core.models import Store, User


pytestmark = pytest.mark.django_db


def test_email_required(db):
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="LongPassword!1", name="X", role=User.Role.CUSTOMER)


def test_email_normalized(db):
    user = User.objects.create_user(email="  TEST@EXAMPLE.COM  ", password="LongPassword!1", name="X", role=User.Role.CUSTOMER)
    assert user.email == "test@example.com"


def test_case_insensitive_email_unique(customer):
    duplicate = User(email="CUSTOMER@EXAMPLE.TEST", name="Duplicado", role=User.Role.CUSTOMER)
    duplicate.set_password("LongPassword!1")
    with pytest.raises(IntegrityError), transaction.atomic():
        duplicate.save()


def test_owner_requires_store(db):
    with pytest.raises(ValidationError):
        User.objects.create_user(email="a@example.test", password="LongPassword!1", name="A", role=User.Role.OWNER)


def test_employee_requires_store(db):
    with pytest.raises(ValidationError):
        User.objects.create_user(email="a@example.test", password="LongPassword!1", name="A", role=User.Role.EMPLOYEE)


@pytest.mark.parametrize("role", [User.Role.ADMIN, User.Role.CUSTOMER])
def test_global_role_cannot_have_store(store, role):
    with pytest.raises(ValidationError):
        User.objects.create_user(email="a@example.test", password="LongPassword!1", name="A", role=role, store=store)


def test_one_active_owner_per_store(owner, store):
    with pytest.raises(ValidationError):
        User.objects.create_user(email="other@example.test", password="LongPassword!1", name="Otro", role=User.Role.OWNER, store=store)


def test_owner_in_another_store_allowed(owner, other_store):
    other = User.objects.create_user(email="other@example.test", password="LongPassword!1", name="Otro", role=User.Role.OWNER, store=other_store)
    assert other.store_id != owner.store_id


def test_inactive_owner_does_not_block_replacement(owner, store):
    owner.is_active = False
    owner.save(update_fields=["is_active"])
    replacement = User.objects.create_user(email="new@example.test", password="LongPassword!1", name="Nuevo", role=User.Role.OWNER, store=store)
    assert replacement.is_active


def test_bad_superuser_flags(db):
    with pytest.raises(ValueError):
        User.objects.create_superuser(email="admin@example.test", password="LongPassword!1", name="Admin", is_staff=False)


def test_superuser_role(db):
    user = User.objects.create_superuser(email="admin@example.test", password="LongPassword!1", name="Admin")
    assert user.role == User.Role.ADMIN and user.is_staff and user.is_superuser


def test_health_public():
    response = Client().get("/api/v1/health")
    assert response.status_code == 200 and response.json() == {"status": "ok", "phase": 1}


def test_me_requires_login():
    assert Client().get("/api/v1/auth/me").status_code in (401, 403)


def test_login_rejects_wrong_password(customer):
    client = Client()
    response = client.post("/api/v1/auth/login", data=json.dumps({"email": customer.email, "password": "wrong"}), content_type="application/json")
    assert response.status_code == 401
    assert "sessionid" not in client.cookies


def test_login_rejects_inactive(customer):
    customer.is_active = False
    customer.save(update_fields=["is_active"])
    response = Client().post("/api/v1/auth/login", data=json.dumps({"email": customer.email, "password": "SecurePass123!"}), content_type="application/json")
    assert response.status_code == 401


def test_login_me_logout_round_trip(customer):
    client = Client()
    response = client.post("/api/v1/auth/login", data=json.dumps({"email": customer.email.upper(), "password": "SecurePass123!"}), content_type="application/json")
    assert response.status_code == 200 and response.json()["role"] == User.Role.CUSTOMER
    assert client.get("/api/v1/auth/me").json()["id"] == str(customer.id)
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code in (401, 403)


def test_login_requires_csrf(customer):
    client = Client(enforce_csrf_checks=True)
    response = client.post("/api/v1/auth/login", data=json.dumps({"email": customer.email, "password": "SecurePass123!"}), content_type="application/json")
    assert response.status_code == 403


def test_login_with_csrf(customer):
    client = Client(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post("/api/v1/auth/login", data=json.dumps({"email": customer.email, "password": "SecurePass123!"}),
                           content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


def test_stores_public_only_active(store, other_store):
    other_store.active = False
    other_store.save(update_fields=["active"])
    response = Client().get("/api/v1/stores")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [store.name]
    assert "staff" not in response.content.decode().lower()


def test_stores_do_not_expose_private_user_data(store, owner):
    body = Client().get("/api/v1/stores").content.decode()
    assert owner.email not in body and "password" not in body


def test_login_rejects_get(customer):
    assert Client().get("/api/v1/auth/login").status_code == 405

