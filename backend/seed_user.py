import os

from dotenv import load_dotenv

from db import execute
from security.password import hash_password

load_dotenv()

SEED_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@designcopilot.ai")
SEED_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123")


def seed_admin_user() -> None:
    password_hash = hash_password(SEED_PASSWORD)

    query = """
    INSERT INTO public.users (email, password)
    VALUES (%s, %s)
    ON CONFLICT (email) DO UPDATE
      SET password = EXCLUDED.password
    RETURNING id, email, created_at;
    """

    row = execute(query, (SEED_EMAIL, password_hash))
    print(f"Seeded user: {row['email']} ({row['id']})")


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not configured")
    seed_admin_user()
