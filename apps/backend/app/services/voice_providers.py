"""
🎙️ Puertos de proveedores de voz — Recepcionista IA (Spec 06 F3, D1/D2/D3/D4).

Fase 1: solo CONTRATOS (ABC) + implementaciones deterministas de prueba.
Fase 2: implementaciones reales detrás de los mismos puertos (el switch es
solo configuración `companies.settings.voice_ai`, §3.3 — D2/D3/D4):

  - STT:      Deepgram Nova-3 (es) default; Google STT fallback;
              PoC sin keys = faster-whisper (es) local.
  - TTS:      Google Chirp3 HD / Azure Neural (es-PE) default;
              PoC sin keys = piper-tts (es_PE, 100% local) / edge-tts.
  - LLM:      Groq/DeepSeek (pipeline texto, ~$0.001/min);
              PoC = DeepSeek deepseek-v4-flash (validado en spike F5:
              spikes/f5-preguntale-al-sistema/ventas_skill.py como
              referencia de estilo determinista).

Estilo de referencia: spike F5 — herramientas deterministas y auditables;
aquí el fallback determinista NO alucina: solo responde con items del menú
real (R1) y deriva a clarifying/transfer si no hay match.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services.voice_ai_service import detect_transfer_reason


# ═══════════════════════════════════════════════════════════════
# Resultados
# ═══════════════════════════════════════════════════════════════

@dataclass
class STTResult:
    """Transcripción de un fragmento/llamada (D2)."""

    text: str
    segments: list[dict] = field(default_factory=list)
    duration_sec: int | None = None
    cost_estimate: float = 0.0
    confidence: float | None = None


@dataclass
class TTSResult:
    """Audio sintetizado (D3). Fase 1: sin audio real — path/placeholder."""

    audio: bytes | None = None
    path: str | None = None
    format: str = "wav"
    cost_estimate: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Puertos abstractos
# ═══════════════════════════════════════════════════════════════

class STTProvider(ABC):
    """Puerto de transcripción (speech-to-text)."""

    name: str = "abstract"

    @abstractmethod
    async def transcribe(self, audio: bytes | None = None, language: str = "es", **kwargs) -> STTResult:
        """Transcribe audio (o texto simulado en Fase 1) → STTResult."""
        ...


class TTSProvider(ABC):
    """Puerto de síntesis de voz (text-to-speech)."""

    name: str = "abstract"

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None, **kwargs) -> TTSResult:
        """Sintetiza texto → TTSResult (audio/path)."""
        ...


class LLMClient(ABC):
    """Puerto del pipeline LLM (D4 — texto, nunca audio-to-audio)."""

    name: str = "abstract"

    @abstractmethod
    async def complete(self, messages: list[dict], temperature: float = 0.2, **kwargs) -> str:
        """Completa la conversación (system = contexto de dominio R1)."""
        ...


class VoiceProvider(ABC):
    """Facade D1/D4: pipeline STT → LLM → TTS de una llamada.

    La lógica de dominio (estados §3.6, create_order, contratos §3.5) es
    AGNÓSTICA al transporte de voz: si el PoC de External Media fallara, la
    Opción B (Vapi/Retell, §2.5) implementa el mismo puerto sin tocar el
    backend.
    """

    name: str = "abstract"
    stt: STTProvider
    tts: TTSProvider
    llm: LLMClient

    @abstractmethod
    async def respond(
        self,
        audio: bytes | None = None,
        context: dict | None = None,
        language: str = "es",
    ) -> dict:
        """Turno completo: STT → LLM → TTS.

        Retorna {transcript, reply, audio_path, cost_usd, transfer_reason}.
        """
        ...


# ═══════════════════════════════════════════════════════════════
# Implementaciones deterministas (Fase 1 — PoC/tests sin keys)
# ═══════════════════════════════════════════════════════════════

class EchoSTTProvider(STTProvider):
    """STT determinista (echo): devuelve el texto simulado del cliente.

    Fase 2 → Deepgram/Google/faster-whisper: misma firma, solo cambia la
    configuración del tenant (D2).
    """

    name = "echo"

    def __init__(self, text: str = ""):
        self._text = text

    async def transcribe(self, audio: bytes | None = None, language: str = "es", **kwargs) -> STTResult:
        return STTResult(
            text=self._text,
            duration_sec=kwargs.get("duration_sec"),
            cost_estimate=kwargs.get("cost_estimate", 0.001),
        )


class LocalTTSProvider(TTSProvider):
    """TTS stub piper/edge-tts (D3): no genera audio real en Fase 1.

    Marca el path del audio que el bridge reproduciría; Fase 2 → piper-tts
    (es_PE local) / edge-tts / Google Chirp3 HD con la misma firma.
    """

    name = "local_piper"

    def __init__(self, out_dir: str = "/tmp/voice_ai_tts"):
        self.out_dir = out_dir

    async def synthesize(self, text: str, voice: str | None = None, **kwargs) -> TTSResult:
        import hashlib
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        path = f"{self.out_dir.rstrip('/')}/tts_{digest}.wav"
        return TTSResult(path=path, format="wav", cost_estimate=0.002)


class DeterministicLLMClient(LLMClient):
    """LLM determinista (fallback estilo spike F5) — R1: nunca inventa.

    No hay red ni keys: responde SOLO a partir del menú real embebido en el
    mensaje de sistema (contexto de dominio). Si el texto del cliente no
    matchea ningún item del menú → deriva a clarificación/transferencia
    (nunca confirma un item inexistente — HU-F3-04).

    Fase 2 → DeepSeek/Groq real con function calling; este fallback queda
    como respaldo auditable (CA-F3-12: log de intents).
    """

    name = "deterministic"

    def __init__(self, menu: dict | None = None):
        self._menu = menu or {}

    # ── Parseo determinista de pedido contra el menú REAL (R1) ──

    def parse_order(self, text: str) -> dict:
        """Extrae items del menú real por match de nombre (sin acentos).

        Retorna {items: [{menu_item_id, name, quantity}], modifiers: [...],
        address, customer: {name, phone}, matched: bool}.
        Sin match de item → items vacío (el llamante decide clarifying o
        transfer — jamás inventar, HU-F3-04).
        """
        from app.services.voice_ai_service import _normalize_text

        norm = _normalize_text(text or "")
        items: list[dict] = []
        modifiers: list[dict] = []
        used_names: list[str] = []

        for section in self._menu.get("sections", []):
            for item in section.get("items", []):
                name = _normalize_text(str(item.get("name", "")))
                if not name or name in used_names:
                    continue
                # Match tolerante al plural: "ceviches mixtos" ↦ "ceviche mixto"
                # (el STT no garantiza número gramatical — R1 sigue exigiendo
                # que el item exista en el menú real).
                if not self._name_in_text(name, norm):
                    continue
                used_names.append(name)
                qty = self._quantity_before(text, item.get("name")) or 1
                items.append({
                    "menu_item_id": item.get("id"),
                    "name": item.get("name"),
                    "quantity": qty,
                })
                # Modificadores del item presentes en el texto
                for mod in item.get("modifiers", []):
                    mod_name = _normalize_text(str(mod.get("name", "")))
                    if mod_name and mod_name in norm:
                        modifiers.append({
                            "id": mod.get("id"),
                            "name": mod.get("name"),
                            "quantity": 1,
                        })

        return {
            "items": items,
            "modifiers": modifiers,
            "address": self._extract_address(text),
            "customer": self._extract_customer(text),
            "matched": bool(items),
        }

    @staticmethod
    def _name_variants(name: str) -> list[str]:
        """Variantes singular/plural por palabra ("ceviche mixto" →
        "ceviche mixto", "ceviches mixtos", …) para match tolerante del STT."""
        words = name.split()
        variants = [""]
        for w in words:
            nxt: list[str] = []
            for v in variants:
                base = (v + " " + w) if v else w
                nxt.append(base)
                nxt.append(base + "s")
                nxt.append(base + "es")
            variants = nxt
        return [v for v in variants if v]

    @staticmethod
    def _name_in_text(name: str, norm: str) -> bool:
        """Match del nombre del item (normalizado) contra el texto, tolerando
        plurales por palabra ("ceviches mixtos" ↦ "ceviche mixto")."""
        if name in norm:
            return True
        return any(v in norm for v in DeterministicLLMClient._name_variants(name))

    @staticmethod
    def _quantity_before(text: str, item_name: str) -> int | None:
        """Cantidad numérica justo antes del item (tolerante al plural)."""
        import re
        lowered = text.lower()
        candidates = DeterministicLLMClient._name_variants(item_name.lower())
        idx = min((lowered.find(c) for c in candidates if lowered.find(c) >= 0), default=-1)
        if idx < 0:
            return None
        head = text[:idx]
        m = re.search(r"(\d+)\s*$", head)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_address(text: str) -> str | None:
        """Captura la dirección: fragmento con 'av'/'calle'/'jr' hasta el final
        de la frase (sin el teléfono)."""
        import re
        m = re.search(
            r"(?:av\.?|avenida|calle|jr\.?|jirón|pasaje|mz\.?|manzana|lot\.?)\s+([a-z0-9\s,.#-]{5,80})",
            text, re.IGNORECASE,
        )
        if not m:
            return None
        address = m.group(0).strip(" .,")
        # cortar en el teléfono si aparece dentro
        phone = re.search(r"\d{9}", address)
        if phone:
            address = address[: phone.start()].strip(" .,")
        return address

    @staticmethod
    def _extract_customer(text: str) -> dict:
        import re
        name = None
        m = re.search(
            r"(?:mi nombre es|soy|me llamo)\s+([a-záéíóúññ\s]{2,40})",
            text, re.IGNORECASE,
        )
        if m:
            raw = m.group(1).strip()
            # cortar en conectores que separan el nombre del resto de la frase
            for stop in (" y mi ", " mi celular", " mi telefono", " mi teléfono",
                         " mi numero", " mi número", ",", "."):
                idx = raw.lower().find(stop)
                if idx > 0:
                    raw = raw[:idx]
            if raw:
                name = raw.strip().title()
        m = re.search(r"(?:celular|telefono|teléfono|mi numero|mi número)?\s*(\d{9})", text)
        phone = m.group(1) if m else None
        return {"name": name, "phone": phone}

    async def complete(self, messages: list[dict], temperature: float = 0.2, **kwargs) -> str:
        """Respuesta determinista: confirma si hay items; si no, pide repetir.

        Fase 2: llamada real al proveedor (DeepSeek/Groq) con el mismo
        messages (system = format_context_for_llm(build_conversation_context)).
        """
        user_text = " ".join(
            str(m.get("content", "")) for m in messages if m.get("role") == "user"
        )
        order = self.parse_order(user_text)
        if not order["matched"]:
            return "Disculpe, no le entendí. ¿Podría repetir su pedido, por favor?"
        names = ", ".join(f"{i['quantity']} {i['name']}" for i in order["items"])
        return f"Perfecto, anoté: {names}. ¿Desea confirmar su pedido?"


class DeterministicVoiceProvider(VoiceProvider):
    """Pipeline completo de prueba: echo STT + stub TTS + LLM determinista.

    Compone los tres puertos y además detecta el motivo de transferencia en
    el texto del cliente (R2) — el bridge de Fase 2 usará esta misma
    estructura con proveedores reales.
    """

    name = "deterministic"

    def __init__(
        self,
        stt: STTProvider | None = None,
        tts: TTSProvider | None = None,
        llm: LLMClient | None = None,
    ):
        self.stt = stt or EchoSTTProvider()
        self.tts = tts or LocalTTSProvider()
        self.llm = llm or DeterministicLLMClient()

    async def respond(
        self,
        audio: bytes | None = None,
        context: dict | None = None,
        language: str = "es",
    ) -> dict:
        stt_result = await self.stt.transcribe(audio, language=language)
        messages = [
            {"role": "system", "content": _context_prompt(context)},
            {"role": "user", "content": stt_result.text},
        ]
        reply = await self.llm.complete(messages)
        tts_result = await self.tts.synthesize(reply)
        return {
            "transcript": stt_result.text,
            "reply": reply,
            "audio_path": tts_result.path,
            "cost_usd": round(
                stt_result.cost_estimate + tts_result.cost_estimate + 0.0005, 6,
            ),
            "transfer_reason": detect_transfer_reason(stt_result.text),
            "state": _state_for_transcript(stt_result.text),
        }


def _context_prompt(context: dict | None) -> str:
    """Prompt de dominio desde el contexto real (R1) — Fase 2 lo usa tal cual."""
    from app.services.voice_ai_service import format_context_for_llm
    return format_context_for_llm(context)


def _state_for_transcript(text: str) -> str:
    """Estado sugerido para el PATCH /ai-state según el texto (heurística F1)."""
    reason = detect_transfer_reason(text)
    if reason:
        return "transfer"
    norm = text.lower()
    if any(w in norm for w in ("si, confirma", "sí, confirma", "confirmo", "esta bien", "está bien", "dale", "ok")):
        return "confirming"
    if any(w in norm for w in ("quiero", "quisiera", "me da", "un ", "una ", "dos ")):
        return "taking_order"
    return "greeting"
