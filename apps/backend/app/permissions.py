JEFE = "jefe"
EMPLEADO = "empleado"


def is_jefe(profile: dict) -> bool:
    return profile["role"] == JEFE


def same_store(profile: dict, store: str) -> bool:
    return profile["store"] == store


def can_edit_product(product: dict, profile: dict) -> bool:
    """RN-10 y RN-11 / ADR-001.

    El jefe edita cualquier fila de su bodega, incluidas las bloqueadas.
    El empleado solo edita filas activas, desbloqueadas y creadas por él.
    """
    if not same_store(profile, product["store"]):
        return False
    if is_jefe(profile):
        return True
    return bool(product["activo"]) and not bool(product["bloqueado"]) and product["creado_por"] == profile["id"]


def can_deactivate(product: dict, profile: dict) -> bool:
    return is_jefe(profile) and same_store(profile, product["store"])
