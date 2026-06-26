"""HU-F1-001: business_type enum en Company + data migration

Revision ID: 0003_business_type
Revises: 0002_users_auth
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_business_type"
down_revision: Union[str, None] = "0002_users_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Añadir columna con DEFAULT ──────────────────────
    op.add_column(
        "companies",
        sa.Column(
            "business_type",
            sa.String(20),
            nullable=False,
            server_default="restaurant",
        ),
    )

    # ─── Agregar CHECK constraint ────────────────────────
    op.create_check_constraint(
        "ck_companies_business_type",
        "companies",
        "business_type IN ('restaurant', 'hardware', 'retail', 'service')",
    )

    # ─── Data migration: inferir business_type desde economic_activity ──
    op.execute("""
        UPDATE companies
        SET business_type = CASE
            WHEN economic_activity ILIKE '%restaurante%' THEN 'restaurant'
            WHEN economic_activity ILIKE '%restaurant%' THEN 'restaurant'
            WHEN economic_activity ILIKE '%ferreter%' THEN 'hardware'
            WHEN economic_activity ILIKE '%comerci%' THEN 'retail'
            WHEN economic_activity ILIKE '%servicio%' THEN 'service'
            ELSE 'retail'
        END
        WHERE business_type = 'restaurant'
    """)


def downgrade() -> None:
    op.drop_constraint("ck_companies_business_type", "companies")
    op.drop_column("companies", "business_type")