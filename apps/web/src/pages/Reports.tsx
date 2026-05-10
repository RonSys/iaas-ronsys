/**
 * Reports — Reportes financieros detallados con navegación por tabs.
 *
 * Cuatro tabs disponibles:
 * - PYG: Estado de Resultados con desglose completo
 * - Balance: Balance General (activo / pasivo + patrimonio)
 * - BCSS: Balance de Comprobación de Sumas y Saldos (tabla completa)
 * - Ratios: Tabla con valor, meta, fórmula y semáforo 🟢🟡🔴
 *
 * Cada tab carga sus datos independientemente vía hooks contables.
 *
 * @page Reports
 */
import { useState, useEffect, useCallback } from "react";
import {
  useIncomeStatement,
  useBalanceSheet,
  useRatios,
  useBCSS,
} from "@/hooks/useAccounting";
import { fmtCurrency, fmtPct, TrafficLight, Skeleton, KPICard } from "@/components/dashboard/KPICard";

type Tab = "pyg" | "balance" | "bcss" | "ratios";

export function Reports() {
  const [tab, setTab] = useState<Tab>("pyg");

  const pyg = useIncomeStatement();
  const balance = useBalanceSheet();
  const bcss = useBCSS();
  const ratios = useRatios();

  const loadAll = useCallback(() => {
    pyg.refetch();
    balance.refetch();
    bcss.refetch();
    ratios.refetch();
  }, [pyg.refetch, balance.refetch, bcss.refetch, ratios.refetch]);

  // Load all on first render if not loaded
  useEffect(() => {
    if (!pyg.data) pyg.refetch();
    if (!balance.data) balance.refetch();
    if (!bcss.data) bcss.refetch();
    if (!ratios.data) ratios.refetch();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">📋 Reportes Financieros</h2>
        <button onClick={loadAll} className="btn-ghost text-sm">
          🔄 Actualizar todos
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {([
          ["pyg", "📄 PYG"],
          ["balance", "⚖️ Balance"],
          ["bcss", "🧾 BCSS"],
          ["ratios", "🚦 Ratios"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === key
                ? "bg-white text-brand-primary shadow-sm"
                : "text-brand-text-secondary hover:text-brand-text-primary"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === "pyg" && <IncomeStatementReport data={pyg.data} loading={pyg.loading} error={pyg.error} />}
      {tab === "balance" && <BalanceSheetReport data={balance.data} loading={balance.loading} error={balance.error} />}
      {tab === "bcss" && <BCSSReport data={bcss.data} loading={bcss.loading} error={bcss.error} />}
      {tab === "ratios" && <RatiosReport data={ratios.data} loading={ratios.loading} error={ratios.error} />}
    </div>
  );
}

/* ─── PYG Report ─── */

function IncomeStatementReport({
  data,
  loading,
  error,
}: {
  data: import("@/types").IncomeStatementResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <SkeletonReport rows={10} />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <EmptyBox message="Ejecutá el Setup para generar el PYG." />;

  const opExpensesTotal = Object.values(data.operating_expenses).reduce((a, b) => a + b, 0);

  return (
    <div className="card">
      <h3 className="font-bold text-brand-text-primary mb-4 text-lg">
        📄 Estado de Resultados (Pérdidas y Ganancias)
      </h3>
      <p className="text-sm text-brand-text-secondary mb-4">Período: {data.period}</p>
      <table className="w-full text-sm">
        <tbody>
          <StatementRow label="(+) Ventas" value={data.revenue} />
          <StatementRow label="(-) Costo de Ventas" value={-data.cost_of_sales} negative />
          <Separator />
          <StatementRow label="Utilidad Bruta" value={data.gross_profit} bold />
          <StatementRow label={`Margen Bruto: ${fmtPct(data.gross_margin_pct)}`} value={0} sub />
          <Separator />
          <StatementRow label="(-) Gastos Operativos" value={-opExpensesTotal} negative />
          {Object.entries(data.operating_expenses).map(([k, v]) => (
            k !== "depreciation" && (
              <StatementRow key={k} label={`     ${formatKey(k)}`} value={-v} sub negative />
            )
          ))}
          {data.operating_expenses["depreciation"] != null && (
            <StatementRow
              label="     Depreciación"
              value={-data.operating_expenses["depreciation"]}
              sub
              negative
            />
          )}
          <Separator />
          <StatementRow label="EBITDA" value={data.ebitda} bold />
          <StatementRow label={`Margen Operativo: ${fmtPct(data.operating_margin_pct)}`} value={0} sub />
          <Separator />
          <StatementRow label="(-) Gastos Financieros" value={-data.financial_expenses} negative />
          <Separator />
          <StatementRow label="Utilidad antes de impuestos" value={data.income_before_tax} bold />
          <StatementRow label="(-) Impuesto a la Renta (29.5%)" value={-data.income_tax} negative />
          <Separator />
          <StatementRow label="UTILIDAD NETA" value={data.net_income} bold accent />
          <StatementRow label={`Margen Neto: ${fmtPct(data.net_margin_pct)}`} value={0} sub />
        </tbody>
      </table>
    </div>
  );
}

/* ─── Balance Sheet Report ─── */

function BalanceSheetReport({
  data,
  loading,
  error,
}: {
  data: import("@/types").BalanceSheetResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <SkeletonReport rows={10} />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <EmptyBox message="Ejecutá el Setup para generar el Balance." />;

  return (
    <div className="card">
      <h3 className="font-bold text-brand-text-primary mb-4 text-lg">⚖️ Balance General</h3>
      <p className="text-sm text-brand-text-secondary mb-4">Al: {data.as_of}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Activos */}
        <div>
          <h4 className="font-bold text-brand-primary mb-3">🏗️ ACTIVOS</h4>
          <table className="w-full text-sm mb-4">
            <tbody>
              <tr><td colSpan={2} className="font-semibold py-1 text-brand-text-secondary">Activo Corriente</td></tr>
              {Object.entries(data.current_assets).map(([k, v]) => (
                <StatementRow key={k} label={`  ${formatKey(k)}`} value={v} sub />
              ))}
              <tr><td colSpan={2} className="font-semibold py-1 pt-3 text-brand-text-secondary">Activo No Corriente</td></tr>
              {Object.entries(data.non_current_assets).map(([k, v]) => (
                <StatementRow key={k} label={`  ${formatKey(k)}`} value={v} sub />
              ))}
              <StatementRow label="Depreciación Acumulada" value={-data.accumulated_depreciation} sub negative />
              <Separator />
              <StatementRow label="TOTAL ACTIVOS" value={data.total_assets} bold />
            </tbody>
          </table>
        </div>

        {/* Pasivo + Patrimonio */}
        <div>
          <h4 className="font-bold text-brand-primary mb-3">💰 PASIVO + PATRIMONIO</h4>
          <table className="w-full text-sm mb-4">
            <tbody>
              <tr><td colSpan={2} className="font-semibold py-1 text-brand-text-secondary">Pasivo Corriente</td></tr>
              {Object.entries(data.current_liabilities).map(([k, v]) => (
                <StatementRow key={k} label={`  ${formatKey(k)}`} value={v} sub />
              ))}
              <tr><td colSpan={2} className="font-semibold py-1 pt-3 text-brand-text-secondary">Pasivo No Corriente</td></tr>
              {Object.entries(data.non_current_liabilities).map(([k, v]) => (
                <StatementRow key={k} label={`  ${formatKey(k)}`} value={v} sub />
              ))}
              <Separator />
              <StatementRow label="Total Pasivos" value={data.total_liabilities} />
              <tr><td colSpan={2} className="font-semibold py-1 pt-3 text-brand-text-secondary">Patrimonio</td></tr>
              <StatementRow label="  Capital" value={data.capital} sub />
              <StatementRow label="  Resultados Acumulados" value={data.retained_earnings} sub />
              <StatementRow label="  Resultado del Ejercicio" value={data.current_income} sub />
              <Separator />
              <StatementRow label="Total Patrimonio" value={data.total_equity} bold />
              <Separator />
              <StatementRow label="TOTAL PASIVO + PATRIMONIO" value={data.total_liabilities_and_equity} bold />
            </tbody>
          </table>

          <div className={`p-3 rounded-lg text-sm font-medium ${data.is_balanced ? "bg-brand-success/10 text-brand-success" : "bg-brand-error/10 text-brand-error"}`}>
            {data.is_balanced ? "✅ Balance Cuadrado: Activo = Pasivo + Patrimonio" : "⚠️ Balance Descuadrado"}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── BCSS Report ─── */

function BCSSReport({
  data,
  loading,
  error,
}: {
  data: import("@/types").BCSSResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <SkeletonReport rows={10} />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <EmptyBox message="Sin datos de BCSS." />;

  return (
    <div className="card">
      <h3 className="font-bold text-brand-text-primary mb-4 text-lg">
        🧾 Balance de Comprobación de Sumas y Saldos
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard title="Total Débitos" value={fmtCurrency(data.total_debits)} />
        <KPICard title="Total Créditos" value={fmtCurrency(data.total_credits)} />
        <KPICard title="Diferencia" value={fmtCurrency(data.total_debits - data.total_credits)} />
        <KPICard title="Estado" value={data.is_balanced ? "✅ Cuadrado" : "⚠️ Descuadrado"} />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-brand-primary/20 text-left text-xs uppercase tracking-wider text-brand-text-secondary">
              <th className="py-2 pr-3">Código</th>
              <th className="py-2 pr-3">Cuenta</th>
              <th className="py-2 pr-3 text-right">Débito</th>
              <th className="py-2 pr-3 text-right">Crédito</th>
              <th className="py-2 pr-3 text-right">Saldo</th>
              <th className="py-2 text-center">Nat.</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.account_code} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 pr-3 font-mono text-xs text-brand-primary">
                  {line.account_code}
                </td>
                <td className="py-2 pr-3">{line.account_name}</td>
                <td className="py-2 pr-3 text-right font-mono text-xs">
                  {fmtCurrency(line.total_debit)}
                </td>
                <td className="py-2 pr-3 text-right font-mono text-xs">
                  {fmtCurrency(line.total_credit)}
                </td>
                <td className={`py-2 pr-3 text-right font-mono text-xs font-semibold ${line.balance >= 0 ? "" : "text-brand-error"}`}>
                  {fmtCurrency(line.balance)}
                </td>
                <td className="py-2 text-center font-mono text-xs">
                  {line.balance_nature === "D" ? (
                    <span className="text-brand-primary font-bold">D</span>
                  ) : (
                    <span className="text-brand-accent font-bold">A</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-brand-primary/20 font-bold bg-gray-50">
              <td colSpan={2} className="py-2 pr-3 text-sm">Totales</td>
              <td className="py-2 pr-3 text-right font-mono text-sm">
                {fmtCurrency(data.total_debits)}
              </td>
              <td className="py-2 pr-3 text-right font-mono text-sm">
                {fmtCurrency(data.total_credits)}
              </td>
              <td colSpan={2}></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

/* ─── Ratios Report ─── */

function RatiosReport({
  data,
  loading,
  error,
}: {
  data: import("@/types").RatioItem[] | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <SkeletonReport rows={8} />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) return <EmptyBox message="Sin ratios calculados." />;

  return (
    <div className="card">
      <h3 className="font-bold text-brand-text-primary mb-4 text-lg">🚦 Ratios Financieros</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-brand-primary/20 text-left text-xs uppercase tracking-wider text-brand-text-secondary">
              <th className="py-2 pr-3">Ratio</th>
              <th className="py-2 pr-3 text-right">Valor</th>
              <th className="py-2 pr-3">Meta</th>
              <th className="py-2 pr-3">Fórmula</th>
              <th className="py-2 text-center">Semáforo</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.name} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2.5 pr-3 font-medium">{r.name}</td>
                <td className="py-2.5 pr-3 text-right font-mono font-semibold">
                  {r.name.includes("Margen") || r.name.includes("RO")
                    ? fmtPct(r.value)
                    : r.value.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="py-2.5 pr-3 text-brand-text-secondary">{r.target}</td>
                <td className="py-2.5 pr-3 text-xs text-brand-text-secondary font-mono">{r.formula}</td>
                <td className="py-2.5 text-center">
                  <TrafficLight status={r.traffic_light} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Shared UI ─── */

function StatementRow({
  label,
  value,
  bold,
  accent,
  sub,
  negative,
}: {
  label: string;
  value: number;
  bold?: boolean;
  accent?: boolean;
  sub?: boolean;
  negative?: boolean;
}) {
  const color = accent ? "text-brand-accent" : negative ? "text-brand-error" : "";
  return (
    <tr className={bold ? "font-semibold" : sub ? "text-xs" : ""}>
      <td className={`py-1 pr-4 ${color}`}>{label}</td>
      <td className={`py-1 text-right font-mono text-xs ${color}`}>
        {fmtCurrency(value)}
      </td>
    </tr>
  );
}

function Separator() {
  return (
    <tr><td colSpan={2} className="py-1"><hr className="border-gray-200" /></td></tr>
  );
}

function SkeletonReport({ rows }: { rows: number }) {
  return (
    <div className="card space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="card border-brand-error bg-brand-error/5 text-brand-error text-sm">
      ⚠️ {message}
    </div>
  );
}

function EmptyBox({ message }: { message: string }) {
  return (
    <div className="card text-center py-8 text-brand-text-secondary">
      <span className="text-3xl">📋</span>
      <p className="mt-2">{message}</p>
    </div>
  );
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
