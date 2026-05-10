"""
Puertos del dominio contable — Interfaces abstractas (Hexagonal).

El dominio depende de estas abstracciones, no de implementaciones concretas.
Las implementaciones viven en adapters/db/repositories/.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Entidades de repositorio (compartidas entre puerto y adaptador)
# ═══════════════════════════════════════════════════════════════


@dataclass
class AccountRecord:
    code: str
    name: str
    parent_code: Optional[str] = None
    nature: str = "D"
    category: str = "asset"
    is_balance_sheet: bool = True
    active: bool = True


@dataclass
class JournalEntryRecord:
    id: Optional[int] = None
    company_id: int = 1
    entry_number: str = ""
    date_: date = date.today()
    description: str = ""
    entry_type: str = "manual"
    reference: Optional[str] = None
    lines: list["JournalLineRecord"] = field(default_factory=list)


@dataclass
class JournalLineRecord:
    entry_id: Optional[int] = None
    account_code: str = ""
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None


@dataclass
class CompanyRecord:
    id: Optional[int] = None
    name: str = ""
    ruc: str = ""
    address: Optional[str] = None
    setup_complete: bool = False


@dataclass
class ProductRecord:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    unit_of_measure: str = "kg"
    current_stock: float = 0.0
    average_cost: float = 0.0
    active: bool = True


@dataclass
class KardexMovementRecord:
    id: Optional[int] = None
    product_id: int = 0
    movement_type: str = ""
    concept: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    total: float = 0.0
    balance_quantity: float = 0.0
    balance_avg_cost: float = 0.0
    balance_total: float = 0.0
    date_: date = date.today()
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════════
# Puertos (Interfaces Abstractas)
# ═══════════════════════════════════════════════════════════════


class AccountingRepository(ABC):
    """Puerto para persistencia contable."""

    @abstractmethod
    async def create_company(self, record: CompanyRecord) -> CompanyRecord: ...

    @abstractmethod
    async def get_company(self, company_id: int) -> Optional[CompanyRecord]: ...

    @abstractmethod
    async def seed_accounts(self, accounts: list[AccountRecord]) -> None: ...

    @abstractmethod
    async def get_accounts(self) -> list[AccountRecord]: ...

    @abstractmethod
    async def save_journal_entry(self, record: JournalEntryRecord) -> JournalEntryRecord: ...

    @abstractmethod
    async def get_journal_entries(
        self, company_id: int, start: Optional[date] = None, end: Optional[date] = None
    ) -> list[JournalEntryRecord]: ...

    @abstractmethod
    async def clear_journal(self, company_id: int) -> None: ...


class InventoryRepository(ABC):
    """Puerto para inventario (Kárdex)."""

    @abstractmethod
    async def create_product(self, record: ProductRecord) -> ProductRecord: ...

    @abstractmethod
    async def get_product(self, product_code: str) -> Optional[ProductRecord]: ...

    @abstractmethod
    async def get_products(self) -> list[ProductRecord]: ...

    @abstractmethod
    async def update_product(self, record: ProductRecord) -> ProductRecord: ...

    @abstractmethod
    async def save_kardex_movement(self, record: KardexMovementRecord) -> KardexMovementRecord: ...

    @abstractmethod
    async def get_kardex(self, product_code: str) -> list[KardexMovementRecord]: ...

    @abstractmethod
    async def clear_inventory(self) -> None: ...
