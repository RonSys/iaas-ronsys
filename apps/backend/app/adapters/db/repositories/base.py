"""
🗄️ BaseRepository — Repositorio genérico con scoping automático por tenant.

HU-F0-001 (Gap 3+4): Proporciona operaciones CRUD base con WHERE tenant_id
                     automático y asignación de tenant_id en INSERT.

Uso:
    class TableRepository(BaseRepository[Table]):
        def __init__(self, session: AsyncSession, tenant_id: int):
            super().__init__(session, tenant_id, Table)

    repo = TableRepository(db, tenant_id=1)
    tables = await repo.list(db)           # scoped
    table = await repo.get_by_id(db, 5)    # scoped
    new_table = await repo.create(db, {"number": 10, "capacity": 4})
"""

from typing import Any, Generic, Optional, Type, TypeVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Repositorio CRUD genérico con tenant scoping automático.

    Todas las operaciones de lectura filtran por tenant_id.
    Las operaciones de escritura asignan tenant_id automáticamente.

    Generic[T] donde T es el modelo ORM (SQLAlchemy DeclarativeBase).
    """

    def __init__(self, session: AsyncSession, tenant_id: int, model: Type[T]):
        self.session = session
        self.tenant_id = tenant_id
        self.model = model

    # ─── Lectura ──────────────────────────────────────────

    async def list(
        self,
        db: AsyncSession,
        **filters,
    ) -> list[T]:
        """
        Lista entidades scoped por tenant_id.

        Filtros adicionales se aplican como keyword args: status="active", etc.
        """
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id  # type: ignore[attr-defined]
        )
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, id: int) -> T:
        """
        Obtiene una entidad por ID con scoping de tenant.

        Raises 404 si no existe o no pertenece al tenant.
        """
        stmt = select(self.model).where(
            self.model.id == id,  # type: ignore[attr-defined]
            self.model.tenant_id == self.tenant_id,  # type: ignore[attr-defined]
        )
        result = await db.execute(stmt)
        entity = result.scalar_one_or_none()
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"{self.model.__name__} no encontrado",
            )
        return entity

    async def get_by_id_or_none(self, db: AsyncSession, id: int) -> Optional[T]:
        """Como get_by_id pero sin lanzar 404 — retorna None si no existe."""
        stmt = select(self.model).where(
            self.model.id == id,  # type: ignore[attr-defined]
            self.model.tenant_id == self.tenant_id,  # type: ignore[attr-defined]
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ─── Escritura ────────────────────────────────────────

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> T:
        """
        Crea una entidad asignando tenant_id automáticamente.

        Args:
            db: AsyncSession
            data: Dict con los campos de la entidad (sin tenant_id)

        Returns:
            La entidad creada (ya flusheada).
        """
        entity = self.model(tenant_id=self.tenant_id, **data)  # type: ignore[call-arg]
        db.add(entity)
        await db.flush()
        await db.refresh(entity)
        return entity

    async def update(
        self, db: AsyncSession, id: int, data: dict[str, Any]
    ) -> T:
        """
        Actualiza una entidad con scoping de tenant.

        Args:
            db: AsyncSession
            id: ID de la entidad
            data: Dict con campos a actualizar (parcial)

        Returns:
            La entidad actualizada.

        Raises 404 si no existe o no pertenece al tenant.
        """
        entity = await self.get_by_id(db, id)
        for key, value in data.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)
        await db.flush()
        await db.refresh(entity)
        return entity

    async def delete(self, db: AsyncSession, id: int) -> None:
        """
        Elimina una entidad con scoping de tenant.

        Raises 404 si no existe o no pertenece al tenant.
        """
        entity = await self.get_by_id(db, id)
        await db.delete(entity)
        await db.flush()
