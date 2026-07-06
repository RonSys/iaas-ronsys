"""
📦 Schemas Pydantic — Inventario (F0-009, F0-010).

Cubre:
  - Categorías: CRUD, árbol jerárquico, product_count
  - Productos: CRUD con precios mayorista/detal, seriales, garantía
  - Seriales: registro individual/masivo, consulta, trazabilidad
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ═══════════════════════════════════════════════════════════════
# Categorías
# ═══════════════════════════════════════════════════════════════


class ProductCategoryResponse(BaseModel):
    """Categoría en lista plana."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    name: str
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    active: bool = True
    product_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductCategoryTreeResponse(BaseModel):
    """Categoría en árbol jerárquico."""
    id: int
    tenant_id: int
    name: str
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    active: bool = True
    product_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    children: list["ProductCategoryTreeResponse"] = []


class ProductCategoryCreate(BaseModel):
    """Crear categoría."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    active: bool = True


class ProductCategoryUpdate(BaseModel):
    """Actualizar categoría (todos los campos opcionales)."""
    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
    active: bool | None = None


# ═══════════════════════════════════════════════════════════════
# Productos
# ═══════════════════════════════════════════════════════════════


class ProductResponse(BaseModel):
    """Producto con categoría, precios mayoristas, seriales y garantía."""
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
    # F0-009: Seriales + garantía
    has_serial: bool = False
    warranty_months: int = 0
    manufacturer: str | None = None
    serial_available_count: int = 0
    serial_total_count: int = 0


class ProductCreate(BaseModel):
    """Crear producto."""
    code: str | None = Field(None, max_length=20, description="Auto-generado del name si no se provee")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    unit_of_measure: str = Field("unidad", max_length=10)
    current_stock: float = Field(0.0, ge=0)
    average_cost: float = Field(0.0, ge=0)
    category_id: int | None = None
    retail_price: float | None = Field(None, ge=0)
    wholesale_price: float | None = Field(None, ge=0)
    wholesale_min_qty: float | None = Field(None, ge=0)
    barcode: str | None = Field(None, max_length=50)
    active: bool = True
    # F0-009
    has_serial: bool = False
    warranty_months: int = Field(0, ge=0)
    manufacturer: str | None = Field(None, max_length=100)

    @model_validator(mode="after")
    def auto_generate_code(self) -> "ProductCreate":
        """Auto-genera code desde name si no se provee."""
        if not self.code and self.name:
            self.code = self.name.strip()[:20].upper().replace(" ", "_").replace("'", "").replace('"', "")
        return self


class ProductUpdate(BaseModel):
    """Actualizar producto (todos los campos opcionales)."""
    code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    unit_of_measure: str | None = Field(None, max_length=10)
    current_stock: float | None = Field(None, ge=0)
    average_cost: float | None = Field(None, ge=0)
    category_id: int | None = None
    retail_price: float | None = Field(None, ge=0)
    wholesale_price: float | None = Field(None, ge=0)
    wholesale_min_qty: float | None = Field(None, ge=0)
    barcode: str | None = Field(None, max_length=50)
    active: bool | None = None
    has_serial: bool | None = None
    warranty_months: int | None = Field(None, ge=0)
    manufacturer: str | None = Field(None, max_length=100)


# ═══════════════════════════════════════════════════════════════
# Seriales (ProductUnit)
# ═══════════════════════════════════════════════════════════════


class SerialCreate(BaseModel):
    """Registrar un serial individual."""
    serial_number: str = Field(..., min_length=1, max_length=100)
    purchase_date: date | None = None
    cost_price: float | None = Field(None, ge=0)
    notes: str | None = None


class SerialBatchCreate(BaseModel):
    """Registro masivo de seriales."""
    serials: list[SerialCreate] = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_no_duplicates(self) -> "SerialBatchCreate":
        """Validar que no haya seriales duplicados en el batch."""
        seen = set()
        for s in self.serials:
            if s.serial_number in seen:
                raise ValueError(f"Serial duplicado en el lote: {s.serial_number}")
            seen.add(s.serial_number)
        return self


class SerialResponse(BaseModel):
    """Respuesta de un serial/unidad."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    serial_number: str
    status: str
    purchase_date: date | None = None
    cost_price: float | None = None
    warranty_expiry: date | None = None
    sale_id: int | None = None
    sale_item_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None


class SerialListResponse(BaseModel):
    """Lista paginada de seriales."""
    items: list[SerialResponse]
    total: int
    available: int
    sold: int


class SerialTraceabilityEvent(BaseModel):
    """Evento en la línea de tiempo de trazabilidad."""
    event_type: str  # registered | sold | voided
    timestamp: datetime | date
    description: str
    reference: str | None = None
    details: dict | None = None


class SerialTraceabilityResponse(BaseModel):
    """Trazabilidad completa de un serial."""
    serial_number: str
    product_name: str
    product_id: int
    warranty_expiry: date | None = None
    warranty_status: str = "N/A"  # vigente | vencida | sin_garantia
    warranty_days_remaining: int | None = None
    current_status: str
    cost_price: float | None = None
    timeline: list[SerialTraceabilityEvent] = []
    current_sale: dict | None = None


# ═══════════════════════════════════════════════════════════════
# Inventario — Valor total
# ═══════════════════════════════════════════════════════════════


class InventoryValueResponse(BaseModel):
    """Valor total del inventario (mixto: serial + no serial)."""
    serialized_products_value: float = 0.0
    non_serialized_products_value: float = 0.0
    total_value: float = 0.0
    serialized_product_count: int = 0
    non_serialized_product_count: int = 0
    total_serial_units_available: int = 0
