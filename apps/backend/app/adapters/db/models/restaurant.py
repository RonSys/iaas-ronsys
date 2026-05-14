"""
Modelos ORM — Restaurante (HU-F0-003).

Tablas:
  - tables:               Mesas del salón
  - menu_items:           Ítems del menú/carta
  - menu_modifiers:       Modificadores de ítems (ej: "Sin huevo", "Extra queso")
  - kitchen_orders:       Comandas / pedidos a cocina
  - takeaway_orders:      Pedidos para llevar
  - promotions:           Promociones (combos, descuentos)
"""

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base


# ═══════════════════════════════════════════════════════════════
# Tables (Mesas del salón)
# ═══════════════════════════════════════════════════════════════


class Table(Base):
    """Mesa del salón. UNIQUE(tenant_id, number)."""

    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free"
    )  # free | occupied | reserved | closed
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    qr_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_table_tenant_number"),
        Index("idx_tables_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('free', 'occupied', 'reserved', 'closed')",
            name="ck_tables_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Table(id={self.id}, number={self.number}, status={self.status})>"


# ═══════════════════════════════════════════════════════════════
# Menu Items (Ítems del menú/carta)
# ═══════════════════════════════════════════════════════════════


class MenuItem(Base):
    """Ítem del menú (plato, bebida, entrada, postre)."""

    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="plato"
    )  # plato | porción | unidad | botella | vaso
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_modifiers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    modifiers: Mapped[list["MenuModifier"]] = relationship(
        "MenuModifier", back_populates="menu_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_menu_items_tenant_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name={self.name}, price={self.price})>"


class MenuModifier(Base):
    """Modificador de ítem del menú (ej: "Sin huevo", "Extra queso")."""

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

    # Relación inversa
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="modifiers")

    def __repr__(self) -> str:
        return f"<MenuModifier(id={self.id}, name={self.name}, adj={self.price_adjustment})>"


# ═══════════════════════════════════════════════════════════════
# Kitchen Orders (Comandas / Pedidos a cocina)
# ═══════════════════════════════════════════════════════════════


class KitchenOrder(Base):
    """Comanda / pedido enviado a cocina."""

    __tablename__ = "kitchen_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True
    )
    table_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    order_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="dine_in"
    )  # dine_in | takeaway | delivery
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | preparing | ready | served | cancelled
    items: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list
    )  # [{menu_item_id, name, quantity, modifiers, notes}]
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_kitchen_orders_tenant_status", "tenant_id", "status", "sent_at"),
        CheckConstraint(
            "order_type IN ('dine_in', 'takeaway', 'delivery')",
            name="ck_ko_order_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'served', 'cancelled')",
            name="ck_ko_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<KitchenOrder(id={self.id}, status={self.status}, type={self.order_type})>"


# ═══════════════════════════════════════════════════════════════
# Takeaway Orders (Pedidos para llevar)
# ═══════════════════════════════════════════════════════════════


class TakeawayOrder(Base):
    """Pedido takeaway (para llevar)."""

    __tablename__ = "takeaway_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | preparing | ready | picked_up | cancelled
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    pickup_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_takeaway_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'picked_up', 'cancelled')",
            name="ck_to_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<TakeawayOrder(id={self.id}, status={self.status})>"


# ═══════════════════════════════════════════════════════════════
# Promotions (Promociones)
# ═══════════════════════════════════════════════════════════════


class Promotion(Base):
    """Promoción: combos, descuentos fijos, porcentajes, happy hour."""

    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # combo | fixed_discount | percentage_discount | happy_hour
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    conditions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # {min_items, min_amount, applicable_categories, applicable_menu_item_ids}
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_promotions_tenant_active", "tenant_id", "active", "start_date", "end_date"),
        CheckConstraint(
            "type IN ('combo', 'fixed_discount', 'percentage_discount', 'happy_hour')",
            name="ck_promotions_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<Promotion(id={self.id}, name={self.name}, type={self.type})>"
