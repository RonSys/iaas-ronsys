/**
 * Gráficos de flujo de caja con Recharts + selectores de período/vista.
 *
 * HU-F1-007: UI de Flujo de Caja con selector de período/vista
 *
 * Componentes:
 * - CashflowChart: componente principal con selectores y gráfico
 * - CashflowBarChart: barras de ingresos vs egresos mensuales (proyectado/real)
 * - CashflowComparisonChart: barras lado a lado (proyectado vs real) para comparativa
 * - CashflowAlerts: banner de alertas para vista comparativa
 * - CashflowSkeleton: skeleton loader
 * - generateCashflowData: helper para datos locales
 *
 * @module dashboard/CashflowChart
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { fmtCurrency, Skeleton } from "./KPICard";
import { AlertsBanner } from "../ui/AlertsBanner";
import type { CashflowResponse } from "@/types";

// ─── Helpers ─────────────────────────────────────────────

const MONTH_NAMES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

const MONTHS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: MONTH_NAMES[i],
}));

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - 2 + i);

// ─── Data types for charts ───────────────────────────────

export interface CashflowDataPoint {
  month: string;
  ingresos: number;
  egresos: number;
  saldo: number;
  acumulado: number;
}

export interface CashflowComparisonPoint {
  month: string;
  proyectado: number;
  real: number;
  diferencia?: number;
}

// ─── Chart sub-components ────────────────────────────────

function CashflowBarChartInner({
  data,
  title,
}: {
  data: CashflowDataPoint[];
  title?: string;
}) {
  return (
    <div className="w-full">
      {title && (
        <h3 className="font-bold text-brand-text-primary mb-3">{title}</h3>
      )}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#718096" }} />
            <YAxis
              tick={{ fontSize: 11, fill: "#718096" }}
              tickFormatter={(v: number) =>
                v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString()
              }
            />
            <Tooltip
              formatter={(value: number) => [fmtCurrency(value), ""]}
              contentStyle={{
                borderRadius: "0.5rem",
                border: "1px solid #e5e7eb",
                fontSize: "0.8rem",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
            <Bar
              dataKey="ingresos"
              name="Ingresos"
              fill="var(--color-success)"
              radius={[4, 4, 0, 0]}
            />
            <Bar
              dataKey="egresos"
              name="Egresos"
              fill="var(--color-error)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CashflowComparisonChartInner({
  data,
  title,
}: {
  data: CashflowComparisonPoint[];
  title?: string;
}) {
  return (
    <div className="w-full">
      {title && (
        <h3 className="font-bold text-brand-text-primary mb-3">{title}</h3>
      )}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#718096" }} />
            <YAxis
              tick={{ fontSize: 11, fill: "#718096" }}
              tickFormatter={(v: number) =>
                v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString()
              }
            />
            <Tooltip
              formatter={(value: number) => [fmtCurrency(value), ""]}
              contentStyle={{
                borderRadius: "0.5rem",
                border: "1px solid #e5e7eb",
                fontSize: "0.8rem",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
            <Bar
              dataKey="proyectado"
              name="Proyectado"
              fill="var(--color-primary)"
              radius={[4, 4, 0, 0]}
            />
            <Bar
              dataKey="real"
              name="Real"
              fill="var(--color-accent)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CashflowLineChartInner({
  data,
  title,
}: {
  data: CashflowDataPoint[];
  title?: string;
}) {
  return (
    <div className="w-full">
      {title && (
        <h3 className="font-bold text-brand-text-primary mb-3">{title}</h3>
      )}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#718096" }} />
            <YAxis
              tick={{ fontSize: 11, fill: "#718096" }}
              tickFormatter={(v: number) =>
                v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString()
              }
            />
            <Tooltip
              formatter={(value: number) => [fmtCurrency(value), ""]}
              contentStyle={{
                borderRadius: "0.5rem",
                border: "1px solid #e5e7eb",
                fontSize: "0.8rem",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
            <Line
              type="monotone"
              dataKey="acumulado"
              name="Flujo Acumulado"
              stroke="var(--color-primary)"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "var(--color-primary)" }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="saldo"
              name="Saldo Mensual"
              stroke="var(--color-secondary)"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={{ r: 2, fill: "var(--color-secondary)" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Alerts (via ui/AlertsBanner) ───────────────────────

// ─── Skeleton ────────────────────────────────────────────

function CashflowSkeleton() {
  return (
    <div className="w-full space-y-4 animate-pulse">
      <div className="flex gap-4">
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-40" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

// ─── Selectors ───────────────────────────────────────────

interface CashflowSelectorsProps {
  view: string;
  fromYear: number;
  fromMonth: number;
  toYear: number;
  toMonth: number;
  onViewChange: (view: string) => void;
  onPeriodChange: (fromYear: number, fromMonth: number, toYear: number, toMonth: number) => void;
  periodValid: boolean;
  onConsult: () => void;
  loading: boolean;
}

function CashflowSelectors({
  view,
  fromYear,
  fromMonth,
  toYear,
  toMonth,
  onViewChange,
  onPeriodChange,
  periodValid,
  onConsult,
  loading,
}: CashflowSelectorsProps) {
  const views = [
    { value: "projected", label: "Proyectado" },
    { value: "actual", label: "Real" },
    { value: "comparison", label: "Comparativa" },
  ];

  return (
    <div className="flex flex-wrap items-end gap-3 mb-4">
      {/* Vista */}
      <div>
        <label htmlFor="cf-view" className="block text-xs font-medium text-brand-text-secondary mb-1">
          Vista
        </label>
        <select
          id="cf-view"
          value={view}
          onChange={(e) => onViewChange(e.target.value)}
          disabled={loading}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 bg-white
            text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20
            disabled:opacity-50"
        >
          {views.map((v) => (
            <option key={v.value} value={v.value}>
              {v.label}
            </option>
          ))}
        </select>
      </div>

      {/* Desde */}
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Desde
        </label>
        <div className="flex gap-1">
          <select
            value={fromYear}
            onChange={(e) =>
              onPeriodChange(Number(e.target.value), fromMonth, toYear, toMonth)
            }
            disabled={loading}
            className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 bg-white
              text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <select
            value={fromMonth}
            onChange={(e) =>
              onPeriodChange(fromYear, Number(e.target.value), toYear, toMonth)
            }
            disabled={loading}
            className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 bg-white
              text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          >
            {MONTHS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Hasta */}
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Hasta
        </label>
        <div className="flex gap-1">
          <select
            value={toYear}
            onChange={(e) =>
              onPeriodChange(fromYear, fromMonth, Number(e.target.value), toMonth)
            }
            disabled={loading}
            className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 bg-white
              text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <select
            value={toMonth}
            onChange={(e) =>
              onPeriodChange(fromYear, fromMonth, toYear, Number(e.target.value))
            }
            disabled={loading}
            className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 bg-white
              text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          >
            {MONTHS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className="self-center ml-2">
          <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Consultar button + validation */}
      <div className="self-end ml-2">
        <button
          type="button"
          onClick={onConsult}
          disabled={!periodValid || loading}
          className="px-4 py-1.5 text-sm rounded-lg font-medium transition-all
            bg-brand-primary text-white hover:bg-brand-secondary
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Cargando..." : "🔍 Consultar"}
        </button>
      </div>

      {!periodValid && (
        <div className="w-full mt-1">
          <p className="text-xs text-brand-error">
            ⚠️ La fecha "Desde" debe ser menor o igual a "Hasta"
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Summary ─────────────────────────────────────────────

function CashflowSummary({
  response,
}: {
  response: CashflowResponse;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      <div className="card">
        <div className="text-xs text-brand-text-secondary uppercase tracking-wider">
          Saldo Inicial
        </div>
        <div className="text-lg font-bold text-brand-text-primary">
          {fmtCurrency(response.opening_balance)}
        </div>
      </div>
      <div className="card">
        <div className="text-xs text-brand-text-secondary uppercase tracking-wider">
          Flujo Neto
        </div>
        <div
          className={`text-lg font-bold ${response.net_cashflow >= 0 ? "text-brand-success" : "text-brand-error"}`}
        >
          {fmtCurrency(response.net_cashflow)}
        </div>
      </div>
      <div className="card">
        <div className="text-xs text-brand-text-secondary uppercase tracking-wider">
          Saldo Final
        </div>
        <div className="text-lg font-bold text-brand-text-primary">
          {fmtCurrency(response.closing_balance)}
        </div>
      </div>
      <div className="card">
        <div className="text-xs text-brand-text-secondary uppercase tracking-wider">
          Período
        </div>
        <div className="text-sm font-bold text-brand-text-primary">
          {response.from_date} → {response.to_date}
        </div>
      </div>
    </div>
  );
}

// ─── Data Transformers ───────────────────────────────────

function responseToBarData(response: CashflowResponse): CashflowDataPoint[] {
  let acumulado = response.opening_balance;
  const monthly: Record<number, { ingresos: number; egresos: number }> = {};

  for (const line of response.lines) {
    const m = line.month;
    if (!monthly[m]) monthly[m] = { ingresos: 0, egresos: 0 };
    // For comparison view, use projected as default bar display
    const value = response.view === "actual" ? line.actual : line.projected;
    if (line.category === "income") {
      monthly[m].ingresos += value;
    } else {
      monthly[m].egresos += value;
    }
  }

  return Object.entries(monthly)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([month, vals]) => {
      const saldo = vals.ingresos - vals.egresos;
      acumulado += saldo;
      return {
        month: MONTH_NAMES[Number(month) - 1] ?? `M${month}`,
        ingresos: vals.ingresos,
        egresos: vals.egresos,
        saldo,
        acumulado,
      };
    });
}

function responseToComparisonData(
  response: CashflowResponse,
): CashflowComparisonPoint[] {
  const monthly: Record<
    number,
    { proyectado: number; real: number; diferencia: number }
  > = {};

  for (const line of response.lines) {
    const m = line.month;
    if (!monthly[m])
      monthly[m] = { proyectado: 0, real: 0, diferencia: 0 };
    monthly[m].proyectado += line.projected;
    monthly[m].real += line.actual;
    monthly[m].diferencia += line.difference;
  }

  return Object.entries(monthly)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([month, vals]) => ({
      month: MONTH_NAMES[Number(month) - 1] ?? `M${month}`,
      proyectado: vals.proyectado,
      real: vals.real,
      diferencia: vals.diferencia,
    }));
}

