/**
 * Calls API — Central Telefónica (Spec F2 "Central que No Pierde Llamadas", §3.5).
 *
 * Endpoints autenticados (/api/v1/calls*) usando authFetch (JWT + X-Tenant-ID),
 * mismo patrón que deliveryApi.ts.
 *
 * Contratos consumidos (Spec 05 §3.5.1/3.5.3):
 *   GET  /api/v1/calls?status=&direction=&from=&to=&limit=&offset=
 *   GET  /api/v1/calls/{id}
 *   POST /api/v1/calls/{id}/convert-to-order
 *   POST /api/v1/calls/originate
 *   WS   /ws/calls/{tenant_id}   (shorthand de la spec — resuelto en callsWsUrl)
 *
 * @module services/callsApi
 */
import { authFetch } from "./authFetch";

// ─── Tipos ────────────────────────────────────────────────

export type CallStatus =
  | "ringing"
  | "in_progress"
  | "answered"
  | "missed"
  | "completed"
  | "failed";

export type CallDirection = "inbound" | "outbound";

export interface CallRecord {
  id: number;
  external_call_id: string;
  caller: string;
  callee: string;
  direction: CallDirection;
  status: CallStatus;
  started_at: string;
  answered_at: string | null;
  ended_at: string | null;
  duration: number;
  recording_path: string | null;
  converted_order_id: number | null;
  metadata: Record<string, unknown> | null;
}

