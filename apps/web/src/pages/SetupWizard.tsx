/**
 * SetupWizard — Formulario de configuración inicial de inversión.
 *
 * Permite ingresar todas las variables del modelo financiero:
 * - Inversión inicial (capital, préstamo)
 * - Gastos de instalación (equipamiento, mobiliario, licencias)
 * - Gastos fijos mensuales (alquiler, sueldos, servicios)
 * - Proyección de ventas (precio, volumen, costo %)
 * - Vida útil de activos (depreciación)
 *
 * Al enviar, hace POST /api/accounting/setup y muestra un resumen
 * de resultados con enlaces al Dashboard y Simulador.
 *
 * @page Setup
 */
import { useState } from "react";
import { useSimulation } from "@/hooks/useAccounting";
import { fmtCurrency } from "@/components/dashboard/KPICard";
import type { InvestmentInput } from "@/types";

const DEFAULT_INPUT: InvestmentInput = {
  capital: 50000,
  loan_amount: 30000,
  loan_rate_annual: 0.125,
  loan_term_months: 24,
  equipment_cost: 15000,
  furniture_cost: 5000,
  computer_cost: 3000,
  software_cost: 1000,
  guarantee_deposit: 3000,
  initial_inventory: 5000,
  monthly_sales: [25000, 25000, 25000, 25000, 25000, 25000, 25000, 25000, 25000, 25000, 25000, 25000],
  monthly_cost_pct: 0.40,
  monthly_rent: 2500,
  monthly_utilities: 800,
  monthly_salaries: 5000,
  monthly_marketing: 500,
  monthly_admin: 0,
  monthly_maintenance: 0,
  equipment_life_years: 8,
  furniture_life_years: 10,
  computer_life_years: 5,
  software_life_years: 3,
  months: 12,
};

