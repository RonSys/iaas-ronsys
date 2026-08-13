"""
🤖 VoiceAIService — Recepcionista IA por Voz (Spec 06 F3, §3.5/§3.6/§3.8).

Fase 1 (base backend, sin Asterisk/proveedores externos): persiste el
estado conversacional, las transcripciones y el cierre de la llamada sobre
la infraestructura de F2 (`call_records`), y expone la lógica de dominio
que Fase 2 (bridge de voz STT→LLM→TTS) consumirá:

  - `save_transcription`      POST /transcript (upsert por call_id, D8/R3)
  - `get_transcription`       GET /{ref}/transcript (CA-F3-3)
  - `get_ai_state`            GET /ai-state (R10 panel en vivo)
  - `update_ai_state`         PATCH /ai-state (§3.6, espeja la máquina de estados)
  - `update_context`          PATCH /ai-context (resumen incremental D9)
  - `transfer_call`           POST /transfer (D9/R2: motivo + contexto + WS)
  - `complete_call`           POST /complete (R4 costo; R7/R9 create_order si
                              hubo items confirmados — patrón convert_to_order F2)
  - `build_conversation_context`  contexto del LLM = menú + zonas REALES (R1)
  - `detect_transfer_reason`  detección determinista (queja / fuera de dominio /
                              usuario pidió / …)
  - `ConversationStateMachine` máquina de estados §3.6 (greeting → … → hangup|transfer)
  - gobernanza de costo:      budget_status / get_daily_cost_usd / estimate_call_cost
                              (R4 tope diario + R5 kill-switch → ring_operator)

Reglas de negocio (Spec 06 §3.8): R1 (nunca inventar — el contexto sale de
get_public_menu/get_public_zones), R2 (transferencia obligatoria con contexto),
R3 (transcripción siempre), R4 (costo por llamada + tope diario), R7 (pago cash,
pedido SIEMPRE vía create_order — jamás flujo paralelo), R8 (aislamiento por
tenant: toda query filtra tenant_id), R9 (converted_order_id + eventos Fase B
los dispara el motor existente), R10 (ai_state → WS calls).
"""

