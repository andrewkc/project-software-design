import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import email_exists, fetch_profile, next_profile_id
from security import create_token, fail, hash_password, identity_from_header, require, verify_password

router = APIRouter()


@router.post("/auth/signup")
def signup(body: dict = Body(...)):
    require(body, "nombres", "apellidos", "correo", "password", "nombre_bodega")
    if len(str(body["password"])) < 8:
        fail(400, "La contraseña debe tener al menos 8 caracteres")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if email_exists(conn, body["correo"]):
            fail(409, "Ya existe una cuenta con ese correo")
        # Reuse a seeded warehouse that has no manager, so its inventory
        # stays attached to the account created from the signup screen.
        bodega = conn.execute(
            """SELECT b.id FROM Bodega b
               WHERE b.nombre = %s
                 AND NOT EXISTS (SELECT 1 FROM Jefe j WHERE j.id_bodega = b.id)
               ORDER BY b.id LIMIT 1""",
            (body["nombre_bodega"],),
        ).fetchone()
        if not bodega:
            bodega = conn.execute(
                "INSERT INTO Bodega (nombre, direccion) VALUES (%s, %s) RETURNING id",
                (body["nombre_bodega"], ""),
            ).fetchone()
        jefe = conn.execute(
            """INSERT INTO Jefe (id, nombres, apellidos, correo, password, id_bodega)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (
                next_profile_id(conn), body["nombres"], body["apellidos"],
                body["correo"].strip().lower(), hash_password(str(body["password"])), bodega["id"],
            ),
        ).fetchone()
        who = {"id": jefe["id"], "rol": "jefe"}
        perfil = fetch_profile(conn, who)
    return {"token": create_token(who["id"], who["rol"]), "perfil": perfil}


@router.post("/auth/login")
def login(body: dict = Body(...)):
    require(body, "correo", "password")
    correo = str(body["correo"]).strip().lower()
    password = str(body["password"])
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        jefe = conn.execute("SELECT * FROM Jefe WHERE lower(correo) = lower(%s)", (correo,)).fetchone()
        if jefe:
            if (jefe.get("estado") or "activo") != "activo":
                fail(403, "Esa cuenta está desactivada")
            if not verify_password(password, jefe["password"]):
                fail(401, "Correo o contraseña incorrectos")
            who = {"id": jefe["id"], "rol": "jefe"}
        else:
            empleado = conn.execute("SELECT * FROM Empleado WHERE lower(correo) = lower(%s)", (correo,)).fetchone()
            if not empleado:
                fail(401, "Correo o contraseña incorrectos")
            if (empleado.get("estado") or "activo") != "activo":
                fail(403, "Esa cuenta ya no tiene acceso a la bodega")
            if not verify_password(password, empleado["password"]):
                fail(401, "Correo o contraseña incorrectos")
            who = {"id": empleado["id"], "rol": "empleado"}
        perfil = fetch_profile(conn, who)
    return {"token": create_token(who["id"], who["rol"]), "perfil": perfil}


@router.get("/auth/me")
def me(who: dict = Depends(identity_from_header)):
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        perfil = fetch_profile(conn, who)
    if not perfil or not perfil["activo"]:
        fail(401, "La cuenta ya no tiene acceso")
    return perfil


@router.post("/auth/change-password")
def change_password(body: dict = Body(...), who: dict = Depends(identity_from_header)):
    require(body, "password_actual", "password_nueva")
    if len(str(body["password_nueva"])) < 8:
        fail(400, "La contraseña nueva debe tener al menos 8 caracteres")
    table = "Jefe" if who["rol"] == "jefe" else "Empleado"
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        row = conn.execute(f"SELECT password FROM {table} WHERE id = %s", (who["id"],)).fetchone()
        if not row or not verify_password(str(body["password_actual"]), row["password"]):
            fail(400, "La contraseña actual no es correcta")
        conn.execute(
            f"UPDATE {table} SET password = %s WHERE id = %s",
            (hash_password(str(body["password_nueva"])), who["id"]),
        )
    return {"ok": True}
