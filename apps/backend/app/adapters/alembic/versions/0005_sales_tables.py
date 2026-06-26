"""HU-F2-001 + HU-F2-002: Tablas base de ventas + especialización

Revision ID: 0005_sales_tables
Revises: 0004_cashflow_projections
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_sales_tables"
down_revision: Union[str, None] = "0004_cashflow_projections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── pos_sessions ────────────────────────────────────
    op.create_table(
        "pos_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opened_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("opening_cash", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("closing_cash", sa.Numeric(12, 2), nullable=True),
        sa.Column("expected_cash", sa.Numeric(12, 2), nullable=True),
        sa.Column("difference", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_check_constraint(
        "ck_pos_sessions_status", "pos_sessions",
        "status IN ('open', 'closed')"
    )

    # ─── sales ───────────────────────────────────────────
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("pos_sessions.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sale_number", sa.String(30), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("sale_time", sa.Time(), server_default=sa.func.now(), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("customer_doc", sa.String(20), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("tip_amount", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("business_type", sa.String(20), nullable=False),
        sa.Column("is_voided", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("void_reason", sa.String(300), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_sales_company_date", "sales", ["company_id", "sale_date"])
    op.create_index("idx_sales_session", "sales", ["session_id"])
    op.create_unique_constraint("uq_sale_number", "sales", ["sale_number"])

    # ─── sale_items ──────────────────────────────────────
    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False, server_default="product"),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_of_measure", sa.String(10), nullable=False, server_default="unidad"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, default=0),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("tax_pct", sa.Numeric(5, 2), nullable=False, default=0),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("kardex_movement_id", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_sale_items_item_type", "sale_items",
        "item_type IN ('product', 'service', 'combo')"
    )
    op.create_index("idx_sale_items_sale", "sale_items", ["sale_id"])

    # ─── sale_payments ───────────────────────────────────
    op.create_table(
        "sale_payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
    )
    op.create_check_constraint(
        "ck_sale_payments_method", "sale_payments",
        "payment_method IN ('cash', 'card', 'yape', 'plin', 'transfer')"
    )
    op.create_index("idx_sale_payments_sale", "sale_payments", ["sale_id"])

    # ─── restaurant_sales (HU-F2-002) ────────────────────
    op.create_table(
        "restaurant_sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("table_number", sa.String(10), nullable=True),
        sa.Column("guests", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_type", sa.String(20), nullable=False, server_default="dine_in"),
        sa.Column("waiter_name", sa.String(100), nullable=True),
        sa.Column("tip_amount", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("tip_pct", sa.Numeric(5, 2), nullable=False, default=0),
        sa.Column("kitchen_notes", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_restaurant_order_type", "restaurant_sales",
        "order_type IN ('dine_in', 'takeout', 'delivery')"
    )

    # ─── hardware_sales (HU-F2-002) ──────────────────────
    op.create_table(
        "hardware_sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("invoice_type", sa.String(20), nullable=False, server_default="boleta"),
        sa.Column("delivery_address", sa.String(300), nullable=True),
        sa.Column("requires_install", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("warranty_months", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_hardware_invoice_type", "hardware_sales",
        "invoice_type IN ('boleta', 'factura')"
    )


def downgrade() -> None:
    op.drop_table("hardware_sales")
    op.drop_table("restaurant_sales")
    op.drop_table("sale_payments")
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.drop_table("pos_sessions")