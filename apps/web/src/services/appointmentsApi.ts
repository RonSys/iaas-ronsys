/**
 * Appointments API — Agenda de Citas (Spec 07 F6).
 *
 * Contratos consumidos (Spec 07 §3.3 — backend implementado en paralelo):
 *   GET  /api/v1/appointments/availability?date=YYYY-MM-DD&guests=N&from=HH:MM&to=HH:MM
 *        → 200 { slots: [ { table_id, table_number, section, capacity, start, end } ] }
 *   POST /api/v1/appointments
 *        Body: { table_id?, date, time, guests, customer_name, customer_phone?, notes?, source }
 *        → 201 { id, ... }  (409 doble reserva · 422 fuera de ventana / guests > capacidad)
 *   GET  /api/v1/appointments?date=&status=&source= → 200 { items: [...], total }
 *   PATCH /api/v1/appointments/{id}
 *        Body: { status: "confirmada"|"cumplida"|"cancelada"|"no_show", table_id? }
 *        → 200 (transiciones validadas R5; espejo tables.status='reserved' D1)
 *   POST /api/v1/appointments/{id}/remind → 202 (evento appointment.reminder → cola F1)
 *
 * Config por tenant `companies.settings.appointments` (patrón D-03) expuesta por
 * GET/PATCH /api/settings — mismo mecanismo que voice_ai (callsApi.ts).
 *
 * ⚠️ REQUISITO RON: los fixtures/mocks de tests usan tenant-id = 3.
 *
 * @module services/appointmentsApi
 */
import { authFetch } from "./authFetch";

// ─── Tipos ────────────────────────────────────────────────

/** Estados de cita — espejo del CHECK en BD (Spec 07 §3.1, transiciones R5) */
export type AppointmentStatus =
  | "solicitada"
  | "confirmada"
  | "cumplida"
  | "cancelada"
  | "no_show";

/** Canales de origen (Spec 07 D7). En F6 la UI solo crea `in_person` (staff);
 *  `voice_ai` llega de la Recepcionista IA; web/whatsapp quedan como registro. */
export type AppointmentSource = "voice_ai" | "whatsapp" | "web" | "in_person";

export const APPOINTMENT_STATUSES: AppointmentStatus[] = [
  "solicitada",
  "confirmada",
  "cumplida",
  "cancelada",
  "no_show",
];

export const APPOINTMENT_STATUS_LABEL: Record<AppointmentStatus, string> = {
  solicitada: "Solicitada",
  confirmada: "Confirmada",
  cumplida: "Cumplida",
  cancelada: "Cancelada",
  no_show: "No show",
};

export const APPOINTMENT_SOURCE_LABEL: Record<AppointmentSource, string> = {
  voice_ai: "Voz",
  whatsapp: "WhatsApp",
  web: "Web",
  in_person: "Staff",
};

/** Cita completa (GET list / POST create / PATCH) */
export interface Appointment {
  id: number;
  table_id: number | null;
  table_number?: string | null;
  section?: string | null;
  customer_name: string;
  customer_phone: string | null;
  guests: number;
  starts_at: string; // ISO timestamptz (fecha + hora local de la cita)
  duration_min: number;
  status: AppointmentStatus;
  source: AppointmentSource;
  notes: string | null;
  call_id: string | null; // external_call_id de F2/F3 (trazabilidad voz, R6)
  created_at?: string;
  updated_at?: string;
}

export interface AppointmentListParams {
  date?: string; // YYYY-MM-DD
  status?: AppointmentStatus | "";
  source?: AppointmentSource | "";
}

export interface AppointmentListResponse {
  items: Appointment[];
  total: number;
}

export interface AvailabilityParams {
  date: string; // YYYY-MM-DD
  guests: number;
  from: string; // HH:MM
  to: string; // HH:MM
}

/** Slot de mesa libre (Spec 07 §3.3 — start/end en HH:MM local) */
export interface AvailabilitySlot {
  table_id: number;
  table_number: string;
  section: string | null;
  capacity: number;
  start: string;
  end: string;
}

export interface AvailabilityResponse {
  slots: AvailabilitySlot[];
}

/** Body de POST /api/v1/appointments (Spec 07 §3.3) */
export interface CreateAppointmentPayload {
  table_id?: number | null;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  guests: number;
  customer_name: string;
  customer_phone?: string | null;
  notes?: string | null;
  source: AppointmentSource;
}

