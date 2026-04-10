import os

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from db import fetch_one, get_db_connection
from security.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from security.password import verify_password

router = APIRouter()

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "").strip() or None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60,
        path="/",
        domain=COOKIE_DOMAIN,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 7,
        path="/",
        domain=COOKIE_DOMAIN,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie("refresh_token", path="/", domain=COOKIE_DOMAIN)


def _ensure_users_table() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.users (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )


try:
    _ensure_users_table()
except Exception:
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def get_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "", 1).strip()
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    payload = decode_access_token(token)

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = fetch_one(
        "SELECT id, email, created_at FROM public.users WHERE id = %s LIMIT 1;",
        (user_id,),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post("/login")
def login(payload: LoginRequest):
    user_row = fetch_one(
        "SELECT id, email, password FROM public.users WHERE email = %s LIMIT 1;",
        (payload.email.strip().lower(),),
    )

    if not user_row or not verify_password(payload.password, user_row["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user_row["id"]), user_row["email"])
    refresh_token = create_refresh_token(str(user_row["id"]), user_row["email"])

    response = JSONResponse(content={
        "authenticated": True,
        "user": {
            "id": str(user_row["id"]),
            "email": user_row["email"],
        },
    })
    _set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/refresh")
def refresh_session(refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    payload = decode_refresh_token(refresh_token)
    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = fetch_one(
        "SELECT id, email FROM public.users WHERE id = %s LIMIT 1;",
        (user_id,),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access = create_access_token(str(user["id"]), user["email"])
    new_refresh = create_refresh_token(str(user["id"]), user["email"])
    response = JSONResponse(content={"refreshed": True})
    _set_auth_cookies(response, new_access, new_refresh)
    return response


@router.post("/logout")
def logout():
    response = JSONResponse(content={"logged_out": True})
    _clear_auth_cookies(response)
    return response


@router.get("/dashboard-data")
def dashboard_data(current_user: dict = Depends(get_current_user)):
    return {
        "ok": True,
        "email": current_user["email"],
    }
