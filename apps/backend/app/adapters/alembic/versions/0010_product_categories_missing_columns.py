"""Hotfix: Add missing columns to product_categories (if migration 0008 was incomplete)

Production may have migration 0008 applied before commit 96b4494 added
description, parent_id, sort_order, active columns.

This migration adds them with IF NOT EXISTS pattern.

Revision ID: 0010_product_categories_missing_columns
Revises: 0009_product_units_and_serials
Create Date: 2026-05-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_product_categories_missing_columns"
down_revision: Union[str, None] = "0009_product_units_and_serials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns that may be missing from an early 0008 application
    # Using op.execute to safely check existence before altering
    columns_to_check = [
        ("description", "ADD COLUMN IF NOT EXISTS description TEXT"),
        ("parent_id",
         "ADD COLUMN IF NOT EXISTS parent_id INTEGER "
         "REFERENCES product_categories(id) ON DELETE SET NULL"),
        ("active",
         "ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true"),
        ("sort_order",
         "ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0"),
    ]

    for col_name, alter_sql in columns_to_check:
        # PostgreSQL 9.6+ supports ADD COLUMN IF NOT EXISTS
        op.execute(f"ALTER TABLE product_categories {alter_sql}")

    # Ensure FK constraints and indexes exist (idempotent)
    try:
        op.create_index(
            "idx_product_categories_parent",
            "product_categories", ["parent_id"],
            if_not_exists=True,
        )
    except Exception:
        pass  # Index may already exist


def downgrade() -> None:
    # No downgrade for safety — these columns should exist in any correct schema
    pass
