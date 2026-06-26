"""
📊 Estados Financieros — Servicio de alto nivel.

Basado en:
  - simulador-financiero/docs/04-estados-financieros.md

Orquesta el motor contable y los ratios para producir reportes completos.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.core.accounting.engine import (
    BCSS,
    BalanceSheet,
    IncomeStatement,
    InvestmentVariables,
    JournalEntry,
    build_general_ledger,
    calculate_bcss,
    generate_balance_sheet,
    generate_income_statement,
    generate_monthly_entries,
    generate_opening_entries,
    validate_double_entry,
)
from app.core.accounting.ratios import FinancialRatios, calculate_ratios, evaluate_ratios


# ═══════════════════════════════════════════════════════════════
# Resultado de la Simulación Financiera
# ═══════════════════════════════════════════════════════════════


@dataclass
class FinancialReport:
    """Reporte financiero completo para un período."""

    # Datos de entrada
    variables: InvestmentVariables
    period_start: date
    period_end: date

    # Contabilidad
    journal: list[JournalEntry] = field(default_factory=list)
    bcss: BCSS | None = None

    # Estados Financieros
    income_statement: IncomeStatement | None = None
    balance_sheet: BalanceSheet | None = None

    # Ratios
    ratios: FinancialRatios | None = None

    # Validaciones
    validations: dict[str, bool] = field(default_factory=dict)


class FinancialStatementService:
    """
    Servicio de estados financieros.
    Orquesta el motor contable para producir reportes completos.
    """

    @staticmethod
    def run_simulation(
        vars_: InvestmentVariables,
        months: int = 12,
        start_date: date = date(2026, 1, 1),
        income_tax_rate: float = 0.295,
    ) -> FinancialReport:
        """
        Ejecuta la simulación financiera completa.

        Args:
            vars_: Variables de inversión y operación
            months: Número de meses a proyectar
            start_date: Fecha de inicio
            income_tax_rate: Tasa de impuesto a la renta (default 29.5% Perú)

        Returns:
            FinancialReport con todos los estados financieros y validaciones.
        """
        year = start_date.year

        # 1. Asientos de apertura
        all_entries = generate_opening_entries(vars_, start_date)

        # 2. Asientos operativos mensuales
        for m in range(1, months + 1):
            month_entries = generate_monthly_entries(vars_, m, year, all_entries)
            all_entries.extend(month_entries)

        # 3. Validar partida doble
        errors = validate_double_entry(all_entries)

        # 4. Libro Mayor
        ledger = build_general_ledger(all_entries)

        # 5. BCSS
        bcss = calculate_bcss(ledger)

        # 6. PYG
        period = f"{year}-{months:02d}"
        income_stmt = generate_income_statement(bcss, period, income_tax_rate)

        # 7. Balance General
        end_date = date(year, months, 28)  # fecha aprox de cierre
        balance = generate_balance_sheet(bcss, income_stmt, end_date)

        # 8. Ratios
        # Flujos de caja: ingresos netos mensuales + depreciación
        monthly_flows = [
            vars_.monthly_sales[i] * (1 - vars_.monthly_cost_pct)
            - (vars_.monthly_rent + vars_.monthly_utilities + vars_.monthly_salaries
               + vars_.monthly_marketing + vars_.monthly_admin + vars_.monthly_maintenance)
            for i in range(min(months, len(vars_.monthly_sales)) or 1)
        ]
        initial_investment = (
            vars_.equipment_cost + vars_.furniture_cost + vars_.computer_cost
            + vars_.software_cost + vars_.guarantee_deposit + vars_.initial_inventory
        )

        ratios = calculate_ratios(
            income_stmt,
            balance,
            initial_investment=initial_investment,
            monthly_cashflows=monthly_flows if monthly_flows else None,
        )

        # 9. Validaciones
        validations = {
            "double_entry_ok": len(errors) == 0,
            "bcss_balanced": bcss.is_balanced(),
            "balance_sheet_balanced": balance.is_balanced(),
            "income_coherent": income_stmt.net_income > -999999,
        }

        return FinancialReport(
            variables=vars_,
            period_start=start_date,
            period_end=end_date,
            journal=all_entries,
            bcss=bcss,
            income_statement=income_stmt,
            balance_sheet=balance,
            ratios=ratios,
            validations=validations,
        )
