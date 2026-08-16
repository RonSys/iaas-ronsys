"""
🗓️ AppointmentsService — Agenda de Citas (Spec 07 F6, §3.2/§3.4).

Dominio puro del módulo de agenda (multi-tenant por construcción):

  - `availability`        R2/R3/R7: mesas libres por fecha/personas dentro de
                          la ventana configurable (D3) con capacidad ≥ guests,
                          sin solapamiento con citas activas. D4: mesa libre
                          con duración (rangos, sin grilla fija).
  - `create_appointment`  CA-F6-1..4: valida ventana (422), capacidad (422) y
                          solapamiento con query atómica FOR UPDATE (409).
  - `update_appointment`  R5: transiciones solicitada→confirmada|cancelada,
                          confirmada→cumplida|cancelada|no_show; terminales
                          no transitan. D1: espejo `tables.status` (confirmada
                          → 'reserved'; cumplida/cancelada/no_show → 'available'
                          si no queda otra cita activa).
  - `remind`              R9: publica `appointment.reminder` UNA sola vez
                          (idempotente vía `reminded_at`).

Reglas (Spec 07 §3.4): R1 (la IA usa SOLO availability real — nunca inventar),
R2 (anti-doble-reserva dura), R3 (ventana), R4 (espejo del mapa), R5
(transiciones), R6 (source + call_id trazabilidad), R7 (tenant scope siempre),
R8 (WhatsApp fire-and-forget, dry-run sin Meta), R9 (recordatorio idempotente),
R10 (datos mínimos).
"""

import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Company
from app.adapters.db.models.appointments import (
    ACTIVE_APPOINTMENT_STATUSES,
    Appointment,
)
from app.adapters.db.models.restaurant import Table
from app.schemas.appointments import (
    DEFAULT_APPOINTMENT_HOURS,
    AppointmentSettings,
)

logger = logging.getLogger(__name__)

LIMA_TZ = "America/Lima"
_LIMA = ZoneInfo(LIMA_TZ)


def _now() -> datetime:
    return datetime.now(UTC)


# ═══════════════════════════════════════════════════════════════
# Config por tenant — companies.settings.appointments (§3.2, D-03)
# ═══════════════════════════════════════════════════════════════

def appointment_settings_from_company(company: Company | None) -> AppointmentSettings:
    """Lee `companies.settings.appointments` con defaults (patrón D-03).

    Igual que `call_settings_from_company` (F2) / `voice_ai_settings_from_company`
    (F3): lo persistido gana, los campos ausentes toman el default del schema
    (AppointmentSettings §3.2 — D3 ventana 12:00–23:00, D4 duración 60).
    """
    raw = (company.settings or {}) if company else {}
    raw = raw if isinstance(raw, dict) else {}
    appointments = raw.get("appointments", {}) if isinstance(raw.get("appointments"), dict) else {}
    return AppointmentSettings(**appointments)


async def _company(db: AsyncSession, tenant_id: int) -> Company:
    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


async def get_settings(db: AsyncSession, tenant_id: int) -> AppointmentSettings:
    """Config appointments del tenant (R7: por tenant, nunca global)."""
    return appointment_settings_from_company(await _company(db, tenant_id))


# ═══════════════════════════════════════════════════════════════
# Helpers de tiempo (hora local del negocio = America/Lima)
# ═══════════════════════════════════════════════════════════════

def _parse_hhmm(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Hora '{value}' inválida — formato HH:MM",
        )


def _local_dt(day: date, hour: time) -> datetime:
    """Combina fecha + hora LOCAL (America/Lima) → datetime aware UTC."""
    return datetime.combine(day, hour, tzinfo=_LIMA).astimezone(UTC)


def _window_bounds(settings: AppointmentSettings, day: date) -> tuple[datetime, datetime]:
    """Rango [open, close) de la ventana del día (D3, hora local)."""
    open_t = _parse_hhmm(settings.hours.open or DEFAULT_APPOINTMENT_HOURS["open"])
    close_t = _parse_hhmm(settings.hours.close or DEFAULT_APPOINTMENT_HOURS["close"])
    return _local_dt(day, open_t), _local_dt(day, close_t)


