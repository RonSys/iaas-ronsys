/**
 * 📅 Agenda de Citas (Spec 07 F6) — Panel staff de reservas por mesa.
 *
 * - Vista del día: lista de citas ordenadas por hora con estado, mesa, cliente,
 *   comensales, fuente (badge) y notas.
 * - Filtros: fecha + estado + fuente (GET /api/v1/appointments).
 * - Acciones rápidas (transiciones R5): confirmar / cumplir / cancelar / no_show
 *   (PATCH /api/v1/appointments/{id}) + recordatorio manual (POST .../remind).
 * - "Nueva cita": modal con fecha, hora, duración, personas, nombre, teléfono y
 *   notas — selector de mesa basado en disponibilidad REAL (D4: mesa libre con
 *   duración; GET /api/v1/appointments/availability). La cita se crea con
 *   source="in_person" (D7: solo staff + voz en F6).
 * - Banner si la agenda está desactivada (companies.settings.appointments.enabled,
 *   D3 — configurable desde Settings).
 *
 * @module pages/restaurante/AgendaPage
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import {
  ApiError,
  addMinutesToTime,
  formatAppointmentEnd,
  formatAppointmentTime,
  getAppointmentSettings,
  getAvailability,
  listAppointments,
  patchAppointment,
  remindAppointment,
  createAppointment,
  todayLocal,
  type Appointment,
  type AppointmentSettings,
  type AppointmentSource,
  type AppointmentStatus,
  type AvailabilitySlot,
  APPOINTMENT_STATUS_LABEL,
  APPOINTMENT_STATUSES,
  APPOINTMENT_SOURCE_LABEL,
  DEFAULT_APPOINTMENT_SETTINGS,
} from "@/services/appointmentsApi";

const STATUS_BADGE: Record<AppointmentStatus, string> = {
  solicitada: "bg-blue-100 text-blue-700",
  confirmada: "bg-green-100 text-green-700",
  cumplida: "bg-emerald-100 text-emerald-800",
  cancelada: "bg-red-100 text-red-700",
  no_show: "bg-slate-200 text-slate-600",
};

const SOURCE_BADGE: Record<AppointmentSource, string> = {
  voice_ai: "bg-purple-100 text-purple-700",
  whatsapp: "bg-teal-100 text-teal-700",
  web: "bg-cyan-100 text-cyan-700",
  in_person: "bg-gray-100 text-gray-600",
};

const SOURCE_ICON: Record<AppointmentSource, string> = {
  voice_ai: "🤖",
  whatsapp: "💬",
  web: "🌐",
  in_person: "🧑‍💼",
};

export function AgendaPage() {
  const [date, setDate] = useState(todayLocal());
  const [statusFilter, setStatusFilter] = useState<"" | AppointmentStatus>("");
  const [sourceFilter, setSourceFilter] = useState<"" | AppointmentSource>("");
  const [items, setItems] = useState<Appointment[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<AppointmentSettings>(DEFAULT_APPOINTMENT_SETTINGS);
  const [showNew, setShowNew] = useState(false);
  const [actingId, setActingId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAppointments({
        date,
        status: statusFilter,
        source: sourceFilter,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }, [date, statusFilter, sourceFilter]);

  useEffect(() => {
    load();
  }, [load]);

  // D3: config de la agenda (ventana editable desde Settings)
  useEffect(() => {
    getAppointmentSettings().then(setSettings).catch(() => {
      // silencioso: la página funciona con defaults
    });
  }, []);

  const flash = (kind: "ok" | "err", text: string) => {
    setMessage({ kind, text });
    window.setTimeout(() => setMessage(null), 3500);
  };

  /** Transición de estado (R5) vía PATCH + refresh */
  const quickAction = async (a: Appointment, status: AppointmentStatus, label: string) => {
    setActingId(a.id);
    try {
      await patchAppointment(a.id, { status });
      flash("ok", `Cita de ${a.customer_name} → ${label}`);
      await load();
    } catch (e) {
      flash("err", errText(e));
    } finally {
      setActingId(null);
    }
  };

  const onRemind = async (a: Appointment) => {
    setActingId(a.id);
    try {
      const res = await remindAppointment(a.id);
      flash("ok", res.message ?? `Recordatorio programado para ${a.customer_name}`);
    } catch (e) {
      flash("err", errText(e));
    } finally {
      setActingId(null);
    }
  };

  const sorted = useMemo(
    () => [...items].sort((a, b) => a.starts_at.localeCompare(b.starts_at)),
    [items],
  );

  const counts = useMemo(() => {
    const c: Record<AppointmentStatus, number> = {
      solicitada: 0,
      confirmada: 0,
      cumplida: 0,
      cancelada: 0,
      no_show: 0,
    };
    for (const a of items) c[a.status] += 1;
    return c;
  }, [items]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold text-brand-text-primary">📅 Agenda de Citas</h2>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
        >
          ＋ Nueva cita
        </button>
      </div>

      {message && (
        <div
          className={`rounded-xl border px-4 py-2 text-sm ${
            message.kind === "ok"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* D3: aviso si la agenda está desactivada */}
      {!settings.enabled && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          ⚠️ La agenda de citas está desactivada para este local. Activá el
          horario de reservas en{" "}
          <a href="/config/marca" className="font-medium underline">
            Configuración → Agenda de Citas
          </a>{" "}
          (D3: ventana editable, default 12:00–23:00).
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-gray-200 bg-white p-3">
        <label className="text-xs text-gray-500">
          Fecha
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-gray-500">
          Estado
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "" | AppointmentStatus)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          >
            <option value="">Todos</option>
            {APPOINTMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {APPOINTMENT_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-gray-500">
          Fuente
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as "" | AppointmentSource)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          >
            <option value="">Todas</option>
            {(Object.keys(APPOINTMENT_SOURCE_LABEL) as AppointmentSource[]).map((s) => (
              <option key={s} value={s}>
                {APPOINTMENT_SOURCE_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={load}
          className="rounded-lg bg-brand-primary px-3 py-2 text-sm text-white"
        >
          Filtrar
        </button>
      </div>

      {/* Resumen del día */}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">
          {total} cita(s)
        </span>
        {APPOINTMENT_STATUSES.map((s) => (
          <span key={s} className={`rounded-full px-2.5 py-1 font-medium ${STATUS_BADGE[s]}`}>
            {APPOINTMENT_STATUS_LABEL[s]}: {counts[s]}
          </span>
        ))}
      </div>

      {/* Lista del día */}
      {loading ? (
        <Skeleton className="h-40 w-full" />
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : sorted.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
          Sin citas para {date}. Presioná <b>＋ Nueva cita</b> para reservar una mesa.
        </div>
      ) : (
        <div className="space-y-2">
          {sorted.map((a) => (
            <AppointmentRow
              key={a.id}
              appointment={a}
              busy={actingId === a.id}
              onAction={(status, label) => quickAction(a, status, label)}
              onRemind={() => onRemind(a)}
            />
          ))}
        </div>
      )}

      {showNew && (
        <NewAppointmentModal
          date={date}
          settings={settings}
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false);
            flash("ok", "Cita creada — mesa reservada");
            load();
          }}
        />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Fila de cita
// ═══════════════════════════════════════════════════════════════

function AppointmentRow({
  appointment: a,
  busy,
  onAction,
  onRemind,
}: {
  appointment: Appointment;
  busy: boolean;
  onAction: (status: AppointmentStatus, label: string) => void;
  onRemind: () => void;
}) {
  const remindable = a.status === "solicitada" || a.status === "confirmada";
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {/* Hora */}
        <span className="font-mono text-sm font-semibold text-brand-text-primary">
          {formatAppointmentTime(a.starts_at)}–{formatAppointmentEnd(a.starts_at, a.duration_min)}
        </span>
        {/* Estado */}
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[a.status]}`}>
          {APPOINTMENT_STATUS_LABEL[a.status]}
        </span>
        {/* Fuente (badge patrón F3) */}
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SOURCE_BADGE[a.source]}`}>
          {SOURCE_ICON[a.source]} {APPOINTMENT_SOURCE_LABEL[a.source]}
        </span>
        {/* Mesa */}
        <span className="text-sm text-gray-600">
          🪑 {a.table_number ?? `Mesa #${a.table_id}`}
          {a.section ? <span className="text-gray-400"> · {a.section}</span> : null}
        </span>
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span className="font-medium text-brand-text-primary">{a.customer_name}</span>
        {a.customer_phone && (
          <span className="font-mono text-xs text-gray-500">{a.customer_phone}</span>
        )}
        <span className="text-xs text-gray-500">👥 {a.guests} persona(s)</span>
        {a.call_id && (
          <span className="rounded bg-purple-50 px-1.5 py-0.5 text-[11px] text-purple-700" title={`Llamada ${a.call_id}`}>
            📞 {a.call_id.slice(0, 12)}
          </span>
        )}
      </div>

      {a.notes && <p className="mt-1 text-xs text-gray-500">📝 {a.notes}</p>}

      {/* Acciones rápidas (transiciones R5) */}
      <div className="mt-2 flex flex-wrap gap-2">
        {a.status === "solicitada" && (
          <>
            <ActionButton busy={busy} onClick={() => onAction("confirmada", "Confirmada")} className="bg-brand-primary text-white">
              ✅ Confirmar
            </ActionButton>
            <ActionButton busy={busy} onClick={() => onAction("cancelada", "Cancelada")} className="border border-gray-300 text-gray-700 hover:bg-gray-50">
              ✕ Cancelar
            </ActionButton>
          </>
        )}
        {a.status === "confirmada" && (
          <>
            <ActionButton busy={busy} onClick={() => onAction("cumplida", "Cumplida")} className="bg-green-600 text-white">
              🍽️ Cumplir
            </ActionButton>
            <ActionButton busy={busy} onClick={() => onAction("no_show", "No show")} className="border border-slate-300 text-slate-600 hover:bg-slate-50">
              🚫 No show
            </ActionButton>
            <ActionButton busy={busy} onClick={() => onAction("cancelada", "Cancelada")} className="border border-gray-300 text-gray-700 hover:bg-gray-50">
              ✕ Cancelar
            </ActionButton>
          </>
        )}
        {remindable && (
          <ActionButton busy={busy} onClick={onRemind} className="border border-gray-300 text-gray-700 hover:bg-gray-50">
            🔔 Recordar
          </ActionButton>
        )}
      </div>
    </div>
  );
}

