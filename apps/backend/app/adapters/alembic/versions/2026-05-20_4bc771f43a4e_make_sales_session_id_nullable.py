"""make_sales_session_id_nullable

Revision ID: 4bc771f43a4e
Revises: 0010_product_categories_missing_columns
Create Date: 2026-05-20 03:10:25.906798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bc771f43a4e'
down_revision: Union[str, Sequence[str], None] = '0010_product_categories_missing_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make sales.session_id nullable for Phase 1 sales without POS session."""
    op.alter_column('sales', 'session_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    """Revert: sales.session_id NOT NULL."""
    op.alter_column('sales', 'session_id',
               existing_type=sa.INTEGER(),
               nullable=False)
