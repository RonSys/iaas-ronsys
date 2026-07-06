"""merge_baseline

Revision ID: 4b731e20252e
Revises: 0000_baseline, 0012_recipes, 4bc771f43a4e
Create Date: 2026-05-27 07:04:32.677473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b731e20252e'
down_revision: Union[str, Sequence[str], None] = ('0000_baseline', '0012_recipes', '4bc771f43a4e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
