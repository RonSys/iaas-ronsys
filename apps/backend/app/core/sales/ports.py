"""
Puertos del dominio de Ventas — Interfaces abstractas (Hexagonal).

HU-F1-009: Define SalesRepository(ABC) con métodos abstractos para
operaciones de ventas, sesiones POS, y especializaciones por negocio.

El dominio depende de estas abstracciones, no de implementaciones concretas.
Las implementaciones viven en adapters/db/repositories/sales.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Records de dominio (compartidos entre puerto y adaptador)
# ═══════════════════════════════════════════════════════════════


@dataclass
class PosSessionRecord:
    """Turno de caja (apertura/cierre)."""
    id: Optional[int] = None
    tenant_id: int = 0
    user_id: int = 0
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    opening_cash: float = 0.0
    closing_cash: float | None = None
    expected_cash: float | None = None
    difference: float | None = None
    status: str = "open"  # open | closed
    notes: str | None = None


@dataclass
class SaleItemRecord:
    """Ítem de una venta."""
    id: Optional[int] = None
    sale_id: Optional[int] = None
    product_id: Optional[int] = None
    item_name: str = ""
    item_type: str = "product"  # product | service | combo
    quantity: float = 0.0
    unit_of_measure: str = "unidad"
    unit_price: float = 0.0
    discount_pct: float = 0.0
    discount_amount: float = 0.0
    tax_pct: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    kardex_movement_id: Optional[int] = None


@dataclass
class SalePaymentRecord:
    """Método de pago de una venta."""
    id: Optional[int] = None
    sale_id: Optional[int] = None
    payment_method: str = "cash"  # cash | card | yape | plin | transfer
    amount: float = 0.0
    reference: str | None = None


@dataclass
class SaleRecord:
    """Venta completa (cabecera)."""
    id: Optional[int] = None
    tenant_id: int = 0
    session_id: int = 0
    user_id: int = 0
    sale_number: str = ""
    sale_date: date | None = None
    sale_time: time | None = None
    customer_name: str | None = None
    customer_doc: str | None = None
    subtotal: float = 0.0
    discount_total: float = 0.0
    tax_total: float = 0.0
    tip_amount: float = 0.0
    total: float = 0.0
    business_type: str = "restaurant"  # restaurant | hardware | retail | service
    is_voided: bool = False
    void_reason: str | None = None
    journal_entry_id: Optional[int] = None
    items: list[SaleItemRecord] = field(default_factory=list)
    payments: list[SalePaymentRecord] = field(default_factory=list)


@dataclass
class RestaurantSaleRecord:
    """Especialización restaurante (1:1 con Sale)."""
    id: Optional[int] = None
    sale_id: int = 0
    table_number: str | None = None
    guests: int = 1
    order_type: str = "dine_in"  # dine_in | takeout | delivery
    waiter_name: str | None = None
    tip_amount: float = 0.0
    tip_pct: float = 0.0
    kitchen_notes: str | None = None


@dataclass
class HardwareSaleRecord:
    """Especialización ferretería (1:1 con Sale)."""
    id: Optional[int] = None
    sale_id: int = 0
    invoice_type: str = "boleta"  # boleta | factura
    delivery_address: str | None = None
    requires_install: bool = False
    warranty_months: int = 0


# ═══════════════════════════════════════════════════════════════
# Puerto Abstracto
# ═══════════════════════════════════════════════════════════════


class SalesRepository(ABC):
    """
    Puerto para persistencia de ventas y sesiones POS.

    HU-F1-009: Define la interfaz que los adaptadores DB deben implementar.
    En Fase 2, sales_service.py usará este puerto en lugar de importar
    modelos ORM directamente.
    """

    # ─── Sesiones POS ──────────────────────────────────────

    @abstractmethod
    async def create_session(self, record: PosSessionRecord) -> PosSessionRecord:
        """Abre una nueva sesión POS."""
        ...

    @abstractmethod
    async def get_current_session(self, tenant_id: int) -> Optional[PosSessionRecord]:
        """Obtiene la sesión POS abierta actual."""
        ...

    @abstractmethod
    async def get_session(self, session_id: int, tenant_id: int) -> Optional[PosSessionRecord]:
        """Obtiene una sesión POS por ID."""
        ...

    @abstractmethod
    async def close_session(
        self, session_id: int, tenant_id: int, closing_cash: float,
        expected_cash: float, difference: float, notes: str | None = None,
    ) -> PosSessionRecord:
        """Cierra una sesión POS."""
        ...

    # ─── Ventas ────────────────────────────────────────────

    @abstractmethod
    async def create_sale(self, record: SaleRecord) -> SaleRecord:
        """Crea una venta con sus ítems y pagos en una transacción."""
        ...

    @abstractmethod
    async def get_sale(self, sale_id: int, tenant_id: int) -> Optional[SaleRecord]:
        """Obtiene detalle completo de una venta (cabecera + items + payments)."""
        ...

    @abstractmethod
    async def list_sales(
        self, tenant_id: int,
        page: int = 1, limit: int = 20,
        from_date: date | None = None,
        to_date: date | None = None,
        business_type: str | None = None,
        session_id: int | None = None,
        is_voided: bool | None = None,
    ) -> tuple[list[SaleRecord], int]:
        """Lista ventas paginado con filtros. Retorna (items, total_count)."""
        ...

    @abstractmethod
    async def void_sale(
        self, sale_id: int, tenant_id: int, reason: str,
    ) -> SaleRecord:
        """Anula una venta (soft delete)."""
        ...

    # ─── Especializaciones ─────────────────────────────────

    @abstractmethod
    async def create_restaurant_sale(
        self, record: RestaurantSaleRecord,
    ) -> RestaurantSaleRecord:
        """Crea registro de especialización restaurante."""
        ...

    @abstractmethod
    async def create_hardware_sale(
        self, record: HardwareSaleRecord,
    ) -> HardwareSaleRecord:
        """Crea registro de especialización ferretería."""
        ...

    @abstractmethod
    async def get_restaurant_sale(
        self, sale_id: int,
    ) -> Optional[RestaurantSaleRecord]:
        """Obtiene especialización restaurante de una venta."""
        ...

    @abstractmethod
    async def get_hardware_sale(
        self, sale_id: int,
    ) -> Optional[HardwareSaleRecord]:
        """Obtiene especialización ferretería de una venta."""
        ...
