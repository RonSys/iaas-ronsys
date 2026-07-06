/**
 * KPICard, TrafficLight, Skeleton y formateadores.
 *
 * Componentes base reutilizables para construir dashboards financieros.
 *
 * @module dashboard/KPICard
 */
import type { ReactNode } from "react";

/**
 * Tarjeta de indicador clave (KPI) con título, valor, tendencia e ícono.
 *
 * @param title - Etiqueta del indicador (ej. "Ventas")
 * @param value - Valor formateado a mostrar (ej. "S/ 25,000")
 * @param subtitle - Texto secundario opcional debajo del valor
 * @param icon - Emoji o ícono opcional
 * @param trend - Dirección de la tendencia (up/down/neutral)
 * @param trendLabel - Etiqueta de tendencia (ej. "+5%")
 */

interface KPICardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: string;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
}

export function KPICard({ title, value, subtitle, icon, trend, trendLabel }: KPICardProps) {
  const trendColor =
    trend === "up"
      ? "text-brand-success"
      : trend === "down"
        ? "text-brand-error"
        : "text-brand-text-secondary";

  return (
    <div className="card animate-fade-in">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-brand-text-secondary">
          {title}
        </span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-brand-text-primary">{value}</div>
      {(subtitle || trendLabel) && (
        <div className="mt-1.5 flex items-center gap-1.5">
          {trendLabel && (
            <span className={`text-xs font-medium ${trendColor}`}>
              {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"} {trendLabel}
            </span>
          )}
          {subtitle && (
            <span className="text-xs text-brand-text-secondary">{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
}

interface SectionHeaderProps {
  title: string;
  icon?: string;
  children?: ReactNode;
}

export function SectionHeader({ title, icon, children }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-bold text-brand-text-primary flex items-center gap-2">
        {icon && <span>{icon}</span>}
        {title}
      </h2>
      {children}
    </div>
  );
}

/** Semi-circulo para ratios tipo semáforo */
export function TrafficLight({ status }: { status: "green" | "yellow" | "red" }) {
  const label = status === "green" ? "✅" : status === "yellow" ? "⚠️" : "🔴";
  const color =
    status === "green"
      ? "text-brand-success"
      : status === "yellow"
        ? "text-brand-warning"
        : "text-brand-error";
  return (
    <span className={`text-sm font-semibold ${color}`}>
      <span className={`traffic-dot traffic-dot-${status} mr-1.5 align-middle`} />
      {label}
    </span>
  );
}

/** Skeleton loading */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
  );
}

/** Formatea moneda PEN */
export function fmtCurrency(value: number): string {
  return new Intl.NumberFormat("es-PE", {
    style: "currency",
    currency: "PEN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function fmtPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function fmtNum(value: number, decimals = 1): string {
  return value.toLocaleString("es-PE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
