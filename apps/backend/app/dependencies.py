from fastapi import Depends, Header, HTTPException, status

from .db import get_connection
from .permissions import JEFE


def get_current_profile(authorization: str | None = Header(default=None), conn=Depends(get_connection)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere un token Bearer.")

    token = authorization.split(" ", 1)[1].strip()
    row = conn.execute(
        """SELECT p.* FROM sessions s
           JOIN profiles p ON p.id = s.profile_id
           WHERE s.token = ? AND s.revocado_en IS NULL AND p.activo = 1""",
        (token,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o cuenta sin acceso.")
    return dict(row)


def get_jefe_profile(profile: dict = Depends(get_current_profile)) -> dict:
    if profile["role"] != JEFE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el jefe puede realizar esta acción.")
    return profile
