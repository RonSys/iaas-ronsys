"""
🧠 Motor Contable — Dominio Puro (sin dependencias externas)

Basado en:
  - simulador-financiero/docs/03-logica-contable.md
  - simulador-financiero/docs/02-plan-cuentas.md

Arquitectura hexagonal: dominio puro, sin DB, sin framework.

Responsabilidad:
  - Generar asientos de apertura desde variables de inversión
  - Construir Libro Mayor desde una lista de asientos
  - Calcular Balance de Comprobación (BCSS)
  - Validar consistencia (partida doble, Σ Debe = Σ Haber)
  - Generar estados financieros (PYG, Balance General)
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from functools import total_ordering
from typing import Optional
import uuid


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════


class AccountNature(str, Enum):
    DEBIT = "D"  # Activo, Costo, Gasto
    CREDIT = "A"  # Pasivo, Patrimonio, Ingreso


class AccountCategory(str, Enum):
    ASSET = "asset"  # Activo (1xx)
    CONTRA_ASSET = "contra_asset"  # Depreciación acum. (19x)
    LIABILITY = "liability"  # Pasivo (2xx)
    EQUITY = "equity"  # Patrimonio (3xx)
    INCOME = "income"  # Ingresos (4xx)
    COST = "cost"  # Costos (5xx)
    EXPENSE = "expense"  # Gastos (6xx)
    CLOSING = "closing"  # Cierre (8xx)


class EntryType(str, Enum):
    APERTURA = "apertura"
    COMPRA = "compra"
    VENTA = "venta"
    GASTO = "gasto"
    DEPRECIACION = "depreciacion"
    CIERRE = "cierre"
    MANUAL = "manual"


class MovementType(str, Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    AJUSTE = "ajuste"


# ═══════════════════════════════════════════════════════════════
# Entidades del Dominio (puro)
# ═══════════════════════════════════════════════════════════════


@dataclass
class AccountDef:
    """Definición de cuenta contable (dominio)."""
    code: str
    name: str
    parent_code: Optional[str] = None
    nature: AccountNature = AccountNature.DEBIT
    category: AccountCategory = AccountCategory.ASSET
    is_balance_sheet: bool = True
    active: bool = True


@dataclass
class JournalLine:
    """Línea de asiento (dominio)."""
    account_code: str
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None

    def __post_init__(self):
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Debit y credit no pueden ser negativos")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("Al menos debit o credit debe ser > 0")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("Una línea no puede tener debit y credit simultáneamente")


@dataclass
class JournalEntry:
    """Asiento contable (dominio)."""
    entry_number: str
    date_: date
    description: str
    entry_type: EntryType = EntryType.MANUAL
    lines: list[JournalLine] = field(default_factory=list)
    reference: Optional[str] = None

    @property
    def total_debit(self) -> float:
        return round(sum(line.debit for line in self.lines), 2)

    @property
    def total_credit(self) -> float:
        return round(sum(line.credit for line in self.lines), 2)

    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def add_line(self, line: JournalLine) -> None:
        self.lines.append(line)


@dataclass
class LedgerAccount:
    """Cuenta en el Libro Mayor."""
    account_code: str
    account_name: str
    nature: AccountNature
    category: AccountCategory
    entries: list[tuple[JournalEntry, JournalLine]] = field(default_factory=list)

    @property
    def total_debit(self) -> float:
        return round(sum(line.debit for _, line in self.entries), 2)

    @property
    def total_credit(self) -> float:
        return round(sum(line.credit for _, line in self.entries), 2)

    @property
    def balance(self) -> float:
        """Saldo de la cuenta según su naturaleza."""
        if self.nature == AccountNature.DEBIT:
            return round(self.total_debit - self.total_credit, 2)
        else:
            return round(self.total_credit - self.total_debit, 2)

    @property
    def balance_nature(self) -> str:
        """'D' si saldo deudor, 'A' si saldo acreedor."""
        bal = self.total_debit - self.total_credit
        return "D" if bal > 0 else ("A" if bal < 0 else "-")


@dataclass
class BCSSLine:
    """Línea del Balance de Comprobación."""
    account_code: str
    account_name: str
    total_debit: float
    total_credit: float
    balance: float
    balance_nature: str  # 'D' o 'A'


@dataclass
class BCSS:
    """Balance de Comprobación de Sumas y Saldos."""
    lines: list[BCSSLine] = field(default_factory=list)

    @property
    def total_debits(self) -> float:
        return round(sum(line.total_debit for line in self.lines), 2)

    @property
    def total_credits(self) -> float:
        return round(sum(line.total_credit for line in self.lines), 2)

    @property
    def total_debit_balances(self) -> float:
        return round(sum(line.balance for line in self.lines if line.balance > 0), 2)

    @property
    def total_credit_balances(self) -> float:
        return round(sum(abs(line.balance) for line in self.lines if line.balance < 0), 2)

    def is_balanced(self) -> bool:
        """Regla de oro: Σ Saldos Deudores = Σ Saldos Acreedores."""
        return self.total_debits == self.total_credits


@dataclass
class IncomeStatement:
    """Estado de Resultados (PYG)."""
    period: str  # ej: '2026-06'
    revenue: float = 0.0  # Ingresos (40x)
    cost_of_sales: float = 0.0  # Costo de Ventas (50x)
    gross_profit: float = 0.0  # Utilidad Bruta
    operating_expenses: dict[str, float] = field(default_factory=dict)  # por categoría
    depreciation: float = 0.0
    financial_expenses: float = 0.0
    ebitda: float = 0.0
    ebit: float = 0.0  # Operating Income
    income_before_tax: float = 0.0
    income_tax: float = 0.0  # 29.5% Perú
    net_income: float = 0.0


@dataclass
class BalanceSheet:
    """Balance General."""
    as_of: date
    # Activo
    current_assets: dict[str, float] = field(default_factory=dict)
    non_current_assets: dict[str, float] = field(default_factory=dict)
    accumulated_depreciation: float = 0.0
    # Pasivo
    current_liabilities: dict[str, float] = field(default_factory=dict)
    non_current_liabilities: dict[str, float] = field(default_factory=dict)
    # Patrimonio
    capital: float = 0.0
    retained_earnings: float = 0.0
    current_income: float = 0.0

    @property
    def total_assets(self) -> float:
        current = sum(self.current_assets.values())
        non_current = (
            sum(self.non_current_assets.values()) - abs(self.accumulated_depreciation)
        )
        return round(current + non_current, 2)

    @property
    def total_liabilities(self) -> float:
        return round(
            sum(self.current_liabilities.values())
            + sum(self.non_current_liabilities.values()),
            2,
        )

    @property
    def total_equity(self) -> float:
        return round(self.capital + self.retained_earnings + self.current_income, 2)

    @property
    def total_liabilities_and_equity(self) -> float:
        return round(self.total_liabilities + self.total_equity, 2)

    def is_balanced(self) -> bool:
        """Activo = Pasivo + Patrimonio."""
        return self.total_assets == self.total_liabilities_and_equity


# ═══════════════════════════════════════════════════════════════
# Variables de Entrada (para Setup)
# ═══════════════════════════════════════════════════════════════


@dataclass
class InvestmentVariables:
    """Variables de inversión inicial y operación."""

    # ─── Apertura ──────────────────────────────────────────
    capital: float  # Aporte de socios
    loan_amount: float = 0.0  # Préstamo bancario
    loan_rate_annual: float = 0.10  # Tasa de interés anual
    loan_term_months: int = 12

    # ─── Compras iniciales ────────────────────────────────
    equipment_cost: float = 0.0  # Equipamiento de cocina
    furniture_cost: float = 0.0  # Mobiliario
    computer_cost: float = 0.0  # Equipos de cómputo
    software_cost: float = 0.0  # Software / licencias
    guarantee_deposit: float = 0.0  # Garantía de alquiler
    initial_inventory: float = 0.0  # Inventario inicial

    # ─── Proyecciones mensuales ───────────────────────────
    monthly_sales: list[float] = field(default_factory=list)
    monthly_cost_pct: float = 0.40  # % de costo sobre ventas
    monthly_rent: float = 0.0
    monthly_utilities: float = 0.0  # Luz, agua, internet
    monthly_salaries: float = 0.0
    monthly_marketing: float = 0.0
    monthly_admin: float = 0.0
    monthly_maintenance: float = 0.0

    # ─── Vida útil equipos (para depreciación) ────────────
    equipment_life_years: int = 8
    furniture_life_years: int = 10
    computer_life_years: int = 5
    software_life_years: int = 3


# ═══════════════════════════════════════════════════════════════
# Plan de Cuentas por Defecto (PCGE adaptado)
# ═══════════════════════════════════════════════════════════════

DEFAULT_CHART_OF_ACCOUNTS: list[AccountDef] = [
    # ─── ACTIVO ──────────────────────────────────────────
    AccountDef("10", "Efectivo y Equivalentes", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("101", "Caja", "10", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("102", "Bancos", "10", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("11", "Cuentas por Cobrar", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("12", "Inventarios", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("121", "Insumos de cocina", "12", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("13", "Inmuebles, Maquinaria y Equipo", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("131", "Equipamiento de cocina", "13", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("132", "Mobiliario del local", "13", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("133", "Equipos de cómputo", "13", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("14", "Activos Intangibles", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("141", "Software (ERP, licencias)", "14", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("142", "Marca y derechos", "14", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("15", "Depósitos en Garantía", nature=AccountNature.DEBIT, category=AccountCategory.ASSET),
    AccountDef("151", "Garantía de alquiler", "15", AccountNature.DEBIT, AccountCategory.ASSET),
    AccountDef("19", "Depreciación Acumulada", nature=AccountNature.CREDIT, category=AccountCategory.CONTRA_ASSET),
    AccountDef("191", "Dep. Acum. Equipamiento cocina", "19", AccountNature.CREDIT, AccountCategory.CONTRA_ASSET),
    AccountDef("192", "Dep. Acum. Mobiliario", "19", AccountNature.CREDIT, AccountCategory.CONTRA_ASSET),
    AccountDef("193", "Dep. Acum. Equipos cómputo", "19", AccountNature.CREDIT, AccountCategory.CONTRA_ASSET),
    # ─── PASIVO ──────────────────────────────────────────
    AccountDef("20", "Tributos por Pagar", nature=AccountNature.CREDIT, category=AccountCategory.LIABILITY),
    AccountDef("201", "IGV por pagar", "20", AccountNature.CREDIT, AccountCategory.LIABILITY),
    AccountDef("202", "Impuesto a la Renta por pagar", "20", AccountNature.CREDIT, AccountCategory.LIABILITY),
    AccountDef("21", "Cuentas por Pagar Comerciales", nature=AccountNature.CREDIT, category=AccountCategory.LIABILITY),
    AccountDef("22", "Préstamos Bancarios", nature=AccountNature.CREDIT, category=AccountCategory.LIABILITY),
    AccountDef("221", "Préstamo CP", "22", AccountNature.CREDIT, AccountCategory.LIABILITY),
    AccountDef("222", "Préstamo LP", "22", AccountNature.CREDIT, AccountCategory.LIABILITY),
    AccountDef("23", "Remuneraciones por Pagar", nature=AccountNature.CREDIT, category=AccountCategory.LIABILITY),
    AccountDef("24", "Cuentas por Pagar Varias", nature=AccountNature.CREDIT, category=AccountCategory.LIABILITY),
    # ─── PATRIMONIO ─────────────────────────────────────
    AccountDef("30", "Capital", nature=AccountNature.CREDIT, category=AccountCategory.EQUITY),
    AccountDef("301", "Aporte de socios", "30", AccountNature.CREDIT, AccountCategory.EQUITY),
    AccountDef("31", "Resultados Acumulados", nature=AccountNature.CREDIT, category=AccountCategory.EQUITY),
    AccountDef("32", "Resultado del Ejercicio", nature=AccountNature.CREDIT, category=AccountCategory.EQUITY),
    # ─── INGRESOS ───────────────────────────────────────
    AccountDef("40", "Ventas", nature=AccountNature.CREDIT, category=AccountCategory.INCOME, is_balance_sheet=False),
    AccountDef("401", "Venta de platos y bebidas", "40", AccountNature.CREDIT, AccountCategory.INCOME, is_balance_sheet=False),
    AccountDef("41", "Otros Ingresos", nature=AccountNature.CREDIT, category=AccountCategory.INCOME, is_balance_sheet=False),
    # ─── COSTOS ─────────────────────────────────────────
    AccountDef("50", "Costo de Ventas", nature=AccountNature.DEBIT, category=AccountCategory.COST, is_balance_sheet=False),
    AccountDef("501", "Materia prima e insumos", "50", AccountNature.DEBIT, AccountCategory.COST, is_balance_sheet=False),
    AccountDef("502", "Mano de obra directa", "50", AccountNature.DEBIT, AccountCategory.COST, is_balance_sheet=False),
    AccountDef("503", "Costos indirectos", "50", AccountNature.DEBIT, AccountCategory.COST, is_balance_sheet=False),
    # ─── GASTOS ─────────────────────────────────────────
    AccountDef("60", "Gastos de Personal", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("601", "Sueldos y salarios", "60", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("602", "Beneficios sociales", "60", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("61", "Gastos de Operación", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("611", "Alquiler del local", "61", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("612", "Servicios públicos", "61", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("613", "Mantenimiento", "61", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("62", "Gastos de Ventas y Marketing", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("621", "Publicidad y redes", "62", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("622", "Delivery", "62", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("63", "Gastos Administrativos", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("631", "Útiles de oficina", "63", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("632", "Suscripciones (software)", "63", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("64", "Gastos Financieros", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("641", "Intereses de préstamo", "64", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("642", "Comisiones bancarias", "64", AccountNature.DEBIT, AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("65", "Depreciación", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    AccountDef("66", "Otros Gastos", nature=AccountNature.DEBIT, category=AccountCategory.EXPENSE, is_balance_sheet=False),
    # ─── CUENTAS DE CIERRE ──────────────────────────────
    AccountDef("80", "Resumen de Resultados", nature=AccountNature.CREDIT, category=AccountCategory.CLOSING, is_balance_sheet=False),
    AccountDef("81", "Pérdidas y Ganancias", nature=AccountNature.CREDIT, category=AccountCategory.CLOSING, is_balance_sheet=False),
]


def get_account_map(accounts: list[AccountDef] | None = None) -> dict[str, AccountDef]:
    """Construye un mapa code → AccountDef para lookup rápido."""
    if accounts is None:
        accounts = DEFAULT_CHART_OF_ACCOUNTS
    return {a.code: a for a in accounts}


# ═══════════════════════════════════════════════════════════════
# Generador de Asientos
# ═══════════════════════════════════════════════════════════════


def generate_opening_entries(
    vars_: InvestmentVariables,
    start_date: date = date(2026, 1, 1),
    accounts: list[AccountDef] | None = None,
) -> list[JournalEntry]:
    """
    Genera los asientos de apertura desde variables de inversión.

    Asientos generados:
      - Aporte de capital: Debe 10 / Haber 30
      - Préstamo:           Debe 10 / Haber 22
      - Compra equipos:     Debe 13 / Haber 10
      - Garantía alquiler:  Debe 15 / Haber 10
      - Inventario inicial: Debe 12 / Haber 10
    """
    entries: list[JournalEntry] = []
    n = 0

    def next_number() -> str:
        nonlocal n
        n += 1
        return f"AS-{n:03d}"

    # 1. Aporte de Capital
    if vars_.capital > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Aporte de capital de socios",
            entry_type=EntryType.APERTURA,
            lines=[
                JournalLine("10", debit=vars_.capital, description="Efectivo recibido"),
                JournalLine("30", credit=vars_.capital, description="Capital social"),
            ],
        )
        entries.append(e)

    # 2. Préstamo Bancario
    if vars_.loan_amount > 0:
        # Se registra como LP para simplificar (se reclasifica CP en ajustes)
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Préstamo bancario recibido",
            entry_type=EntryType.APERTURA,
            lines=[
                JournalLine("10", debit=vars_.loan_amount, description="Efectivo recibido del préstamo"),
                JournalLine("222", credit=vars_.loan_amount, description="Préstamo LP por pagar"),
            ],
        )
        entries.append(e)

    # 3. Compra de Equipamiento
    if vars_.equipment_cost > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Compra de equipamiento de cocina",
            entry_type=EntryType.COMPRA,
            lines=[
                JournalLine("131", debit=vars_.equipment_cost, description="Equipamiento de cocina"),
                JournalLine("10", credit=vars_.equipment_cost, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # 4. Compra de Mobiliario
    if vars_.furniture_cost > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Compra de mobiliario del local",
            entry_type=EntryType.COMPRA,
            lines=[
                JournalLine("132", debit=vars_.furniture_cost, description="Mobiliario"),
                JournalLine("10", credit=vars_.furniture_cost, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # 5. Compra de Equipos de Cómputo
    if vars_.computer_cost > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Compra de equipos de cómputo",
            entry_type=EntryType.COMPRA,
            lines=[
                JournalLine("133", debit=vars_.computer_cost, description="Equipos de cómputo"),
                JournalLine("10", credit=vars_.computer_cost, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # 6. Compra de Software
    if vars_.software_cost > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Adquisición de software y licencias",
            entry_type=EntryType.COMPRA,
            lines=[
                JournalLine("141", debit=vars_.software_cost, description="Software"),
                JournalLine("10", credit=vars_.software_cost, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # 7. Garantía de Alquiler
    if vars_.guarantee_deposit > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Depósito de garantía de alquiler",
            entry_type=EntryType.APERTURA,
            lines=[
                JournalLine("151", debit=vars_.guarantee_deposit, description="Garantía"),
                JournalLine("10", credit=vars_.guarantee_deposit, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # 8. Inventario Inicial
    if vars_.initial_inventory > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=start_date,
            description="Compra de inventario inicial",
            entry_type=EntryType.APERTURA,
            lines=[
                JournalLine("12", debit=vars_.initial_inventory, description="Inventario inicial"),
                JournalLine("10", credit=vars_.initial_inventory, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    return entries


def generate_monthly_entries(
    vars_: InvestmentVariables,
    month: int,
    year: int = 2026,
    entries_so_far: list[JournalEntry] | None = None,
) -> list[JournalEntry]:
    """
    Genera asientos operativos para un mes específico.

    meses 1-indexed: month=1 para enero, etc.
    """
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    month_date = date(year, month, last_day)

    # Número base para los asientos
    base = (entries_so_far or [])
    n = len(base)

    def next_number() -> str:
        nonlocal n
        n += 1
        return f"AS-{n:03d}"

    entries: list[JournalEntry] = []
    idx = month - 1

    # ─── Ventas (todas son contado) ──────────────────────
    sales = vars_.monthly_sales[idx] if idx < len(vars_.monthly_sales) else 0
    if sales > 0:
        cost_pct = vars_.monthly_cost_pct
        cost = round(sales * cost_pct, 2)

        # Registro de venta: ingreso efectivo y ventas
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Ventas del mes {month:02d}/{year}",
            entry_type=EntryType.VENTA,
            lines=[
                JournalLine("10", debit=sales, description="Efectivo por ventas"),
                JournalLine("40", credit=sales, description="Ventas del mes"),
            ],
        )
        entries.append(e)

        # Costo de venta: reduce inventario, aumenta costo
        if cost > 0:
            e2 = JournalEntry(
                entry_number=next_number(),
                date_=month_date,
                description=f"Costo de ventas mes {month:02d}/{year}",
                entry_type=EntryType.VENTA,
                lines=[
                    JournalLine("50", debit=cost, description="Costo de ventas"),
                    JournalLine("12", credit=cost, description="Reducción de inventario"),
                ],
            )
            entries.append(e2)

    # ─── Gastos mensuales ────────────────────────────────
    # Alquiler
    if vars_.monthly_rent > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Alquiler del mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("611", debit=vars_.monthly_rent, description="Alquiler"),
                JournalLine("10", credit=vars_.monthly_rent, description="Pago en efectivo"),
            ],
        )
        entries.append(e)

    # Servicios públicos
    if vars_.monthly_utilities > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Servicios públicos mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("612", debit=vars_.monthly_utilities, description="Luz, agua, internet"),
                JournalLine("10", credit=vars_.monthly_utilities, description="Pago"),
            ],
        )
        entries.append(e)

    # Sueldos
    if vars_.monthly_salaries > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Sueldos mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("601", debit=vars_.monthly_salaries, description="Sueldos"),
                JournalLine("10", credit=vars_.monthly_salaries, description="Pago"),
            ],
        )
        entries.append(e)

    # Marketing
    if vars_.monthly_marketing > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Marketing mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("621", debit=vars_.monthly_marketing, description="Publicidad"),
                JournalLine("10", credit=vars_.monthly_marketing, description="Pago"),
            ],
        )
        entries.append(e)

    # Administrativos
    if vars_.monthly_admin > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Gastos administrativos mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("631", debit=vars_.monthly_admin, description="Administrativos"),
                JournalLine("10", credit=vars_.monthly_admin, description="Pago"),
            ],
        )
        entries.append(e)

    # Mantenimiento
    if vars_.monthly_maintenance > 0:
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Mantenimiento mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("613", debit=vars_.monthly_maintenance, description="Mantenimiento"),
                JournalLine("10", credit=vars_.monthly_maintenance, description="Pago"),
            ],
        )
        entries.append(e)

    # ─── Depreciación ────────────────────────────────────
    depr_entries = _generate_depreciation_entry(
        vars_, month_date, next_number
    )
    entries.extend(depr_entries)

    # ─── Intereses del préstamo ──────────────────────────
    if vars_.loan_amount > 0 and vars_.loan_rate_annual > 0:
        monthly_rate = vars_.loan_rate_annual / 12
        interest = round(vars_.loan_amount * monthly_rate, 2)
        e = JournalEntry(
            entry_number=next_number(),
            date_=month_date,
            description=f"Intereses préstamo mes {month:02d}/{year}",
            entry_type=EntryType.GASTO,
            lines=[
                JournalLine("641", debit=interest, description="Intereses"),
                JournalLine("10", credit=interest, description="Pago"),
            ],
        )
        entries.append(e)

    return entries


def _generate_depreciation_entry(
    vars_: InvestmentVariables, date_: date, next_number_fn
) -> list[JournalEntry]:
    """Genera asientos de depreciación mensual (línea recta)."""
    entries: list[JournalEntry] = []
    months_in_year = 12

    # Equipamiento de cocina
    if vars_.equipment_cost > 0:
        monthly = round(
            vars_.equipment_cost / (vars_.equipment_life_years * months_in_year), 2
        )
        entries.append(
            JournalEntry(
                entry_number=next_number_fn(),
                date_=date_,
                description=f"Depreciación mensual equipamiento cocina",
                entry_type=EntryType.DEPRECIACION,
                lines=[
                    JournalLine("65", debit=monthly, description="Gasto depreciación"),
                    JournalLine("191", credit=monthly, description="Dep acum equipamiento"),
                ],
            )
        )

    # Mobiliario
    if vars_.furniture_cost > 0:
        monthly = round(
            vars_.furniture_cost / (vars_.furniture_life_years * months_in_year), 2
        )
        entries.append(
            JournalEntry(
                entry_number=next_number_fn(),
                date_=date_,
                description="Depreciación mensual mobiliario",
                entry_type=EntryType.DEPRECIACION,
                lines=[
                    JournalLine("65", debit=monthly, description="Gasto depreciación"),
                    JournalLine("192", credit=monthly, description="Dep acum mobiliario"),
                ],
            )
        )

    # Equipos de cómputo
    if vars_.computer_cost > 0:
        monthly = round(
            vars_.computer_cost / (vars_.computer_life_years * months_in_year), 2
        )
        entries.append(
            JournalEntry(
                entry_number=next_number_fn(),
                date_=date_,
                description="Depreciación mensual equipos cómputo",
                entry_type=EntryType.DEPRECIACION,
                lines=[
                    JournalLine("65", debit=monthly, description="Gasto depreciación"),
                    JournalLine("193", credit=monthly, description="Dep acum cómputo"),
                ],
            )
        )

    return entries


def generate_closing_entry(
    all_entries: list[JournalEntry],
    income_tax_rate: float = 0.295,
    closing_date: date | None = None,
) -> JournalEntry:
    """
    Genera asiento de cierre: determina resultado del ejercicio.
    Cierra ingresos y gastos contra la cuenta 32 (Resultado del Ejercicio).
    """
    ledger = build_general_ledger(all_entries)
    bcss = calculate_bcss(ledger)

    # Sumar ingresos (4xx)
    total_income = sum(
        line.balance for line in bcss.lines if line.account_code.startswith("4")
    )
    # Sumar costos y gastos (5xx, 6xx)
    total_costs_expenses = sum(
        line.balance for line in bcss.lines
        if line.account_code.startswith("5") or line.account_code.startswith("6")
    )
    # Depreciación ya está en 65, y contabilizada como débito
    # Pero en BCSS, 19x tiene saldo acreedor (naturaleza A)

    gross_income = round(total_income - total_costs_expenses, 2)

    # Impuesto a la renta
    tax = round(max(0, gross_income) * income_tax_rate, 2)
    net_income = round(gross_income - tax, 2)

    # Fecha de cierre
    close_date = closing_date or date(all_entries[-1].date_.year, 12, 31)

    return JournalEntry(
        entry_number="CIERRE-001",
        date_=close_date,
        description="Cierre del ejercicio — determinación de resultado",
        entry_type=EntryType.CIERRE,
        lines=[
            # Cerrar ingresos contra PyG
            JournalLine("40", debit=total_income, description="Cierre de ingresos"),
            JournalLine("80", credit=total_income, description="Pase a PyG"),
            # Cerrar costos y gastos contra PyG
            JournalLine("80", debit=total_costs_expenses, description="Cierre de costos/gastos"),
            *[
                JournalLine(
                    line.account_code, credit=line.balance
                )
                for line in bcss.lines
                if (line.account_code.startswith("5") or line.account_code.startswith("6"))
                and line.balance > 0
            ],
            # Pasar resultado a 32
            JournalLine("80", debit=net_income + tax, description="Utilidad antes de IR"),
            JournalLine("202", credit=tax, description="IR por pagar"),
            JournalLine("32", credit=net_income, description="Utilidad neta del ejercicio"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# Libro Mayor
# ═══════════════════════════════════════════════════════════════


def build_general_ledger(
    entries: list[JournalEntry],
    accounts: list[AccountDef] | None = None,
) -> dict[str, LedgerAccount]:
    """
    Construye el Libro Mayor desde una lista de asientos.
    Agrupa todas las líneas por cuenta contable.

    Retorna: dict[account_code, LedgerAccount]
    """
    account_map = get_account_map(accounts)
    ledger: dict[str, LedgerAccount] = {}

    for entry in entries:
        for line in entry.lines:
            if line.account_code not in ledger:
                acct = account_map.get(line.account_code)
                ledger[line.account_code] = LedgerAccount(
                    account_code=line.account_code,
                    account_name=acct.name if acct else line.account_code,
                    nature=acct.nature if acct else AccountNature.DEBIT,
                    category=acct.category if acct else AccountCategory.ASSET,
                )
            ledger[line.account_code].entries.append((entry, line))

    return ledger


# ═══════════════════════════════════════════════════════════════
# Balance de Comprobación (BCSS)
# ═══════════════════════════════════════════════════════════════


def calculate_bcss(
    ledger: dict[str, LedgerAccount],
) -> BCSS:
    """
    Calcula el Balance de Comprobación de Sumas y Saldos desde el Libro Mayor.

    Validación: Σ Debe = Σ Haber (partida doble)
    """
    lines: list[BCSSLine] = []

    for account_code, la in sorted(ledger.items()):
        balance = la.balance
        balance_nature = la.balance_nature
        lines.append(
            BCSSLine(
                account_code=account_code,
                account_name=la.account_name,
                total_debit=la.total_debit,
                total_credit=la.total_credit,
                balance=balance,
                balance_nature=balance_nature,
            )
        )

    return BCSS(lines=lines)


def validate_double_entry(entries: list[JournalEntry]) -> list[str]:
    """
    Valida que todos los asientos cumplan partida doble.
    Retorna lista de errores (vacía si todo OK).
    """
    errors: list[str] = []
    total_debits = 0.0
    total_credits = 0.0

    for entry in entries:
        if not entry.is_balanced():
            errors.append(
                f"Asiento {entry.entry_number}: Σ Debe {entry.total_debit} ≠ "
                f"Σ Haber {entry.total_credit} ({entry.description})"
            )
        total_debits += entry.total_debit
        total_credits += entry.total_credit

    if round(total_debits, 2) != round(total_credits, 2):
        errors.append(
            f"TOTAL GLOBAL: Σ Debe {round(total_debits, 2)} ≠ "
            f"Σ Haber {round(total_credits, 2)}"
        )

    return errors


# ═══════════════════════════════════════════════════════════════
# Estados Financieros
# ═══════════════════════════════════════════════════════════════


def generate_income_statement(
    bcss: BCSS,
    period: str = "2026-06",
    income_tax_rate: float = 0.295,
) -> IncomeStatement:
    """
    Genera Estado de Resultados (PYG) desde un BCSS.

    Estructura:
      Ventas - Costo Ventas = Utilidad Bruta
      - Gastos Operativos = EBIT
      - Gastos Financieros = UAI
      - IR = Utilidad Neta
    """
    stmt = IncomeStatement(period=period)

    # Ingresos (cuentas 40x, 41x)
    stmt.revenue = round(
        sum(line.balance for line in bcss.lines if line.account_code.startswith("4")), 2
    )

    # Costo de Ventas (50x)
    stmt.cost_of_sales = round(
        sum(line.balance for line in bcss.lines if line.account_code.startswith("50")), 2
    )

    stmt.gross_profit = round(stmt.revenue - stmt.cost_of_sales, 2)

    # Gastos operativos desglosados
    expense_mapping = {
        "60": "salaries",       # Gastos de Personal
        "61": "operations",     # Alquiler, servicios, mantto
        "62": "marketing",      # Marketing
        "63": "admin",          # Administrativos
        "64": "financial",      # Financieros
        "65": "depreciation",   # Depreciación
        "66": "other",          # Otros gastos
    }

    for code, label in expense_mapping.items():
        amount = round(
            sum(line.balance for line in bcss.lines if line.account_code.startswith(code)),
            2,
        )
        if amount > 0:
            stmt.operating_expenses[label] = amount

    stmt.depreciation = stmt.operating_expenses.pop("depreciation", 0.0)
    stmt.financial_expenses = stmt.operating_expenses.pop("financial", 0.0)

    total_opex = sum(stmt.operating_expenses.values())
    stmt.ebitda = round(stmt.gross_profit - total_opex, 2)
    stmt.ebit = round(stmt.ebitda - stmt.depreciation, 2)
    stmt.income_before_tax = round(stmt.ebit - stmt.financial_expenses, 2)
    stmt.income_tax = round(max(0, stmt.income_before_tax) * income_tax_rate, 2)
    stmt.net_income = round(stmt.income_before_tax - stmt.income_tax, 2)

    return stmt


def generate_balance_sheet(
    bcss: BCSS,
    income_stmt: IncomeStatement,
    as_of: date | None = None,
) -> BalanceSheet:
    """
    Genera Balance General desde un BCSS y PYG.

    Agrega cuentas hijas por prefijo (ej: 131, 132, 133 → 13).
    Activo = Pasivo + Patrimonio
    """
    sheet = BalanceSheet(as_of=as_of or date.today())

    def sum_by_prefix(prefix: str) -> float:
        """Suma balances de todas las líneas cuyo código empieza con prefix."""
        return round(
            sum(line.balance for line in bcss.lines if line.account_code.startswith(prefix)),
            2,
        )

    def max_balance(prefix: str) -> float:
        """Retorna el máximo balance absoluto (para cuentas acreedoras donde el balance es negativo)."""
        vals = [line.balance for line in bcss.lines if line.account_code.startswith(prefix)]
        if not vals:
            return 0.0
        # Para pasivo/patrimonio, el balance en BCSS es positivo pero la naturaleza es acreedora
        # Tomamos el valor absoluto
        total = round(abs(sum(vals)), 2)
        return total

    # ─── Activo Corriente ────────────────────────────
    efect = sum_by_prefix("10")
    if efect != 0:
        sheet.current_assets["Efectivo"] = efect
    cobrar = sum_by_prefix("11")
    if cobrar != 0:
        sheet.current_assets["Ctas por Cobrar"] = cobrar
    invent = sum_by_prefix("12")
    if invent != 0:
        sheet.current_assets["Inventarios"] = invent

    # ─── Activo No Corriente ─────────────────────────
    ime = sum_by_prefix("13")
    if ime != 0:
        sheet.non_current_assets["Inm. Maq. y Equipo"] = ime
    intang = sum_by_prefix("14")
    if intang != 0:
        sheet.non_current_assets["Intangibles"] = intang
    garant = sum_by_prefix("15")
    if garant != 0:
        sheet.non_current_assets["Garantías"] = garant

    # Depreciación acumulada (19x) — naturaleza acreedora
    sheet.accumulated_depreciation = max_balance("19")

    # ─── Pasivo Corriente ────────────────────────────
    # Incluye impuesto a la renta implícito del PYG
    tributos = max_balance("20") + income_stmt.income_tax
    if tributos != 0:
        sheet.current_liabilities["Tributos por pagar"] = tributos
    cxp = max_balance("21")
    if cxp != 0:
        sheet.current_liabilities["Ctas por Pagar Comerciales"] = cxp
    prest_cp = max_balance("221")
    if prest_cp != 0:
        sheet.current_liabilities["Préstamo CP"] = prest_cp
    rem = max_balance("23")
    if rem != 0:
        sheet.current_liabilities["Remuneraciones por Pagar"] = rem
    varias = max_balance("24")
    if varias != 0:
        sheet.current_liabilities["Ctas por Pagar Varias"] = varias

    # ─── Pasivo No Corriente ─────────────────────────
    prest_lp = max_balance("222")
    if prest_lp != 0:
        sheet.non_current_liabilities["Préstamo LP"] = prest_lp

    # ─── Patrimonio ──────────────────────────────────
    sheet.capital = max_balance("30")
    sheet.retained_earnings = max_balance("31")

    # Resultado del ejercicio viene del PYG
    sheet.current_income = income_stmt.net_income

    return sheet
