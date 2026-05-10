/**
 * Gráficos de flujo de caja con Recharts.
 *
 * Componentes para visualizar la proyección financiera:
 * - CashflowBarChart: barras de ingresos vs egresos mensuales
 * - CashflowLineChart: líneas de saldo mensual y flujo acumulado
 * - generateCashflowData: helper para generar datos desde resúmenes
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
import { fmtCurrency } from "./KPICard";

export interface CashflowDataPoint {
  month: string;
  ingresos: number;
  egresos: number;
  saldo: number;
  acumulado: number;
}

interface CashflowChartProps {
  data: CashflowDataPoint[];
  title?: string;
}

/** Genera datos de flujo de caja proyectado a partir del resumen mensual */
export function generateCashflowData(
  monthlyRevenue: number,
  monthlyCostPct: number,
  monthlyFixedCosts: number,
  months: number = 12,
): CashflowDataPoint[] {
  const monthNames = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
  ];

  const costOfSales = monthlyRevenue * monthlyCostPct;
  const egresos = costOfSales + monthlyFixedCosts;
  const saldo = monthlyRevenue - egresos;

  let acumulado = 0;
  return Array.from({ length: months }, (_, i) => {
    acumulado += saldo;
    return {
      month: monthNames[i % 12],
      ingresos: monthlyRevenue,
      egresos,
      saldo,
      acumulado,
    };
  });
}

export function CashflowBarChart({ data, title }: CashflowChartProps) {
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

export function CashflowLineChart({ data, title }: CashflowChartProps) {
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
