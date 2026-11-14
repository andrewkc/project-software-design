"""CU-01: platform administration of accounts. No access to store costs or sales."""

import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AuditEvent, Store, User
from .services import DomainError, required_text


GLOBAL_ROLES = (User.Role.ADMIN, User.Role.CUSTOMER)


def require_admin(actor):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise DomainError("AUTH_REQUIRED", "Inicia sesión", 401)
    if actor.role != User.Role.ADMIN:
        raise DomainError("FORBIDDEN", "No tienes permiso para esta operación", 403)


def account_payload(user):
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "store_id": str(user.store_id) if user.store_id else None,
        "store_name": user.store.name if user.store_id else None,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def store_payload(store):
    return {"id": str(store.id), "name": store.name, "active": store.active}


def list_accounts(actor):
    require_admin(actor)
    return User.objects.select_related("store").order_by("role", "name", "email")


def list_stores(actor):
    require_admin(actor)
    return Store.objects.order_by("name")


def create_account(actor, data):
    require_admin(actor)
    role = _role(data.get("role"))
    user = User(email=_email(data.get("email")), name=required_text(data.get("name"), "Nombre", 120),
                role=role, store=_store_for(role, data.get("store_id")), is_staff=role == User.Role.ADMIN)
    _set_password(user, data.get("password"))
    with transaction.atomic():
        _save(user)
        _audit(actor, "USER_CREATED", user, None)
    return user


def update_account(actor, user_id, data):
    require_admin(actor)
    with transaction.atomic():
        user = User.objects.select_for_update().filter(id=user_id).first()
        if not user:
            raise DomainError("NOT_FOUND", "Cuenta no encontrada", 404)
        before = _snapshot(user)
        if "name" in data:
            user.name = required_text(data["name"], "Nombre", 120)
        if "email" in data:
            user.email = _email(data["email"])
        if "role" in data:
            user.role = _role(data["role"])
        if "role" in data or "store_id" in data:
            user.store = _store_for(user.role, data.get("store_id", user.store_id))
        if "is_active" in data:
            if not isinstance(data["is_active"], bool):
                raise DomainError("INVALID_DATA", "Estado activo inválido")
            user.is_active = data["is_active"]
        # Blocking self-demotion also guarantees at least one active admin remains.
        if user.id == actor.id and (user.role != User.Role.ADMIN or not user.is_active):
            raise DomainError("SELF_LOCKOUT", "No puedes quitarte el rol de administrador ni desactivar tu cuenta")
        user.is_staff = user.role == User.Role.ADMIN
        if user.role != User.Role.ADMIN:
            user.is_superuser = False
        if "password" in data:
            _set_password(user, data["password"])
        _save(user)
        _audit(actor, "USER_UPDATED", user, before)
    return user


def _email(value):
    return str(value or "").strip().lower()


def _role(value):
    if value not in User.Role.values:
        raise DomainError("INVALID_ROLE", "Rol inválido")
    return value


def _store_for(role, store_id):
    if role in GLOBAL_ROLES:
        return None
    if not store_id:
        raise DomainError("INVALID_STORE", "Jefes y empleados requieren una bodega")
    try:
        store = Store.objects.filter(id=store_id).first()
    except (ValidationError, ValueError):
        store = None
    if not store:
        raise DomainError("INVALID_STORE", "Bodega no encontrada")
    return store


def _set_password(user, password):
    if not isinstance(password, str):
        raise DomainError("INVALID_PASSWORD", "Contraseña inválida")
    try:
        validate_password(password, user)
    except ValidationError as error:
        raise DomainError("INVALID_PASSWORD", "; ".join(error.messages)) from error
    user.set_password(password)


def _save(user):
    try:
        user.full_clean()
    except ValidationError as error:
        raise DomainError("INVALID_DATA", "; ".join(error.messages)) from error
    user.save()


def _snapshot(user):
    return {"name": user.name, "email": user.email, "role": user.role,
            "store_id": str(user.store_id) if user.store_id else None, "is_active": user.is_active}


def _audit(actor, action, user, before):
    AuditEvent.objects.create(actor=actor, action=action, entity="User", entity_id=user.id,
                              before=before, after=_snapshot(user), correlation_id=uuid.uuid4())
