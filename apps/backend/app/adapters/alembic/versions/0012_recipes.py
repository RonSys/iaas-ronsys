"""Caso 6: Recetas e Insumos — recipes + recipe_ingredients tables.

Migration:
  - Crear tabla recipes (FK → menu_items, unique)
  - Crear tabla recipe_ingredients (FK → recipes, FK → products)
  - Índices necesarios

Revision ID: 0012_recipes
Revises: 0011_restaurant_sections
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0012_recipes"
down_revision: Union[str, None] = "0011_restaurant_sections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Crear tabla recipes ────────────────────────────────
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("menu_item_id", sa.Integer(),
                  sa.ForeignKey("menu_items.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_recipes_menu_item_id", "recipes", ["menu_item_id"],
    )

    # ─── Crear tabla recipe_ingredients ────────────────────
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(),
                  sa.ForeignKey("recipes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("product_id", sa.Integer(),
                  sa.ForeignKey("products.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("unit_of_measure", sa.String(10), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_recipe_ingredients_recipe_id", table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")
    op.drop_index("idx_recipes_menu_item_id", table_name="recipes")
    op.drop_table("recipes")
