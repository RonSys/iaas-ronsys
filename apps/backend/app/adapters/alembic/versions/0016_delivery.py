"""Spec 02 (Fase A — MVP Delivery nocturno): módulo delivery + marketing.

Tablas nuevas:
  - delivery_zones        Zonas de reparto (fee, min_order, ETA)
  - couriers              Repartidores internos (user_id opcional)
  - marketing_campaigns   Campañas digitales (UTM + spend para ROAS)
  - delivery_orders       Pedidos delivery (1:1 con sales, tracking, estados)

Columnas nuevas:
  - menu_items.delivery_enabled / available_from / available_to / delivery_surcharge
  - companies.slug        (URL pública de la landing: /menu/{slug})

Regla de arquitectura: el pedido delivery crea un Sale directo
(order_type='delivery'); delivery_orders.sale_id es la única FK al motor
de ventas (kárdex + asientos automáticos).

Revision ID: 0016_delivery
Revises: 0015_recipes_sale_items
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016_delivery"
down_revision: Union[str, Sequence[str], None] = "0015_recipes_sale_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════
    # 1. delivery_zones
    # ═══════════════════════════════════════════════════════════
    op.create_table(
        "delivery_zones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("districts", postgresql.JSONB(), nullable=True),
        sa.Column("fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("min_order", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("eta_min", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint("fee >= 0", name="ck_delivery_zones_fee"),
        sa.CheckConstraint("min_order >= 0", name="ck_delivery_zones_min_order"),
        sa.CheckConstraint("eta_min >= 0", name="ck_delivery_zones_eta_min"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_delivery_zone_tenant_name"),
    )
    op.create_index(
        "idx_delivery_zones_tenant_active", "delivery_zones", ["tenant_id", "active"]
    )

    # ═══════════════════════════════════════════════════════════
    # 2. couriers
    # ═══════════════════════════════════════════════════════════
    op.create_table(
        "couriers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("vehicle", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('available', 'on_delivery', 'offline')",
            name="ck_couriers_status",
        ),
    )
    op.create_index("idx_couriers_tenant_status", "couriers", ["tenant_id", "status"])

    # ═══════════════════════════════════════════════════════════
    # 3. marketing_campaigns
    # ═══════════════════════════════════════════════════════════
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="meta"),
        sa.Column("utm_source", sa.String(50), nullable=True),
        sa.Column("utm_medium", sa.String(50), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("budget", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("spend", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint("budget >= 0", name="ck_campaigns_budget"),
        sa.CheckConstraint("spend >= 0", name="ck_campaigns_spend"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_campaign_tenant_name"),
    )
    op.create_index("idx_campaigns_tenant_active", "marketing_campaigns", ["tenant_id", "active"])

    # ═══════════════════════════════════════════════════════════
    # 4. delivery_orders
    # ═══════════════════════════════════════════════════════════
    op.create_table(
        "delivery_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "sale_id", sa.Integer(),
            sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True,
        ),
        sa.Column(
            "zone_id", sa.Integer(),
            sa.ForeignKey("delivery_zones.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "courier_id", sa.Integer(),
            sa.ForeignKey("couriers.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "campaign_id", sa.Integer(),
            sa.ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("tracking_code", sa.String(20), nullable=False, unique=True),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("customer_address", sa.String(300), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("eta_min", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("utm", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("out_for_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('received', 'preparing', 'ready', 'out_for_delivery', "
            "'delivered', 'cancelled')",
            name="ck_delivery_orders_status",
        ),
        sa.CheckConstraint("fee >= 0", name="ck_delivery_orders_fee"),
    )
    op.create_index(
        "idx_delivery_orders_tenant_status", "delivery_orders", ["tenant_id", "status"]
    )
    op.create_index(
        "idx_delivery_orders_tenant_created", "delivery_orders", ["tenant_id", "created_at"]
    )
    op.create_index("idx_delivery_orders_campaign", "delivery_orders", ["campaign_id"])

    # ═══════════════════════════════════════════════════════════
    # 5. menu_items: disponibilidad delivery (menú nocturno)
    # ═══════════════════════════════════════════════════════════
    op.execute(
        "ALTER TABLE menu_items "
        "ADD COLUMN IF NOT EXISTS delivery_enabled BOOLEAN NOT NULL DEFAULT true"
    )
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_from TIME")
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_to TIME")
    op.execute(
        "ALTER TABLE menu_items "
        "ADD COLUMN IF NOT EXISTS delivery_surcharge NUMERIC(10, 2) NOT NULL DEFAULT 0"
    )

    # ═══════════════════════════════════════════════════════════
    # 6. companies.slug (URL pública de la landing)
    # ═══════════════════════════════════════════════════════════
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS slug VARCHAR(100)")
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)

    # ═══════════════════════════════════════════════════════════
    # 7. Seed inicial (D2 + slug público — Spec 03 §3.2)
    # ═══════════════════════════════════════════════════════════
    # Zona 1 de lanzamiento: Montenegro / Motupe / Canto Grande (SJL).
    # Guarded: solo si no existe (idempotente ante re-ejecución).
    op.execute("""
        INSERT INTO delivery_zones
            (tenant_id, name, description, districts, fee, min_order, eta_min, active)
        SELECT 1, 'Montenegro / Motupe / Canto Grande',
               'Zona 1 de lanzamiento — radio cercano al local (SJL, límite Montenegro–Motupe)',
               '["Montenegro", "Motupe", "Canto Grande"]'::jsonb,
               5.00, 35.00, 35, true
        WHERE NOT EXISTS (
            SELECT 1 FROM delivery_zones
            WHERE tenant_id = 1 AND name = 'Montenegro / Motupe / Canto Grande'
        )
    """)
    # Slug público del tenant de operación (El Segoviano corre en tenant 1):
    # habilita la landing /menu/el-segoviano desde el día 1 sin configuración manual.
    op.execute("UPDATE companies SET slug = 'el-segoviano' WHERE id = 1 AND slug IS NULL")


def downgrade() -> None:
    # 7. Seed inicial
    op.execute("UPDATE companies SET slug = NULL WHERE id = 1 AND slug = 'el-segoviano'")
    op.execute(
        "DELETE FROM delivery_zones "
        "WHERE tenant_id = 1 AND name = 'Montenegro / Motupe / Canto Grande'"
    )

    # 6. companies.slug
    op.drop_index("ix_companies_slug", table_name="companies")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS slug")

    # 5. menu_items
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS delivery_surcharge")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS available_to")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS available_from")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS delivery_enabled")

    # 4. delivery_orders
    op.drop_index("idx_delivery_orders_campaign", table_name="delivery_orders")
    op.drop_index("idx_delivery_orders_tenant_created", table_name="delivery_orders")
    op.drop_index("idx_delivery_orders_tenant_status", table_name="delivery_orders")
    op.drop_table("delivery_orders")

    # 3. marketing_campaigns
    op.drop_index("idx_campaigns_tenant_active", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")

    # 2. couriers
    op.drop_index("idx_couriers_tenant_status", table_name="couriers")
    op.drop_table("couriers")

    # 1. delivery_zones
    op.drop_index("idx_delivery_zones_tenant_active", table_name="delivery_zones")
    op.drop_table("delivery_zones")
