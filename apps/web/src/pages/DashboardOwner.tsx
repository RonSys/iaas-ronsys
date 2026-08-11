/**
 * DashboardOwner — Panel de Indicadores para el Dueño (Spec 04, V1 + V2).
 *
 * Vista ejecutiva de solo lectura: KPIs del día con comparativa ▲▼ (CA12),
 * alertas de desviación (CA14), heatmaps hora×día por canal con CSS grid
 * coloreado (CA10), márgenes por canal con costeo (CA11), ventas por hora/día,
 * canales, top platos, pagos, delivery y ROAS por campaña. Dropdown de
 * descarga CSV/PDF del período (CA13 + CA13-b).
 *
 * Data: GET /api/v1/dashboard/owner?date_from=&date_to=
 * Export: GET /api/v1/dashboard/owner/export?format=csv|pdf&date_from=&date_to=
 * Contrato: docs/specs/04-panel-indicadores/spec-panel-dueño.md §3.1 + §3.1-V2
 *
 * @page DashboardOwner
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
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
import { exportOwnerDashboardCsv, exportOwnerDashboardPdf, getOwnerDashboard } from "@/services/dashboardApi";
import type {
  AlertItem,
  ComparisonDeltas,
  HeatmapChannel,
  MarginsData,
  OwnerDashboardResponse,
  OwnerDashboardParams,
} from "@/types";

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

const CHANNEL_LABELS: Record<string, string> = {
  dine_in: "Salón",
  takeout: "Para llevar",
  delivery: "Delivery",
};

const PAYMENT_COLORS = ["#6366f1", "#ec4899", "#10b981", "#8b5cf6", "#f59e0b"];

// ─── V2: Indicador de delta ▲▼ (CA12) ───────────────────────
/**
 * Flecha ▲ verde si el delta es positivo, ▼ roja si es negativo, junto al
 * valor. `suffix` distingue % (deltas relativos) de " pts" (delivery_pct_delta,
 * que llega en puntos porcentuales). Si delta es null → sin indicador.
 */
function DeltaChip({ delta, suffix = "%" }: { delta: number | null | undefined; suffix?: string }) {
  if (delta == null || Number.isNaN(delta)) return null;
  const positive = delta > 0;
  const zero = delta === 0;
  const cls = zero ? "text-slate-400" : positive ? "text-emerald-400" : "text-red-400";
  const arrow = zero ? "→" : positive ? "▲" : "▼";
  const sign = positive ? "+" : "";
  return (
    <span className={`text-xs font-semibold ${cls}`} title="vs período anterior (CA12)">
      {arrow} {sign}{delta.toFixed(1)}{suffix}
    </span>
  );
}

/** KPI con indicador de comparativa semana vs semana (CA12). */
function KpiWithDelta({
  title,
  value,
  icon,
  subtitle,
  delta,
  deltaSuffix = "%",
}: {
  title: string;
  value: string;
  icon?: string;
  subtitle?: string;
  delta?: number | null;
  deltaSuffix?: string;
}) {
  return (
    <div className="card animate-fade-in">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-brand-text-secondary">
          {title}
        </span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-brand-text-primary">{value}</div>
      <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
        <DeltaChip delta={delta} suffix={deltaSuffix} />
        {subtitle && <span className="text-xs text-brand-text-secondary">{subtitle}</span>}
      </div>
    </div>
  );
}

