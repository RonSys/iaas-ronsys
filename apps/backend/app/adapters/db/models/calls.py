"""
📞 Modelo ORM — Central Telefónica / Call Records (Spec 05 F2, §3.2).

Alcance aprobado (F2 "Central que No Pierde Llamadas"):
  - call_records:       Registro por llamada (inbound/outbound) con idempotencia
                        por `external_call_id` (Uniqueid de Asterisk / ORIGINATE_ID).

Diseño (Spec 05 §3.2):
  - `external_call_id` UNIQUE = Uniqueid de Asterisk → idempotencia natural:
    los eventos AMI (Newchannel/Newstate/Hangup) hacen upsert del mismo
    registro (INSERT ... ON CONFLICT DO UPDATE); el adapter call-bridge es
    re-arrancable sin duplicar llamadas (R8).
  - `direction` inbound/outbound; outbound nace del click-to-call (Originate
    vía ARI desde POST /api/v1/calls/originate).
  - `status` refleja el ciclo de vida AMI: ringing → in_progress → answered →
    completed (o missed/failed según hangup cause). `duration` solo cuenta
    tiempo answered (answered_at → ended_at).
  - `metadata` jsonb crudo (contexto de Asterisk, hangup_cause, DID resuelto,
    extensión del operador) — trazabilidad sin columnas nuevas.
  - `transcription_fk` NULL en F2: RESERVADO para el módulo futuro de
    transcripción (fuera de alcance, sin FK por ahora).
  - `converted_order_id` → delivery_orders: 1 sola conversión por llamada (R6).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base

# Estados del ciclo de vida AMI (Spec 05 §3.2) — espejo del CHECK en BD
CALL_STATUSES = ("ringing", "in_progress", "answered", "missed", "completed", "failed")
CALL_DIRECTIONS = ("inbound", "outbound")
# Estados terminales (la llamada ya no está activa)
TERMINAL_STATUSES = ("missed", "completed", "failed")
# Estados "activos" (una llamada en curso — 1 línea activa por operador)
ACTIVE_STATUSES = ("ringing", "in_progress", "answered")

# Estados conversacionales de la Recepcionista IA (Spec 06 F3 §3.6) — espejo
# del CHECK en BD (0019_voice_ai). `completed|failed` son los estados de
# cierre del POST /complete (contrato §3.5.1), añadidos al CHECK de la spec
# (ver bitácora Spec Anchor 2026-08-13).
AI_STATES = (
    "greeting", "taking_order", "clarifying", "confirming",
    "transfer", "hangup", "completed", "failed",
)
# Motivos de transferencia a humano (D9) — espejo del CHECK en BD
TRANSFER_REASONS = (
    "complaint", "out_of_domain", "low_confidence", "user_requested", "budget",
)


class CallRecord(Base):
    """Registro de una llamada (inbound/outbound) de la central telefónica."""

    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Uniqueid de Asterisk (inbound) u ORIGINATE_ID (outbound click-to-call):
    # fuente de idempotencia del upsert (R8).
    external_call_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    # ANI: número entrante (o DESTINO en outbound, Spec 05 §3.2 nota de diseño)
    caller: Mapped[str] = mapped_column(String(32), nullable=False)
    # DNIS: extensión/DID atendida (u ORIGEN/operador en outbound)
    callee: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound | outbound
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ringing", server_default="ringing"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Segundos (answered_at → ended_at); 0 si nunca se contestó (R8/CA-F2.1)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Ruta/alias de la grabación MixMonitor (R1) — null hasta call.recording_ready
    recording_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # RESERVADO F2: transcripción futura (fuera de alcance; sin FK aún).
    # F3 (0019_voice_ai) lo llena al persistir `call_transcriptions` (D8/R3).
    transcription_fk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ── Columnas IA (Spec 06 F3 §3.2, migración 0019_voice_ai) ──────────
    # Máquina de estados conversacional (§3.6): greeting|taking_order|
    # clarifying|confirming|transfer|hangup + cierre completed|failed.
    ai_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Motivo de transferencia a humano (D9): complaint|out_of_domain|
    # low_confidence|user_requested|budget.
    transfer_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Resumen incremental para el operador (D9): items capturados,
    # dirección/zona, nombre/teléfono — actualizado vía PATCH ai-context.
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Costo acumulado STT+TTS+LLM de la llamada en USD (R4, CHECK >= 0).
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0",
    )
    # Contexto Asterisk crudo: channel, hangup_cause, did_resuelto, extension,
    # trunk, provider, recording_failed (R1)...
    # `metadata_` (atributo Python) → columna `metadata` (BD): "metadata" es
    # nombre reservado del API declarativo de SQLAlchemy.
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    # Pedido de delivery creado desde la llamada (R6: 1 sola conversión)
    converted_order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("delivery_orders.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    converted_order = relationship("DeliveryOrder", foreign_keys=[converted_order_id])

    __table_args__ = (
        UniqueConstraint("external_call_id", name="uq_call_records_external_call_id"),
        Index("idx_call_records_tenant_status", "tenant_id", "status"),
        Index("idx_call_records_tenant_started", "tenant_id", "started_at"),
        CheckConstraint(
            "direction IN ('inbound', 'outbound')", name="ck_call_records_direction"
        ),
        CheckConstraint(
            "status IN ('ringing', 'in_progress', 'answered', 'missed', 'completed', 'failed')",
            name="ck_call_records_status",
        ),
        CheckConstraint("duration >= 0", name="ck_call_records_duration"),
        # Spec 06 §3.2 (0019_voice_ai): dominio blindado a nivel de datos
        CheckConstraint(
            "ai_state IN ('greeting','taking_order','clarifying','confirming',"
            "'transfer','hangup','completed','failed')",
            name="ck_call_records_ai_state",
        ),
        CheckConstraint(
            "transfer_reason IN ('complaint','out_of_domain','low_confidence',"
            "'user_requested','budget')",
            name="ck_call_records_transfer_reason",
        ),
        CheckConstraint("cost_usd >= 0", name="ck_call_records_cost_usd"),
    )

    def __repr__(self) -> str:
        return f"<CallRecord #{self.id}: {self.caller}→{self.callee} [{self.status}]>"


class CallTranscription(Base):
    """Transcripción de una llamada (Spec 06 F3 §3.2 — D8/R3, 0019_voice_ai).

    `call_id` = `call_records.external_call_id` (Uniqueid de Asterisk, UNIQUE
    en F2) → una transcripción por llamada; `call_records.transcription_fk`
    (columna reservada por F2) se actualiza al persistirla — el detalle de la
    llamada en F2 la muestra sin cambio de contrato (CA-F3-3).

    Reglas:
      - R8: todo filtrado por tenant (tenant_id FK companies CASCADE).
      - R4: `cost_estimate` = costo STT estimado de la transcripción.
      - R3: retención hereda `calls.retention_days` de F2 (purga en cascada
        con la llamada).
    """

    __tablename__ = "call_transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # = call_records.external_call_id (Uniqueid Asterisk / ORIGINATE_ID)
    call_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # [{start, end, speaker, text, confidence}] — crudo del proveedor STT
    segments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    lang: Mapped[str] = mapped_column(
        String(10), nullable=False, default="es-PE", server_default="es-PE",
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Costo STT estimado en USD (R4/CA-F3-8)
    cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_call_transcriptions_call_id", "call_id"),
        Index("ix_call_transcriptions_tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<CallTranscription #{self.id}: call={self.call_id} [{self.provider}]>"
