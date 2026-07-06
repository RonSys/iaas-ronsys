"""F0-009: Product units (serial tracking) + has_serial, warranty_months, manufacturer

Migration:
  - product_units table (serial tracking per product unit)
  - products.has_serial (Boolean DEFAULT FALSE)
  - products.warranty_months (Integer DEFAULT 0)
  - products.manufacturer (VARCHAR(100))

Product units stores individual serialized items with:
  - serial_number UNIQUE
  - status: available | sold | reserved | damaged | voided
  - warranty_expiry = purchase_date + product.warranty_months
  - sale_id / sale_item_id for traceability

Revision ID: 0009_product_units_and_serials
Revises: 0008_product_categories_pricing
Create Date: 2026-05-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_product_units_and_serials"
down_revision: Union[str, None] = "0008_product_categories_pricing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── product_units ────────────────────────────────────────
    op.create_table(
        "product_units",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(),
                  sa.ForeignKey("products.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="available"),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("cost_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        sa.Column("sale_id", sa.Integer(),
                  sa.ForeignKey("sales.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sale_item_id", sa.Integer(),
                  sa.ForeignKey("sale_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        # Unique constraint + indexes
        sa.UniqueConstraint("serial_number", name="uq_product_units_serial"),
        sa.Index("idx_product_units_product_status", "product_id", "status"),
        sa.Index("idx_product_units_sale", "sale_id"),
        sa.Index("idx_product_units_warranty_expiry", "warranty_expiry"),
    )

    # ─── products: has_serial, warranty_months, manufacturer ──
    op.add_column("products",
                  sa.Column("has_serial", sa.Boolean(), nullable=False,
                            server_default=sa.text("false")))
    op.add_column("products",
                  sa.Column("warranty_months", sa.Integer(), nullable=False,
                            server_default="0"))
    op.add_column("products",
                  sa.Column("manufacturer", sa.String(100), nullable=True))
    op.create_index("idx_products_has_serial", "products", ["has_serial"])


def downgrade() -> None:
    # ─── products: drop new columns ───────────────────────────
    op.drop_index("idx_products_has_serial", table_name="products")
    op.drop_column("products", "manufacturer")
    op.drop_column("products", "warranty_months")
    op.drop_column("products", "has_serial")

    # ─── product_units: drop table ────────────────────────────
    op.drop_table("product_units")
