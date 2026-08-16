"""
🗓️ Router — Agenda de Citas (Spec 07 F6, §3.3).

Endpoints (auth staff admin/manager — tenant-scoped vía X-Tenant-ID/JWT):

  GET   /api/v1/appointments/availability?date&guests&from&to  (rate-limit Redis)
  POST  /api/v1/appointments                     → 201 | 409 | 422
  GET   /api/v1/appointments?date&status&source  → agenda del día (staff)
  PATCH /api/v1/appointments/{id}                → transiciones R5 + espejo D1
  POST  /api/v1/appointments/{id}/remind         → 202 (R9, idempotente)

Contratos §3.3: D4 mesa libre con duración (availability valida overlap de
rangos) · D3 ventana configurable por tenant (settings.appointments.hours) ·
R7 aislamiento multi-tenant + rate-limit Redis en availability (anti-scraping).
"""

import logging
from datetime import date
from datetime import time as dt_time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import require_role
from app.core.rate_limit import get_rate_limiter
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.appointments import (
    AppointmentCreateIn,
    AppointmentListOut,
    AppointmentOut,
    AppointmentPatchIn,
    AvailabilityOut,
)
from app.services import appointments_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["Agenda de Citas (F6)"])

# Rate limit de availability (R7 — anti-scraping/abuso): 60 req/hora por
# (tenant, fecha, guests). El limiter cae a in-memory si Redis no responde.
AVAILABILITY_MAX_REQUESTS = 60
AVAILABILITY_WINDOW_SECONDS = 3600


@router.get("/availability", response_model=AvailabilityOut)
async def get_availability(
    request: Request,
    date: date,
    guests: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_time: dt_time | None = None,
    to_time: dt_time | None = None,
) -> AvailabilityOut:
    """CA-F6-3/CA-F6-10: mesas libres por fecha/personas (solo staff).

    - `from`/`to` acotan la ventana consultada (D4: hora exacta → un slot por
      mesa [from, from+duration); sin `from` → slots cada granularidad).
    - Rate-limit Redis por (tenant, fecha, guests) — R7.
    - 422 si guests fuera de 1–50 o la hora pedida no cabe en la ventana (R3).
    """
    if not 1 <= guests <= 50:
        raise HTTPException(status_code=422, detail="guests debe estar entre 1 y 50")

    limiter = get_rate_limiter()
    rl = await limiter.check(
        key=f"appointments:availability:{tenant_id}:{date.isoformat()}:{guests}",
        max_requests=AVAILABILITY_MAX_REQUESTS,
        window_seconds=AVAILABILITY_WINDOW_SECONDS,
    )
    if not rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas consultas de disponibilidad. Espera un momento.",
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )

    return await appointments_service.availability(
        db,
        tenant_id,
        date,
        guests,
        from_time=from_time,
        to_time=to_time,
    )


@router.post("", response_model=AppointmentOut, status_code=201)
async def create_appointment(
    body: AppointmentCreateIn,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentOut:
    """CA-F6-1/2/4: crea la cita (estado `solicitada`, source D7).

    201 creada · 409 doble reserva / sin mesa libre (R2) · 422 fuera de
    ventana (R3) o capacidad insuficiente (CA-F6-4).
    """
    return await appointments_service.create_appointment(
        db,
        tenant_id,
        body.model_dump(),
        created_by=current_user.id,
    )


@router.get("", response_model=AppointmentListOut)
async def list_appointments(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    date: date | None = None,
    status: str | None = None,
    source: str | None = None,
) -> AppointmentListOut:
    """Agenda del día (staff) con filtros opcionales por estado y canal (R7)."""
    if status is not None and status not in (
        "solicitada", "confirmada", "cumplida", "cancelada", "no_show",
    ):
        raise HTTPException(status_code=422, detail=f"status '{status}' inválido")
    if source is not None and source not in (
        "voice_ai", "whatsapp", "web", "in_person",
    ):
        raise HTTPException(status_code=422, detail=f"source '{source}' inválido")
    return await appointments_service.list_appointments(
        db, tenant_id, day=date, status=status, source=source,
    )


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: int,
    body: AppointmentPatchIn,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentOut:
    """CA-F6-5/6: transición de estado (R5) + espejo tables.status (D1).

    - solicitada→confirmada: `tables.status='reserved'` + evento
      `appointment.confirmed` (motor F1, dry-run sin Meta — CA-F6-5).
    - →cumplida/cancelada/no_show: libera la mesa si no queda otra cita
      activa (CA-F6-6). Transiciones inválidas → 422.
    - `table_id` opcional: reasigna mesa (verifica capacidad + overlap → 409).
    """
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=422, detail="Sin cambios para aplicar")
    return await appointments_service.update_appointment(
        db, tenant_id, appointment_id, data,
    )


@router.post("/{appointment_id}/remind", status_code=202)
async def remind_appointment(
    appointment_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """CA-F6-7: recordatorio manual (202) — publica `appointment.reminder`.

    Idempotente (R9): si la cita ya tiene `reminded_at` → 202 sin re-publicar
    (el job diario y el manual nunca duplican el envío).
    """
    return await appointments_service.remind(db, tenant_id, appointment_id)
