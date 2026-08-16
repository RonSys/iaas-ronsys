"""
Tests Spec 07 — F6 "Agenda de Citas" (backend, §3.1/§3.3/§3.4).

Cubre (misma metodología que test_f3_voice_ai.py — mock-based + migración
con BD de test real):

  - Migración 0021_appointments: upgrade head (CA-F6-11), CHECKs/UNIQUE/
    índices, ai_state ampliado con taking_reservation (D5), downgrade 0020
    revierte TODO y restaura el CHECK de F3.
  - Creación (CA-F6-1): 201 status solicitada + source (D7) + auto-asignación.
  - Anti-doble-reserva (CA-F6-2): overlap → 409, ninguna fila creada.
  - Disponibilidad (CA-F6-3/CA-F6-9): solo mesas libres con capacidad ≥ guests.
  - Validaciones (CA-F6-4): fuera de ventana (R3) y capacidad → 422.
  - Transiciones (CA-F6-5/6, R5): confirmada → espejo tables.status='reserved'
    + evento appointment.confirmed; terminales liberan la mesa si no hay otra
    cita activa; transiciones inválidas → 422.
  - Recordatorio (CA-F6-7, R9): 202 + publish UNA sola vez (reminded_at).
  - Aislamiento tenant (CA-F6-10): cita de otro tenant → 404.
  - Skills de voz (CA-F6-8, D5): consultar_disponibilidad / reservar con
    source='voice_ai' + call_id (R6); 409 → alternativas REALES (R1).
  - Máquina de estados: taking_reservation (greeting → … → confirming).
  - Settings D-03: defaults de companies.settings.appointments.

⚠️ REQUISITO DE RON: todos los fixtures/mocks usan tenant-id = 3 (no 1).
"""

import asyncio
import os
import subprocess
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.adapters.db.models.appointments import (
    Appointment,
)
from app.adapters.db.models.restaurant import Table
from app.schemas.appointments import AppointmentSettings
from app.services import appointments_service
from app.services.appointments_service import (
    availability,
    create_appointment,
    find_reminders_due,
    remind,
    update_appointment,
)
from app.services.voice_ai_service import AppointmentSkills, ConversationStateMachine
from app.services.voice_providers import (
    DeterministicLLMClient,
    _state_for_transcript,
)

APP_ROOT = Path(__file__).resolve().parents[1]
# BD de test dedicada (nunca la de prod). En CI se inyecta F6_TEST_DATABASE_URL.
MIGRATION_TEST_URL = os.environ.get(
    "F6_TEST_DATABASE_URL",
    "postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys_test",
)

# ═══════════════════════════════════════════════════════════════
# Helpers (estilo test_f3_voice_ai.py — tenant-id = 3, requisito de Ron)
# ═══════════════════════════════════════════════════════════════

TENANT = 3  # ⚠️ Ron: E2E/fixtures con tenant-id = 3 (no 1)


def _make_table(id=1, number="M1", capacity=4, status="available", tenant=TENANT, section="Salón"):
    t = Table(
        tenant_id=tenant, number=number, capacity=capacity,
        status=status, section=section,
    )
    t.id = id
    return t


def _make_appointment(
    id=1, tenant=TENANT, table_id=1, name="Cliente Test", phone="999000111",
    guests=2, starts_at=None, duration_min=60, status="solicitada",
    source="web", call_id=None, reminded_at=None,
):
    appt = Appointment(
        tenant_id=tenant, table_id=table_id, customer_name=name,
        customer_phone=phone, guests=guests,
        starts_at=starts_at or datetime(2026, 8, 25, 20, 0, tzinfo=UTC),
        duration_min=duration_min, status=status, source=source, call_id=call_id,
        reminded_at=reminded_at,
    )
    appt.id = id
    appt.created_at = datetime(2026, 8, 20, tzinfo=UTC)
    appt.updated_at = datetime(2026, 8, 20, tzinfo=UTC)
    return appt


def _make_company(tenant=TENANT, settings=None):
    company = MagicMock()
    company.id = tenant
    company.settings = settings or {}
    return company


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return [r[0] if isinstance(r, tuple) else r for r in self.rows]


