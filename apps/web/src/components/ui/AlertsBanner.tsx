/**
 * AlertsBanner — Banner de alertas con severidad visual.
 *
 * Muestra alertas de flujo de caja, inventario, validaciones, etc.
 * con colores semáforo: green (info), yellow (warning), red (critical).
 *
 * HU-F1-007: UI de Flujo de Caja — alertas de vista comparativa
 *
 * @module components/ui/AlertsBanner
 */

export type AlertSeverity = "green" | "yellow" | "red";

export interface CashflowAlert {
  severity: AlertSeverity;
  message: string;
}

interface AlertsBannerProps {
  alerts: CashflowAlert[];
}

const BG_MAP: Record<AlertSeverity, string> = {
  red: "bg-red-50 border-red-300 text-red-800",
  yellow: "bg-yellow-50 border-yellow-300 text-yellow-800",
  green: "bg-green-50 border-green-300 text-green-800",
};

const ICON_MAP: Record<AlertSeverity, string> = {
  red: "🔴",
  yellow: "⚠️",
  green: "✅",
};

export function AlertsBanner({ alerts }: AlertsBannerProps) {
  if (!alerts || alerts.length === 0) return null;

  return (
    <div className="space-y-2" role="alert">
      {alerts.map((alert, i) => (
        <div
          key={i}
          className={`p-3 rounded-lg border text-sm flex items-start gap-2 ${BG_MAP[alert.severity]}`}
        >
          <span className="flex-shrink-0 mt-0.5">{ICON_MAP[alert.severity]}</span>
          <span>{alert.message}</span>
        </div>
      ))}
    </div>
  );
}
