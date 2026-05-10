/**
 * Simulator — Simulador interactivo "¿qué pasa si...?"
 *
 * Ofrece 5 sliders (precio, platos/día, costo %, alquiler, sueldos)
 * que disparan automáticamente POST /api/accounting/setup con debounce
 * de 400ms. Los resultados se actualizan en vivo.
 *
 * Permite guardar hasta 4 escenarios y compararlos en una tabla
 * lado a lado (nombre, variables, ventas, utilidad, payback, VAN, TIR).
 *
 * @page Simulator
 */
import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useSimulation } from "@/hooks/useAccounting";
import { fmtCurrency, fmtPct, TrafficLight, Skeleton } from "@/components/dashboard/KPICard";
import type { InvestmentInput } from "@/types";

interface ScenarioSnapshot {
  id: string;
  name: string;
  price: number;
  platesPerDay: number;
  costPct: number;
  rent: number;
  salaries: number;
  revenue: number;
  grossProfit: number;
  netIncome: number;
  payback: number | null;
  van: number | null;
  tir: number | null;
  timestamp: Date;
}

const BASE_INPUT: InvestmentInput = {
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
  equipment_life_years: 8,
  furniture_life_years: 10,
  computer_life_years: 5,
  software_life_years: 3,
  months: 12,
};