class _Result:
    """Resultado flexible: soporta scalar_one_or_none/scalars/all (FakeDB)."""

    def __init__(self, rows):
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.rows[0] if self.rows else None

    def scalar(self):
        r = self.rows[0] if self.rows else None
        return r[0] if isinstance(r, tuple) else r

    def scalars(self):
        return _Scalars(self.rows)

    def all(self):
        return self.rows


class _FakeDB:
    """Mini-AsyncSession con despacho por entidad (patrón F3, tenant=3).

    - companies: `self.company` (scalar_one_or_none).
    - tables: `self.tables` — entidad (scalars) o pares (id, number).
    - appointments: `self.appointments` — entidad; las queries de overlap
      (Appointment.id) devuelven `self.overlap_ids`; el count `self.count_result`.
    """

    def __init__(self):
        self.company: MagicMock | None = None
        self.tables: list = []
        self.appointments: list = []
        self.overlap_ids: list[int] = []
        self.count_result: int = 0
        self.commits = 0
        self._next_id = 100

    def queue_overlap(self, ids: list[int]) -> None:
        self.overlap_ids = ids

    async def execute(self, stmt, *a, **kw):
        descs = list(getattr(stmt, "column_descriptions", []) or [])
        try:
            froms = list(stmt.get_final_froms())
        except Exception:  # noqa: BLE001
            froms = list(getattr(stmt, "froms", []) or [])
        tname = getattr(froms[0], "name", "") if froms else ""
        entity = next((d.get("entity") for d in descs if d.get("entity") is not None), None)
        ncols = len(descs)
        params = self._params(stmt)
        tenant = params.get("tenant_id")

        if tname == "companies":
            return _Result([self.company])
        if tname == "tables":
            if ncols == 2:  # Table.id, Table.number (_table_numbers)
                return _Result([(t.id, t.number) for t in self.tables])
            return _Result(list(self.tables))
        if tname == "appointments" and entity is Appointment:
            name0 = descs[0].get("name") if descs else ""
            if name0 == "count":
                return _Result([self.count_result])
            if name0 == "id":
                # overlap (Appointment.id) — el test setea el resultado
                return _Result(list(self.overlap_ids))
            # select(Appointment) completo → filas (filtradas por tenant R7)
            rows = self.appointments
            tenant = params.get("tenant_id") or params.get("tenant_id_1")
            if tenant is not None:
                rows = [a for a in rows if a.tenant_id == int(tenant)]
            return _Result(list(rows))
        return _Result([])

    @staticmethod
    def _params(stmt):
        try:
            return stmt.compile().params or {}
        except Exception:  # noqa: BLE001
            return {}

    def add(self, obj):
        obj.id = self._next_id
        self._next_id += 1
        self.appointments.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass

    async def refresh(self, obj):
        return obj


@pytest.fixture
def fake_db():
    db = _FakeDB()
    db.company = _make_company()  # tenant 3, settings default
    return db


def _day(hour: int = 20, minute: int = 0) -> tuple[date, time]:
    return date(2026, 8, 25), time(hour, minute)


# ═══════════════════════════════════════════════════════════════
# Settings D-03 (§3.2 — ventana independiente D3, duración D4)
# ═══════════════════════════════════════════════════════════════

def test_appointment_settings_defaults():
    """D3: ventana independiente 12:00–23:00 · D4: duración 60 · R9: 24h."""
    s = AppointmentSettings()
    assert s.enabled is False
    assert s.hours.open == "12:00" and s.hours.close == "23:00"
    assert s.duration_min_default == 60
    assert s.reminder_hours_before == 24
    assert s.templates["appointment_confirmed"] == "appointment_confirmed"
    assert s.templates["appointment_reminder"] == "appointment_reminder"

    # persistido gana al default (patrón D-03)
    company = _make_company(settings={
        "appointments": {"enabled": True, "hours": {"open": "10:00", "close": "22:00"}},
    })
    s2 = appointments_service.appointment_settings_from_company(company)
    assert s2.enabled is True
    assert s2.hours.open == "10:00"
    assert s2.duration_min_default == 60  # no enviado → default


