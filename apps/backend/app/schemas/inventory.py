"""
📦 Schemas Pydantic — Inventario (F0-009, F0-010).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    name: str
    product_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductResponse(BaseModel):
    """Producto con categoría y precios mayoristas (F0-010)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    code: str
    name: str
    description: str | None = None
    unit_of_measure: str = "kg"
    current_stock: float = 0.0
    average_cost: float = 0.0
    category_id: int | None = None
    category_name: str | None = None
    retail_price: float | None = None
    wholesale_price: float | None = None
    wholesale_min_qty: float | None = None
    barcode: str | None = None
    active: bool = True
