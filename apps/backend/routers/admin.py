"""CU-01: platform administration. Kept separate from jefe/empleado routers."""

import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import email_exists, next_profile_id
from security import (
    create_token,
    fail,
    hash_password,
    identity_from_header,
    require,
    require_admin,
    verify_password,
)

router = APIRouter()

ROLES = ("admin", "jefe", "empleado", "cliente")
TABLES = {
    "admin": "Admin",
    "jefe": "Jefe",
    "empleado": "Empleado",
    "cliente": "Cliente",
}

USER_UNION = """
SELECT 'admin' AS rol, a.id, a.nombres, a.apellidos, a.correo,
       NULL::text AS bodega_nombre, a.estado,
       a.fecha_creacion::timestamptz AS fecha_creacion, a.ultimo_acceso
FROM Admin a
UNION ALL
SELECT 'jefe' AS rol, j.id, j.nombres, j.apellidos, j.correo,
       b.nombre AS bodega_nombre, COALESCE(j.estado, 'activo') AS estado,
       NULL::timestamptz AS fecha_creacion, NULL::timestamptz AS ultimo_acceso
FROM Jefe j JOIN Bodega b ON b.id = j.id_bodega
UNION ALL
SELECT 'empleado' AS rol, e.id, e.nombres, e.apellidos, e.correo,
       b.nombre AS bodega_nombre, COALESCE(e.estado, 'activo') AS estado,
       NULL::timestamptz AS fecha_creacion, NULL::timestamptz AS ultimo_acceso
FROM Empleado e
JOIN Jefe j ON j.id = e.id_jefe
JOIN Bodega b ON b.id = j.id_bodega
UNION ALL
SELECT 'cliente' AS rol, c.id, c.nombres, c.apellidos, c.correo,
       NULL::text AS bodega_nombre, c.estado,
       c.fecha_creacion::timestamptz AS fecha_creacion, NULL::timestamptz AS ultimo_acceso
FROM Cliente c
"""


def account_response(row) -> dict:
    return {
        "id": f"{row['rol']}:{row['id']}",
        "rol": row["rol"],
        "nombres": row["nombres"],
        "apellidos": row["apellidos"],
        "nombre": f"{row['nombres']} {row['apellidos']}".strip(),
        "correo": row["correo"],
        "bodegaNombre": row.get("bodega_nombre") or "",
        "activo": (row.get("estado") or "activo") == "activo",
        "creado": row["fecha_creacion"].isoformat() if row.get("fecha_creacion") else None,
        "ultimoAcceso": row["ultimo_acceso"].isoformat() if row.get("ultimo_acceso") else None,
    }


def admin_profile(row) -> dict:
    nombres = row["nombres"]
    apellidos = row["apellidos"]
    return {
        "id": row["id"],
        "rol": "admin",
        "nombres": nombres,
        "apellidos": apellidos,
        "nombre": f"{nombres} {apellidos}".strip(),
        "correo": row["correo"],
        "bodegaNombre": "Plataforma BodeSmart",
        "activo": (row.get("estado") or "activo") == "activo",
    }


def parse_uid(uid: str):
    try:
        rol, raw_id = str(uid).split(":", 1)
        profile_id = int(raw_id)
    except (ValueError, AttributeError):
        fail(400, "Identificador de cuenta inválido")
    if rol not in ROLES:
        fail(400, "Rol de cuenta inválido")
    return rol, profile_id


def guard_admin_target(rol: str, profile_id: int, who: dict):
    """Admins may maintain their own account, never another admin's."""
    if rol == "admin" and profile_id != who["id"]:
        fail(403, "Un administrador no puede modificar la cuenta de otro administrador")


def find_user(conn, rol: str, profile_id: int):
    row = conn.execute(
        f"SELECT * FROM ({USER_UNION}) AS usuarios WHERE rol = %s AND id = %s",
        (rol, profile_id),
    ).fetchone()
    return account_response(row) if row else None


def email_exists_except(conn, correo: str, rol: str, profile_id: int) -> bool:
    for table, table_role in TABLES.items():
        sql = f"SELECT id FROM {table} WHERE lower(correo) = lower(%s)"
        params = [correo]
        if table_role == rol:
            sql += " AND id <> %s"
            params.append(profile_id)
        if conn.execute(sql, params).fetchone():
            return True
    return False


def clean_text(value, field: str, limit: int = 100) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        fail(400, f"Falta el campo {field}")
    return text[:limit]


def clean_email(value) -> str:
    return str(value or "").strip().lower()