def test_company_settings_includes_appointments():
    """CompanySettings (PATCH /api/settings) expone appointments (D-03)."""
    from app.schemas import CompanySettings
    cs = CompanySettings()
    assert cs.appointments.hours.open == "12:00"
    assert cs.appointments.duration_min_default == 60


# ═══════════════════════════════════════════════════════════════
# Creación (CA-F6-1 / CA-F6-2 / CA-F6-4)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_appointment_201(fake_db):
    """CA-F6-1: cita creada con status solicitada + source (D7) + mesa correcta."""
    fake_db.tables = [_make_table(id=7, number="VIP1", capacity=6)]
    day, hour = _day(20)
    out = await create_appointment(fake_db, TENANT, {
        "date": day, "time": hour, "guests": 4,
        "customer_name": "María Pérez", "customer_phone": "999000111",
        "source": "web", "table_id": 7,
    }, created_by=42)
    assert out["status"] == "solicitada"
    assert out["source"] == "web"
    assert out["table_id"] == 7
    assert out["customer_name"] == "María Pérez"
    assert out["guests"] == 4
    assert out["duration_min"] == 60  # default D4
    # la mesa NO se marca reserved en solicitada (D1: solo confirmada)
    assert fake_db.tables[0].status == "available"
    assert fake_db.appointments[0].created_by == 42


@pytest.mark.asyncio
async def test_create_overlap_409(fake_db):
    """CA-F6-2: solapamiento con cita activa → 409, ninguna fila creada."""
    fake_db.tables = [_make_table(id=7)]
    fake_db.queue_overlap([1])  # ya hay una cita activa en el rango
    day, hour = _day(20)
    with pytest.raises(Exception) as exc:
        await create_appointment(fake_db, TENANT, {
            "date": day, "time": hour, "guests": 2,
            "customer_name": "Cliente", "source": "in_person", "table_id": 7,
        })
    assert exc.value.status_code == 409
    assert len(fake_db.appointments) == 0  # nada creado


@pytest.mark.asyncio
async def test_create_outside_window_422(fake_db):
    """CA-F6-4/R3: hora fuera de la ventana (12:00–23:00) → 422."""
    fake_db.tables = [_make_table(id=7)]
    day, hour = _day(10)  # 10:00 < open 12:00
    with pytest.raises(Exception) as exc:
        await create_appointment(fake_db, TENANT, {
            "date": day, "time": hour, "guests": 2,
            "customer_name": "Cliente", "source": "in_person", "table_id": 7,
        })
    assert exc.value.status_code == 422
    assert "ventana" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_create_guests_over_capacity_422(fake_db):
    """CA-F6-4: guests > capacidad de la mesa → 422."""
    fake_db.tables = [_make_table(id=7, capacity=2)]
    day, hour = _day(20)
    with pytest.raises(Exception) as exc:
        await create_appointment(fake_db, TENANT, {
            "date": day, "time": hour, "guests": 4,
            "customer_name": "Cliente", "source": "in_person", "table_id": 7,
        })
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_auto_assign_free_table(fake_db):
    """D1: sin table_id → auto-asigna la primera mesa libre con capacidad."""
    fake_db.tables = [_make_table(id=1, capacity=2), _make_table(id=2, capacity=6)]
    fake_db.queue_overlap([])  # mesas libres
    day, hour = _day(20)
    out = await create_appointment(fake_db, TENANT, {
        "date": day, "time": hour, "guests": 3,
        "customer_name": "Cliente", "source": "voice_ai",
    })
    assert out["table_id"] == 2  # la de capacidad 6 (2 < 3)
    assert out["status"] == "solicitada"


@pytest.mark.asyncio
async def test_create_no_free_table_409(fake_db):
    """R1/CA-F6-9: sin mesa libre → 409 (la IA nunca inventa)."""
    fake_db.tables = [_make_table(id=1, capacity=4)]
    fake_db.queue_overlap([99])  # la única mesa está ocupada en el rango
    day, hour = _day(20)
    with pytest.raises(Exception) as exc:
        await create_appointment(fake_db, TENANT, {
            "date": day, "time": hour, "guests": 2,
            "customer_name": "Cliente", "source": "in_person",
        })
    assert exc.value.status_code == 409