/** Body de PATCH /api/v1/appointments/{id} (Spec 07 §3.3 — transición de estado) */
export interface PatchAppointmentPayload {
  status?: AppointmentStatus;
  table_id?: number | null;
}

/** Respuesta de POST /api/v1/appointments/{id}/remind (202 → evento en cola) */
export interface RemindResult {
  ok?: boolean;
  message?: string;
}

export interface AppointmentHours {
  open: string; // "HH:MM"
  close: string; // "HH:MM"
}

/** Config por tenant `companies.settings.appointments` (Spec 07 §3.2, D-03/D3/D4) */
export interface AppointmentSettings {
  enabled: boolean;
  /** D3: ventana de reservas independiente, editable desde UI staff (default 12:00–23:00) */
  hours: AppointmentHours;
  /** D4: duración por defecto de la cita (mesa libre con duración) */
  duration_min_default: number;
  slot_granularity_min: number;
  max_guests_per_table: number;
  reminder_hours_before: number;
  templates: {
    appointment_confirmed: string;
    appointment_reminder: string;
  };
}

/** Defaults Spec 07 §3.2 (D3: 12:00–23:00 · D4: 60 min · recordatorio 24h) */
export const DEFAULT_APPOINTMENT_SETTINGS: AppointmentSettings = {
  enabled: false,
  hours: { open: "12:00", close: "23:00" },
  duration_min_default: 60,
  slot_granularity_min: 30,
  max_guests_per_table: 12,
  reminder_hours_before: 24,
  templates: {
    appointment_confirmed: "appointment_confirmed",
    appointment_reminder: "appointment_reminder",
  },
};

/** Patch parcial de settings (PATCH /api/settings { appointments }) — sub-objetos
 *  hours/templates admiten merges parciales de 1 nivel (patrón voice_ai). */
export type AppointmentSettingsPatch = Partial<
  Omit<AppointmentSettings, "hours" | "templates">
