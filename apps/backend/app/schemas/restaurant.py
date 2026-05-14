"""
Schemas Pydantic — Restaurante (HU-F0-004 a HU-F0-008, HU-F0-013).

Validation layer para endpoints de restaurante: mesas, menú, comandas,
takeaway y promociones.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ═══════════════════════════════════════════════════════════════
# Tables (HU-F0-004)
# ═══════════════════════════════════════════════════════════════


class TableOpenRequest(BaseModel):
    """Abrir mesa."""
    waiter_id: int | None = None
    guest_count: int = Field(1, ge=1, le=50)


class TableResponse(BaseModel):
    """Respuesta de mesa."""
    id: int
    tenant_id: int
    number: int
    capacity: int
    status: str
    section: str | None = None
    qr_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TableOpenResponse(BaseModel):
    """Respuesta al abrir mesa."""
    id: int
    number: int
    status: str = "occupied"
    opened_at: datetime
    guest_count: int
    session_token: str | None = None


# ═══════════════════════════════════════════════════════════════
# Menu Items (HU-F0-005)
# ═══════════════════════════════════════════════════════════════


class MenuModifierCreate(BaseModel):
    """Modificador de ítem del menú."""
    name: str = Field(..., min_length=1, max_length=50)
    price_adjustment: float = Field(0.0, ge=0)
    max_select: int = Field(1, ge=1)


class MenuItemCreate(BaseModel):
    """Creación de ítem del menú."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    category: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., ge=0)
    cost: float | None = None
    unit: str = Field("plato", max_length=20)
    image_url: str | None = None
    available: bool = True
    has_modifiers: bool = False
    modifiers: list[MenuModifierCreate] = []


class MenuItemResponse(BaseModel):
    """Respuesta de ítem del menú."""
    id: int
    tenant_id: int
    name: str
    description: str | None = None
    category: str
    price: float
    cost: float | None = None
    unit: str
    image_url: str | None = None
    available: bool
    has_modifiers: bool
    modifiers: list[dict] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MenuItemUpdate(BaseModel):
    """Actualización de ítem del menú (parcial)."""
    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = Field(None, ge=0)
    cost: float | None = None
    unit: str | None = None
    image_url: str | None = None
    available: bool | None = None
    has_modifiers: bool | None = None


# ═══════════════════════════════════════════════════════════════
# Kitchen Orders (HU-F0-005, F0-006, F0-007)
# ═══════════════════════════════════════════════════════════════


class OrderItem(BaseModel):
    """Ítem de pedido."""
    menu_item_id: int = Field(..., gt=0)
    name: str | None = None
    quantity: float = Field(..., gt=0)
    modifiers: list[dict] = Field(default_factory=list)
    notes: str | None = None


class OrderCreateRequest(BaseModel):
    """Tomar pedido en una mesa."""
    items: list[OrderItem] = Field(..., min_length=1)


class OrderCreateResponse(BaseModel):
    """Respuesta de creación de pedido."""
    order_id: int
    items_count: int
    total: float
    status: str = "pending"


class OrderDetailResponse(BaseModel):
    """Detalle completo de orden de cocina."""
    id: int
    tenant_id: int
    sale_id: int | None = None
    table_id: int | None = None
    table_number: int | None = None
    order_type: str
    status: str
    items: list[dict]
    priority: int
    notes: str | None = None
    sent_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    subtotal: float = 0.0
    elapsed_minutes: int = 0


class OrderStatusUpdate(BaseModel):
    """Cambiar estado de orden."""
    status: str = Field(..., pattern=r"^(pending|preparing|ready|served|cancelled)$")


# ═══════════════════════════════════════════════════════════════
# Close Order / Pay (HU-F0-007)
# ═══════════════════════════════════════════════════════════════


class CloseOrderResponse(BaseModel):
    """Resumen de cuenta al cerrar comanda."""
    table_number: int
    items: list[dict]
    subtotal: float
    igv: float
    total: float
    payment_pending: bool = True


class PayRequest(BaseModel):
    """Pago de mesa."""
    payment_method: str = Field(..., pattern=r"^(cash|card|yape|plin|transfer)$")
    amount: float = Field(..., gt=0)
    reference: str | None = None
    tip_amount: float = Field(0.0, ge=0)
    tip_pct: float = Field(0.0, ge=0, le=100)


class PayResponse(BaseModel):
    """Respuesta de pago."""
    sale_id: int
    sale_number: str
    total: float
    change: float = 0.0
    payment_method: str
    ticket: dict


# ═══════════════════════════════════════════════════════════════
# Takeaway (HU-F0-013)
# ═══════════════════════════════════════════════════════════════


class TakeawayCreateRequest(BaseModel):
    """Crear pedido takeaway."""
    customer_name: str | None = Field(None, max_length=100)
    customer_phone: str | None = Field(None, max_length=20)
    items: list[OrderItem] = Field(..., min_length=1)
    pickup_time: datetime | None = None


class TakeawayResponse(BaseModel):
    """Respuesta de pedido takeaway."""
    id: int
    tenant_id: int
    sale_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    status: str
    items: list[dict]
    pickup_time: datetime | None = None
    created_at: datetime | None = None
    is_late: bool = False

    model_config = ConfigDict(from_attributes=True)


class TakeawayPickupRequest(BaseModel):
    """Marcar takeaway como recogido."""
    pass


# ═══════════════════════════════════════════════════════════════
# Promotions (HU-F0-008)
# ═══════════════════════════════════════════════════════════════


class PromotionCreate(BaseModel):
    """Crear promoción."""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern=r"^(combo|fixed_discount|percentage_discount|happy_hour)$")
    discount_value: float = Field(..., ge=0)
    conditions: dict | None = None
    start_date: datetime
    end_date: datetime | None = None
    active: bool = True
    max_uses: int | None = None


class PromotionUpdate(BaseModel):
    """Actualizar promoción (parcial)."""
    name: str | None = None
    type: str | None = None
    discount_value: float | None = Field(None, ge=0)
    conditions: dict | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    active: bool | None = None
    max_uses: int | None = None


class PromotionResponse(BaseModel):
    """Respuesta de promoción."""
    id: int
    tenant_id: int
    name: str
    type: str
    discount_value: float
    conditions: dict | None = None
    start_date: datetime
    end_date: datetime | None = None
    active: bool
    max_uses: int | None = None
    current_uses: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplyPromotionResponse(BaseModel):
    """Respuesta al aplicar promoción."""
    order_id: int
    promotion_id: int
    promotion_name: str
    discount_applied: float
    new_total: float


# ═══════════════════════════════════════════════════════════════
# WebSocket Events (HU-F0-006)
# ═══════════════════════════════════════════════════════════════


class WSEvent(BaseModel):
    """Evento WebSocket."""
    event: str  # new_order | order_ready | order_cancelled | state_sync
    data: dict[str, Any]
