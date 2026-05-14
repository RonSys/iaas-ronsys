"""F0-003: Tablas Restaurante — tables, menu_items, menu_modifiers,
kitchen_orders, takeaway_orders, promotions

Revision ID: 0007_restaurant_tables
Revises: 0006_scenarios
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_restaurant_tables"
down_revision: Union[str, None] = "0006_scenarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── tables ───────────────────────────────────────────────
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.String(10), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("section", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "number", name="uq_table_tenant_number"),
        sa.CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'cleaning')",
            name="ck_tables_status",
        ),
    )
    op.create_index("idx_tables_tenant_status", "tables", ["tenant_id", "status"])

    # ─── menu_items ───────────────────────────────────────────
    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False, server_default="food"),
        sa.Column("modifiers", postgresql.JSONB, nullable=True),
        sa.Column("image_url", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_menu_items_tenant_category", "menu_items", ["tenant_id", "category"])

    # ─── menu_modifiers ───────────────────────────────────────
    op.create_table(
        "menu_modifiers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("price_adjustment", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("idx_modifiers_menu_item", "menu_modifiers", ["menu_item_id"])

    # ─── kitchen_orders ───────────────────────────────────────
    op.create_table(
        "kitchen_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("items", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'delivered', 'cancelled')",
            name="ck_ko_status",
        ),
    )
    op.create_index("idx_kitchen_orders_tenant_status", "kitchen_orders", ["tenant_id", "status"])

    # ─── takeaway_orders ──────────────────────────────────────
    op.create_table(
        "takeaway_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("items", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pickup_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'picked_up', 'cancelled')",
            name="ck_to_status",
        ),
    )
    op.create_index("idx_takeaway_tenant_status", "takeaway_orders", ["tenant_id", "status"])

    # ─── promotions ───────────────────────────────────────────
    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("promo_type", sa.String(20), nullable=False),
        sa.Column("rules", postgresql.JSONB, nullable=True),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "promo_type IN ('combo', 'discount_pct', 'discount_fixed', 'bogof')",
            name="ck_promotions_type",
        ),
    )
    op.create_index("idx_promotions_tenant_active", "promotions", ["tenant_id", "active"])


def downgrade() -> None:
    op.drop_table("promotions")
    op.drop_table("takeaway_orders")
    op.drop_table("kitchen_orders")
    op.drop_table("menu_modifiers")
    op.drop_table("menu_items")
    op.drop_table("tables")
