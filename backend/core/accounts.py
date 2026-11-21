"""Account and store administration with scoped permissions and audit."""

import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from . import services
from .models import AuditEvent, Reservation, Store, StorePricingPolicy, User


def _admin(actor):
    if not actor or not actor.is_authenticated or not actor.is_active or actor.role != User.Role.ADMIN:
        raise services.DomainError("FORBIDDEN", "Solo el administrador puede hacer esto", 403)


def _owner(actor):
    services.require_staff(actor, owner_only=True)


def _fields(data, allowed):
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise services.DomainError("INVALID_FIELDS", "Campos no permitidos")


def _bool(value, field):
    if not isinstance(value, bool):
        raise services.DomainError("INVALID_FIELD", f"{field} debe ser verdadero o falso")
    return value


def _audit(actor, action, entity, before, after, store=None):
    AuditEvent.objects.create(store=store, actor=actor, action=action, entity_id=entity.id,
                              entity=entity.__class__.__name__,
                              before=before, after=after, correlation_id=uuid.uuid4())


def store_payload(store):
    return {"id": str(store.id), "name": store.name, "address": store.address,
            "opening_hours": store.opening_hours, "active": store.active}


def user_payload(user):
    return {"id": str(user.id), "email": user.email, "name": user.name,
            "role": user.role, "store_id": str(user.store_id) if user.store_id else None,
            "active": user.is_active}


def list_stores(actor):
    _admin(actor)
    return list(Store.objects.order_by("name", "id"))


@transaction.atomic
def create_store(actor, data):
    _admin(actor)
    _fields(data, ("name", "address", "opening_hours"))
    store = Store(name=services.required_text(data.get("name"), "Nombre", 150),
                  address=services.required_text(data.get("address"), "Dirección", 500),
                  opening_hours=(services.required_text(data.get("opening_hours"), "Horario", 120)
                                                       if data.get("opening_hours") != "" and "opening_hours" in data
                                                       else "08:00–20:00"))
    services._model_save(store)
    _audit(actor, "STORE_CREATED", store, None, store_payload(store), store)
    return store


@transaction.atomic
def update_store(actor, store_id, data):
    _admin(actor)
    _fields(data, ("name", "address", "opening_hours", "active"))
    if not data:
        raise services.DomainError("INVALID_FIELDS", "Indica un cambio")
    store = Store.objects.select_for_update().filter(pk=services.parse_uuid(store_id, "store_id")).first()
    if store is None:
        raise services.DomainError("NOT_FOUND", "Bodega no encontrada", 404)
    before = store_payload(store)
    for field, limit in (("name", 150), ("address", 500), ("opening_hours", 120)):
        if field in data:
            setattr(store, field, services.required_text(data[field], field, limit))
    if "active" in data:
        active = _bool(data["active"], "active")
        if not active and store.active and Reservation.objects.filter(
                line__order__store=store, state=Reservation.State.ACTIVE).exists():
            raise services.DomainError("ACTIVE_RESERVATIONS", "La bodega tiene pedidos reservados", 409)
        store.active = active
    if before != store_payload(store):
        services._model_save(store)
        _audit(actor, "STORE_UPDATED", store, before, store_payload(store), store)
    return store


def list_users(actor):
    _admin(actor)
    return list(User.objects.order_by("role", "email"))


def list_staff(actor):
    _owner(actor)
    return list(User.objects.filter(store_id=actor.store_id, role=User.Role.EMPLOYEE).order_by("email"))


@transaction.atomic
def create_user(actor, data, staff_only=False):
    _owner(actor) if staff_only else _admin(actor)
    allowed = ("email", "name", "password") if staff_only else ("email", "name", "password", "role", "store_id")
    _fields(data, allowed)
    role = User.Role.EMPLOYEE if staff_only else data.get("role")
    if role not in User.Role.values:
        raise services.DomainError("INVALID_ROLE", "Rol no válido")
    store = None
    if role in (User.Role.OWNER, User.Role.EMPLOYEE):
        store_id = actor.store_id if staff_only else services.parse_uuid(data.get("store_id"), "store_id")
        store = Store.objects.select_for_update().filter(pk=store_id, active=True).first()
        if not store:
            raise services.DomainError("NOT_FOUND", "Bodega activa no encontrada", 404)
        if role == User.Role.OWNER and User.objects.filter(store=store, role=role, is_active=True).exists():
            raise services.DomainError("OWNER_EXISTS", "La bodega ya tiene dueño activo", 409)
    elif data.get("store_id") not in (None, ""):
        raise services.DomainError("INVALID_STORE", "Este rol no pertenece a una bodega")
    email = services.required_text(data.get("email"), "Correo", 254).lower()
    name = services.required_text(data.get("name"), "Nombre", 120)
    password = data.get("password")
    if not isinstance(password, str):
        raise services.DomainError("INVALID_PASSWORD", "Contraseña inválida")
    user = User(email=email, name=name, role=role, store=store)
    try:
        validate_password(password, user)
        user = User.objects.create_user(email=email, password=password, name=name, role=role, store=store,
                                        is_staff=role == User.Role.ADMIN, is_superuser=role == User.Role.ADMIN)
    except ValidationError as error:
        raise services.DomainError("INVALID_DATA", "; ".join(error.messages)) from error
    if role == User.Role.OWNER and not StorePricingPolicy.objects.filter(store=store).exists():
        StorePricingPolicy.objects.create(store=store, version=1, mode=StorePricingPolicy.Mode.REVIEW,
                                          starts_at=user.created_at, created_by=user)
    _audit(actor, "STAFF_CREATED" if staff_only else "USER_CREATED", user, None, user_payload(user), store)
    return user


@transaction.atomic
def update_user(actor, user_id, data, staff_only=False):
    _owner(actor) if staff_only else _admin(actor)
    _fields(data, ("name", "active"))
    if not data:
        raise services.DomainError("INVALID_FIELDS", "Indica un cambio")
    user = User.objects.select_for_update().filter(pk=services.parse_uuid(user_id, "user_id")).first()
    if not user or (staff_only and (user.role != User.Role.EMPLOYEE or user.store_id != actor.store_id)):
        raise services.DomainError("NOT_FOUND", "Cuenta no encontrada", 404)
    before = user_payload(user)
    if "name" in data:
        user.name = services.required_text(data["name"], "Nombre", 120)
    if "active" in data:
        active = _bool(data["active"], "active")
        if not active and user.is_active:
            if user.role == User.Role.ADMIN and User.objects.select_for_update().filter(
                    role=User.Role.ADMIN, is_active=True).count() <= 1:
                raise services.DomainError("LAST_ADMIN", "No puedes desactivar al último administrador", 409)
            if user.role == User.Role.OWNER and user.store and user.store.active:
                raise services.DomainError("ACTIVE_OWNER", "Desactiva la bodega antes de retirar a su dueño", 409)
        if active and user.role == User.Role.OWNER and User.objects.filter(
                role=User.Role.OWNER, store=user.store, is_active=True).exclude(pk=user.pk).exists():
            raise services.DomainError("OWNER_EXISTS", "La bodega ya tiene dueño activo", 409)
        user.is_active = active
    if before != user_payload(user):
        services._model_save(user)
        _audit(actor, "STAFF_UPDATED" if staff_only else "USER_UPDATED", user, before, user_payload(user), user.store)
    return user
