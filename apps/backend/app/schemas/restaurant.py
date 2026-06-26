"""
🍽️ Schemas Pydantic — Restaurante (F0-004 a F0-008).

Validation layer para endpoints de mesas, secciones, menú, comandas, takeaway y promociones.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# Secciones
# ═══════════════════════════════════════════════════════════════

class SectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    sort_order: int = 0


class SectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    sort_order: int | None = None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    sort_order: int = 0
    table_count: int = 0
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Mesa
# ═══════════════════════════════════════════════════════════════

class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    capacity: int
    status: str
    section_id: int | None = None
    section_name: str | None = None
    created_at: datetime | None = None


class TableOpenRequest(BaseModel):
    guests: int = Field(1, ge=1, le=50)
    waiter_name: str | None = None


class TableOpenResponse(BaseModel):
    id: int
    number: str
    status: str
    opened_at: str
    guests: int
    waiter_name: str | None = None
    session_token: str


class TableCloseResponse(BaseModel):
    table_id: int
    table_number: str
    status: str
    subtotal: float = 0.0
    igv: float = 0.0
    total: float = 0.0
    items: list[dict] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Menú
# ═══════════════════════════════════════════════════════════════

class MenuModifierItem(BaseModel):
    id: int
    name: str
    price_adjustment: float = 0.0
    max_select: int = 1


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    price: float
    cost_price: float | None = None
    category: str
    item_type: str = "food"
    preparation_area: str = "cocina"
    modifiers: list | None = None
    image_url: str | None = None
    active: bool = True


class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: float = Field(..., gt=0)
    cost_price: float | None = None
    category: str = Field(..., min_length=1, max_length=30)
    item_type: str = Field("food", pattern=r"^(food|beverage|dessert|combo)$")
    preparation_area: str = Field("cocina", pattern=r"^(cocina|barra|none)$")
    modifiers: list[dict] | None = None
    image_url: str | None = None
    active: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    cost_price: float | None = None
    category: str | None = None
    item_type: str | None = None
    preparation_area: str | None = None
    image_url: str | None = None
    active: bool | None = None


# ═══════════════════════════════════════════════════════════════
# Comanda (Kitchen Order)
# ═══════════════════════════════════════════════════════════════

class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(1, ge=1)
    modifiers: list[dict] = Field(default_factory=list)
    notes: str | None = None


class OrderCreateRequest(BaseModel):
    items: list[OrderItemRequest] = Field(..., min_length=1)


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(pending|preparing|ready|delivered|cancelled)$")


class KitchenOrderResponse(BaseModel):
    id: int
    tenant_id: int
    table_id: int | None = None
    status: str
    items: list[dict]
    notes: str | None = None
    ordered_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Pago / Cierre
# ═══════════════════════════════════════════════════════════════

class PaymentItem(BaseModel):
    """Un pago individual dentro del split."""
    method: str = Field(..., pattern=r"^(cash|card|yape|plin|transfer)$")
    amount: float = Field(..., gt=0)
    reference: str | None = None


class PayTableRequest(BaseModel):
    # Nuevo formato: lista de pagos
    payments: list[PaymentItem] | None = None
    # Legacy (compatibilidad)
    payment_method: str | None = Field(None, pattern=r"^(cash|card|yape|plin|transfer)$")
    amount: float | None = Field(None, gt=0)
    reference: str | None = None
    # Comunes
    tip_amount: float = Field(0.0, ge=0)
    tip_pct: float = Field(0.0, ge=0, le=100)
    customer_name: str | None = None
    waiter_name: str | None = None
    guest_count: int = Field(1, ge=1)

    @classmethod
    def resolve_payments(cls, data: dict) -> list[dict]:
        """Devuelve la lista de payments desde cualquiera de los formatos."""
        if data.get("payments"):
            return [{"method": p["method"], "amount": p["amount"],
                     "reference": p.get("reference")}
                    for p in data["payments"]]
        # Legacy: payment_method + amount
        method = data.get("payment_method", "cash")
        amount = data.get("amount")
        if amount is not None:
            return [{"method": method, "amount": amount,
                     "reference": data.get("reference")}]
        return []


class PayTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sale_id: int
    sale_number: str
    table_number: str
    subtotal: float
    igv: float
    tip: float
    total: float
    payments: list[dict] = Field(default_factory=list)
    payment_method: str
    amount_paid: float
    change: float


# ═══════════════════════════════════════════════════════════════
# TakeAway
# ═══════════════════════════════════════════════════════════════

class TakeawayCreateRequest(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_time: datetime | None = None
    items: list[OrderItemRequest] = Field(..., min_length=1)
    notes: str | None = None


class TakeawayResponse(BaseModel):
    id: int
    customer_name: str | None = None
    customer_phone: str | None = None
    status: str
    items: list[dict]
    pickup_time: datetime | None = None
    notes: str | None = None
    created_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# Promociones
# ═══════════════════════════════════════════════════════════════

class PromotionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    promo_type: str = Field(..., pattern=r"^(combo|discount_pct|discount_fixed|bogof)$")
    rules: dict | None = None
    discount_value: float = Field(..., ge=0)
    valid_from: datetime
    valid_to: datetime | None = None
    active: bool = True


class PromotionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rules: dict | None = None
    discount_value: float | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    active: bool | None = None


class PromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    name: str
    description: str | None = None
    promo_type: str
    rules: dict | None = None
    discount_value: float
    valid_from: datetime
    valid_to: datetime | None = None
    active: bool
    created_at: datetime | None = None


class ApplyPromotionResponse(BaseModel):
    order_id: int
    promotion_id: int
    promotion_name: str
    discount_applied: float
    new_total: float


# ═══════════════════════════════════════════════════════════════
# Recetas e Insumos (Caso 6)
# ═══════════════════════════════════════════════════════════════


class RecipeIngredientItem(BaseModel):
    """Un ingrediente individual de la receta."""
    product_id: int
    product_name: str | None = None
    quantity: float = Field(..., gt=0)
    unit_of_measure: str
    sort_order: int = 0
    average_cost: float | None = None
    estimated_cost: float | None = None


class RecipeIngredientInput(BaseModel):
    """Input para crear/actualizar un ingrediente."""
    product_id: int
    quantity: float = Field(..., gt=0)
    unit_of_measure: str = Field(..., min_length=1, max_length=10)
    sort_order: int = 0


class RecipeResponse(BaseModel):
    """Respuesta completa de receta con ingredientes y costos."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    menu_item_id: int
    menu_item_name: str | None = None
    has_recipe: bool = True
    ingredients: list[RecipeIngredientItem] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    menu_item_price: float | None = None
    margin: float | None = None
    margin_pct: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecipeUpdateInput(BaseModel):
    """Input para guardar/actualizar receta completa."""
    ingredients: list[RecipeIngredientInput] = Field(default_factory=list)


