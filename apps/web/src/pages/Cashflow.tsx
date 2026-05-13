/**
 * CashflowPage — Página de Flujo de Caja con selector de período/vista.
 *
 * HU-F1-007: UI de Flujo de Caja con selector de período/vista
 *
 * @module pages/Cashflow
 */
import { useCashflow } from "@/hooks/useAccounting";
import { CashflowChart } from "@/components/dashboard/CashflowChart";

export function CashflowPage() {
  const { data, loading, error, params, changeParams } = useCashflow({
    view: "projected",
  });

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

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      <CashflowChart
        data={data}
        loading={loading}
        params={params}
        onParamsChange={changeParams}
      />

      {/* No data state */}
      {!loading && !data && !error && (
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
