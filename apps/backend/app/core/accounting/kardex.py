"""
📦 Kárdex — Control de Inventarios con Promedio Ponderado

Basado en:
  - simulador-financiero/docs/10-kardex.md

Arquitectura hexagonal: dominio puro.

Responsabilidad:
  - Registrar productos
  - Procesar entradas (compras) con Promedio Ponderado
  - Procesar salidas (ventas, mermas) valorizadas al costo promedio
  - Calcular valor total del inventario
  - Cierre de almacén: verificar Σ Kárdex = Cuenta 12
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from app.core.accounting.engine import (
    EntryType,
    JournalEntry,
    JournalLine,
    MovementType,
)


# ═══════════════════════════════════════════════════════════════
# Entidades del Dominio
# ═══════════════════════════════════════════════════════════════


@dataclass
class Product:
    """Producto del inventario (dominio)."""
    code: str
    name: str
    unit_of_measure: str = "kg"
    description: str | None = None
    current_stock: float = 0.0
    average_cost: float = 0.0  # Costo promedio ponderado
    active: bool = True

    @property
    def total_value(self) -> float:
        """Valor total del inventario de este producto."""
        return round(self.current_stock * self.average_cost, 2)


@dataclass
class KardexRecord:
    """Registro de un movimiento en el Kárdex."""
    product_code: str
    movement_type: MovementType  # entrada | salida | ajuste
    concept: str  # Compra / Venta / Merma
    quantity: float
    unit_cost: float
    total: float
    balance_quantity: float  # Saldo después del movimiento
    balance_avg_cost: float  # Costo promedio después del movimiento
    balance_total: float  # Saldo valorizado
    date_: date
    reference_type: str | None = None
    reference_id: int | None = None


# ═══════════════════════════════════════════════════════════════
# Motor del Kárdex
# ═══════════════════════════════════════════════════════════════


class KardexEngine:
    """
    Motor de Kárdex con método Promedio Ponderado.

    Mantiene el estado de productos en memoria y genera:
      - Registros de Kárdex (historial de movimientos)
      - Asientos contables automáticos
    """

    def __init__(self):
        self.products: dict[str, Product] = {}
        self.records: list[KardexRecord] = []
        self.generated_entries: list[JournalEntry] = []
        self._entry_counter = 0

    def _next_entry_number(self) -> str:
        self._entry_counter += 1
        return f"KAR-{self._entry_counter:04d}"

    # ─── Gestión de Productos ──────────────────────────────────

    def register_product(
        self,
        code: str,
        name: str,
        unit: str = "kg",
        initial_stock: float = 0.0,
        initial_cost: float = 0.0,
    ) -> Product:
        """Registra un nuevo producto en el inventario."""
        if code in self.products:
            raise ValueError(f"Producto {code} ya existe")
        p = Product(
            code=code,
            name=name,
            unit_of_measure=unit,
            current_stock=initial_stock,
            average_cost=initial_cost,
        )
        self.products[code] = p
        return p

    def get_product(self, code: str) -> Product:
        """Obtiene un producto por código."""
        if code not in self.products:
            raise KeyError(f"Producto {code} no encontrado")
        return self.products[code]

    # ─── Movimientos de Inventario ─────────────────────────────

    def record_entry(
        self,
        product_code: str,
        quantity: float,
        unit_cost: float,
        concept: str,
        movement_date: date,
        reference_type: str = "compra",
        reference_id: int | None = None,
    ) -> tuple[KardexRecord, JournalEntry | None]:
        """
        Registra una ENTRADA de inventario (compra).

        Calcula nuevo promedio ponderado y genera asiento contable:
          Debe: 12 Inventarios  /  Haber: 10 Efectivo

        Fórmula:
          Nuevo Promedio = (Saldo Total Anterior + Nuevo Total) /
                           (Saldo Cantidad Anterior + Nueva Cantidad)
        """
        if quantity <= 0:
            raise ValueError("La cantidad de entrada debe ser > 0")

        product = self.get_product(product_code)
        total_entry = round(quantity * unit_cost, 2)

        # Calcular nuevo promedio ponderado
        old_total = round(product.current_stock * product.average_cost, 2)
        new_total = old_total + total_entry
        new_quantity = product.current_stock + quantity

        new_avg_cost = round(new_total / new_quantity, 4) if new_quantity > 0 else unit_cost
        new_balance_total = round(new_quantity * new_avg_cost, 2)

        # Crear registro de kárdex
        record = KardexRecord(
            product_code=product_code,
            movement_type=MovementType.ENTRADA,
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
        self.records.append(record)

        # Actualizar producto
        product.current_stock = new_quantity
        product.average_cost = new_avg_cost

        # Generar asiento contable
        entry = JournalEntry(
            entry_number=self._next_entry_number(),
            date_=movement_date,
            description=f"Compra: {concept} — {product.name}",
            entry_type=EntryType.COMPRA,
            reference=reference_type,
            lines=[
                JournalLine("12", debit=total_entry, description=f"Inventario + {product.name}"),
                JournalLine("10", credit=total_entry, description="Efectivo"),
            ],
        )
        self.generated_entries.append(entry)

        return record, entry

    def record_exit(
        self,
        product_code: str,
        quantity: float,
        concept: str,
        movement_date: date,
        reference_type: str = "venta",
        reference_id: int | None = None,
    ) -> tuple[KardexRecord, JournalEntry | None]:
        """
        Registra una SALIDA de inventario (venta/merma).

        Valoriza al costo promedio actual y genera asiento:
          - Venta:  Debe: 50 Costo Ventas  /  Haber: 12 Inventarios
          - Merma:  Debe: 66 Otros Gastos  /  Haber: 12 Inventarios

        El costo promedio NO cambia con las salidas.
        """
        if quantity <= 0:
            raise ValueError("La cantidad de salida debe ser > 0")

        product = self.get_product(product_code)

        if quantity > product.current_stock:
            raise ValueError(
                f"Stock insuficiente de {product.name}: "
                f"disponible {product.current_stock} {product.unit_of_measure}, "
                f"solicitado {quantity}"
            )

        # Valorizar al costo promedio actual
        exit_cost = round(quantity * product.average_cost, 4)
        exit_total = round(quantity * product.average_cost, 2)

        new_quantity = round(product.current_stock - quantity, 2)
        new_avg = product.average_cost if new_quantity > 0 else 0.0
        new_balance_total = round(new_quantity * new_avg, 2)

        # Crear registro
        record = KardexRecord(
            product_code=product_code,
            movement_type=MovementType.SALIDA,
            concept=concept,
            quantity=quantity,
            unit_cost=product.average_cost,  # Valorizado al promedio
            total=exit_total,
            balance_quantity=new_quantity,
            balance_avg_cost=new_avg,
            balance_total=new_balance_total,
            date_=movement_date,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.records.append(record)

        # Actualizar producto
        product.current_stock = new_quantity
        product.average_cost = new_avg

        # Generar asiento contable
        is_merma = reference_type in ("merma", "ajuste", "inventario_fisico")
        debit_account = "66" if is_merma else "50"
        debit_desc = "Merma / Otros gastos" if is_merma else "Costo de ventas"

        entry = JournalEntry(
            entry_number=self._next_entry_number(),
            date_=movement_date,
            description=f"{'Venta' if not is_merma else 'Merma'}: {concept} — {product.name}",
            entry_type=EntryType.VENTA if not is_merma else EntryType.MANUAL,
            reference=reference_type,
            lines=[
                JournalLine(
                    debit_account, debit=exit_total, description=f"{debit_desc} - {product.name}"
                ),
                JournalLine(
                    "12", credit=exit_total, description=f"Inventario - {product.name}"
                ),
            ],
        )
        self.generated_entries.append(entry)

        return record, entry

    def record_initial_inventory(
        self,
        product_code: str,
        quantity: float,
        unit_cost: float,
        concept: str = "Inventario inicial",
        movement_date: date | None = None,
    ) -> tuple[KardexRecord, JournalEntry]:
        """Registra inventario inicial (primera entrada sin promedio previo)."""
        product = self.get_product(product_code)
        total = round(quantity * unit_cost, 2)
        md = movement_date or date.today()

        record = KardexRecord(
            product_code=product_code,
            movement_type=MovementType.ENTRADA,
            concept=concept,
            quantity=quantity,
            unit_cost=unit_cost,
            total=total,
            balance_quantity=quantity,
            balance_avg_cost=unit_cost,
            balance_total=total,
            date_=md,
            reference_type="inventario_inicial",
        )
        self.records.append(record)

        product.current_stock = quantity
        product.average_cost = unit_cost

        entry = JournalEntry(
            entry_number=self._next_entry_number(),
            date_=md,
            description=f"Inventario inicial: {product.name}",
            entry_type=EntryType.APERTURA,
            lines=[
                JournalLine("12", debit=total, description=f"Inventario inicial {product.name}"),
                JournalLine("30", credit=total, description="Aporte en especie"),
            ],
        )
        self.generated_entries.append(entry)
        return record, entry

    # ─── Consultas ─────────────────────────────────────────────

    def get_kardex(self, product_code: str) -> list[KardexRecord]:
        """Kárdex completo de un producto (historial de movimientos)."""
        return [r for r in self.records if r.product_code == product_code]

    def get_total_inventory_value(self) -> float:
        """Valor total del inventario = Σ (stock × costo_promedio)."""
        return round(sum(p.total_value for p in self.products.values()), 2)

    def get_cost_of_sales(
        self, product_code: str | None = None, start_date: date | None = None,
        end_date: date | None = None
    ) -> float:
        """
        Costo de ventas (total salidas valorizadas) para un período/producto.
        """
        total = 0.0
        for r in self.records:
            if r.movement_type != MovementType.SALIDA:
                continue
            if r.reference_type == "merma":
                continue
            if product_code and r.product_code != product_code:
                continue
            if start_date and r.date_ < start_date:
                continue
            if end_date and r.date_ > end_date:
                continue
            total += r.total
        return round(total, 2)

    # ─── Cierre de Almacén ─────────────────────────────────────

    def warehouse_close(
        self,
        accounting_inventory_balance: float,  # Saldo de Cuenta 12 según contabilidad
    ) -> dict:
        """
        Verifica que el inventario físico (Kárdex) cuadre con la contabilidad.

        Retorna:
          - inventory_value: valor total según Kárdex
          - accounting_balance: saldo contable (Cuenta 12)
          - difference: diferencia (0 = cuadra)
          - is_balanced: True si cuadra
          - details: detalle por producto
          - alerts: productos con stock cero, negativos, etc.
        """
        inventory_value = self.get_total_inventory_value()
        difference = round(inventory_value - accounting_inventory_balance, 2)
        details = {
            p.code: {
                "name": p.name,
                "stock": p.current_stock,
                "unit_cost": p.average_cost,
                "total": p.total_value,
            }
            for p in self.products.values() if p.active
        }
        alerts = []
        for p in self.products.values():
            if not p.active:
                continue
            if p.current_stock < 0:
                alerts.append(f"⚠️ {p.name}: stock negativo ({p.current_stock})")
            elif p.current_stock == 0 and p.active:
                alerts.append(f"🟡 {p.name}: stock cero")

        return {
            "inventory_value": inventory_value,
            "accounting_balance": accounting_inventory_balance,
            "difference": difference,
            "is_balanced": difference == 0,
            "details": details,
            "alerts": alerts,
        }