def clean_password(value) -> str:
    password = str(value or "")
    if len(password) < 8:
        fail(400, "La contraseña debe tener al menos 8 caracteres")
    return password


def clean_role(value) -> str:
    rol = str(value or "").strip().lower()
    if rol not in ROLES:
        fail(400, "Rol inválido. Opciones: " + ", ".join(ROLES))
    return rol


def warehouse_id(conn, value):
    try:
        bodega_id = int(value)
    except (TypeError, ValueError):
        fail(400, "Se requiere una bodega válida")
    if not conn.execute("SELECT id FROM Bodega WHERE id = %s", (bodega_id,)).fetchone():
        fail(404, "Bodega no encontrada")
    return bodega_id


@router.post("/admin/auth/login")
def admin_login(body: dict = Body(...)):
    require(body, "correo", "password")
    correo = clean_email(body["correo"])
    password = str(body["password"])
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT * FROM Admin WHERE lower(correo) = lower(%s)", (correo,)
        ).fetchone()
        if not row or not verify_password(password, row["password"]):
            fail(401, "Correo o contraseña incorrectos")
        if (row.get("estado") or "activo") != "activo":
            fail(403, "Esa cuenta de administrador está desactivada")
        conn.execute(
            "UPDATE Admin SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = %s",
            (row["id"],),
        )
        perfil = admin_profile(row)
    return {"token": create_token(row["id"], "admin"), "perfil": perfil}