class ProductForRecipeResponse(BaseModel):
    """Producto ligero para selector de insumos en receta."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    unit_of_measure: str
    average_cost: float = 0.0
    current_stock: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Inversión / Puesta en Marcha (Caso 7)
# ═══════════════════════════════════════════════════════════════


INVESTMENT_CATEGORIES = [
    "infraestructura",
    "mobiliario",
    "equipamiento_cocina",
    "instalaciones",
    "vestimenta",
    "dyl",
    "tecnologia",
    "marketing",
    "gastos_operativos",
]


class InvestmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern=f"^({'|'.join(INVESTMENT_CATEGORIES)})$")
    estimated_cost: float = Field(..., ge=0)
    actual_cost: float | None = Field(None, ge=0)
    receipt_code: str | None = Field(None, max_length=50)
    status: str = Field("pending", pattern=r"^(pending|acquired)$")
    notes: str | None = Field(None, max_length=500)


class InvestmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    category: str | None = Field(None, pattern=f"^({'|'.join(INVESTMENT_CATEGORIES)})$")
    estimated_cost: float | None = Field(None, ge=0)
    actual_cost: float | None = None  # None = no cambiar; null explícito
    receipt_code: str | None = Field(None, max_length=50)
    status: str | None = Field(None, pattern=r"^(pending|acquired)$")
    notes: str | None = Field(None, max_length=500)


class InvestmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    estimated_cost: float
    actual_cost: float | None = None
    receipt_code: str | None = None
    status: str = "pending"
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvestmentSummary(BaseModel):
    total_estimated: float = 0.0
    total_actual: float = 0.0
    difference: float = 0.0
    acquired_count: int = 0
    pending_count: int = 0
    total_count: int = 0