def validate_window(
    starts_at: datetime,
    duration_min: int,
    settings: AppointmentSettings,
    day: date | None = None,
) -> None:
    """R3: la cita debe caber dentro de la ventana → 422 fuera de ventana.

    `starts_at` llega como datetime aware (UTC); la comparación es contra la
    ventana local del día de la cita (D3: ventana independiente del salón).
    """
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    day = day or starts_at.astimezone(_LIMA).date()
    open_dt, close_dt = _window_bounds(settings, day)
    end = starts_at + timedelta(minutes=int(duration_min))
    if starts_at < open_dt or end > close_dt:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Hora fuera de la ventana de reservas "
                f"({settings.hours.open}–{settings.hours.close}): "
                f"{starts_at.astimezone(_LIMA).strftime('%H:%M')} "
                f"({duration_min} min)"
            ),
        )


# ═══════════════════════════════════════════════════════════════
# Serialización
# ═══════════════════════════════════════════════════════════════

def _out(appointment: Appointment, table_number: str | None = None) -> dict:
    return {
        "id": appointment.id,
        "tenant_id": appointment.tenant_id,
        "table_id": appointment.table_id,
        "table_number": table_number,
        "customer_name": appointment.customer_name,
        "customer_phone": appointment.customer_phone,
        "guests": appointment.guests,
        "starts_at": appointment.starts_at.isoformat(),
        "duration_min": appointment.duration_min,
        "status": appointment.status,
        "source": appointment.source,
        "notes": appointment.notes,
        "call_id": appointment.call_id,
        "reminded_at": appointment.reminded_at.isoformat() if appointment.reminded_at else None,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
        "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
    }


async def _table_numbers(db: AsyncSession, tenant_id: int, table_ids: set[int]) -> dict[int, str]:
    """Mapa {table_id: number} del tenant (para serializar slots/agenda)."""
    if not table_ids:
        return {}
    rows = (await db.execute(
        select(Table.id, Table.number).where(
            Table.tenant_id == tenant_id,
            Table.id.in_(table_ids),
        )
    )).all()
    return {r[0]: r[1] for r in rows}


# ═══════════════════════════════════════════════════════════════
# Disponibilidad (R2/R3/R7 — CA-F6-3, CA-F6-9)
# ═══════════════════════════════════════════════════════════════

def _overlap_filter(
    table_id: int,
    start: datetime,
    end: datetime,
    *,
    exclude_id: int | None = None,
) -> tuple:
    """Filtro SQL de solapamiento de rangos [start, end) — R2.

    `starts_at < end AND (starts_at + duration_min) > start` sobre citas
    activas (solicitada|confirmada) de la misma mesa. Usado por
    `_active_overlap_ids` (query completa con tenant scope).
    """
    return (
        Appointment.table_id == table_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.starts_at < end,
        (Appointment.starts_at + func.make_interval(
            0, 0, 0, 0, 0, Appointment.duration_min,
        )) > start,
        *( () if exclude_id is None else (Appointment.id != exclude_id,) ),
    )


async def _active_overlap_ids(
    db: AsyncSession,
    tenant_id: int,
    table_id: int,
    start: datetime,
    end: datetime,
    *,
    exclude_id: int | None = None,
    for_update: bool = False,
) -> list[int]:
    """Ids de citas activas que solapan [start, end) en la mesa (R2).

    `for_update=True` → SELECT ... FOR UPDATE: la transacción bloquea las
    filas solapadas hasta el commit, cerrando la ventana de carrera entre el
    check y el INSERT (anti-doble-reserva atómica, CA-F6-2).
    """
    stmt = select(Appointment.id).where(
        Appointment.tenant_id == tenant_id,
        Appointment.table_id == table_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.starts_at < end,
        (Appointment.starts_at + func.make_interval(
            0, 0, 0, 0, 0, Appointment.duration_min,
        )) > start,
    )
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    if for_update:
        stmt = stmt.with_for_update()
    return list((await db.execute(stmt)).scalars().all())


