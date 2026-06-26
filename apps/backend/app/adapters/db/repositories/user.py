"""
User Repository — Acceso a datos de usuarios.

Implementa operaciones CRUD para el modelo User con scoping por tenant.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.user import User


class UserRepository:
    """Repositorio de usuarios con scoping automático por company_id."""

    def __init__(self, session: AsyncSession, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id

    def _scope(self, stmt: Select) -> Select:
        """Agrega filtro de company_id a cualquier query."""
        return stmt.where(User.tenant_id == self.tenant_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = self._scope(select(User).where(User.email == email))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = self._scope(select(User).where(User.id == user_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        stmt = self._scope(select(User))

        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            stmt = stmt.where(
                (User.email.ilike(f"%{search}%"))
                | (User.full_name.ilike(f"%{search}%"))
            )

        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User) -> User:
        await self.session.flush()
        return user