export function Simulator() {
  const { isAuthenticated } = useAuth();
  const [price, setPrice] = useState(28);
  const [platesPerDay, setPlatesPerDay] = useState(40);
  const [daysPerMonth] = useState(26);
  const [costPct, setCostPct] = useState(40);
  const [rent, setRent] = useState(2500);
  const [salaries, setSalaries] = useState(5000);
  const [scenarios, setScenarios] = useState<ScenarioSnapshot[]>([]);

  const { result, loading, error, simulate } = useSimulation();

  const recalcMonthlySales = useCallback(
    () => Array(12).fill(price * platesPerDay * daysPerMonth),
    [price, platesPerDay, daysPerMonth],
  );

  const runSimulation = useCallback(() => {
    // No simular si no hay sesión activa
    if (!isAuthenticated) return;
    const input: InvestmentInput = {
      ...BASE_INPUT,
      monthly_sales: recalcMonthlySales(),
      monthly_cost_pct: costPct / 100,
      monthly_rent: rent,
      monthly_salaries: salaries,
    };
    // Ignorar rechazos: el error ya está en el estado 'error'
    simulate(input).catch(() => {});
  }, [recalcMonthlySales, costPct, rent, salaries, simulate, isAuthenticated]);

  // Auto-simulate on first render and every slider change
  useEffect(() => {
    if (!isAuthenticated) return;
    const timer = setTimeout(runSimulation, 400);
    return () => clearTimeout(timer);
  }, [runSimulation, isAuthenticated]);

  const incomeStmt = result?.income_statement;
  const ratios = result?.ratios;

  // Find payback ratio if available
  const paybackRatio = ratios?.find((r) => r.name.toLowerCase().includes("payback"));
  const vanRatio = ratios?.find((r) => r.name.toLowerCase().includes("van"));
  const tirRatio = ratios?.find((r) => r.name.toLowerCase().includes("tir"));

  const saveScenario = () => {
    if (!incomeStmt) return;
    const snapshot: ScenarioSnapshot = {
      id: Date.now().toString(),
      name: scenarios.length === 0
        ? "Realista"
        : scenarios.length === 1
          ? "Optimista"
          : `Escenario ${scenarios.length + 1}`,
      price,
      platesPerDay,
      costPct,
      rent,
      salaries,
      revenue: incomeStmt.revenue,
      grossProfit: incomeStmt.gross_profit,
      netIncome: incomeStmt.net_income,
      payback: paybackRatio?.value ?? null,
      van: vanRatio?.value ?? null,
      tir: tirRatio?.value ?? null,
      timestamp: new Date(),
    };
    setScenarios((prev) => [...prev, snapshot]);
  };

  const deleteScenario = (id: string) => {
    setScenarios((prev) => prev.filter((s) => s.id !== id));
  };

  const clearScenarios = () => setScenarios([]);

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold">🎮 Simulador — ¿Qué pasa si...?</h2>

      {/* Sliders */}
      <div className="card space-y-5">
        <SliderField
          label="💵 Precio promedio por plato"
          value={price}
          min={15}
          max={50}
          step={1}
          onChange={setPrice}
          format={(v) => `S/ ${v}`}
        />
        <SliderField
          label="🍽️ Platos vendidos por día"
          value={platesPerDay}
          min={10}
          max={80}
          step={5}
          onChange={setPlatesPerDay}
        />
        <SliderField
          label="🥘 Costo de insumos (% de ventas)"
          value={costPct}
          min={25}
          max={65}
          step={5}
          onChange={setCostPct}
          format={(v) => `${v}%`}
        />
        <SliderField
          label="🏠 Alquiler mensual"
          value={rent}
          min={1000}
          max={8000}
          step={100}
          onChange={setRent}
          format={(v) => fmtCurrency(v)}
        />
        <SliderField
          label="👥 Sueldos totales"
          value={salaries}
          min={2000}
          max={15000}
          step={100}
          onChange={setSalaries}
          format={(v) => fmtCurrency(v)}
        />
        
        {/* Botón manual para forzar simulación */}
        <div className="pt-2 flex items-center justify-between">
          <span className="text-xs text-brand-text-secondary">
            Los cambios se aplican automáticamente
          </span>
          <button
            onClick={runSimulation}
            disabled={loading || !isAuthenticated}
            className="btn-primary text-sm"
          >
            {loading ? "⏳ Simulando..." : "🔄 Simular Ahora"}
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      )}

      {/* Empty state — simulación aún no ejecutada */}
      {!loading && !error && !result && isAuthenticated && (
        <div className="card text-center py-8 text-brand-text-secondary">
          <span className="text-3xl">🎮</span>
          <p className="mt-2 text-sm">Mové los sliders o presioná "Simular Ahora" para ver resultados.</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card border-brand-error bg-brand-error/5 text-brand-error text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Resultados en vivo */}
      {incomeStmt && (
        <div className="card border-brand-primary/20 bg-gradient-to-br from-brand-primary/5 to-transparent animate-fade-in">
          <h3 className="font-bold text-brand-text-primary mb-4">
            📊 Resultados en Vivo
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <ResultRow label="Ventas mensuales" value={fmtCurrency(incomeStmt.revenue)} />
            <ResultRow label="Costo de ventas" value={fmtCurrency(incomeStmt.cost_of_sales)} />
            <ResultRow label="Utilidad Bruta" value={`${fmtCurrency(incomeStmt.gross_profit)} (${fmtPct(incomeStmt.gross_margin_pct)})`} accent />
            <ResultRow label="Gastos operativos" value={fmtCurrency(Object.values(incomeStmt.operating_expenses).reduce((a, b) => a + b, 0))} />
            <ResultRow label="EBITDA" value={fmtCurrency(incomeStmt.ebitda)} bold />
            <ResultRow label="Utilidad Operativa" value={fmtCurrency(incomeStmt.ebit)} />
            <ResultRow label="Utilidad Neta" value={fmtCurrency(incomeStmt.net_income)} bold accent />
            <ResultRow label="Margen Neto" value={fmtPct(incomeStmt.net_margin_pct)} />
          </div>

          {/* Payback / VAN / TIR */}
          <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-white/70 border border-brand-primary/10">
            <MiniResult
              label="Payback"
              value={paybackRatio ? `${fmtCurrency(paybackRatio.value)} meses` : "—"}
              light={paybackRatio?.traffic_light}
            />
            <MiniResult
              label="VAN"
              value={vanRatio ? fmtCurrency(vanRatio.value) : "—"}
              light={vanRatio?.traffic_light}
            />
            <MiniResult
              label="TIR"
              value={tirRatio ? fmtPct(tirRatio.value) : "—"}
              light={tirRatio?.traffic_light}
            />
          </div>

          <div className="mt-4 flex gap-2">
            <a href="/reportes" className="btn-primary text-sm">📊 Ver PYG</a>
            <a href="/reportes?tab=balance" className="btn-outline text-sm">⚖️ Ver Balance</a>
            <a href="/reportes?tab=ratios" className="btn-ghost text-sm">🚦 Ver Ratios</a>
            <button
              onClick={saveScenario}
              disabled={scenarios.length >= 4}
              className="btn-primary text-sm ml-auto"
              title={scenarios.length >= 4 ? "Máximo 4 escenarios" : "Guardar configuración actual"}
            >
              💾 Guardar Escenario
            </button>
          </div>
        </div>
      )}

      {/* Comparativa de Escenarios */}
      {scenarios.length > 0 && (
        <div className="card animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-brand-text-primary">
              🔍 Comparativa de Escenarios
            </h3>
            <button onClick={clearScenarios} className="btn-ghost text-xs">
              🗑️ Limpiar todo
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-brand-primary/20 text-left text-xs uppercase tracking-wider text-brand-text-secondary">
                  <th className="py-2 pr-3">Variable</th>
                  {scenarios.map((s) => (
                    <th key={s.id} className="py-2 pr-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <span
                          className="w-2.5 h-2.5 rounded-full inline-block"
                          style={{
                            background:
                              s.name === "Realista"
                                ? "var(--color-primary)"
                                : s.name === "Optimista"
                                  ? "var(--color-success)"
                                  : s.name === "Pesimista"
                                    ? "var(--color-error)"
                                    : "var(--color-warning)",
                          }}
                        />
                        {s.name}
                        <button
                          onClick={() => deleteScenario(s.id)}
                          className="text-brand-text-secondary hover:text-brand-error ml-0.5"
                          title="Eliminar"
                        >
                          ×
                        </button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <CompareRow label="Precio por plato" values={scenarios.map((s) => `S/ ${s.price}`)} />
                <CompareRow label="Platos / día" values={scenarios.map((s) => s.platesPerDay.toString())} />
                <CompareRow label="Costo insumos" values={scenarios.map((s) => `${s.costPct}%`)} />
                <CompareRow label="Alquiler" values={scenarios.map((s) => fmtCurrency(s.rent))} />
                <CompareRow label="Sueldos" values={scenarios.map((s) => fmtCurrency(s.salaries))} />
                <CompareSep />
                <CompareRow label="Ventas / mes" values={scenarios.map((s) => fmtCurrency(s.revenue))} bold />
                <CompareRow label="Utilidad Bruta" values={scenarios.map((s) => fmtCurrency(s.grossProfit))} />
                <CompareRow
                  label="Utilidad Neta"
                  values={scenarios.map((s) => fmtCurrency(s.netIncome))}
                  bold
                  accent
                />
                <CompareRow
                  label="Payback"
                  values={scenarios.map((s) => (s.payback ? `${fmtCurrency(s.payback)} meses` : "—"))}
                />
                <CompareRow
                  label="VAN"
                  values={scenarios.map((s) => (s.van ? fmtCurrency(s.van) : "—"))}
                />
                <CompareRow
                  label="TIR"
                  values={scenarios.map((s) => (s.tir ? fmtPct(s.tir) : "—"))}
                />
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Slider ─── */

function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-sm font-medium text-brand-text-primary">{label}</span>
        <span className="text-sm font-bold text-brand-primary tabular-nums">
          {format ? format(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, var(--color-primary) ${pct}%, #e5e7eb ${pct}%)`,
        }}
      />
      <div className="flex justify-between text-[10px] text-brand-text-secondary mt-0.5">
        <span>{format ? format(min) : min}</span>
        <span>{format ? format(max) : max}</span>
      </div>
    </div>
  );
}

/* ─── Result Row ─── */

function ResultRow({
  label,
  value,
  bold,
  accent,
}: {
  label: string;
  value: string;
  bold?: boolean;
  accent?: boolean;
}) {
  return (
    <div className={`flex justify-between items-center py-1.5 px-2 rounded ${bold ? "bg-white/60" : ""}`}>
      <span className="text-sm text-brand-text-secondary">{label}</span>
      <span className={`text-sm font-mono font-semibold ${accent ? "text-brand-accent" : bold ? "text-brand-text-primary" : ""}`}>
        {value}
      </span>
    </div>
  );
}

function MiniResult({
  label,
  value,
  light,
}: {
  label: string;
  value: string;
  light?: string;
}) {
  return (
    <div className="text-center">
      <div className="text-xs text-brand-text-secondary mb-0.5">{label}</div>
      <div className="text-base font-bold text-brand-text-primary">{value}</div>
      {light && <TrafficLight status={light as "green" | "yellow" | "red"} />}
    </div>
  );
}

/* ─── Comparativa ─── */

function CompareRow({
  label,
  values,
  bold,
  accent,
}: {
  label: string;
  values: string[];
  bold?: boolean;
  accent?: boolean;
}) {
  return (
    <tr className={`border-b border-gray-100 ${bold ? "font-semibold" : ""}`}>
      <td className="py-1.5 pr-3 text-brand-text-secondary">{label}</td>
      {values.map((v, i) => (
        <td
          key={i}
          className={`py-1.5 pr-3 text-center font-mono text-xs ${accent ? "text-brand-accent" : ""}`}
        >
          {v}
        </td>
      ))}
    </tr>
  );
}

function CompareSep() {
  return (
    <tr>
      <td colSpan={10} className="py-0.5">
        <hr className="border-gray-200" />
      </td>
    </tr>
  );
}
