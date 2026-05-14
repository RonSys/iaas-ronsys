"""
📦 Inventory Service — Categorías de productos y precios mayoristas.

HU-F0-009: Categorías de productos (1 nivel)
HU-F0-010: Precios mayoristas
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Product


class InventoryCategoriesService:
    """Gestión de categorías de productos."""

    @staticmethod
    async def create_category(db: AsyncSession, tenant_id: int, name: str) -> dict:
        """Crea una categoría de producto."""
        # Verificar duplicado
        stmt = text(
            "SELECT id FROM product_categories "
            "WHERE tenant_id = :tenant_id AND name = :name"
        )
        result = await db.execute(stmt, {"tenant_id": tenant_id, "name": name})
        if result.fetchone():
            raise HTTPException(status_code=409, detail="Categoría ya existe")

        # Insertar
        stmt = text(
            "INSERT INTO product_categories (tenant_id, name) "
            "VALUES (:tenant_id, :name) "
            "RETURNING id, tenant_id, name, created_at, updated_at"
        )
        result = await db.execute(stmt, {"tenant_id": tenant_id, "name": name})
        row = result.fetchone()
        await db.flush()

        return {
            "id": row[0],
            "tenant_id": row[1],
            "name": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }

    @staticmethod
    async def list_categories(db: AsyncSession, tenant_id: int) -> list[dict]:
        """Lista categorías del tenant con conteo de productos."""
        stmt = text("""
            SELECT pc.id, pc.tenant_id, pc.name, pc.created_at, pc.updated_at,
                   COUNT(p.id) as product_count
            FROM product_categories pc
            LEFT JOIN products p ON p.category_id = pc.id AND p.tenant_id = :tenant_id
            WHERE pc.tenant_id = :tenant_id
            GROUP BY pc.id, pc.tenant_id, pc.name, pc.created_at, pc.updated_at
            ORDER BY pc.name
        """)
        result = await db.execute(stmt, {"tenant_id": tenant_id})
        rows = result.fetchall()

        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "name": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
                "product_count": row[5],
            }
            for row in rows
        ]

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, tenant_id: int, name: str
    ) -> dict:
        """Actualiza el nombre de una categoría."""
        # Verificar existencia
        stmt_check = text(
            "SELECT id, name FROM product_categories "
            "WHERE id = :id AND tenant_id = :tenant_id"
        )
        result = await db.execute(stmt_check, {"id": category_id, "tenant_id": tenant_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Verificar nombre duplicado
        stmt_dup = text(
            "SELECT id FROM product_categories "
            "WHERE tenant_id = :tenant_id AND name = :name AND id != :id"
        )
        result_dup = await db.execute(
            stmt_dup, {"tenant_id": tenant_id, "name": name, "id": category_id}
        )
        if result_dup.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

        # Actualizar
        stmt = text(
            "UPDATE product_categories SET name = :name, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id "
            "RETURNING id, tenant_id, name, created_at, updated_at"
        )
        result = await db.execute(
            stmt, {"name": name, "id": category_id, "tenant_id": tenant_id}
        )
        updated = result.fetchone()
        await db.flush()

        return {
            "id": updated[0],
            "tenant_id": updated[1],
            "name": updated[2],
            "created_at": updated[3].isoformat() if updated[3] else None,
            "updated_at": updated[4].isoformat() if updated[4] else None,
        }

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int, tenant_id: int):
        """Elimina una categoría si no tiene productos asignados."""
        # Verificar productos asociados
        stmt = select(func.count()).select_from(Product).where(
            Product.category_id == category_id
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0

        if count > 0:
            raise HTTPException(
                status_code=409,
                detail="Categoría con productos asignados",
            )

        stmt = text(
            "DELETE FROM product_categories WHERE id = :id AND tenant_id = :tenant_id"
        )
        result = await db.execute(stmt, {"id": category_id, "tenant_id": tenant_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        await db.flush()
