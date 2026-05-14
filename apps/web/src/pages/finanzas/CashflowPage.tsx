/**
 * CashflowPage — Página de Flujo de Caja con selector de período/vista.
 *
 * HU-F1-007: UI de Flujo de Caja con selector de período/vista
 *
 * Estados completos:
 * - Loading: skeleton mientras carga
 * - Error: mensaje + botón "Reintentar"
 * - Empty: "No hay transacciones en este período"
 * - Data: gráfico de barras/comparativa + alertas + KPIs
 *
 * Validación: botón "Consultar" deshabilitado si from > to
 *
 * @module pages/finanzas/CashflowPage
 */
import { useState, useCallback } from "react";
import { useCashflow } from "@/hooks/useAccounting";
import { CashflowChart } from "@/components/dashboard/CashflowChart";

const CURRENT_YEAR = new Date().getFullYear();

export function CashflowPage() {
  const { data, loading, error, changeParams } = useCashflow({
    view: "projected",
  });

  // Local state for period selectors (validated before fetch)
  const [fromYear, setFromYear] = useState(CURRENT_YEAR);
  const [fromMonth, setFromMonth] = useState(1);
  const [toYear, setToYear] = useState(CURRENT_YEAR);
  const [toMonth, setToMonth] = useState(12);
  const [view, setView] = useState("projected");

  const periodValid = fromYear < toYear || (fromYear === toYear && fromMonth <= toMonth);

  const handleConsult = useCallback(() => {
    changeParams({
      view: view as "projected" | "actual" | "comparison",
      from: `${fromYear}-${String(fromMonth).padStart(2, "0")}`,
      to: `${toYear}-${String(toMonth).padStart(2, "0")}`,
    });
  }, [view, fromYear, fromMonth, toYear, toMonth, changeParams]);

  const hasData = data && data.lines && data.lines.length > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            💰 Flujo de Caja
          </h2>
          <p className="text-sm text-brand-text-secondary">
            Proyección, datos reales y comparativa de ingresos y egresos
          </p>
        </div>
      </div>

      {/* Error state with Retry */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button
            onClick={handleConsult}
            className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      )}

      <CashflowChart
        data={data}
        loading={loading}
        // Extended props for consult button + validation
        fromYear={fromYear}
        fromMonth={fromMonth}
        toYear={toYear}
        toMonth={toMonth}
        view={view}
        periodValid={periodValid}
        onViewChange={setView}
        onFromYearChange={setFromYear}
        onFromMonthChange={setFromMonth}
        onToYearChange={setToYear}
        onToMonthChange={setToMonth}
        onConsult={handleConsult}
      />

      {/* Empty state: no transactions */}
      {!loading && !error && data && !hasData && (
        <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center">
          <span className="text-4xl">📭</span>
          <p className="mt-2 text-brand-text-secondary font-medium">
            No hay transacciones en este período
          </p>
          <p className="text-sm text-brand-text-secondary">
            Probá con otro rango de fechas o cambiá la vista.
          </p>
        </div>
      )}

      {/* No data at all (initial state) */}
      {!loading && !error && !data && (
        <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center">
          <span className="text-4xl">📊</span>
          <p className="mt-2 text-brand-text-secondary">
            No hay datos de flujo de caja disponibles.
          </p>
          <p className="text-sm text-brand-text-secondary">
            Ejecutá el setup contable para generar proyecciones.
          </p>
        </div>
      )}
    </div>
  );
}
