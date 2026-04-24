"""
supabase_client.py — Direct PostgreSQL connection to Supabase.

NO Supabase SDK. NO RLS. NO policies. NO auth complexity.
Just raw psycopg2 SQL — like using MongoDB Atlas directly.

All writes/reads hit the Supabase Postgres DB instantly and
reflect in the Supabase dashboard in real-time.
"""

import os
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CONNECTION STRING
# ---------------------------------------------------------------------------
# Grab it from: Supabase Dashboard → Settings → Database → Connection string
# Format: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
#
# Paste it in your .env file as DATABASE_URL
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "")

# In-memory fallback when no DATABASE_URL is set
_fallback_store = []


# ---------------------------------------------------------------------------
# CONNECTION HELPER
# ---------------------------------------------------------------------------
@contextmanager
def get_conn():
    """
    Yield a psycopg2 connection with autocommit=True so every
    INSERT / UPDATE / DELETE is immediately committed — no caching,
    no delayed sync.  Shows up in Supabase dashboard instantly.
    """
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


def _db_available() -> bool:
    """Check if we have a valid DATABASE_URL."""
    return bool(DATABASE_URL)


# ---------------------------------------------------------------------------
# AUTO-CREATE TABLES ON IMPORT  (idempotent — safe to run every time)
# ---------------------------------------------------------------------------
_INIT_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.analyses (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name   TEXT NOT NULL,
    material    TEXT NOT NULL,
    risk_score  REAL NOT NULL,
    risk_label  TEXT NOT NULL,
    confidence  REAL,
    features    JSONB,
    violations  JSONB,
    shap_values JSONB,
    recommendations JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.analyses ADD COLUMN IF NOT EXISTS top_issues JSONB;
ALTER TABLE public.analyses ADD COLUMN IF NOT EXISTS estimated_cost_impact INTEGER DEFAULT 0;
ALTER TABLE public.analyses ADD COLUMN IF NOT EXISTS cost_breakdown JSONB;
ALTER TABLE public.analyses ADD COLUMN IF NOT EXISTS confidence REAL;

-- Disable RLS so every query works without policies
ALTER TABLE public.analyses DISABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON public.analyses (created_at DESC);
"""


def _ensure_tables():
    """Run the init SQL once at import time."""
    if not _db_available():
        print("[db] No DATABASE_URL found. Using in-memory fallback.")
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_INIT_SQL)
        print("[db] ✅ Connected to Supabase PostgreSQL — tables ready.")
    except Exception as e:
        print(f"[db] ⚠️  Could not initialize tables: {e}")


_ensure_tables()


# ===================================================================
#  CRUD — ANALYSES
# ===================================================================

def store_analysis(
    file_name: str,
    material: str,
    risk_score: float,
    risk_label: str,
    confidence: float | None,
    features: dict,
    violations: list,
    shap_values: dict,
    recommendations: dict,
    top_issues: list | None = None,
    estimated_cost_impact: int = 0,
    cost_breakdown: list | None = None,
) -> dict:
    """INSERT a new analysis record.  Returns the stored row."""
    if not _db_available():
        record = {
            "id": str(uuid.uuid4()),
            "file_name": file_name,
            "material": material,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "confidence": confidence,
            "features": features,
            "violations": violations,
            "shap_values": shap_values,
            "recommendations": recommendations,
            "top_issues": top_issues or [],
            "estimated_cost_impact": max(0, int(estimated_cost_impact or 0)),
            "cost_breakdown": cost_breakdown or ["Minimal additional tooling cost"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _fallback_store.insert(0, record)
        if len(_fallback_store) > 50:
            _fallback_store.pop()
        return record

    sql = """
        INSERT INTO analyses (file_name, material, risk_score, risk_label,
                              confidence,
                              features, violations, shap_values, recommendations,
                              top_issues, estimated_cost_impact, cost_breakdown)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                file_name, material, risk_score, risk_label,
                confidence,
                Json(features), Json(violations),
                Json(shap_values), Json(recommendations),
                Json(top_issues or []),
                max(0, int(estimated_cost_impact or 0)),
                Json(cost_breakdown or ["Minimal additional tooling cost"]),
            ))
            row = cur.fetchone()
            return dict(row)


def get_analysis(analysis_id: str) -> dict | None:
    """SELECT a single analysis by UUID."""
    if not _db_available():
        return next((r for r in _fallback_store if r["id"] == analysis_id), None)

    sql = "SELECT * FROM analyses WHERE id = %s;"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (analysis_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_recent_analyses(limit: int = 10) -> list:
    """SELECT recent analyses ordered by created_at DESC."""
    if not _db_available():
        return _fallback_store[:limit]

    sql = """
        SELECT id, file_name, material, risk_score, risk_label, created_at
        FROM analyses
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(r) for r in cur.fetchall()]


def update_analysis(analysis_id: str, updates: dict) -> dict | None:
    """
    UPDATE an analysis record.  Pass only the fields you want to change.

    Example:
        update_analysis("some-uuid", {"risk_label": "low", "material": "steel"})
    """
    if not updates:
        return get_analysis(analysis_id)

    if not _db_available():
        for r in _fallback_store:
            if r["id"] == analysis_id:
                r.update(updates)
                return r
        return None

    # Build dynamic SET clause
    json_cols = {
        "features",
        "violations",
        "shap_values",
        "recommendations",
        "top_issues",
        "cost_breakdown",
    }
    set_parts = []
    values = []
    for col, val in updates.items():
        set_parts.append(f"{col} = %s")
        values.append(Json(val) if col in json_cols else val)
    values.append(analysis_id)

    sql = f"UPDATE analyses SET {', '.join(set_parts)} WHERE id = %s RETURNING *;"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, values)
            row = cur.fetchone()
            return dict(row) if row else None


def delete_analysis(analysis_id: str) -> bool:
    """DELETE an analysis by UUID.  Returns True if a row was removed."""
    if not _db_available():
        before = len(_fallback_store)
        _fallback_store[:] = [r for r in _fallback_store if r["id"] != analysis_id]
        return len(_fallback_store) < before

    sql = "DELETE FROM analyses WHERE id = %s;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (analysis_id,))
            return cur.rowcount > 0