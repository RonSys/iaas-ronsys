"""
Schemas Pydantic — Ventas + POS + Flujo de Caja (HU-F2, HU-F1).

Validation layer para los endpoints de ventas, sesiones y cashflow.
"""

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ═══════════════════════════════════════════════════════════════
# Sesiones POS
# ═══════════════════════════════════════════════════════════════


class PosSessionOpen(BaseModel):
    """Apertura de sesión POS."""
    opening_cash: float = Field(..., ge=0, description="Monto de caja inicial")
    notes: str | None = None


class PosSessionClose(BaseModel):
    """Cierre de sesión POS."""
    closing_cash: float = Field(..., ge=0, description="Efectivo contado al cierre")
    notes: str | None = None


class PosSessionResponse(BaseModel):
    """Respuesta de sesión POS."""
    id: int
    company_id: int
    user_id: int
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: float
    closing_cash: float | None = None
    expected_cash: float | None = None
    difference: float | None = None
    status: str
    notes: str | None = None
    sales_count: int = 0
    total_sales: float = 0.0

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# Ventas
# ═══════════════════════════════════════════════════════════════


class SaleItemCreate(BaseModel):
    """Ítem de venta a crear."""
    product_id: int | None = None
    item_name: str = Field(..., min_length=1, max_length=200)
    item_type: str = Field("product", description="product | service | combo")
    quantity: float = Field(..., gt=0)
    unit_of_measure: str = Field("unidad", max_length=10)
    unit_price: float = Field(..., ge=0)
    discount_pct: float = Field(0.0, ge=0, le=100)
    discount_amount: float = Field(0.0, ge=0)
    tax_pct: float = Field(18.0, ge=0, le=100)
    tax_amount: float = Field(0.0, ge=0)
    total: float = Field(..., ge=0)


class SalePaymentCreate(BaseModel):
    """Método de pago de una venta."""
    payment_method: str = Field(..., description="cash | card | yape | plin | transfer")
    amount: float = Field(..., gt=0)
    reference: str | None = None


class RestaurantSaleCreate(BaseModel):
    """Especialización restaurante."""
    table_number: str | None = None
    guests: int = 1
    order_type: str = Field("dine_in", description="dine_in | takeout | delivery")
    waiter_name: str | None = None
    tip_amount: float = 0.0
    tip_pct: float = 0.0
    kitchen_notes: str | None = None


class HardwareSaleCreate(BaseModel):
    """Especialización ferretería."""
    invoice_type: str = Field("boleta", description="boleta | factura")
    delivery_address: str | None = None
    requires_install: bool = False
    warranty_months: int = 0


class SaleCreate(BaseModel):
    """Creación de venta completa."""
    customer_name: str | None = None
    customer_doc: str | None = None
    business_type: str = Field(..., description="restaurant | hardware | retail | service")
    items: list[SaleItemCreate] = Field(..., min_length=1)
    payments: list[SalePaymentCreate] = Field(..., min_length=1)
    # Especialización (opcional, uno u otro según business_type)
    restaurant_data: RestaurantSaleCreate | None = None
    hardware_data: HardwareSaleCreate | None = None

    @model_validator(mode="after")
    def validate_payments_cover_total(self) -> "SaleCreate":
        total_items = sum(i.total for i in self.items)
        total_payments = sum(p.amount for p in self.payments)
        if total_payments < total_items - 0.01:
            raise ValueError(
                f"El total de pagos ({total_payments:.2f}) no cubre "
                f"el total de la venta ({total_items:.2f})"
            )
        return self


class SaleVoidRequest(BaseModel):
    """Solicitud de anulación de venta."""
    reason: str = Field(..., min_length=1, max_length=300)


class SaleItemResponse(BaseModel):
    """Ítem de venta en respuesta."""
    id: int
    product_id: int | None = None
    item_name: str
    item_type: str
    quantity: float
    unit_of_measure: str
    unit_price: float
    discount_pct: float
    discount_amount: float
    tax_pct: float
    tax_amount: float
    total: float
    kardex_movement_id: int | None = None

    class Config:
        from_attributes = True


class SalePaymentResponse(BaseModel):
    """Método de pago en respuesta."""
    id: int
    payment_method: str
    amount: float
    reference: str | None = None

    class Config:
        from_attributes = True


class RestaurantSaleResponse(BaseModel):
    """Especialización restaurante en respuesta."""
    id: int
    table_number: str | None = None
    guests: int
    order_type: str
    waiter_name: str | None = None
    tip_amount: float
    tip_pct: float
    kitchen_notes: str | None = None

    class Config:
        from_attributes = True


class HardwareSaleResponse(BaseModel):
    """Especialización ferretería en respuesta."""
    id: int
    invoice_type: str
    delivery_address: str | None = None
    requires_install: bool
    warranty_months: int

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    """Venta en respuesta (lista)."""
    id: int
    sale_number: str
    sale_date: date
    sale_time: time
    customer_name: str | None = None
    business_type: str
    subtotal: float
    discount_total: float
    tax_total: float
    tip_amount: float
    total: float
    is_voided: bool
    void_reason: str | None = None
    payments: list[SalePaymentResponse] = []

    class Config:
        from_attributes = True