def test_schema_rejects_bad_source_and_guests():
    """D7/R2: source fuera del dominio y guests fuera de rango → 422 de schema."""
    from app.schemas.appointments import AppointmentCreateIn
    with pytest.raises(ValidationError):
        AppointmentCreateIn(date=date(2026, 8, 25), time=time(20, 0),
                            customer_name="X", source="fax", guests=2)
    with pytest.raises(ValidationError):
        AppointmentCreateIn(date=date(2026, 8, 25), time=time(20, 0),
                            customer_name="X", source="web", guests=51)
    assert AppointmentCreateIn(
        date=date(2026, 8, 25), time=time(20, 0), customer_name="X",
        source="voice_ai", guests=4,
    ).source == "voice_ai"


# ═══════════════════════════════════════════════════════════════
# Disponibilidad (CA-F6-3 / CA-F6-9)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_availability_only_free_tables(fake_db):
    """CA-F6-3: solo mesas libres con capacidad ≥ guests (sin overlap)."""
    fake_db.tables = [
        _make_table(id=1, number="M1", capacity=4),
        _make_table(id=2, number="M2", capacity=2),
        _make_table(id=3, number="M3", capacity=6),
    ]
    # M2 ocupada en el rango: cita 20:00–22:00 Lima (01:00–03:00 UTC) vs
    # consulta 20:00–21:00 Lima → solapamiento real (R2)
    fake_db.appointments = [_make_appointment(
        id=1, table_id=2, starts_at=datetime(2026, 8, 26, 1, 0, tzinfo=UTC),
        duration_min=120, status="confirmada",
    )]
    out = await availability(fake_db, TENANT, date(2026, 8, 25), 2, from_time=time(20, 0))
    assert out["guests"] == 2
    numbers = {s["table_id"] for s in out["slots"]}
    assert numbers == {1, 3}  # M2 excluida por overlap (capacidad 2 ≥ 2 OK)
    slot = next(s for s in out["slots"] if s["table_id"] == 3)
    assert slot["start"] == "20:00" and slot["end"] == "21:00"  # D4: duración 60
    assert slot["section"] == "Salón"


@pytest.mark.asyncio
async def test_availability_filters_by_guest_capacity(fake_db):
    """CA-F6-4: mesa con capacidad < guests jamás aparece en slots."""
    fake_db.tables = [
        _make_table(id=1, number="M1", capacity=2),
        _make_table(id=2, number="M2", capacity=8),
    ]
    out = await availability(fake_db, TENANT, date(2026, 8, 25), 4, from_time=time(20, 0))
    assert {s["table_id"] for s in out["slots"]} == {2}


@pytest.mark.asyncio
async def test_availability_grilla_without_from(fake_db):
    """Sin from: slots cada granularidad en la ventana (grilla opcional UI)."""
    fake_db.tables = [_make_table(id=1, number="M1", capacity=4)]
    out = await availability(fake_db, TENANT, date(2026, 8, 25), 2)
    starts = {s["start"] for s in out["slots"]}
    # ventana 12:00–23:00, duración 60, granularidad 30 → 21 slots (12:00..22:00)
    assert len(out["slots"]) == 21
    assert "12:00" in starts and "22:00" in starts


@pytest.mark.asyncio
async def test_availability_from_outside_window_422(fake_db):
    """R3: consulta de una hora que no cabe en la ventana → 422."""
    fake_db.tables = [_make_table(id=1)]
    with pytest.raises(Exception) as exc:
        await availability(fake_db, TENANT, date(2026, 8, 25), 2, from_time=time(23, 0))
    assert exc.value.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Transiciones (CA-F6-5/6, R5) + espejo (D1/R4)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confirmada_reserves_table_and_publishes(fake_db):
    """CA-F6-5: solicitada→confirmada → espejo reserved + evento confirmed."""
    table = _make_table(id=7, number="VIP1")
    fake_db.tables = [table]
    fake_db.appointments = [_make_appointment(id=1, table_id=7)]
    publish = AsyncMock(return_value=True)

    out = await update_appointment(fake_db, TENANT, 1, {"status": "confirmada"}, publish=publish)

    assert out["status"] == "confirmada"
    assert table.status == "reserved"  # D1: espejo del mapa del POS
    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    assert kwargs["tenant_id"] == TENANT
    assert kwargs["appointment_id"] == 1
    assert kwargs["customer_phone"] == "999000111"


