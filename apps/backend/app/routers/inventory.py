"""
📦 Inventory Router — Categorías de productos y consultas.

HU-F0-009: Categorías de productos (CRUD)
HU-F0-015: Productos con categorías
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.models.accounting import Product
from app.core.dependencies import get_current_active_user, require_role
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.services.inventory_service import InventoryCategoriesService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventario"])


# ═══════════════════════════════════════════════════════════════
# PRODUCT CATEGORIES (HU-F0-009)
# ═══════════════════════════════════════════════════════════════


@router.post("/categories")
async def create_category(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea una categoría de producto."""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'name' es requerido")
    return await InventoryCategoriesService.create_category(db, tenant_id, name)


@router.get("/categories")
async def list_categories(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista categorías del tenant."""
    return await InventoryCategoriesService.list_categories(db, tenant_id)


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza una categoría de producto."""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'name' es requerido")
    return await InventoryCategoriesService.update_category(
        db, category_id, tenant_id, name
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina una categoría (solo si no tiene productos)."""
    await InventoryCategoriesService.delete_category(db, category_id, tenant_id)
    return None


# ═══════════════════════════════════════════════════════════════
# PRODUCTS (extended with categories & wholesale)
# ═══════════════════════════════════════════════════════════════


@router.get("/products")
async def list_products(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None, description="Filtrar por nombre de categoría"),
    category_id: int | None = Query(None, description="Filtrar por ID de categoría"),
    search: str | None = Query(None, description="Búsqueda por nombre o código"),
    active: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista productos con información extendida (categoría, precios mayoristas)."""
    from sqlalchemy import text

    where_clauses = ["p.tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if category:
        where_clauses.append("pc.name = :category")
        params["category"] = category

    if category_id is not None:
        where_clauses.append("p.category_id = :category_id")
        params["category_id"] = category_id

    if active is not None:
        where_clauses.append("p.active = :active")
        params["active"] = active

    if search:
        where_clauses.append("(p.name ILIKE :search OR p.code ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses)

    stmt = text(f"""
        SELECT p.id, p.tenant_id, p.code, p.name, p.description,
               p.unit_of_measure, p.current_stock, p.average_cost,
               p.category_id, pc.name as category_name,
               p.wholesale_price, p.wholesale_min_qty, p.barcode, p.active
        FROM products p
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        WHERE {where_sql}
        ORDER BY p.name
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(stmt, params)
    rows = result.fetchall()

    return [
        {
            "id": row[0],
            "tenant_id": row[1],
            "code": row[2],
            "name": row[3],
            "description": row[4],
            "unit_of_measure": row[5],
            "current_stock": float(row[6]) if row[6] else 0,
            "average_cost": float(row[7]) if row[7] else 0,
            "category_id": row[8],
            "category_name": row[9],
            "wholesale_price": float(row[10]) if row[10] else None,
            "wholesale_min_qty": row[11],
            "barcode": row[12],
            "active": row[13],
        }
        for row in rows
    ]