// ─── V2: Banner de alertas (CA14) ───────────────────────────
/** Lista de alertas de desviación; rojo/ámbar según severidad. Vacío → nada. */
function AlertsBanner({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts || alerts.length === 0) return null;
  return (
    <div className="space-y-2">
      {alerts.map((a, i) => {
        const isRed = a.severity === "red";
        return (
          <div
            key={`${a.metric}-${i}`}
            className={`card flex items-center gap-2 p-3 text-sm ${
              isRed
                ? "border-red-500/40 bg-red-500/10 text-red-300"
                : "border-yellow-500/40 bg-yellow-500/10 text-yellow-300"
            }`}
          >
            <span className="text-base">⚠️</span>
            <span className="font-medium">{a.message}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── V2: Heatmap hora×día con CSS grid coloreado (CA10, R4) ──
const HEATMAP_ACCENTS: Record<string, string> = { dine_in: "#3b82f6", delivery: "#10b981" };

/** Fila del grid: etiqueta de hora + 7 celdas (Lun..Dom). */
function HeatmapHourRow({
  hour,
  totalsByWeekday,
  max,
  accent,
}: {
  hour: number;
  totalsByWeekday: Map<number, number> | undefined;
  max: number;
  accent: string;
}) {
  return (
    <>
      <div className="text-right text-[10px] text-slate-500 pr-1 leading-4">
        {String(hour).padStart(2, "0")}
      </div>
      {Array.from({ length: 7 }, (_, i) => {
        const weekday = i + 1;
        const total = totalsByWeekday?.get(weekday) ?? 0;
        // Intensidad relativa al máximo del canal; celdas vacías casi transparentes
        const opacity = total > 0 ? 0.18 + (max > 0 ? total / max : 0) * 0.82 : 0.04;
        return (
          <div
            key={weekday}
            title={`${WEEKDAY_NAMES[weekday]} ${String(hour).padStart(2, "0")}:00 — ${fmtCurrency(total)}`}
            className="h-4 rounded-sm"
            style={{ backgroundColor: accent, opacity }}
          />
        );
      })}
    </>
  );
}

/** Heatmap completo de un canal: 7 columnas (Lun..Dom) × 24 filas (hora). */
function HeatmapGrid({
  title,
  channel,
  accent,
}: {
  title: string;
  channel: HeatmapChannel;
  accent: string;
}) {
  const max = useMemo(
    () => Math.max(...channel.rows.map((r) => r.total), 0),
    [channel],
  );
  const byHour = useMemo(() => {
    const map = new Map<number, Map<number, number>>();
    for (const r of channel.rows) {
      let col = map.get(r.hour);
      if (!col) {
        col = new Map<number, number>();
        map.set(r.hour, col);
      }
      col.set(r.weekday, r.total);
    }
    return map;
  }, [channel]);

  return (
    <div className="card p-4">
      <h3 className="font-semibold text-sm mb-3">{title}</h3>
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[480px]"
          style={{ gridTemplateColumns: "2.5rem repeat(7, minmax(0, 1fr))", gap: "2px" }}
        >
          <div />
          {WEEKDAY_NAMES.slice(1).map((d) => (
            <div key={d} className="text-center text-[10px] font-semibold text-slate-400">
              {d}
            </div>
          ))}
          {Array.from({ length: 24 }, (_, h) => (
            <HeatmapHourRow key={h} hour={h} totalsByWeekday={byHour.get(h)} max={max} accent={accent} />
          ))}
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-400">
        <span>Bajo</span>
        <div
          className="h-2 flex-1 rounded"
          style={{ background: `linear-gradient(to right, ${accent}14, ${accent})` }}
        />
        <span>Alto</span>
      </div>
    </div>
  );
}

// ─── V2: Márgenes por canal (CA11) ──────────────────────────
function marginColor(pct: number): string {
  if (pct >= 50) return "bg-emerald-500";
  if (pct >= 30) return "bg-amber-500";
  return "bg-red-500";
}

function marginTextColor(pct: number): string {
  if (pct >= 50) return "text-emerald-400";
  if (pct >= 30) return "text-amber-400";
  return "text-red-400";
}

/** Tarjetas de margen por canal con barra de progreso + nota de costeabilidad (R2). */
function MarginsCards({ margins }: { margins: MarginsData }) {
  return (
    <div className="card p-4">
      <h3 className="font-semibold text-sm mb-3">Margen por canal (costeo por recetas)</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {margins.by_channel.map((m) => (
          <div key={m.channel} className="rounded-lg bg-white/5 p-3 border border-white/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {CHANNEL_LABELS[m.channel] ?? m.channel}
              </span>
              <span className={`text-lg font-bold ${marginTextColor(m.margin_pct)}`}>
                {m.margin_pct.toFixed(1)}%
              </span>
            </div>
            <div className="mt-2 h-2 bg-white/10 rounded overflow-hidden">
              <div
                className={`h-full ${marginColor(m.margin_pct)}`}
                style={{ width: `${Math.max(0, Math.min(m.margin_pct, 100))}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-slate-400 space-y-0.5">
              <div className="flex justify-between">
                <span>Ingresos</span>
                <span>{fmtCurrency(m.revenue)}</span>
              </div>
              <div className="flex justify-between">
                <span>Costo</span>
                <span>{fmtCurrency(m.cost)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-500">{margins.costable_note}</p>
    </div>
  );
}

// ─── Página ─────────────────────────────────────────────────
export function DashboardOwner() {
  const [data, setData] = useState<OwnerDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
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

  // ─── CA13 + CA13-b: Descarga CSV/PDF del período seleccionado ─
  const downloadExport = useCallback(async (format: "csv" | "pdf") => {
    setExporting(true);
    try {
      const exporter =
        format === "pdf" ? exportOwnerDashboardPdf : exportOwnerDashboardCsv;
      const { blob, filename } = await exporter({
        date_from: range.date_from,
        date_to: range.date_to,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Filename del header Content-Disposition (RFC 5987, con ñ) si existe
      a.download = filename ?? `panel_dueño_${range.date_to ?? todayISO()}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al descargar el reporte");
    } finally {
      setExporting(false);
    }
  }, [range]);

  /** Cierra el menú <details> tras elegir una opción */
  const closeExportMenu = (e: ReactMouseEvent<HTMLElement>) => {
    const details = e.currentTarget.closest("details");
    if (details) details.removeAttribute("open");
  };

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
  const deltas: ComparisonDeltas | undefined = data?.comparison?.deltas;

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader title="Panel del Dueño" icon="📊">
        <div className="flex items-center gap-1 flex-wrap">
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
          {/* CA13-b: dropdown Descargar CSV / Descargar PDF */}
          <details className="relative ml-1 group">
            <summary
              role="button"
              aria-disabled={exporting || loading || !data}
              className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-brand-primary/10 border border-brand-primary/30 text-brand-primary hover:bg-brand-primary/20 transition-colors list-none [&::-webkit-details-marker]:hidden cursor-pointer select-none ${
                exporting || loading || !data
                  ? "opacity-50 pointer-events-none"
                  : ""
              }`}
              title="Descargar reporte del período (CSV o PDF) — CA13-b"
            >
              {exporting ? "⏳ Generando…" : "⬇️ Descargar"}
              <span className="text-[9px] opacity-70" aria-hidden>
                ▾
              </span>
            </summary>
            <div className="absolute right-0 top-full mt-1 z-20 w-44 overflow-hidden rounded-lg border border-slate-700 bg-slate-800 shadow-xl">
              <button
                type="button"
                onClick={(e) => {
                  closeExportMenu(e);
                  void downloadExport("csv");
                }}
                disabled={exporting || loading || !data}
                className="flex w-full items-center gap-2 px-3 py-2 text-xs text-slate-100 hover:bg-brand-primary/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ⬇️ Descargar CSV
              </button>
              <button
                type="button"
                onClick={(e) => {
                  closeExportMenu(e);
                  void downloadExport("pdf");
                }}
                disabled={exporting || loading || !data}
                className="flex w-full items-center gap-2 px-3 py-2 text-xs text-slate-100 hover:bg-brand-primary/20 transition-colors border-t border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ⬇️ Descargar PDF
              </button>
            </div>
          </details>
        </div>
      </SectionHeader>

      {error && (
        <div className="card border-red-500/40 bg-red-500/5 text-red-300 p-4 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* ─── V2: Alertas de desviación (CA14) ─────────────── */}
      {data && <AlertsBanner alerts={data.alerts} />}

      {/* ─── KPIs (con comparativa ▲▼, CA12) ──────────────── */}
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
                <KpiWithDelta
                  title="Ventas"
                  value={fmtCurrency(kpis.sales_total)}
                  icon="💰"
                  subtitle={kpis.orders_count ? `${kpis.orders_count} pedidos` : "sin pedidos"}
                  delta={deltas?.sales_total_pct}
                />
                <KpiWithDelta
                  title="Ticket promedio"
                  value={fmtCurrency(kpis.avg_ticket)}
                  icon="🎫"
                  delta={deltas?.avg_ticket_pct}
                />
                <KpiWithDelta
                  title="Delivery"
                  value={fmtPct(kpis.delivery_pct / 100)}
                  icon="🛵"
                  subtitle={`${kpis.orders_delivery} pedidos`}
                  delta={deltas?.delivery_pct_delta}
                  deltaSuffix=" pts"
                />
                <KPICard title="Salón" value={`${kpis.orders_dine_in} pedidos`} icon="🍽️" subtitle="dine-in" />
                <KPICard title="Cocina en vivo" value={String(kpis.kitchen_open)} icon="👨‍🍳" subtitle="pedidos activos" />
                <KPICard title="En ruta" value={String(kpis.delivery_in_route)} icon="🏍️" subtitle="delivery activo" />
              </>
            )}
      </div>

      {/* ─── V2: Heatmaps de demanda hora×día (CA10, R4) ──── */}
      {data && data.heatmap && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <HeatmapGrid
            title="Heatmap de demanda — Salón"
            channel={data.heatmap.dine_in}
            accent={HEATMAP_ACCENTS.dine_in}
          />
          <HeatmapGrid
            title="Heatmap de demanda — Delivery"
            channel={data.heatmap.delivery}
            accent={HEATMAP_ACCENTS.delivery}
          />
        </div>
      )}

      {/* ─── V2: Márgenes por canal (CA11) ────────────────── */}
      {data && data.margins && <MarginsCards margins={data.margins} />}

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
