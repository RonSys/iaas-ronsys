"""HU-F0-009 + HU-F0-010: Product categories + wholesale pricing

Revision ID: 0009_product_categories_wholesale
Revises: 0008_restaurant_tables
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_product_categories_wholesale"
down_revision: Union[str, None] = "0008_restaurant_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── product_categories (HU-F0-009) ───────────────────────
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_product_category_tenant_name"),
    )

    # ─── Agregar category_id a products (HU-F0-009) ──────────
    op.add_column(
        "products",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True),
    )

    # ─── Agregar wholesale columns a products (HU-F0-010) ────
    op.add_column(
        "products",
        sa.Column("wholesale_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("wholesale_min_qty", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("barcode", sa.String(50), nullable=True),
    )

    # ─── Índice para búsqueda por categoría ──────────────────
    op.create_index("idx_products_tenant_category", "products", ["tenant_id", "category_id"])


def downgrade() -> None:
    op.drop_index("idx_products_tenant_category", table_name="products")
    op.drop_column("products", "barcode")
    op.drop_column("products", "wholesale_min_qty")
    op.drop_column("products", "wholesale_price")
    op.drop_column("products", "category_id")
    op.drop_table("product_categories")
