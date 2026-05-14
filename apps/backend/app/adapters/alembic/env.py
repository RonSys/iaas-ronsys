"""
Alembic Environment Configuration — Async.

Usa SQLAlchemy async engine con PostgreSQL.
Carga la URL desde app.config.settings.

DEV-02: Import-safe — no accede a context.config a nivel módulo.
         run_async_migrations() es await-able desde main.py lifespan.
"""

import asyncio
from logging.config import fileConfig

from alembic import context as _alembic_context  # noqa: F401 — proxy global
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.adapters.db.models.accounting import Base


def _get_config():
    """Lazy access — solo funciona dentro del runtime de alembic."""
    return _alembic_context.config


# Metadata para autogenerate (incluye accounting + auth + restaurant)
import app.models.user  # noqa: E402, F401 — registra tablas en Base.metadata
import app.adapters.db.models.restaurant  # noqa: E402, F401 — registra tablas restaurante
target_metadata = Base.metadata


def _setup_logging():
    """Configura logging si hay config file."""
    config = _get_config()
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (genera SQL sin conectar)."""
    _setup_logging()
    config = _get_config()
    url = config.get_main_option("sqlalchemy.url")
    _alembic_context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with _alembic_context.begin_transaction():
        _alembic_context.run_migrations()


def do_run_migrations(connection):
    """Ejecuta migraciones con la conexión dada."""
    _alembic_context.configure(connection=connection, target_metadata=target_metadata)
    with _alembic_context.begin_transaction():
        _alembic_context.run_migrations()


async def run_async_migrations() -> None:
    """
    DEV-02: Ejecuta migraciones online — await-able desde main.py lifespan.

    Usa create_async_engine directamente en vez de depender de alembic.ini.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Wrapper para modo online async (CLI directo — alembic upgrade head)."""
    asyncio.run(run_async_migrations())


# ─── Auto-ejecución: solo cuando alembic CLI carga env.py ──
# Cuando main.py importa run_async_migrations, salta esto.
def _is_alembic_cli() -> bool:
    import sys
    return any("alembic" in a for a in sys.argv)


if _is_alembic_cli():
    if _alembic_context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()