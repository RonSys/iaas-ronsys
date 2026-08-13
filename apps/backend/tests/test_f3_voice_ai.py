"""
Tests Spec 06 — F3 "Recepcionista IA por Voz" (backend, §3.5/§3.6/§3.8).

Cubre (Fase 1 — sin Asterisk/proveedores externos):
  - Migración 0019_voice_ai: upgrade head (CA-F3-13), CHECKs rechazan
    valores inválidos (HU-F3-10), downgrade 0018 revierte SIN tocar F2.
  - Transcripción: upsert idempotente por call_id (D8/R3), transcription_fk
    (CA-F3-3), aislamiento de tenant (R8).
  - Estado IA: PATCH/GET ai-state + WS ai_call_state en vivo (R10).
  - Transferencia con contexto (D9/R2): motivo + context_summary +
    WS call.transferred + transferencia a extensión del operador (F2).
  - Cierre: cost_usd (R4), create_order solo con items confirmados (R7/R9,
    patrón convert_to_order F2), 409 conversión duplicada (R6).
  - Gobernanza: presupuesto diario + kill-switch → can_start=false (R4/R5,
    CA-F3-10/CA-F3-11).
  - Máquina de estados §3.6 + detección determinista de motivos.
  - Proveedores (D2/D3/D4): puertos abstractos + impls deterministas
    (echo STT, stub TTS, LLM determinista contra el menú real — R1).

Regla dura (precedente F2 D4): ningún test usa números personales del agente.
"""

import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.adapters.db.models.calls import (
    AI_STATES,
    TRANSFER_REASONS,
    CallRecord,
    CallTranscription,
)
from app.schemas.voice_ai import (
    AiCompleteIn,
    AiTransferIn,
    TranscriptionIn,
    VoiceAiSettings,
)
from app.services import voice_ai_service, voice_providers
from app.services.voice_ai_service import (
    ConversationStateMachine,
    budget_status,
    complete_call,
    detect_transfer_reason,
    estimate_call_cost,
    get_daily_cost_usd,
    save_transcription,
    transfer_call,
    update_ai_state,
)

APP_ROOT = Path(__file__).resolve().parents[1]
# BD de test dedicada (nunca la de prod). En el contenedor de CI se inyecta
# F3_TEST_DATABASE_URL apuntando al postgres de la red interna.
MIGRATION_TEST_URL = os.environ.get(
    "F3_TEST_DATABASE_URL",
    "postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys_test",
)


# ═══════════════════════════════════════════════════════════════
# Helpers (estilo test_f2_calls.py)
# ═══════════════════════════════════════════════════════════════

