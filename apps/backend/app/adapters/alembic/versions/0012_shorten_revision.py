"""QA Post-Deploy: Empty bridge migration — asegura revision IDs ≤ 32 chars.

No altera tablas. Sirve como marcador para que todas las migraciones
futuras tengan revision IDs que quepan en alembic_version.version_num VARCHAR(32).

Contexto:
  - 0009_product_categories (antes 0009_product_categories_wholesale, 33 chars)
    fue renombrado a ≤32 chars en el source. DBs existentes usan ALTER TABLE
    alembic_version ALTER COLUMN version_num TYPE VARCHAR(255) como fix permanente.
  - Esta migración garantiza que la cadena continúa con IDs cortos.

Revision ID: 0012_shorten_revision
Revises: 0011_role_permissions
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0012_shorten_revision"
down_revision: Union[str, None] = "0011_role_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: solo establece un revision ID corto en la cadena."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
