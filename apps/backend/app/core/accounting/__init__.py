"""
📊 Módulo de Contabilidad — Motor contable + Kárdex + Estados Financieros

Responde a la documentación detallada en:
  ../../simulador-financiero/docs/03-logica-contable.md
  ../../simulador-financiero/docs/04-estados-financieros.md
  ../../simulador-financiero/docs/05-flujo-caja.md
  ../../simulador-financiero/docs/06-ratios.md
  ../../simulador-financiero/docs/10-kardex.md
"""

from app.core.accounting.engine import (  # noqa: F401
    BCSS,
    BCSSLine,
    AccountCategory,
    AccountDef,
    AccountNature,
    BalanceSheet,
    DEFAULT_CHART_OF_ACCOUNTS,
    EntryType,
    IncomeStatement,
    InvestmentVariables,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    MovementType,
    build_general_ledger,
    calculate_bcss,
    generate_closing_entry,
    generate_income_statement,
    generate_balance_sheet,
    generate_monthly_entries,
    generate_opening_entries,
    get_account_map,
    validate_double_entry,
)

from app.core.accounting.kardex import (  # noqa: F401
    KardexEngine,
    KardexRecord,
    Product as KardexProduct,
)

from app.core.accounting.statements import (  # noqa: F401
    FinancialReport,
    FinancialStatementService,
)

from app.core.accounting.ratios import (  # noqa: F401
    FinancialRatios,
    RatioResult,
    TrafficLight,
    calculate_ratios,
    evaluate_ratios,
)

from app.core.accounting.ports import (  # noqa: F401
    AccountingRepository,
    AccountRecord,
    CompanyRecord,
    InventoryRepository,
    JournalEntryRecord,
    JournalLineRecord,
    KardexMovementRecord,
    ProductRecord,
)
