import psycopg
from fastapi import APIRouter, Body, Depends
from psycopg.rows import dict_row

from config import DSN
from database import bodega_id_for, email_exists, fetch_profile, next_profile_id, profile_response
from security import fail, hash_password, identity_from_header, require

router = APIRouter()


@router.get("/profiles")
def list_profiles(who: dict = Depends(identity_from_header)):
    if who["rol"] != "jefe":
        fail(403, "Solo el jefe puede ver las cuentas")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        bodega_id = bodega_id_for(conn, who)
        jefes = conn.execute(
            """SELECT j.*, b.nombre AS nombre_bodega
               FROM Jefe j JOIN Bodega b ON b.id = j.id_bodega
               WHERE j.id_bodega = %s ORDER BY j.id""",
            (bodega_id,),
        ).fetchall()
        empleados = conn.execute(
            """SELECT e.*, b.nombre AS nombre_bodega
               FROM Empleado e
               JOIN Jefe j ON j.id = e.id_jefe
               JOIN Bodega b ON b.id = j.id_bodega
               WHERE j.id_bodega = %s ORDER BY e.id""",
            (bodega_id,),
        ).fetchall()
    return [profile_response(row, "jefe") for row in jefes] + [profile_response(row, "empleado") for row in empleados]


@router.post("/profiles/employees")
def create_employee(body: dict = Body(...), who: dict = Depends(identity_from_header)):
    if who["rol"] != "jefe":
        fail(403, "Solo el jefe puede crear empleados")
    require(body, "nombres", "apellidos", "correo", "password")
    if len(str(body["password"])) < 8:
        fail(400, "La contraseña debe tener al menos 8 caracteres")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if email_exists(conn, body["correo"]):
            fail(409, "Ya existe una cuenta con ese correo")
        empleado = conn.execute(
            """INSERT INTO Empleado (id, nombres, apellidos, correo, password, id_jefe, estado)
               VALUES (%s, %s, %s, %s, %s, %s, 'activo') RETURNING id""",
            (
                next_profile_id(conn), body["nombres"], body["apellidos"],
                body["correo"].strip().lower(), hash_password(str(body["password"])), who["id"],
            ),
        ).fetchone()
        perfil = fetch_profile(conn, {"id": empleado["id"], "rol": "empleado"})
    return perfil


@router.post("/profiles/employees/{empleado_id}/revoke")
def revoke_employee(empleado_id: int, who: dict = Depends(identity_from_header)):
    if who["rol"] != "jefe":
        fail(403, "Solo el jefe puede revocar accesos")
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        target = conn.execute(
            "SELECT id FROM Empleado WHERE id = %s AND id_jefe = %s",
            (empleado_id, who["id"]),
        ).fetchone()
        if not target:
            fail(404, "Empleado no encontrado")
        conn.execute("UPDATE Empleado SET estado = 'revocado' WHERE id = %s", (empleado_id,))
        conn.execute(
            """UPDATE ProductosBodega
               SET bloqueado = TRUE, bloqueado_por = %s
               WHERE creado_por = %s""",
            (who["id"], empleado_id),
        )
        perfil = fetch_profile(conn, {"id": empleado_id, "rol": "empleado"})
    return perfil