// ─── Main Component ──────────────────────────────────────

export interface CashflowChartProps {
  data: CashflowResponse | null;
  loading: boolean;
  // Extended for consult button + validation (HU-F1-007)
  fromYear: number;
  fromMonth: number;
  toYear: number;
  toMonth: number;
  view: string;
  periodValid: boolean;
  onViewChange: (v: string) => void;
  onFromYearChange: (y: number) => void;
  onFromMonthChange: (m: number) => void;
  onToYearChange: (y: number) => void;
  onToMonthChange: (m: number) => void;
  onConsult: () => void;
}

export function CashflowChart({
  data,
  loading,
  fromYear,
  fromMonth,
  toYear,
  toMonth,
  view,
  periodValid,
  onViewChange,
  onFromYearChange,
  onFromMonthChange,
  onToYearChange,
  onToMonthChange,
  onConsult,
}: CashflowChartProps) {
  if (loading && !data) {
    return <CashflowSkeleton />;
  }

  return (
    <div className="w-full">
      <CashflowSelectors
        view={view}
        fromYear={fromYear}
        fromMonth={fromMonth}
        toYear={toYear}
        toMonth={toMonth}
        onViewChange={onViewChange}
        onPeriodChange={(fy, fm, ty, tm) => {
          onFromYearChange(fy);
          onFromMonthChange(fm);
          onToYearChange(ty);
          onToMonthChange(tm);
        }}
        periodValid={periodValid}
        onConsult={onConsult}
        loading={loading}
      />

      {data && data.alerts && data.alerts.length > 0 && (
        <AlertsBanner alerts={data.alerts} />
      )}

      {data && <CashflowSummary response={data} />}

      {data && view === "comparison" ? (
        <CashflowComparisonChartInner
          data={responseToComparisonData(data)}
          title="Comparativa: Proyectado vs Real"
        />
      ) : data ? (
        <>
          <CashflowBarChartInner
            data={responseToBarData(data)}
            title={
              view === "projected"
                ? "Flujo de Caja Proyectado"
                : "Flujo de Caja Real"
            }
          />
          <div className="mt-6">
            <CashflowLineChartInner
              data={responseToBarData(data)}
              title="Tendencia de Flujo"
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

// ─── Legacy exports (backward compat) ────────────────────

export function CashflowBarChart({
  data,
  title,
}: {
  data: CashflowDataPoint[];
  title?: string;
}) {
  return <CashflowBarChartInner data={data} title={title} />;
}

export function CashflowLineChart({
  data,
  title,
}: {
  data: CashflowDataPoint[];
  title?: string;
}) {
  return <CashflowLineChartInner data={data} title={title} />;
}

/** Helper para generar datos locales (backward compat) */
export function generateCashflowData(
  monthlyRevenue: number,
  monthlyCostPct: number,
  monthlyFixedCosts: number,
  months: number = 12,
): CashflowDataPoint[] {
  const costOfSales = monthlyRevenue * monthlyCostPct;
  const egresos = costOfSales + monthlyFixedCosts;
  const saldo = monthlyRevenue - egresos;

  let acumulado = 0;
  return Array.from({ length: months }, (_, i) => {
    acumulado += saldo;
    return {
      month: MONTH_NAMES[i % 12],
      ingresos: monthlyRevenue,
      egresos,
      saldo,
      acumulado,
    };
  });
}
