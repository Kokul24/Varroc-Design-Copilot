from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr

from db import fetch_one, get_db_connection
from security.jwt_utils import create_access_token, decode_access_token
from security.password import verify_password

router = APIRouter()


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


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    token = authorization.replace("Bearer ", "", 1).strip()
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

    token = create_access_token(str(user_row["id"]), user_row["email"])

    return {
        "authenticated": True,
        "token": token,
        "user": {
            "id": str(user_row["id"]),
            "email": user_row["email"],
        },
    }


@router.get("/dashboard-data")
def dashboard_data(current_user: dict = Depends(get_current_user)):
    return {
        "ok": True,
        "email": current_user["email"],
    }
