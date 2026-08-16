"""
🗓️ Modelo ORM — Agenda de Citas (Spec 07 F6, §3.1).

Tabla `appointments`: reservas por mesa con fecha/hora/duración/estado/canal.
El toggle `tables.status='reserved'` sigue existiendo como ESPEJO (D1) — la
fuente de verdad de la agenda es esta tabla (ver `appointments_service.py`).

Estados/canales — espejo de los CHECKs en BD (0021_appointments):
  - APPOINTMENT_STATUSES: solicitada → confirmada → cumplida|cancelada|no_show
    (R5: terminales cumplida|cancelada|no_show; ver transiciones válidas).
  - ACTIVE_APPOINTMENT_STATUSES: solicitada|confirmada — las únicas que
    bloquean disponibilidad (overlap, R2) y mantienen el espejo reserved.
  - APPOINTMENT_SOURCES: voice_ai|whatsapp|web|in_person (D7, trazabilidad R6).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base

# Estados del ciclo de vida de la cita (R5) — espejo del CHECK en BD
APPOINTMENT_STATUSES = (
    "solicitada", "confirmada", "cumplida", "cancelada", "no_show",
)
# Estados que bloquean la mesa (overlap R2 + espejo reserved D1)
ACTIVE_APPOINTMENT_STATUSES = ("solicitada", "confirmada")
# Estados terminales (la cita ya no bloquea la mesa)
TERMINAL_APPOINTMENT_STATUSES = ("cumplida", "cancelada", "no_show")
# Canales de origen (D7 — se registra desde el día 1)
APPOINTMENT_SOURCES = ("voice_ai", "whatsapp", "web", "in_person")

# Transiciones válidas (R5): {estado_actual: (estados_permitidos,)}
APPOINTMENT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "solicitada": ("confirmada", "cancelada"),
    "confirmada": ("cumplida", "cancelada", "no_show"),
    "cumplida": (),
    "cancelada": (),
    "no_show": (),
}


class Appointment(Base):
    """Reserva de mesa (Spec 07 §3.1). La fuente de verdad de la agenda."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    guests: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="solicitada")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="in_person")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    table = relationship("Table", foreign_keys=[table_id])

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "table_id", "starts_at",
            name="uq_appointments_tenant_table_start",
        ),
        Index("idx_appointments_tenant_date", "tenant_id", "starts_at"),
        Index("idx_appointments_tenant_state", "tenant_id", "status"),
        CheckConstraint("guests BETWEEN 1 AND 50", name="ck_appointments_guests"),
        CheckConstraint(
            "duration_min BETWEEN 15 AND 240", name="ck_appointments_duration_min",
        ),
        CheckConstraint(
            "status IN ('solicitada','confirmada','cumplida','cancelada','no_show')",
            name="ck_appointments_status",
        ),
        CheckConstraint(
            "source IN ('voice_ai','whatsapp','web','in_person')",
            name="ck_appointments_source",
        ),
    )

    def __repr__(self):
        return (
            f"<Appointment #{self.id} tenant={self.tenant_id} "
            f"table={self.table_id} starts_at={self.starts_at} "
            f"status={self.status} source={self.source}>"
        )