@pytest.mark.asyncio
async def test_terminal_releases_table(fake_db):
    """CA-F6-6: confirmada→cumplida libera la mesa (sin otra cita activa)."""
    table = _make_table(id=7, status="reserved")
    fake_db.tables = [table]
    fake_db.appointments = [_make_appointment(id=1, table_id=7, status="confirmada")]
    fake_db.count_result = 0  # no hay otra cita activa futura

    out = await update_appointment(fake_db, TENANT, 1, {"status": "cumplida"})

    assert out["status"] == "cumplida"
    assert table.status == "available"


@pytest.mark.asyncio
async def test_terminal_keeps_reserved_with_future_active(fake_db):
    """D1: libera SOLO si no queda otra cita activa (futura)."""
    table = _make_table(id=7, status="reserved")
    fake_db.tables = [table]
    fake_db.appointments = [_make_appointment(id=1, table_id=7, status="confirmada")]
    fake_db.count_result = 1  # otra cita activa futura en la misma mesa

    await update_appointment(fake_db, TENANT, 1, {"status": "no_show"})
    assert table.status == "reserved"  # sigue reservada


@pytest.mark.asyncio
async def test_invalid_transition_422(fake_db):
    """R5: solicitada→cumplida y terminal→cualquiera → 422."""
    fake_db.appointments = [_make_appointment(id=1, status="solicitada")]
    with pytest.raises(Exception) as exc:
        await update_appointment(fake_db, TENANT, 1, {"status": "cumplida"})
    assert exc.value.status_code == 422

    fake_db.appointments = [_make_appointment(id=2, status="cumplida")]
    with pytest.raises(Exception) as exc:
        await update_appointment(fake_db, TENANT, 2, {"status": "confirmada"})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_reassign_table_overlap_409(fake_db):
    """Reasignar mesa con cita activa solapada → 409 (excluye la propia)."""
    fake_db.tables = [_make_table(id=7, number="VIP1"), _make_table(id=8, number="M8")]
    fake_db.appointments = [_make_appointment(id=1, table_id=7, status="solicitada")]
    fake_db.queue_overlap([5])  # mesa 8 ocupada en el rango
    with pytest.raises(Exception) as exc:
        await update_appointment(fake_db, TENANT, 1, {"table_id": 8})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_tenant_isolation_404(fake_db):
    """CA-F6-10/R7: cita de otro tenant (4) invisible para tenant 3 → 404."""
    fake_db.appointments = [_make_appointment(id=1, tenant=4)]
    with pytest.raises(Exception) as exc:
        await update_appointment(fake_db, TENANT, 1, {"status": "cancelada"})
    assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Recordatorio (CA-F6-7, R9 — idempotente vía reminded_at)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_remind_publishes_once_idempotent(fake_db):
    """R9: 202 publica UNA vez; el segundo remind no re-publica (idempotente)."""
    fake_db.appointments = [_make_appointment(id=1, status="confirmada")]
    publish = AsyncMock(return_value=True)

    first = await remind(fake_db, TENANT, 1, publish=publish)
    assert first["published"] is True
    publish.assert_awaited_once()
    assert publish.await_args.kwargs["appointment_id"] == 1
    assert publish.await_args.kwargs["tenant_id"] == TENANT

    second = await remind(fake_db, TENANT, 1, publish=publish)
    assert second["published"] is False  # reminded_at ya seteado
    assert publish.await_count == 1  # nunca re-envía


