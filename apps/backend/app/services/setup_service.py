"""
Servicio de Setup — Orquestación de la configuración inicial.

Orquesta:
  1. Recibir datos de inversión inicial
  2. Crear empresa (Company) en BD
  3. Sembrar plan de cuentas
  4. Llamar al motor contable para generar asientos
  5. Persistir asientos en BD
  6. Retornar reporte financiero completo

Arquitectura hexagonal: depende del puerto AccountingRepository.
"""

from datetime import date
from typing import Optional

from app.core.accounting import (
    AccountDef,
    AccountNature,
    AccountRecord,
    CompanyRecord,
    DEFAULT_CHART_OF_ACCOUNTS,
    FinancialReport,
    FinancialStatementService,
    InvestmentVariables,
    JournalEntry,
    JournalEntryRecord,
    JournalLineRecord,
    AccountingRepository,
)


class SetupService:
    """
    Servicio de configuración inicial de empresa y contabilidad.

    Uso:
        repo = SQLAlchemyAccountingRepository(session)
        service = SetupService(repo)
        report = await service.setup_company(investment_input)
    """

    def __init__(self, repo: AccountingRepository):
        self.repo = repo

    async def setup_company(
        self,
        name: str,
        ruc: str,
        variables: InvestmentVariables,
        address: Optional[str] = None,
        months: int = 12,
        start_date: date = date(2026, 1, 1),
    ) -> FinancialReport:
        """
        Configura una empresa nueva con datos de inversión.

        Pasos:
          1. Crea la empresa en BD
          2. Siembra el plan de cuentas PCGE
          3. Ejecuta la simulación financiera (motor contable)
          4. Persiste los asientos generados en BD
          5. Retorna el reporte financiero completo

        Returns:
            FinancialReport con BCSS, PYG, Balance, Ratios y validaciones.
        """
        # 1. Crear empresa
        company = await self.repo.create_company(
            CompanyRecord(
                name=name,
                ruc=ruc,
                address=address,
                setup_complete=False,
            )
        )

        # 2. Sembrar plan de cuentas (si no existe ya)
        existing_accounts = await self.repo.get_accounts()
        if not existing_accounts:
            account_records = _build_account_records(DEFAULT_CHART_OF_ACCOUNTS)
            await self.repo.seed_accounts(account_records)

        # 3. Ejecutar simulación financiera
        report = FinancialStatementService.run_simulation(
            variables,
            months=months,
            start_date=start_date,
        )

        # 4. Persistir asientos en BD
        for entry in report.journal:
            await self._persist_entry(entry, company.id or 1)

        # 5. Marcar empresa como configurada
        company.setup_complete = True

        return report

    async def _persist_entry(self, entry: JournalEntry, company_id: int) -> None:
        """Persiste un asiento contable y sus líneas en BD."""
        record = JournalEntryRecord(
            company_id=company_id,
            entry_number=entry.entry_number,
            date_=entry.date_,
            description=entry.description,
            entry_type=entry.entry_type.value
            if hasattr(entry.entry_type, "value")
            else entry.entry_type,
            reference=entry.reference,
            lines=[
                JournalLineRecord(
                    account_code=line.account_code,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
                for line in entry.lines
            ],
        )
        await self.repo.save_journal_entry(record)


def _build_account_records(defs: list[AccountDef]) -> list[AccountRecord]:
    """Convierte AccountDef (dominio) → AccountRecord (puerto)."""
    return [
        AccountRecord(
            code=a.code,
            name=a.name,
            parent_code=a.parent_code,
            nature=a.nature.value if hasattr(a.nature, "value") else str(a.nature),
            category=a.category.value
            if hasattr(a.category, "value")
            else str(a.category),
            is_balance_sheet=a.is_balance_sheet,
            active=a.active,
        )
        for a in defs
    ]
