"""CU-01: platform administration of accounts. No access to store costs or sales."""

from .models import Store, User
from .services import DomainError


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