@pytest.mark.asyncio
async def test_remind_non_confirmed_422(fake_db):
    """Solo citas confirmadas reciben recordatorio."""
    fake_db.appointments = [_make_appointment(id=1, status="solicitada")]
    with pytest.raises(Exception) as exc:
        await remind(fake_db, TENANT, 1)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_find_reminders_due_window(fake_db):
    """R9: job diario → solo confirmadas a ≤24h sin reminded_at."""
    now = datetime.now(UTC)
    soon = _make_appointment(
        id=1, status="confirmada", starts_at=now + timedelta(hours=6),
    )
    late = _make_appointment(
        id=2, status="confirmada", starts_at=now + timedelta(hours=48),
    )
    reminded = _make_appointment(
        id=3, status="confirmada", starts_at=now + timedelta(hours=2),
        reminded_at=now,
    )
    fake_db.appointments = [soon, late, reminded]
    due = await find_reminders_due(fake_db, TENANT)
    assert [d["id"] for d in due] == [1]


# ═══════════════════════════════════════════════════════════════
# Skills de voz (CA-F6-8, D5 — R1/R6/R10)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_voice_skill_reservar_source_and_call_id(fake_db):
    """CA-F6-8: la IA reserva con source='voice_ai' + call_id (R6 trazabilidad)."""
    fake_db.tables = [_make_table(id=7, capacity=6)]
    fake_db.queue_overlap([])
    result = await AppointmentSkills.reservar(
        fake_db, TENANT,
        nombre="Pedro", telefono="999000111", fecha="2026-08-25",
        hora="20:30", personas=3, call_id="SIP-F6.777",
    )
    assert result["ok"] is True
    appt = fake_db.appointments[0]
    assert appt.source == "voice_ai"
    assert appt.call_id == "SIP-F6.777"
    assert appt.customer_name == "Pedro"
    assert result["appointment"]["table_id"] == 7


@pytest.mark.asyncio
async def test_voice_skill_reservar_409_offers_real_alternatives(fake_db):
    """R1/CA-F6-9: sin mesa libre → ok=False + alternativas REALES (no inventa)."""
    fake_db.tables = [_make_table(id=7, capacity=4)]
    fake_db.queue_overlap([1])  # la única mesa ocupada en el rango
    result = await AppointmentSkills.reservar(
        fake_db, TENANT,
        nombre="Pedro", telefono="999000111", fecha="2026-08-25",
        hora="20:30", personas=2, call_id="SIP-F6.888",
    )
    assert result["ok"] is False
    assert result["reason"] == "no_disponible"
    assert len(fake_db.appointments) == 0  # jamás crea una cita fantasma
    # alternativas: slots REALES del día (otra hora de la misma mesa)
    assert len(result["alternatives"]) == 21
    assert "alternatives" in result


@pytest.mark.asyncio
async def test_voice_skill_consultar_disponibilidad(fake_db):
    """R1: consultar_disponibilidad(fecha, personas) → slots reales."""
    fake_db.tables = [_make_table(id=1, number="M1", capacity=4)]
    result = await AppointmentSkills.consultar_disponibilidad(
        fake_db, TENANT, "2026-08-25", 2,
    )
    assert result["ok"] is True
    assert result["fecha"] == "2026-08-25"
    assert result["personas"] == 2
    assert len(result["slots"]) == 21  # ventana completa real


@pytest.mark.asyncio
async def test_voice_skill_confirmar_transitions(fake_db):
    """D5: confirmar() → solicitada→confirmada (mismo contrato staff)."""
    table = _make_table(id=7)
    fake_db.tables = [table]
    fake_db.appointments = [_make_appointment(id=1, table_id=7, source="voice_ai")]
    publish = AsyncMock(return_value=True)
    with patch("app.services.appointments_service._publish_confirmed", publish):
        result = await AppointmentSkills.confirmar(fake_db, TENANT, 1)
    assert result["ok"] is True
    assert result["appointment"]["status"] == "confirmada"
    assert table.status == "reserved"  # espejo D1
    publish.assert_awaited_once()


def test_state_machine_taking_reservation():
    """D5: greeting + reserva → taking_reservation → confirming → hangup."""
    sm = ConversationStateMachine()
    assert sm.next_state("greeting", reservation_requested=True) == "taking_reservation"
    assert sm.next_state("taking_reservation") == "confirming"
    assert sm.next_state("confirming", confirmed=True) == "hangup"
    # pedido normal sigue igual (F3 intacta)
    assert sm.next_state("greeting") == "taking_order"
    # transferencia funciona desde taking_reservation
    assert sm.next_state("taking_reservation", transfer_reason="complaint") == "transfer"


