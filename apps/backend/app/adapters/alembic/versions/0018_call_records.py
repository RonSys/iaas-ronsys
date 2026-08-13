"""Spec 05 (F2 — Central que No Pierde Llamadas, §3.2): tabla call_records.

Tabla nueva:
  - call_records        Registro por llamada (inbound/outbound) con
                        idempotencia por `external_call_id` (Uniqueid de
                        Asterisk / ORIGINATE_ID outbound).

Reglas (Spec 05 §3.2 / §3.7):
  - R8:  upsert por `external_call_id` (UNIQUE) — el adapter call-bridge es
         re-arrancable sin duplicar llamadas.
  - R6:  `converted_order_id` → delivery_orders (SET NULL) — 1 sola
         conversión por llamada (409 si ya existe).
  - R1:  `recording_path` nullable hasta call.recording_ready (MixMonitor).
  - `transcription_fk` RESERVADO (transcripción futura, fuera de alcance F2):
    columna int nullable SIN FK.
  - CHECKs: direction (inbound|outbound), status (ringing|in_progress|
    answered|missed|completed|failed), duration >= 0.

Solo adición de tabla: ninguna tabla existente se modifica (CA-F2.11).

Revision ID: 0018_call_records
Revises: 0017_whatsapp_bsuid
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0018_call_records"
down_revision: Union[str, Sequence[str], None] = "0017_whatsapp_bsuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("external_call_id", sa.String(64), nullable=False),
        sa.Column("caller", sa.String(32), nullable=False),
        sa.Column("callee", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="ringing",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recording_path", sa.Text(), nullable=True),
        sa.Column("transcription_fk", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "converted_order_id", sa.Integer(),
            sa.ForeignKey("delivery_orders.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.UniqueConstraint(
            "external_call_id", name="uq_call_records_external_call_id",
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')", name="ck_call_records_direction",
        ),
        sa.CheckConstraint(
            "status IN ('ringing', 'in_progress', 'answered', 'missed', 'completed', 'failed')",
            name="ck_call_records_status",
        ),
        sa.CheckConstraint("duration >= 0", name="ck_call_records_duration"),
    )
    op.create_index(
        "idx_call_records_tenant_status", "call_records", ["tenant_id", "status"]
    )
    op.create_index(
        "idx_call_records_tenant_started", "call_records", ["tenant_id", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_call_records_tenant_started", table_name="call_records")
    op.drop_index("idx_call_records_tenant_status", table_name="call_records")
    op.drop_table("call_records")
