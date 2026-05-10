"""
Endpoints de Contabilidad — FastAPI Router.

Endpoints:
  POST /api/accounting/setup        → Configurar empresa + simulación inicial
  GET  /api/accounting/bcss         → Balance de Comprobación
  GET  /api/accounting/pyg          → Estado de Resultados
  GET  /api/accounting/balance      → Balance General
  GET  /api/accounting/ratios       → Ratios financieros
  POST /api/accounting/transaction  → Registrar transacción manual

  POST /api/accounting/kardex/products → Registrar producto
  POST /api/accounting/kardex/entry    → Entrada de inventario
  POST /api/accounting/kardex/exit     → Salida de inventario
  GET  /api/accounting/kardex/{code}   → Kárdex de un producto
  GET  /api/accounting/kardex/inventory → Resumen inventario
  POST /api/accounting/kardex/warehouse-close → Cierre de almacén
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.accounting import (
    FinancialStatementService,
    InvestmentVariables,
    KardexEngine,
    KardexProduct,
    calculate_bcss,
    calculate_ratios,
    build_general_ledger,
    evaluate_ratios,
    generate_balance_sheet,
    generate_income_statement,
    generate_monthly_entries,
    generate_opening_entries,
    validate_double_entry,
)
from app.schemas import (
    BCSSAccountResponse,
    BCSSResponse,
    BalanceSheetResponse,
    FinancialReportResponse,
    IncomeStatementResponse,
    InvestmentInput,
    KardexEntryInput,
    KardexExitInput,
    KardexMovementInput,
    KardexProductResponse,
    KardexRecordResponse,
    ProductInput,
    RatioItemResponse,
    TransactionInput,
    TransactionLine,
    ValidationResponse,
    WarehouseCloseResponse,
)

router = APIRouter(prefix="/api/accounting", tags=["Contabilidad"])

from app.core.dependencies import get_current_active_user  # noqa: E402
from app.core.tenant import get_tenant_id  # noqa: E402
from app.models.user import User  # noqa: E402

# ─── Estado en memoria (temporal, hasta implementar repositorio) ───
_investment: InvestmentVariables | None = None
_journal: list = []
_kardex_engine: KardexEngine = KardexEngine()


# ═══════════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════════


@router.post("/setup", response_model=FinancialReportResponse)
async def setup_accounting(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: InvestmentInput):
    """
    Configura la empresa y ejecuta la simulación financiera inicial.

    Recibe variables de inversión y devuelve el reporte financiero completo:
    BCSS, PYG, Balance General y Ratios.
    """
    global _investment, _journal

    start = data.start_date or date(2026, 1, 1)

    vars_ = InvestmentVariables(
        capital=data.capital,
        loan_amount=data.loan_amount,
        loan_rate_annual=data.loan_rate_annual,
        loan_term_months=data.loan_term_months,
        equipment_cost=data.equipment_cost,
        furniture_cost=data.furniture_cost,
        computer_cost=data.computer_cost,
        software_cost=data.software_cost,
        guarantee_deposit=data.guarantee_deposit,
        initial_inventory=data.initial_inventory,
        monthly_sales=data.monthly_sales,
        monthly_cost_pct=data.monthly_cost_pct,
        monthly_rent=data.monthly_rent,
        monthly_utilities=data.monthly_utilities,
        monthly_salaries=data.monthly_salaries,
        monthly_marketing=data.monthly_marketing,
        monthly_admin=data.monthly_admin,
        monthly_maintenance=data.monthly_maintenance,
        equipment_life_years=data.equipment_life_years,
        furniture_life_years=data.furniture_life_years,
        computer_life_years=data.computer_life_years,
        software_life_years=data.software_life_years,
    )

    _investment = vars_

    report = FinancialStatementService.run_simulation(
        vars_, months=data.months, start_date=start
    )
    _journal = report.journal

    # Construir respuesta
    is_income = report.income_statement
    bs = report.balance_sheet

    income_resp = None
    if is_income:
        income_resp = IncomeStatementResponse(
            period=is_income.period,
            revenue=is_income.revenue,
            cost_of_sales=is_income.cost_of_sales,
            gross_profit=is_income.gross_profit,
            gross_margin_pct=round(
                is_income.gross_profit / is_income.revenue * 100, 1
            ) if is_income.revenue else 0,
            operating_expenses=is_income.operating_expenses,
            depreciation=is_income.depreciation,
            financial_expenses=is_income.financial_expenses,
            ebitda=is_income.ebitda,
            ebit=is_income.ebit,
            operating_margin_pct=round(
                is_income.ebit / is_income.revenue * 100, 1
            ) if is_income.revenue else 0,
            income_before_tax=is_income.income_before_tax,
            income_tax=is_income.income_tax,
            net_income=is_income.net_income,
            net_margin_pct=round(
                is_income.net_income / is_income.revenue * 100, 1
            ) if is_income.revenue else 0,
        )

    balance_resp = None
    if bs:
        balance_resp = BalanceSheetResponse(
            as_of=bs.as_of,
            current_assets=bs.current_assets,
            non_current_assets=bs.non_current_assets,
            accumulated_depreciation=bs.accumulated_depreciation,
            total_assets=bs.total_assets,
            current_liabilities=bs.current_liabilities,
            non_current_liabilities=bs.non_current_liabilities,
            total_liabilities=bs.total_liabilities,
            capital=bs.capital,
            retained_earnings=bs.retained_earnings,
            current_income=bs.current_income,
            total_equity=bs.total_equity,
            total_liabilities_and_equity=bs.total_liabilities_and_equity,
            is_balanced=bs.is_balanced(),
        )

    bcss_resp = None
    if report.bcss:
        bcss_resp = BCSSResponse(
            lines=[
                BCSSAccountResponse(
                    account_code=line.account_code,
                    account_name=line.account_name,
                    total_debit=line.total_debit,
                    total_credit=line.total_credit,
                    balance=line.balance,
                    balance_nature=line.balance_nature,
                )
                for line in report.bcss.lines
            ],
            total_debits=report.bcss.total_debits,
            total_credits=report.bcss.total_credits,
            is_balanced=report.bcss.is_balanced(),
        )

    ratios_list = None
    if report.ratios:
        ratios_list = [
            RatioItemResponse(
                name=r.name, value=r.value, target=r.target,
                traffic_light=r.traffic_light, formula=r.formula,
            )
            for r in evaluate_ratios(report.ratios)
        ]

    return FinancialReportResponse(
        period_start=report.period_start,
        period_end=report.period_end,
        total_entries=len(report.journal),
        bcss=bcss_resp,
        income_statement=income_resp,
        balance_sheet=balance_resp,
        ratios=ratios_list,
        validations=report.validations,
    )


# ═══════════════════════════════════════════════════════════════
# Consultas Contables
# ═══════════════════════════════════════════════════════════════


@router.get("/bcss", response_model=BCSSResponse)
async def get_bcss(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Balance de Comprobación de Sumas y Saldos."""
    if not _journal:
        raise HTTPException(404, "No hay asientos. Ejecuta /api/accounting/setup primero.")

    ledger = build_general_ledger(_journal)
    bcss = calculate_bcss(ledger)

    return BCSSResponse(
        lines=[
            BCSSAccountResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                total_debit=line.total_debit,
                total_credit=line.total_credit,
                balance=line.balance,
                balance_nature=line.balance_nature,
            )
            for line in bcss.lines
        ],
        total_debits=bcss.total_debits,
        total_credits=bcss.total_credits,
        is_balanced=bcss.is_balanced(),
    )