def test_state_for_transcript_reservation_intent():
    """El transcript de reserva sugiere taking_reservation (D5)."""
    assert _state_for_transcript("quiero reservar una mesa para mañana") == "taking_reservation"
    assert _state_for_transcript("quiero un ceviche mixto") == "taking_order"


def test_llm_parse_reservation_minimal_data():
    """R10: el LLM determinista extrae fecha/hora/personas/nombre/teléfono."""
    llm = DeterministicLLMClient()
    res = llm.parse_reservation(
        "quiero reservar para 4 personas el 20 de agosto a las 7:30 pm, "
        "mi nombre es Pedro y mi celular 999000111"
    )
    assert res["fecha"] == "2026-08-20"
    assert res["hora"] == "19:30"
    assert res["personas"] == 4
    assert res["nombre"] == "Pedro"
    assert res["telefono"] == "999000111"

    incomplete = llm.parse_reservation("hola buenas noches")
    assert incomplete["fecha"] is None and incomplete["hora"] is None


# ═══════════════════════════════════════════════════════════════
# Migración 0021_appointments (CA-F6-11) — BD de test real
# ═══════════════════════════════════════════════════════════════

# Estado inicial: F5 (0020) aplicada — companies/users/tables/call_records
# mínimos para que los FKs y el ALTER del CHECK de ai_state funcionen.
_F5_0020_SCHEMA = """
CREATE TABLE alembic_version (version_num VARCHAR(100) NOT NULL);
INSERT INTO alembic_version (version_num) VALUES ('0020_assistant');
CREATE TABLE companies (
  id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, ruc VARCHAR(20) UNIQUE NOT NULL,
  settings JSONB, created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now()
);
CREATE TABLE users (
  id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL, full_name VARCHAR(150) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'viewer', tenant_id INTEGER REFERENCES companies(id),
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE tables (
  id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  number VARCHAR(10) NOT NULL, capacity INTEGER NOT NULL DEFAULT 4,
  status VARCHAR(20) NOT NULL DEFAULT 'available', section VARCHAR(50),
  guests INTEGER, waiter_name VARCHAR(100), opened_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_table_tenant_number UNIQUE (tenant_id, number),
  CONSTRAINT ck_tables_status CHECK (status IN ('available','occupied','reserved','cleaning'))
);
CREATE TABLE call_records (
  id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  external_call_id VARCHAR(64) NOT NULL, caller VARCHAR(32) NOT NULL,
  callee VARCHAR(32) NOT NULL, direction VARCHAR(10) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'ringing', started_at TIMESTAMPTZ NOT NULL,
  duration INTEGER NOT NULL DEFAULT 0, ai_state VARCHAR(20),
  CONSTRAINT uq_call_records_external_call_id UNIQUE (external_call_id),
  CONSTRAINT ck_call_records_ai_state CHECK (ai_state IN
    ('greeting','taking_order','clarifying','confirming','transfer','hangup','completed','failed'))
);
INSERT INTO companies (name, ruc) VALUES ('El Segoviano F6','88888888888');
INSERT INTO tables (tenant_id, number, capacity, status) VALUES (1, 'M1', 4, 'available');
"""


def _alembic_available() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "--version"],
            cwd=APP_ROOT, capture_output=True, timeout=30,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def _run_alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": MIGRATION_TEST_URL}
    env.setdefault("PYTHONPATH", str(APP_ROOT))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=APP_ROOT, env=env, capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} falló: {result.stderr.decode()[-2000:]}"
        )


