"""
🍽️ Schemas Pydantic — Restaurante (F0-004 a F0-008).

Validation layer para endpoints de mesas, menú, comandas, takeaway y promociones.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# Mesa
# ═══════════════════════════════════════════════════════════════

class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    capacity: int
    status: str
    section: str | None = None
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

class PayTableRequest(BaseModel):
    payment_method: str = Field("cash", pattern=r"^(cash|card|yape|plin|transfer)$")
    amount: float = Field(..., gt=0)
    tip_amount: float = Field(0.0, ge=0)
    tip_pct: float = Field(0.0, ge=0, le=100)
    customer_name: str | None = None
    reference: str | None = None
    waiter_name: str | None = None
    guest_count: int = Field(1, ge=1)


class PayTableResponse(BaseModel):
    sale_id: int
    sale_number: str
    table_number: str
    subtotal: float
    igv: float
    tip: float
    total: float
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
