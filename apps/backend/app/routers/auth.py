from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_connection
from ..dependencies import get_current_profile
from ..mappers import profile_out
from ..permissions import JEFE
from ..schemas import ChangePasswordIn, LoginIn, ProfileOut, SignupIn, TokenOut
from ..security import hash_password, verify_password
from ..services import create_profile, create_session, find_profile_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, conn=Depends(get_connection)):
    if find_profile_by_email(conn, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con ese correo.")

    with conn:
        profile = create_profile(
            conn,
            role=JEFE,
            nombres=payload.nombres,
            apellidos=payload.apellidos,
            email=payload.email,
            password=payload.password,
            store=payload.store,
        )
        token = create_session(conn, profile["id"])
    return {"token": token, "profile": profile_out(profile)}


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, conn=Depends(get_connection)):
    profile = find_profile_by_email(conn, payload.email)
    if profile is None or not verify_password(payload.password, profile["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos.")
    if not profile["activo"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esa cuenta ya no tiene acceso.")

    with conn:
        token = create_session(conn, profile["id"])
    return {"token": token, "profile": profile_out(profile)}


@router.get("/me", response_model=ProfileOut)
def me(profile: dict = Depends(get_current_profile)):
    return profile_out(profile)


@router.post("/change-password", response_model=ProfileOut)
def change_password(payload: ChangePasswordIn, profile: dict = Depends(get_current_profile), conn=Depends(get_connection)):
    if not verify_password(payload.currentPassword, profile["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual no es correcta.")

    with conn:
        conn.execute(
            "UPDATE profiles SET password_hash = ? WHERE id = ?",
            (hash_password(payload.newPassword), profile["id"]),
        )
        updated = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile["id"],)).fetchone()
    return profile_out(updated)
