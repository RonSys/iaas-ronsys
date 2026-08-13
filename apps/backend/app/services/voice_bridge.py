"""
🎙️ Voice-Bridge — Recepcionista IA por Voz, Fase 2a (Spec 06 F3, §3.7).

Proceso separado (patrón del call-bridge F2: contenedor Python, sin API
propia). Conecta a **ARI Stasis** (control de canales) de Asterisk — bind
127.0.0.1 (D3) — y habla con el backend por HTTP interno:

  - ARI REST: POST /ari/channels/{id}/answer · /play · /continue ·
    DELETE /ari/channels/{id} · GET /ari/channels. Usa `ari-py` si está
    instalado; si no, el cliente HTTP mínimo de abajo (PoC).
  - Eventos Stasis: WS `GET /ari/events?app=voice-receptionist` (librería
    `websockets`, en requirements) o polling REST simple (env
    VOICE_BRIDGE_USE_WS=0, default) — lo que sea más simple y funcione.
  - Canal entrante: registra el call vía POST /api/v1/calls/events (contrato
    F2, upsert idempotente por external_call_id), consulta gobernanza
    (budget_status del service de Fase 1, import directo — mismo proceso) y
    SOLO si `can_start` contesta: answer + saludo TTS stub + ai_state=greeting.
    Si no puede atender → NO contesta: libera el canal al operador
    (POST /ari/channels/{id}/continue, ring_operator — R4/R5).
  - Bucle de turno mínimo (D4): STT (echo en 2a) → LLM determinista de
    Fase 1 → TTS stub → respuesta. La integración External Media RTP→WS
    queda como stub documentado `_handle_external_media` (Fase 2b).
  - Reconexión con backoff, logging estructurado, sin credenciales en logs.

Configuración (env, defaults SOLO desarrollo — nunca credenciales reales):
  ARI_HOST=127.0.0.1  ARI_PORT=8088  ARI_USER=ari_user  ARI_PASS=ari_secret
  BACKEND_INTERNAL_URL=http://127.0.0.1:8000
  SERVICE_TOKEN=<token del backend — openssl rand -hex 32>
  STT_PROVIDER=echo  TTS_PROVIDER=local  LLM_PROVIDER=deterministic
  STASIS_APP=voice-receptionist
  VOICE_BRIDGE_TENANT_ID=1        (MVP 1 tenant — R8 deriva por CallRecord)
  VOICE_BRIDGE_POLL_SECONDS=2.0   (intervalo de polling REST)
  VOICE_BRIDGE_USE_WS=0           (1 = WS /ari/events vía websockets)
  VOICE_BRIDGE_SIMULATED=0        (1 = modo simulado, sin Asterisk)

Entrypoint: python -m app.services.voice_bridge
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("voice_bridge")

# ─── Config (env) ───────────────────────────────────────────────

ARI_HOST = os.getenv("ARI_HOST", "127.0.0.1")
ARI_PORT = int(os.getenv("ARI_PORT", "8088"))
ARI_USER = os.getenv("ARI_USER", "ari_user")
ARI_PASS = os.getenv("ARI_PASS", "ari_secret")

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "")

STT_PROVIDER = os.getenv("STT_PROVIDER", "echo")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "local")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deterministic")

STASIS_APP = os.getenv("STASIS_APP", "voice-receptionist")
TENANT_ID = int(os.getenv("VOICE_BRIDGE_TENANT_ID", "1"))
POLL_SECONDS = float(os.getenv("VOICE_BRIDGE_POLL_SECONDS", "2.0"))
USE_WS = os.getenv("VOICE_BRIDGE_USE_WS", "0") == "1"
SIMULATED = os.getenv("VOICE_BRIDGE_SIMULATED", "0") == "1"
GREETING = os.getenv("VOICE_BRIDGE_GREETING", "")  # vacío → default del schema
SIM_ZONE_ID = int(os.getenv("VOICE_BRIDGE_SIM_ZONE_ID", "1"))

RECONNECT_BACKOFF = (1, 5, 15, 30, 60)  # segundos entre reintentos de conexión


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_greeting() -> str:
    """Saludo pre-generado (CA-F3-5: no depende del LLM) — default del schema."""
    try:
        from app.schemas.voice_ai import VoiceAiSettings
        return VoiceAiSettings().greeting
    except Exception:  # noqa: BLE001
        return (
            "Buenas noches, gracias por llamar. Esta llamada es atendida por un "
            "asistente automático. ¿Qué le ofrezco esta noche?"
        )


def _try_import_ari_py() -> Any:
    """`ari-py` si está disponible; si no → None (el bridge usa REST HTTP mínimo)."""
    try:
        import ari  # type: ignore  # noqa: F401 — dependencia opcional
        return ari
    except ImportError:
        return None


# ─── Cliente ARI mínimo (REST HTTP — PoC sin ari-py) ───────────

class AriClient:
    """Cliente ARI Stasis mínimo (fallback documentado si `ari-py` falta).

    Endpoints usados (Asterisk REST API):
      GET    /ari/channels                 → canales activos (polling)
      POST   /ari/channels/{id}/answer     → contesta el canal
      POST   /ari/channels/{id}/play       → reproduce media (saludo TTS)
      POST   /ari/channels/{id}/continue   → libera el canal al dialplan
                                             (ring_operator R5)
      DELETE /ari/channels/{id}            → cuelga (limpieza)
    Auth: HTTP Basic (ARI_USER:ARI_PASS). Fase 2b: ari-py/Stasis WS completo.
    """

    def __init__(self, host: str, port: int, user: str, secret: str):
        self.host = host
        self.port = port
        self.user = user
        self.secret = secret
        self.ari_py = _try_import_ari_py()
        self.uses_ari_py = self.ari_py is not None
        self._base = f"http://{host}:{port}/ari"

    def _url(self, channel_id: str, action: str) -> str:
        from urllib.parse import quote
        return f"{self._base}/channels/{quote(str(channel_id), safe='')}{action}"

    async def channels(self) -> list[dict]:
        """GET /ari/channels — canales activos (polling simple del PoC)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base}/channels", auth=(self.user, self.secret))
            resp.raise_for_status()
            return resp.json()

    async def answer(self, channel_id: str) -> dict:
        """POST /ari/channels/{id}/answer — levanta el canal."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self._url(channel_id, "/answer"), auth=(self.user, self.secret))
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def play(self, channel_id: str, media: str) -> dict:
        """POST /ari/channels/{id}/play?media=... — reproduce el audio del TTS."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self._url(channel_id, "/play"), params={"media": media},
                auth=(self.user, self.secret),
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def continue_in(self, channel_id: str, context: str | None = None,
                          extension: str | None = None, priority: int | None = None) -> dict:
        """POST /ari/channels/{id}/continue — saca el canal de Stasis al dialplan.

        Con `context=from-internal` el canal cae en el ruteo del operador
        (ring_operator — R5: la IA no contesta y el humano toma la llamada).
        """
        params: dict[str, Any] = {}
        if context:
            params["context"] = context
        if extension:
            params["extension"] = extension
        if priority is not None:
            params["priority"] = priority
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self._url(channel_id, "/continue"), params=params,
                auth=(self.user, self.secret),
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def hangup(self, channel_id: str) -> None:
        """DELETE /ari/channels/{id} — cuelga el canal (limpieza)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(self._url(channel_id, ""), auth=(self.user, self.secret))
            resp.raise_for_status()


# ─── Cliente backend interno (contrato F2/F3 — mismo estilo call_bridge) ──

class BackendClient:
    """HTTP interno al backend (R3: fire-and-forget, nunca rompe la llamada).

    Mismo contrato que el call-bridge de F2: X-Service-Token + upsert
    idempotente por external_call_id. Fallo → warning logueado (no raise).
    """

    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or BACKEND_INTERNAL_URL).rstrip("/")
        self.token = token if token is not None else SERVICE_TOKEN

    def _headers(self) -> dict:
        return {"X-Service-Token": self.token} if self.token else {}

    async def _request(self, method: str, path: str, payload: dict | None = None) -> dict | None:
        if not self.token:
            logger.warning("SERVICE_TOKEN vacío — %s %s no enviado", method, path)
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.request(
                    method, f"{self.base_url}{path}", json=payload, headers=self._headers(),
                )
                if resp.status_code >= 300:
                    logger.warning(
                        "backend %s %s → %s: %s", method, path, resp.status_code, resp.text[:200],
                    )
                    return None
                return resp.json() if resp.content else {}
        except Exception as exc:  # noqa: BLE001 — R3
            logger.warning("backend no disponible para %s %s: %s", method, path, exc)
            return None

    async def post_call_event(self, payload: dict) -> dict | None:
        """POST /api/v1/calls/events (contrato F2 §3.5.2)."""
        return await self._request("POST", "/api/v1/calls/events", payload)

    async def patch_ai_state(self, external_call_id: str, data: dict) -> dict | None:
        """PATCH /api/v1/calls/{id}/ai-state (§3.6, R10)."""
        return await self._request(
            "PATCH", f"/api/v1/calls/{external_call_id}/ai-state", data,
        )

    async def post_transcript(self, external_call_id: str, data: dict) -> dict | None:
        """POST /api/v1/calls/{id}/transcript (D8/R3 — transcripción siempre)."""
        return await self._request(
            "POST", f"/api/v1/calls/{external_call_id}/transcript", data,
        )

    async def post_transfer(self, external_call_id: str, data: dict) -> dict | None:
        """POST /api/v1/calls/{id}/transfer (D9/R2 — transferencia con contexto)."""
        return await self._request(
            "POST", f"/api/v1/calls/{external_call_id}/transfer", data,
        )

    async def post_complete(self, external_call_id: str, data: dict) -> dict | None:
        """POST /api/v1/calls/{id}/complete (R4/R7/R9 — cierre + create_order)."""
        return await self._request(
            "POST", f"/api/v1/calls/{external_call_id}/complete", data,
        )


# ─── Factory de proveedores (D2/D3/D4 — Fase 2a: stubs deterministas) ──

def build_providers(
    stt_name: str | None = None,
    tts_name: str | None = None,
    llm_name: str | None = None,
) -> tuple[Any, Any, Any]:
    """Construye (stt, tts, llm) según env.

    Fase 2a: SIEMPRE funcionan los stubs deterministas de Fase 1 (la suite
    corre sin faster-whisper/piper). Los nombres de proveedores reales se
    aceptan pero caen al stub con warning documentado (implementación real
    de los puertos = Fase 2b, misma firma — D2/D3/D4).
    """
    from app.services.voice_providers import (
        DeterministicLLMClient, EchoSTTProvider, LocalTTSProvider,
    )

    stt_name = (stt_name or STT_PROVIDER or "echo").lower()
    tts_name = (tts_name or TTS_PROVIDER or "local").lower()
    llm_name = (llm_name or LLM_PROVIDER or "deterministic").lower()

    stt: Any = EchoSTTProvider()
    if stt_name != "echo":
        logger.warning(
            "STT '%s' no implementado en Fase 2a — usando echo (determinista, D2)",
            stt_name,
        )

    tts: Any = LocalTTSProvider()
    if tts_name not in ("local", "piper", "edge-tts"):
        logger.warning(
            "TTS '%s' no implementado en Fase 2a — usando stub local_piper (D3)",
            tts_name,
        )

    llm: Any = DeterministicLLMClient()
    if llm_name != "deterministic":
        logger.warning(
            "LLM '%s' no implementado en Fase 2a — usando deterministic (D4, R1)",
            llm_name,
        )

    return stt, tts, llm


# ─── Gobernanza (R4/R5 — budget_status del service de Fase 1) ──

async def _open_session():
    """Sesión de la app (mismo proceso) o None si no hay BD disponible."""
    try:
        from app.adapters.db.database import get_session_factory
        return get_session_factory()()
    except Exception:  # noqa: BLE001
        return None


async def _budget_checker_default(tenant_id: int) -> bool:
    """Gobernanza R4/R5 — consulta `budget_status` vía voice_ai_service
    (import directo del service, mismo proceso — Fase 1).

    `can_start=false` (deshabilitado, kill_switch o tope diario superado) →
    el bridge NO contesta: libera el canal al operador (ring_operator,
    CA-F3-10/CA-F3-11). Sin BD disponible (proceso standalone de prueba) →
    loguea y atiende (default conservador del PoC, la llamada nunca se rompe).
    """
    try:
        from app.services.voice_ai_service import budget_status
        db = await _open_session()
        if db is None:
            logger.warning("sin sesión de BD — budget_status no consultable; se atiende (default PoC)")
            return True
        try:
            status = await budget_status(db, tenant_id)
            return bool(status.get("can_start", True))
        finally:
            await db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("budget_status falló (%s) — se atiende (default PoC)", exc)
        return True


# ─── Payloads / helpers ─────────────────────────────────────────

def _channel_to_event(channel: dict, status: str = "ringing") -> dict:
    """Canal ARI → payload POST /api/v1/calls/events (contrato F2 §3.5.2).

    En inbound el caller es el número del cliente (caller.number) y el
    callee el DID (dialplan.exten) — mismo criterio que el call-bridge F2.
    """
    caller = channel.get("caller") or {}
    dialplan = channel.get("dialplan") or {}
    channel_id = str(channel.get("id") or "")
    return {
        "external_call_id": channel_id,
        "caller": caller.get("number") or caller.get("name") or "anónimo",
        "callee": dialplan.get("exten") or "",
        "direction": "inbound",
        "status": status,
        "started_at": _now_iso(),
        "metadata": {
            "channel": channel.get("name") or channel_id,
            "source": "ari-stasis",
            "app": STASIS_APP,
        },
    }


def _media_for(path: str | None) -> str | None:
    """Path TTS → media ARI (sound:<nombre sin extensión>). None si no hay path."""
    if not path:
        return None
    import os
    stem = os.path.splitext(os.path.basename(path))[0]
    return f"sound:{stem}" if stem else None


def _is_confirmation(text: str, keywords: tuple[str, ...] | None = None) -> bool:
    """Heurística de confirmación para el flujo simulado (Fase 2a)."""
    norm = (text or "").lower()
    for k in (keywords or ("confirmo", "si, confirma", "sí, confirma", "si confirma",
                           "sí confirma", "dale", "ok", "esta bien", "está bien")):
        if k in norm:
            return True
    return False


# ─── Bridge principal ───────────────────────────────────────────

class VoiceBridge:
    """Orquestador del bridge de voz (Fase 2a).

    Inyectable para tests (ari/backend/providers/budget_checker) — sin red
    real: los mocks reemplazan los clientes HTTP.
    """

    def __init__(
        self,
        ari: AriClient | None = None,
        backend: BackendClient | None = None,
        providers: tuple | None = None,
        budget_checker=None,
        tenant_id: int | None = None,
        stasis_app: str | None = None,
        greeting: str | None = None,
        simulated: bool | None = None,
    ):
        self.ari = ari or AriClient(ARI_HOST, ARI_PORT, ARI_USER, ARI_PASS)
        self.backend = backend or BackendClient()
        self.stt, self.tts, self.llm = providers or build_providers()
        self.budget_checker = budget_checker or _budget_checker_default
        self.tenant_id = int(tenant_id if tenant_id is not None else TENANT_ID)
        self.stasis_app = stasis_app or STASIS_APP
        self.greeting = greeting or GREETING or _default_greeting()
        self.simulated = bool(simulated if simulated is not None else SIMULATED)
        self._handled: set[str] = set()      # channel ids ya procesados
        self.active_calls: dict[str, dict] = {}

    # ── Canal entrante (StasisStart / polling) ──

    async def handle_incoming_channel(self, channel: dict) -> dict:
        """Flujo de canal entrante (CA-F3-5): registro → gobernanza → saludo.

        1. Registra el call vía POST /events (F2 — el panel lo ve aunque la
           IA no conteste).
        2. Gobernanza R4/R5: budget_status (voice_ai_service, mismo proceso).
           `can_start=false` → NO contesta: ring_operator (continue al
           dialplan del operador).
        3. Atiende: answer + saludo TTS stub + play + ai_state=greeting.
        """
        channel_id = str(channel.get("id") or "")
        if not channel_id:
            return {"attended": False, "reason": "no_channel_id"}
        external_call_id = channel_id

        # 1) registro (upsert idempotente por external_call_id — R8)
        await self.backend.post_call_event(_channel_to_event(channel, status="ringing"))

        # 2) gobernanza ANTES de atender (R4/R5, CA-F3-10/CA-F3-11)
        can_start = await self.budget_checker(self.tenant_id)
        if not can_start:
            logger.info(
                "canal %s: presupuesto agotado/IA off → ring_operator (no contesta)",
                channel_id,
            )
            await self.ring_operator(channel_id)
            return {"attended": False, "reason": "budget", "external_call_id": external_call_id}

        # 3) atender + saludo (greeting pre-generado — no depende del LLM)
        try:
            await self.ari.answer(channel_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("answer ARI falló (canal %s): %s", channel_id, exc)
            return {"attended": False, "reason": "answer_failed", "external_call_id": external_call_id}

        tts_result = await self.tts.synthesize(self.greeting)
        media = _media_for(tts_result.path) or "sound:voice-receptionist-greeting"
        try:
            await self.ari.play(channel_id, media)
        except Exception as exc:  # noqa: BLE001
            logger.warning("play ARI falló (canal %s): %s", channel_id, exc)

        await self.backend.patch_ai_state(external_call_id, {"state": "greeting"})

        # stub External Media (Fase 2b — streaming RTP→WS)
        await self._handle_external_media(channel_id, ws_url=None)

        result = {"attended": True, "external_call_id": external_call_id, "ai_state": "greeting"}
        self.active_calls[channel_id] = result
        return result

    async def ring_operator(self, channel_id: str) -> None:
        """R5: la IA no atiende — libera el canal al dialplan del operador.

        ARI: POST /ari/channels/{id}/continue?context=from-internal (F2).
        En modo simulado solo loguea (no hay Asterisk).
        """
        if self.simulated:
            logger.info("sim: canal %s → ring_operator (sin Asterisk)", channel_id)
            return
        try:
            await self.ari.continue_in(channel_id, context="from-internal")
            logger.info("canal %s → ring_operator (from-internal)", channel_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ring_operator falló (canal %s): %s", channel_id, exc)

    async def on_event(self, event: dict) -> None:
        """Evento Stasis (WS /ari/events). PoC: StasisStart → atender; StasisEnd → limpieza."""
        etype = event.get("type")
        channel = event.get("channel") or {}
        channel_id = str(channel.get("id") or "")
        if etype == "StasisStart":
            if not channel_id or channel_id in self._handled:
                return
            self._handled.add(channel_id)
            try:
                await self.handle_incoming_channel(channel)
            except Exception as exc:  # noqa: BLE001
                logger.warning("fallo atendiendo canal %s: %s", channel_id, exc)
        elif etype == "StasisEnd":
            self._handled.discard(channel_id)
            self.active_calls.pop(channel_id, None)

    # ── Turno conversacional (D4: STT → LLM → TTS) ──

    async def run_turn(
        self, external_call_id: str, user_text: str, context: dict | None = None,
    ) -> dict:
        """Un turno completo: transcripción → LLM → respuesta TTS → backend.

        Fase 2a: STT echo (texto simulado) + LLM determinista Fase 1 + TTS
        stub. Detecta transferencia (R2) y espeja ai_state (§3.6).
        """
        from app.services.voice_providers import (
            _context_prompt, _state_for_transcript,
        )
        from app.services.voice_ai_service import detect_transfer_reason

        stt = self._stt_for(user_text)
        stt_result = await stt.transcribe()
        transcript = stt_result.text or ""

        await self.backend.post_transcript(external_call_id, {
            "provider": stt.name,
            "text": transcript or "…",
            "lang": "es-PE",
            "duration_sec": 15,
            "cost_estimate": stt_result.cost_estimate,
        })

        messages = [
            {"role": "system", "content": _context_prompt(context)},
            {"role": "user", "content": transcript},
        ]
        reply = await self.llm.complete(messages)
        tts_result = await self.tts.synthesize(reply)

        reason = detect_transfer_reason(transcript)
        if reason:
            state = "transfer"
            await self.backend.post_transfer(external_call_id, {
                "reason": reason,
                "context_summary": f"Cliente: {transcript}",
            })
        else:
            state = _state_for_transcript(transcript)
            await self.backend.patch_ai_state(external_call_id, {"state": state})

        return {
            "transcript": transcript,
            "reply": reply,
            "audio_path": tts_result.path,
            "cost_usd": round(stt_result.cost_estimate + tts_result.cost_estimate + 0.0005, 6),
            "transfer_reason": reason,
            "state": state,
        }

    def _stt_for(self, text: str):
        """STT del turno: echo con el texto simulado; proveedor real tal cual."""
        if getattr(self.stt, "name", "") == "echo":
            from app.services.voice_providers import EchoSTTProvider
            return EchoSTTProvider(text=text)
        return self.stt

    # ── Flujo simulado completo (validación end-to-end sin Asterisk) ──

    async def run_simulated_call(
        self,
        external_call_id: str,
        turns: list[str],
        context: dict | None = None,
        order_zone_id: int | None = None,
        confirm_keywords: tuple[str, ...] | None = None,
        turn_delay_sec: float = 0.0,
    ) -> dict:
        """Flujo completo en modo simulado (script scripts/simulate_voice_call.py).

        registro (ringing→in_progress) → gobernanza → saludo TTS stub →
        turnos (STT echo → LLM determinista → TTS stub) → POST /complete
        (con `order` si hubo items confirmados → create_order, R7/R9).

        `turn_delay_sec` > 0 pausa entre turnos (demo E2E visible en monitor).
        """
        # LLM determinista con el menú del contexto (R1: match contra datos reales)
        if hasattr(self.llm, "parse_order") and not getattr(self.llm, "_menu", None) and context:
            from app.services.voice_providers import DeterministicLLMClient
            self.llm = DeterministicLLMClient(menu=context)

        summary: dict[str, Any] = {
            "external_call_id": external_call_id,
            "attended": True,
            "turns": [],
        }

        # 1) registro (F2) — tenant_id explícito (el payload lleva el tenant;
        # si faltara, el backend resuelve por DID y en simulación el DID
        # +5115551234 pertenece a otro tenant sin zona/menú).
        base_event = {
            "external_call_id": external_call_id,
            "tenant_id": int(self.tenant_id),
            "caller": "999888777",
            "callee": "+5115551234",
            "direction": "inbound",
            "started_at": _now_iso(),
            "metadata": {"source": "simulador-f3", "app": STASIS_APP},
        }
        await self.backend.post_call_event({**base_event, "status": "ringing"})
        await self.backend.post_call_event({
            **base_event, "status": "in_progress", "answered_at": _now_iso(),
        })

        # 2) gobernanza (R4/R5)
        if not await self.budget_checker(self.tenant_id):
            summary["attended"] = False
            summary["reason"] = "budget"
            logger.info("sim %s: presupuesto agotado → ring_operator", external_call_id)
            await self.ring_operator(external_call_id)
            return summary

        # 3) saludo (CA-F3-5)
        tts_greet = await self.tts.synthesize(self.greeting)
        summary["greeting"] = self.greeting
        summary["greeting_audio"] = tts_greet.path
        await self.backend.patch_ai_state(external_call_id, {"state": "greeting"})

        # 4) turnos
        total_cost = 0.0
        parsed_items: list[dict] = []
        parsed_customer: dict = {}
        parsed_address: str | None = None
        confirmed = False
        for text in turns:
            if turn_delay_sec > 0 and summary["turns"]:
                await asyncio.sleep(turn_delay_sec)  # demo E2E visible
            turn = await self.run_turn(external_call_id, text, context=context)
            total_cost += turn["cost_usd"]
            summary["turns"].append(turn)
            if turn["transfer_reason"]:
                summary["ended"] = "transfer"
                summary["transfer_reason"] = turn["transfer_reason"]
                break
            order = self.llm.parse_order(text) if hasattr(self.llm, "parse_order") else {}
            if order.get("items"):
                parsed_items = order["items"]
                parsed_customer = order.get("customer") or {}
                parsed_address = order.get("address")
            if _is_confirmation(text, confirm_keywords):
                confirmed = True
                break

        # 5) cierre (R4/R7/R9)
        duration_sec = 30 + 15 * len(summary["turns"])
        complete_payload: dict[str, Any] = {
            "state": "completed",
            "duration_sec": duration_sec,
            "cost_usd": round(total_cost, 4),
        }
        if confirmed and parsed_items:
            complete_payload["order"] = {
                "zone_id": int(order_zone_id if order_zone_id is not None else SIM_ZONE_ID),
                "items": [
                    {"menu_item_id": it["menu_item_id"], "quantity": it["quantity"], "modifiers": []}
                    for it in parsed_items
                ],
                "customer": {
                    "name": parsed_customer.get("name"),
                    "phone": parsed_customer.get("phone") or "999888777",
                    "address": parsed_address or "Av. Simulada 123, Lima",
                },
                "payment": {"method": "cash"},  # R7: contraentrega
            }
            summary["order"] = complete_payload["order"]
        summary["complete"] = await self.backend.post_complete(external_call_id, complete_payload)
        summary["ended"] = summary.get("ended") or ("completed" if confirmed else "hangup")
        return summary

    # ── External Media (Fase 2b — stub documentado) ──

    async def _handle_external_media(self, channel_id: str, ws_url: str | None) -> dict:
        """Integración External Media RTP→WS (Fase 2b — NO implementada en 2a).

        Asterisk envía el audio del cliente por RTP a un socket del bridge
        (stasis_external_media) y el bridge lo reenvía por WS al STT en
        streaming. Aquí SOLO se registra el intento: la llamada no depende
        de esto (el bucle de turno de 2a es texto simulado / STT echo).
        """
        logger.info(
            "canal %s: external_media solicitado (ws=%s) — streaming RTP→WS en Fase 2b",
            channel_id, ws_url,
        )
        return {"attempted": False, "reason": "external_media_es_fase_2b", "channel_id": channel_id}


# ─── Bucles (polling REST + WS opcional) ────────────────────────

async def _poll_loop(bridge: VoiceBridge) -> None:
    """Polling REST simple (GET /ari/channels) — el PoC no depende del WS.

    Cada canal nuevo → handle_incoming_channel (dedup por `_handled`).
    """
    backoff_idx = 0
    while True:
        try:
            channels = await bridge.ari.channels()
            backoff_idx = 0
            for ch in channels or []:
                channel_id = str(ch.get("id") or "")
                if not channel_id or channel_id in bridge._handled:
                    continue
                bridge._handled.add(channel_id)
                try:
                    await bridge.handle_incoming_channel(ch)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("fallo atendiendo canal %s: %s", channel_id, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — reconexión con backoff
            delay = RECONNECT_BACKOFF[min(backoff_idx, len(RECONNECT_BACKOFF) - 1)]
            backoff_idx += 1
            logger.warning("poll ARI falló (%s) — reintento en %ss", exc, delay)
            await asyncio.sleep(delay)
            continue
        await asyncio.sleep(POLL_SECONDS)


async def _ws_events_loop(bridge: VoiceBridge) -> None:
    """WS ARI `/ari/events?app=voice-receptionist` (requiere `websockets`).

    Opcional (env VOICE_BRIDGE_USE_WS=1): el polling REST del PoC ya cubre
    el flujo; este loop es el camino productivo cuando hay WS estable.
    """
    try:
        import websockets  # noqa: F401 — requirements (14.1)
    except ImportError:
        logger.warning(
            "websockets no disponible — uso SOLO polling REST (VOICE_BRIDGE_USE_WS=1 requiere websockets)",
        )
        return
    url = (
        f"ws://{bridge.ari.host}:{bridge.ari.port}/ari/events"
        f"?app={bridge.stasis_app}&api_key={bridge.ari.user}:{bridge.ari.secret}"
    )
    backoff_idx = 0
    while True:
        try:
            async with websockets.connect(url, ping_interval=None) as ws:  # type: ignore
                backoff_idx = 0
                logger.info("WS ARI conectado (app=%s)", bridge.stasis_app)
                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    await bridge.on_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            delay = RECONNECT_BACKOFF[min(backoff_idx, len(RECONNECT_BACKOFF) - 1)]
            backoff_idx += 1
            logger.warning("WS ARI desconectado (%s) — reconexión en %ss", exc, delay)
            await asyncio.sleep(delay)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bridge = VoiceBridge()
    logger.info(
        "voice-bridge iniciando — ARI %s:%s (app=%s, ari_py=%s) backend %s | stt=%s tts=%s llm=%s",
        ARI_HOST, ARI_PORT, bridge.stasis_app, bridge.ari.uses_ari_py,
        BACKEND_INTERNAL_URL, getattr(bridge.stt, "name", "?"),
        getattr(bridge.tts, "name", "?"), getattr(bridge.llm, "name", "?"),
    )
    tasks = [_poll_loop(bridge)]
    if USE_WS:
        tasks.append(_ws_events_loop(bridge))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
