"""
Schemas Pydantic para Contabilidad — Request/Response.

Validation layer para los endpoints contables.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Setup / Inversión
# ═══════════════════════════════════════════════════════════════


class InvestmentInput(BaseModel):
    """Variables de inversión para setup inicial."""

    capital: float = Field(..., gt=0, description="Aporte de capital de socios")
    loan_amount: float = Field(0.0, ge=0, description="Préstamo bancario")
    loan_rate_annual: float = Field(
        0.10, ge=0, le=1, description="Tasa de interés anual (0.10 = 10%)"
    )
    loan_term_months: int = Field(12, ge=1, le=60)

    # Compras iniciales
    equipment_cost: float = Field(0.0, ge=0, description="Equipamiento de cocina")
    furniture_cost: float = Field(0.0, ge=0, description="Mobiliario")
    computer_cost: float = Field(0.0, ge=0, description="Equipos de cómputo")
    software_cost: float = Field(0.0, ge=0, description="Software / licencias")
    guarantee_deposit: float = Field(0.0, ge=0, description="Garantía de alquiler")
    initial_inventory: float = Field(0.0, ge=0, description="Inventario inicial")

    # Proyecciones
    monthly_sales: list[float] = Field(
        default_factory=list, description="Ventas proyectadas por mes (12)"
    )
    monthly_cost_pct: float = Field(
        0.40, ge=0, le=1, description="% de costo sobre ventas"
    )
    monthly_rent: float = Field(0.0, ge=0)
    monthly_utilities: float = Field(0.0, ge=0, description="Luz, agua, internet")
    monthly_salaries: float = Field(0.0, ge=0)
    monthly_marketing: float = Field(0.0, ge=0)
    monthly_admin: float = Field(0.0, ge=0)
    monthly_maintenance: float = Field(0.0, ge=0)

    # Vida útil
    equipment_life_years: int = Field(8, ge=1, le=50)
    furniture_life_years: int = Field(10, ge=1, le=50)
    computer_life_years: int = Field(5, ge=1, le=20)
    software_life_years: int = Field(3, ge=1, le=10)

    months: int = Field(12, ge=1, le=60, description="Meses a proyectar")
    start_date: Optional[date] = Field(None, description="Fecha de inicio")


# ═══════════════════════════════════════════════════════════════
# Transacción
# ═══════════════════════════════════════════════════════════════


class TransactionLine(BaseModel):
    account_code: str = Field(..., min_length=1, max_length=10)
    debit: float = Field(0.0, ge=0)
    credit: float = Field(0.0, ge=0)
    description: Optional[str] = None


class TransactionInput(BaseModel):
    entry_type: str = Field("manual", pattern=r"^(apertura|compra|venta|gasto|manual)$")
    date: date
    description: str = Field(..., min_length=1, max_length=300)
    lines: list[TransactionLine] = Field(..., min_length=2)
    reference: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Kárdex
# ═══════════════════════════════════════════════════════════════


class ProductInput(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field("kg", max_length=10)
    initial_stock: float = Field(0.0, ge=0)
    initial_cost: float = Field(0.0, ge=0)


class KardexMovementInput(BaseModel):
    product_code: str
    quantity: float = Field(..., gt=0)
    unit_cost: float = Field(0.0, ge=0)
    concept: str = Field(..., min_length=1, max_length=200)
    date: date
    reference_type: str = Field("compra", description="compra | venta | merma")


class KardexEntryInput(KardexMovementInput):
    """Entrada de inventario (compra)."""
    reference_type: str = Field("compra")


class KardexExitInput(BaseModel):
    product_code: str
    quantity: float = Field(..., gt=0)
    concept: str = Field(..., min_length=1, max_length=200)
    date: date
    reference_type: str = Field("venta", description="venta | merma | ajuste")


# ═══════════════════════════════════════════════════════════════
# Respuestas
# ═══════════════════════════════════════════════════════════════


class BCSSAccountResponse(BaseModel):
    account_code: str
    account_name: str
    total_debit: float
    total_credit: float
    balance: float
    balance_nature: str  # D | A


class BCSSResponse(BaseModel):
    lines: list[BCSSAccountResponse]
    total_debits: float
    total_credits: float
    is_balanced: bool


class IncomeStatementResponse(BaseModel):
    period: str
    revenue: float
    cost_of_sales: float
    gross_profit: float
    gross_margin_pct: float
    operating_expenses: dict[str, float]
    depreciation: float
    financial_expenses: float
    ebitda: float
    ebit: float
    operating_margin_pct: float
    income_before_tax: float
    income_tax: float
    net_income: float
    net_margin_pct: float


class BalanceSheetResponse(BaseModel):
    as_of: date
    current_assets: dict[str, float]
    non_current_assets: dict[str, float]
    accumulated_depreciation: float
    total_assets: float
    current_liabilities: dict[str, float]
    non_current_liabilities: dict[str, float]
    total_liabilities: float
    capital: float
    retained_earnings: float
    current_income: float
    total_equity: float
    total_liabilities_and_equity: float
    is_balanced: bool


class RatioItemResponse(BaseModel):
    name: str
    value: float
    target: str
    traffic_light: str
    formula: str


class KardexProductResponse(BaseModel):
    code: str
    name: str
    unit: str
    current_stock: float
    average_cost: float
    total_value: float


class KardexRecordResponse(BaseModel):
    product_code: str
    movement_type: str
    concept: str
    quantity: float
    unit_cost: float
    total: float
    balance_quantity: float
    balance_avg_cost: float
    balance_total: float
    date: date


class WarehouseCloseResponse(BaseModel):
    inventory_value: float
    accounting_balance: float
    difference: float
    is_balanced: bool
    details: dict
    alerts: list[str]


class FinancialReportResponse(BaseModel):
    period_start: date
    period_end: date
    total_entries: int
    bcss: BCSSResponse | None = None
    income_statement: IncomeStatementResponse | None = None
    balance_sheet: BalanceSheetResponse | None = None
    ratios: list[RatioItemResponse] | None = None
    validations: dict[str, bool]


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[str]


# ═══════════════════════════════════════════════════════════════
# Company Settings / Branding
# ═══════════════════════════════════════════════════════════════


class ColorPalette(BaseModel):
    """Paleta de colores configurable por empresa."""
    primary: str = Field("#1a365d", description="Color primario")
    secondary: str = Field("#2b6cb0", description="Color secundario")
    accent: str = Field("#e53e3e", description="Color de acento")
    background: str = Field("#f7fafc", description="Fondo base")
    surface: str = Field("#ffffff", description="Superficie (cards)")
    text_primary: str = Field("#1a202c", description="Texto principal")
    text_secondary: str = Field("#718096", description="Texto secundario")
    success: str = Field("#38a169", description="Éxito / verde")
    warning: str = Field("#d69e2e", description="Advertencia / amarillo")
    error: str = Field("#e53e3e", description="Error / rojo")


class CompanySettings(BaseModel):
    """Configuración de empresa (branding, preferencias)."""
    palette: ColorPalette = Field(default_factory=ColorPalette)
    logo_url: str | None = None
    favicon_url: str | None = None
    date_format: str = Field("DD/MM/YYYY", description="Formato de fecha")
    currency: str = Field("PEN", description="Moneda (PEN, USD)")
    timezone: str = Field("America/Lima", description="Zona horaria IANA")