@router.get("/pyg", response_model=IncomeStatementResponse)
async def get_pyg(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Estado de Resultados (Pérdidas y Ganancias)."""
    if not _journal:
        raise HTTPException(404, "No hay asientos. Ejecuta /api/accounting/setup primero.")

    ledger = build_general_ledger(_journal)
    bcss = calculate_bcss(ledger)
    is_income = generate_income_statement(bcss)

    return IncomeStatementResponse(
        period=is_income.period,
        revenue=is_income.revenue,
        cost_of_sales=is_income.cost_of_sales,
        gross_profit=is_income.gross_profit,
        gross_margin_pct=round(
            is_income.gross_profit / is_income.revenue * 100, 1
        ) if is_income.revenue else 0,
        operating_expenses=is_income.operating_expenses,
        depreciation=is_income.depreciation,
        financial_expenses=is_income.financial_expenses,
        ebitda=is_income.ebitda,
        ebit=is_income.ebit,
        operating_margin_pct=round(
            is_income.ebit / is_income.revenue * 100, 1
        ) if is_income.revenue else 0,
        income_before_tax=is_income.income_before_tax,
        income_tax=is_income.income_tax,
        net_income=is_income.net_income,
        net_margin_pct=round(
            is_income.net_income / is_income.revenue * 100, 1
        ) if is_income.revenue else 0,
    )


@router.get("/balance", response_model=BalanceSheetResponse)
async def get_balance(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Balance General."""
    if not _journal:
        raise HTTPException(404, "No hay asientos. Ejecuta /api/accounting/setup primero.")

    ledger = build_general_ledger(_journal)
    bcss = calculate_bcss(ledger)
    is_income = generate_income_statement(bcss)
    bs = generate_balance_sheet(bcss, is_income)

    return BalanceSheetResponse(
        as_of=bs.as_of,
        current_assets=bs.current_assets,
        non_current_assets=bs.non_current_assets,
        accumulated_depreciation=bs.accumulated_depreciation,
        total_assets=bs.total_assets,
        current_liabilities=bs.current_liabilities,
        non_current_liabilities=bs.non_current_liabilities,
        total_liabilities=bs.total_liabilities,
        capital=bs.capital,
        retained_earnings=bs.retained_earnings,
        current_income=bs.current_income,
        total_equity=bs.total_equity,
        total_liabilities_and_equity=bs.total_liabilities_and_equity,
        is_balanced=bs.is_balanced(),
    )


@router.get("/ratios", response_model=list[RatioItemResponse])
async def get_ratios(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Ratios financieros con semáforo."""
    if not _journal:
        raise HTTPException(404, "No hay asientos. Ejecuta /api/accounting/setup primero.")

    ledger = build_general_ledger(_journal)
    bcss = calculate_bcss(ledger)
    is_income = generate_income_statement(bcss)
    bs = generate_balance_sheet(bcss, is_income)

    ratios = calculate_ratios(is_income, bs)
    evaluated = evaluate_ratios(ratios)

    return [
        RatioItemResponse(
            name=r.name, value=r.value, target=r.target,
            traffic_light=r.traffic_light, formula=r.formula,
        )
        for r in evaluated
    ]


# ═══════════════════════════════════════════════════════════════
# Transacciones Manuales
# ═══════════════════════════════════════════════════════════════


@router.post("/transaction")
async def post_transaction(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: TransactionInput):
    """Registra una transacción contable manual."""
    from app.core.accounting import JournalEntry, JournalLine

    entry = JournalEntry(
        entry_number=f"MAN-{len(_journal) + 1:03d}",
        date_=data.date,
        description=data.description,
        entry_type=data.entry_type,
        reference=data.reference,
        lines=[
            JournalLine(
                account_code=line.account_code,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in data.lines
        ],
    )

    if not entry.is_balanced():
        raise HTTPException(
            422,
            f"Asiento no balanceado: Debe {entry.total_debit} ≠ Haber {entry.total_credit}",
        )

    _journal.append(entry)
    return {"status": "ok", "entry_number": entry.entry_number}


@router.post("/validate", response_model=ValidationResponse)
async def validate_accounting(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Valida la consistencia contable (partida doble)."""
    if not _journal:
        return ValidationResponse(valid=True, errors=[])

    errors = validate_double_entry(_journal)
    return ValidationResponse(valid=len(errors) == 0, errors=errors)


# ═══════════════════════════════════════════════════════════════
# Kárdex
# ═══════════════════════════════════════════════════════════════

kardex_router = APIRouter(prefix="/api/accounting/kardex", tags=["Kárdex"])


@kardex_router.post("/products", response_model=KardexProductResponse)
async def register_product(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: ProductInput):
    """Registra un nuevo producto en el inventario."""
    try:
        p = _kardex_engine.register_product(
            code=data.code,
            name=data.name,
            unit=data.unit,
            initial_stock=data.initial_stock,
            initial_cost=data.initial_cost,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))

    return KardexProductResponse(
        code=p.code,
        name=p.name,
        unit=p.unit_of_measure,
        current_stock=p.current_stock,
        average_cost=p.average_cost,
        total_value=p.total_value,
    )


@kardex_router.post("/entry", response_model=KardexRecordResponse)
async def kardex_entry(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: KardexEntryInput):
    """Registra una entrada de inventario (compra). Genera asiento contable."""
    try:
        record, entry = _kardex_engine.record_entry(
            product_code=data.product_code,
            quantity=data.quantity,
            unit_cost=data.unit_cost,
            concept=data.concept,
            movement_date=data.date,
            reference_type=data.reference_type,
        )
        if entry:
            _journal.append(entry)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))

    return KardexRecordResponse(
        product_code=record.product_code,
        movement_type=record.movement_type.value,
        concept=record.concept,
        quantity=record.quantity,
        unit_cost=record.unit_cost,
        total=record.total,
        balance_quantity=record.balance_quantity,
        balance_avg_cost=record.balance_avg_cost,
        balance_total=record.balance_total,
        date=record.date_,
    )


