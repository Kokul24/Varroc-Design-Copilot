import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "1"))
REFRESH_EXPIRE_HOURS = int(os.getenv("REFRESH_EXPIRE_HOURS", "168"))

_WEAK_SECRET_MARKERS = {
    "change-this-jwt-secret",
    "changeme",
    "change-me",
    "default",
    "secret",
    "jwt-secret",
}


def _validate_jwt_secret(secret: str | None) -> None:
    if not secret or secret.startswith("<"):
        raise RuntimeError("JWT_SECRET must be set in environment")

    normalized = secret.strip().lower()
    if len(secret.strip()) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters long")

    if normalized in _WEAK_SECRET_MARKERS or "change-this" in normalized:
        raise RuntimeError("JWT_SECRET uses a default/weak value and must be replaced")


_validate_jwt_secret(JWT_SECRET)


def create_access_token(user_id: str, email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=REFRESH_EXPIRE_HOURS)
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def decode_access_token(token: str) -> dict:
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict:
    return decode_token(token, expected_type="refresh")
