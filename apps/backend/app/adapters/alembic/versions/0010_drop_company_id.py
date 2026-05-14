"""HU-F0-001 QA Fix: Drop company_id columns — unify to tenant_id

Elimina la columna company_id de todas las tablas donde coexistía con tenant_id.
Los datos ya fueron copiados de company_id → tenant_id en la migración 0007.

Tablas afectadas: journal_entries, products, cashflow_projections,
                   pos_sessions, sales, users, refresh_tokens, scenarios

Además renombra índices que usaban el sufijo "company" a "tenant".

Revision ID: 0010_drop_company_id
Revises: 0009_product_categories
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0010_drop_company_id"
down_revision: Union[str, None] = "0009_product_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_company_id_column(table: str, fk_name: str, old_index: str, new_index: str):
    """Elimina company_id y renombra índice si existe."""
    # Drop old index
    op.drop_index(old_index, table_name=table)
    # Drop FK constraint
    op.drop_constraint(fk_name, table, type_="foreignkey")
    # Drop column
    op.drop_column(table, "company_id")
    # Rename tenant_id index to include "tenant"
    op.create_index(new_index, table, ["tenant_id"])


def upgrade() -> None:
    # journal_entries: already has idx_journal_entries_tenant_date from model
    op.drop_index("idx_journal_entries_c_d", table_name="journal_entries")
    op.drop_constraint("journal_entries_company_id_fkey", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "company_id")

    # products
    op.drop_constraint("products_company_id_fkey", "products", type_="foreignkey")
    op.drop_column("products", "company_id")

    # cashflow_projections
    op.drop_index("idx_cf_proj_company_year", table_name="cashflow_projections")
    op.drop_constraint("cashflow_projections_company_id_fkey", "cashflow_projections", type_="foreignkey")
    op.drop_column("cashflow_projections", "company_id")
    op.create_index("idx_cf_proj_tenant_year", "cashflow_projections", ["tenant_id", "year"])

    # pos_sessions
    op.drop_constraint("pos_sessions_company_id_fkey", "pos_sessions", type_="foreignkey")
    op.drop_column("pos_sessions", "company_id")

    # sales
    op.drop_index("idx_sales_company_date", table_name="sales")
    op.drop_constraint("sales_company_id_fkey", "sales", type_="foreignkey")
    op.drop_column("sales", "company_id")

    # users
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_constraint("users_company_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "company_id")
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # refresh_tokens
    op.drop_constraint("refresh_tokens_company_id_fkey", "refresh_tokens", type_="foreignkey")
    op.drop_column("refresh_tokens", "company_id")

    # scenarios
    op.drop_index("ix_scenarios_company_id", table_name="scenarios")
    op.drop_constraint("scenarios_company_id_fkey", "scenarios", type_="foreignkey")
    op.drop_column("scenarios", "company_id")


def downgrade() -> None:
    import sqlalchemy as sa

    # Restaurar company_id en cada tabla (sin datos — los datos están en tenant_id)
    # Nota: en downgrade no podemos recuperar los datos originales de company_id
    # porque ya fueron sobrescritos. Se asume que tenant_id es la fuente de verdad.

    # scenarios
    op.add_column("scenarios", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("scenarios_company_id_fkey", "scenarios", "companies", ["company_id"], ["id"], ondelete="CASCADE")
    op.execute('UPDATE scenarios SET company_id = tenant_id')
    op.alter_column("scenarios", "company_id", nullable=False)
    op.create_index("ix_scenarios_company_id", "scenarios", ["company_id"])

    # refresh_tokens
    op.add_column("refresh_tokens", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("refresh_tokens_company_id_fkey", "refresh_tokens", "companies", ["company_id"], ["id"], ondelete="CASCADE")
    op.execute('UPDATE refresh_tokens SET company_id = tenant_id')
    op.alter_column("refresh_tokens", "company_id", nullable=False)

    # users
    op.add_column("users", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("users_company_id_fkey", "users", "companies", ["company_id"], ["id"], ondelete="CASCADE")
    op.execute('UPDATE users SET company_id = tenant_id')
    op.alter_column("users", "company_id", nullable=False)
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.drop_index("ix_users_tenant_id", table_name="users")

    # sales
    op.add_column("sales", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("sales_company_id_fkey", "sales", "companies", ["company_id"], ["id"])
    op.execute('UPDATE sales SET company_id = tenant_id')
    op.alter_column("sales", "company_id", nullable=False)
    op.create_index("idx_sales_company_date", "sales", ["company_id", "sale_date"])

    # pos_sessions
    op.add_column("pos_sessions", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("pos_sessions_company_id_fkey", "pos_sessions", "companies", ["company_id"], ["id"])
    op.execute('UPDATE pos_sessions SET company_id = tenant_id')
    op.alter_column("pos_sessions", "company_id", nullable=False)

    # cashflow_projections
    op.add_column("cashflow_projections", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("cashflow_projections_company_id_fkey", "cashflow_projections", "companies", ["company_id"], ["id"])
    op.execute('UPDATE cashflow_projections SET company_id = tenant_id')
    op.alter_column("cashflow_projections", "company_id", nullable=False)
    op.create_index("idx_cf_proj_company_year", "cashflow_projections", ["company_id", "year"])
    op.drop_index("idx_cf_proj_tenant_year", table_name="cashflow_projections")

    # products
    op.add_column("products", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("products_company_id_fkey", "products", "companies", ["company_id"], ["id"])
    op.execute('UPDATE products SET company_id = tenant_id')
    op.alter_column("products", "company_id", nullable=False)

    # journal_entries
    op.add_column("journal_entries", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key("journal_entries_company_id_fkey", "journal_entries", "companies", ["company_id"], ["id"])
    op.execute('UPDATE journal_entries SET company_id = tenant_id')
    op.alter_column("journal_entries", "company_id", nullable=False)
    op.create_index("idx_journal_entries_c_d", "journal_entries", ["company_id", "date"])
