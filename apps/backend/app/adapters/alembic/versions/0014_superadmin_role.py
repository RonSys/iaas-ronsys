"""Add superadmin role, make tenant_id nullable

Revision ID: 0014_superadmin_role
Revises: 0013_investment_items
Create Date: 2026-06-02

FEATURE: Superadmin
- Añade rol 'superadmin' al CHECK constraint de users.role
- Hace tenant_id nullable (superadmin no pertenece a ningún tenant)
- Hace tenant_id nullable en refresh_tokens
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_superadmin_role"
down_revision: Union[str, None] = "0013_investment_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. Hacer tenant_id nullable en users ──────────────
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default=None,
    )

    # ─── 2. Hacer tenant_id nullable en refresh_tokens ─────
    op.alter_column(
        "refresh_tokens",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default=None,
    )

    # ─── 3. Actualizar CHECK constraint de role ────────────
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        sa.text("role IN ('superadmin', 'admin', 'manager', 'operator', 'viewer')"),
    )


def downgrade() -> None:
    # ─── 1. Revertir CHECK constraint ──────────────────────
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        sa.text("role IN ('admin', 'manager', 'operator', 'viewer')"),
    )

    # ─── 2. Rehacer tenant_id NOT NULL en refresh_tokens ───
    op.alter_column(
        "refresh_tokens",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
        existing_server_default=None,
    )

    # ─── 3. Rehacer tenant_id NOT NULL en users ────────────
    # Asignar tenant por defecto a superadmins antes de hacer NOT NULL
    op.execute("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL")
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
        existing_server_default=None,
    )
