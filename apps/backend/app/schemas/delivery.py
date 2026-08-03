"""
📦 Schemas — Módulo Delivery (Spec 03, Fase A).

Contratos de los endpoints públicos (/api/public) y staff (/api/v1/delivery).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Catálogo público
# ═══════════════════════════════════════════════════════════════

class PublicModifier(BaseModel):
    id: int
    name: str
    price_adjustment: float = 0
    max_select: int = 1


class PublicMenuItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    delivery_surcharge: float = 0
    category: str
    item_type: str = "food"
    preparation_area: str = "cocina"
    modifiers: list[PublicModifier] = Field(default_factory=list)
    image_url: Optional[str] = None
    available: bool = True  # dentro de la ventana horaria en este momento


class PublicMenuSection(BaseModel):
    id: int
    name: str
    items: list[PublicMenuItem] = Field(default_factory=list)


class PublicPromotion(BaseModel):
    id: int
    name: str
    promo_type: str
    discount_value: float
    description: Optional[str] = None


class PublicMenuResponse(BaseModel):
    tenant_name: str
    delivery_window: dict = Field(default_factory=dict)  # {from, to}
    currency: str = "PEN"
    yape_phone: Optional[str] = None  # D4: configurable en companies.settings
    branding: dict = Field(default_factory=dict)  # D-03: {palette, logo_url} para la landing
    sections: list[PublicMenuSection] = Field(default_factory=list)
    promotions: list[PublicPromotion] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Zonas (público)
# ═══════════════════════════════════════════════════════════════

class PublicZone(BaseModel):
    id: int
    name: str
    districts: Optional[list] = None
    fee: float
    min_order: float
    eta_min: int


# ═══════════════════════════════════════════════════════════════
# Checkout
# ═══════════════════════════════════════════════════════════════

class CheckoutItem(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1)
    modifiers: list[dict] = Field(default_factory=list)


class CheckoutCustomer(BaseModel):
    name: Optional[str] = None
    phone: str
    address: str = Field(min_length=5)
    lat: Optional[float] = None
    lng: Optional[float] = None


class CheckoutPayment(BaseModel):
    method: str  # yape | plin | cash
    reference: Optional[str] = None


class CheckoutUtm(BaseModel):
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    term: Optional[str] = None
    content: Optional[str] = None


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem] = Field(min_length=1)
    customer: CheckoutCustomer
    zone_id: int
    payment: CheckoutPayment
    utm: Optional[CheckoutUtm] = None
    notes: Optional[str] = None


class CheckoutResponse(BaseModel):
    tracking_code: str
    sale_id: int
    sale_number: str
    status: str = "received"
    eta_min: Optional[int] = None
    totals: dict = Field(default_factory=dict)  # {subtotal, discount_total, fee, total}
    payment: dict = Field(default_factory=dict)  # {method, status}
    promotion: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════
# Seguimiento público
# ═══════════════════════════════════════════════════════════════

class TrackingStatusOut(BaseModel):
    tracking_code: str
    status: str
    eta_min: Optional[int] = None
    timestamps: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Staff — Zonas / Repartidores / Campañas
# ═══════════════════════════════════════════════════════════════

class ZoneIn(BaseModel):
    name: str
    description: Optional[str] = None
    districts: Optional[list] = None
    fee: float = 0
    min_order: float = 0
    eta_min: int = 45
    active: bool = True


class ZoneOut(ZoneIn):
    id: int
    created_at: Optional[datetime] = None


class CourierIn(BaseModel):
    name: str
    phone: Optional[str] = None
    vehicle: Optional[str] = None
    user_id: Optional[int] = None
    status: str = "available"  # available | on_delivery | offline
    active: bool = True


class CourierOut(CourierIn):
    id: int
    created_at: Optional[datetime] = None


class CampaignIn(BaseModel):
    name: str
    channel: str = "meta"
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    budget: float = 0
    spend: float = 0
    starts_on: Optional[str] = None
    ends_on: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None


class CampaignOut(CampaignIn):
    id: int
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════
# Métricas
# ═══════════════════════════════════════════════════════════════

class CampaignMetricsOut(BaseModel):
    campaign_id: int
    name: str
    channel: str
    spend: float
    orders: int
    gmv: float
    aov: float
    roas: float


class DeliveryOverviewOut(BaseModel):
    orders: int
    gmv: float
    fee_total: float
    avg_delivery_min: Optional[float] = None
    cancelled: int
