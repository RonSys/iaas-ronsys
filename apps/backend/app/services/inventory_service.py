"""
📦 Inventory Service — Categorías de productos (F0-009).
"""

from fastapi import HTTPException
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Product


class InventoryCategoriesService:

    @staticmethod
    async def create_category(db: AsyncSession, tenant_id: int, name: str) -> dict:
        dup = await db.execute(
            text("SELECT id FROM product_categories WHERE tenant_id = :tid AND name = :n"),
            {"tid": tenant_id, "n": name},
        )
        if dup.fetchone():
            raise HTTPException(status_code=409, detail="Categoría ya existe")

        result = await db.execute(
            text(
                "INSERT INTO product_categories (tenant_id, name) "
                "VALUES (:tid, :n) RETURNING id, tenant_id, name, created_at"
            ),
            {"tid": tenant_id, "n": name},
        )
        row = result.fetchone()
        await db.flush()
        return {
            "id": row[0], "tenant_id": row[1], "name": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
        }

    @staticmethod
    async def list_categories(db: AsyncSession, tenant_id: int) -> list[dict]:
        result = await db.execute(
            text(
                "SELECT pc.id, pc.tenant_id, pc.name, pc.created_at, pc.updated_at, "
                "COUNT(p.id) as product_count "
                "FROM product_categories pc "
                "LEFT JOIN products p ON p.category_id = pc.id AND p.tenant_id = :tid "
                "WHERE pc.tenant_id = :tid "
                "GROUP BY pc.id, pc.tenant_id, pc.name, pc.created_at, pc.updated_at "
                "ORDER BY pc.name"
            ),
            {"tid": tenant_id},
        )
        rows = result.fetchall()
        return [
            {
                "id": r[0], "tenant_id": r[1], "name": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "updated_at": r[4].isoformat() if r[4] else None,
                "product_count": r[5],
            }
            for r in rows
        ]

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, tenant_id: int, name: str,
    ) -> dict:
        check = await db.execute(
            text("SELECT id FROM product_categories WHERE id = :id AND tenant_id = :tid"),
            {"id": category_id, "tid": tenant_id},
        )
        if not check.fetchone():
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        dup = await db.execute(
            text(
                "SELECT id FROM product_categories "
                "WHERE tenant_id = :tid AND name = :n AND id != :id"
            ),
            {"tid": tenant_id, "n": name, "id": category_id},
        )
        if dup.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

        result = await db.execute(
            text(
                "UPDATE product_categories SET name = :n, updated_at = NOW() "
                "WHERE id = :id AND tenant_id = :tid "
                "RETURNING id, tenant_id, name, created_at, updated_at"
            ),
            {"n": name, "id": category_id, "tid": tenant_id},
        )
        row = result.fetchone()
        await db.flush()
        return {
            "id": row[0], "tenant_id": row[1], "name": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int, tenant_id: int):
        count_result = await db.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        count = count_result.scalar() or 0
        if count > 0:
            raise HTTPException(status_code=409, detail="Categoría con productos asignados")

        result = await db.execute(
            text("DELETE FROM product_categories WHERE id = :id AND tenant_id = :tid"),
            {"id": category_id, "tid": tenant_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        await db.flush()