async def availability(
    db: AsyncSession,
    tenant_id: int,
    day: date,
    guests: int,
    *,
    from_time: time | None = None,
    to_time: time | None = None,
    settings: AppointmentSettings | None = None,
) -> dict:
    """CA-F6-3/CA-F6-9: mesas libres (capacidad ≥ guests, sin overlap activo).

    - D4: si `from_time` viene, un slot por mesa [from, from+duration) (flujo
      "hora exacta" — voz/UI); si no, slots cada `slot_granularity_min` en la
      ventana (grilla opcional de la UI).
    - `to_time` acota el fin de la ventana considerada (default: close).
    - R1: SOLO mesas reales libres — la IA jamás inventa disponibilidad.
    """
    settings = settings or await get_settings(db, tenant_id)
    open_dt, close_dt = _window_bounds(settings, day)
    duration = int(settings.duration_min_default)

    # Ventana efectiva de búsqueda [start_min, end_max]
    start_min = _local_dt(day, from_time) if from_time is not None else open_dt
    end_max = close_dt
    if to_time is not None:
        end_max = _local_dt(day, to_time)

    # Mesas candidatas: capacidad suficiente y no en limpieza (el espejo
    # 'reserved' no excluye: la agenda es la fuente de verdad — D1).
    tables = (await db.execute(
        select(Table).where(
            Table.tenant_id == tenant_id,
            Table.capacity >= int(guests),
            Table.status != "cleaning",
        ).order_by(Table.capacity, Table.id)
    )).scalars().all()

    # Citas activas del día (ventana ampliada por duración máx 240 min)
    busy_start = start_min - timedelta(minutes=240)
    busy_end = end_max + timedelta(minutes=240)
    active = (await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.table_id.in_([t.id for t in tables]),
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            Appointment.starts_at >= busy_start,
            Appointment.starts_at < busy_end,
        )
    )).scalars().all()

    def _is_busy(table_id: int, start: datetime, end: datetime) -> bool:
        for appt in active:
            if appt.table_id != table_id:
                continue
            appt_end = appt.starts_at + timedelta(minutes=int(appt.duration_min))
            if appt.starts_at < end and appt_end > start:
                return True
        return False

    def _fits(table: Table) -> bool:
        # Doble guardia de capacidad (la query ya filtra por capacity — la
        # chequeamos también en Python: defensa en profundidad, y hace los
        # tests mock-based deterministas).
        return int(table.capacity) >= int(guests)

    # Candidatos de inicio (D4)
    starts: list[datetime] = []
    if from_time is not None:
        if start_min + timedelta(minutes=duration) > end_max:
            raise HTTPException(
                status_code=422,
                detail=f"Hora {from_time.isoformat()} fuera de la ventana de reservas",
            )
        starts.append(start_min)
    else:
        cursor = start_min
        while cursor + timedelta(minutes=duration) <= end_max:
            starts.append(cursor)
            cursor += timedelta(minutes=int(settings.slot_granularity_min))

    slots: list[dict] = []
    for start in starts:
        end = start + timedelta(minutes=duration)
        for table in tables:
            if not _fits(table):
                continue
            if _is_busy(table.id, start, end):
                continue
            slots.append({
                "table_id": table.id,
                "table_number": table.number,
                "section": table.section,
                "capacity": table.capacity,
                "start": start.astimezone(_LIMA).strftime("%H:%M"),
                "end": end.astimezone(_LIMA).strftime("%H:%M"),
            })

    return {
        "date": day.isoformat(),
        "guests": int(guests),
        "window": {"open": settings.hours.open, "close": settings.hours.close},
        "duration_min": duration,
        "slots": slots,
    }


# ═══════════════════════════════════════════════════════════════
# Creación (CA-F6-1..4 — 201/409/422)
# ═══════════════════════════════════════════════════════════════

async def _resolve_table(
    db: AsyncSession, tenant_id: int, table_id: int, guests: int,
) -> Table:
    table = (await db.execute(
        select(Table).where(
            Table.tenant_id == tenant_id,
            Table.id == table_id,
        )
    )).scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    if table.capacity < guests:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Mesa {table.number} tiene capacidad para {table.capacity} "
                f"personas (pediste {guests})"
            ),
        )
    return table


