import base64
import hashlib
import hmac
import json
import time
from typing import Optional

import bcrypt
from fastapi import Header, HTTPException

from config import SECRET, TOKEN_HOURS


def fail(status: int, detail: str):
    raise HTTPException(status_code=status, detail=detail)


def require(data: dict, *keys: str):
    for key in keys:
        if key not in data or data[key] is None or str(data[key]).strip() == "":
            fail(400, f"Falta el campo {key}")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), str(stored).encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def create_token(profile_id: int, rol: str) -> str:
    payload = {
        "sub": profile_id,
        "rol": rol,
        "exp": int(time.time()) + TOKEN_HOURS * 3600,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def identity_from_header(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        fail(401, "Se requiere un token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            fail(401, "Token inválido")
        padding = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + padding).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            fail(401, "Token expirado")
        return {"id": payload["sub"], "rol": payload["rol"]}
    except (ValueError, KeyError, TypeError):
        fail(401, "Token inválido")