export interface CallListParams {
  status?: CallStatus | "";
  direction?: CallDirection | "";
  /** ISO fecha inicio (rango started_at) */
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

export interface CallListResponse {
  items: CallRecord[];
  total: number;
}

/** Payload de POST /api/v1/calls/{id}/convert-to-order (Spec 05 §3.5.1) */
export interface ConvertToOrderPayload {
  zone_id: number;
  items: {
    menu_item_id: number;
    quantity: number;
    modifiers: { id: number; quantity: number }[];
  }[];
  customer: {
    name?: string | null;
    phone?: string | null;
    address: string;
  };
  payment: {
    method: "yape" | "plin" | "cash";
    reference?: string | null;
  };
  notes?: string | null;
}

/** Respuesta 201 de convert-to-order — reusa DeliveryService.create_order (R7) */
export interface ConvertToOrderResult {
  tracking_code: string;
  sale_id: number;
  sale_number: string;
  status: string;
  totals: { subtotal: number; discount_total: number; fee: number; total: number };
  call_id: number;
}

export interface OriginatePayload {
  target: string;
  extension: string;
}

export interface OriginateResult {
  external_call_id: string;
  status: string;
}

/** Estados conversacionales de la Recepcionista IA (Spec 06 §3.6 — espejo de AI_STATES backend) */
export type AiState =
  | "greeting"
  | "taking_order"
  | "clarifying"
  | "confirming"
  | "transfer"
  | "hangup"
  | "completed"
  | "failed";

/** Motivos de transferencia a humano (Spec 06 D9 — espejo de TRANSFER_REASONS backend) */
export type AiTransferReason =
  | "complaint"
  | "out_of_domain"
  | "low_confidence"
  | "user_requested"
  | "budget";

/** Estados IA válidos (AI_STATES del backend — app/adapters/db/models/calls.py) */
export const AI_STATES: AiState[] = [
  "greeting",
  "taking_order",
  "clarifying",
  "confirming",
  "transfer",
  "hangup",
  "completed",
  "failed",
];

export const AI_STATE_LABEL: Record<AiState, string> = {
  greeting: "Saludo",
  taking_order: "Tomando pedido",
  clarifying: "Aclarando",
  confirming: "Confirmando",
  transfer: "Transferiendo",
  hangup: "Colgando",
  completed: "Completada",
  failed: "Fallida",
};

/**
 * Info IA de una llamada — poblada en el panel en vivo desde el WS
 * (`ai_call_state` / `call.transferred`, Spec 06 §3.5.2/§3.5.1).
 *
 * NOTA verificada contra el backend (2026-08-13): el evento WS `ai_call_state`
 * NO incluye `cost_usd` y el GET staff de llamadas tampoco lo expone hoy — el
 * campo queda tipado para cuando el backend lo publique (CA-F3-8); mientras
 * tanto el panel muestra `cost_estimate` de la transcripción (STT).
 */
export interface AiCallStateInfo {
  external_call_id: string;
  call_record_id?: number | null;
  caller?: string;
  ai_state?: AiState | null;
  duration_sec?: number;
  converted_order_id?: number | null;
  transfer_reason?: string | null;
  context_summary?: string | null;
  cost_usd?: number;
}

/** Payload de GET/PATCH /api/v1/calls/{external_call_id}/ai-state (espejo AiStateOut) */
export interface AiStateOut {
  external_call_id: string;
  call_record_id?: number | null;
  caller?: string | null;
  callee?: string | null;
  call_status?: string | null;
  ai_state?: AiState | null;
  transfer_reason?: string | null;
  context_summary?: string | null;
  duration_sec?: number;
  cost_usd?: number;
  converted_order_id?: number | null;
  transcription_id?: number | null;
  transcription_text?: string | null;
  budget?: Record<string, unknown>;
  updated_at?: string | null;
}

/** Body de POST /api/v1/calls/{external_call_id}/transfer (Spec 06 §3.5.1) */
export interface AiTransferRequest {
  reason: AiTransferReason;
  context_summary?: string | null;
  priority?: "normal" | "high";
}

export interface AiTransferResult {
  external_call_id: string;
  transferred_to?: string | null;
  via?: string;
  ai_state?: string;
  transfer_reason?: string;
  context_summary?: string | null;
  priority?: string;
}

/** Segmento de transcripción (start/end/speaker/text/confidence) */
export interface TranscriptionSegment {
  start?: number | null;
  end?: number | null;
  speaker?: string | null;
  text: string;
  confidence?: number | null;
}

/** Transcripción completa (espejo TranscriptionOut — GET staff CA-F3-3) */
export interface Transcription {
  id: number;
  tenant_id: number;
  call_id: string;
  call_record_id: number;
  provider: string;
  text: string;
  segments?: TranscriptionSegment[] | null;
  lang?: string;
  duration_sec?: number | null;
  /** Costo STT estimado USD (R4/CA-F3-8) — único costo visible por staff hoy */
  cost_estimate?: number;
  created_at?: string | null;
}

/**
 * Config de voz por tenant `companies.settings.voice_ai` (Spec 06 §3.3) —
 * expuesta por GET/PATCH /api/settings. Espejo de VoiceAiSettings del backend.
 * api_key NUNCA se muestra en UI (solo settings por tenant).
 */
export interface VoiceAiSettings {
  enabled: boolean;
  kill_switch: boolean;
  max_calls_concurrent: number;
  stt: { provider: string; model: string; language: string; api_key?: string | null };
  tts: { provider: string; voice: string; api_key?: string | null };
  llm: { provider: string; model: string; api_key?: string | null };
  transfer: { confidence_threshold: number; max_clarify_attempts: number };
  budget: { max_usd_per_minute: number; daily_budget_usd: number };
  greeting: string;
  payment_method: string;
}

/** Eventos del WS /ws/calls/{tenant_id} (Spec 05 §3.5.3 + Spec 06 §3.5.2) */
export type CallWsEvent =
  | {
      event: "call.incoming";
      id: number;
      external_call_id: string;
      caller: string;
      callee: string;
      direction?: string;
      started_at: string;
    }
  | {
      event: "call.answered";
      id: number;
      external_call_id: string;
      caller: string;
      answered_at: string;
    }
  | {
      event: "call.ended";
      id: number;
      external_call_id: string;
      caller: string;
      duration: number;
      status: CallStatus;
      hangup_cause?: string | null;
    }
  | {
      event: "call.recording_ready";
      external_call_id: string;
      recording_path: string;
    }
  | {
      event: "call.converted";
      external_call_id: string;
      tracking_code: string;
      sale_id: number;
    }
  /**
   * Spec 06 §3.5.2 (R10): estado conversacional del agente IA en vivo.
   * Publicado por `_broadcast_ai_state` (app/services/voice_ai_service.py).
   */
  | {
      event: "ai_call_state";
      external_call_id: string;
      call_record_id?: number | null;
      caller?: string;
      ai_state?: AiState | null;
      duration_sec?: number;
      converted_order_id?: number | null;
      transfer_reason?: string | null;
      context_summary?: string | null;
    }
  /**
   * Spec 06 §3.5.1 (D9): transferencia a humano — publicado por
   * `transfer_call` (voice_ai_service.py) con motivo + resumen + ext SIP.
   */
  | {
      event: "call.transferred";
      external_call_id: string;
      caller?: string;
      transfer_reason?: string | null;
      context_summary?: string | null;
      transferred_to?: string | null;
      via?: string;
      priority?: string;
    };

/**
 * Envoltura real del WsManager del backend (patrón spec 03 §2.2, clonado en
 * spec 05 §3.5.3): `{"event": <event>, "data": {…}}`. La spec 05 describe los
 * eventos "planos" (`call.incoming {external_call_id, …}`).
 *
 * INTERPRETACIÓN DOCUMENTADA: el parseo acepta AMBOS formatos (envoltura
 * `data` del backend y plano de la spec) para no acoplarse a la implementación
 * en paralelo del backend.
 */
export interface CallWsEnvelope {
  event?: string;
  data?: Record<string, unknown>;
}

/** Estados que cuentan como "llamada en vivo" en el panel */
export const LIVE_STATUSES: CallStatus[] = ["ringing", "in_progress", "answered"];

export const CALL_STATUS_LABEL: Record<CallStatus, string> = {
  ringing: "Sonando",
  in_progress: "En curso",
  answered: "Contestada",
  missed: "Perdida",
  completed: "Completada",
  failed: "Fallida",
};

export const CALL_DIRECTION_LABEL: Record<CallDirection, string> = {
  inbound: "Entrante",
  outbound: "Saliente",
};

// ─── Error tipado (409/422/404 manejables desde la UI) ────

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => ({}));
  const detail = (body as { detail?: unknown }).detail;
  let message = `Error (${res.status})`;
  if (typeof detail === "string") {
    message = detail;
  } else if (detail && typeof detail === "object") {
    const d = detail as { message?: unknown; msg?: unknown };
    if (typeof d.message === "string") message = d.message;
    else if (typeof d.msg === "string") message = d.msg;
  }
  return new ApiError(message, res.status, detail);
}

