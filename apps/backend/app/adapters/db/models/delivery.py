"""
🛵 Modelos ORM — Módulo Delivery + Marketing (Fase A, Spec 02).

Alcance aprobado (Plan de Upgrade Dark Kitchen / Delivery nocturno):
  - delivery_zones:        Zonas de reparto (fee, pedido mínimo, ETA)
  - couriers:              Repartidores (internos; user_id opcional)
  - marketing_campaigns:   Campañas de marketing digital (atribución UTM + ROAS)
  - delivery_orders:       Pedidos de delivery (1:1 con sales, tracking, estados)

Regla de oro (revisión técnica):
  - El pedido delivery crea un `Sale` directo con order_type="delivery"
    (NO se copia el patrón TakeawayOrder, que queda fuera de kárdex/contabilidad).
  - La integración con cocina se hace vía `KitchenOrder.sale_id` (ya existe),
    sin columna duplicada de kitchen_order aquí.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
# Zona de reparto
# ═══════════════════════════════════════════════════════════════

class DeliveryZone(Base):
    """Zona/área de cobertura de delivery con tarifa y ETA."""

    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Fase A: lista de distritos/áreas cubiertas (ej: ["Miraflores", "San Isidro"]).
    # Fase C: reemplazar por polígono geográfico (GeoJSON) para routing.
    districts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    min_order: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    eta_min: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    orders: Mapped[list["DeliveryOrder"]] = relationship(
        "DeliveryOrder", back_populates="zone"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_delivery_zone_tenant_name"),
        Index("idx_delivery_zones_tenant_active", "tenant_id", "active"),
        CheckConstraint("fee >= 0", name="ck_delivery_zones_fee"),
        CheckConstraint("min_order >= 0", name="ck_delivery_zones_min_order"),
        CheckConstraint("eta_min >= 0", name="ck_delivery_zones_eta_min"),
    )

    def __repr__(self) -> str:
        return f"<DeliveryZone #{self.id}: {self.name} fee={self.fee}>"


# ═══════════════════════════════════════════════════════════════
# Repartidor
# ═══════════════════════════════════════════════════════════════

class Courier(Base):
    """Repartidor interno (Fase A). user_id opcional si tiene cuenta en el ERP."""

    __tablename__ = "couriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle: Mapped[str | None] = mapped_column(String(50), nullable=True)  # moto | bicicleta | auto
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )  # available | on_delivery | offline
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    orders: Mapped[list["DeliveryOrder"]] = relationship(
        "DeliveryOrder", back_populates="courier"
    )

    __table_args__ = (
        Index("idx_couriers_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('available', 'on_delivery', 'offline')",
            name="ck_couriers_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Courier #{self.id}: {self.name} [{self.status}]>"


# ═══════════════════════════════════════════════════════════════
# Campaña de marketing digital
# ═══════════════════════════════════════════════════════════════

class MarketingCampaign(Base):
    """Campaña de marketing digital para atribución (UTM) y ROAS."""

    __tablename__ = "marketing_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="meta"
    )  # meta | google | tiktok | other
    # UTM esperados de la campaña (match con delivery_orders.utm al checkout)
    utm_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    spend: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )  # gasto real registrado → ROAS = GMV / spend
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    orders: Mapped[list["DeliveryOrder"]] = relationship(
        "DeliveryOrder", back_populates="campaign"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_campaign_tenant_name"),
        Index("idx_campaigns_tenant_active", "tenant_id", "active"),
        CheckConstraint("budget >= 0", name="ck_campaigns_budget"),
        CheckConstraint("spend >= 0", name="ck_campaigns_spend"),
    )

    def __repr__(self) -> str:
        return f"<MarketingCampaign #{self.id}: {self.name} [{self.channel}]>"


# ═══════════════════════════════════════════════════════════════
# Pedido de Delivery
# ═══════════════════════════════════════════════════════════════

class DeliveryOrder(Base):
    """Pedido de delivery — 1:1 con Sale (el Sale contabiliza kárdex + asientos).

    Estados (máquina de estados Fase A):
      received → preparing → ready → out_for_delivery → delivered
        └──────────┴──────────┴──────────┴────────────┘ → cancelled
    """

    __tablename__ = "delivery_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    zone_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("delivery_zones.id", ondelete="SET NULL"), nullable=True
    )
    courier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("couriers.id", ondelete="SET NULL"), nullable=True
    )
    campaign_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    tracking_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Spec 04 F1 (D3): BSUID/user_id de Meta — se persiste cuando el payload lo
    # trae; NUNCA reemplaza a customer_phone (R-F1.6). Webhook entrante es F3 (D7).
    whatsapp_bsuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_address: Mapped[str] = mapped_column(String(300), nullable=False)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    eta_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="received"
    )  # received | preparing | ready | out_for_delivery | delivered | cancelled
    # UTM capturados en el primer clic de la campaña (JSON: source/medium/campaign/term/content)
    utm: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamps de transición de estado (para SLAs y métricas de tiempo)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    out_for_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    zone: Mapped["DeliveryZone | None"] = relationship("DeliveryZone", back_populates="orders")
    courier: Mapped["Courier | None"] = relationship("Courier", back_populates="orders")
    campaign: Mapped["MarketingCampaign | None"] = relationship(
        "MarketingCampaign", back_populates="orders"
    )

    __table_args__ = (
        Index("idx_delivery_orders_tenant_status", "tenant_id", "status"),
        Index("idx_delivery_orders_tenant_created", "tenant_id", "created_at"),
        Index("idx_delivery_orders_campaign", "campaign_id"),
        CheckConstraint(
            "status IN ('received', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled')",
            name="ck_delivery_orders_status",
        ),
        CheckConstraint("fee >= 0", name="ck_delivery_orders_fee"),
    )

    def __repr__(self) -> str:
        return f"<DeliveryOrder #{self.id}: {self.tracking_code} [{self.status}]>"
