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

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    # RESERVADO F2: transcripción futura (fuera de alcance; sin FK aún)
    transcription_fk: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    )

    def __repr__(self) -> str:
        return f"<CallRecord #{self.id}: {self.caller}→{self.callee} [{self.status}]>"
