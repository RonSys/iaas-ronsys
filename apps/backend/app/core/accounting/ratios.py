"""
📊 Ratios Financieros — Cálculo puro de indicadores.

Basado en:
  - simulador-financiero/docs/06-ratios.md

Responsabilidad:
  - Liquidez: corriente, prueba ácida, capital de trabajo
  - Rentabilidad: margen bruto, operativo, neto, ROE, ROA
  - Endeudamiento: ratio de deuda, cobertura de intereses
  - Proyecto: Payback, VAN, TIR, punto de equilibrio
"""

from dataclasses import dataclass, field
from typing import Optional

from app.core.accounting.engine import BalanceSheet, IncomeStatement


# ═══════════════════════════════════════════════════════════════
# Semáforo
# ═══════════════════════════════════════════════════════════════


class TrafficLight(str):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class RatioResult:
    name: str
    value: float
    target: str
    traffic_light: str  # green | yellow | red
    formula: str
    interpretation: str = ""


# ═══════════════════════════════════════════════════════════════
# Tablero de Ratios
# ═══════════════════════════════════════════════════════════════


@dataclass
class FinancialRatios:
    """Contenedor de todos los ratios financieros."""

    # Liquidez
    current_ratio: float = 0.0
    quick_ratio: float = 0.0
    working_capital: float = 0.0

    # Rentabilidad
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    roe: float = 0.0
    roa: float = 0.0

    # Endeudamiento
    debt_ratio: float = 0.0
    interest_coverage: float = 0.0
    debt_quality: float = 0.0  # Deuda CP / Deuda Total

    # Eficiencia
    inventory_turnover: float = 0.0
    asset_turnover: float = 0.0

    # Proyecto
    payback_months: float = 0.0
    npv: float = 0.0
    irr: float = 0.0
    break_even_units: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Cálculo de Ratios
# ═══════════════════════════════════════════════════════════════


def calculate_ratios(
    income_stmt: IncomeStatement,
    balance_sheet: BalanceSheet,
    initial_investment: float = 0.0,
    discount_rate: float = 0.12,
    avg_inventory: float | None = None,
    monthly_cashflows: list[float] | None = None,
) -> FinancialRatios:
    """
    Calcula todos los ratios financieros desde PYG + Balance General.

    Args:
        income_stmt: Estado de Resultados
        balance_sheet: Balance General
        initial_investment: Inversión inicial (para Payback, VAN, TIR)
        discount_rate: Tasa de descuento anual (para VAN, default 12%)
        avg_inventory: Inventario promedio para rotación
        monthly_cashflows: Flujos de caja mensuales (para Payback, VAN, TIR)
    """
    r = FinancialRatios()

    total_current_assets = sum(balance_sheet.current_assets.values())
    total_current_liabilities = sum(balance_sheet.current_liabilities.values())
    total_liabilities = balance_sheet.total_liabilities
    total_assets = balance_sheet.total_assets
    total_equity = balance_sheet.total_equity
    revenue = income_stmt.revenue
    gross_profit = income_stmt.gross_profit
    ebit = income_stmt.ebit
    net_income = income_stmt.net_income
    financial_expenses = income_stmt.financial_expenses

    # ─── Liquidez ──────────────────────────────────────
    if total_current_liabilities > 0:
        r.current_ratio = round(total_current_assets / total_current_liabilities, 2)
        inventories = balance_sheet.current_assets.get("Inventarios", 0)
        quick_assets = total_current_assets - inventories
        r.quick_ratio = round(quick_assets / total_current_liabilities, 2)

    r.working_capital = round(total_current_assets - total_current_liabilities, 2)

    # ─── Rentabilidad ──────────────────────────────────
    if revenue > 0:
        r.gross_margin = round(gross_profit / revenue, 4)
        r.operating_margin = round(ebit / revenue, 4)
        r.net_margin = round(net_income / revenue, 4)

    if total_equity > 0:
        r.roe = round(net_income / total_equity, 4)

    if total_assets > 0:
        r.roa = round(net_income / total_assets, 4)

    # ─── Endeudamiento ─────────────────────────────────
    if total_equity > 0:
        r.debt_ratio = round(total_liabilities / total_equity, 2)

    if financial_expenses > 0:
        r.interest_coverage = round(ebit / financial_expenses, 2)

    if total_liabilities > 0:
        r.debt_quality = round(total_current_liabilities / total_liabilities, 2)

    # ─── Eficiencia ────────────────────────────────────
    if avg_inventory and avg_inventory > 0 and income_stmt.cost_of_sales > 0:
        r.inventory_turnover = round(income_stmt.cost_of_sales / avg_inventory, 2)

    if total_assets > 0 and revenue > 0:
        r.asset_turnover = round(revenue / total_assets, 2)

    # ─── Proyecto ──────────────────────────────────────
    if monthly_cashflows and initial_investment > 0:
        r.payback_months = _calculate_payback(initial_investment, monthly_cashflows)
        r.npv = _calculate_npv(initial_investment, monthly_cashflows, discount_rate)
        r.irr = _calculate_irr(initial_investment, monthly_cashflows)

    return r


