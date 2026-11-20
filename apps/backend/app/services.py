import uuid

from .db import now_iso
from .security import hash_password, new_token


def find_profile_by_email(conn, email: str):
    return conn.execute("SELECT * FROM profiles WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()


def create_profile(conn, *, role: str, nombres: str, apellidos: str, email: str, password: str, store: str):
    profile_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO profiles
           (id, role, name, nombres, apellidos, email, password_hash, store, activo, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (
            profile_id,
            role,
            f"{nombres} {apellidos}".strip(),
            nombres.strip(),
            apellidos.strip(),
            email.strip().lower(),
            hash_password(password),
            store.strip(),
            now_iso(),
        ),
    )
    return conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()


def create_session(conn, profile_id: str) -> str:
    token = new_token()
    conn.execute(
        "INSERT INTO sessions (token, profile_id, creado_en) VALUES (?, ?, ?)",
        (token, profile_id, now_iso()),
    )
    return token