function ActionButton({
  busy,
  onClick,
  className,
  children,
}: {
  busy: boolean;
  onClick: () => void;
  className: string;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className={`rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════
// Modal Nueva cita — selector de mesa con disponibilidad real (D4)
// ═══════════════════════════════════════════════════════════════

function NewAppointmentModal({
  date,
  settings,
  onClose,
  onCreated,
}: {
  date: string;
  settings: AppointmentSettings;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [time, setTime] = useState(settings.hours.open);
  const [duration, setDuration] = useState(settings.duration_min_default);
  const [guests, setGuests] = useState(2);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotError, setSlotError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const to = addMinutesToTime(time, duration);

  // Disponibilidad real: se consulta al cambiar fecha/hora/duración/personas
  useEffect(() => {
    let alive = true;
    if (!time || !to) return;
    setSlotLoading(true);
    setSlotError(null);
    setSelected(null);
    getAvailability({ date, guests, from: time, to })
      .then((s) => {
        if (!alive) return;
        setSlots(s);
        if (s.length === 1) setSelected(s[0].table_id);
      })
      .catch((e) => {
        if (!alive) return;
        setSlotError(errText(e));
        setSlots([]);
      })
      .finally(() => {
        if (alive) setSlotLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [date, time, to, guests]);

  const inWindow = time >= settings.hours.open && to <= settings.hours.close;

  const onSave = async () => {
    if (!name.trim() || selected == null) return;
    setSaving(true);
    setError(null);
    try {
      await createAppointment({
        table_id: selected,
        date,
        time,
        guests,
        customer_name: name.trim(),
        customer_phone: phone.trim() || null,
        notes: notes.trim() || null,
        source: "in_person", // D7: solo staff + voz en F6
      });
      onCreated();
    } catch (e) {
      const err = e instanceof ApiError ? e : null;
      setError(
        err && err.status === 409
          ? "La mesa ya no está disponible en ese horario (doble reserva). Elegí otra mesa u hora."
          : errText(e),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[88vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-bold text-brand-text-primary">＋ Nueva cita</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <p className="mb-3 text-xs text-gray-500">
          Mesa libre con duración (D4) — ventana de reservas{" "}
          <span className="font-mono">{settings.hours.open}–{settings.hours.close}</span> (editable en Configuración, D3).
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-xs text-gray-500">
            Hora *
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-xs text-gray-500">
            Duración (min) *
            <input
              type="number"
              min={15}
              max={240}
              step={15}
              value={duration}
              onChange={(e) => setDuration(Math.max(15, Number(e.target.value) || 60))}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-xs text-gray-500">
            Personas *
            <input
              type="number"
              min={1}
              max={settings.max_guests_per_table}
              value={guests}
              onChange={(e) => setGuests(Math.max(1, Number(e.target.value) || 1))}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-xs text-gray-500">
            Teléfono
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+51 999 999 999"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
        </div>
        <label className="mt-3 block text-xs text-gray-500">
          Nombre del cliente *
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre y apellido"
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="mt-3 block text-xs text-gray-500">
          Notas
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Ocasión, preferencias… (opcional)"
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>

        {/* Ventana de reserva (R3) */}
        {!inWindow && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            ⚠️ {time}–{to} está fuera de la ventana de reservas ({settings.hours.open}–{settings.hours.close}).
            El backend rechazará la cita (422).
          </p>
        )}

        {/* Selector de mesa con disponibilidad real (CA-F6-3) */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500">Mesas libres · {date} {time}–{to}</span>
            {slotLoading && <span className="text-[10px] text-gray-400">consultando…</span>}
          </div>
          {slotError ? (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{slotError}</p>
          ) : slots.length === 0 && !slotLoading ? (
            <p className="rounded-lg border border-dashed border-gray-300 px-3 py-3 text-center text-xs text-gray-400">
              Sin mesas libres en ese horario. Probá otra hora o menos personas.
            </p>
          ) : (
            <div className="max-h-36 space-y-1 overflow-y-auto rounded-lg border border-gray-200 p-2">
              {slots.map((s) => (
                <button
                  key={s.table_id}
                  onClick={() => setSelected(s.table_id)}
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    selected === s.table_id
                      ? "border-brand-primary bg-brand-primary/5 text-brand-text-primary"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  <span className="font-medium">🪑 Mesa {s.table_number}</span>
                  <span className="text-xs text-gray-500">
                    {s.section ?? "Sin sección"} · capacidad {s.capacity}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700"
          >
            Cancelar
          </button>
          <button
            onClick={onSave}
            disabled={saving || !name.trim() || selected == null}
            className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Reservando…" : "Reservar mesa"}
          </button>
        </div>
      </div>
    </div>
  );
}

function errText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
