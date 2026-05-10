"""
Tests para el Motor Contable.

Cubre:
  - Asientos de apertura
  - Libro Mayor
  - BCSS
  - Validación partida doble
  - Estados Financieros
  - Ratios
  - Simulación completa
"""

import pytest
from datetime import date

from app.core.accounting.engine import (
    AccountCategory,
    AccountDef,
    AccountNature,
    BCSSLine,
    EntryType,
    InvestmentVariables,
    JournalEntry,
    JournalLine,
    MovementType,
    build_general_ledger,
    calculate_bcss,
    generate_balance_sheet,
    generate_closing_entry,
    generate_income_statement,
    generate_monthly_entries,
    generate_opening_entries,
    get_account_map,
    validate_double_entry,
)
from app.core.accounting.ratios import (
    FinancialRatios,
    calculate_ratios,
    evaluate_ratios,
    _calculate_payback,
    _calculate_npv,
    _calculate_irr,
)
from app.core.accounting.statements import FinancialStatementService


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_investment() -> InvestmentVariables:
    """Variables típicas para un restaurante pequeño."""
    return InvestmentVariables(
        capital=50000.0,
        loan_amount=30000.0,
        loan_rate_annual=0.12,
        loan_term_months=12,
        equipment_cost=20000.0,
        furniture_cost=5000.0,
        computer_cost=3000.0,
        software_cost=1000.0,
        guarantee_deposit=3000.0,
        initial_inventory=5000.0,
        monthly_sales=[25000.0] * 12,
        monthly_cost_pct=0.40,
        monthly_rent=1500.0,
        monthly_utilities=800.0,
        monthly_salaries=5000.0,
        monthly_marketing=500.0,
        monthly_admin=300.0,
        monthly_maintenance=200.0,
        equipment_life_years=8,
        furniture_life_years=10,
        computer_life_years=5,
        software_life_years=3,
    )


@pytest.fixture
def minimal_vars() -> InvestmentVariables:
    """Variables mínimas para tests unitarios."""
    return InvestmentVariables(
        capital=10000.0,
        equipment_cost=5000.0,
        monthly_sales=[1000.0] * 3,
        monthly_cost_pct=0.40,
        monthly_rent=200.0,
        monthly_salaries=300.0,
    )


# ═══════════════════════════════════════════════════════════════
# Tests: Entidades
# ═══════════════════════════════════════════════════════════════


class TestJournalLine:
    def test_valid_line(self):
        line = JournalLine("10", debit=100.0)
        assert line.debit == 100.0
        assert line.credit == 0.0

    def test_credit_line(self):
        line = JournalLine("30", credit=100.0)
        assert line.debit == 0.0
        assert line.credit == 100.0

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            JournalLine("10", debit=-50)

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            JournalLine("10")

    def test_rejects_both_debit_credit(self):
        with pytest.raises(ValueError):
            JournalLine("10", debit=50, credit=50)


class TestJournalEntry:
    def test_is_balanced(self):
        entry = JournalEntry(
            entry_number="AS-001",
            date_=date(2026, 1, 1),
            description="Aporte",
            lines=[
                JournalLine("10", debit=1000),
                JournalLine("30", credit=1000),
            ],
        )
        assert entry.is_balanced()
        assert entry.total_debit == 1000
        assert entry.total_credit == 1000

    def test_is_not_balanced(self):
        entry = JournalEntry(
            entry_number="AS-001",
            date_=date(2026, 1, 1),
            description="Error",
            lines=[
                JournalLine("10", debit=1000),
                JournalLine("30", credit=500),
            ],
        )
        assert not entry.is_balanced()


class TestLedgerAccount:
    def test_asset_balance(self):
        """Activo: saldo = débitos - créditos."""
        from app.core.accounting.engine import LedgerAccount
        la = LedgerAccount(
            account_code="10",
            account_name="Efectivo",
            nature=AccountNature.DEBIT,
            category=AccountCategory.ASSET,
        )
        # Simular entradas
        e1 = JournalEntry("AS-001", date(2026, 1, 1), "Aporte",
                          lines=[JournalLine("10", debit=1000), JournalLine("30", credit=1000)])
        e2 = JournalEntry("AS-002", date(2026, 1, 1), "Compra",
                          lines=[JournalLine("13", debit=300), JournalLine("10", credit=300)])
        la.entries.append((e1, e1.lines[0]))
        la.entries.append((e2, e2.lines[1]))

        assert la.total_debit == 1000
        assert la.total_credit == 300
        assert la.balance == 700
        assert la.balance_nature == "D"


