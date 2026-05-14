"""
Repositorios SQLAlchemy — Implementaciones de los puertos contables.

Implementa AccountingRepository e InventoryRepository usando SQLAlchemy async.
"""

from datetime import date
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.accounting.ports import (
    AccountingRepository,
    AccountRecord,
    CompanyRecord,
    InventoryRepository,
    JournalEntryRecord,
    JournalLineRecord,
    KardexMovementRecord,
    ProductRecord,
)
from app.adapters.db.models.accounting import (
    Account,
    Company,
    JournalEntry,
    JournalEntryLine,
    KardexMovement,
    Product,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _to_company_record(c: Company) -> CompanyRecord:
    return CompanyRecord(
        id=c.id,
        name=c.name or "",
        ruc=c.ruc or "",
        address=c.address,
        setup_complete=c.setup_complete or False,
    )


def _to_account_record(a: Account) -> AccountRecord:
    return AccountRecord(
        code=a.code,
        name=a.name,
        parent_code=a.parent_code,
        nature=a.nature,
        category=a.category,
        is_balance_sheet=a.is_balance_sheet,
        active=a.active,
    )


def _to_journal_entry_record(je: JournalEntry) -> JournalEntryRecord:
    return JournalEntryRecord(
        id=je.id,
        tenant_id=je.tenant_id,
        entry_number=je.entry_number,
        date_=je.date,
        description=je.description,
        entry_type=je.entry_type,
        reference=je.reference,
        lines=[
            JournalLineRecord(
                account_code=line.account_code,
                debit=float(line.debit),
                credit=float(line.credit),
                description=line.description,
            )
            for line in (je.lines or [])
        ],
    )


def _to_product_record(p: Product) -> ProductRecord:
    return ProductRecord(
        id=p.id,
        code=p.code,
        name=p.name,
        unit_of_measure=p.unit_of_measure,
        current_stock=float(p.current_stock),
        average_cost=float(p.average_cost),
        active=p.active,
    )


def _to_kardex_record(km: KardexMovement) -> KardexMovementRecord:
    return KardexMovementRecord(
        id=km.id,
        product_id=km.product_id,
        movement_type=km.movement_type,
        concept=km.concept,
        quantity=float(km.quantity),
        unit_cost=float(km.unit_cost),
        total=float(km.total),
        balance_quantity=float(km.balance_quantity),
        balance_avg_cost=float(km.balance_avg_cost),
        balance_total=float(km.balance_total),
        date_=km.date,
        reference_type=km.reference_type,
        reference_id=km.reference_id,
    )


# ═══════════════════════════════════════════════════════════════
# SQLAlchemy Accounting Repository
# ═══════════════════════════════════════════════════════════════


class SQLAlchemyAccountingRepository(AccountingRepository):
    """Implementación SQLAlchemy del puerto de contabilidad."""

    def __init__(self, session: AsyncSession, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id

    async def create_company(self, record: CompanyRecord) -> CompanyRecord:
        company = Company(
            name=record.name,
            ruc=record.ruc,
            address=record.address,
            setup_complete=record.setup_complete,
        )
        self.session.add(company)
        await self.session.flush()
        return _to_company_record(company)

    async def get_company(self, tenant_id: int) -> Optional[CompanyRecord]:
        stmt = select(Company).where(Company.id == tenant_id)
        result = await self.session.execute(stmt)
        c = result.scalar_one_or_none()
        return _to_company_record(c) if c else None

    async def seed_accounts(self, records: list[AccountRecord]) -> None:
        accounts = [
            Account(
                code=r.code,
                name=r.name,
                parent_code=r.parent_code,
                nature=r.nature,
                category=r.category,
                is_balance_sheet=r.is_balance_sheet,
                active=r.active,
            )
            for r in records
        ]
        self.session.add_all(accounts)
        await self.session.flush()

    async def get_accounts(self) -> list[AccountRecord]:
        stmt = select(Account).order_by(Account.code)
        result = await self.session.execute(stmt)
        return [_to_account_record(a) for a in result.scalars()]

    async def save_journal_entry(self, record: JournalEntryRecord) -> JournalEntryRecord:
        je = JournalEntry(
            tenant_id=record.tenant_id,
            entry_number=record.entry_number,
            date=record.date_,
            description=record.description,
            entry_type=record.entry_type,
            reference=record.reference,
        )
        for line in record.lines:
            je.lines.append(
                JournalEntryLine(
                    account_code=line.account_code,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
            )

        self.session.add(je)
        await self.session.flush()
        return _to_journal_entry_record(je)

    async def get_journal_entries(
        self, tenant_id: int, start: Optional[date] = None, end: Optional[date] = None
    ) -> list[JournalEntryRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.tenant_id == tenant_id)
            .order_by(JournalEntry.date, JournalEntry.entry_number)
        )
        if start:
            stmt = stmt.where(JournalEntry.date >= start)
        if end:
            stmt = stmt.where(JournalEntry.date <= end)

        result = await self.session.execute(stmt)
        return [_to_journal_entry_record(je) for je in result.unique().scalars()]

    async def clear_journal(self, tenant_id: int) -> None:
        # Delete lines first
        subq = select(JournalEntry.id).where(JournalEntry.tenant_id == tenant_id)
        await self.session.execute(
            delete(JournalEntryLine).where(JournalEntryLine.entry_id.in_(subq))
        )
        await self.session.execute(
            delete(JournalEntry).where(JournalEntry.tenant_id == tenant_id)
        )
        await self.session.flush()


# ═══════════════════════════════════════════════════════════════
# SQLAlchemy Inventory Repository
# ═══════════════════════════════════════════════════════════════


class SQLAlchemyInventoryRepository(InventoryRepository):
    """Implementación SQLAlchemy del puerto de inventario."""

    def __init__(self, session: AsyncSession, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id

    async def create_product(self, record: ProductRecord) -> ProductRecord:
        p = Product(
            tenant_id=self.tenant_id,
            code=record.code,
            name=record.name,
            unit_of_measure=record.unit_of_measure,
            current_stock=record.current_stock,
            average_cost=record.average_cost,
            active=record.active,
        )
        self.session.add(p)
        await self.session.flush()
        return _to_product_record(p)

    async def get_product(self, product_code: str) -> Optional[ProductRecord]:
        stmt = select(Product).where(Product.code == product_code)
        result = await self.session.execute(stmt)
        p = result.scalar_one_or_none()
        return _to_product_record(p) if p else None

    async def get_products(self) -> list[ProductRecord]:
        stmt = select(Product).order_by(Product.name)
        result = await self.session.execute(stmt)
        return [_to_product_record(p) for p in result.scalars()]

    async def update_product(self, record: ProductRecord) -> ProductRecord:
        stmt = select(Product).where(Product.code == record.code)
        result = await self.session.execute(stmt)
        p = result.scalar_one()
        p.current_stock = record.current_stock
        p.average_cost = record.average_cost
        p.active = record.active
        await self.session.flush()
        return _to_product_record(p)

    async def save_kardex_movement(
        self, record: KardexMovementRecord
    ) -> KardexMovementRecord:
        km = KardexMovement(
            product_id=record.product_id,
            movement_type=record.movement_type,
            concept=record.concept,
            quantity=record.quantity,
            unit_cost=record.unit_cost,
            total=record.total,
            balance_quantity=record.balance_quantity,
            balance_avg_cost=record.balance_avg_cost,
            balance_total=record.balance_total,
            date=record.date_,
            reference_type=record.reference_type,
            reference_id=record.reference_id,
        )
        self.session.add(km)
        await self.session.flush()
        return _to_kardex_record(km)

    async def get_kardex(self, product_code: str) -> list[KardexMovementRecord]:
        stmt = (
            select(KardexMovement)
            .join(Product)
            .where(Product.code == product_code)
            .order_by(KardexMovement.date, KardexMovement.id)
        )
        result = await self.session.execute(stmt)
        return [_to_kardex_record(km) for km in result.scalars()]

    async def clear_inventory(self) -> None:
        await self.session.execute(delete(KardexMovement))
        await self.session.execute(delete(Product))
        await self.session.flush()
