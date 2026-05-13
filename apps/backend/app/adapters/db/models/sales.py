"""
Modelos ORM — Ventas + POS + Especialización (HU-F2-001, HU-F2-002).

Tablas:
  - pos_sessions:       Sesiones de caja (apertura/cierre)
  - sales:              Ventas (cabecera)
  - sale_items:         Ítems de venta
  - sale_payments:      Métodos de pago
  - restaurant_sales:   Especialización restaurante (1:1 con sales)
  - hardware_sales:     Especialización ferretería (1:1 con sales)
"""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base


# ═══════════════════════════════════════════════════════════════
# Sesiones POS
# ═══════════════════════════════════════════════════════════════


class PosSession(Base):
    """Turno de caja (apertura y cierre)."""

    __tablename__ = "pos_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opening_cash: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    closing_cash: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_cash: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    difference: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="open"
    )  # open | closed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relaciones
    sales: Mapped[list["Sale"]] = relationship(
        "Sale", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PosSession(id={self.id}, status={self.status})>"


# ═══════════════════════════════════════════════════════════════
# Ventas
# ═══════════════════════════════════════════════════════════════


class Sale(Base):
    """Venta — cabecera del comprobante."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    sale_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )  # VEN-YYYY-NNNNN
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sale_time: Mapped[time] = mapped_column(
        Time, server_default=func.now(), nullable=False
    )
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_doc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    tax_total: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    tip_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    business_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # restaurant | hardware | retail | service
    is_voided: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    void_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    journal_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    session: Mapped["PosSession"] = relationship("PosSession", back_populates="sales")
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    payments: Mapped[list["SalePayment"]] = relationship(
        "SalePayment", back_populates="sale", cascade="all, delete-orphan"
    )
    restaurant_sale: Mapped["RestaurantSale | None"] = relationship(
        "RestaurantSale", back_populates="sale", cascade="all, delete-orphan",
        uselist=False,
    )
    hardware_sale: Mapped["HardwareSale | None"] = relationship(
        "HardwareSale", back_populates="sale", cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_sales_company_date", "company_id", "sale_date"),
    )

    def __repr__(self) -> str:
        return f"<Sale(id={self.id}, number={self.sale_number})>"


# ═══════════════════════════════════════════════════════════════
# Ítems de Venta
# ═══════════════════════════════════════════════════════════════


class SaleItem(Base):
    """Ítem / línea de una venta."""

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="product"
    )  # product | service | combo
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(
        String(10), nullable=False, default="unidad"
    )
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    tax_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    kardex_movement_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relaciones
    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")

    def __repr__(self) -> str:
        return f"<SaleItem(id={self.id}, name={self.item_name}, qty={self.quantity})>"


# ═══════════════════════════════════════════════════════════════
# Pagos de Venta
# ═══════════════════════════════════════════════════════════════


class SalePayment(Base):
    """Método de pago asociado a una venta."""

    __tablename__ = "sale_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # cash | card | yape | plin | transfer
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relaciones
    sale: Mapped["Sale"] = relationship("Sale", back_populates="payments")

    def __repr__(self) -> str:
        return f"<SalePayment(id={self.id}, method={self.payment_method}, amt={self.amount})>"


# ═══════════════════════════════════════════════════════════════
# Especialización: Restaurante (HU-F2-002)
# ═══════════════════════════════════════════════════════════════


class RestaurantSale(Base):
    """Datos específicos de una venta de restaurante (1:1 con Sale)."""

    __tablename__ = "restaurant_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    table_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    guests: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="dine_in"
    )  # dine_in | takeout | delivery
    waiter_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tip_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tip_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    kitchen_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    sale: Mapped["Sale"] = relationship("Sale", back_populates="restaurant_sale")

    def __repr__(self) -> str:
        return f"<RestaurantSale(id={self.id}, table={self.table_number})>"


# ═══════════════════════════════════════════════════════════════
# Especialización: Ferretería (HU-F2-002)
# ═══════════════════════════════════════════════════════════════


class HardwareSale(Base):
    """Datos específicos de una venta de ferretería (1:1 con Sale)."""

    __tablename__ = "hardware_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    invoice_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="boleta"
    )  # boleta | factura
    delivery_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    requires_install: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    warranty_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Relaciones
    sale: Mapped["Sale"] = relationship("Sale", back_populates="hardware_sale")

    def __repr__(self) -> str:
        return f"<HardwareSale(id={self.id}, invoice={self.invoice_type})>"