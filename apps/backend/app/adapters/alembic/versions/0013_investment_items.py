"""Caso 7: Inversión / Puesta en Marcha — investment_items table.

Migration:
  - Crear tabla investment_items
  - Índices en tenant_id + category, tenant_id + status
  - Constraints: estimated_cost >= 0, actual_cost >= 0, status/válidos, categorías válidas

Revision ID: 0013_investment_items
Revises: 4b731e20252e
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_investment_items"
down_revision: Union[str, Sequence[str], None] = "4b731e20252e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("receipt_code", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_investment_tenant_category", "investment_items", ["tenant_id", "category"],
    )
    op.create_index(
        "idx_investment_tenant_status", "investment_items", ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_investment_tenant_status", table_name="investment_items")
    op.drop_index("idx_investment_tenant_category", table_name="investment_items")
    op.drop_table("investment_items")