def _res_one(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _res_sum(value):
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _make_record(external="SIP-F3.1", tenant=1, status="in_progress", **kw):
    rec = CallRecord(
        tenant_id=tenant, external_call_id=external, caller="999888777",
        callee="+5115551234", direction="inbound", status=status,
        started_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    rec.id = kw.pop("id", 7)
    for k, v in kw.items():
        setattr(rec, k, v)
    return rec


def _make_company(tenant=1, settings=None):
    company = MagicMock()
    company.id = tenant
    company.settings = settings or {}
    return company


class _FakeDB:
    """Mini-AsyncSession (estilo F2) + cola de resultados de execute()."""

    def __init__(self):
        self.records: dict[str, CallRecord] = {}
        self.transcriptions: list[CallTranscription] = []
        self.commits = 0
        self._next_id = 1
        self.results: list = []

    def queue(self, *results):
        self.results.extend(results)

    async def execute(self, stmt, *a, **kw):
        if self.results:
            return self.results.pop(0)
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        empty.scalars.return_value.all.return_value = []
        empty.scalar.return_value = None
        return empty

    def add(self, obj):
        obj.id = self._next_id
        self._next_id += 1
        if isinstance(obj, CallRecord):
            self.records[obj.external_call_id] = obj
        elif isinstance(obj, CallTranscription):
            self.transcriptions.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return obj


@pytest.fixture
def fake_db():
    return _FakeDB()


@pytest.fixture(autouse=True)
def _no_real_network():
    """Aísla WS/publish/create_order reales (R3: los eventos nunca bloquean)."""
    with (
        patch("app.services.voice_ai_service.manager.broadcast_to_calls", new_callable=AsyncMock) as bcast,
        patch("app.services.voice_ai_service.delivery_create_order", new_callable=AsyncMock) as create_order,
    ):
        yield {"broadcast": bcast, "create_order": create_order}


# ═══════════════════════════════════════════════════════════════
# Transcripción (D8/R3 — upsert idempotente, CA-F3-3, R8)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_save_transcription_creates_and_links_fk(fake_db):
    """POST /transcript: crea call_transcriptions y llena transcription_fk (D8)."""
    record = _make_record()
    fake_db.queue(_res_one(record), _res_one(None))  # llamada + transcripción existente

    out = await save_transcription(fake_db, 1, "SIP-F3.1", {
        "provider": "deepgram", "text": "quiero un ceviche mixto",
        "segments": [{"start": 0.0, "end": 2.5, "speaker": "caller", "text": "quiero un ceviche"}],
        "lang": "es-PE", "duration_sec": 42, "cost_estimate": 0.0123,
    })
    assert out["call_id"] == "SIP-F3.1"
    assert out["call_record_id"] == record.id
    assert out["provider"] == "deepgram"
    assert record.transcription_fk == out["id"]  # FK reservada por F2
    assert len(fake_db.transcriptions) == 1


@pytest.mark.asyncio
async def test_save_transcription_upserts_same_call(fake_db):
    """Streaming: dos POST del mismo external_call_id actualizan (no duplican)."""
    record = _make_record()
    trans = CallTranscription(
        tenant_id=1, call_id="SIP-F3.1", provider="deepgram",
        text="primera versión", lang="es-PE",
    )
    trans.id = 99
    fake_db.queue(_res_one(record), _res_one(trans))  # segunda llamada encuentra la existente

    out = await save_transcription(fake_db, 1, "SIP-F3.1", {
        "provider": "deepgram", "text": "versión final del stream",
        "duration_sec": 42, "cost_estimate": 0.02,
    })
    assert out["id"] == 99
    assert out["text"] == "versión final del stream"
    assert len(fake_db.transcriptions) == 0  # no se creó otra (upsert)


@pytest.mark.asyncio
async def test_save_transcription_cross_tenant_404(fake_db):
    """R8: la transcripción de una llamada de otro tenant → 404."""
    fake_db.queue(_res_one(None))  # llamada no encontrada para ese tenant
    with pytest.raises(Exception) as exc:
        await save_transcription(fake_db, 2, "SIP-F3.1", {
            "provider": "deepgram", "text": "hola",
        })
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_transcription_not_found(fake_db):
    """CA-F3-3: sin transcripción → 404 (no inventa)."""
    record = _make_record()
    fake_db.queue(_res_one(record), _res_one(None))
    from app.services.voice_ai_service import get_transcription
    with pytest.raises(Exception) as exc:
        await get_transcription(fake_db, 1, "SIP-F3.1")
    assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Estado IA (R10 — PATCH/GET ai-state + WS en vivo)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_ai_state_persists_and_broadcasts(fake_db, _no_real_network):
    """PATCH ai-state: persiste y emite WS ai_call_state (R10, §3.5.2)."""
    record = _make_record()
    fake_db.queue(
        _res_one(record),          # resolve call
        _res_one(None),            # _state_out: transcripción
        _res_one(_make_company()),  # _state_out: budget_status → company
        _res_sum(0),               # _state_out: budget_status → suma diaria
    )
    out = await update_ai_state(fake_db, 1, "SIP-F3.1", {"state": "taking_order"})
    assert record.ai_state == "taking_order"
    assert out["ai_state"] == "taking_order"
    assert out["budget"]["can_start"] is False  # settings default: enabled=false

    bcast = _no_real_network["broadcast"]
    event_call = bcast.await_args_list[-1]
    assert event_call.args[0] == 1
    assert event_call.args[1] == "ai_call_state"
    assert event_call.args[2]["external_call_id"] == "SIP-F3.1"


@pytest.mark.asyncio
async def test_update_ai_state_invalid_state_422(fake_db):
    """Estado fuera del dominio → 422 (blinda el CHECK de BD)."""
    fake_db.queue(_res_one(_make_record()))
    with pytest.raises(Exception) as exc:
        await update_ai_state(fake_db, 1, "SIP-F3.1", {"state": "hacking"})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_ai_state_includes_cost_and_transcription(fake_db):
    """GET ai-state: costo acumulado + transcripción + contexto (R10)."""
    record = _make_record(cost_usd=0.75, ai_state="confirming")
    trans = MagicMock()
    trans.id = 5
    trans.text = "quiero 2 ceviches"
    fake_db.queue(
        _res_one(record),
        _res_one(trans),
        _res_one(_make_company(settings={"voice_ai": {"enabled": True, "budget": {"daily_budget_usd": 10.0}}})),
        _res_sum(2.5),
    )
    out = await voice_ai_service.get_ai_state(fake_db, 1, "SIP-F3.1")
    assert out["ai_state"] == "confirming"
    assert out["cost_usd"] == 0.75
    assert out["transcription_id"] == 5
    assert out["budget"]["daily_spent_usd"] == 2.5
    assert out["budget"]["can_start"] is True


# ═══════════════════════════════════════════════════════════════
# Transferencia a humano (D9/R2 — POST /transfer)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_transfer_sets_state_reason_and_broadcasts(fake_db, _no_real_network):
    """Transfer: ai_state=transfer + motivo + WS call.transferred (D9)."""
    record = _make_record()
    fake_db.queue(_res_one(record), _res_one(_make_company(settings={
        "calls": {"extensions": ["6001", "6002"]},
    })))
    out = await transfer_call(fake_db, 1, "SIP-F3.1", {
        "reason": "complaint",
        "context_summary": "Cliente molesto por demora, pidió 2 ceviches",
        "priority": "high",
    })
    assert record.ai_state == "transfer"
    assert record.transfer_reason == "complaint"
    assert out["transferred_to"] == "6001"  # F2 calls.extensions
    assert out["via"] == "sip"

    bcast = _no_real_network["broadcast"]
    events = [c.args[1] for c in bcast.await_args_list]
    assert "call.transferred" in events
    assert "ai_call_state" in events
    # el evento de transferencia lleva el contexto (panel delante del operador)
    transferred = [c for c in bcast.await_args_list if c.args[1] == "call.transferred"][0]
    assert transferred.args[2]["context_summary"] == "Cliente molesto por demora, pidió 2 ceviches"
    assert transferred.args[2]["transfer_reason"] == "complaint"


@pytest.mark.asyncio
async def test_transfer_invalid_reason_422(fake_db):
    """Motivo fuera del dominio → 422 (CHECK transfer_reason en BD)."""
    fake_db.queue(_res_one(_make_record()))
    with pytest.raises(Exception) as exc:
        await transfer_call(fake_db, 1, "SIP-F3.1", {"reason": "other"})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_transfer_fallback_callee_without_extensions(fake_db):
    """Sin calls.extensions configuradas → transferred_to = callee (F2)."""
    record = _make_record(callee="100")
    fake_db.queue(_res_one(record), _res_one(_make_company(settings={})))
    out = await transfer_call(fake_db, 1, "SIP-F3.1", {"reason": "user_requested"})
    assert out["transferred_to"] == "100"


# ═══════════════════════════════════════════════════════════════
# Cierre (R4/R7/R9 — POST /complete)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_complete_persists_cost(fake_db):
    """Complete sin order: persiste cost_usd + ai_state=completed (R4)."""
    record = _make_record(status="in_progress")
    fake_db.queue(_res_one(record))
    out = await complete_call(fake_db, 1, "SIP-F3.1", {
        "duration_sec": 180, "cost_usd": 0.45, "state": "completed",
    })
    assert record.ai_state == "completed"
    assert float(record.cost_usd) == 0.45
    assert record.duration == 180
    assert out["converted_order_id"] is None
    assert out["tracking_code"] is None


@pytest.mark.asyncio
async def test_complete_with_order_creates_order(fake_db, _no_real_network):
    """CA-F3-1: complete con items confirmados → create_order + converted_order_id (R9)."""
    record = _make_record()
    delivery_order = MagicMock()
    delivery_order.id = 42

    async def _fake_create(db, tenant, data):
        assert data["payment"]["method"] == "cash"  # R7: contraentrega default
        return {"tracking_code": "DLV-f3test01", "sale_id": 99,
                "sale_number": "V-0001", "status": "received", "totals": {}}

    async def _fake_delivery_order(db, tenant, sale_id):
        return delivery_order

    fake_db.queue(_res_one(record))
    with (
        patch("app.services.voice_ai_service.delivery_create_order", side_effect=_fake_create),
        patch("app.services.voice_ai_service._delivery_order_id_for_sale", side_effect=_fake_delivery_order),
    ):
        out = await complete_call(fake_db, 1, "SIP-F3.1", {
            "duration_sec": 210, "cost_usd": 0.55, "state": "completed",
            "order": {
                "zone_id": 3,
                "items": [{"menu_item_id": 10, "quantity": 2}],
                "customer": {"name": "Pedro", "phone": "999888777", "address": "Av. Canto Grande 1234, SJL"},
                "payment": {"method": "cash"},
            },
        })
    assert record.converted_order_id == 42
    assert out["tracking_code"] == "DLV-f3test01"
    assert out["sale_id"] == 99
    assert record.ai_state == "completed"

    # WS call.converted (R9/R10)
    bcast = _no_real_network["broadcast"]
    assert "call.converted" in [c.args[1] for c in bcast.await_args_list]


@pytest.mark.asyncio
async def test_complete_without_order_no_create(fake_db, _no_real_network):
    """Sin items confirmados → create_order NUNCA se llama (R7)."""
    record = _make_record()
    fake_db.queue(_res_one(record))
    await complete_call(fake_db, 1, "SIP-F3.1", {"cost_usd": 0.1, "state": "completed"})
    _no_real_network["create_order"].assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_already_converted_409(fake_db):
    """R6: segunda conversión de la misma llamada → 409."""
    record = _make_record(converted_order_id=42)
    fake_db.queue(_res_one(record))
    with pytest.raises(Exception) as exc:
        await complete_call(fake_db, 1, "SIP-F3.1", {
            "state": "completed",
            "order": {"zone_id": 3, "items": [{"menu_item_id": 10, "quantity": 1}],
                      "customer": {"address": "Av. Lima 123"}},
        })
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_complete_failed_with_order_422(fake_db):
    """state=failed + order → 422 (no se crea pedido de una llamada fallida)."""
    fake_db.queue(_res_one(_make_record()))
    with pytest.raises(Exception) as exc:
        await complete_call(fake_db, 1, "SIP-F3.1", {
            "state": "failed", "order": {"items": [{"menu_item_id": 1, "quantity": 1}]},
        })
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_complete_missing_zone_422(fake_db, _no_real_network):
    """Sin zona y sin distrito inferible → 422 (patrón F2, D7)."""
    record = _make_record()
    fake_db.queue(_res_one(record))
    with (
        patch("app.services.voice_ai_service.suggest_zone_by_address", new_callable=AsyncMock, return_value=None),
    ):
        with pytest.raises(Exception) as exc:
            await complete_call(fake_db, 1, "SIP-F3.1", {
                "state": "completed",
                "order": {"items": [{"menu_item_id": 1, "quantity": 1}],
                          "customer": {"address": "Sin distrito conocido"}},
            })
    assert exc.value.status_code == 422
    _no_real_network["create_order"].assert_not_awaited()


# ═══════════════════════════════════════════════════════════════
# Gobernanza de costo (R4/R5/D10 — kill-switch + presupuesto)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_budget_status_kill_switch_disables(fake_db):
    """R5/CA-F3-10: kill_switch=true → can_start=false (ring_operator)."""
    fake_db.queue(
        _res_one(_make_company(settings={"voice_ai": {"enabled": True, "kill_switch": True}})),
        _res_sum(0),
    )
    st = await budget_status(fake_db, 1)
    assert st["can_start"] is False
    assert st["kill_switch"] is True


@pytest.mark.asyncio
async def test_budget_status_daily_exceeded_disables(fake_db):
    """R4/CA-F3-8/CA-F3-11: tope diario alcanzado → can_start=false."""
    fake_db.queue(
        _res_one(_make_company(settings={
            "voice_ai": {"enabled": True, "budget": {"daily_budget_usd": 10.0}},
        })),
        _res_sum(10.0),  # acumulado del día == tope
    )
    st = await budget_status(fake_db, 1)
    assert st["budget_exceeded"] is True
    assert st["can_start"] is False


@pytest.mark.asyncio
async def test_budget_status_disabled_tenant(fake_db):
    """CA-F3-11: enabled=false → la IA jamás arranca."""
    fake_db.queue(
        _res_one(_make_company(settings={})),
        _res_sum(0),
    )
    st = await budget_status(fake_db, 1)
    assert st["enabled"] is False
    assert st["can_start"] is False


@pytest.mark.asyncio
async def test_daily_cost_sums_only_tenant(fake_db):
    """get_daily_cost_usd: suma el cost_usd del día (query tenant-scoped)."""
    fake_db.queue(_res_sum(3.25))
    total = await get_daily_cost_usd(fake_db, 1)
    assert total == 3.25


def test_estimate_call_cost_and_per_minute():
    """R4: estimador por minuto."""
    assert estimate_call_cost(60, 0.15) == 0.15
    assert estimate_call_cost(180, 0.15) == 0.45
    assert estimate_call_cost(None, 0.15) == 0.0
    assert voice_ai_service.per_minute_exceeded(0.5, 60, 0.15) is True
    assert voice_ai_service.per_minute_exceeded(0.1, 60, 0.15) is False


# ═══════════════════════════════════════════════════════════════
# Máquina de estados (§3.6) + detección de motivos (R2)
# ═══════════════════════════════════════════════════════════════

def test_state_machine_happy_path():
    sm = ConversationStateMachine(max_clarify_attempts=2)
    assert sm.next_state("greeting") == "taking_order"
    assert sm.next_state("taking_order") == "confirming"
    assert sm.next_state("confirming", confirmed=True) == "hangup"


def test_state_machine_clarify_then_transfer():
    """HU-F3-02: 1ª captura fallida + 1 repregunta fallida = transfer low_confidence."""
    sm = ConversationStateMachine(max_clarify_attempts=2)
    assert sm.next_state("taking_order", clarify_needed=True) == "clarifying"
    assert sm.remaining_clarify_attempts == 1
    assert sm.next_state("clarifying", clarify_needed=True) == "transfer"


def test_state_machine_clarify_resolved():
    sm = ConversationStateMachine(max_clarify_attempts=2)
    assert sm.next_state("taking_order", clarify_needed=True) == "clarifying"
    # resuelto con items → confirmar; sin items → seguir tomando
    assert sm.next_state("clarifying", clarify_resolved=True) == "confirming"
    sm2 = ConversationStateMachine()
    sm2.clarify_attempts = 1
    assert sm2.next_state("clarifying", clarify_resolved=False) == "taking_order"


def test_state_machine_transfer_from_any_state():
    sm = ConversationStateMachine()
    for current in ("greeting", "taking_order", "clarifying", "confirming"):
        assert sm.next_state(current, transfer_reason="complaint") == "transfer"
    # terminales no transitan
    assert sm.next_state("hangup", transfer_reason="complaint") == "hangup"
    assert sm.next_state("transfer") == "transfer"


def test_detect_transfer_reason_keywords():
    assert detect_transfer_reason("esto es carísimo, quiero quejarme") == "complaint"
    assert detect_transfer_reason("demoraron demasiado mi pedido") == "complaint"
    assert detect_transfer_reason("pásame con una persona por favor") == "user_requested"
    assert detect_transfer_reason("quiero hablar con alguien") == "user_requested"
    assert detect_transfer_reason("¿me prestas plata?") == "out_of_domain"
    assert detect_transfer_reason("¿cuál es tu nombre real?") == "out_of_domain"
    assert detect_transfer_reason("¿venden chicha?") == "out_of_domain"
    # pedido normal → sin transferencia
    assert detect_transfer_reason("quiero un ceviche mixto y una jalea") is None
    assert detect_transfer_reason(None) is None
    assert detect_transfer_reason("") is None


# ═══════════════════════════════════════════════════════════════
# Contexto del agente (R1 — solo menú real)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_build_conversation_context_uses_real_menu(fake_db):
    """HU-F3-04: el contexto = output REAL de get_public_menu/zones (nada hardcodeado)."""
    menu = {
        "tenant_name": "El Segoviano",
        "delivery_window": {"from": "19:00", "to": "24:00"},
        "currency": "PEN",
        "sections": [{"id": 1, "name": "Ceviches", "items": [
            {"id": 10, "name": "Ceviche Mixto", "price": 32.0, "modifiers": []},
        ]}],
        "promotions": [],
    }
    zones = [{"id": 3, "name": "Zona 1", "districts": ["Canto Grande", "Montenegro"]}]
    fake_db.queue(_res_one(_make_company(settings={"voice_ai": {"enabled": True}})))
    with (
        patch("app.services.voice_ai_service.get_public_menu", new_callable=AsyncMock, return_value=menu),
        patch("app.services.voice_ai_service.get_public_zones", new_callable=AsyncMock, return_value=zones),
    ):
        ctx = await voice_ai_service.build_conversation_context(fake_db, 1)
    assert ctx["sections"][0]["items"][0]["price"] == 32.0
    assert ctx["zones"][0]["districts"] == ["Canto Grande", "Montenegro"]
    assert ctx["payment_method"] == "cash"  # R7 default
    assert "no_inventar" in ctx["rules"]
    prompt = voice_ai_service.format_context_for_llm(ctx)
    assert '"Ceviche Mixto"' in prompt
    assert "32.0" in prompt


# ═══════════════════════════════════════════════════════════════
# Proveedores (D2/D3/D4 — puertos + impls deterministas de Fase 1)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_echo_stt_provider():
    stt = voice_providers.EchoSTTProvider(text="quiero un ceviche mixto")
    result = await stt.transcribe()
    assert result.text == "quiero un ceviche mixto"
    assert result.cost_estimate == 0.001


@pytest.mark.asyncio
async def test_local_tts_stub():
    tts = voice_providers.LocalTTSProvider(out_dir="/tmp/f3_tts")
    result = await tts.synthesize("Buenas noches")
    assert result.path.startswith("/tmp/f3_tts/tts_")
    assert result.path.endswith(".wav")


def test_deterministic_llm_parses_order_from_real_menu():
    """R1: el LLM determinista solo matchea items del menú real (CA-F3-12)."""
    menu = {
        "sections": [{"name": "Ceviches", "items": [
            {"id": 10, "name": "Ceviche Mixto", "price": 32.0, "modifiers": [
                {"id": 1, "name": "Choclo extra", "price_adjustment": 3.0},
            ]},
            {"id": 11, "name": "Jalea Mixta", "price": 38.0, "modifiers": []},
        ]}],
    }
    llm = voice_providers.DeterministicLLMClient(menu=menu)
    order = llm.parse_order("quiero 2 ceviches mixtos y una jalea mixta con choclo extra")
    assert order["matched"] is True
    ids = {i["menu_item_id"]: i["quantity"] for i in order["items"]}
    assert ids == {10: 2, 11: 1}
    assert any(m["name"] == "Choclo extra" for m in order["modifiers"])

    # item fuera del menú → jamás se confirma (HU-F3-04)
    no_match = llm.parse_order("quiero un lomo saltado")
    assert no_match["matched"] is False
    assert no_match["items"] == []


@pytest.mark.asyncio
async def test_deterministic_voice_provider_respond():
    """Pipeline F1: STT→LLM→TTS + motivo de transferencia detectado (R2)."""
    provider = voice_providers.DeterministicVoiceProvider(
        stt=voice_providers.EchoSTTProvider(text="esto es carísimo, quiero quejarme"),
    )
    result = await provider.respond(context={"sections": []})
    assert result["transfer_reason"] == "complaint"
    assert result["state"] == "transfer"
    assert result["audio_path"].endswith(".wav")
    assert result["cost_usd"] > 0


def test_deterministic_llm_extracts_address_and_phone():
    llm = voice_providers.DeterministicLLMClient()
    order = llm.parse_order("av. Canto Grande 1234, San Juan de Lurigancho, mi nombre es Pedro y mi celular 999111222")
    assert order["address"] and "Canto Grande" in order["address"]
    assert order["customer"]["name"] == "Pedro"
    assert order["customer"]["phone"] == "999111222"


# ═══════════════════════════════════════════════════════════════
# Schemas (validación de dominio a nivel contrato)
# ═══════════════════════════════════════════════════════════════

def test_schema_transfer_reason_validated():
    AiTransferIn(reason="complaint", context_summary="x")
    with pytest.raises(ValidationError):
        AiTransferIn(reason="other")


def test_schema_complete_state_validated():
    AiCompleteIn(state="completed")
    AiCompleteIn(state="failed")
    with pytest.raises(ValidationError):
        AiCompleteIn(state="hacking")


def test_schema_transcription_validation():
    TranscriptionIn(provider="deepgram", text="hola")
    with pytest.raises(ValidationError):
        TranscriptionIn(provider="deepgram", text="")


def test_voice_ai_settings_defaults():
    s = VoiceAiSettings()
    assert s.enabled is False
    assert s.kill_switch is False
    assert s.budget.max_usd_per_minute == 0.15
    assert s.budget.daily_budget_usd == 10.0
    assert s.transfer.max_clarify_attempts == 2
    assert s.stt.provider == "whisper"
    assert s.tts.provider == "piper"
    assert s.payment_method == "cash"  # R7


# ═══════════════════════════════════════════════════════════════
# Migración 0019_voice_ai (CA-F3-13 / HU-F3-10) — BD de test real
# ═══════════════════════════════════════════════════════════════

# DDL de F2 (0018) replicado: el test arranca de "BD con call_records de F2
# aplicada" (HU-F3-10). No se usa `upgrade head` desde base porque el árbol
# de migraciones del repo tiene fallas PREEXISTENTES ajenas a F3 (seed admin
# sin company en 0002; revision_id de 0010 > varchar(32) de alembic_version;
# baseline 0000 con conexión propia que hace lock-timeout en BD vacía).
_F2_0018_SCHEMA = """
CREATE TABLE alembic_version (version_num VARCHAR(100) NOT NULL);
INSERT INTO alembic_version (version_num) VALUES ('0018_call_records');
CREATE TABLE companies (
  id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, ruc VARCHAR(20) UNIQUE NOT NULL,
  settings JSONB, created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now()
);
CREATE TABLE delivery_orders (
  id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  tracking_code VARCHAR(40) UNIQUE NOT NULL, sale_id INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'received'
);
CREATE TABLE call_records (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  external_call_id VARCHAR(64) NOT NULL, caller VARCHAR(32) NOT NULL,
  callee VARCHAR(32) NOT NULL, direction VARCHAR(10) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'ringing', started_at TIMESTAMPTZ NOT NULL,
  answered_at TIMESTAMPTZ, ended_at TIMESTAMPTZ, duration INTEGER NOT NULL DEFAULT 0,
  recording_path TEXT, transcription_fk INTEGER, metadata JSONB,
  converted_order_id INTEGER REFERENCES delivery_orders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL, updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_call_records_external_call_id UNIQUE (external_call_id),
  CONSTRAINT ck_call_records_direction CHECK (direction IN ('inbound','outbound')),
  CONSTRAINT ck_call_records_status CHECK (status IN
    ('ringing','in_progress','answered','missed','completed','failed')),
  CONSTRAINT ck_call_records_duration CHECK (duration >= 0)
);
CREATE INDEX idx_call_records_tenant_status ON call_records (tenant_id, status);
CREATE INDEX idx_call_records_tenant_started ON call_records (tenant_id, started_at);
INSERT INTO companies (name, ruc) VALUES ('El Segoviano Test','99999999999');
INSERT INTO call_records (tenant_id, external_call_id, caller, callee, direction, status,
  started_at, duration) VALUES (1,'SIP-LEGACY.1','999888777','+5115551234','inbound',
  'completed', now(), 120);
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
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        await engine.dispose()
        raise
    return engine


async def _reset_schema(engine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


async def _bootstrap_f2(engine) -> None:
    async with engine.connect() as conn:
        for stmt in _F2_0018_SCHEMA.split(";"):
            if stmt.strip():
                await conn.execute(text(stmt.strip()))


@pytest.mark.asyncio
async def test_migration_0019_up_down():
    """CA-F3-13: upgrade head → 0019_voice_ai; downgrade 0018 revierte TODO.

    Skip si la BD de test no está disponible o alembic no está instalado
    (la suite principal es mock-based; este test requiere Postgres real).
    """
    if not _alembic_available():
        pytest.skip("alembic no disponible — saltando migración up/down")
    try:
        engine = await _migration_engine()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"BD de test F3 no disponible ({exc}) — saltando migración up/down")
        return

    try:
        # 1) Estado inicial: F2 aplicada (0018) con una llamada legacy
        await _reset_schema(engine)
        await _bootstrap_f2(engine)

        # 2) upgrade head → 0019_voice_ai
        await asyncio.to_thread(_run_alembic, "upgrade", "head")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0019_voice_ai"

            table = (await conn.execute(
                text("SELECT to_regclass('public.call_transcriptions')")
            )).scalar()
            assert table is not None, "call_transcriptions no se creó"

            idx = (await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='call_transcriptions' "
                     "AND indexname='ix_call_transcriptions_call_id'")
            )).scalar()
            assert idx == "ix_call_transcriptions_call_id"

            cols = set((await conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='call_records'")
            )).scalars().all())
            for col in ("ai_state", "transfer_reason", "context_summary", "cost_usd"):
                assert col in cols, f"columna IA {col} no existe en call_records"

            checks = set((await conn.execute(
                text("SELECT conname FROM pg_constraint WHERE conrelid='call_records'::regclass")
            )).scalars().all())
            for ck in ("ck_call_records_ai_state", "ck_call_records_transfer_reason", "ck_call_records_cost_usd"):
                assert ck in checks, f"CHECK {ck} no existe"

            # filas previas: ai_state NULL, cost_usd=0 (HU-F3-10 — F2 intacta)
            row = (await conn.execute(
                text("SELECT ai_state, transfer_reason, cost_usd FROM call_records "
                     "WHERE external_call_id='SIP-LEGACY.1'")
            )).one()
            assert row[0] is None and row[1] is None and float(row[2]) == 0.0

        # 3) CHECKs rechazan valores fuera del dominio (HU-F3-10)
        async with engine.connect() as conn:
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO call_records (tenant_id, external_call_id, caller, callee, "
                    "direction, status, started_at, ai_state) VALUES "
                    "(1,'X-BAD.1','1','2','inbound','ringing',now(),'hacking')"
                ))
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO call_records (tenant_id, external_call_id, caller, callee, "
                    "direction, status, started_at, transfer_reason) VALUES "
                    "(1,'X-BAD.2','1','2','inbound','ringing',now(),'other')"
                ))

        # 4) downgrade 0018 → revierte TODO lo de F3, F2 intacta (CA-F3-13)
        await asyncio.to_thread(_run_alembic, "downgrade", "0018_call_records")
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            assert version == "0018_call_records"
            assert (await conn.execute(
                text("SELECT to_regclass('public.call_transcriptions')")
            )).scalar() is None
            cols = set((await conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='call_records'")
            )).scalars().all())
            assert "ai_state" not in cols and "cost_usd" not in cols
            # columnas de F2 siguen intactas
            for col in ("external_call_id", "transcription_fk", "converted_order_id"):
                assert col in cols

        # 5) dejar la BD de test consistente en head
        await asyncio.to_thread(_run_alembic, "upgrade", "head")
    finally:
        await engine.dispose()


async def test_router_handlers_await_bridge_tenant(monkeypatch):
    """Regresión: _bridge_tenant es async — ningún handler puede pasarlo sin await.

    Bug real QA 2026-08-13: 6 handlers llamaban `tenant_id = _bridge_tenant(...)`
    sin await → asyncpg DataError 500 ("coroutine object cannot be interpreted
    as an integer") en POST /complete (el flujo E2E del simulador no persistía).
    """
    import re

    src = Path(__file__).resolve().parents[1] / "app" / "routers" / "ai_calls.py"
    text = src.read_text()
    offenders = re.findall(r"tenant_id = (?!# )_bridge_tenant\(", text)
    assert not offenders, f"handlers sin await en _bridge_tenant: {len(offenders)}"
