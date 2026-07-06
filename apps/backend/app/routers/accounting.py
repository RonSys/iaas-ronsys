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
from sqlalchemy import or_, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.accounting import (
    CashflowReport,
    CashflowService,
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
async def get_kardex(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    product_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Kárdex completo de un producto (historial de movimientos).

    Busca primero en el motor in-memory (restaurant). Si no existe,
    consulta la tabla products + kardex_movements en BD (ferretería).
    """
    from app.adapters.db.models.accounting import Product as ProductModel, KardexMovement

    try:
        _kardex_engine.get_product(product_code)
        # Existe en simulador → usar motor in-memory (restaurant)
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
    except KeyError:
        pass  # No encontrado en simulador, buscar en DB

    # Buscar en BD (ferretería u otros business_type con productos reales)
    conditions = [
        ProductModel.tenant_id == tenant_id,
        ProductModel.active == True,
    ]
    if product_code.isdigit():
        conditions.append(
            or_(ProductModel.code == product_code, ProductModel.id == int(product_code))
        )
    else:
        conditions.append(ProductModel.code == product_code)

    result = await db.execute(sa_select(ProductModel).where(*conditions))
    product_db = result.scalar_one_or_none()

    if not product_db:
        raise HTTPException(404, f"Producto {product_code} no encontrado")

    # Obtener movimientos ordenados cronológicamente
    move_result = await db.execute(
        sa_select(KardexMovement)
        .where(KardexMovement.product_id == product_db.id)
        .order_by(KardexMovement.date.asc(), KardexMovement.id.asc())
    )
    movements = move_result.scalars().all()

    return [
        KardexRecordResponse(
            product_code=product_code,
            movement_type=m.movement_type,
            concept=m.concept,
            quantity=float(m.quantity),
            unit_cost=float(m.unit_cost),
            total=float(m.total),
            balance_quantity=float(m.balance_quantity),
            balance_avg_cost=float(m.balance_avg_cost),
            balance_total=float(m.balance_total),
            date=m.date,
        )
        for m in movements
    ]


@kardex_router.get("/inventory/summary", response_model=list[KardexProductResponse])
async def get_inventory_summary(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resumen del inventario actual (todos los productos activos).

    Combina productos del motor in-memory (restaurant) con productos de
    la tabla products en BD (ferretería). Los productos del simulador
    tienen prioridad para evitar duplicados.
    """
    from app.adapters.db.models.accounting import Product as ProductModel

    # Productos del simulador (restaurant) — tienen prioridad sobre DB
    simulator_codes: set[str] = {
        p.code for p in _kardex_engine.products.values() if p.active
    }

    result: list[KardexProductResponse] = [
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

    # Agregar productos DB que NO estén duplicados en el simulador
    db_result = await db.execute(
        sa_select(ProductModel).where(
            ProductModel.tenant_id == tenant_id,
            ProductModel.active == True,
        )
    )
    db_products = db_result.scalars().all()

    for p_db in db_products:
        code = p_db.code or str(p_db.id)
        if code not in simulator_codes:
            result.append(
                KardexProductResponse(
                    code=code,
                    name=p_db.name,
                    unit=p_db.unit_of_measure,
                    current_stock=float(p_db.current_stock),
                    average_cost=float(p_db.average_cost),
                    total_value=round(
                        float(p_db.current_stock) * float(p_db.average_cost), 2
                    ),
                )
            )

    return result


@kardex_router.post("/warehouse-close", response_model=WarehouseCloseResponse)
async def close_warehouse(
    accounting_balance: float = Query(..., ge=0, description="Saldo de Cuenta 12"),
):
    """
    Cierre de almacén: verifica que Σ Kárdex = Cuenta 12 (contable).
    """
    result = _kardex_engine.warehouse_close(accounting_balance)
    return WarehouseCloseResponse(**result)


# ═══════════════════════════════════════════════════════════════
# Kárdex DB-backed (HU-F2-012) — persistencia real en PostgreSQL
# ═══════════════════════════════════════════════════════════════

from app.services.kardex_service import KardexDBService, get_kardex_service  # noqa: E402


@kardex_router.post("/db/products", response_model=KardexProductResponse)
async def register_product_db(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
    data: ProductInput,
):
    """HU-F2-012: Registra producto en DB (persistente)."""
    try:
        p = await kardex.register_product(
            code=data.code, name=data.name, unit=data.unit,
            initial_stock=data.initial_stock, initial_cost=data.initial_cost,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))

    return KardexProductResponse(
        code=p.code, name=p.name, unit=p.unit_of_measure,
        current_stock=p.current_stock, average_cost=p.average_cost,
        total_value=round(p.current_stock * p.average_cost, 2),
    )


@kardex_router.post("/db/entry", response_model=KardexRecordResponse)
async def kardex_entry_db(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
    data: KardexEntryInput,
):
    """HU-F2-012: Registra entrada de inventario en DB."""
    try:
        record = await kardex.record_entry(
            product_code=data.product_code, quantity=data.quantity,
            unit_cost=data.unit_cost, concept=data.concept,
            movement_date=data.date, reference_type=data.reference_type,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))

    return KardexRecordResponse(
        product_code="",  # Se infiere del product_id
        movement_type=record.movement_type,
        concept=record.concept,
        quantity=record.quantity,
        unit_cost=record.unit_cost,
        total=record.total,
        balance_quantity=record.balance_quantity,
        balance_avg_cost=record.balance_avg_cost,
        balance_total=record.balance_total,
        date=record.date_,
    )


@kardex_router.post("/db/exit", response_model=KardexRecordResponse)
async def kardex_exit_db(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
    data: KardexExitInput,
):
    """HU-F2-012: Registra salida de inventario en DB."""
    try:
        record = await kardex.record_exit(
            product_code=data.product_code, quantity=data.quantity,
            concept=data.concept, movement_date=data.date,
            reference_type=data.reference_type,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))

    return KardexRecordResponse(
        product_code="",
        movement_type=record.movement_type,
        concept=record.concept,
        quantity=record.quantity,
        unit_cost=record.unit_cost,
        total=record.total,
        balance_quantity=record.balance_quantity,
        balance_avg_cost=record.balance_avg_cost,
        balance_total=record.balance_total,
        date=record.date_,
    )


