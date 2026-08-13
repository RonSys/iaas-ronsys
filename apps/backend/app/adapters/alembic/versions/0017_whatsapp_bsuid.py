"""Spec 04 (F1 — WhatsApp en Vivo, D3): columna BSUID en delivery_orders.

Meta exige registrar el `user_id`/BSUID de cada usuario desde el día 1
(cumplimiento usernames/BSUID, vigente desde 31-mar-2026). La columna es
nullable: se persiste cuando el payload del evento de notificación lo trae
(el webhook de recepción que lo produce es F3 — fuera de alcance F1, D7).

Columna nueva:
  - delivery_orders.whatsapp_bsuid  varchar(64), nullable
    Identificador BSUID de Meta (nunca reemplaza a customer_phone, R-F1.6).

Revision ID: 0017_whatsapp_bsuid
Revises: 0016_delivery
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_whatsapp_bsuid"
down_revision: Union[str, Sequence[str], None] = "0016_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # D3: BSUID desde el día 1 — nullable, se completa vía payload de eventos.
    op.execute(
        "ALTER TABLE delivery_orders "
        "ADD COLUMN IF NOT EXISTS whatsapp_bsuid VARCHAR(64)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE delivery_orders DROP COLUMN IF EXISTS whatsapp_bsuid")
