"""HU-F0-003: Tablas Restaurante (tables, menu_items, menu_modifiers, kitchen_orders, takeaway_orders, promotions)

Revision ID: 0008_restaurant_tables
Revises: 0007_multitenant_standardization
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_restaurant_tables"
down_revision: Union[str, None] = "0007_multitenant_standardization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── tables ───────────────────────────────────────────────
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(20), nullable=False, server_default="free"),
        sa.Column("section", sa.String(50), nullable=True),
        sa.Column("qr_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "number", name="uq_table_tenant_number"),
        sa.CheckConstraint(
            "status IN ('free', 'occupied', 'reserved', 'closed')",
            name="ck_tables_status",
        ),
    )
    op.create_index("idx_tables_tenant_status", "tables", ["tenant_id", "status"])

    # ─── menu_items ───────────────────────────────────────────
    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="plato"),
        sa.Column("image_url", sa.String(255), nullable=True),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("has_modifiers", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_menu_items_tenant_category", "menu_items", ["tenant_id", "category"])

    # ─── menu_modifiers ───────────────────────────────────────
    op.create_table(
        "menu_modifiers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("price_adjustment", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── kitchen_orders ───────────────────────────────────────
    op.create_table(
        "kitchen_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_type", sa.String(20), nullable=False, server_default="dine_in"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("items", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "order_type IN ('dine_in', 'takeaway', 'delivery')",
            name="ck_ko_order_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'served', 'cancelled')",
            name="ck_ko_status",
        ),
    )
    op.create_index("idx_kitchen_orders_tenant_status", "kitchen_orders", ["tenant_id", "status", "sent_at"])

    # ─── takeaway_orders ──────────────────────────────────────
    op.create_table(
        "takeaway_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("items", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pickup_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
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
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("conditions", postgresql.JSONB, nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "type IN ('combo', 'fixed_discount', 'percentage_discount', 'happy_hour')",
            name="ck_promotions_type",
        ),
    )
    op.create_index("idx_promotions_tenant_active", "promotions", ["tenant_id", "active", "start_date", "end_date"])


def downgrade() -> None:
    op.drop_table("promotions")
    op.drop_table("takeaway_orders")
    op.drop_table("kitchen_orders")
    op.drop_table("menu_modifiers")
    op.drop_table("menu_items")
    op.drop_table("tables")