// ─── Llamadas (list/detail) ───────────────────────────────

export async function getCalls(params: CallListParams = {}): Promise<CallListResponse> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.direction) qs.set("direction", params.direction);
  if (params.from) qs.set("from", params.from);
  if (params.to) qs.set("to", params.to);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  const q = qs.toString();
  const res = await authFetch(`/api/v1/calls${q ? `?${q}` : ""}`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function getCall(id: number): Promise<CallRecord> {
  const res = await authFetch(`/api/v1/calls/${id}`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

// ─── Convertir a pedido (R6/R7) ───────────────────────────

/**
 * Convierte una llamada en pedido de delivery (reusa create_order).
 * Errores tipados: 409 conversión duplicada, 422 estado/ítems inválidos,
 * 404 llamada inexistente (Spec 05 §3.5.1).
 */
export async function convertCallToOrder(
  callId: number,
  payload: ConvertToOrderPayload,
): Promise<ConvertToOrderResult> {
  const res = await authFetch(`/api/v1/calls/${callId}/convert-to-order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

// ─── Click-to-call (CA-F2.8) ──────────────────────────────

/** Originate vía ARI: 202 { external_call_id, status: "ringing" } | 400 | 409 */
export async function originateCall(payload: OriginatePayload): Promise<OriginateResult> {
  const res = await authFetch("/api/v1/calls/originate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

// ─── WebSocket ────────────────────────────────────────────

/**
 * URL del WS en vivo.
 *
 * INTERPRETACIÓN DOCUMENTADA: la spec (§3.5.3) escribe `WS /ws/calls/{tenant_id}`,
 * pero igual que la spec 03 escribe `ws/kitchen/{tenant_id}` cuando la URL real es
 * `/api/v1/restaurant/ws/kitchen/{tenant_id}` (router con prefix `/api/v1/restaurant`),
 * aquí el shorthand resuelve al router de calls (prefix `/api/v1/calls`, §3.5.1):
 *   → `/api/v1/calls/ws/{tenant_id}`
 * El proxy de Vite redirige `/api/*` al backend (vite.config.ts).
 */
/**
 * Normaliza un mensaje WS crudo a un evento tipado, aceptando tanto la
 * envoltura del backend `{"event", "data"}` como el formato plano de la spec
 * (`{event, external_call_id, …}`). Devuelve `null` si no es un evento
 * conocido o el payload está malformado (los eventos desconocidos se ignoran).
 */
export function parseCallWsMessage(raw: string): CallWsEvent | null {
  let msg: unknown;
  try {
    msg = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!msg || typeof msg !== "object") return null;
  const obj = msg as CallWsEnvelope;
  const eventName = typeof obj.event === "string" ? obj.event : null;
  if (!eventName) return null;

  const d =
    obj.data && typeof obj.data === "object" ? obj.data : (obj as Record<string, unknown>);
  const s = (k: string): string =>
    typeof d[k] === "string" ? (d[k] as string) : "";
  const n = (k: string): number | null => {
    const v = d[k];
    return typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : null;
  };

  switch (eventName) {
    case "call.incoming":
      return {
        event: "call.incoming",
        id: n("id") ?? 0,
        external_call_id: s("external_call_id"),
        caller: s("caller"),
        callee: s("callee"),
        direction: s("direction") as CallDirection | undefined,
        started_at: s("started_at"),
      };
    case "call.answered":
      return {
        event: "call.answered",
        id: n("id") ?? 0,
        external_call_id: s("external_call_id"),
        caller: s("caller"),
        answered_at: s("answered_at"),
      };
    case "call.ended": {
      const status = s("status") as CallStatus;
      return {
        event: "call.ended",
        id: n("id") ?? 0,
        external_call_id: s("external_call_id"),
        caller: s("caller"),
        duration: n("duration") ?? 0,
        status: LIVE_STATUSES.includes(status) || CALL_STATUS_LABEL[status] ? status : "completed",
        hangup_cause: s("hangup_cause") || null,
      };
    }
    case "call.recording_ready":
      return {
        event: "call.recording_ready",
        external_call_id: s("external_call_id"),
        recording_path: s("recording_path"),
      };
    case "call.converted":
      return {
        event: "call.converted",
        external_call_id: s("external_call_id"),
        tracking_code: s("tracking_code"),
        sale_id: n("sale_id") ?? 0,
      };
    case "ai_call_state": {
      const state = s("ai_state") as AiState;
      return {
        event: "ai_call_state",
        external_call_id: s("external_call_id"),
        call_record_id: n("call_record_id"),
        caller: s("caller") || undefined,
        ai_state: AI_STATES.includes(state) ? state : null,
        duration_sec: n("duration_sec") ?? undefined,
        converted_order_id: n("converted_order_id"),
        transfer_reason: s("transfer_reason") || null,
        context_summary: s("context_summary") || null,
      };
    }
    case "call.transferred":
      return {
        event: "call.transferred",
        external_call_id: s("external_call_id"),
        caller: s("caller") || undefined,
        transfer_reason: s("transfer_reason") || null,
        context_summary: s("context_summary") || null,
        transferred_to: s("transferred_to") || null,
        via: s("via") || undefined,
        priority: s("priority") || undefined,
      };
    default:
      return null;
  }
}

export function callsWsUrl(tenantId: number | string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/calls/ws/${tenantId}`;
}

// ─── Recepcionista IA (F3 — Spec 06 §3.5) ───────────────────

/**
 * GET /api/v1/calls/{external_call_id}/ai-state — estado IA + costo + contexto.
 *
 * ⚠️ VERIFICADO CONTRA BACKEND (2026-08-13): este endpoint es del bridge
 * (X-Service-Token + allowlist IP, CA-F2.5) — el token de staff NO lo puede
 * llamar hoy. El panel obtiene el estado en vivo por WS `ai_call_state`; esta
 * función queda como contrato para cuando el backend exponga variante staff
 * (Spec 06 §3.5.2: "detalle F2 + ai_state, context_summary, cost_usd").
 */
export async function getAiState(callId: string): Promise<AiStateOut> {
  const res = await authFetch(`/api/v1/calls/${encodeURIComponent(callId)}/ai-state`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/**
 * PATCH /api/v1/calls/{external_call_id}/ai-state — actualiza estado IA.
 * Mismo caveat de auth bridge que getAiState.
 */
export async function patchAiState(
  callId: string,
  body: { state: AiState; transfer_reason?: string; context_summary?: string },
): Promise<AiStateOut> {
  const res = await authFetch(`/api/v1/calls/${encodeURIComponent(callId)}/ai-state`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/**
 * POST /api/v1/calls/{external_call_id}/transfer — transferencia a humano (D9).
 *
 * ⚠️ VERIFICADO CONTRA BACKEND (2026-08-13): también bridge-only (CA-F2.5);
 * con token de staff devuelve 401. El panel llama esta función y muestra el
 * error con contexto cuando el bridge aún no expone la vía staff (Fase 2 —
 * el ring a la extensión lo ejecuta el bridge, no el panel).
 * Alias equivalente: POST /api/v1/ai-calls/{external_call_id}/transfer.
 */
export async function transferCall(
  callId: string,
  body: AiTransferRequest,
): Promise<AiTransferResult> {
  const res = await authFetch(`/api/v1/calls/${encodeURIComponent(callId)}/transfer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/**
 * GET /api/v1/calls/{call_ref}/transcript — transcripción recuperable por
 * id de llamada o external_call_id (CA-F3-3). ÚNICO endpoint F3 staff hoy.
 */
export async function getTranscript(callRef: string | number): Promise<Transcription> {
  const res = await authFetch(`/api/v1/calls/${encodeURIComponent(String(callRef))}/transcript`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/**
 * GET /api/settings → companies.settings.voice_ai (Spec 06 §3.3, D-03).
 * Auth staff estándar (JWT + X-Tenant-ID).
 */
export async function getVoiceAiSettings(): Promise<VoiceAiSettings> {
  const res = await authFetch("/api/settings");
  if (!res.ok) throw await parseError(res);
  const body = (await res.json()) as { voice_ai?: VoiceAiSettings };
  return body.voice_ai ?? ({} as VoiceAiSettings);
}

/**
 * PATCH /api/settings { voice_ai } — merge parcial de 1 nivel en el backend:
 * los sub-objetos (budget/stt/tts/llm/transfer) se REEMPLAZAN enteros si se
 * envían → enviar el sub-objeto completo al tocar (ej. budget completo).
 * Los campos top-level (enabled, kill_switch, greeting, …) se mergean bien.
 */
export async function patchVoiceAiSettings(
  patch: Partial<VoiceAiSettings>,
): Promise<VoiceAiSettings> {
  const res = await authFetch("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice_ai: patch }),
  });
  if (!res.ok) throw await parseError(res);
  const body = (await res.json()) as { voice_ai?: VoiceAiSettings };
  return body.voice_ai ?? ({} as VoiceAiSettings);
}

/**
 * Href de descarga/escucha de la grabación (R1).
 * - URL absoluta (http/https) o root-relative → link directo.
 * - Otro alias (ej. ruta interna del volumen MixMonitor) → null (se muestra como texto;
 *   el backend debe exponer un alias descargable para estos casos).
 */
export function recordingHref(recordingPath: string): string | null {
  if (/^https?:\/\//i.test(recordingPath)) return recordingPath;
  if (recordingPath.startsWith("/")) return recordingPath;
  return null;
}