async def _migration_engine():
    engine = create_async_engine(MIGRATION_TEST_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return engine


async def _reset_schema(engine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


async def _bootstrap_f5(engine) -> None:
    async with engine.connect() as conn:
        for stmt in _F5_0020_SCHEMA.split(";"):
            if stmt.strip():
                await conn.execute(text(stmt.strip()))


@pytest.mark.asyncio
async def test_migration_0021_up_down():
    """CA-F6-11: upgrade 0021 → tabla+CHECKs+UNIQUE+ai_state; downgrade 0020 revierte.

    Skip si la BD de test no está disponible o alembic no está instalado
    (la suite principal es mock-based; este test requiere Postgres real).
    """
    if not _alembic_available():
        pytest.skip("alembic no disponible — saltando migración up/down")
    try:
        engine = await _migration_engine()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"BD de test F6 no disponible ({exc}) — saltando migración up/down")
        return

    try:
        # 1) Estado inicial: F5 aplicada (0020) con mesas/empresa
        await _reset_schema(engine)
        await _bootstrap_f5(engine)

        # 2) upgrade → 0021_appointments
        await asyncio.to_thread(_run_alembic, "upgrade", "0021_appointments")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0021_appointments"

            assert (await conn.execute(
                text("SELECT to_regclass('public.appointments')")
            )).scalar() is not None

            cols = set((await conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='appointments'")
            )).scalars().all())
            for col in ("id", "tenant_id", "table_id", "customer_name", "customer_phone",
                        "guests", "starts_at", "duration_min", "status", "source",
                        "notes", "call_id", "created_by", "reminded_at",
                        "created_at", "updated_at"):
                assert col in cols, f"columna {col} no existe"

            checks = set((await conn.execute(
                text("SELECT conname FROM pg_constraint WHERE conrelid='appointments'::regclass")
            )).scalars().all())
            for ck in ("ck_appointments_guests", "ck_appointments_duration_min",
                       "ck_appointments_status", "ck_appointments_source",
                       "uq_appointments_tenant_table_start"):
                assert ck in checks, f"constraint {ck} no existe"

            idxs = set((await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='appointments'")
            )).scalars().all())
            assert "idx_appointments_tenant_date" in idxs
            assert "idx_appointments_tenant_state" in idxs

            # 3) CHECKs rechazan valores fuera del dominio (espejo service)
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO appointments (tenant_id, table_id, customer_name, "
                    "guests, starts_at, status, source) VALUES "
                    "(1, 1, 'X', 99, now(), 'solicitada', 'in_person')"
                ))
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO appointments (tenant_id, table_id, customer_name, "
                    "guests, starts_at, status, source) VALUES "
                    "(1, 1, 'X', 2, now(), 'hacking', 'in_person')"
                ))
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO appointments (tenant_id, table_id, customer_name, "
                    "guests, starts_at, status, source) VALUES "
                    "(1, 1, 'X', 2, now(), 'solicitada', 'fax')"
                ))
            # 4) F3 D5: ai_state acepta taking_reservation tras 0021
            await conn.execute(text(
                "INSERT INTO call_records (tenant_id, external_call_id, caller, callee, "
                "direction, status, started_at, ai_state) VALUES "
                "(1,'SIP-F6.1','999000111','100','inbound','ringing',now(),'taking_reservation')"
            ))
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO call_records (tenant_id, external_call_id, caller, callee, "
                    "direction, status, started_at, ai_state) VALUES "
                    "(1,'SIP-F6.2','999000111','100','inbound','ringing',now(),'hacking')"
                ))

        # 5) downgrade 0020 → revierte TODO, CHECK de F3 restaurado (sin D5)
        #    (limpia la fila con taking_reservation antes de restaurar el CHECK)
        async with engine.connect() as conn:
            await conn.execute(text("DELETE FROM call_records WHERE external_call_id LIKE 'SIP-F6.%'"))
        await asyncio.to_thread(_run_alembic, "downgrade", "0020_assistant")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0020_assistant"
            assert (await conn.execute(
                text("SELECT to_regclass('public.appointments')")
            )).scalar() is None
            # F3 vuelve a rechazar taking_reservation (CHECK original restaurado)
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO call_records (tenant_id, external_call_id, caller, callee, "
                    "direction, status, started_at, ai_state) VALUES "
                    "(1,'SIP-F6.3','999000111','100','inbound','ringing',now(),'taking_reservation')"
                ))

        # 6) dejar la BD de test consistente en head
        await asyncio.to_thread(_run_alembic, "upgrade", "0021_appointments")
    finally:
        await engine.dispose()
