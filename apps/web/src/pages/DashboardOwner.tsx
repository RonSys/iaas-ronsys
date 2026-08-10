/**
 * DashboardOwner — Panel de Indicadores para el Dueño (Spec 04, V1).
 *
 * Vista ejecutiva de solo lectura: KPIs del día, ventas por hora/día,
 * canales (salón/takeaway/delivery), top 10 platos, métodos de pago,
 * delivery (zonas, embudo, SLA, GMV) y ROAS por campaña.
 *
 * Data: GET /api/v1/dashboard/owner?date_from=&date_to=
 * Contrato: docs/specs/04-panel-indicadores/spec-panel-dueño.md §3.1
 *
 * @page DashboardOwner
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { KPICard, SectionHeader, Skeleton, fmtCurrency, fmtPct } from "@/components/dashboard/KPICard";
import { getOwnerDashboard } from "@/services/dashboardApi";
import type { OwnerDashboardResponse, OwnerDashboardParams } from "@/types";

// ─── Helpers de fecha (America/Lima) ────────────────────────
function todayISO(): string {
  // Fecha local YYYY-MM-DD (el navegador del usuario está en Lima)
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ─── Rango rápido ───────────────────────────────────────────
const RANGES = [
  { key: "today", label: "Hoy", from: () => todayISO(), to: () => todayISO() },
  { key: "7d", label: "7 días", from: () => daysAgoISO(6), to: () => todayISO() },
  { key: "30d", label: "30 días", from: () => daysAgoISO(29), to: () => todayISO() },
];

const WEEKDAY_NAMES = ["", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const HOUR_LABELS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);

const CHANNEL_COLORS: Record<string, string> = {
  dine_in: "#3b82f6",
  takeout: "#f59e0b",
  delivery: "#10b981",
};

const PAYMENT_COLORS = ["#6366f1", "#ec4899", "#10b981", "#8b5cf6", "#f59e0b"];

export function DashboardOwner() {
  const [data, setData] = useState<OwnerDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<OwnerDashboardParams>({
    date_from: daysAgoISO(6),
    date_to: todayISO(),
  });

  const load = useCallback(async (params: OwnerDashboardParams) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getOwnerDashboard(params);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar el panel");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(range);
  }, [load, range]);

  // ─── Datos derivados para gráficos ───────────────────────
  const hourly = useMemo(() => {
    if (!data) return [];
    return Array.from({ length: 24 }, (_, hour) => {
      const found = data.sales_by_hour.find((s) => s.hour === hour);
      return {
        hour: HOUR_LABELS[hour],
        Salón: found?.dine_in ?? 0,
        Delivery: found?.delivery ?? 0,
      };
    });
  }, [data]);

  const weekday = useMemo(() => {
    if (!data) return [];
    return data.sales_by_weekday.map((s) => ({
      day: WEEKDAY_NAMES[s.weekday] ?? `D${s.weekday}`,
      Ventas: s.total,
    }));
  }, [data]);

  const channelPie = useMemo(() => {
    if (!data) return [];
    return [
      { name: "Salón", value: data.channels.dine_in, color: CHANNEL_COLORS.dine_in },
      { name: "Para llevar", value: data.channels.takeout, color: CHANNEL_COLORS.takeout },
      { name: "Delivery", value: data.channels.delivery, color: CHANNEL_COLORS.delivery },
    ].filter((c) => c.value > 0);
  }, [data]);

  const paymentsPie = useMemo(() => {
    if (!data) return [];
    const labels: Record<string, string> = {
      yape: "Yape",
      plin: "Plin",
      cash: "Efectivo",
      card: "Tarjeta",
      transfer: "Transferencia",
    };
    return Object.entries(data.payments)
      .filter(([, v]) => (v as number) > 0)
      .map(([k, v], i) => ({
        name: labels[k] ?? k,
        value: v as number,
        color: PAYMENT_COLORS[i % PAYMENT_COLORS.length],
      }));
  }, [data]);

  const funnel = useMemo(() => {
    if (!data) return [];
    const f = data.delivery.funnel;
    return [
      { stage: "Recibido", value: f.received },
      { stage: "En cocina", value: f.preparing },
      { stage: "Listo", value: f.ready },
      { stage: "En ruta", value: f.out_for_delivery },
      { stage: "Entregado", value: f.delivered },
      { stage: "Cancelado", value: f.cancelled },
    ];
  }, [data]);

  const kpis = data?.kpis;

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader title="Panel del Dueño" icon="📊">
        <div className="flex items-center gap-1">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() =>
                setRange({ date_from: r.from(), date_to: r.to() })
              }
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                range.date_from === r.from()
                  ? "bg-brand-primary text-white"
                  : "btn-ghost"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </SectionHeader>

      {error && (
        <div className="card border-red-500/40 bg-red-500/5 text-red-300 p-4 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* ─── KPIs ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {loading || !kpis
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card space-y-2">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-7 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            ))
          : (
              <>
                <KPICard title="Ventas" value={fmtCurrency(kpis.sales_total)} icon="💰" subtitle={kpis.orders_count ? `${kpis.orders_count} pedidos` : "sin pedidos"} />
                <KPICard title="Ticket promedio" value={fmtCurrency(kpis.avg_ticket)} icon="🎫" />
                <KPICard title="Delivery" value={fmtPct(kpis.delivery_pct / 100)} icon="🛵" subtitle={`${kpis.orders_delivery} pedidos`} />
                <KPICard title="Salón" value={`${kpis.orders_dine_in} pedidos`} icon="🍽️" subtitle="dine-in" />
                <KPICard title="Cocina en vivo" value={String(kpis.kitchen_open)} icon="👨‍🍳" subtitle="pedidos activos" />
                <KPICard title="En ruta" value={String(kpis.delivery_in_route)} icon="🏍️" subtitle="delivery activo" />
              </>
            )}
      </div>

      {/* ─── Fila 2: ventas por hora + por día ─────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Ventas por hora — Salón vs Delivery</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={hourly} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={3} stroke="#64748b" />
              <YAxis tick={{ fontSize: 10 }} stroke="#64748b" />
              <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey="Salón" stroke={CHANNEL_COLORS.dine_in} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Delivery" stroke={CHANNEL_COLORS.delivery} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Ventas por día de la semana</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={weekday} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="#64748b" />
              <YAxis tick={{ fontSize: 10 }} stroke="#64748b" />
              <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
              <Bar dataKey="Ventas" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ─── Fila 3: canales + top platos + pagos ──────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Canales de venta</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={channelPie} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                {channelPie.map((c, i) => (
                  <Cell key={i} fill={c.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Top platos vendidos</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={data?.top_platos ?? []}
              layout="vertical"
              margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} stroke="#64748b" />
              <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 10 }} stroke="#64748b" />
              <Tooltip formatter={(v) => `${v} unds`} />
              <Bar dataKey="qty" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Métodos de pago</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={paymentsPie} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                {paymentsPie.map((c, i) => (
                  <Cell key={i} fill={c.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ─── Fila 4: delivery — zonas + embudo + ROAS ──────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Pedidos por zona</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data?.delivery.orders_by_zone ?? []} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
              <XAxis dataKey="zone" tick={{ fontSize: 10 }} stroke="#64748b" />
              <YAxis tick={{ fontSize: 10 }} stroke="#64748b" allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="orders" name="Pedidos" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">Embudo de pedidos delivery</h3>
          <div className="space-y-1.5">
            {funnel.map((f) => (
              <div key={f.stage} className="flex items-center gap-2">
                <span className="w-24 text-xs text-slate-400">{f.stage}</span>
                <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all"
                    style={{
                      width: `${funnel[0]?.value ? (f.value / funnel[0].value) * 100 : 0}%`,
                      minWidth: f.value > 0 ? "6px" : 0,
                    }}
                  />
                </div>
                <span className="w-8 text-right text-xs font-semibold">{f.value}</span>
              </div>
            ))}
            {data && (
              <div className="pt-2 text-xs text-slate-400 flex justify-between">
                <span>⏱️ Promedio entrega: {data.delivery.avg_delivery_min != null ? `${data.delivery.avg_delivery_min} min` : "—"}</span>
                <span>💵 Fee total: {fmtCurrency(data.delivery.fee_total)}</span>
              </div>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">ROAS por campaña (marketing)</h3>
          {data && data.campaigns.length === 0 ? (
            <p className="text-xs text-slate-400">Sin campañas en el período.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data?.campaigns ?? []} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
                <XAxis dataKey="name" tick={{ fontSize: 9 }} stroke="#64748b" interval={0} angle={-15} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} stroke="#64748b" />
                <Tooltip formatter={(v) => `S/ ${Number(v).toFixed(2)}`} />
                <Bar dataKey="roas" name="ROAS" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ─── GMV delivery ──────────────────────────────────── */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <KPICard title="GMV delivery (entregados)" value={fmtCurrency(data.delivery.gmv)} icon="🛵" subtitle="total ventas canal" />
          <KPICard title="Pedidos delivery" value={String(data.kpis.orders_delivery)} icon="📦" subtitle={`${data.delivery.orders_by_zone.length} zona(s) activa(s)`} />
        </div>
      )}
    </div>
  );
}
