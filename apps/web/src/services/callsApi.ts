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

/** Eventos del WS /ws/calls/{tenant_id} (Spec 05 §3.5.3) */
export type CallWsEvent =
  | {
      event: "call.incoming";
      external_call_id: string;
      caller: string;
      callee: string;
      started_at: string;
    }
  | {
      event: "call.answered";
      external_call_id: string;
      caller: string;
      answered_at: string;
    }
  | {
      event: "call.ended";
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
        external_call_id: s("external_call_id"),
        caller: s("caller"),
        callee: s("callee"),
        started_at: s("started_at"),
      };
    case "call.answered":
      return {
        event: "call.answered",
        external_call_id: s("external_call_id"),
        caller: s("caller"),
        answered_at: s("answered_at"),
      };
    case "call.ended": {
      const status = s("status") as CallStatus;
      return {
        event: "call.ended",
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
    default:
      return null;
  }
}

export function callsWsUrl(tenantId: number | string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/calls/ws/${tenantId}`;
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