async def _pick_free_table(
    db: AsyncSession,
    tenant_id: int,
    day: date,
    guests: int,
    start: datetime,
    end: datetime,
    settings: AppointmentSettings,
) -> Table | None:
    """Auto-asignación (D1/CA-F6-1): primera mesa libre con capacidad ≥ guests.

    Sin mesa libre → None (el caller decide 409: R2 — no hay disponibilidad
    real, la IA NUNCA inventa una mesa).
    """
    tables = (await db.execute(
        select(Table).where(
            Table.tenant_id == tenant_id,
            Table.capacity >= int(guests),
            Table.status != "cleaning",
        ).order_by(Table.capacity, Table.id)
    )).scalars().all()
    for table in tables:
        if int(table.capacity) < int(guests):
            continue  # doble guardia (la query ya filtra por capacidad)
        overlap = await _active_overlap_ids(
            db, tenant_id, table.id, start, end, for_update=True,
        )
        if not overlap:
            return table
    return None


async def create_appointment(
    db: AsyncSession,
    tenant_id: int,
    data: dict,
    *,
    created_by: int | None = None,
    settings: AppointmentSettings | None = None,
) -> dict:
    """POST /api/v1/appointments (CA-F6-1..4).

    - 422: guests fuera de 1–50 (schema), hora fuera de ventana (R3),
      mesa sin capacidad (CA-F6-4).
    - 409: solapamiento con cita activa de la mesa (R2/CA-F6-2) — verificado
      con SELECT ... FOR UPDATE dentro de la misma transacción; el UNIQUE
      (tenant_id, table_id, starts_at) es el backstop del caso exacto.
    - `table_id` None → auto-asignación de mesa libre (D1); si no hay → 409.
    - R6: `source` SIEMPRE persistido (D7); `call_id` para trazabilidad voz.
    """
    settings = settings or await get_settings(db, tenant_id)
    day = data["date"]
    starts_at = _local_dt(day, data["time"])
    duration = int(data.get("duration_min") or settings.duration_min_default)
    guests = int(data["guests"])

    validate_window(starts_at, duration, settings, day)
    end = starts_at + timedelta(minutes=duration)

    table: Table | None = None
    if data.get("table_id") is not None:
        table = await _resolve_table(db, tenant_id, int(data["table_id"]), guests)
        overlap = await _active_overlap_ids(
            db, tenant_id, table.id, starts_at, end, for_update=True,
        )
        if overlap:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"La mesa {table.number} ya tiene una reserva activa "
                    f"en ese horario ({starts_at.astimezone(_LIMA).strftime('%H:%M')}–"
                    f"{end.astimezone(_LIMA).strftime('%H:%M')})"
                ),
            )
    else:
        table = await _pick_free_table(db, tenant_id, day, guests, starts_at, end, settings)
        if table is None:
            raise HTTPException(
                status_code=409,
                detail="No hay mesas libres para ese horario y número de personas",
            )

    appointment = Appointment(
        tenant_id=tenant_id,
        table_id=table.id,
        customer_name=str(data["customer_name"]).strip(),
        customer_phone=data.get("customer_phone"),
        guests=guests,
        starts_at=starts_at,
        duration_min=duration,
        status="solicitada",
        source=str(data.get("source") or "in_person"),
        notes=data.get("notes"),
        call_id=data.get("call_id"),
        created_by=created_by,
    )
    db.add(appointment)
    try:
        await db.commit()
    except IntegrityError:
        # Backstop UNIQUE (tenant_id, table_id, starts_at) — doble reserva exacta
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Doble reserva detectada: la mesa ya tiene una cita en ese horario exacto",
        )
    await db.refresh(appointment)
    return _out(appointment, table_number=table.number)


# ═══════════════════════════════════════════════════════════════
# Consulta de agenda (staff — CA-F6-10)
# ═══════════════════════════════════════════════════════════════

