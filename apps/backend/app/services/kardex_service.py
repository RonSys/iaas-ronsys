"""
📦 DB-Backed Kardex Service — HU-F2-012

Migra el kárdex de variables globales en memoria a repositorio DB.
Usa SQLAlchemyInventoryRepository para persistencia real.

Arquitectura hexagonal: el servicio usa el InventoryRepository (puerto abstracto)
inyectado vía FastAPI Depends.
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.repositories.accounting import SQLAlchemyInventoryRepository
from app.core.accounting.ports import (
    InventoryRepository,
    KardexMovementRecord,
    ProductRecord,
)
from app.core.accounting.kardex import KardexRecord, Product, MovementType
from app.core.tenant import get_tenant_id


class KardexDBService:
    """
    Servicio de kárdex con persistencia DB (HU-F2-012).

    Reemplaza el uso de variables globales _kardex_engine por
    repositorio SQLAlchemy con soporte transaccional.
    """

    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    # ─── Productos ──────────────────────────────────────────────

    async def register_product(
        self,
        code: str,
        name: str,
        unit: str = "kg",
        initial_stock: float = 0.0,
        initial_cost: float = 0.0,
    ) -> ProductRecord:
        """Registra un nuevo producto en DB."""
        existing = await self.repo.get_product(code)
        if existing:
            raise ValueError(f"Producto {code} ya existe")

        return await self.repo.create_product(
            ProductRecord(
                code=code,
                name=name,
                unit_of_measure=unit,
                current_stock=initial_stock,
                average_cost=initial_cost,
                active=True,
            )
        )

    async def get_product(self, code: str) -> ProductRecord:
        """Obtiene producto por código desde DB."""
        p = await self.repo.get_product(code)
        if not p:
            raise KeyError(f"Producto {code} no encontrado")
        return p

    async def get_products(self) -> list[ProductRecord]:
        """Lista todos los productos activos."""
        products = await self.repo.get_products()
        return [p for p in products if p.active]

    # ─── Movimientos de Inventario ─────────────────────────────

    async def record_entry(
        self,
        product_code: str,
        quantity: float,
        unit_cost: float,
        concept: str,
        movement_date: date,
        reference_type: str = "compra",
        reference_id: int | None = None,
    ) -> KardexMovementRecord:
        """
        Registra una ENTRADA de inventario (compra) con promedio ponderado.

        Actualiza stock y costo promedio del producto en DB.
        """
        if quantity <= 0:
            raise ValueError("La cantidad de entrada debe ser > 0")

        product = await self.get_product(product_code)
        total_entry = round(quantity * unit_cost, 2)

        # Calcular nuevo promedio ponderado
        old_total = round(product.current_stock * product.average_cost, 2)
        new_total = old_total + total_entry
        new_quantity = product.current_stock + quantity

        new_avg_cost = round(new_total / new_quantity, 4) if new_quantity > 0 else unit_cost
        new_balance_total = round(new_quantity * new_avg_cost, 2)

        # Guardar movimiento kárdex
        record = await self.repo.save_kardex_movement(
            KardexMovementRecord(
                product_id=product.id or 0,
                movement_type="entrada",
                concept=concept,
                quantity=quantity,
                unit_cost=unit_cost,
                total=total_entry,
                balance_quantity=new_quantity,
                balance_avg_cost=new_avg_cost,
                balance_total=new_balance_total,
                date_=movement_date,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        )

        # Actualizar producto
        product.current_stock = new_quantity
        product.average_cost = new_avg_cost
        await self.repo.update_product(product)

        return record

    async def record_exit(
        self,
        product_code: str,
        quantity: float,
        concept: str,
        movement_date: date,
        reference_type: str = "venta",
        reference_id: int | None = None,
    ) -> KardexMovementRecord:
        """
        Registra una SALIDA de inventario (venta/merma).

        Valoriza al costo promedio actual. No modifica el promedio.
        """
        if quantity <= 0:
            raise ValueError("La cantidad de salida debe ser > 0")

        product = await self.get_product(product_code)

        if quantity > product.current_stock:
            raise ValueError(
                f"Stock insuficiente de {product.name}: "
                f"disponible {product.current_stock} {product.unit_of_measure}, "
                f"solicitado {quantity}"
            )

        exit_total = round(quantity * product.average_cost, 2)
        new_quantity = round(product.current_stock - quantity, 2)
        new_avg = product.average_cost if new_quantity > 0 else 0.0
        new_balance_total = round(new_quantity * new_avg, 2)

        # Guardar movimiento
        record = await self.repo.save_kardex_movement(
            KardexMovementRecord(
                product_id=product.id or 0,
                movement_type="salida",
                concept=concept,
                quantity=quantity,
                unit_cost=product.average_cost,
                total=exit_total,
                balance_quantity=new_quantity,
                balance_avg_cost=new_avg,
                balance_total=new_balance_total,
                date_=movement_date,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        )

        # Actualizar producto
        product.current_stock = new_quantity
        product.average_cost = new_avg
        await self.repo.update_product(product)

        return record

    # ─── Consultas ─────────────────────────────────────────────

    async def get_kardex(self, product_code: str) -> list[KardexMovementRecord]:
        """Historial de movimientos de un producto desde DB."""
        await self.get_product(product_code)  # Valida existencia
        return await self.repo.get_kardex(product_code)

    async def get_inventory_summary(self) -> list[dict]:
        """Resumen del inventario actual con valores calculados."""
        products = await self.get_products()
        return [
            {
                "code": p.code,
                "name": p.name,
                "unit": p.unit_of_measure,
                "current_stock": p.current_stock,
                "average_cost": p.average_cost,
                "total_value": round(p.current_stock * p.average_cost, 2),
            }
            for p in products
        ]

    async def get_total_inventory_value(self) -> float:
        """Valor total del inventario."""
        products = await self.get_products()
        return round(sum(p.current_stock * p.average_cost for p in products), 2)

    async def warehouse_close(self, accounting_balance: float) -> dict:
        """
        Cierre de almacén: verifica Σ Kárdex = Cuenta 12 contable.
        """
        products = await self.get_products()
        inventory_value = await self.get_total_inventory_value()
        difference = round(inventory_value - accounting_balance, 2)

        details = {
            p.code: {
                "name": p.name,
                "stock": p.current_stock,
                "unit_cost": p.average_cost,
                "total": round(p.current_stock * p.average_cost, 2),
            }
            for p in products
        }
        alerts = []
        for p in products:
            if p.current_stock < 0:
                alerts.append(f"⚠️ {p.name}: stock negativo ({p.current_stock})")
            elif p.current_stock == 0:
                alerts.append(f"🟡 {p.name}: stock cero")

        return {
            "inventory_value": inventory_value,
            "accounting_balance": accounting_balance,
            "difference": difference,
            "is_balanced": difference == 0,
            "details": details,
            "alerts": alerts,
        }


# ─── Dependencia FastAPI ────────────────────────────────────

async def get_kardex_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[int, Depends(get_tenant_id)],
) -> KardexDBService:
    """
    FastAPI Depends: inyecta KardexDBService con repositorio DB.

    Uso:
        @router.post("/kardex/...")
        async def endpoint(kardex: KardexDBService = Depends(get_kardex_service)):
            ...
    """
    repo = SQLAlchemyInventoryRepository(db, company_id=tenant_id)
    return KardexDBService(repo)
