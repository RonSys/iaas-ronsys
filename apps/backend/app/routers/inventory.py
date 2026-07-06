"""
📦 Inventory Router — Categorías, Productos y Seriales (F0-009).

Endpoints:
  - HU-F0-009-01: Categorías con CRUD extendido + árbol jerárquico
  - HU-F0-009-02: Productos CRUD con búsqueda, sort, barcode
  - HU-F0-009-04: Seriales individual y batch + listado con filtros
  - HU-F0-009-07: Valor de inventario mixto
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductUpdate,
    SerialBatchCreate,
    SerialCreate,
)
from app.services.inventory_service import (
    InventoryCategoriesService,
    InventoryProductsService,
    SerialService,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventario"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIES (HU-F0-009-01)
# ═══════════════════════════════════════════════════════════════


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ProductCategoryCreate,
):
    """Crear categoría con description, parent_id, sort_order, active."""
    return await InventoryCategoriesService.create_category(db, tenant_id, body)


@router.get("/categories")
async def list_categories(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tree: bool = Query(False, description="Retornar estructura jerárquica anidada"),
):
    """
    Listar categorías con product_count.
    Si tree=true, devuelve estructura jerárquica con children anidados.
    """
    return await InventoryCategoriesService.list_categories(db, tenant_id, tree=tree)


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ProductCategoryUpdate,
):
    """
    Actualizar categoría.
    Soporta: name, description, parent_id, sort_order, active.
    Valida anti-ciclos en parent_id.
    """
    return await InventoryCategoriesService.update_category(
        db, category_id, tenant_id, body
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Eliminar categoría (soft-delete).
    Rechaza con 409 si tiene productos activos asignados.
    """
    await InventoryCategoriesService.delete_category(db, category_id, tenant_id)
    return None


# ═══════════════════════════════════════════════════════════════
# PRODUCTS (HU-F0-009-02)
# ═══════════════════════════════════════════════════════════════


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ProductCreate,
):
    """Crear producto con precios, seriales, garantía."""
    return await InventoryProductsService.create_product(db, tenant_id, body)


@router.get("/products")
async def list_products(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None, description="Filtrar por nombre de categoría"),
    category_id: int | None = Query(None, description="Filtrar por ID de categoría"),
    search: str | None = Query(None, description="Búsqueda por nombre o código"),
    barcode: str | None = Query(None, description="Búsqueda exacta por código de barras"),
    active: bool | None = Query(None),
    has_serial: bool | None = Query(None, description="Filtrar por control de seriales"),
    sort_by: str = Query("name", description="Campo de ordenación: name, retail_price, current_stock, code"),
    order: str = Query("asc", description="Dirección: asc o desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Listar productos con filtros avanzados y ordenación server-side.
    Soporta búsqueda por barcode exacto.
    """
    return await InventoryProductsService.list_products(
        db, tenant_id,
        category=category,
        category_id=category_id,
        search=search,
        barcode=barcode,
        active=active,
        has_serial=has_serial,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/products/value")
async def get_inventory_value(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Valor total del inventario mixto (serial + no serial).
    - Productos con serial: cost_price de seriales disponibles
    - Productos sin serial: current_stock * average_cost
    """
    from sqlalchemy import func, select, and_
    from app.adapters.db.models.accounting import Product, ProductUnit

    # Productos sin serial
    non_serial_result = await db.execute(
        select(
            func.count(Product.id),
            func.coalesce(func.sum(Product.current_stock * Product.average_cost), 0),
        ).where(
            Product.tenant_id == tenant_id,
            Product.has_serial == False,  # noqa: E712
            Product.active == True,  # noqa: E712
        )
    )
    row = non_serial_result.one()
    non_serial_count = int(row[0]) if row[0] else 0
    non_serial_value = float(row[1]) if row[1] else 0.0

    # Productos con serial: valor de seriales disponibles
    serial_result = await db.execute(
        select(
            func.count(func.distinct(ProductUnit.product_id)),
            func.coalesce(func.sum(ProductUnit.cost_price), 0),
            func.count(ProductUnit.id),
        ).select_from(ProductUnit).join(
            Product, Product.id == ProductUnit.product_id
        ).where(
            Product.tenant_id == tenant_id,
            Product.active == True,  # noqa: E712
            ProductUnit.status == "available",
        )
    )
    row2 = serial_result.one()
    serial_product_count = int(row2[0]) if row2[0] else 0
    serial_value = float(row2[1]) if row2[1] else 0.0
    serial_units_available = int(row2[2]) if row2[2] else 0

    return {
        "serialized_products_value": round(serial_value, 2),
        "non_serialized_products_value": round(non_serial_value, 2),
        "total_value": round(serial_value + non_serial_value, 2),
        "serialized_product_count": serial_product_count,
        "non_serialized_product_count": non_serial_count,
        "total_serial_units_available": serial_units_available,
    }


@router.get("/products/{product_id}")
async def get_product(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtener detalle de un producto con conteos de seriales."""
    return await InventoryProductsService.get_product(db, product_id, tenant_id)


@router.patch("/products/{product_id}")
async def update_product(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ProductUpdate,
):
    """
    Actualizar producto.
    Incluye validación de transiciones has_serial (HU-F0-009-07).
    """
    return await InventoryProductsService.update_product(
        db, product_id, tenant_id, body
    )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Soft-delete de producto."""
    result = await InventoryProductsService.delete_product(db, product_id, tenant_id)
    if result.get("warnings"):
        # Devolver 200 con warnings en lugar de 204
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content=result)
    return None


# ═══════════════════════════════════════════════════════════════
# SERIALS (HU-F0-009-04)
# ═══════════════════════════════════════════════════════════════


@router.post("/products/{product_id}/serials", status_code=status.HTTP_201_CREATED)
async def register_serial(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: SerialCreate,
):
    """Registrar un serial individual para un producto con has_serial=true."""
    return await SerialService.register_serial(db, product_id, tenant_id, body)


@router.post(
    "/products/{product_id}/serials/batch",
    status_code=status.HTTP_201_CREATED,
)
async def register_serial_batch(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: SerialBatchCreate,
):
    """Registro masivo de seriales (transaccional: rollback si alguno falla)."""
    return await SerialService.register_serial_batch(db, product_id, tenant_id, body)


@router.get("/products/{product_id}/serials")
async def list_product_serials(
    product_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status", description="Filtrar por status: available, sold, damaged"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Listar seriales de un producto con conteo available/sold."""
    return await SerialService.list_serials(
        db, product_id, tenant_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


# ═══════════════════════════════════════════════════════════════
# TRACEABILITY & WARRANTY (HU-F0-009-06)
# ═══════════════════════════════════════════════════════════════


@router.get("/serials/warranties/expiring")
async def get_expiring_warranties(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365, description="Dias para alerta de vencimiento"),
):
    """
    Alertas de garantia por vencer (HU-F0-009-06).
    Seriales vendidos con warranty_expiry en los proximos N dias.
    """
    return await SerialService.get_expiring_warranties(db, tenant_id, days)


@router.get("/serials/{serial_number}/traceability")
async def get_serial_traceability(
    serial_number: str,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Trazabilidad completa de un serial (HU-F0-009-06).
    Timeline de eventos: registered -> sold -> voided.
    Incluye estado de garantia.
    """
    return await SerialService.get_traceability(db, serial_number, tenant_id)


# ═══════════════════════════════════════════════════════════════
# INVENTORY VALUE (moved before /products/{product_id} — Bug #1 fix)
# ═══════════════════════════════════════════════════════════════
