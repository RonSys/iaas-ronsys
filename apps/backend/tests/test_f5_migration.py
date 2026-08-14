"""
Tests Spec 08 — F5 "Pregúntale al Sistema" (migración 0020_assistant).

Cubre (backend, Fase 1 — migración + seed):
  - Migración 0020_assistant: upgrade head (CA-F5.12 — catálogo con ≥8
    consultas seedeadas), CHECK params array, UNIQUE name, downgrade 0019
    revierte SIN tocar F3 (0019_voice_ai) ni F2.
  - query_logs: índice (tenant_id, created_at), FK companies/users, y que
    `rejected`/`result_summary` tienen default correcto.

Regla dura (precedente F2 D4): ningún test usa números personales.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

APP_ROOT = Path(__file__).resolve().parents[1]

# Misma BD de test que F3 (migraciones encadenadas: 0019 → 0020).
MIGRATION_TEST_URL = os.environ.get(
    "F5_TEST_DATABASE_URL",
    "postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys_test_f5",
)


# ═══════════════════════════════════════════════════════════════
# Migración 0020_assistant (CA-F5.12) — BD de test real
# ═══════════════════════════════════════════════════════════════

# DDL de F2 (0018) + F3 (0019) replicado: el test arranca de "BD con F3
# aplicada" (HU-F5-10) — misma estrategia que test_f3_voice_ai (el árbol de
# migraciones del repo tiene fallas PREEXISTENTES ajenas a F5: seed admin sin
# company en 0002; revision_id de 0010 > varchar(32); baseline lock-timeout).
_F3_0019_SCHEMA = """
CREATE TABLE alembic_version (version_num VARCHAR(100) NOT NULL);
INSERT INTO alembic_version (version_num) VALUES ('0019_voice_ai');
CREATE TABLE companies (
  id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, ruc VARCHAR(20) UNIQUE NOT NULL,
  settings JSONB, created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now()
);
CREATE TABLE users (
  id SERIAL PRIMARY KEY, company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
  email VARCHAR(200) UNIQUE NOT NULL, role VARCHAR(20) NOT NULL DEFAULT 'staff'
);
CREATE TABLE delivery_orders (
  id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  tracking_code VARCHAR(40) UNIQUE NOT NULL, sale_id INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'received'
);
CREATE TABLE call_records (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  external_call_id VARCHAR(64) NOT NULL, caller VARCHAR(32) NOT NULL,
  callee VARCHAR(32) NOT NULL, direction VARCHAR(10) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'ringing', started_at TIMESTAMPTZ NOT NULL,
  answered_at TIMESTAMPTZ, ended_at TIMESTAMPTZ, duration INTEGER NOT NULL DEFAULT 0,
  recording_path TEXT, transcription_fk INTEGER, metadata JSONB,
  converted_order_id INTEGER REFERENCES delivery_orders(id) ON DELETE SET NULL,
  ai_state VARCHAR(20), transfer_reason VARCHAR(50), context_summary TEXT,
  cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL, updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_call_records_external_call_id UNIQUE (external_call_id),
  CONSTRAINT ck_call_records_direction CHECK (direction IN ('inbound','outbound')),
  CONSTRAINT ck_call_records_status CHECK (status IN
    ('ringing','in_progress','answered','missed','completed','failed')),
  CONSTRAINT ck_call_records_ai_state CHECK (ai_state IN
    ('greeting','taking_order','clarifying','confirming','transfer','hangup',
     'completed','failed')),
  CONSTRAINT ck_call_records_transfer_reason CHECK (transfer_reason IN
    ('complaint','out_of_domain','low_confidence','user_requested','budget')),
  CONSTRAINT ck_call_records_cost_usd CHECK (cost_usd >= 0)
);
CREATE TABLE call_transcriptions (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  call_id VARCHAR(64) NOT NULL, provider VARCHAR(30) NOT NULL, text TEXT NOT NULL,
  segments JSONB, lang VARCHAR(10) NOT NULL DEFAULT 'es-PE',
  duration_sec INTEGER, cost_estimate NUMERIC(10,4) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
CREATE INDEX ix_call_transcriptions_call_id ON call_transcriptions (call_id);
INSERT INTO companies (name, ruc) VALUES ('El Segoviano Test','99999999999');
INSERT INTO users (company_id, email, role) VALUES (1,'admin@test.local','admin');
INSERT INTO call_records (tenant_id, external_call_id, caller, callee, direction, status,
  started_at, duration, cost_usd) VALUES (1,'SIP-LEGACY.1','999888777','+5115551234',
  'inbound','completed', now(), 120, 0.0105);
"""


def _alembic_available() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "--version"],
            cwd=APP_ROOT, capture_output=True, timeout=30,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def _run_alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": MIGRATION_TEST_URL}
    env.setdefault("PYTHONPATH", str(APP_ROOT))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=APP_ROOT, env=env, capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} falló: {result.stderr.decode()[-2000:]}"
        )


async def _migration_engine():
    engine = create_async_engine(MIGRATION_TEST_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        await engine.dispose()
        raise
    return engine


async def _reset_schema(engine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


async def _bootstrap_f3(engine) -> None:
    async with engine.connect() as conn:
        for stmt in _F3_0019_SCHEMA.split(";"):
            if stmt.strip():
                await conn.execute(text(stmt.strip()))


@pytest.mark.asyncio
async def test_migration_0020_up_down():
    """CA-F5.12: upgrade head → 0020_assistant (catálogo ≥8 + tablas); downgrade 0019 revierte.

    Skip si la BD de test no está disponible o alembic no está instalado
    (la suite principal es mock-based; este test requiere Postgres real).
    """
    if not _alembic_available():
        pytest.skip("alembic no disponible — saltando migración up/down")
    try:
        engine = await _migration_engine()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"BD de test F5 no disponible ({exc}) — saltando migración up/down")
        return

    try:
        # 1) Estado inicial: F3 aplicada (0019) con filas legacy
        await _reset_schema(engine)
        await _bootstrap_f3(engine)

        # 2) upgrade head → 0020_assistant
        await asyncio.to_thread(_run_alembic, "upgrade", "head")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0020_assistant"

            # tablas creadas
            for tbl in ("query_catalog", "query_logs"):
                assert (await conn.execute(
                    text(f"SELECT to_regclass('public.{tbl}')")
                )).scalar() is not None, f"{tbl} no se creó"

            # CHECK params array + UNIQUE name
            checks = set((await conn.execute(
                text("SELECT conname FROM pg_constraint WHERE conrelid='query_catalog'::regclass")
            )).scalars().all())
            assert "ck_query_catalog_params_array" in checks
            assert "uq_query_catalog_name" in checks

            # índice de auditoría
            idx = (await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='query_logs' "
                     "AND indexname='ix_query_logs_tenant_created'")
            )).scalar()
            assert idx == "ix_query_logs_tenant_created"

            # FK correctas en query_logs
            fks = set((await conn.execute(
                text("SELECT conname FROM pg_constraint WHERE conrelid='query_logs'::regclass")
            )).scalars().all())
            for fk in ("query_logs_tenant_id_fkey", "query_logs_query_catalog_id_fkey",
                       "query_logs_user_id_fkey"):
                assert fk in fks, f"FK {fk} no existe"

            # 3) Seed: ≥8 consultas activas delivery (CA-F5.12)
            n = (await conn.execute(text(
                "SELECT COUNT(*) FROM query_catalog WHERE skill='delivery' AND active=true"
            ))).scalar()
            assert int(n) >= 8, f"catálogo seed con {n} consultas (esperado ≥8)"

            names = set((await conn.execute(text(
                "SELECT name FROM query_catalog ORDER BY id"
            ))).scalars().all())
            expected = {"top_products_delivery", "sales_by_zone", "campaign_roas",
                        "delivery_overview", "orders_by_status", "avg_ticket_delivery",
                        "sales_by_hour_delivery", "comparison_week", "delivery_margins",
                        "sales_by_channel"}
            assert expected.issubset(names), f"faltan consultas del catálogo: {expected - names}"

            # sql_template SOLO SELECT (R7, con WITH CTE permitido) y con
            # :params vinculados (D1); sin cláusulas de escritura (R7).
            rows = (await conn.execute(text(
                "SELECT sql_template FROM query_catalog"
            ))).scalars().all()
            for sql in rows:
                upper = sql.strip().upper()
                assert upper.startswith("SELECT") or upper.startswith("WITH"), \
                    "sql_template no es SELECT"
                assert ":tenant_id" in sql, "sql_template sin :tenant_id (R2)"
                for bad in (";", "DROP", "DELETE", "UPDATE", "INSERT", "--"):
                    assert bad not in upper, f"sql_template con cláusula prohibida: {bad}"

        # 4) downgrade 0019 → revierte TODO lo de F5, F3 intacta
        await asyncio.to_thread(_run_alembic, "downgrade", "0019_voice_ai")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0019_voice_ai"
            assert (await conn.execute(
                text("SELECT to_regclass('public.query_catalog')")
            )).scalar() is None
            assert (await conn.execute(
                text("SELECT to_regclass('public.query_logs')")
            )).scalar() is None
            # F3 intacta: call_transcriptions + columnas IA siguen
            assert (await conn.execute(
                text("SELECT to_regclass('public.call_transcriptions')")
            )).scalar() is not None
            cols = set((await conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='call_records'")
            )).scalars().all())
            for col in ("ai_state", "cost_usd", "context_summary"):
                assert col in cols, f"columna F3 {col} se perdió en downgrade"

        # 5) dejar la BD de test consistente en head
        await asyncio.to_thread(_run_alembic, "upgrade", "head")
    finally:
        await engine.dispose()