async def list_appointments(
    db: AsyncSession,
    tenant_id: int,
    *,
    day: date | None = None,
    status: str | None = None,
    source: str | None = None,
) -> dict:
    """GET /api/v1/appointments — agenda del día con filtros (R7 siempre)."""
    stmt = select(Appointment).where(Appointment.tenant_id == tenant_id)
    if day is not None:
        day_start = _local_dt(day, time.min)
        stmt = stmt.where(
            Appointment.starts_at >= day_start,
            Appointment.starts_at < day_start + timedelta(days=1),
        )
    if status is not None:
        stmt = stmt.where(Appointment.status == status)
    if source is not None:
        stmt = stmt.where(Appointment.source == source)
    stmt = stmt.order_by(Appointment.starts_at)

    appointments = (await db.execute(stmt)).scalars().all()
    numbers = await _table_numbers(
        db, tenant_id, {a.table_id for a in appointments if a.table_id},
    )
    items = [_out(a, table_number=numbers.get(a.table_id)) for a in appointments]
    return {"items": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════════
# Transiciones de estado (R5) + espejo del mapa (D1/R4)
# ═══════════════════════════════════════════════════════════════

_TERMINAL = ("cumplida", "cancelada", "no_show")


async def _sync_table_mirror(
    db: AsyncSession, tenant_id: int, appointment: Appointment,
) -> None:
    """D1/R4: espeja `tables.status` con la agenda (la agenda es la verdad).

    - confirmada  → 'reserved'.
    - cumplida/cancelada/no_show → 'available' SI no queda otra cita activa
      (solicitada|confirmada) futura para la misma mesa.
    - solicitada → sin cambio (el POS solo muestra reservadas las confirmadas).
    """
    if appointment.table_id is None:
        return
    table = (await db.execute(
        select(Table).where(
            Table.tenant_id == tenant_id,
            Table.id == appointment.table_id,
        )
    )).scalar_one_or_none()
    if table is None:
        return

    if appointment.status == "confirmada":
        if table.status != "reserved":
            table.status = "reserved"
    elif appointment.status in _TERMINAL:
        future_active = (await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.tenant_id == tenant_id,
                Appointment.table_id == appointment.table_id,
                Appointment.id != appointment.id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                Appointment.starts_at > _now(),
            )
        )).scalar_one()
        if future_active == 0 and table.status == "reserved":
            table.status = "available"


async def _require_appointment(
    db: AsyncSession, tenant_id: int, appointment_id: int,
) -> Appointment:
    appointment = (await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.id == int(appointment_id),
        )
    )).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return appointment


async def update_appointment(
    db: AsyncSession,
    tenant_id: int,
    appointment_id: int,
    data: dict,
    *,
    publish: Any = None,
) -> dict:
    """PATCH /api/v1/appointments/{id} — transición R5 + reasignación de mesa.

    - 404 cita inexistente/cross-tenant (R7) · 422 transición inválida o
      mesa sin capacidad · 409 overlap al reasignar mesa.
    - D1: espejo tables.status (confirmada→reserved; terminal→available si
      no hay otra cita activa).
    - Evento `appointment.confirmed` al llegar a confirmada (fire-and-forget,
      motor F1 — dry-run sin Meta). `publish` se inyecta para tests.
    """
    appointment = await _require_appointment(db, tenant_id, appointment_id)
    new_status = data.get("status")
    new_table_id = data.get("table_id")

    if new_status is not None and new_status != appointment.status:
        allowed = _TRANSITIONS.get(appointment.status, ())
        if new_status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Transición inválida '{appointment.status}' → '{new_status}'. "
                    f"Permitidas: {', '.join(allowed) or 'ninguna (estado terminal)'}"
                ),
            )

    # Reasignación de mesa (verifica capacidad + overlap, excluye la propia cita)
    if new_table_id is not None and int(new_table_id) != appointment.table_id:
        table = await _resolve_table(db, tenant_id, int(new_table_id), appointment.guests)
        end = appointment.starts_at + timedelta(minutes=int(appointment.duration_min))
        overlap = await _active_overlap_ids(
            db, tenant_id, table.id, appointment.starts_at, end,
            exclude_id=appointment.id, for_update=True,
        )
        if overlap:
            raise HTTPException(
                status_code=409,
                detail=f"La mesa {table.number} ya tiene una reserva activa en ese horario",
            )
        appointment.table_id = table.id

    old_status = appointment.status
    if new_status is not None:
        appointment.status = new_status
    if data.get("notes") is not None:
        appointment.notes = data["notes"]

    await db.commit()
    await db.refresh(appointment)
    await _sync_table_mirror(db, tenant_id, appointment)
    await db.commit()

    # Evento F1: appointment.confirmed (R8 — fire-and-forget, dry-run sin Meta)
    if appointment.status == "confirmada" and old_status != "confirmada":
        publisher = publish or _publish_confirmed
        try:
            await publisher(
                tenant_id=tenant_id,
                appointment_id=appointment.id,
                table_id=appointment.table_id,
                customer_name=appointment.customer_name,
                customer_phone=appointment.customer_phone,
                starts_at=appointment.starts_at,
                duration_min=appointment.duration_min,
                guests=appointment.guests,
            )
        except Exception:  # noqa: BLE001 — los eventos nunca rompen la transición
            logger.warning(
                "evento appointment.confirmed falló (id=%s) — transición ya persistida",
                appointment.id, exc_info=True,
            )

    number = None
    if appointment.table_id:
        numbers = await _table_numbers(db, tenant_id, {appointment.table_id})
        number = numbers.get(appointment.table_id)
    return _out(appointment, table_number=number)


