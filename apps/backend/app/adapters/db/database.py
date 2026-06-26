"""
Configuración de Base de Datos — SQLAlchemy Async

Responsabilidad:
  - Crear engine async con PostgreSQL
  - Session factory
  - Dependencia get_db() para FastAPI
  - Soporte para SQLite in-memory en tests

Basado en:
  - SQLAlchemy 2.0 async
  - PostgreSQL 16 (producción)
  - SQLite (tests)
"""

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Engine y session factory — se inicializan bajo demanda
_engine = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine():
    """Retorna el engine async, inicializándolo si es necesario."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retorna la session factory async."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia FastAPI que provee una sesión de BD por request.

    Uso:
        @router.get("/algo")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Utilidad para tests ───────────────────────────────────────


def reset_engine():
    """Resetea el engine y session factory (útil en tests para cambiar DB)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
