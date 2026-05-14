"""
🍽️ Modelos ORM — Restaurante (F0-003).

Tablas:
  - tables:          Mesas del salón
  - menu_items:      Ítems del menú/carta
  - menu_modifiers:  Modificadores (ej: "Sin cebolla", "Extra queso")
  - kitchen_orders:  Comandas enviadas a cocina
  - takeaway_orders: Pedidos para llevar
  - promotions:      Promociones (combos, descuentos, BOGOF)
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base


# ═══════════════════════════════════════════════════════════════
# Mesa del salón
# ═══════════════════════════════════════════════════════════════

class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(10), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )  # available | occupied | reserved | cleaning
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    waiter_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_table_tenant_number"),
        Index("idx_tables_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'cleaning')",
            name="ck_tables_status",
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Ítem del Menú
# ═══════════════════════════════════════════════════════════════

class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="food"
    )  # food | beverage | dessert | combo
    modifiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_menu_items_tenant_category", "tenant_id", "category"),
    )


# ═══════════════════════════════════════════════════════════════
# Modificador de ítem del Menú
# ═══════════════════════════════════════════════════════════════

class MenuModifier(Base):
    __tablename__ = "menu_modifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price_adjustment: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    max_select: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════
# Comanda de Cocina
# ═══════════════════════════════════════════════════════════════

class KitchenOrder(Base):
    __tablename__ = "kitchen_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    table_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | preparing | ready | delivered | cancelled
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_kitchen_orders_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'delivered', 'cancelled')",
            name="ck_ko_status",
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Pedido TakeAway
# ═══════════════════════════════════════════════════════════════

class TakeawayOrder(Base):
    __tablename__ = "takeaway_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    pickup_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | preparing | ready | picked_up | cancelled
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_takeaway_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'picked_up', 'cancelled')",
            name="ck_to_status",
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Promoción
# ═══════════════════════════════════════════════════════════════

class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    promo_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # combo | discount_pct | discount_fixed | bogof
    rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_promotions_tenant_active", "tenant_id", "active"),
        CheckConstraint(
            "promo_type IN ('combo', 'discount_pct', 'discount_fixed', 'bogof')",
            name="ck_promotions_type",
        ),
    )
