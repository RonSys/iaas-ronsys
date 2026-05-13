"""HU-F1-008: Persistencia proyecciones cashflow

Revision ID: 0004_cashflow_projections
Revises: 0003_business_type
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_cashflow_projections"
down_revision: Union[str, None] = "0003_business_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cashflow_projections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("concept", sa.String(100), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),  # income | expense
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("company_id", "year", "month", "concept", name="uq_cashflow_projection"),
    )
    op.create_index("idx_cf_proj_company_year", "cashflow_projections", ["company_id", "year"])


def downgrade() -> None:
    op.drop_table("cashflow_projections")