> & {
  hours?: Partial<AppointmentHours>;
  templates?: Partial<AppointmentSettings["templates"]>;
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

// ─── Helpers puros (fecha/hora locales; testables sin DOM) ──

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** Fecha local de hoy como "YYYY-MM-DD" */
export function todayLocal(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
}

/** "YYYY-MM-DD" + "HH:MM" → ISO local (para starts_at) */
export function appointmentStartsAt(date: string, time: string): string {
  const [h, m] = time.split(":").map(Number);
  const d = new Date(`${date}T00:00:00`);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
}

/** ISO → "HH:MM" local (hora de la cita) */
export function formatAppointmentTime(iso: string): string {
  const d = new Date(iso);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** ISO + duración → "HH:MM" local (hora fin de la cita) */
export function formatAppointmentEnd(iso: string, durationMin: number): string {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() + durationMin);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** "HH:MM" + minutos → "HH:MM" (wrap 24h; para el rango del modal) */
export function addMinutesToTime(time: string, minutes: number): string {
  const [h, m] = time.split(":").map(Number);
  const total = h * 60 + m + minutes;
  const hh = ((Math.floor(total / 60) % 24) + 24) % 24;
  const mm = ((total % 60) + 60) % 60;
  return `${pad2(hh)}:${pad2(mm)}`;
}

/** Acepta `{items: [...]}` (contrato) o array plano; nunca revienta */
export function normalizeAppointments(data: unknown): Appointment[] {
  if (Array.isArray(data)) return data as Appointment[];
  if (data && typeof data === "object" && Array.isArray((data as { items?: unknown }).items)) {
    return (data as { items: Appointment[] }).items;
  }
  return [];
}

/** Acepta `{slots: [...]}` (contrato) o array plano */
export function normalizeSlots(data: unknown): AvailabilitySlot[] {
  if (Array.isArray(data)) return data as AvailabilitySlot[];
  if (data && typeof data === "object" && Array.isArray((data as { slots?: unknown }).slots)) {
    return (data as { slots: AvailabilitySlot[] }).slots;
  }
  return [];
}

/** Merge con defaults para configs parciales persistidas (patrón voice_ai) */
export function mergeAppointmentSettings(
  raw: AppointmentSettingsPatch | null | undefined,
): AppointmentSettings {
  if (!raw || typeof raw !== "object") return { ...DEFAULT_APPOINTMENT_SETTINGS };
  return {
    ...DEFAULT_APPOINTMENT_SETTINGS,
    ...raw,
    hours: { ...DEFAULT_APPOINTMENT_SETTINGS.hours, ...(raw.hours ?? {}) },
    templates: { ...DEFAULT_APPOINTMENT_SETTINGS.templates, ...(raw.templates ?? {}) },
  };
}

// ─── Disponibilidad (D2/D4 — mesa libre con duración) ─────

/**
 * GET /api/v1/appointments/availability — mesas libres en la ventana
 * [from, to) con capacidad ≥ guests (CA-F6-3). Sin solapamiento con citas
 * activas de la misma mesa (regla dura anti-doble-reserva, R2).
 */
export async function getAvailability(params: AvailabilityParams): Promise<AvailabilitySlot[]> {
  const qs = new URLSearchParams({
    date: params.date,
    guests: String(params.guests),
    from: params.from,
    to: params.to,
  });
  const res = await authFetch(`/api/v1/appointments/availability?${qs.toString()}`);
  if (!res.ok) throw await parseError(res);
  return normalizeSlots(await res.json());
}

// ─── CRUD de citas ────────────────────────────────────────

/**
 * POST /api/v1/appointments — crea cita (CA-F6-1).
 * 409 doble reserva (R2) · 422 fuera de ventana o guests > capacidad (R3/R4).
 * source: la UI staff usa "in_person" (D7 — solo staff + voz en F6).
 */
export async function createAppointment(payload: CreateAppointmentPayload): Promise<Appointment> {
  const res = await authFetch("/api/v1/appointments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/** GET /api/v1/appointments?date=&status=&source= — agenda filtrada (staff) */
export async function listAppointments(
  params: AppointmentListParams = {},
): Promise<AppointmentListResponse> {
  const qs = new URLSearchParams();
  if (params.date) qs.set("date", params.date);
  if (params.status) qs.set("status", params.status);
  if (params.source) qs.set("source", params.source);
  const q = qs.toString();
  const res = await authFetch(`/api/v1/appointments${q ? `?${q}` : ""}`);
  if (!res.ok) throw await parseError(res);
  const body = (await res.json()) as AppointmentListResponse | Appointment[];
  if (Array.isArray(body)) return { items: body, total: body.length };
  return { items: body.items ?? [], total: body.total ?? body.items?.length ?? 0 };
}

/**
 * PATCH /api/v1/appointments/{id} — transiciones de estado (R5):
 * solicitada→confirmada|cancelada · confirmada→cumplida|cancelada|no_show.
 * El backend sincroniza el espejo tables.status='reserved' (D1, CA-F6-5/6).
 */
export async function patchAppointment(
  id: number,
  payload: PatchAppointmentPayload,
): Promise<Appointment> {
  const res = await authFetch(`/api/v1/appointments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

/** POST /api/v1/appointments/{id}/remind — recordatorio manual (202 → cola F1) */
export async function remindAppointment(id: number): Promise<RemindResult> {
  const res = await authFetch(`/api/v1/appointments/${id}/remind`, { method: "POST" });
  if (!res.ok) throw await parseError(res);
  const body = (await res.json().catch(() => ({}))) as RemindResult;
  return body ?? {};
}

// ─── Config por tenant — companies.settings.appointments (D-03/D3) ──

/**
 * GET /api/settings → companies.settings.appointments (Spec 07 §3.2).
 * Merge con defaults: configs parciales (ej. solo hours) completan el resto.
 */
export async function getAppointmentSettings(): Promise<AppointmentSettings> {
  const res = await authFetch("/api/settings");
  if (!res.ok) throw await parseError(res);
  const body = (await res.json()) as { appointments?: Partial<AppointmentSettings> };
  return mergeAppointmentSettings(body.appointments);
}

/**
 * PATCH /api/settings { appointments } — merge parcial (D3: horarios editables
 * desde la UI staff; mismo mecanismo que voice_ai en callsApi.ts).
 */
export async function patchAppointmentSettings(
  patch: AppointmentSettingsPatch,
): Promise<AppointmentSettings> {
  const res = await authFetch("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appointments: patch }),
  });
  if (!res.ok) throw await parseError(res);
  const body = (await res.json()) as { appointments?: AppointmentSettingsPatch };
  return mergeAppointmentSettings(body.appointments);
}
