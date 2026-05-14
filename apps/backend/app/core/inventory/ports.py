"""
Puertos del dominio de Inventario — Interfaces abstractas (Hexagonal).

HU-F1-009: Define InventoryRepository(ABC) con métodos abstractos para
productos, movimientos de kárdex, y categorías.

El dominio depende de estas abstracciones, no de implementaciones concretas.
Las implementaciones viven en adapters/db/repositories/inventory.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Records de dominio
# ═══════════════════════════════════════════════════════════════


@dataclass
class ProductRecord:
    """Producto del inventario."""
    id: Optional[int] = None
    tenant_id: int = 0
    code: str = ""
    name: str = ""
    description: str | None = None
    unit_of_measure: str = "kg"
    current_stock: float = 0.0
    average_cost: float = 0.0
    active: bool = True
    category_id: Optional[int] = None
    category_name: str | None = None
    wholesale_price: float | None = None
    wholesale_min_qty: int | None = None
    barcode: str | None = None


@dataclass
class CategoryRecord:
    """Categoría de producto."""
    id: Optional[int] = None
    tenant_id: int = 0
    name: str = ""
    product_count: int = 0


@dataclass
class KardexMovementRecord:
    """Movimiento de kárdex (entrada/salida/ajuste)."""
    id: Optional[int] = None
    product_id: int = 0
    movement_type: str = ""  # entrada | salida | ajuste
    concept: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    total: float = 0.0
    balance_quantity: float = 0.0
    balance_avg_cost: float = 0.0
    balance_total: float = 0.0
    date_: date | None = None
    reference_type: str | None = None  # compra | venta | inventario_inicial
    reference_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════════
# Puerto Abstracto
# ═══════════════════════════════════════════════════════════════


class InventoryRepository(ABC):
    """
    Puerto para persistencia de inventario y kárdex.

    HU-F1-009: Define la interfaz que los adaptadores DB deben implementar.
    """

    # ─── Productos ─────────────────────────────────────────

    @abstractmethod
    async def create_product(self, record: ProductRecord) -> ProductRecord:
        """Crea un producto en el inventario."""
        ...

    @abstractmethod
    async def get_product(self, product_code: str, tenant_id: int) -> Optional[ProductRecord]:
        """Obtiene un producto por código con scoping de tenant."""
        ...

    @abstractmethod
    async def get_product_by_id(self, product_id: int, tenant_id: int) -> Optional[ProductRecord]:
        """Obtiene un producto por ID con scoping de tenant."""
        ...

    @abstractmethod
    async def list_products(
        self, tenant_id: int,
        category_id: int | None = None,
        category_name: str | None = None,
        search: str | None = None,
        active: bool | None = None,
        limit: int = 100, offset: int = 0,
    ) -> tuple[list[ProductRecord], int]:
        """Lista productos con filtros. Retorna (items, total_count)."""
        ...

    @abstractmethod
    async def update_product(self, record: ProductRecord) -> ProductRecord:
        """Actualiza un producto (stock, costo, etc.)."""
        ...

    # ─── Categorías ────────────────────────────────────────

    @abstractmethod
    async def create_category(self, tenant_id: int, name: str) -> CategoryRecord:
        """Crea una categoría de producto."""
        ...

    @abstractmethod
    async def list_categories(self, tenant_id: int) -> list[CategoryRecord]:
        """Lista categorías con conteo de productos."""
        ...

    @abstractmethod
    async def update_category(
        self, category_id: int, tenant_id: int, name: str,
    ) -> CategoryRecord:
        """Actualiza una categoría."""
        ...

    @abstractmethod
    async def delete_category(self, category_id: int, tenant_id: int) -> None:
        """Elimina una categoría si no tiene productos."""
        ...

    # ─── Kárdex ────────────────────────────────────────────

    @abstractmethod
    async def save_kardex_movement(
        self, record: KardexMovementRecord,
    ) -> KardexMovementRecord:
        """Registra un movimiento de kárdex."""
        ...

    @abstractmethod
    async def get_kardex(
        self, product_code: str, tenant_id: int,
    ) -> list[KardexMovementRecord]:
        """Historial de kárdex de un producto."""
        ...

    @abstractmethod
    async def get_inventory_summary(self, tenant_id: int) -> list[ProductRecord]:
        """Resumen de inventario actual con valores."""
        ...
