"""
Modelos ORM — Contabilidad + Kárdex.

Basado en:
  - simulador-financiero/docs/02-plan-cuentas.md
  - simulador-financiero/docs/03-logica-contable.md
  - simulador-financiero/docs/10-kardex.md

Tablas:
  - companies:         Datos de la empresa (tenant)
  - accounts:           Catálogo de cuentas contables
  - journal_entries:    Asientos contables (cabecera)
  - journal_entry_lines: Líneas de asiento (detalle)
  - products:           Productos del inventario
  - kardex_movements:   Movimientos de kárdex
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ═══════════════════════════════════════════════════════════════
# Base común
# ═══════════════════════════════════════════════════════════════


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════
# Empresa (tenant)
# ═══════════════════════════════════════════════════════════════


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ruc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(300))
    economic_activity: Mapped[str | None] = mapped_column(String(200))
    business_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="restaurant", default="restaurant"
    )  # restaurant | hardware | retail | service
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════
# Plan de Cuentas
# ═══════════════════════════════════════════════════════════════


class Account(Base):
    """
    Catálogo de cuentas contables — PCGE peruano adaptado.

    Naturaleza:
      - 'D' = Deudora (saldo normal al debe): Activo, Costos, Gastos
      - 'A' = Acreedora (saldo normal al haber): Pasivo, Patrimonio, Ingresos

    Categoría:
      - 'asset'           → Activo (1xx)
      - 'contra_asset'     → Depreciación acumulada (19x)
      - 'liability'        → Pasivo (2xx)
      - 'equity'           → Patrimonio (3xx)
      - 'income'           → Ingresos (4xx)
      - 'cost'             → Costos (5xx)
      - 'expense'          → Gastos (6xx)
      - 'closing'          → Cierre (8xx)
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("accounts.code"), nullable=True
    )
    nature: Mapped[str] = mapped_column(
        String(1), nullable=False, default="D"
    )  # 'D' | 'A'
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    is_balance_sheet: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # True=Balance, False=Resultado
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════
# Asientos Contables
# ═══════════════════════════════════════════════════════════════


class JournalEntry(Base):
    """Cabecera del asiento contable."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    entry_number: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ej: 'AS-001', 'VEN-2026-001'
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    entry_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )  # 'apertura' | 'compra' | 'venta' | 'gasto' | 'depreciacion' | 'cierre' | 'manual'
    reference: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relación a líneas
    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine", back_populates="entry", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_journal_entries_company_date", "company_id", "date"),
    )


class JournalEntryLine(Base):
    """Línea (detalle) de un asiento contable."""

    __tablename__ = "journal_entry_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("journal_entries.id"), nullable=False, index=True
    )
    account_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("accounts.code"), nullable=False
    )
    debit: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    credit: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))

    # Relación inversa
    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    account: Mapped["Account"] = relationship("Account")

    __table_args__ = (
        Index("idx_jel_entry_id", "entry_id"),
    )


# ═══════════════════════════════════════════════════════════════
# Productos (Inventario)
# ═══════════════════════════════════════════════════════════════


class Product(Base):
    """Maestro de productos del inventario.

    F0-010: wholesale_price, wholesale_min_qty, retail_price, barcode.
    F0-009: category_id FK → product_categories.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_of_measure: Mapped[str] = mapped_column(
        String(10), nullable=False, default="kg"
    )  # kg, unidad, litro, etc.
    current_stock: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    average_cost: Mapped[float] = mapped_column(
        Numeric(12, 4), default=0, nullable=False
    )  # Costo promedio ponderado
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # F0-009: Categoría de producto
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    # F0-010: Precios
    retail_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    wholesale_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    wholesale_min_qty: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════
# Movimientos de Kárdex
# ═══════════════════════════════════════════════════════════════


class KardexMovement(Base):
    """
    Tarjeta de existencia valorizada — cada línea es un movimiento.
    Método: Promedio Ponderado.
    """

    __tablename__ = "kardex_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # 'entrada' | 'salida' | 'ajuste'
    concept: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # Compra / Venta / Ajuste / Merma
    reference_type: Mapped[str | None] = mapped_column(
        String(30)
    )  # 'compra' | 'venta' | 'inventario_inicial'
    reference_id: Mapped[int | None] = mapped_column(Integer)  # ID del documento origen
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_avg_cost: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    balance_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        Index("idx_kardex_product_date", "product_id", "date"),
    )


# ═══════════════════════════════════════════════════════════════
# Proyecciones de Flujo de Caja (HU-F1-008)
# ═══════════════════════════════════════════════════════════════


class CashflowProjection(Base):
    """Proyección mensual de flujo de caja persistida en DB."""

    __tablename__ = "cashflow_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    concept: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # income | expense
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "year", "month", "concept",
            name="uq_cashflow_projection"
        ),
        Index("idx_cf_proj_company_year", "company_id", "year"),
    )
