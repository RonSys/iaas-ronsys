#!/usr/bin/env python3
"""
Script de Demostración — Motor Contable.

Ejecuta una simulación financiera completa con datos de ejemplo
y muestra los resultados en consola. No requiere base de datos.

Uso:
  cd apps/backend
  python3 scripts/seed.py
"""

from datetime import date

from app.core.accounting import (
    FinancialStatementService,
    InvestmentVariables,
    evaluate_ratios,
)


def main():
    print("=" * 70)
    print("  🧠 IaaS-RonSys — Motor Contable Demo")
    print("  Datos: Restaurante \"El Segoviano\" — Simulación 12 meses")
    print("=" * 70)

    # ─── Variables de Inversión ─────────────────────────
    vars_ = InvestmentVariables(
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

    # ─── Ejecutar Simulación ────────────────────────────
    report = FinancialStatementService.run_simulation(
        vars_, months=12, start_date=date(2026, 1, 1)
    )

    # ─── Mostrar Resultados ─────────────────────────────
    print(f"\n📊 Período: {report.period_start} → {report.period_end}")
    print(f"   Total Asientos: {len(report.journal)}")

    # Validaciones
    print("\n🔍 Validaciones:")
    for k, v in report.validations.items():
        icon = "✅" if v else "❌"
        print(f"   {icon} {k}")

    # BCSS
    if report.bcss:
        print(f"\n📋 Balance de Comprobación:")
        print(f"   Σ Debe:  S/ {report.bcss.total_debits:,.2f}")
        print(f"   Σ Haber: S/ {report.bcss.total_credits:,.2f}")
        print(f"   Cuadra:  {'✅' if report.bcss.is_balanced() else '❌'}")

    # PYG
    if report.income_statement:
        pyg = report.income_statement
        gm_pct = round(pyg.gross_profit / pyg.revenue * 100, 1) if pyg.revenue else 0
        om_pct = round(pyg.ebit / pyg.revenue * 100, 1) if pyg.revenue else 0
        nm_pct = round(pyg.net_income / pyg.revenue * 100, 1) if pyg.revenue else 0
        print(f"\n📊 Estado de Resultados (PYG) — {pyg.period}")
        print(f"   Ventas:            S/ {pyg.revenue:>12,.2f}")
        print(f"   Costo de Ventas:   S/ {pyg.cost_of_sales:>12,.2f}")
        print(f"   ─────────────────────────────────")
        print(f"   Utilidad Bruta:    S/ {pyg.gross_profit:>12,.2f}  ({gm_pct:.1f}%)")
        total_opex = sum(pyg.operating_expenses.values())
        print(f"   Gastos Operativos: S/ {total_opex:>12,.2f}")
        print(f"   Depreciación:      S/ {pyg.depreciation:>12,.2f}")
        print(f"   ─────────────────────────────────")
        print(f"   EBIT:              S/ {pyg.ebit:>12,.2f}")
        print(f"   Gastos Financieros:S/ {pyg.financial_expenses:>12,.2f}")
        print(f"   ─────────────────────────────────")
        print(f"   UAI:               S/ {pyg.income_before_tax:>12,.2f}")
        print(f"   Impuesto Renta:    S/ {pyg.income_tax:>12,.2f}")
        print(f"   ─────────────────────────────────")
        print(f"   Utilidad Neta:     S/ {pyg.net_income:>12,.2f}  ({nm_pct:.1f}%)")

    # Balance General
    if report.balance_sheet:
        bs = report.balance_sheet
        print(f"\n📊 Balance General — {bs.as_of}")
        print(f"   ACTIVO:")
        print(f"     Corriente:       S/ {sum(bs.current_assets.values()):>12,.2f}")
        print(f"     No Corriente:    S/ {sum(bs.non_current_assets.values()):>12,.2f}")
        print(f"     (-) Dep. Acum.:  S/ {bs.accumulated_depreciation:>12,.2f}")
        print(f"   TOTAL ACTIVO:      S/ {bs.total_assets:>12,.2f}")
        print(f"   PASIVO:            S/ {bs.total_liabilities:>12,.2f}")
        print(f"   PATRIMONIO:        S/ {bs.total_equity:>12,.2f}")
        print(f"   P + P:             S/ {bs.total_liabilities_and_equity:>12,.2f}")
        print(f"   Cuadra:            {'✅' if bs.is_balanced() else '❌'}")

    # Ratios
    if report.ratios:
        print(f"\n📊 Ratios Financieros:")
        for r in evaluate_ratios(report.ratios):
            light = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[r.traffic_light]
            print(f"   {light} {r.name:<25} {r.value:>8.2f}  (meta: {r.target})")

    print("\n" + "=" * 70)
    print("  ✅ Simulación completada exitosamente")
    print("=" * 70)


if __name__ == "__main__":
    main()
