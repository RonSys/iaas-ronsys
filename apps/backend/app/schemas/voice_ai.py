"""
🤖 Schemas — Recepcionista IA por Voz (Spec 06 F3, §3.3/§3.5).

Contratos de los endpoints F3 (mismo recurso /api/v1/calls de F2):
  - Bridge interno (token de servicio + allowlist IP, igual que /events):
      POST /calls/{external_call_id}/transcript
      GET  /calls/{external_call_id}/ai-state
      PATCH /calls/{external_call_id}/ai-state
      PATCH /calls/{external_call_id}/ai-context
      POST /calls/{external_call_id}/transfer
      POST /calls/{external_call_id}/complete
  - Staff (JWT + X-Tenant-ID):
      GET  /calls/{id|external_call_id}/transcript  (CA-F3-3)

Además: configuración por tenant `companies.settings.voice_ai` (§3.3, patrón
D-03): proveedores STT/TTS/LLM conmutables, umbral de confianza,
max_clarify_attempts, presupuesto (max_usd_per_minute / daily_budget_usd),
greeting y kill-switch (R4/R5).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.adapters.db.models.calls import AI_STATES, TRANSFER_REASONS


# ═══════════════════════════════════════════════════════════════
# Config por tenant — companies.settings.voice_ai (Spec §3.3, D-03)
# ═══════════════════════════════════════════════════════════════

class VoiceAiSTTSettings(BaseModel):
    """STT (D2). PoC interno sin keys: faster-whisper (es) local."""
    provider: str = Field("whisper", description="deepgram | google | whisper")
    model: str = Field("nova-3", description="Modelo del proveedor STT")
    language: str = Field("es", description="Código de idioma (es)")
    api_key: Optional[str] = Field(None, description="NUNCA en código — solo settings por tenant")


class VoiceAiTTSSettings(BaseModel):
    """TTS (D3). PoC interno sin keys: piper-tts (es_PE) / edge-tts."""
    provider: str = Field("piper", description="google | azure | elevenlabs | piper | edge-tts")
    voice: str = Field("es_PE", description="Voz (es-PE-Chirp3-HD-Fenella, es_PE…)")
    api_key: Optional[str] = Field(None, description="NUNCA en código — solo settings por tenant")


class VoiceAiLLMSettings(BaseModel):
    """LLM (D4). Pipeline texto STT→LLM→TTS; PoC: DeepSeek validado en spike F5."""
    provider: str = Field("deepseek", description="groq | deepseek | openai")
    model: str = Field("deepseek-v4-flash", description="Modelo del proveedor LLM")
    api_key: Optional[str] = Field(None, description="NUNCA en código — solo settings por tenant")


class VoiceAiTransferSettings(BaseModel):
    """Umbrales de transferencia (D9/R2)."""
    confidence_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Confianza mínima de match")
    max_clarify_attempts: int = Field(2, ge=1, le=5, description="Máx intentos de aclaración → transfer")


class VoiceAiBudget(BaseModel):
    """Gobernanza de costo (R4/D10)."""
    max_usd_per_minute: float = Field(0.15, ge=0.0, description="Presupuesto por minuto")
    daily_budget_usd: float = Field(10.0, ge=0.0, description="Tope diario por tenant")


class VoiceAiSettings(BaseModel):
    """Config completa `companies.settings.voice_ai` (§3.3, patrón D-03).

    Defaults = PoC sin keys externas (faster-whisper/piper/DeepSeek); el
    switch a Deepgram/Google/ElevenLabs con keys reales es solo configuración
    (D2/D3/D4 — proveedores conmutables vía puerto VoiceProvider).
    """

    enabled: bool = Field(False, description="Activa la recepcionista IA del tenant")
    kill_switch: bool = Field(False, description="R5: apagado inmediato → ring_operator (F2)")
    max_calls_concurrent: int = Field(4, ge=1, le=8, description="R6: canales IA simultáneos")
    stt: VoiceAiSTTSettings = Field(default_factory=VoiceAiSTTSettings)
    tts: VoiceAiTTSSettings = Field(default_factory=VoiceAiTTSSettings)
    llm: VoiceAiLLMSettings = Field(default_factory=VoiceAiLLMSettings)
    transfer: VoiceAiTransferSettings = Field(default_factory=VoiceAiTransferSettings)
    budget: VoiceAiBudget = Field(default_factory=VoiceAiBudget)
    greeting: str = Field(
        "Buenas noches, gracias por llamar a El Segoviano. Esta llamada es atendida "
        "por un asistente automático y puede ser grabada. ¿Qué le ofrezco esta noche?",
        description="Saludo pre-generado (CA-F3-5: no depende del LLM; §3.7 transparencia IA)",
    )
    payment_method: str = Field("cash", description="R7: pago por voz = contraentrega (cash)")


# ═══════════════════════════════════════════════════════════════
# Transcripción (§3.5.1, D8/R3)
# ═══════════════════════════════════════════════════════════════

class TranscriptionSegment(BaseModel):
    """Segmento de transcripción (start/end/speaker/text/confidence)."""

    start: Optional[float] = Field(None, ge=0)
    end: Optional[float] = Field(None, ge=0)
    speaker: Optional[str] = None
    text: str = ""
    confidence: Optional[float] = Field(None, ge=0, le=1)


class TranscriptionIn(BaseModel):
    """POST /api/v1/calls/{external_call_id}/transcript — body del bridge."""

    provider: str = Field(..., min_length=1, max_length=30)
    text: str = Field(..., min_length=1, description="Transcripción completa")
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    lang: str = Field("es-PE", max_length=10)
    duration_sec: Optional[int] = Field(None, ge=0)
    cost_estimate: float = Field(0.0, ge=0, description="Costo STT estimado USD (R4)")


class TranscriptionOut(BaseModel):
    """201 / 200: transcripción persistida (upsert idempotente por call_id)."""

    id: int
    tenant_id: int
    call_id: str  # = call_records.external_call_id
    call_record_id: int
    provider: str
    text: str
    segments: Optional[list[dict]] = None
    lang: str = "es-PE"
    duration_sec: Optional[int] = None
    cost_estimate: float = 0.0
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════
# Estado IA (§3.5.1 PATCH / GET ai-state, R10 panel en vivo)
# ═══════════════════════════════════════════════════════════════

class AiStateIn(BaseModel):
    """PATCH /api/v1/calls/{external_call_id}/ai-state — panel en vivo (§3.6)."""

    state: str = Field(..., min_length=1, max_length=20)
    transfer_reason: Optional[str] = Field(None, max_length=50)
    context_summary: Optional[str] = None

    @field_validator("state")
    @classmethod
    def _valid_state(cls, v: str) -> str:
        if v not in AI_STATES:
            raise ValueError(
                f"estado inválido '{v}' — permitidos: {', '.join(AI_STATES)}"
            )
        return v

    @field_validator("transfer_reason")
    @classmethod
    def _valid_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TRANSFER_REASONS:
            raise ValueError(
                f"motivo inválido '{v}' — permitidos: {', '.join(TRANSFER_REASONS)}"
            )
        return v


class AiStateOut(BaseModel):
    """GET /ai-state: estado conversacional + costo acumulado + contexto (R10)."""

    external_call_id: str
    call_record_id: Optional[int] = None
    caller: Optional[str] = None
    callee: Optional[str] = None
    call_status: Optional[str] = None
    ai_state: Optional[str] = None
    transfer_reason: Optional[str] = None
    context_summary: Optional[str] = None
    duration_sec: int = 0
    cost_usd: float = 0.0
    converted_order_id: Optional[int] = None
    transcription_id: Optional[int] = None
    transcription_text: Optional[str] = None
    # R4/R5/D10: gobernanza de costo del tenant (can_start=false → ring_operator)
    budget: dict = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════
# Contexto incremental (§3.5.1 PATCH ai-context, D9)
# ═══════════════════════════════════════════════════════════════

class AiContextIn(BaseModel):
    """PATCH /api/v1/calls/{external_call_id}/ai-context — resumen incremental."""

    context_summary: str = Field(..., min_length=1, description="Resumen para el operador (D9)")


class AiContextOut(BaseModel):
    external_call_id: str
    context_summary: str


# ═══════════════════════════════════════════════════════════════
# Transferencia a humano (§3.5.1 POST transfer, D9/R2)
# ═══════════════════════════════════════════════════════════════

class AiTransferIn(BaseModel):
    """POST /api/v1/calls/{external_call_id}/transfer — body del bridge."""

    reason: str = Field(..., min_length=1, max_length=50)
    context_summary: Optional[str] = Field(None, description="Resumen de lo dicho (D9)")
    priority: str = Field("normal", pattern=r"^(normal|high)$")

    @field_validator("reason")
    @classmethod
    def _valid_reason(cls, v: str) -> str:
        if v not in TRANSFER_REASONS:
            raise ValueError(
                f"motivo inválido '{v}' — permitidos: {', '.join(TRANSFER_REASONS)}"
            )
        return v


class AiTransferOut(BaseModel):
    """200: el bridge libera el canal IA y ringea a la extensión del operador."""

    external_call_id: str
    transferred_to: Optional[str] = Field(None, description="Extensión SIP del operador (F2 calls.extensions)")
    via: str = "sip"
    ai_state: str = "transfer"
    transfer_reason: str
    context_summary: Optional[str] = None
    priority: str = "normal"


# ═══════════════════════════════════════════════════════════════
# Cierre (§3.5.1 POST complete, R4/R7/R9)
# ═══════════════════════════════════════════════════════════════

class VoiceOrderItem(BaseModel):
    menu_item_id: int
    quantity: int = Field(1, ge=1)
    modifiers: list[dict] = Field(default_factory=list)


class VoiceOrderRequest(BaseModel):
    """Pedido confirmado por voz — payload de `create_order` (reuso total §2.4).

    Misma forma que ConvertToOrderRequest de F2; R7: `payment.method` es
    SIEMPRE cash (contraentrega) salvo override explícito del bridge.
    """

    zone_id: Optional[int] = None
    items: list[VoiceOrderItem] = Field(min_length=1)
    customer: dict = Field(
        default_factory=dict,
        description="name / phone / address (phone default = caller de la llamada)",
    )
    payment: dict = Field(default_factory=lambda: {"method": "cash"})
    notes: Optional[str] = None


class AiCompleteIn(BaseModel):
    """POST /api/v1/calls/{external_call_id}/complete — cierre de la llamada IA.

    `order` solo si hubo items confirmados en voz: reusa `create_order`
    (Sale → kárdex → asiento → cocina → DeliveryOrder DLV-, R7) y vincula
    `converted_order_id` (columna F2, R9).
    """

    duration_sec: Optional[int] = Field(None, ge=0)
    cost_usd: float = Field(0.0, ge=0, description="STT+TTS+LLM acumulado de la llamada (R4)")
    state: str = Field("completed", description="completed | failed")
    order: Optional[VoiceOrderRequest] = None

    @field_validator("state")
    @classmethod
    def _valid_state(cls, v: str) -> str:
        if v not in ("completed", "failed"):
            raise ValueError("state debe ser 'completed' o 'failed'")
        return v


class AiCompleteOut(BaseModel):
    external_call_id: str
    ai_state: str
    cost_usd: float
    duration_sec: Optional[int] = None
    converted_order_id: Optional[int] = None
    tracking_code: Optional[str] = None
    sale_id: Optional[int] = None
    sale_number: Optional[str] = None
