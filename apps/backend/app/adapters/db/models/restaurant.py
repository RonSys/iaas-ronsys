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
# Sección del salón
# ═══════════════════════════════════════════════════════════════

class RestaurantSection(Base):
    __tablename__ = "restaurant_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_section_tenant_name"),
        Index("idx_sections_tenant_sort", "tenant_id", "sort_order"),
    )

    def __repr__(self):
        return f"<RestaurantSection #{self.id}: {self.name}>"


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
    section_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_sections.id", ondelete="SET NULL"), nullable=True
    )
    guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    waiter_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    section_rel = relationship("RestaurantSection", back_populates="tables")

    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_table_tenant_number"),
        Index("idx_tables_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'cleaning')",
            name="ck_tables_status",
        ),
    )


# Add back_populates on RestaurantSection
RestaurantSection.tables = relationship("Table", back_populates="section_rel", lazy="dynamic")


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
    preparation_area: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="cocina"
    )  # cocina | barra | none
    modifiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relación a receta (Caso 6)
    recipe = relationship("Recipe", back_populates="menu_item", uselist=False)

    __table_args__ = (
        Index("idx_menu_items_tenant_category", "tenant_id", "category"),
    )


# ═══════════════════════════════════════════════════════════════
# Modificador de ítem del Menú
# ═══════════════════════════════════════════════════════════════

class Recipe(Base):
    """Receta — insumos que componen un plato del menú (Caso 6).

    Solo los menu_items con preparation_area='cocina' pueden tener receta.
    """

    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    menu_item = relationship("MenuItem", back_populates="recipe")
    ingredients = relationship(
        "RecipeIngredient", back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.sort_order",
    )

    def __repr__(self):
        return f"<Recipe #{self.id} for menu_item #{self.menu_item_id}>"


class RecipeIngredient(Base):
    """Ingrediente individual de una receta (Caso 6)."""

    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1)
    unit_of_measure: Mapped[str] = mapped_column(String(10), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relaciones
    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship("Product")

    def __repr__(self):
        return f"<RecipeIngredient #{self.id} product=#{self.product_id} qty={self.quantity}>"


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


# ═══════════════════════════════════════════════════════════════
# Inversión / Puesta en Marcha (Caso 7)
# ═══════════════════════════════════════════════════════════════

class InvestmentItem(Base):
    """Bien de inversión para la puesta en marcha (Caso 7)."""

    __tablename__ = "investment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    actual_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    receipt_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | acquired
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_investment_tenant_category", "tenant_id", "category"),
        Index("idx_investment_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "estimated_cost >= 0",
            name="ck_investment_estimated_cost",
        ),
        CheckConstraint(
            "actual_cost IS NULL OR actual_cost >= 0",
            name="ck_investment_actual_cost",
        ),
        CheckConstraint(
            "status IN ('pending', 'acquired')",
            name="ck_investment_status",
        ),
        CheckConstraint(
            "category IN ('infraestructura', 'mobiliario', 'equipamiento_cocina', 'instalaciones', 'vestimenta', 'dyl', 'tecnologia', 'marketing', 'gastos_operativos')",
            name="ck_investment_category",
        ),
    )

    def __repr__(self):
        return f"<InvestmentItem #{self.id}: {self.name} [{self.status}]>"
