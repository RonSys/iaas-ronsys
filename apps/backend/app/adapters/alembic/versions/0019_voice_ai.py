"""Spec 06 (F3 — Recepcionista IA por Voz, §3.2): capa IA sobre call_records.

Adopta la tabla `call_records` de F2 (NO crea otra). Esta migración:

1) Columnas IA en `call_records` (F2 ya definió `transcription_fk` RESERVADA
   y `converted_order_id`):
     - ai_state         varchar(20)   — máquina de estados conversacional
       (§3.6): greeting|taking_order|clarifying|confirming|transfer|hangup
       + estados terminales de cierre `completed|failed` (POST /complete,
       contrato §3.5.1 — el CHECK se extiende para admitirlos).
     - transfer_reason  varchar(50)   — complaint|out_of_domain|
       low_confidence|user_requested|budget (D9, CHECK).
     - context_summary  text          — resumen incremental para el operador
       (D9): items capturados, dirección/zona, nombre/teléfono.
     - cost_usd         numeric(10,4) — STT+TTS+LLM acumulado de la llamada
       (R4, CHECK >= 0, default 0; filas previas quedan en 0 sin pérdida).

2) Tabla nueva `call_transcriptions` (D8/R3):
     - call_id = call_records.external_call_id (Uniqueid Asterisk, UNIQUE en
       F2) → la transcripción se persiste por idempotencia con el patrón de
       F2 (mismo `external_call_id` por llamada; upsert a nivel servicio).
     - `transcription_fk` (F2, hoy NULL) se actualiza al crear la
       transcripción → el detalle de la llamada en F2 la muestra sin cambio
       de contrato (CA-F3-3).
     - segments jsonb [{start, end, speaker, text, confidence}], lang
       default 'es-PE', cost_estimate = costo STT estimado (R4).

Reglas (Spec 06 §3.2 / §3.8):
  - CA-F3-13: `alembic upgrade head` → head = 0019_voice_ai;
    `downgrade 0018_call_records` revierte TODO lo de F3 sin tocar
    `call_records` de F2 (solo se agregan/eliminan columnas propias).
  - R8: aislamiento por tenant (FK companies ON DELETE CASCADE).

Revision ID: 0019_voice_ai
Revises: 0018_call_records
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0019_voice_ai"
down_revision: Union[str, Sequence[str], None] = "0018_call_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1) Columnas IA en call_records (Spec 06 §3.2) ─────────────
    op.add_column("call_records", sa.Column("ai_state", sa.String(20), nullable=True))
    op.add_column("call_records", sa.Column("transfer_reason", sa.String(50), nullable=True))
    op.add_column("call_records", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column(
        "call_records",
        sa.Column(
            "cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0",
        ),
    )
    # CHECKs de dominio a nivel de datos (HU-F3-10: 'hacking'/'other' → rechazados)
    op.create_check_constraint(
        "ck_call_records_ai_state", "call_records",
        "ai_state IN ('greeting','taking_order','clarifying','confirming',"
        "'transfer','hangup','completed','failed')",
    )
    op.create_check_constraint(
        "ck_call_records_transfer_reason", "call_records",
        "transfer_reason IN ('complaint','out_of_domain','low_confidence',"
        "'user_requested','budget')",
    )
    op.create_check_constraint(
        "ck_call_records_cost_usd", "call_records", "cost_usd >= 0",
    )

    # ── 2) Tabla call_transcriptions (D8/R3) ──────────────────────
    op.create_table(
        "call_transcriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        # = call_records.external_call_id (Uniqueid Asterisk, UNIQUE en F2)
        sa.Column("call_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("segments", postgresql.JSONB(), nullable=True),
        sa.Column("lang", sa.String(10), nullable=False, server_default="es-PE"),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column(
            "cost_estimate", sa.Numeric(10, 4), nullable=False, server_default="0",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_call_transcriptions_call_id", "call_transcriptions", ["call_id"],
    )
    op.create_index(
        "ix_call_transcriptions_tenant_id", "call_transcriptions", ["tenant_id"],
    )


def downgrade() -> None:
    # 2) Tabla de transcripciones
    op.drop_index("ix_call_transcriptions_tenant_id", table_name="call_transcriptions")
    op.drop_index("ix_call_transcriptions_call_id", table_name="call_transcriptions")
    op.drop_table("call_transcriptions")

    # 1) Columnas IA — call_records de F2 queda intacta (CA-F3-13)
    op.drop_constraint("ck_call_records_cost_usd", "call_records", type_="check")
    op.drop_constraint("ck_call_records_transfer_reason", "call_records", type_="check")
    op.drop_constraint("ck_call_records_ai_state", "call_records", type_="check")
    op.drop_column("call_records", "cost_usd")
    op.drop_column("call_records", "context_summary")
    op.drop_column("call_records", "transfer_reason")
    op.drop_column("call_records", "ai_state")
