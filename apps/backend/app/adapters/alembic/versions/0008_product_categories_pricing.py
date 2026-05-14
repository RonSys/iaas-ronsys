"""F0-009 + F0-010: Product categories + wholesale pricing + barcode

Migration:
  - product_categories table (tenant-scoped, with parent_id for future hierarchy)
  - products.category_id FK → product_categories
  - products.retail_price, wholesale_price, wholesale_min_qty, barcode columns

Revision ID: 0008_product_categories_pricing
Revises: 0007_restaurant_tables
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_product_categories_pricing"
down_revision: Union[str, None] = "0007_restaurant_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── product_categories ───────────────────────────────────
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_product_category_tenant_name"),
    )
    op.create_index("idx_product_categories_tenant", "product_categories", ["tenant_id"])

    # ─── products: category_id FK ─────────────────────────────
    op.add_column("products", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_products_category_id", "products", "product_categories",
        ["category_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("idx_products_category", "products", ["category_id"])

    # ─── products: retail_price, wholesale pricing, barcode ───
    op.add_column("products", sa.Column("retail_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("wholesale_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("wholesale_min_qty", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("barcode", sa.String(50), nullable=True))
    op.create_unique_constraint("uq_products_barcode", "products", ["barcode"])


def downgrade() -> None:
    op.drop_constraint("uq_products_barcode", "products", type_="unique")
    op.drop_column("products", "barcode")
    op.drop_column("products", "wholesale_min_qty")
    op.drop_column("products", "wholesale_price")
    op.drop_column("products", "retail_price")
    op.drop_constraint("fk_products_category_id", "products", type_="foreignkey")
    op.drop_index("idx_products_category", table_name="products")
    op.drop_column("products", "category_id")
    op.drop_table("product_categories")