@kardex_router.get("/db/inventory", response_model=list[KardexProductResponse])
async def get_inventory_summary_db(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
):
    """HU-F2-012: Resumen inventario desde DB."""
    summary = await kardex.get_inventory_summary()
    return [KardexProductResponse(**item) for item in summary]


@kardex_router.get("/db/{product_code}", response_model=list[KardexRecordResponse])
async def get_kardex_db(
    product_code: str,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
):
    """HU-F2-012: Historial kárdex desde DB."""
    try:
        records = await kardex.get_kardex(product_code)
    except KeyError:
        raise HTTPException(404, f"Producto {product_code} no encontrado")

    return [
        KardexRecordResponse(
            product_code=product_code,
            movement_type=r.movement_type,
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


@kardex_router.post("/db/warehouse-close", response_model=WarehouseCloseResponse)
async def close_warehouse_db(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    kardex: Annotated[KardexDBService, Depends(get_kardex_service)],
    accounting_balance: float = Query(..., ge=0, description="Saldo de Cuenta 12"),
):
    """HU-F2-012: Cierre de almacén desde DB."""
    result = await kardex.warehouse_close(accounting_balance)
    return WarehouseCloseResponse(**result)


# ═══════════════════════════════════════════════════════════════
# Flujo de Caja (HU-F1-004, F1-005, F1-006)
# ═══════════════════════════════════════════════════════════════


@router.get("/cashflow")
async def get_cashflow(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    view: str = Query("projected", description="projected | actual | comparison"),
    year: int | None = Query(None, ge=2020, le=2100),
    from_date: str | None = Query(None, alias="from", description="YYYY-MM"),
    to_date: str | None = Query(None, alias="to", description="YYYY-MM"),
):
    """
    Flujo de Caja — vista proyectada, real o comparativa.

    Query params:
        view=projected:  Requiere year (default año actual)
        view=actual:     Requiere from y to (YYYY-MM)
        view=comparison: Requiere from, to y calcula ambas
    """
    import calendar
    from datetime import date as date_type
    from app.schemas.sales import (
        CashflowLineResponse,
        CashflowAlertResponse,
        CashflowReportResponse,
    )
    from app.adapters.db.models.accounting import CashflowProjection
    from sqlalchemy import select as sa_select

    current_year = date.today().year
    target_year = year or current_year

    if view == "projected":
        # HU-F1-004: Intentar cargar desde DB, si no hay, generar desde variables en memoria
        lines = await CashflowService.load_projection(db, tenant_id, target_year)

        if lines:
            report = CashflowReport(
                tenant_id=tenant_id,
                from_date=date_type(target_year, 1, 1),
                to_date=date_type(target_year, 12, 31),
                lines=lines,
                opening_balance=0.0,
                total_income=sum(l.projected for l in lines if l.category == "income"),
                total_expenses=sum(l.projected for l in lines if l.category == "expense"),
                view="projected",
            )
            report.net_cashflow = round(report.total_income - report.total_expenses, 2)
            report.closing_balance = round(report.opening_balance + report.net_cashflow, 2)
        else:
            # Fallback: generar desde datos en memoria (setup simulado)
            if not _investment:
                raise HTTPException(
                    404,
                    detail="No hay datos de proyección. Ejecute el setup contable primero.",
                )
            report = CashflowService.generate_projection(_investment, target_year)
            report.company_id = tenant_id

        return CashflowReportResponse(
            company_id=report.company_id,
            from_date=report.from_date,
            to_date=report.to_date,
            view=report.view,
            opening_balance=report.opening_balance,
            total_income=report.total_income,
            total_expenses=report.total_expenses,
            net_cashflow=report.net_cashflow,
            closing_balance=report.closing_balance,
            is_balanced=report.is_balanced,
            lines=[
                CashflowLineResponse(
                    month=l.month, year=l.year,
                    concept=l.concept, category=l.category,
                    projected=l.projected, actual=l.actual,
                    difference=l.difference, difference_pct=l.difference_pct,
                )
                for l in report.lines
            ],
            alerts=[
                CashflowAlertResponse(
                    severity=a.severity, category=a.category,
                    message=a.message, month=a.month,
                )
                for a in report.alerts
            ],
        )

    elif view == "actual":
        # HU-F1-005: Vista real desde journal_entries
        if not from_date or not to_date:
            raise HTTPException(400, detail="view=actual requiere 'from' y 'to' (YYYY-MM)")

        try:
            fd_parts = from_date.split("-")
            td_parts = to_date.split("-")
            fd = date_type(int(fd_parts[0]), int(fd_parts[1]), 1)
            _, last_day = calendar.monthrange(int(td_parts[0]), int(td_parts[1]))
            td = date_type(int(td_parts[0]), int(td_parts[1]), last_day)
        except (ValueError, IndexError):
            raise HTTPException(400, detail="Formato de fecha inválido. Use YYYY-MM")

        report = CashflowService.calculate_real(_journal, tenant_id, fd, td)

        return CashflowReportResponse(
            company_id=report.company_id,
            from_date=report.from_date,
            to_date=report.to_date,
            view=report.view,
            opening_balance=report.opening_balance,
            total_income=report.total_income,
            total_expenses=report.total_expenses,
            net_cashflow=report.net_cashflow,
            closing_balance=report.closing_balance,
            is_balanced=report.is_balanced,
            lines=[
                CashflowLineResponse(
                    month=l.month, year=l.year,
                    concept=l.concept, category=l.category,
                    projected=l.projected, actual=l.actual,
                    difference=l.difference, difference_pct=l.difference_pct,
                )
                for l in report.lines
            ],
            alerts=[
                CashflowAlertResponse(
                    severity=a.severity, category=a.category,
                    message=a.message, month=a.month,
                )
                for a in report.alerts
            ],
        )

    elif view == "comparison":
        # HU-F1-006: Comparativa proyectado vs real
        if not from_date or not to_date:
            raise HTTPException(400, detail="view=comparison requiere 'from' y 'to' (YYYY-MM)")

        try:
            fd_parts = from_date.split("-")
            td_parts = to_date.split("-")
            fd = date_type(int(fd_parts[0]), int(fd_parts[1]), 1)
            _, last_day = calendar.monthrange(int(td_parts[0]), int(td_parts[1]))
            td = date_type(int(td_parts[0]), int(td_parts[1]), last_day)
            comp_year = int(fd_parts[0])
        except (ValueError, IndexError):
            raise HTTPException(400, detail="Formato de fecha inválido. Use YYYY-MM")

        # Cargar/calcular proyectado
        lines = await CashflowService.load_projection(db, tenant_id, comp_year)
        if lines:
            proj = CashflowReport(
                tenant_id=tenant_id,
                from_date=fd, to_date=td,
                lines=lines,
                opening_balance=0.0,
                total_income=sum(l.projected for l in lines if l.category == "income"),
                total_expenses=sum(l.projected for l in lines if l.category == "expense"),
                view="projected",
            )
            proj.net_cashflow = round(proj.total_income - proj.total_expenses, 2)
            proj.closing_balance = round(proj.opening_balance + proj.net_cashflow, 2)
        elif _investment:
            proj = CashflowService.generate_projection(_investment, comp_year)
            proj.company_id = tenant_id
        else:
            raise HTTPException(
                404,
                detail="No hay datos de proyección. Ejecute el setup contable primero.",
            )

        # Calcular real
        actual = CashflowService.calculate_real(_journal, tenant_id, fd, td)

        # Comparar
        report = CashflowService.compare(proj, actual)

        return CashflowReportResponse(
            company_id=report.company_id,
            from_date=report.from_date,
            to_date=report.to_date,
            view=report.view,
            opening_balance=report.opening_balance,
            total_income=report.total_income,
            total_expenses=report.total_expenses,
            net_cashflow=report.net_cashflow,
            closing_balance=report.closing_balance,
            is_balanced=report.is_balanced,
            lines=[
                CashflowLineResponse(
                    month=l.month, year=l.year,
                    concept=l.concept, category=l.category,
                    projected=l.projected, actual=l.actual,
                    difference=l.difference, difference_pct=l.difference_pct,
                )
                for l in report.lines
            ],
            alerts=[
                CashflowAlertResponse(
                    severity=a.severity, category=a.category,
                    message=a.message, month=a.month,
                )
                for a in report.alerts
            ],
        )

    else:
        raise HTTPException(
            400, detail="view debe ser 'projected', 'actual' o 'comparison'"
        )
