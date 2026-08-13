/**
 * 📞 Central Telefónica (Spec 05 F2, §3.6) — Panel de llamadas en vivo.
 *
 * - Llamadas en vivo: tarjetas por llamada vía WS /api/v1/calls/ws/{tenant_id}
 *   (call.incoming / answered / ended / recording_ready / converted).
 * - Histórico con filtros (status / dirección / rango) desde GET /api/v1/calls.
 * - Click-to-call: POST /api/v1/calls/originate (CA-F2.8).
 * - Convertir a pedido: modal que reusa el flujo de checkout (zona + items +
 *   pago yape/plin/cash) → POST /api/v1/calls/{id}/convert-to-order (R6/R7).
 * - Grabación: link de escucha/descarga cuando llega recording_path (R1).
 *
 * Regla dura (Spec 05 D3 / F1 R-F1.3): NINGÚN número hardcodeado — los
 * números SIEMPRE vienen del usuario o de la API.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import { authStore } from "@/services/authStore";
import { getZones } from "@/services/deliveryApi";
import { getPublicMenu, PublicMenuItem, PublicZone } from "@/services/publicMenuApi";
import {
  CallRecord,
  CallWsEvent,
  callsWsUrl,
  convertCallToOrder,
  getCalls,
  originateCall,
  recordingHref,
  LIVE_STATUSES,
  CALL_STATUS_LABEL,
  CALL_DIRECTION_LABEL,
} from "@/services/callsApi";

const MENU_SLUG = "el-segoviano";

// ═══════════════════════════════════════════════════════════════
// Página principal
// ═══════════════════════════════════════════════════════════════

export function CallCenterPage() {
  const [tab, setTab] = useState<"live" | "history">("live");
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-brand-text-primary">📞 Central Telefónica</h2>
        <div className="flex flex-wrap gap-2">
          {(
            [
              { id: "live", label: "En vivo" },
              { id: "history", label: "Histórico" },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === t.id
                  ? "bg-brand-primary text-white"
                  : "border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {tab === "live" && <LiveCallsTab />}
      {tab === "history" && <HistoryTab />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// 📡 Llamadas en vivo (WS)
// ═══════════════════════════════════════════════════════════════

function LiveCallsTab() {
  const [calls, setCalls] = useState<Record<string, CallRecord>>({});
  const [wsState, setWsState] = useState<"connecting" | "open" | "closed">("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const [target, setTarget] = useState("");
  const [extension, setExtension] = useState("100");
  const [originating, setOriginating] = useState(false);
  const [convertTarget, setConvertTarget] = useState<CallRecord | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const applyEvent = useCallback((ev: CallWsEvent) => {
    setCalls((prev) => {
      const next = { ...prev };
      const ext = ev.external_call_id;
      if (ev.event === "call.incoming") {
        next[ext] = {
          id: prev[ext]?.id ?? 0,
          external_call_id: ext,
          caller: ev.caller ?? "",
          callee: ev.callee ?? "",
          direction: "inbound",
          status: "ringing",
          started_at: ev.started_at ?? new Date().toISOString(),
          answered_at: null,
          ended_at: null,
          duration: 0,
          recording_path: null,
          converted_order_id: null,
          metadata: null,
        };
      } else if (ev.event === "call.answered") {
        if (next[ext]) {
          next[ext] = { ...next[ext], status: "answered", answered_at: ev.answered_at ?? null };
        }
      } else if (ev.event === "call.ended") {
        if (next[ext]) {
          next[ext] = {
            ...next[ext],
            status: ev.status ?? "completed",
            ended_at: new Date().toISOString(),
            duration: ev.duration ?? 0,
          };
        }
      } else if (ev.event === "call.recording_ready") {
        if (next[ext]) {
          next[ext] = { ...next[ext], recording_path: ev.recording_path ?? null };
        }
      } else if (ev.event === "call.converted") {
        if (next[ext]) {
          next[ext] = {
            ...next[ext],
            converted_order_id: ev.sale_id ?? null,
            metadata: { ...(next[ext].metadata ?? {}), tracking_code: ev.tracking_code },
          };
        }
      }
      return next;
    });
  }, []);

  // WebSocket del tenant (CA-F2.6: solo eventos del propio tenant)
  useEffect(() => {
    const tenantId = authStore.getTenantId();
    if (!tenantId) return;
    setWsState("connecting");
    const ws = new WebSocket(callsWsUrl(tenantId));
    wsRef.current = ws;
    ws.onopen = () => setWsState("open");
    ws.onclose = () => setWsState("closed");
    ws.onerror = () => setWsState("closed");
    ws.onmessage = (raw) => {
      const ev = parseWs(raw.data);
      if (ev) applyEvent(ev);
    };
    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 25000);
    return () => {
      window.clearInterval(ping);
      ws.close();
      wsRef.current = null;
    };
  }, [applyEvent]);

  const live = useMemo(
    () =>
      Object.values(calls)
        .filter((c) => LIVE_STATUSES.includes(c.status as CallRecord["status"]))
        .sort((a, b) => b.started_at.localeCompare(a.started_at)),
    [calls],
  );

  const onOriginate = async () => {
    if (!target.trim()) return;
    setOriginating(true);
    setMessage(null);
    try {
      const res = await originateCall({ target: target.trim(), extension });
      setMessage({ kind: "ok", text: `Llamada saliente en curso (${res.external_call_id})` });
      setTarget("");
    } catch (e) {
      setMessage({ kind: "err", text: errText(e) });
    } finally {
      setOriginating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Click-to-call (CA-F2.8) */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="mb-2 text-sm font-semibold text-brand-text-primary">📲 Click-to-call</h3>
        <div className="flex flex-wrap gap-2">
          <input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="+51 999 999 999"
            className="flex-1 min-w-48 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <select
            value={extension}
            onChange={(e) => setExtension(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="100">Ext. 100</option>
            <option value="101">Ext. 101</option>
            <option value="102">Ext. 102</option>
          </select>
          <button
            onClick={onOriginate}
            disabled={originating || !target.trim()}
            className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {originating ? "Llamando…" : "Llamar"}
          </button>
        </div>
        {message && (
          <p className={`mt-2 text-xs ${message.kind === "ok" ? "text-green-600" : "text-red-600"}`}>
            {message.text}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-400">
          WS: {wsState === "open" ? "🟢 conectado" : wsState === "connecting" ? "🟡 conectando…" : "🔴 desconectado"}
        </p>
      </div>

      {/* Tarjetas en vivo */}
      {live.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
          Sin llamadas en curso — cuando entre una llamada aparecerá aquí en tiempo real.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {live.map((c) => (
            <LiveCallCard key={c.external_call_id} call={c} onConvert={() => setConvertTarget(c)} />
          ))}
        </div>
      )}

      {convertTarget && (
        <ConvertModal
          call={convertTarget}
          onClose={() => setConvertTarget(null)}
          onConverted={(tracking) => {
            setMessage({ kind: "ok", text: `Pedido ${tracking} creado desde la llamada` });
            setConvertTarget(null);
          }}
        />
      )}
    </div>
  );
}

function LiveCallCard({ call, onConvert }: { call: CallRecord; onConvert: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  // Timer continuo desde started_at (duración total de la llamada) — no se
  // "resetea" al pasar de ringing → answered (fix UX 2026-08-13: el salto
  // a 0 al cambiar answered_at se percibía como glitch; la duración de
  // conversación real queda en el detalle/historial).
  useEffect(() => {
    const t = window.setInterval(() => {
      const start = call.started_at;
      setElapsed(Math.max(0, Math.floor((Date.now() - new Date(start).getTime()) / 1000)));
    }, 1000);
    return () => window.clearInterval(t);
  }, [call.started_at]);

  const recording = call.recording_path ? recordingHref(call.recording_path) : null;
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
          </span>
          <span className="text-sm font-semibold text-brand-text-primary">
            {CALL_DIRECTION_LABEL[call.direction]} · {CALL_STATUS_LABEL[call.status as keyof typeof CALL_STATUS_LABEL]}
          </span>
        </span>
        <span className="font-mono text-sm text-gray-600">{fmtDuration(elapsed)}</span>
      </div>
      <div className="mt-2 space-y-1 text-sm">
        <p>
          <span className="text-gray-400">De: </span>
          <span className="font-mono font-medium">{call.caller || "—"}</span>
        </p>
        <p>
          <span className="text-gray-400">Para: </span>
          <span className="font-mono">{call.callee || "—"}</span>
        </p>
      </div>
      {call.converted_order_id != null && (
        <p className="mt-2 rounded bg-green-50 px-2 py-1 text-xs text-green-700">
          ✅ Convertida — {String((call.metadata as Record<string, unknown> | null)?.tracking_code ?? `pedido #${call.converted_order_id}`)}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {/* Fix UX 2026-08-13: el botón debe aparecer en answered (el operador
            contestó y QUIERE convertir) — antes se ocultaba con status==="answered"
            que es justo el flujo principal. Solo se oculta en estados terminales
            (completed/missed/failed) o si ya fue convertida (R6). */}
        {call.status !== "completed" && call.status !== "missed" && call.status !== "failed" && call.converted_order_id == null && (
          <button
            onClick={onConvert}
            className="rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-medium text-white"
          >
            🧾 Convertir a pedido
          </button>
        )}
        {recording && (
          <a
            href={recording}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
          >
            🎙️ Grabación
          </a>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// 🗂️ Histórico con filtros
// ═══════════════════════════════════════════════════════════════

function HistoryTab() {
  const [items, setItems] = useState<CallRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [direction, setDirection] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCalls({
        status: status as CallRecord["status"],
        direction: direction as CallRecord["direction"],
        from: from ? new Date(from).toISOString() : undefined,
        to: to ? new Date(to).toISOString() : undefined,
        limit: 100,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }, [status, direction, from, to]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-gray-200 bg-white p-3">
        <label className="text-xs text-gray-500">
          Estado
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          >
            <option value="">Todos</option>
            {Object.entries(CALL_STATUS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-gray-500">
          Dirección
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          >
            <option value="">Todas</option>
            <option value="inbound">Entrante</option>
            <option value="outbound">Saliente</option>
          </select>
        </label>
        <label className="text-xs text-gray-500">
          Desde
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-gray-500">
          Hasta
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <button
          onClick={load}
          className="rounded-lg bg-brand-primary px-3 py-2 text-sm text-white"
        >
          Filtrar
        </button>
      </div>

      {loading ? (
        <Skeleton className="h-40 w-full" />
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
          Sin llamadas registradas con esos filtros.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Inicio</th>
                <th className="px-3 py-2">Dirección</th>
                <th className="px-3 py-2">Número</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2">Duración</th>
                <th className="px-3 py-2">Conversión</th>
                <th className="px-3 py-2">Grabación</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => {
                const rec = c.recording_path ? recordingHref(c.recording_path) : null;
                return (
                  <tr key={c.id} className="border-b border-gray-100 last:border-0">
                    <td className="px-3 py-2 text-xs text-gray-500">
                      {new Date(c.started_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2">{CALL_DIRECTION_LABEL[c.direction]}</td>
                    <td className="px-3 py-2 font-mono">{c.caller}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          c.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : c.status === "missed" || c.status === "failed"
                              ? "bg-red-100 text-red-700"
                              : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {CALL_STATUS_LABEL[c.status as keyof typeof CALL_STATUS_LABEL]}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{fmtDuration(c.duration)}</td>
                    <td className="px-3 py-2 text-xs">
                      {c.converted_order_id != null
                        ? `DLV #${c.converted_order_id}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {rec ? (
                        <a href={rec} target="_blank" rel="noreferrer" className="text-xs text-brand-primary underline">
                          🎙️ Escuchar
                        </a>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="border-t border-gray-100 px-3 py-2 text-xs text-gray-400">
            {total} llamada(s)
          </p>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// 🧾 Modal convertir llamada → pedido (R6/R7)
// ═══════════════════════════════════════════════════════════════

function ConvertModal({
  call,
  onClose,
  onConverted,
}: {
  call: CallRecord;
  onClose: () => void;
  onConverted: (tracking: string) => void;
}) {
  const [menu, setMenu] = useState<PublicMenuItem[]>([]);
  const [zones, setZones] = useState<PublicZone[]>([]);
  const [zoneId, setZoneId] = useState<number | "">("");
  const [cart, setCart] = useState<Record<number, number>>({});
  const [customerName, setCustomerName] = useState("");
  const [customerAddress, setCustomerAddress] = useState("");
  const [payment, setPayment] = useState<"yape" | "plin" | "cash">("yape");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [m, z] = await Promise.all([
          getPublicMenu(MENU_SLUG).catch(() => null),
          getZones().catch(() => [] as unknown as PublicZone[]),
        ]);
        setMenu(m?.sections.flatMap((s) => s.items) ?? []);
        setZones(z as PublicZone[]);
      } catch {
        // silencioso: los selectores quedarán vacíos y el usuario puede reintentar
      }
    })();
  }, []);

  const lineItems = Object.entries(cart)
    .filter(([, q]) => (q ?? 0) > 0)
    .map(([id, q]) => ({ menu_item_id: Number(id), quantity: q as number, modifiers: [] }));

  const onSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await convertCallToOrder(call.id, {
        zone_id: Number(zoneId),
        items: lineItems,
        customer: {
          name: customerName || undefined,
          phone: call.caller || undefined,
          address: customerAddress || "",
        },
        payment: { method: payment },
        notes: notes || undefined,
      });
      onConverted(res.tracking_code);
    } catch (e) {
      setError(errText(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-bold text-brand-text-primary">
            🧾 Convertir llamada a pedido
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <p className="mb-4 text-xs text-gray-500">
          Cliente desde la llamada: <span className="font-mono">{call.caller}</span>
        </p>

        {/* Zona (R7: selección explícita; la sugerencia por distrito la hace el backend) */}
        <label className="mb-3 block text-xs text-gray-500">
          Zona de delivery *
          <select
            value={zoneId}
            onChange={(e) => setZoneId(e.target.value ? Number(e.target.value) : "")}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">— Seleccionar zona —</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name} (S/ {z.fee} · {z.eta_min} min)
              </option>
            ))}
          </select>
        </label>

        {/* Items del menú */}
        <label className="mb-3 block text-xs text-gray-500">
          Items del pedido
        </label>
        <div className="mb-3 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-gray-200 p-2">
          {menu.length === 0 && (
            <p className="text-xs text-gray-400">Cargando menú…</p>
          )}
          {menu.map((it) => (
            <div key={it.id} className="flex items-center justify-between text-sm">
              <span className="truncate">{it.name} — S/ {it.price.toFixed(2)}</span>
              <input
                type="number"
                min={0}
                value={cart[it.id] ?? 0}
                onChange={(e) =>
                  setCart((prev) => ({ ...prev, [it.id]: Math.max(0, Number(e.target.value) || 0) }))
                }
                className="w-16 rounded border border-gray-300 px-2 py-1 text-right text-xs"
              />
            </div>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-xs text-gray-500">
            Cliente
            <input
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="Nombre (opcional)"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-xs text-gray-500">
            Dirección
            <input
              value={customerAddress}
              onChange={(e) => setCustomerAddress(e.target.value)}
              placeholder="Av. … (opcional, para sugerir zona)"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block text-xs text-gray-500">
            Pago
            <select
              value={payment}
              onChange={(e) => setPayment(e.target.value as typeof payment)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="yape">Yape</option>
              <option value="plin">Plin</option>
              <option value="cash">Efectivo</option>
            </select>
          </label>
          <label className="block text-xs text-gray-500">
            Notas
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notas del pedido (opcional)"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
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
            disabled={saving || lineItems.length === 0 || zoneId === ""}
            className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Creando pedido…" : "Crear pedido (DLV-)"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function parseWs(raw: unknown): CallWsEvent | null {
  try {
    const obj = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (obj && typeof obj === "object" && "event" in obj) {
      return obj as CallWsEvent;
    }
    return null;
  } catch {
    return null;
  }
}

function fmtDuration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds || 0));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function errText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