# ═══════════════════════════════════════════════════════════════
# Recordatorio (R9 — idempotente vía reminded_at)
# ═══════════════════════════════════════════════════════════════

async def remind(
    db: AsyncSession,
    tenant_id: int,
    appointment_id: int,
    *,
    publish: Any = None,
) -> dict:
    """POST /api/v1/appointments/{id}/remind → 202 (manual o job diario R9).

    Idempotente: si `reminded_at` ya está seteado NO re-publica (R9 — el job
    diario y el manual nunca duplican el recordatorio).
    """
    appointment = await _require_appointment(db, tenant_id, appointment_id)
    if appointment.status != "confirmada":
        raise HTTPException(
            status_code=422,
            detail="Solo las citas confirmadas reciben recordatorio",
        )
    if appointment.reminded_at is not None:
        return {"appointment_id": appointment.id, "reminded": True, "published": False}

    publisher = publish or _publish_reminder
    try:
        await publisher(
            tenant_id=tenant_id,
            appointment_id=appointment.id,
            table_id=appointment.table_id,
            customer_name=appointment.customer_name,
            customer_phone=appointment.customer_phone,
            starts_at=appointment.starts_at,
            duration_min=appointment.duration_min,
            guests=appointment.guests,
        )
    except Exception:  # noqa: BLE001 — fire-and-forget: el job nunca se rompe
        logger.warning(
            "evento appointment.reminder falló (id=%s)", appointment.id, exc_info=True,
        )

    appointment.reminded_at = _now()
    await db.commit()
    return {"appointment_id": appointment.id, "reminded": True, "published": True}


async def find_reminders_due(
    db: AsyncSession,
    tenant_id: int,
    *,
    reminder_hours_before: int | None = None,
) -> list[dict]:
    """R9: citas confirmadas cuyo recordatorio está por vencer (job diario).

    Ventana: starts_at ∈ (now, now + reminder_hours_before] y sin
    `reminded_at` — el job corre 1×/día y es idempotente (nunca re-envía).
    """
    settings = await get_settings(db, tenant_id)
    hours = int(reminder_hours_before or settings.reminder_hours_before)
    now = _now()
    due = (await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "confirmada",
            Appointment.reminded_at.is_(None),
            Appointment.starts_at > now,
            Appointment.starts_at <= now + timedelta(hours=hours),
        )
    )).scalars().all()
    # Doble guardia en Python (la query ya filtra): el job NUNCA re-envía
    # ni adelanta recordatorios (R9 — idempotencia también ante mocks/caches).
    due = [
        a for a in due
        if a.status == "confirmada"
        and a.reminded_at is None
        and now < a.starts_at <= now + timedelta(hours=hours)
    ]
    return [_out(a) for a in due]


# ═══════════════════════════════════════════════════════════════
# Eventos (R8 — publicadores inyectables para tests)
# ═══════════════════════════════════════════════════════════════

async def _publish_confirmed(**kwargs: Any) -> None:
    from app.services.notify_events import publish_appointment_event
    await publish_appointment_event("confirmed", **kwargs)


async def _publish_reminder(**kwargs: Any) -> None:
    from app.services.notify_events import publish_appointment_event
    await publish_appointment_event("reminder", **kwargs)


# Mapa de transiciones (R5) — espejo de APPOINTMENT_TRANSITIONS del modelo
_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "solicitada": ("confirmada", "cancelada"),
    "confirmada": ("cumplida", "cancelada", "no_show"),
    "cumplida": (),
    "cancelada": (),
    "no_show": (),
}
