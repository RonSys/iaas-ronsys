"""
Schemas Pydantic — Inventario (HU-F0-009, HU-F0-010, HU-F0-015).

Categorías de productos, precios mayoristas y productos extendidos.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# Product Categories (HU-F0-009)
# ═══════════════════════════════════════════════════════════════


class ProductCategoryCreate(BaseModel):
    """Crear categoría de producto."""
    name: str = Field(..., min_length=1, max_length=100)


class ProductCategoryResponse(BaseModel):
    """Respuesta de categoría de producto."""
    id: int
    tenant_id: int
    name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    product_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════
# Extended Product (HU-F0-010)
# ═══════════════════════════════════════════════════════════════


class ProductExtendedResponse(BaseModel):
    """Producto con campos mayoristas."""
    id: int
    tenant_id: int
    code: str
    name: str
    description: str | None = None
    unit_of_measure: str
    category_id: int | None = None
    category_name: str | None = None
    current_stock: float
    average_cost: float
    unit_price: float | None = None
    wholesale_price: float | None = None
    wholesale_min_qty: int | None = None
    barcode: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class ProductFilterParams(BaseModel):
    """Parámetros de filtro para productos."""
    category_id: int | None = None
    category: str | None = None
    active: bool | None = None
    search: str | None = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)
