/**
 * Dashboard — Panel principal de control financiero.
 *
 * Muestra KPIs clave (ventas, utilidad neta, EBITDA, activos),
 * PYG resumido, Balance General, gráficos de flujo de caja (Recharts),
 * Ratios con semáforo y BCSS resumido.
 *
 * Todos los datos vienen del backend vía hooks useBCSS, useIncomeStatement,
 * useBalanceSheet, useRatios. Si no hay simulación previa, muestra
 * mensajes de empty state.
 *
 * @page Dashboard
 */
import { useCallback, useMemo } from "react";
import { KPICard, SectionHeader, TrafficLight, Skeleton, fmtCurrency, fmtPct, fmtNum } from "@/components/dashboard/KPICard";
import { CashflowBarChart, CashflowLineChart, generateCashflowData } from "@/components/dashboard/CashflowChart";
import { useIncomeStatement, useBalanceSheet, useRatios, useBCSS } from "@/hooks/useAccounting";

export function Dashboard() {
  const pyg = useIncomeStatement();
  const balance = useBalanceSheet();
  const ratios = useRatios();
  const bcss = useBCSS();

  const loadAll = useCallback(() => {
    pyg.refetch();
    balance.refetch();
    ratios.refetch();
    bcss.refetch();
  }, [pyg.refetch, balance.refetch, ratios.refetch, bcss.refetch]);

  // Generate cashflow data from PYG summary
  const cashflowData = useMemo(() => {
    if (!pyg.data) return null;
    const monthlyRevenue = pyg.data.revenue;
    const monthlyCostPct = pyg.data.cost_of_sales / Math.max(pyg.data.revenue, 1);
    const opExpenses = Object.values(pyg.data.operating_expenses).reduce((a, b) => a + b, 0);
    const monthlyFixedCosts = opExpenses + pyg.data.financial_expenses + pyg.data.income_tax;
    return generateCashflowData(monthlyRevenue, monthlyCostPct, monthlyFixedCosts);
  }, [pyg.data]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header row */}
      <SectionHeader title="Panel de Control" icon="📊">
        <button onClick={loadAll} className="btn-ghost text-sm">
          🔄 Actualizar
        </button>
      </SectionHeader>

      {/* KPIs principales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {pyg.loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-7 w-28" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))
        ) : (
          <>
            <KPICard
              title="Ventas"
              value={pyg.data ? fmtCurrency(pyg.data.revenue) : "—"}
              subtitle={pyg.data ? `Margen bruto: ${fmtPct(pyg.data.gross_margin_pct)}` : undefined}
              icon="💰"
            />
            <KPICard
              title="Utilidad Neta"
              value={pyg.data ? fmtCurrency(pyg.data.net_income) : "—"}
              subtitle={pyg.data ? `Margen neto: ${fmtPct(pyg.data.net_margin_pct)}` : undefined}
              icon="📈"
              trend={pyg.data?.net_income ? (pyg.data.net_income > 0 ? "up" : "down") : undefined}
            />
            <KPICard
              title="EBITDA"
              value={pyg.data ? fmtCurrency(pyg.data.ebitda) : "—"}
              subtitle={pyg.data ? `Margen op: ${fmtPct(pyg.data.operating_margin_pct)}` : undefined}
              icon="💎"
            />
            <KPICard
              title="Activos Totales"
              value={balance.data ? fmtCurrency(balance.data.total_assets) : "—"}
              subtitle={balance.data?.is_balanced ? "Balance cuadrado ✅" : "⚠️ Descuadrado"}
              icon="🏦"
            />
          </>
        )}
      </div>

      {/* Resultados + Balance side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PYG resumido */}
        <div className="card">
          <h3 className="font-bold text-brand-text-primary mb-3">
            📄 Estado de Resultados
          </h3>
          {pyg.loading ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : pyg.error ? (
            <div className="text-brand-error text-sm">{pyg.error}</div>
          ) : pyg.data ? (
            <table className="w-full text-sm">
              <tbody>
                <Row label="Ventas" value={pyg.data.revenue} />
                <Row label="Costo de Ventas" value={-pyg.data.cost_of_sales} />
                <RowSep />
                <Row label="Utilidad Bruta" value={pyg.data.gross_profit} bold />
                <Row label="Gastos Operativos" value={-Object.values(pyg.data.operating_expenses).reduce((a, b) => a + b, 0)} />
                <Row label="EBIT" value={pyg.data.ebit} bold />
                <Row label="Gastos Financieros" value={-pyg.data.financial_expenses} />
                <Row label="Impuesto" value={-pyg.data.income_tax} />
                <RowSep />
                <Row label="Utilidad Neta" value={pyg.data.net_income} bold accent />
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-brand-text-secondary">
              Ejecutá una simulación en{" "}
              <a href="/setup" className="text-brand-primary underline">Setup</a>{" "}
              para ver resultados.
            </p>
          )}
        </div>

        {/* Balance General */}
        <div className="card">
          <h3 className="font-bold text-brand-text-primary mb-3">
            ⚖️ Balance General
          </h3>
          {balance.loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : balance.error ? (
            <div className="text-brand-error text-sm">{balance.error}</div>
          ) : balance.data ? (
            <table className="w-full text-sm">
              <tbody>
                <tr>
                  <td colSpan={2} className="font-semibold text-brand-primary pt-2 pb-1">
                    Activos
                  </td>
                </tr>
                <Row label="Activo Corriente" value={Object.values(balance.data.current_assets).reduce((a, b) => a + b, 0)} />
                <Row label="Activo No Corriente" value={Object.values(balance.data.non_current_assets).reduce((a, b) => a + b, 0)} />
                <Row label="Deprec. Acumulada" value={-balance.data.accumulated_depreciation} />
                <Row label="Total Activos" value={balance.data.total_assets} bold />
                <tr>
                  <td colSpan={2} className="font-semibold text-brand-primary pt-2 pb-1">
                    Pasivo + Patrimonio
                  </td>
                </tr>
                <Row label="Total Pasivos" value={balance.data.total_liabilities} />
                <Row label="Capital" value={balance.data.capital} />
                <Row label="Resultados Acum." value={balance.data.retained_earnings} />
                <Row label="Total P+P" value={balance.data.total_liabilities_and_equity} bold />
                <RowSep />
                <Row
                  label={balance.data.is_balanced ? "✅ Balance cuadrado" : "⚠️ Descuadrado"}
                  value={balance.data.total_assets - balance.data.total_liabilities_and_equity}
                  bold={!balance.data.is_balanced}
                />
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-brand-text-secondary">
              Ejecutá una simulación para ver el balance.
            </p>
          )}
        </div>
      </div>

      {/* Gráficos de Flujo de Caja */}
      {cashflowData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <CashflowBarChart
              data={cashflowData}
              title="📊 Ingresos vs Egresos (Proyectado)"
            />
          </div>
          <div className="card">
            <CashflowLineChart
              data={cashflowData}
              title="📈 Flujo de Caja Acumulado"
            />
          </div>
        </div>
      )}

      {/* Ratios con semáforo */}
      <div className="card">
        <h3 className="font-bold text-brand-text-primary mb-4">🚦 Ratios Financieros</h3>
        {ratios.loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : ratios.error ? (
          <div className="text-brand-error text-sm">{ratios.error}</div>
        ) : ratios.data && ratios.data.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {ratios.data.map((r) => (
              <div key={r.name} className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-brand-text-secondary uppercase">
                    {r.name}
                  </span>
                  <TrafficLight status={r.traffic_light} />
                </div>
                <div className="text-lg font-bold text-brand-text-primary">
                  {r.name.includes("Margen") || r.name.includes("ROE") || r.name.includes("ROA")
                    ? fmtPct(r.value)
                    : fmtNum(r.value, 2)}
                </div>
                <div className="text-[10px] text-brand-text-secondary mt-1 truncate" title={r.formula}>
                  Meta: {r.target}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-brand-text-secondary">
            Ejecutá una simulación para ver los ratios.
          </p>
        )}
      </div>

      {/* BCSS resumen */}
      <div className="card">
        <h3 className="font-bold text-brand-text-primary mb-3">
          🧾 Balance de Comprobación (BCSS)
        </h3>
        {bcss.loading ? (
          <Skeleton className="h-20 w-full" />
        ) : bcss.error ? (
          <div className="text-brand-error text-sm">{bcss.error}</div>
        ) : bcss.data ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KPICard title="Total Débitos" value={fmtCurrency(bcss.data.total_debits)} />
            <KPICard title="Total Créditos" value={fmtCurrency(bcss.data.total_credits)} />
            <KPICard
              title="Cuadrado"
              value={bcss.data.is_balanced ? "✅ Sí" : "⚠️ No"}
              subtitle={`${bcss.data.lines.length} cuentas`}
            />
            <KPICard
              title="Diferencia"
              value={fmtCurrency(bcss.data.total_debits - bcss.data.total_credits)}
            />
          </div>
        ) : (
          <p className="text-sm text-brand-text-secondary">
            Sin datos de BCSS. Ejecutá el Setup.
          </p>
        )}
      </div>
    </div>
  );
}

/* ─── Helpers ─── */

function Row({
  label,
  value,
  bold,
  accent,
}: {
  label: string;
  value: number;
  bold?: boolean;
  accent?: boolean;
}) {
  return (
    <tr className={bold ? "font-semibold" : ""}>
      <td className={`py-1 pr-4 ${accent ? "text-brand-accent" : ""}`}>{label}</td>
      <td className={`py-1 text-right font-mono text-xs ${accent ? "text-brand-accent" : ""}`}>
        {fmtCurrency(value)}
      </td>
    </tr>
  );
}

function RowSep() {
  return (
    <tr>
      <td colSpan={2} className="py-0.5">
        <hr className="border-gray-200" />
      </td>
    </tr>
  );
}
