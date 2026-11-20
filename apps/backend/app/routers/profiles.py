from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_connection, now_iso
from ..dependencies import get_jefe_profile
from ..mappers import profile_out
from ..permissions import EMPLEADO
from ..schemas import EmployeeCreateIn, ProfileOut
from ..services import create_profile, find_profile_by_email

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/employees", response_model=list[ProfileOut])
def list_employees(jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    rows = conn.execute(
        "SELECT * FROM profiles WHERE role = ? AND store = ? ORDER BY creado_en",
        (EMPLEADO, jefe["store"]),
    ).fetchall()
    return [profile_out(row) for row in rows]


@router.post("/employees", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreateIn, jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    if find_profile_by_email(conn, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con ese correo.")

    with conn:
        profile = create_profile(
            conn,
            role=EMPLEADO,
            nombres=payload.nombres,
            apellidos=payload.apellidos,
            email=payload.email,
            password=payload.password,
            store=jefe["store"],
        )
    return profile_out(profile)


@router.post("/employees/{employee_id}/revoke", response_model=ProfileOut)
def revoke_employee(employee_id: str, jefe: dict = Depends(get_jefe_profile), conn=Depends(get_connection)):
    employee = conn.execute(
        "SELECT * FROM profiles WHERE id = ? AND role = ? AND store = ?",
        (employee_id, EMPLEADO, jefe["store"]),
    ).fetchone()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado en tu bodega.")
    if not employee["activo"]:
        return profile_out(employee)

    revoked_at = now_iso()
    with conn:
        conn.execute(
            "UPDATE profiles SET activo = 0, revocado_en = ? WHERE id = ?",
            (revoked_at, employee_id),
        )
        conn.execute(
            "UPDATE sessions SET revocado_en = ? WHERE profile_id = ? AND revocado_en IS NULL",
            (revoked_at, employee_id),
        )
        # ADR-001: las filas del empleado retirado quedan bloqueadas y solo el jefe puede editarlas.
        conn.execute(
            "UPDATE products SET bloqueado = 1, bloqueado_por = ? WHERE creado_por = ?",
            (jefe["id"], employee_id),
        )
        updated = conn.execute("SELECT * FROM profiles WHERE id = ?", (employee_id,)).fetchone()
    return profile_out(updated)