def evaluate_ratios(ratios: FinancialRatios) -> list[RatioResult]:
    """
    Evalúa cada ratio contra metas del proyecto y asigna semáforo.

    Metas "El Segoviano":
      - Liquidez ≥ 1.5
      - Margen Neto ≥ 12%
      - Endeudamiento ≤ 0.6
      - Payback ≤ 18 meses
    """
    results: list[RatioResult] = []

    def _eval(name: str, value: float, target: str, formula: str,
              good_condition: bool, warn_condition: bool | None = None,
              interpretation: str = "") -> RatioResult:
        if good_condition:
            light = TrafficLight.GREEN
        elif warn_condition is not None and not warn_condition:
            light = TrafficLight.RED
        else:
            light = TrafficLight.YELLOW
        return RatioResult(
            name=name, value=value, target=target,
            traffic_light=light, formula=formula, interpretation=interpretation,
        )

    # Liquidez
    results.append(_eval(
        "Liquidez Corriente", ratios.current_ratio, "≥ 1.5",
        "Activo Cte / Pasivo Cte",
        ratios.current_ratio >= 1.5,
        ratios.current_ratio >= 1.0,
    ))
    results.append(_eval(
        "Prueba Ácida", ratios.quick_ratio, "≥ 1.0",
        "(Activo Cte - Inventario) / Pasivo Cte",
        ratios.quick_ratio >= 1.0,
        ratios.quick_ratio >= 0.7,
    ))
    results.append(_eval(
        "Capital de Trabajo", ratios.working_capital, "> 0",
        "Activo Cte - Pasivo Cte",
        ratios.working_capital > 0,
    ))

    # Rentabilidad
    results.append(_eval(
        "Margen Bruto", round(ratios.gross_margin * 100, 1), "≥ 50%",
        "Utilidad Bruta / Ventas",
        ratios.gross_margin >= 0.50,
        ratios.gross_margin >= 0.35,
    ))
    results.append(_eval(
        "Margen Neto", round(ratios.net_margin * 100, 1), "≥ 12%",
        "Utilidad Neta / Ventas",
        ratios.net_margin >= 0.12,
        ratios.net_margin >= 0.08,
    ))
    results.append(_eval(
        "ROE", round(ratios.roe * 100, 1), "≥ 15%",
        "Utilidad Neta / Patrimonio",
        ratios.roe >= 0.15,
        ratios.roe >= 0.05,
    ))
    results.append(_eval(
        "ROA", round(ratios.roa * 100, 1), "≥ 8%",
        "Utilidad Neta / Activo Total",
        ratios.roa >= 0.08,
        ratios.roa >= 0.02,
    ))

    # Endeudamiento
    results.append(_eval(
        "Endeudamiento", ratios.debt_ratio, "≤ 0.6",
        "Pasivo Total / Patrimonio",
        ratios.debt_ratio <= 0.6,
        ratios.debt_ratio <= 1.0,
    ))
    results.append(_eval(
        "Cobertura de Intereses", ratios.interest_coverage, "≥ 3.0",
        "EBIT / Gastos Financieros",
        ratios.interest_coverage >= 3.0,
        ratios.interest_coverage >= 1.5,
    ))

    # Proyecto
    results.append(_eval(
        "Payback", ratios.payback_months, "≤ 18 meses",
        "Inv. Inicial / Flujo Mensual",
        ratios.payback_months <= 18,
        ratios.payback_months <= 24,
    ))
    results.append(_eval(
        "VAN", round(ratios.npv, 2), "> 0",
        "Σ(Flujo/(1+r)^t) - Inv",
        ratios.npv > 0,
    ))
    results.append(_eval(
        "TIR", round(ratios.irr * 100, 1), "> 12%",
        "Tasa que hace VAN=0",
        ratios.irr > 0.12,
        ratios.irr > 0.08,
    ))

    return results


