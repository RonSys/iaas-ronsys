"""Baseline — Esquema completo desde modelos ORM.

Migration única que crea TODAS las tablas del sistema usando
SQLAlchemy ORM metadata.create_all().

Esta migración reemplaza las migraciones 0001-0012 que tenían
problemas de ordenamiento de FKs y cabezas divergentes.

Revision ID: 0000_baseline
Revises: None
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0000_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea todas las tablas desde los modelos ORM actuales."""
    from app.adapters.db.models import Base
    from sqlalchemy import create_engine
    from app.config import settings

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg")
    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()


def downgrade() -> None:
    """Elimina todas las tablas."""
    from app.adapters.db.models import Base
    from sqlalchemy import create_engine
    from app.config import settings

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg")
    sync_engine = create_engine(sync_url)
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()