@kardex_router.post("/exit", response_model=KardexRecordResponse)
async def kardex_exit(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: KardexExitInput):
    """Registra una salida de inventario (venta/merma). Genera asiento contable."""
    try:
        record, entry = _kardex_engine.record_exit(
            product_code=data.product_code,
            quantity=data.quantity,
            concept=data.concept,
            movement_date=data.date,
            reference_type=data.reference_type,
        )
        if entry:
            _journal.append(entry)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))

    return KardexRecordResponse(
        product_code=record.product_code,
        movement_type=record.movement_type.value,
        concept=record.concept,
        quantity=record.quantity,
        unit_cost=record.unit_cost,
        total=record.total,
        balance_quantity=record.balance_quantity,
        balance_avg_cost=record.balance_avg_cost,
        balance_total=record.balance_total,
        date=record.date_,
    )


@kardex_router.get("/{product_code}", response_model=list[KardexRecordResponse])
async def get_kardex(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], product_code: str):
    """Kárdex completo de un producto (historial de movimientos)."""
    try:
        _kardex_engine.get_product(product_code)
    except KeyError:
        raise HTTPException(404, f"Producto {product_code} no encontrado")

    records = _kardex_engine.get_kardex(product_code)
    return [
        KardexRecordResponse(
            product_code=r.product_code,
            movement_type=r.movement_type.value,
            concept=r.concept,
            quantity=r.quantity,
            unit_cost=r.unit_cost,
            total=r.total,
            balance_quantity=r.balance_quantity,
            balance_avg_cost=r.balance_avg_cost,
            balance_total=r.balance_total,
            date=r.date_,
        )
        for r in records
    ]


@kardex_router.get("/inventory/summary", response_model=list[KardexProductResponse])
async def get_inventory_summary(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Resumen del inventario actual (todos los productos activos)."""
    return [
        KardexProductResponse(
            code=p.code,
            name=p.name,
            unit=p.unit_of_measure,
            current_stock=p.current_stock,
            average_cost=p.average_cost,
            total_value=p.total_value,
        )
        for p in _kardex_engine.products.values()
        if p.active
    ]


@kardex_router.post("/warehouse-close", response_model=WarehouseCloseResponse)
async def close_warehouse(
    accounting_balance: float = Query(..., ge=0, description="Saldo de Cuenta 12"),
):
    """
    Cierre de almacén: verifica que Σ Kárdex = Cuenta 12 (contable).
    """
    result = _kardex_engine.warehouse_close(accounting_balance)
    return WarehouseCloseResponse(**result)
