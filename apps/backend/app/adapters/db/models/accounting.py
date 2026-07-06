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
    __table_args__ = (
        UniqueConstraint('code', name='uq_accounts_code'),
    )

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
    tenant_id: Mapped[int] = mapped_column(
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

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value

    __table_args__ = (
        Index("idx_journal_entries_tenant_date", "tenant_id", "date"),
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


class ProductCategory(Base):
    """Categoría de producto (F0-009).

    Tabla creada por migration 0008_product_categories_pricing.
    La migración incluye: description, parent_id, active, sort_order.
    Si alguna columna no existe en BD, se omiten campos opcionales.
    """

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    def get_table_columns(cls) -> list[str]:
        """Retorna los nombres de columnas que realmente existen en BD."""
        return [c.name for c in cls.__table__.columns]


class Product(Base):
    """Maestro de productos del inventario.

    F0-010: wholesale_price, wholesale_min_qty, retail_price, barcode.
    F0-009: category_id FK → product_categories.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
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
    # F0-009: Seriales + garantía
    has_serial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warranty_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relación a unidades serializadas
    serial_units: Mapped[list["ProductUnit"]] = relationship(
        "ProductUnit", back_populates="product", lazy="dynamic"
    )

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value


# ═══════════════════════════════════════════════════════════════
# Unidades Serializadas (F0-009)
# ═══════════════════════════════════════════════════════════════


class ProductUnit(Base):
    """Unidad individual de producto con número de serie.

    Cada fila representa una unidad física con trazabilidad completa:
      - Registro (compra)
      - Venta (sale_id + sale_item_id)
      - Anulación (vuelve a available)
      - Garantía (warranty_expiry)

    status values:
      - available: disponible para venta
      - sold: vendida
      - reserved: reservada temporalmente (futuro)
      - damaged: dañada / merma
      - voided: anulada (devolución)
    """

    __tablename__ = "product_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    serial_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )  # available | sold | reserved | damaged | voided
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    warranty_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True
    )
    sale_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sale_items.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relaciones
    product: Mapped["Product"] = relationship("Product", back_populates="serial_units")

    __table_args__ = (
        Index("idx_product_units_product_status", "product_id", "status"),
        Index("idx_product_units_sale", "sale_id"),
        Index("idx_product_units_warranty_expiry", "warranty_expiry"),
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
    tenant_id: Mapped[int] = mapped_column(
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

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "year", "month", "concept",
            name="uq_cashflow_projection"
        ),
        Index("idx_cf_proj_tenant_year", "tenant_id", "year"),
    )
