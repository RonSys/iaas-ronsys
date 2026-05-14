"""HU-F0-001: Multitenant estandarización — Add tenant_id column + sync

Estrategia:
  - Agregar columna `tenant_id` a tablas que ya tienen `company_id`
  - Poblar `tenant_id` con los mismos valores que `company_id`
  - Mantener `company_id` para backward compatibility (deprecado)
  - Nuevos modelos deben usar `tenant_id` como FK
  - Middleware acepta X-Tenant-ID header y JWT company_id como fallback

Tablas afectadas: journal_entries, products, cashflow_projections,
                   pos_sessions, sales, users, refresh_tokens, scenarios

Revision ID: 0007_multitenant_standardization
Revises: 0006_scenarios
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_multitenant_standardization"
down_revision: Union[str, None] = "0006_scenarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_tenant_id_column(table: str, ts_type=sa.Integer):
    """Agrega tenant_id, lo puebla desde company_id, y lo hace NOT NULL."""
    op.add_column(table, sa.Column("tenant_id", ts_type, nullable=True))
    op.execute(f'UPDATE "{table}" SET tenant_id = company_id')
    op.alter_column(table, "tenant_id", nullable=False)
    op.create_foreign_key(
        f"fk_{table}_tenant_id", table, "companies",
        ["tenant_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(f"idx_{table}_tenant_id", table, ["tenant_id"])


def _drop_tenant_id(table: str):
    """Elimina tenant_id de la tabla."""
    op.drop_index(f"idx_{table}_tenant_id", table_name=table)
    op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
    op.drop_column(table, "tenant_id")


def upgrade() -> None:
    # Tablas existentes con company_id → agregar tenant_id
    _add_tenant_id_column("journal_entries")
    _add_tenant_id_column("products")
    _add_tenant_id_column("cashflow_projections")
    _add_tenant_id_column("pos_sessions")
    _add_tenant_id_column("sales")
    _add_tenant_id_column("users")
    _add_tenant_id_column("refresh_tokens")
    _add_tenant_id_column("scenarios")

    # Index for sales on tenant_id + date
    op.create_index("idx_sales_tenant_date", "sales", ["tenant_id", "sale_date"])


def downgrade() -> None:
    op.drop_index("idx_sales_tenant_date", table_name="sales")
    _drop_tenant_id("scenarios")
    _drop_tenant_id("refresh_tokens")
    _drop_tenant_id("users")
    _drop_tenant_id("sales")
    _drop_tenant_id("pos_sessions")
    _drop_tenant_id("cashflow_projections")
    _drop_tenant_id("products")
    _drop_tenant_id("journal_entries")