export function SetupWizard() {
  const [input, setInput] = useState<InvestmentInput>({ ...DEFAULT_INPUT });
  const { result, loading, error, simulate } = useSimulation();

  const handleChange = (field: keyof InvestmentInput, value: unknown) => {
    setInput((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await simulate(input);
  };

  const handleReset = () => {
    setInput({ ...DEFAULT_INPUT });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">🏗️ Configuración Inicial</h2>
        <button onClick={handleReset} className="btn-ghost text-sm">
          ↺ Restaurar defaults
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Inversión Inicial */}
        <fieldset className="card">
          <legend className="font-bold text-brand-text-primary mb-4 flex items-center gap-2">
            📌 Inversión Inicial
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="Aporte de capital propio"
              value={input.capital}
              onChange={(v) => handleChange("capital", v)}
              min={1}
            />
            <FormField
              label="Préstamo bancario"
              value={input.loan_amount ?? 0}
              onChange={(v) => handleChange("loan_amount", v)}
            />
            <FormField
              label="Tasa de interés anual (%)"
              value={((input.loan_rate_annual ?? 0) * 100)}
              onChange={(v) => handleChange("loan_rate_annual", v / 100)}
              suffix="%"
              decimals={1}
            />
            <FormField
              label="Plazo del préstamo (meses)"
              value={input.loan_term_months ?? 12}
              onChange={(v) => handleChange("loan_term_months", v)}
              isInt
            />
          </div>
        </fieldset>

        {/* Gastos de Instalación */}
        <fieldset className="card">
          <legend className="font-bold text-brand-text-primary mb-4 flex items-center gap-2">
            🏪 Gastos de Instalación
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Equipamiento de cocina" value={input.equipment_cost ?? 0} onChange={(v) => handleChange("equipment_cost", v)} />
            <FormField label="Mobiliario" value={input.furniture_cost ?? 0} onChange={(v) => handleChange("furniture_cost", v)} />
            <FormField label="Equipos de cómputo" value={input.computer_cost ?? 0} onChange={(v) => handleChange("computer_cost", v)} />
            <FormField label="Software / Licencias" value={input.software_cost ?? 0} onChange={(v) => handleChange("software_cost", v)} />
            <FormField label="Garantía de alquiler" value={input.guarantee_deposit ?? 0} onChange={(v) => handleChange("guarantee_deposit", v)} />
            <FormField label="Inventario inicial" value={input.initial_inventory ?? 0} onChange={(v) => handleChange("initial_inventory", v)} />
          </div>
        </fieldset>

        {/* Gastos Fijos Mensuales */}
        <fieldset className="card">
          <legend className="font-bold text-brand-text-primary mb-4 flex items-center gap-2">
            💳 Gastos Fijos Mensuales
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Alquiler" value={input.monthly_rent ?? 0} onChange={(v) => handleChange("monthly_rent", v)} />
            <FormField label="Sueldos (planilla total)" value={input.monthly_salaries ?? 0} onChange={(v) => handleChange("monthly_salaries", v)} />
            <FormField label="Servicios (luz, agua, internet)" value={input.monthly_utilities ?? 0} onChange={(v) => handleChange("monthly_utilities", v)} />
            <FormField label="Marketing" value={input.monthly_marketing ?? 0} onChange={(v) => handleChange("monthly_marketing", v)} />
            <FormField label="Admin / Varios" value={input.monthly_admin ?? 0} onChange={(v) => handleChange("monthly_admin", v)} />
            <FormField label="Mantenimiento" value={input.monthly_maintenance ?? 0} onChange={(v) => handleChange("monthly_maintenance", v)} />
          </div>
        </fieldset>

        {/* Proyección de Ventas */}
        <fieldset className="card">
          <legend className="font-bold text-brand-text-primary mb-4 flex items-center gap-2">
            💵 Proyección de Ventas
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="Ventas mensuales (S/)"
              value={input.monthly_sales?.[0] ?? 25000}
              onChange={(v) => handleChange("monthly_sales", Array(12).fill(v))}
            />
            <FormField
              label="Costo de insumos (% de ventas)"
              value={((input.monthly_cost_pct ?? 0.40) * 100)}
              onChange={(v) => handleChange("monthly_cost_pct", v / 100)}
              suffix="%"
              decimals={1}
            />
            <FormField
              label="Meses a proyectar"
              value={input.months ?? 12}
              onChange={(v) => handleChange("months", v)}
              isInt
              min={1}
              max={60}
            />
          </div>
        </fieldset>

        {/* Vida útil */}
        <fieldset className="card">
          <legend className="font-bold text-brand-text-primary mb-4 flex items-center gap-2">
            ⏳ Vida Útil de Activos (años)
          </legend>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <FormField label="Equipamiento" value={input.equipment_life_years ?? 8} onChange={(v) => handleChange("equipment_life_years", v)} isInt min={1} />
            <FormField label="Mobiliario" value={input.furniture_life_years ?? 10} onChange={(v) => handleChange("furniture_life_years", v)} isInt min={1} />
            <FormField label="Cómputo" value={input.computer_life_years ?? 5} onChange={(v) => handleChange("computer_life_years", v)} isInt min={1} />
            <FormField label="Software" value={input.software_life_years ?? 3} onChange={(v) => handleChange("software_life_years", v)} isInt min={1} />
          </div>
        </fieldset>

        {/* Submit */}
        <div className="flex items-center gap-4">
          <button type="submit" disabled={loading} className="btn-primary px-8 py-2.5 text-base">
            {loading ? "⏳ Simulando..." : "📊 SIMULAR"}
          </button>
          <button type="button" onClick={handleReset} className="btn-outline px-6 py-2.5 text-base">
            💾 Guardar
          </button>
        </div>

        {error && (
          <div className="card border-brand-error bg-brand-error/5 text-brand-error text-sm">
            ⚠️ {error}
          </div>
        )}
      </form>

      {/* Resultados */}
      {result && (
        <div className="card border-brand-success/30 bg-brand-success/5 animate-fade-in">
          <h3 className="font-bold text-brand-success mb-4">✅ Simulación Completada</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MiniKPI label="Ventas" value={fmtCurrency(result.income_statement?.revenue ?? 0)} />
            <MiniKPI label="Utilidad Neta" value={fmtCurrency(result.income_statement?.net_income ?? 0)} />
            <MiniKPI label="Activos Totales" value={fmtCurrency(result.balance_sheet?.total_assets ?? 0)} />
            <MiniKPI label="BCSS" value={result.bcss?.is_balanced ? "✅ Cuadrado" : "⚠️ Descuadrado"} />
          </div>
          <div className="mt-4 flex gap-2">
            <a href="/" className="btn-primary text-sm">📊 Ver Dashboard</a>
            <a href="/simulador" className="btn-outline text-sm">🎮 Abrir Simulador</a>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── FormField ─── */

function FormField({
  label,
  value,
  onChange,
  suffix,
  isInt,
  min,
  max,
  decimals,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  suffix?: string;
  isInt?: boolean;
  min?: number;
  max?: number;
  decimals?: number;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-brand-text-secondary">{label}</span>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-brand-text-secondary">
          S/
        </span>
        <input
          type="number"
          value={isInt ? Math.round(value) : decimals ? value.toFixed(decimals) : value}
          min={min}
          max={max}
          step={isInt ? 1 : "any"}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) onChange(v);
          }}
          className="input-field pl-8"
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-brand-text-secondary">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}

function MiniKPI({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-2 rounded-lg bg-white/50">
      <div className="text-xs text-brand-text-secondary">{label}</div>
      <div className="text-lg font-bold text-brand-text-primary">{value}</div>
    </div>
  );
}