class SaleDetailResponse(SaleResponse):
    """Venta en detalle (incluye items + especialización)."""
    items: list[SaleItemResponse] = []
    restaurant_data: RestaurantSaleResponse | None = None
    hardware_data: HardwareSaleResponse | None = None
    session_id: int
    user_id: int
    customer_doc: str | None = None
    journal_entry_id: int | None = None


class SaleListResponse(BaseModel):
    """Respuesta paginada de listado de ventas."""
    items: list[SaleResponse]
    total: int
    page: int
    limit: int
    pages: int


# ═══════════════════════════════════════════════════════════════
# Ticket
# ═══════════════════════════════════════════════════════════════


class TicketResponse(BaseModel):
    """Ticket de venta formateado (JSON)."""
    sale_number: str
    sale_date: date
    sale_time: time
    customer_name: str | None = None
    customer_doc: str | None = None
    business_type: str
    items: list[dict]
    payments: list[dict]
    subtotal: float
    discount_total: float
    tax_total: float
    tip_amount: float
    total: float
    # Especialización
    table_number: str | None = None
    waiter_name: str | None = None
    order_type: str | None = None
    invoice_type: str | None = None
    # Texto plano
    text: str = ""


# ═══════════════════════════════════════════════════════════════
# Payment Methods
# ═══════════════════════════════════════════════════════════════


class PaymentMethodInfo(BaseModel):
    """Info de un método de pago."""
    method: str
    label: str
    enabled: bool


class PaymentMethodsResponse(BaseModel):
    """Lista de métodos de pago habilitados."""
    methods: list[PaymentMethodInfo]


# ═══════════════════════════════════════════════════════════════
# Cashflow
# ═══════════════════════════════════════════════════════════════


class CashflowLineResponse(BaseModel):
    """Línea de flujo de caja en respuesta."""
    month: int
    year: int
    concept: str
    category: str
    projected: float = 0.0
    actual: float = 0.0
    difference: float = 0.0
    difference_pct: float = 0.0


class CashflowAlertResponse(BaseModel):
    """Alerta financiera en respuesta."""
    severity: str
    category: str
    message: str
    month: int | None = None


class CashflowReportResponse(BaseModel):
    """Reporte completo de flujo de caja."""
    company_id: int
    from_date: date
    to_date: date
    view: str
    opening_balance: float
    total_income: float
    total_expenses: float
    net_cashflow: float
    closing_balance: float
    is_balanced: bool
    lines: list[CashflowLineResponse] = []
    alerts: list[CashflowAlertResponse] = []


# ═══════════════════════════════════════════════════════════════
# Company Settings (HU-F1-002)
# ═══════════════════════════════════════════════════════════════


class FeatureFlags(BaseModel):
    """Feature flags por tipo de negocio."""
    tables_enabled: bool = False
    tips_enabled: bool = False
    recipe_explosion: bool = False
    warranty_tracking: bool = False
    invoice_required: bool = False
    igv_included_in_price: bool = False
    delivery_enabled: bool = False


class TaxConfig(BaseModel):
    """Configuración tributaria."""
    igv_rate: float = Field(18.0, ge=0, le=100)
    igv_included_in_price: bool = False
    income_tax_rate: float = Field(29.5, ge=0, le=100)


class CompanyFeaturesSettings(BaseModel):
    """Configuración completa de features + tax de una empresa."""
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    tax_config: TaxConfig = Field(default_factory=TaxConfig)


class CompanySettingsUpdateRequest(BaseModel):
    """Request para actualizar settings de la empresa."""
    features: FeatureFlags | None = None
    tax_config: TaxConfig | None = None


# ═══════════════════════════════════════════════════════════════
# Defaults por business_type
# ═══════════════════════════════════════════════════════════════

BUSINESS_TYPE_DEFAULTS: dict[str, CompanyFeaturesSettings] = {
    "restaurant": CompanyFeaturesSettings(
        features=FeatureFlags(
            tables_enabled=True,
            tips_enabled=True,
            recipe_explosion=True,
            igv_included_in_price=True,
            delivery_enabled=True,
        ),
        tax_config=TaxConfig(igv_included_in_price=True),
    ),
    "hardware": CompanyFeaturesSettings(
        features=FeatureFlags(
            warranty_tracking=True,
            invoice_required=True,
            igv_included_in_price=False,
        ),
        tax_config=TaxConfig(igv_included_in_price=False),
    ),
    "retail": CompanyFeaturesSettings(
        features=FeatureFlags(
            igv_included_in_price=True,
        ),
        tax_config=TaxConfig(igv_included_in_price=True),
    ),
    "service": CompanyFeaturesSettings(
        features=FeatureFlags(
            igv_included_in_price=True,
        ),
        tax_config=TaxConfig(igv_included_in_price=True),
    ),
}