@router.get("/admin/me")
def admin_me(who: dict = Depends(require_admin)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute("SELECT * FROM Admin WHERE id = %s", (who["id"],)).fetchone()
    if not row or (row.get("estado") or "activo") != "activo":
        fail(401, "La cuenta ya no tiene acceso")
    return admin_profile(row)


@router.get("/admin/stores")
def admin_stores(who: dict = Depends(require_admin)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        rows = conn.execute(
            "SELECT b.id, b.nombre, b.direccion FROM Bodega b ORDER BY b.nombre, b.id"
        ).fetchall()
    return [{"id": row["id"], "nombre": row["nombre"], "direccion": row["direccion"] or ""} for row in rows]


@router.get("/admin/users")
def admin_users(who: dict = Depends(require_admin)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        rows = conn.execute(
            f"SELECT * FROM ({USER_UNION}) AS usuarios "
            "ORDER BY lower(nombres || ' ' || apellidos), rol, id"
        ).fetchall()
    return [account_response(row) for row in rows]


@router.post("/admin/users")
def create_user(body: dict = Body(...), who: dict = Depends(require_admin)):
    require(body, "nombres", "apellidos", "correo", "password", "rol")
    rol = clean_role(body["rol"])
    nombres = clean_text(body["nombres"], "nombres")
    apellidos = clean_text(body["apellidos"], "apellidos")
    correo = clean_email(body["correo"])
    if not correo:
        fail(400, "Falta el campo correo")
    password = clean_password(body["password"])
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if email_exists(conn, correo):
            fail(409, "Ya existe una cuenta con ese correo")
        profile_id = next_profile_id(conn)
        if rol in ("jefe", "empleado"):
            bodega_id = warehouse_id(conn, body.get("id_bodega"))
        else:
            bodega_id = None
        if rol == "jefe":
            if conn.execute("SELECT id FROM Jefe WHERE id_bodega = %s", (bodega_id,)).fetchone():
                fail(409, "Esa bodega ya tiene un jefe")
            conn.execute(
                """INSERT INTO Jefe (id, nombres, apellidos, correo, password, id_bodega, estado)
                   VALUES (%s, %s, %s, %s, %s, %s, 'activo')""",
                (profile_id, nombres, apellidos, correo, hash_password(password), bodega_id),
            )
        elif rol == "empleado":
            jefe = conn.execute(
                "SELECT id FROM Jefe WHERE id_bodega = %s AND COALESCE(estado, 'activo') = 'activo'",
                (bodega_id,),
            ).fetchone()
            if not jefe:
                fail(409, "La bodega no tiene un jefe activo")
            conn.execute(
                """INSERT INTO Empleado
                   (id, nombres, apellidos, correo, password, id_jefe, estado)
                   VALUES (%s, %s, %s, %s, %s, %s, 'activo')""",
                (profile_id, nombres, apellidos, correo, hash_password(password), jefe["id"]),
            )
        elif rol == "admin":
            conn.execute(
                """INSERT INTO Admin (id, nombres, apellidos, correo, password, estado)
                   VALUES (%s, %s, %s, %s, %s, 'activo')""",
                (profile_id, nombres, apellidos, correo, hash_password(password)),
            )
        else:
            conn.execute(
                """INSERT INTO Cliente (id, nombres, apellidos, correo, password, estado)
                   VALUES (%s, %s, %s, %s, %s, 'activo')""",
                (profile_id, nombres, apellidos, correo, hash_password(password)),
            )
        perfil = find_user(conn, rol, profile_id)
    return perfil


@router.patch("/admin/users/{uid}")
def update_user(uid: str, body: dict = Body(...), who: dict = Depends(require_admin)):
    rol, profile_id = parse_uid(uid)
    guard_admin_target(rol, profile_id, who)
    if "rol" in body:
        fail(400, "El rol no se cambia: crea otra cuenta y desactiva la anterior")
    allowed = {"nombres", "apellidos", "correo", "password", "estado", "id_bodega"}
    changes = {key: value for key, value in body.items() if key in allowed}
    if not changes:
        fail(400, "No se enviaron campos para actualizar")
    table = TABLES[rol]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = %s", (profile_id,)).fetchone()
        if not row:
            fail(404, "Cuenta no encontrada")
        if rol == "admin" and changes.get("estado") not in (None, "activo"):
            fail(400, "No puedes desactivar tu propia cuenta")
        updates = []
        params = []
        for field in ("nombres", "apellidos"):
            if field in changes:
                updates.append(f"{field} = %s")
                params.append(clean_text(changes[field], field))
        if "correo" in changes:
            correo = clean_email(changes["correo"])
            if not correo:
                fail(400, "Falta el campo correo")
            if email_exists_except(conn, correo, rol, profile_id):
                fail(409, "Ya existe una cuenta con ese correo")
            updates.append("correo = %s")
            params.append(correo)
        if "password" in changes and changes["password"] not in (None, ""):
            updates.append("password = %s")
            params.append(hash_password(clean_password(changes["password"])))
        if "estado" in changes:
            estado = str(changes["estado"]).strip().lower()
            if estado not in ("activo", "inactivo"):
                fail(400, "Estado inválido. Opciones: activo, inactivo")
            updates.append("estado = %s")
            params.append(estado)
        if "id_bodega" in changes:
            bodega_id = warehouse_id(conn, changes["id_bodega"])
            if rol == "empleado":
                jefe = conn.execute(
                    "SELECT id FROM Jefe WHERE id_bodega = %s AND COALESCE(estado, 'activo') = 'activo'",
                    (bodega_id,),
                ).fetchone()
                if not jefe:
                    fail(409, "La bodega no tiene un jefe activo")
                updates.append("id_jefe = %s")
                params.append(jefe["id"])
            elif rol == "jefe":
                other = conn.execute(
                    "SELECT id FROM Jefe WHERE id_bodega = %s AND id <> %s",
                    (bodega_id, profile_id),
                ).fetchone()
                if other:
                    fail(409, "Esa bodega ya tiene un jefe")
                updates.append("id_bodega = %s")
                params.append(bodega_id)
        if not updates:
            fail(400, "No se enviaron campos válidos para actualizar")
        params.append(profile_id)
        conn.execute(f"UPDATE {table} SET {', '.join(updates)} WHERE id = %s", params)
        perfil = find_user(conn, rol, profile_id)
    return perfil


@router.delete("/admin/users/{uid}")
def deactivate_user(uid: str, who: dict = Depends(require_admin)):
    """CU-01 keeps history: deletion is a revocation, never a physical delete."""
    rol, profile_id = parse_uid(uid)
    guard_admin_target(rol, profile_id, who)
    if rol == "admin":
        fail(400, "No puedes desactivar tu propia cuenta")
    table = TABLES[rol]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(f"SELECT id FROM {table} WHERE id = %s", (profile_id,)).fetchone()
        if not row:
            fail(404, "Cuenta no encontrada")
        conn.execute(f"UPDATE {table} SET estado = 'inactivo' WHERE id = %s", (profile_id,))
        if rol == "empleado":
            # Products created by a revoked employee remain, but become
            # jefe-only rows, as ADR-001 requires for the existing flow.
            conn.execute(
                "UPDATE ProductosBodega SET bloqueado = TRUE, bloqueado_por = NULL "
                "WHERE creado_por = %s",
                (profile_id,),
            )
        perfil = find_user(conn, rol, profile_id)
    return {"ok": True, "perfil": perfil}
