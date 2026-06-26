"""Users + Refresh Tokens — Auth Multi-Tenant

Revision ID: 0002_users_auth
Revises: 0001_initial
Create Date: 2026-05-10

US-02: Crea tablas users y refresh_tokens con seed de admin inicial.

IMPORTANTE: El admin seed tiene contraseña TEMPORAL.
Debe ser cambiada inmediatamente en producción.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Sequence, Union
import os
import sys

from alembic import op
import sqlalchemy as sa


revision: str = "0002_users_auth"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Users ────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.ForeignKeyConstraint(["tenant_id"], ["companies.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "role IN ('admin', 'manager', 'operator', 'viewer')",
            name="ck_users_role",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ─── Refresh Tokens ───────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("replaced_by_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_tokens.id"]),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_tokens_hash", "refresh_tokens", ["token_hash"])

    # ─── Seed: Admin inicial ──────────────────────────────
    _seed_admin(op)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("users")


def _seed_admin(op) -> None:
    """Crea el usuario admin inicial con contraseña temporal."""
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher

    ph = PasswordHash([Argon2Hasher()])
    temp_password = secrets.token_urlsafe(16)
    hashed = ph.hash(temp_password)

    now = datetime.now(UTC)
    expires = now + timedelta(days=365 * 10)  # 10 años — no expira

    users_table = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("full_name", sa.String),
        sa.column("role", sa.String),
        sa.column("tenant_id", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("is_verified", sa.Boolean),
        sa.column("failed_login_attempts", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "email": "admin@elsegoviano.pe",
                "hashed_password": hashed,
                "full_name": "Admin Principal",
                "role": "admin",
                "tenant_id": 1,
                "is_active": True,
                "is_verified": True,
                "failed_login_attempts": 0,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    # ⚠️  Security: imprimir contraseña temporal para cambio inmediato
    print("\n" + "=" * 60)
    print("  ⚠️  ADMIN SEED — CAMBIAR CONTRASEÑA INMEDIATAMENTE")
    print(f"  Email:    admin@elsegoviano.pe")
    print(f"  Password: {temp_password}")
    print(f"  Expira:   NUNCA (cambiar manualmente)")
    print("=" * 60 + "\n")