import logging
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Company
from app.adapters.db.models.calls import AI_STATES, TRANSFER_REASONS, CallRecord, CallTranscription
from app.core.ws_manager import manager
from app.schemas import CallSettings  # noqa: E402 — definido en app/schemas/__init__.py (D-03)
from app.schemas.voice_ai import VoiceAiSettings
from app.services.call_service import (
    _delivery_order_id_for_sale,
    call_settings_from_company,
    suggest_zone_by_address,
)
from app.services.delivery_service import (
    _LIMA,  # Zona horaria del negocio (Spec 03: America/Lima) — tope diario en hora local
    create_order as delivery_create_order,
    get_public_menu,
    get_public_zones,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _dec(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Convierte a Decimal sin explotar con None/str (costos numeric)."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return default


# ═══════════════════════════════════════════════════════════════
# Config por tenant — companies.settings.voice_ai (§3.3, patrón D-03)
# ═══════════════════════════════════════════════════════════════

def voice_ai_settings_from_company(company: Company | None) -> VoiceAiSettings:
    """Lee `companies.settings.voice_ai` con defaults (patrón D-03).

    Igual que `call_settings_from_company` (F2): lo persistido gana, los
    campos ausentes toman el default del schema (VoiceAiSettings §3.3).
    """
    raw = (company.settings or {}) if company else {}
    raw = raw if isinstance(raw, dict) else {}
    voice = raw.get("voice_ai", {}) if isinstance(raw.get("voice_ai"), dict) else {}
    return VoiceAiSettings(**voice)


async def _company(db: AsyncSession, tenant_id: int) -> Company:
    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


async def get_settings(db: AsyncSession, tenant_id: int) -> VoiceAiSettings:
    """Config voice_ai del tenant (R8: por tenant, nunca global)."""
    return voice_ai_settings_from_company(await _company(db, tenant_id))


async def get_daily_cost_usd(db: AsyncSession, tenant_id: int) -> float:
    """R4/CA-F3-8: suma de `cost_usd` de la llamada del día (America/Lima)."""
    today = datetime.now(_LIMA).date()
    start = datetime.combine(today, time.min, tzinfo=_LIMA)
    total = (await db.execute(
        select(func.coalesce(func.sum(CallRecord.cost_usd), 0)).where(
            CallRecord.tenant_id == tenant_id,
            CallRecord.started_at >= start,
        )
    )).scalar()
    return float(_dec(total))


async def budget_status(db: AsyncSession, tenant_id: int) -> dict:
    """D10/R4/R5: estado de gobernanza de costo del tenant.

    `can_start=false` → el ruteo cae a `inbound_behavior=ring_operator` (F2):
    la IA jamás arranca (CA-F3-10/CA-F3-11). La llamada EN CURSO no se corta
    (el kill-switch aplica a las SIGUIENTES).
    """
    settings = await get_settings(db, tenant_id)
    daily = await get_daily_cost_usd(db, tenant_id)
    exceeded = (
        settings.enabled
        and not settings.kill_switch
        and settings.budget.daily_budget_usd > 0
        and daily >= settings.budget.daily_budget_usd
    )
    return {
        "enabled": settings.enabled,
        "kill_switch": settings.kill_switch,
        "daily_spent_usd": round(daily, 4),
        "daily_budget_usd": settings.budget.daily_budget_usd,
        "max_usd_per_minute": settings.budget.max_usd_per_minute,
        "budget_exceeded": exceeded,
        "can_start": settings.enabled and not settings.kill_switch and not exceeded,
    }


def estimate_call_cost(duration_sec: int | None, max_usd_per_minute: float = 0.15) -> float:
    """R4: costo estimado de una llamada = max_usd_per_minute × minutos."""
    seconds = max(0, int(duration_sec or 0))
    return round(seconds / 60.0 * float(max_usd_per_minute), 4)


def per_minute_exceeded(cost_usd: float, duration_sec: int | None, max_usd_per_minute: float) -> bool:
    """R4: una llamada que supera el presupuesto por minuto → transfer budget."""
    minutes = max(0, int(duration_sec or 0)) / 60.0
    if minutes <= 0:
        return False
    return (float(cost_usd) / minutes) > float(max_usd_per_minute)


# ═══════════════════════════════════════════════════════════════
# Contexto del agente de dominio (R1 — SOLO datos reales)
# ═══════════════════════════════════════════════════════════════

async def build_conversation_context(db: AsyncSession, tenant_id: int) -> dict:
    """Contexto del LLM = output REAL de get_public_menu + get_public_zones.

    HU-F3-04 (anti-alucinación): nada hardcodeado — precios, modificadores,
    promos, ventana horaria y zonas salen exclusivamente del menú real (R1).
    """
    menu = await get_public_menu(db, tenant_id)
    zones = await get_public_zones(db, tenant_id)
    settings = await get_settings(db, tenant_id)
    return {
        "tenant_name": menu.get("tenant_name", ""),
        "delivery_window": menu.get("delivery_window"),
        "currency": menu.get("currency", "PEN"),
        "greeting": settings.greeting,
        "payment_method": settings.payment_method,
        "sections": menu.get("sections", []),
        "promotions": menu.get("promotions", []),
        "zones": zones,
        "rules": {
            "no_inventar": (
                "Solo respondas con datos presentes en este contexto (menú real). "
                "Nunca inventes precios, items, promos ni horarios."
            ),
            "desconocido": (
                "Si el cliente pide algo fuera del contexto, declina amablemente "
                "y transfiere al operador (motivo out_of_domain)."
            ),
            "intents": [
                "tomar_pedido", "confirmar_pedido", "consultar_estado",
                "modificar", "cancelar", "queja", "fuera_de_dominio",
            ],
        },
    }


def format_context_for_llm(context: dict | None) -> str:
    """Serializa el contexto a JSON compacto para el prompt del LLM (Fase 2).

    El prompt de dominio se construye SOLO desde este output (HU-F3-04).
    """
    import json
    return json.dumps(context or {}, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# Detección determinista de motivo de transferencia (D9/R2)
# ═══════════════════════════════════════════════════════════════

# Frases clave (fragmentos normalizados, sin acentos) — orden de prioridad:
# queja > usuario pidió > fuera de dominio. La baja confianza (low_confidence)
# NO se detecta por texto: la decide la máquina de estados (2 intentos fallidos)
# o el matcher de zona (D7) — ver ConversationStateMachine.
_COMPLAINT_PATTERNS = (
    "queja", "quejarme", "reclamo", "carisimo", "carísimo", "esto es caro",
    "demoraron", "demoro mucho", "mal servicio", "pesimo", "pésimo",
    "horrible", "nunca llega", "me estafaron",
)
_USER_REQUESTED_PATTERNS = (
    "hablar con alguien", "con una persona", "con un humano", "con alguien",
    "con el operador", "con la operadora", "persona real", "un ser humano",
    "pasame con", "pásame con", "transferir", "quiero que me atienda",
    "atención humana",
)
_OUT_OF_DOMAIN_PATTERNS = (
    "me prestas plata", "prestame plata", "préstame plata", "prestamo",
    "préstamo", "chicha", "nombre real", "cual es tu nombre", "cuál es tu nombre",
    "cuantos anos tienes", "cuántos años tienes", "novia", "futbol", "fútbol",
    "loteria", "lotería", "regatear", "regateame", "descuento", "rebaja",
    "precio especial", "venta de droga", "apuestas",
)


def _normalize_text(text: str) -> str:
    """Minúsculas + sin acentos (match robusto sobre texto del STT)."""
    text = (text or "").lower()
    trans = str.maketrans("áéíóúüñ", "aeiouun")
    return text.translate(trans)


def detect_transfer_reason(text: str | None) -> str | None:
    """Detecta el motivo de transferencia por patrones (R2, determinista).

    Retorna uno de TRANSFER_REASONS (excepto low_confidence, que es decisión
    de la máquina de estados) o None si el texto no amerita transferencia.
    """
    norm = _normalize_text(text or "")
    if not norm:
        return None
    for pattern in _COMPLAINT_PATTERNS:
        if pattern in norm:
            return "complaint"
    for pattern in _USER_REQUESTED_PATTERNS:
        if pattern in norm:
            return "user_requested"
    for pattern in _OUT_OF_DOMAIN_PATTERNS:
        if pattern in norm:
            return "out_of_domain"
    return None


# ═══════════════════════════════════════════════════════════════
# Máquina de estados conversacional (§3.6)
# ═══════════════════════════════════════════════════════════════

class ConversationStateMachine:
    """Máquina de estados del agente de dominio (Spec 06 §3.6).

        greeting ──► taking_order ──► clarifying ──► confirming ──► hangup
                       ▲  ▲  │            │              │
                       │  │  └─ clarify_needed (máx N)   └─ confirmed=False
                       │  └──── clarify_resolved (sin items)
                       └─────── cualquier dato faltante
        cualquier estado + transfer_reason ──► transfer (R2/D9)

    `max_clarify_attempts` (default 2) = 1ª captura fallida + 1 repregunta
    fallida → transfer con motivo low_confidence (HU-F3-02: repregunta 1 vez).
    Los estados terminales (hangup/transfer/completed/failed) no transitan.
    """

    def __init__(self, max_clarify_attempts: int = 2):
        self.max_clarify_attempts = max(1, int(max_clarify_attempts))
        self.clarify_attempts = 0

    @property
    def remaining_clarify_attempts(self) -> int:
        return max(0, self.max_clarify_attempts - self.clarify_attempts)

    def reset(self) -> None:
        self.clarify_attempts = 0

    def next_state(
        self,
        current: str,
        *,
        transfer_reason: str | None = None,
        confirmed: bool = False,
        clarify_needed: bool = False,
        clarify_resolved: bool = False,
    ) -> str:
        """Transición determinista; devuelve el siguiente estado (§3.6)."""
        if current in ("hangup", "transfer", "completed", "failed"):
            return current  # terminales — no transitan
        if transfer_reason:
            return "transfer"
        if clarify_needed:
            self.clarify_attempts += 1
            if self.clarify_attempts >= self.max_clarify_attempts:
                return "transfer"  # R2: 2 intentos fallidos → humano
            return "clarifying"
        if current == "greeting":
            return "taking_order"
        if current == "clarifying":
            # Resuelto: si ya hay items capturados → confirmar; si no → seguir tomando
            return "confirming" if clarify_resolved else "taking_order"
        if current == "taking_order":
            return "confirming"
        if current == "confirming":
            return "hangup" if confirmed else "taking_order"
        return current


# ═══════════════════════════════════════════════════════════════
# Resolución de CallRecord (R8: SIEMPRE tenant-scoped)
# ═══════════════════════════════════════════════════════════════

async def _resolve_call_record(
    db: AsyncSession, tenant_id: int, ref: str | int,
) -> CallRecord | None:
    """Resuelve por external_call_id (bridge) o id numérico (panel)."""
    stmt = select(CallRecord).where(
        CallRecord.tenant_id == tenant_id,
        CallRecord.external_call_id == str(ref),
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if record is not None:
        return record
    if str(ref).isdigit():
        record = (await db.execute(
            select(CallRecord).where(
                CallRecord.tenant_id == tenant_id,
                CallRecord.id == int(ref),
            )
        )).scalar_one_or_none()
    return record


async def _require_call(db: AsyncSession, tenant_id: int, ref: str | int) -> CallRecord:
    record = await _resolve_call_record(db, tenant_id, ref)
    if not record:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    return record


# ═══════════════════════════════════════════════════════════════
# Broadcast WS (R10 — el WS nunca rompe la operación)
# ═══════════════════════════════════════════════════════════════

def _ai_state_ws_payload(record: CallRecord) -> dict:
    """Payload del evento `ai_call_state` (Spec 06 §3.5.2)."""
    return {
        "external_call_id": record.external_call_id,
        "call_record_id": record.id,
        "caller": record.caller,
        "ai_state": record.ai_state,
        "duration_sec": record.duration,
        "converted_order_id": record.converted_order_id,
        "transfer_reason": record.transfer_reason,
        "context_summary": record.context_summary,
    }


async def _broadcast_ai_state(record: CallRecord) -> None:
    try:
        await manager.broadcast_to_calls(
            record.tenant_id, "ai_call_state", _ai_state_ws_payload(record),
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "broadcast ai_call_state falló (external=%s)", record.external_call_id, exc_info=True,
        )


# ═══════════════════════════════════════════════════════════════
# Transcripción (D8/R3 — POST /transcript + GET /transcript)
# ═══════════════════════════════════════════════════════════════

def _transcription_out(trans: CallTranscription, record: CallRecord) -> dict:
    return {
        "id": trans.id,
        "tenant_id": trans.tenant_id,
        "call_id": trans.call_id,
        "call_record_id": record.id,
        "provider": trans.provider,
        "text": trans.text,
        "segments": trans.segments,
        "lang": trans.lang,
        "duration_sec": trans.duration_sec,
        "cost_estimate": float(_dec(trans.cost_estimate)),
        "created_at": trans.created_at,
    }


async def save_transcription(
    db: AsyncSession, tenant_id: int, external_call_id: str, data: dict,
) -> dict:
    """POST /transcript — upsert idempotente por call_id (= external_call_id).

    - 404 si la llamada no existe o es cross-tenant (R8).
    - Persiste `call_transcriptions` y llena `call_records.transcription_fk`
      (columna RESERVADA de F2) → el detalle de F2 muestra la transcripción
      sin cambio de contrato (CA-F3-3). R3: transcripción siempre.
    """
    record = await _require_call(db, tenant_id, external_call_id)

    existing = (await db.execute(
        select(CallTranscription).where(
            CallTranscription.tenant_id == tenant_id,
            CallTranscription.call_id == record.external_call_id,
        )
    )).scalar_one_or_none()

    if existing:
        existing.provider = str(data["provider"])
        existing.text = str(data["text"])
        existing.segments = data.get("segments")
        existing.lang = str(data.get("lang") or "es-PE")
        existing.duration_sec = data.get("duration_sec")
        existing.cost_estimate = _dec(data.get("cost_estimate"))
        trans = existing
    else:
        trans = CallTranscription(
            tenant_id=tenant_id,
            call_id=record.external_call_id,
            provider=str(data["provider"]),
            text=str(data["text"]),
            segments=data.get("segments"),
            lang=str(data.get("lang") or "es-PE"),
            duration_sec=data.get("duration_sec"),
            cost_estimate=_dec(data.get("cost_estimate")),
        )
        db.add(trans)
        await db.flush()
        # FK reservada por F2 (D8) — el detalle de la llamada la muestra
        record.transcription_fk = trans.id

    await db.commit()
    await db.refresh(trans)
    return _transcription_out(trans, record)


async def get_transcription(
    db: AsyncSession, tenant_id: int, ref: str | int,
) -> dict:
    """GET /{ref}/transcript (CA-F3-3) — 404 sin llamada o sin transcripción."""
    record = await _require_call(db, tenant_id, ref)
    trans = (await db.execute(
        select(CallTranscription).where(
            CallTranscription.tenant_id == tenant_id,
            CallTranscription.call_id == record.external_call_id,
        )
    )).scalar_one_or_none()
    if not trans:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    return _transcription_out(trans, record)


# ═══════════════════════════════════════════════════════════════
# Estado IA (R10 — PATCH/GET ai-state + PATCH ai-context)
# ═══════════════════════════════════════════════════════════════

async def _state_out(db: AsyncSession, record: CallRecord) -> dict:
    trans = (await db.execute(
        select(CallTranscription).where(
            CallTranscription.tenant_id == record.tenant_id,
            CallTranscription.call_id == record.external_call_id,
        )
    )).scalar_one_or_none()
    budget = await budget_status(db, record.tenant_id)
    return {
        "external_call_id": record.external_call_id,
        "call_record_id": record.id,
        "caller": record.caller,
        "callee": record.callee,
        "call_status": record.status,
        "ai_state": record.ai_state,
        "transfer_reason": record.transfer_reason,
        "context_summary": record.context_summary,
        "duration_sec": record.duration,
        "cost_usd": float(_dec(record.cost_usd)),
        "converted_order_id": record.converted_order_id,
        "transcription_id": trans.id if trans else None,
        "transcription_text": trans.text if trans else None,
        "budget": budget,
        "updated_at": record.updated_at,
    }


async def get_ai_state(db: AsyncSession, tenant_id: int, external_call_id: str) -> dict:
    """GET /ai-state — estado conversacional + costo acumulado + contexto (R10)."""
    record = await _require_call(db, tenant_id, external_call_id)
    return await _state_out(db, record)


async def update_ai_state(
    db: AsyncSession, tenant_id: int, external_call_id: str, data: dict,
) -> dict:
    """PATCH /ai-state — espeja la máquina de estados (§3.6) + WS en vivo.

    `transfer_reason` se acepta junto al estado (el bridge puede cerrar el
    estado en la misma transición); la transferencia formal usa /transfer.
    """
    record = await _require_call(db, tenant_id, external_call_id)
    state = data["state"]
    if state not in AI_STATES:
        raise HTTPException(
            status_code=422, detail=f"Estado inválido '{state}' — permitidos: {', '.join(AI_STATES)}",
        )
    reason = data.get("transfer_reason")
    if reason is not None and reason not in TRANSFER_REASONS:
        raise HTTPException(
            status_code=422,
            detail=f"Motivo inválido '{reason}' — permitidos: {', '.join(TRANSFER_REASONS)}",
        )
    record.ai_state = state
    if reason is not None:
        record.transfer_reason = reason
    if data.get("context_summary") is not None:
        record.context_summary = data["context_summary"]
    await db.commit()
    await db.refresh(record)
    await _broadcast_ai_state(record)
    return await _state_out(db, record)


async def update_context(
    db: AsyncSession, tenant_id: int, external_call_id: str, context_summary: str,
) -> dict:
    """PATCH /ai-context — resumen incremental para el operador (D9)."""
    record = await _require_call(db, tenant_id, external_call_id)
    record.context_summary = context_summary
    await db.commit()
    await db.refresh(record)
    await _broadcast_ai_state(record)
    return {"external_call_id": record.external_call_id, "context_summary": record.context_summary}


# ═══════════════════════════════════════════════════════════════
# Transferencia a humano (D9/R2 — POST /transfer)
# ═══════════════════════════════════════════════════════════════

async def _operator_extension(company: Company | None, record: CallRecord) -> str | None:
    """Extensión destino: F2 `calls.extensions` (primera) o la callee.

    El bridge libera el canal IA y ringea a esta extensión (Asterisk, Fase 2);
    aquí solo se resuelve y reporta ({transferred_to, via: "sip"}).
    """
    cs: CallSettings = call_settings_from_company(company)
    extensions = [e for e in (cs.extensions or []) if str(e).strip()]
    if extensions:
        return str(extensions[0])
    return record.callee or None


async def transfer_call(
    db: AsyncSession, tenant_id: int, external_call_id: str, data: dict,
) -> dict:
    """POST /transfer — marca transfer_reason + ai_state='transfer' + WS.

    - 422 si el motivo no está en TRANSFER_REASONS (blinda el dominio).
    - Emite `call.transferred` (con context_summary, contrato F3) y
      `ai_call_state` (panel en vivo, §3.5.2: ai_state=transfer + motivo).
    - 200 {transferred_to: ext SIP del operador (F2 calls.extensions),
      via: "sip"} — el ring lo ejecuta el bridge (Fase 2).
    """
    reason = data["reason"]
    if reason not in TRANSFER_REASONS:
        raise HTTPException(
            status_code=422,
            detail=f"Motivo inválido '{reason}' — permitidos: {', '.join(TRANSFER_REASONS)}",
        )
    record = await _require_call(db, tenant_id, external_call_id)
    record.ai_state = "transfer"
    record.transfer_reason = reason
    if data.get("context_summary") is not None:
        record.context_summary = data["context_summary"]
    await db.commit()
    await db.refresh(record)

    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    transferred_to = await _operator_extension(company, record)

    # WS panel en vivo (R10): el operador ve motivo + resumen antes de hablar
    try:
        await manager.broadcast_to_calls(tenant_id, "call.transferred", {
            "external_call_id": record.external_call_id,
            "caller": record.caller,
            "transfer_reason": reason,
            "context_summary": record.context_summary,
            "transferred_to": transferred_to,
            "via": "sip",
            "priority": data.get("priority", "normal"),
        })
    except Exception:  # noqa: BLE001
        logger.warning(
            "broadcast call.transferred falló (external=%s)", external_call_id, exc_info=True,
        )
    await _broadcast_ai_state(record)

    return {
        "external_call_id": record.external_call_id,
        "transferred_to": transferred_to,
        "via": "sip",
        "ai_state": "transfer",
        "transfer_reason": reason,
        "context_summary": record.context_summary,
        "priority": data.get("priority", "normal"),
    }


# ═══════════════════════════════════════════════════════════════
# Cierre (R4/R7/R9 — POST /complete)
# ═══════════════════════════════════════════════════════════════

async def _create_order_for_call(
    db: AsyncSession, tenant_id: int, record: CallRecord, order_data: dict,
) -> dict:
    """Reusa el motor de F2 (patrón convert_to_order): create_order + vínculo.

    - R7: el pedido por voz entra SIEMPRE por `create_order` (Sale → kárdex →
      asiento → KitchenOrder → DeliveryOrder DLV- + eventos Fase B) — jamás
      flujo paralelo (§2.4).
    - Zona: explícita o sugerida por distrito (D7, suggest_zone_by_address);
      sin zona → 422.
    - R9: `converted_order_id` (columna F2) poblado; 409 si ya hay conversión.
    """
    # R6 (F2): 1 sola conversión por llamada
    if record.converted_order_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"La llamada ya fue convertida (delivery_orders id {record.converted_order_id})",
        )

    customer = dict(order_data.get("customer") or {})
    # Default: el número de la llamada como teléfono del cliente (§3.5.1)
    if not customer.get("phone"):
        customer["phone"] = record.caller

    zone_id = order_data.get("zone_id")
    if not zone_id:
        suggested = await suggest_zone_by_address(
            db, tenant_id, customer.get("address") or "",
        )
        if suggested is None:
            raise HTTPException(
                status_code=422,
                detail="Se requiere zona de delivery (no se pudo inferir del distrito de la dirección)",
            )
        zone_id = suggested.id

    payment = dict(order_data.get("payment") or {})
    payment.setdefault("method", "cash")  # R7: contraentrega default

    result = await delivery_create_order(db, tenant_id, {
        "zone_id": int(zone_id),
        "items": order_data.get("items") or [],
        "customer": customer,
        "payment": payment,
        "notes": order_data.get("notes"),
    })

    delivery_order = await _delivery_order_id_for_sale(db, tenant_id, result["sale_id"])
    if delivery_order is None:
        raise HTTPException(status_code=500, detail="No se pudo vincular el pedido a la llamada")
    record.converted_order_id = delivery_order.id
    return result


async def complete_call(
    db: AsyncSession, tenant_id: int, external_call_id: str, data: dict,
) -> dict:
    """POST /complete — cierre de la llamada IA (el status lo cierra F2/AMI).

    - Persiste `cost_usd` (R4/CA-F3-8) y `ai_state` completed|failed.
    - `order` presente (hubo items confirmados en voz) → create_order vía
      `_create_order_for_call` (patrón F2) + WS call.converted (R9).
    - El guard de status de F2 (answered/completed) NO aplica aquí: el flujo
      de voz es el cierre autoritativo y el estado AMI llega por su cuenta.
    """
    state = data.get("state") or "completed"
    if state not in ("completed", "failed"):
        raise HTTPException(status_code=422, detail="state debe ser 'completed' o 'failed'")
    if state == "failed" and data.get("order"):
        raise HTTPException(status_code=422, detail="No se puede crear pedido con state=failed")

    record = await _require_call(db, tenant_id, external_call_id)
    record.ai_state = state
    record.cost_usd = _dec(data.get("cost_usd"))
    if data.get("duration_sec") is not None:
        record.duration = int(data["duration_sec"])

    order_result = None
    if data.get("order"):
        order_result = await _create_order_for_call(db, tenant_id, record, data["order"])

    await db.commit()
    await db.refresh(record)

    # WS panel en vivo: estado de cierre + conversión (R9/R10)
    await _broadcast_ai_state(record)
    if order_result:
        try:
            await manager.broadcast_to_calls(tenant_id, "call.converted", {
                "external_call_id": record.external_call_id,
                "tracking_code": order_result["tracking_code"],
                "sale_id": order_result["sale_id"],
            })
        except Exception:  # noqa: BLE001
            logger.warning(
                "broadcast call.converted falló (external=%s)", external_call_id, exc_info=True,
            )

    return {
        "external_call_id": record.external_call_id,
        "ai_state": state,
        "cost_usd": float(_dec(record.cost_usd)),
        "duration_sec": record.duration,
        "converted_order_id": record.converted_order_id,
        "tracking_code": order_result.get("tracking_code") if order_result else None,
        "sale_id": order_result.get("sale_id") if order_result else None,
        "sale_number": order_result.get("sale_number") if order_result else None,
    }
