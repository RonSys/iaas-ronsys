"""F0-018: Crear tabla role_permissions con PK no nullable

Crea la tabla role_permissions para mapeo de roles a permisos.
PK compuesta (role, permission) — ambas NOT NULL por diseño.

Revision ID: 0011_role_permissions
Revises: 0010_drop_company_id
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_role_permissions"
down_revision: Union[str, None] = "0010_drop_company_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("permission", sa.String(100), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("role", "permission"),
    )

    # Seed básico: admin tiene todos los permisos
    permissions = [
        ("admin", "users:read"),
        ("admin", "users:write"),
        ("admin", "settings:read"),
        ("admin", "settings:write"),
        ("admin", "accounting:read"),
        ("admin", "accounting:write"),
        ("admin", "inventory:read"),
        ("admin", "inventory:write"),
        ("admin", "sales:read"),
        ("admin", "sales:write"),
        ("admin", "pos:open"),
        ("admin", "pos:close"),
        ("admin", "reports:read"),
        ("manager", "users:read"),
        ("manager", "settings:read"),
        ("manager", "accounting:read"),
        ("manager", "inventory:read"),
        ("manager", "inventory:write"),
        ("manager", "sales:read"),
        ("manager", "sales:write"),
        ("manager", "pos:open"),
        ("manager", "pos:close"),
        ("manager", "reports:read"),
        ("operator", "inventory:read"),
        ("operator", "sales:read"),
        ("operator", "sales:write"),
        ("operator", "pos:open"),
        ("operator", "pos:close"),
        ("viewer", "accounting:read"),
        ("viewer", "inventory:read"),
        ("viewer", "sales:read"),
        ("viewer", "reports:read"),
    ]
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role", sa.String),
            sa.column("permission", sa.String),
            sa.column("description", sa.String),
        ),
        [
            {"role": r, "permission": p, "description": None}
            for r, p in permissions
        ],
    )


def downgrade() -> None:
    op.drop_table("role_permissions")