# ═══════════════════════════════════════════════════════════════
# Tests: Asientos de Apertura
# ═══════════════════════════════════════════════════════════════


class TestOpeningEntries:
    def test_capital_only(self):
        vars_ = InvestmentVariables(capital=50000)
        entries = generate_opening_entries(vars_)
        assert len(entries) == 1
        assert entries[0].description == "Aporte de capital de socios"
        assert entries[0].total_debit == 50000
        assert entries[0].is_balanced()

    def test_full_opening(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        # Capital + Préstamo + Equipos + Muebles + Computadoras + Software + Garantía + Inventario
        assert len(entries) == 8
        for e in entries:
            assert e.is_balanced(), f"Asiento {e.entry_number} no balanceado"

    def test_no_empty_entries(self):
        vars_ = InvestmentVariables(capital=0)
        entries = generate_opening_entries(vars_)
        assert len(entries) == 0

    def test_opening_entries_types(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        types = {e.entry_type for e in entries}
        assert EntryType.APERTURA in types
        assert EntryType.COMPRA in types


# ═══════════════════════════════════════════════════════════════
# Tests: Validación Partida Doble
# ═══════════════════════════════════════════════════════════════


class TestValidation:
    def test_all_balanced(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        errors = validate_double_entry(entries)
        assert len(errors) == 0

    def test_unbalanced_entry(self):
        entry = JournalEntry(
            "AS-001", date(2026, 1, 1), "Error",
            lines=[JournalLine("10", debit=100), JournalLine("30", credit=50)],
        )
        errors = validate_double_entry([entry])
        assert len(errors) == 2  # asiento + total global
        assert "Asiento AS-001" in errors[0]


# ═══════════════════════════════════════════════════════════════
# Tests: Libro Mayor y BCSS
# ═══════════════════════════════════════════════════════════════


class TestLedgerAndBCSS:
    def test_general_ledger(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        ledger = build_general_ledger(entries)
        # Debe haber cuenta Efectivo (10), Capital (30), Préstamo (222), etc.
        assert "10" in ledger
        assert "30" in ledger
        assert ledger["10"].account_name != ""

    def test_bcss_is_balanced(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        assert bcss.is_balanced(), f"BCSS no cuadra: Σ Debe {bcss.total_debits} ≠ Σ Haber {bcss.total_credits}"

    def test_bcss_has_all_accounts(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        # Cuentas que deben aparecer
        codes = {line.account_code for line in bcss.lines}
        assert "10" in codes  # Efectivo
        assert "30" in codes  # Capital
        assert "40" in codes  # Ventas (del monthly)


# ═══════════════════════════════════════════════════════════════
# Tests: Asientos Mensuales
# ═══════════════════════════════════════════════════════════════


class TestMonthlyEntries:
    def test_generates_sales_entry(self, minimal_vars):
        entries = generate_opening_entries(minimal_vars)
        month_entries = generate_monthly_entries(minimal_vars, 1, entries_so_far=entries)

        # Debe haber un asiento de ventas
        sales_entries = [e for e in month_entries if e.entry_type == EntryType.VENTA]
        assert len(sales_entries) >= 1

        # La venta debe estar balanceada
        for e in sales_entries:
            assert e.is_balanced()

    def test_generates_expense_entries(self, minimal_vars):
        entries = generate_opening_entries(minimal_vars)
        month_entries = generate_monthly_entries(minimal_vars, 1, entries_so_far=entries)

        expense_entries = [e for e in month_entries if e.entry_type == EntryType.GASTO]
        assert len(expense_entries) >= 2  # alquiler + sueldos mínimo

    def test_generates_depreciation(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        month_entries = generate_monthly_entries(sample_investment, 1, entries_so_far=entries)

        depr = [e for e in month_entries if e.entry_type == EntryType.DEPRECIACION]
        assert len(depr) >= 2  # equipamiento + mobiliario mín


# ═══════════════════════════════════════════════════════════════
# Tests: Estados Financieros
# ═══════════════════════════════════════════════════════════════


class TestIncomeStatement:
    def test_basic_pyg(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        pyg = generate_income_statement(bcss)

        assert pyg.revenue > 0  # Ventas
        assert pyg.cost_of_sales > 0  # Costo
        assert pyg.gross_profit == round(pyg.revenue - pyg.cost_of_sales, 2)
        assert pyg.gross_profit > 0  # Margen bruto positivo

    def test_income_tax(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        pyg = generate_income_statement(bcss)

        # Con ventas > costos + gastos, debe haber impuesto
        if pyg.income_before_tax > 0:
            assert pyg.income_tax > 0
            assert pyg.income_tax == round(pyg.income_before_tax * 0.295, 2)


class TestBalanceSheet:
    def test_balance_sheet_balanced(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        pyg = generate_income_statement(bcss)
        bs = generate_balance_sheet(bcss, pyg)

        assert bs.is_balanced(), (
            f"Balance no cuadra: Activo={bs.total_assets}, "
            f"Pasivo+Patrimonio={bs.total_liabilities_and_equity}"
        )


# ═══════════════════════════════════════════════════════════════
# Tests: Ratios
# ═══════════════════════════════════════════════════════════════


class TestRatios:
    def test_calculate_ratios(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        pyg = generate_income_statement(bcss)
        bs = generate_balance_sheet(bcss, pyg)

        ratios = calculate_ratios(pyg, bs)
        assert ratios.gross_margin > 0
        assert ratios.net_margin > 0

    def test_evaluate_ratios(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        ledger = build_general_ledger(entries)
        bcss = calculate_bcss(ledger)
        pyg = generate_income_statement(bcss)
        bs = generate_balance_sheet(bcss, pyg)
        ratios = calculate_ratios(pyg, bs)
        evaluated = evaluate_ratios(ratios)
        assert len(evaluated) > 5
        for r in evaluated:
            assert r.traffic_light in ("green", "yellow", "red")

    def test_payback(self):
        assert _calculate_payback(10000, [5000, 5000, 5000]) == 2.0
        assert _calculate_payback(10000, [4000, 4000, 4000]) == 2.5
        assert _calculate_payback(10000, [1000] * 5) == -1.0

    def test_npv(self):
        npv = _calculate_npv(10000, [2000] * 12, 0.12)
        # Con flujo positivo, VAN debe ser > -10000 (al menos algo)
        assert npv > -10000

    def test_irr(self):
        irr = _calculate_irr(10000, [2000] * 12)
        assert irr > 0  # TIR positiva si flujos > inversión


# ═══════════════════════════════════════════════════════════════
# Tests: Simulación Completa
# ═══════════════════════════════════════════════════════════════


class TestFinancialSimulation:
    def test_full_12_month_simulation(self, sample_investment):
        report = FinancialStatementService.run_simulation(
            sample_investment, months=12, start_date=date(2026, 1, 1)
        )

        # Validaciones
        assert report.validations["double_entry_ok"], "Partida doble falló"
        assert report.validations["bcss_balanced"], "BCSS no cuadra"
        assert report.validations["balance_sheet_balanced"], "Balance no cuadra"

        # PYG
        assert report.income_statement is not None
        assert report.income_statement.revenue > 0
        assert report.income_statement.gross_profit > 0

        # Balance
        assert report.balance_sheet is not None
        assert report.balance_sheet.total_assets > 0

        # Ratios
        assert report.ratios is not None

    def test_3_month_minimal(self, minimal_vars):
        report = FinancialStatementService.run_simulation(
            minimal_vars, months=3
        )
        assert report.validations["double_entry_ok"]
        assert report.bcss is not None
        assert report.bcss.is_balanced()

    def test_no_loan_no_equipment(self):
        vars_ = InvestmentVariables(
            capital=10000,
            monthly_sales=[5000] * 6,
            monthly_cost_pct=0.30,
            monthly_rent=500,
            monthly_salaries=1000,
        )
        report = FinancialStatementService.run_simulation(vars_, months=6)
        assert report.validations["double_entry_ok"]
        assert report.income_statement.net_income > -99999  # No debería explotar


# ═══════════════════════════════════════════════════════════════
# Tests: Cierre Contable
# ═══════════════════════════════════════════════════════════════


class TestClosing:
    def test_closing_entry_generated(self, sample_investment):
        entries = generate_opening_entries(sample_investment)
        entries += generate_monthly_entries(sample_investment, 1, entries_so_far=entries)
        closing = generate_closing_entry(entries)
        assert closing.entry_type == EntryType.CIERRE
        assert len(closing.lines) >= 4
