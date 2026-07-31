"""Caso 6b (Spec 01 v0.2): Explosión de recetas.

- sale_items.menu_item_id (nullable FK → menu_items ON DELETE SET NULL)
- menu_items.preparation_area (materializa columna del modelo; default 'cocina')

Revision ID: 0015_recipes_sale_items
Revises: 0014_superadmin_role
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_recipes_sale_items"
down_revision: Union[str, Sequence[str], None] = "0014_superadmin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── menu_items.preparation_area (falta en BD; el modelo ya lo define) ──
    op.execute(
        "ALTER TABLE menu_items "
        "ADD COLUMN IF NOT EXISTS preparation_area VARCHAR(20) NOT NULL DEFAULT 'cocina'"
    )

    # ─── sale_items.menu_item_id (para mapear plato → receta en la venta) ──
    op.add_column("sale_items", sa.Column("menu_item_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_sale_items_menu_item", "sale_items", "menu_items",
        ["menu_item_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("idx_sale_items_menu_item", "sale_items", ["menu_item_id"])


def downgrade() -> None:
    op.drop_index("idx_sale_items_menu_item", table_name="sale_items")
    op.drop_constraint("fk_sale_items_menu_item", "sale_items", type_="foreignkey")
    op.drop_column("sale_items", "menu_item_id")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS preparation_area")
