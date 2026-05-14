"""
SqlAlchemyInventoryRepository — Implementación DB del puerto InventoryRepository.

HU-F1-009: Adaptador concreto para persistencia de inventario y kárdex.
Usa los modelos ORM existentes (Product, KardexMovement, product_categories).
"""

from datetime import date
from typing import Optional

from sqlalchemy import func, select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import KardexMovement, Product
from app.core.inventory.ports import (
    InventoryRepository,
    ProductRecord,
    CategoryRecord,
    KardexMovementRecord,
)


class SqlAlchemyInventoryRepository(InventoryRepository):
    """Implementación SQLAlchemy del puerto de inventario."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Productos ─────────────────────────────────────────

    async def create_product(self, record: ProductRecord) -> ProductRecord:
        p = Product(
            tenant_id=record.tenant_id,
            code=record.code,
            name=record.name,
            description=record.description,
            unit_of_measure=record.unit_of_measure,
            current_stock=record.current_stock,
            average_cost=record.average_cost,
            active=record.active,
            category_id=record.category_id,
            wholesale_price=record.wholesale_price,
            wholesale_min_qty=record.wholesale_min_qty,
            barcode=record.barcode,
        )
        self.session.add(p)
        await self.session.flush()
        await self.session.refresh(p)
        return _to_product_record(p)

    async def get_product(
        self, product_code: str, tenant_id: int,
    ) -> Optional[ProductRecord]:
        stmt = select(Product).where(
            Product.code == product_code,
            Product.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        p = result.scalar_one_or_none()
        return _to_product_record(p) if p else None

    async def get_product_by_id(
        self, product_id: int, tenant_id: int,
    ) -> Optional[ProductRecord]:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        p = result.scalar_one_or_none()
        return _to_product_record(p) if p else None

    async def list_products(
        self, tenant_id: int,
        category_id: int | None = None,
        category_name: str | None = None,
        search: str | None = None,
        active: bool | None = None,
        limit: int = 100, offset: int = 0,
    ) -> tuple[list[ProductRecord], int]:
        where_clauses = ["p.tenant_id = :tenant_id"]
        params: dict = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if category_id is not None:
            where_clauses.append("p.category_id = :category_id")
            params["category_id"] = category_id

        if category_name:
            where_clauses.append("pc.name = :category_name")
            params["category_name"] = category_name

        if active is not None:
            where_clauses.append("p.active = :active")
            params["active"] = active

        if search:
            where_clauses.append("(p.name ILIKE :search OR p.code ILIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses)

        count_stmt = text(
            f"SELECT COUNT(*) FROM products p "
            f"LEFT JOIN product_categories pc ON pc.id = p.category_id "
            f"WHERE {where_sql}"
        )
        count_result = await self.session.execute(count_stmt, params)
        total = count_result.scalar() or 0

        stmt = text(
            f"SELECT p.id, p.tenant_id, p.code, p.name, p.description, "
            f"p.unit_of_measure, p.current_stock, p.average_cost, "
            f"p.category_id, pc.name as category_name, "
            f"p.wholesale_price, p.wholesale_min_qty, p.barcode, p.active "
            f"FROM products p "
            f"LEFT JOIN product_categories pc ON pc.id = p.category_id "
            f"WHERE {where_sql} "
            f"ORDER BY p.name "
            f"LIMIT :limit OFFSET :offset"
        )
        result = await self.session.execute(stmt, params)
        rows = result.fetchall()

        products = [
            ProductRecord(
                id=row[0],
                tenant_id=row[1],
                code=row[2],
                name=row[3],
                description=row[4],
                unit_of_measure=row[5],
                current_stock=float(row[6]) if row[6] else 0.0,
                average_cost=float(row[7]) if row[7] else 0.0,
                category_id=row[8],
                category_name=row[9],
                wholesale_price=float(row[10]) if row[10] else None,
                wholesale_min_qty=row[11],
                barcode=row[12],
                active=row[13],
            )
            for row in rows
        ]
        return products, total

    async def update_product(self, record: ProductRecord) -> ProductRecord:
        stmt = select(Product).where(Product.id == record.id)
        result = await self.session.execute(stmt)
        p = result.scalar_one()
        p.code = record.code
        p.name = record.name
        p.description = record.description
        p.unit_of_measure = record.unit_of_measure
        p.current_stock = record.current_stock
        p.average_cost = record.average_cost
        p.active = record.active
        p.category_id = record.category_id
        p.wholesale_price = record.wholesale_price
        p.wholesale_min_qty = record.wholesale_min_qty
        p.barcode = record.barcode
        await self.session.flush()
        return _to_product_record(p)

    # ─── Categorías ────────────────────────────────────────

    async def create_category(self, tenant_id: int, name: str) -> CategoryRecord:
        stmt_check = text(
            "SELECT id FROM product_categories "
            "WHERE tenant_id = :tenant_id AND name = :name"
        )
        result = await self.session.execute(stmt_check, {"tenant_id": tenant_id, "name": name})
        if result.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="Categoría ya existe")

        stmt = text(
            "INSERT INTO product_categories (tenant_id, name) "
            "VALUES (:tenant_id, :name) "
            "RETURNING id, tenant_id, name"
        )
        result = await self.session.execute(stmt, {"tenant_id": tenant_id, "name": name})
        row = result.fetchone()
        await self.session.flush()

        return CategoryRecord(id=row[0], tenant_id=row[1], name=row[2])

    async def list_categories(self, tenant_id: int) -> list[CategoryRecord]:
        stmt = text(
            "SELECT pc.id, pc.tenant_id, pc.name, COUNT(p.id) as product_count "
            "FROM product_categories pc "
            "LEFT JOIN products p ON p.category_id = pc.id AND p.tenant_id = :tenant_id "
            "WHERE pc.tenant_id = :tenant_id "
            "GROUP BY pc.id, pc.tenant_id, pc.name "
            "ORDER BY pc.name"
        )
        result = await self.session.execute(stmt, {"tenant_id": tenant_id})
        rows = result.fetchall()
        return [
            CategoryRecord(id=row[0], tenant_id=row[1], name=row[2], product_count=row[3])
            for row in rows
        ]

    async def update_category(
        self, category_id: int, tenant_id: int, name: str,
    ) -> CategoryRecord:
        stmt_check = text(
            "SELECT id, name FROM product_categories "
            "WHERE id = :id AND tenant_id = :tenant_id"
        )
        result = await self.session.execute(stmt_check, {"id": category_id, "tenant_id": tenant_id})
        if not result.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        stmt = text(
            "UPDATE product_categories SET name = :name, updated_at = NOW() "
            "WHERE id = :id AND tenant_id = :tenant_id "
            "RETURNING id, tenant_id, name"
        )
        result = await self.session.execute(
            stmt, {"name": name, "id": category_id, "tenant_id": tenant_id}
        )
        row = result.fetchone()
        await self.session.flush()
        return CategoryRecord(id=row[0], tenant_id=row[1], name=row[2])

    async def delete_category(self, category_id: int, tenant_id: int) -> None:
        count_result = await self.session.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        count = count_result.scalar() or 0

        if count > 0:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="Categoría con productos asignados")

        stmt = text(
            "DELETE FROM product_categories WHERE id = :id AND tenant_id = :tenant_id"
        )
        result = await self.session.execute(stmt, {"id": category_id, "tenant_id": tenant_id})
        if result.rowcount == 0:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        await self.session.flush()

    # ─── Kárdex ────────────────────────────────────────────

    async def save_kardex_movement(
        self, record: KardexMovementRecord,
    ) -> KardexMovementRecord:
        km = KardexMovement(
            product_id=record.product_id,
            movement_type=record.movement_type,
            concept=record.concept,
            quantity=record.quantity,
            unit_cost=record.unit_cost,
            total=record.total,
            balance_quantity=record.balance_quantity,
            balance_avg_cost=record.balance_avg_cost,
            balance_total=record.balance_total,
            date=record.date_ or date.today(),
            reference_type=record.reference_type,
            reference_id=record.reference_id,
        )
        self.session.add(km)
        await self.session.flush()
        await self.session.refresh(km)
        return _to_kardex_record(km)

    async def get_kardex(
        self, product_code: str, tenant_id: int,
    ) -> list[KardexMovementRecord]:
        stmt = (
            select(KardexMovement)
            .join(Product, KardexMovement.product_id == Product.id)
            .where(Product.code == product_code, Product.tenant_id == tenant_id)
            .order_by(KardexMovement.date, KardexMovement.id)
        )
        result = await self.session.execute(stmt)
        return [_to_kardex_record(km) for km in result.scalars()]

    async def get_inventory_summary(self, tenant_id: int) -> list[ProductRecord]:
        stmt = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.active == True,
        ).order_by(Product.name)
        result = await self.session.execute(stmt)
        return [_to_product_record(p) for p in result.scalars()]


# ═══════════════════════════════════════════════════════════════
# Helpers de conversión
# ═══════════════════════════════════════════════════════════════


def _to_product_record(p: Product) -> ProductRecord:
    return ProductRecord(
        id=p.id,
        tenant_id=p.tenant_id,
        code=p.code,
        name=p.name,
        description=p.description,
        unit_of_measure=p.unit_of_measure,
        current_stock=float(p.current_stock),
        average_cost=float(p.average_cost),
        active=p.active,
        category_id=p.category_id,
        wholesale_price=float(p.wholesale_price) if p.wholesale_price else None,
        wholesale_min_qty=p.wholesale_min_qty,
        barcode=p.barcode,
    )


def _to_kardex_record(km: KardexMovement) -> KardexMovementRecord:
    return KardexMovementRecord(
        id=km.id,
        product_id=km.product_id,
        movement_type=km.movement_type,
        concept=km.concept,
        quantity=float(km.quantity),
        unit_cost=float(km.unit_cost),
        total=float(km.total),
        balance_quantity=float(km.balance_quantity),
        balance_avg_cost=float(km.balance_avg_cost),
        balance_total=float(km.balance_total),
        date_=km.date,
        reference_type=km.reference_type,
        reference_id=km.reference_id,
    )


# ═══════════════════════════════════════════════════════════════
# Dependencia FastAPI
# ═══════════════════════════════════════════════════════════════


async def get_inventory_repo(
    db: AsyncSession,
) -> SqlAlchemyInventoryRepository:
    """
    FastAPI Depends: inyecta el repositorio de inventario.

    Uso en Fase 2:
        @router.get("/products")
        async def list_products(
            repo: SqlAlchemyInventoryRepository = Depends(get_inventory_repo),
        ):
            ...
    """
    return SqlAlchemyInventoryRepository(db)
