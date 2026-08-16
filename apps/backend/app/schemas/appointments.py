"""
🗓️ Schemas — Agenda de Citas (Spec 07 F6, §3.2/§3.3).

Contratos:
  - AppointmentSettings: config por tenant `companies.settings.appointments`
    (patrón D-03, igual que whatsapp/calls/voice_ai). D3 ✅: la ventana
    `hours.open/close` es INDEPENDIENTE del salón/delivery y configurable
    desde el frontend staff vía PATCH /api/settings. D4: `duration_min_default`
    (mesa libre con duración). D6: `templates` para el motor WhatsApp F1.
  - Contratos API §3.3: availability (rate-limited), POST 201/409/422,
    GET agenda del día, PATCH transiciones (R5), POST /{id}/remind (R9).

Validaciones de dominio: guests 1–50, duration_min 15–240, source ∈ D7,
estado ∈ R5 — espejo de los CHECKs de BD (0021_appointments) para 422 con
detalle ANTES de tocar la base.
"""

from datetime import date as DateType  # noqa: N812 — alias para evitar clash pydantic (campo `date`/`time`)
from datetime import time as TimeType  # noqa: N812 — idem

from pydantic import BaseModel, Field, field_validator

from app.adapters.db.models.appointments import (
    APPOINTMENT_SOURCES,
    APPOINTMENT_STATUSES,
)

# ═══════════════════════════════════════════════════════════════
# Config por tenant — companies.settings.appointments (§3.2, D-03)
# ═══════════════════════════════════════════════════════════════

DEFAULT_APPOINTMENT_HOURS = {"open": "12:00", "close": "23:00"}


class AppointmentHoursSettings(BaseModel):
    """Ventana de reservas (D3 — independiente, configurable desde el frontend)."""
    open: str = Field("12:00", description="Apertura de reservas (HH:MM, hora local)")
    close: str = Field("23:00", description="Cierre de reservas (HH:MM, hora local)")

    @field_validator("open", "close")
    @classmethod
    def _validate_hhmm(cls, v: str) -> str:
        try:
            TimeType.fromisoformat(v)
        except ValueError:
            raise ValueError(f"hora '{v}' inválida — formato HH:MM")
        return v


class AppointmentSettings(BaseModel):
    """Config completa `companies.settings.appointments` (§3.2, patrón D-03).

    Defaults: enabled=false (el módulo se enciende por tenant), ventana
    independiente 12:00–23:00 (D3), duración default 60 min (D4),
    recordatorio 24h antes (D6/R9) y templates del motor F1 (dry-run sin
    cuenta Meta — CA-B5/CA-B7).
    """

    enabled: bool = Field(False, description="Activa el módulo de agenda del tenant")
    hours: AppointmentHoursSettings = Field(
        default_factory=AppointmentHoursSettings,
        description="Ventana de reservas (D3: open/close, editable desde la UI staff)",
    )
    duration_min_default: int = Field(
        60, ge=15, le=240, description="Duración default de cita (D4, minutos)",
    )
    slot_granularity_min: int = Field(
        30, ge=5, le=120, description="Granularidad de slots para la UI de grilla (opcional)",
    )
    max_guests_per_table: int = Field(
        12, ge=1, le=50, description="Tope de comensales por mesa del local",
    )
    reminder_hours_before: int = Field(
        24, ge=1, le=168, description="Anticipación del recordatorio (R9)",
    )
    templates: dict[str, str] = Field(
        default_factory=lambda: {
            "appointment_confirmed": "appointment_confirmed",
            "appointment_reminder": "appointment_reminder",
        },
        description="Plantillas Meta: appointment_confirmed / appointment_reminder (D6)",
    )


# ═══════════════════════════════════════════════════════════════
# Contratos API (§3.3)
# ═══════════════════════════════════════════════════════════════

class AppointmentCreateIn(BaseModel):
    """POST /api/v1/appointments — body.

    `table_id` opcional (D1: la mesa se puede asignar después); si no viene,
    el servicio asigna la primera mesa libre con capacidad suficiente (R1:
    la IA nunca inventa — solo mesas reales libres). `source` SIEMPRE
    requerido (D7/R6, default in_person para staff presencial).
    """

    table_id: int | None = Field(None, description="Mesa a reservar (opcional: auto-asignación)")
    date: DateType = Field(..., description="Fecha de la cita (YYYY-MM-DD, hora local)")
    time: TimeType = Field(..., description="Hora de la cita (HH:MM, hora local)")
    guests: int = Field(2, ge=1, le=50, description="Comensales (1–50)")
    customer_name: str = Field(..., min_length=1, max_length=200, description="Nombre del cliente")
    customer_phone: str | None = Field(
        None, max_length=20, description="Teléfono para confirmación/recordatorio WhatsApp (D6)",
    )
    duration_min: int | None = Field(
        None, ge=15, le=240, description="Duración (default: settings.duration_min_default)",
    )
    notes: str | None = Field(None, description="Notas internas del staff")
    source: str = Field("in_person", description="Canal de origen (D7)")

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        if v not in APPOINTMENT_SOURCES:
            raise ValueError(
                f"source '{v}' inválido — permitidos: {', '.join(APPOINTMENT_SOURCES)}",
            )
        return v


class AppointmentPatchIn(BaseModel):
    """PATCH /api/v1/appointments/{id} — transiciones R5 + reasignación de mesa."""

    status: str | None = Field(None, description="Nuevo estado (R5)")
    table_id: int | None = Field(None, description="Reasignar mesa (verifica capacidad + overlap)")

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in APPOINTMENT_STATUSES:
            raise ValueError(
                f"status '{v}' inválido — permitidos: {', '.join(APPOINTMENT_STATUSES)}",
            )
        return v


class AppointmentOut(BaseModel):
    """Cita serializada (201/200)."""

    id: int
    tenant_id: int
    table_id: int | None
    table_number: str | None = None
    customer_name: str
    customer_phone: str | None
    guests: int
    starts_at: str
    duration_min: int
    status: str
    source: str
    notes: str | None
    call_id: str | None
    reminded_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AppointmentListOut(BaseModel):
    """GET /api/v1/appointments — agenda del día (staff)."""

    items: list[AppointmentOut]
    total: int


class AvailabilitySlot(BaseModel):
    """Un slot libre: mesa + rango horario (D4 — mesa libre con duración)."""

    table_id: int
    table_number: str
    section: str | None = None
    capacity: int
    start: str
    end: str


class AvailabilityOut(BaseModel):
    """GET /api/v1/appointments/availability — mesas libres (R2/R7)."""

    date: str
    guests: int
    window: dict
    duration_min: int
    slots: list[AvailabilitySlot]