# ═══════════════════════════════════════════════════════════════
# Métricas de Proyecto
# ═══════════════════════════════════════════════════════════════


def _calculate_payback(investment: float, cashflows: list[float]) -> float:
    """
    Payback en meses.
    Retorna el número de meses para recuperar la inversión.
    """
    if investment <= 0:
        return 0.0

    cumulative = 0.0
    for i, cf in enumerate(cashflows):
        cumulative += cf
        if cumulative >= investment:
            # Interpolar entre meses
            prev = cumulative - cf
            fraction = (investment - prev) / cf if cf > 0 else 0
            return round(i + fraction, 1)

    return -1.0  # No se recupera


def _calculate_npv(
    investment: float,
    cashflows: list[float],
    annual_discount_rate: float = 0.12,
) -> float:
    """
    VAN (Valor Actual Neto).
    VAN = Σ(Flujo_t / (1+r)^t) - Inversión Inicial
    """
    monthly_rate = annual_discount_rate / 12
    npv = -investment

    for i, cf in enumerate(cashflows):
        npv += cf / ((1 + monthly_rate) ** (i + 1))

    return round(npv, 2)


def _calculate_irr(
    investment: float,
    cashflows: list[float],
    max_iterations: int = 200,
) -> float:
    """
    TIR (Tasa Interna de Retorno) mensual → anualizada.
    Método de Newton-Raphson simplificado con guardas de overflow.
    """
    if investment <= 0 or not cashflows:
        return 0.0

    # Si todos los flujos son negativos o la suma es menor que inversión, no hay TIR real
    total_flows = sum(cashflows)
    if total_flows <= 0:
        return -0.99

    # TIR mensual estimada
    rate = 0.03  # 3% inicial más conservador
    flows = [-investment] + cashflows

    for _ in range(max_iterations):
        npv = 0.0
        dnpv = 0.0

        for t, cf in enumerate(flows):
            divisor = (1.0 + rate) ** t
            if divisor > 1e15:  # Guarda contra overflow
                rate = max(-0.5, rate - 0.1)
                break
            npv += cf / divisor
            if t > 0:
                divisor2 = (1.0 + rate) ** (t + 1)
                if divisor2 > 1e15:
                    dnpv = -1e-6
                    break
                dnpv -= t * cf / divisor2

        if abs(npv) < 1e-6:
            break

        if dnpv != 0 and abs(npv / dnpv) < 2.0:
            rate -= npv / dnpv
        elif dnpv != 0:
            # Paso grande → reducir
            rate -= 0.5 * npv / dnpv
        else:
            break

        # Clamp rate mensual a rango razonable (-50% a +200%)
        rate = max(-0.5, min(rate, 2.0))

    # Anualizar
    annual_irr = round(((1.0 + max(-0.5, rate)) ** 12) - 1.0, 4)

    # Clamp a rango razonable
    return max(-0.99, min(annual_irr, 9.99))
