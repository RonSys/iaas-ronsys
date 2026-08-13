"""
Tests F3 Fase 2a — voice_bridge.py (bridge ARI Stasis + simulador).

Cubre (SIN Asterisk real, SIN red — mocks/monkeypatch, precedente test_f2_calls):
  - Arranque con env mínimo: configuración desde env + stubs deterministas
    (echo STT / local_piper TTS / deterministic LLM) + fallback REST HTTP
    del cliente ARI (ari-py opcional).
  - Canal entrante: registra el call vía POST /api/v1/calls/events (F2),
    contesta (answer), reproduce el saludo TTS y setea ai_state=greeting.
  - Gobernanza R4/R5: budget_status consultado vía voice_ai_service
    (import directo, mismo proceso); budget agotado → NO contesta
    (answer no se llama) → ring_operator (continue_in from-internal).
  - Flujo simulado end-to-end: termina en POST /complete con `order`
    (items confirmados → create_order del service, R7/R9) o sin order.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services import voice_bridge
from app.services.voice_bridge import VoiceBridge, build_providers


# ═══════════════════════════════════════════════════════════════
# Arranque (env mínimo + factory de proveedores)
# ═══════════════════════════════════════════════════════════════

def test_bridge_arranca_con_env_minimo(monkeypatch):
    """El bridge se construye solo con env (sin red, sin Asterisk)."""
    # las constantes se leen al importar el módulo → parchear los atributos
    monkeypatch.setattr(voice_bridge, "ARI_HOST", "10.0.0.5")
    monkeypatch.setattr(voice_bridge, "ARI_PORT", 8089)
    monkeypatch.setattr(voice_bridge, "ARI_USER", "voice")
    monkeypatch.setattr(voice_bridge, "ARI_PASS", "voice_secret")
    monkeypatch.setattr(voice_bridge, "BACKEND_INTERNAL_URL", "http://10.0.0.9:8000")
    monkeypatch.setattr(voice_bridge, "STT_PROVIDER", "echo")
    monkeypatch.setattr(voice_bridge, "TTS_PROVIDER", "local")
    monkeypatch.setattr(voice_bridge, "LLM_PROVIDER", "deterministic")
    monkeypatch.setattr(voice_bridge, "STASIS_APP", "voice-receptionist")
    monkeypatch.setattr(voice_bridge, "TENANT_ID", 1)

    b = VoiceBridge()

    # ARI: cliente REST mínimo (fallback PoC — _base siempre HTTP REST)
    assert b.ari.host == "10.0.0.5"
    assert b.ari.port == 8089
    assert b.ari.user == "voice"
    assert b.ari._base == "http://10.0.0.5:8089/ari"

    # backend interno + app Stasis + tenant (MVP 1 tenant)
    assert b.backend.base_url == "http://10.0.0.9:8000"
    assert b.stasis_app == "voice-receptionist"
    assert b.tenant_id == 1

    # proveedores = stubs deterministas de Fase 1 (D2/D3/D4)
    assert b.stt.name == "echo"
    assert b.tts.name == "local_piper"
    assert b.llm.name == "deterministic"

    # saludo pre-generado (CA-F3-5: no depende del LLM)
    assert "gracias por llamar" in b.greeting.lower()


def test_build_providers_fallback_determinista(monkeypatch):
    """Proveedores reales no implementados en 2a → fallback determinista con warning."""
    monkeypatch.setattr(voice_bridge, "STT_PROVIDER", "deepgram")
    monkeypatch.setattr(voice_bridge, "TTS_PROVIDER", "elevenlabs")
    monkeypatch.setattr(voice_bridge, "LLM_PROVIDER", "groq")
    stt, tts, llm = build_providers()
    assert stt.name == "echo"
    assert tts.name == "local_piper"
    assert llm.name == "deterministic"


# ═══════════════════════════════════════════════════════════════
# Canal entrante (registro + greeting + gobernanza)
# ═══════════════════════════════════════════════════════════════

def _fake_channel(channel_id="1500000001.1", caller="999888777", exten="+5115551234"):
    return {
        "id": channel_id,
        "name": f"PJSIP/{caller}-00000001",
        "caller": {"name": "PEDRO", "number": caller},
        "dialplan": {"context": "from-pstn", "exten": exten},
    }


@pytest.mark.asyncio
async def test_canal_entrante_dispara_registro_y_greeting():
    """StasisStart → registro F2 + answer + saludo TTS + ai_state=greeting."""
    b = VoiceBridge()
    b.ari = AsyncMock()
    b.ari.answer = AsyncMock()
    b.ari.play = AsyncMock()
    b.ari.continue_in = AsyncMock()
    b.backend = AsyncMock()
    b.budget_checker = AsyncMock(return_value=True)

    result = await b.handle_incoming_channel(_fake_channel())

    assert result["attended"] is True
    assert result["ai_state"] == "greeting"

    # 1) registro del call (contrato F2 §3.5.2)
    b.backend.post_call_event.assert_awaited_once()
    event = b.backend.post_call_event.await_args.args[0]
    assert event["external_call_id"] == "1500000001.1"
    assert event["caller"] == "999888777"
    assert event["callee"] == "+5115551234"
    assert event["direction"] == "inbound"
    assert event["status"] == "ringing"

    # 2) atiende: answer + play del saludo TTS
    b.ari.answer.assert_awaited_once_with("1500000001.1")
    b.ari.play.assert_awaited_once()
    media = b.ari.play.await_args.args[1]
    assert media.startswith("sound:")  # audio del TTS stub

    # 3) ai_state=greeting (R10 panel en vivo)
    b.backend.patch_ai_state.assert_awaited_once()
    assert b.backend.patch_ai_state.await_args.args[0] == "1500000001.1"
    assert b.backend.patch_ai_state.await_args.args[1] == {"state": "greeting"}


@pytest.mark.asyncio
async def test_budget_agotado_no_contesta_y_ring_operator():
    """R4/R5: can_start=false → NO contesta (answer no se llama) → ring_operator."""
    b = VoiceBridge()
    b.ari = AsyncMock()
    b.ari.answer = AsyncMock()
    b.ari.play = AsyncMock()
    b.ari.continue_in = AsyncMock()
    b.backend = AsyncMock()
    b.budget_checker = AsyncMock(return_value=False)

    result = await b.handle_incoming_channel(_fake_channel(channel_id="1500000002.2"))

    assert result["attended"] is False
    assert result["reason"] == "budget"

    # el registro SÍ ocurre (el panel F2 ve la llamada entrante)
    b.backend.post_call_event.assert_awaited_once()
    # la IA no contesta ni saluda ni toca ai_state
    b.ari.answer.assert_not_awaited()
    b.ari.play.assert_not_awaited()
    b.backend.patch_ai_state.assert_not_awaited()
    # libera el canal al operador (R5, CA-F3-11)
    b.ari.continue_in.assert_awaited_once_with("1500000002.2", context="from-internal")


@pytest.mark.asyncio
async def test_budget_checker_consulta_voice_ai_service(monkeypatch):
    """Gobernanza: budget_status se consulta vía voice_ai_service (mismo proceso)."""
    fake_db = AsyncMock()  # close() async
    monkeypatch.setattr(voice_bridge, "_open_session", AsyncMock(return_value=fake_db))

    with patch(
        "app.services.voice_ai_service.budget_status",
        new_callable=AsyncMock,
        return_value={"can_start": False, "kill_switch": True},
    ) as bs:
        assert await voice_bridge._budget_checker_default(1) is False
        bs.assert_awaited_once_with(fake_db, 1)

    with patch(
        "app.services.voice_ai_service.budget_status",
        new_callable=AsyncMock,
        return_value={"can_start": True},
    ):
        assert await voice_bridge._budget_checker_default(1) is True


# ═══════════════════════════════════════════════════════════════
# Flujo simulado (scripts/simulate_voice_call.py — end-to-end sin Asterisk)
# ═══════════════════════════════════════════════════════════════

_SIM_TURNS = ["Hola, buenas noches", "Quiero 2 ceviches mixtos", "Sí, confirmo mi pedido"]
_SIM_CONTEXT = {
    "tenant_name": "El Segoviano (test)",
    "sections": [{"name": "Marinos", "items": [
        {"id": 10, "name": "Ceviche Mixto", "price": 38.0, "modifiers": []},
    ]}],
}


@pytest.mark.asyncio
async def test_flujo_simulado_termina_en_complete_con_create_order():
    """Sim completo: registro → saludo → turnos → POST /complete con order (R7/R9)."""
    b = VoiceBridge(simulated=True)
    b.backend = AsyncMock()
    b.budget_checker = AsyncMock(return_value=True)

    summary = await b.run_simulated_call(
        "f3-sim-12345", _SIM_TURNS, context=_SIM_CONTEXT, order_zone_id=3,
    )

    assert summary["attended"] is True
    assert summary["ended"] == "completed"
    assert summary["greeting_audio"] is not None  # TTS stub generó el saludo

    # registro ringing + in_progress (F2)
    events = [c.args[0] for c in b.backend.post_call_event.await_args_list]
    assert [e["status"] for e in events] == ["ringing", "in_progress"]
    assert all(e["external_call_id"] == "f3-sim-12345" for e in events)

    # ai_state=greeting al inicio (R10)
    states = [c.args[1] for c in b.backend.patch_ai_state.await_args_list]
    assert states[0] == {"state": "greeting"}

    # transcripción SIEMPRE (R3) — un POST por turno
    assert len(b.backend.post_transcript.await_args_list) == len(_SIM_TURNS)

    # cierre con order → create_order del service (Fase 1 lo testea): aquí
    # se valida que el bridge manda el pedido confirmado (R7/R9)
    b.backend.post_complete.assert_awaited_once()
    payload = b.backend.post_complete.await_args.args[1]
    assert payload["state"] == "completed"
    assert payload["order"]["zone_id"] == 3
    assert payload["order"]["items"] == [{"menu_item_id": 10, "quantity": 2, "modifiers": []}]
    assert payload["order"]["payment"]["method"] == "cash"  # R7: contraentrega
    assert payload["order"]["customer"]["phone"] == "999888777"
    assert summary["order"]["items"] == payload["order"]["items"]


@pytest.mark.asyncio
async def test_flujo_simulado_sin_confirmacion_no_crea_order():
    """Sin confirmación → complete sin order (no inventa pedido — R1/HU-F3-04)."""
    b = VoiceBridge(simulated=True)
    b.backend = AsyncMock()
    b.budget_checker = AsyncMock(return_value=True)

    summary = await b.run_simulated_call(
        "f3-sim-456", ["Hola, buenas noches", "Quiero 2 ceviches mixtos"],
        context=_SIM_CONTEXT, order_zone_id=3,
    )

    assert summary["ended"] == "hangup"
    assert "order" not in summary
    payload = b.backend.post_complete.await_args.args[1]
    assert "order" not in payload


@pytest.mark.asyncio
async def test_flujo_simulado_budget_agotado_no_contesta():
    """Sim con presupuesto agotado → no atiende y no cierra con complete."""
    b = VoiceBridge(simulated=True)
    b.backend = AsyncMock()
    b.budget_checker = AsyncMock(return_value=False)

    summary = await b.run_simulated_call("f3-sim-budget", ["Hola"])

    assert summary["attended"] is False
    assert summary["reason"] == "budget"
    b.backend.patch_ai_state.assert_not_awaited()
    b.backend.post_complete.assert_not_awaited()
