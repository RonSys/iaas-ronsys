/**
 * SerialTable — Tabla de seriales con filtro por estado.
 *
 * DT-F0-009 HU-F0-009-04: Registro y CRUD de seriales
 *
 * @module components/inventario/SerialTable
 */

import type { ProductSerial, SerialStatus } from "@/types";
import { fmtCurrency } from "@/components/dashboard/KPICard";

const STATUS_LABELS: Record<SerialStatus, { label: string; color: string }> = {
  available: { label: "Disponible", color: "bg-green-100 text-green-700" },
  reserved: { label: "Reservado", color: "bg-yellow-100 text-yellow-700" },
  sold: { label: "Vendido", color: "bg-blue-100 text-blue-700" },
  voided: { label: "Anulado", color: "bg-red-100 text-red-700" },
  returned: { label: "Devuelto", color: "bg-orange-100 text-orange-700" },
  warranty: { label: "Garantía", color: "bg-purple-100 text-purple-700" },
};

const ALL_STATUSES: (SerialStatus | "all")[] = [
  "all",
  "available",
  "reserved",
  "sold",
  "voided",
  "returned",
  "warranty",
];

interface SerialTableProps {
  serials: ProductSerial[];
  loading: boolean;
  statusFilter: SerialStatus | undefined;
  onStatusFilterChange: (status: SerialStatus | undefined) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export function SerialTable({
  serials,
  loading,
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchChange,
}: SerialTableProps) {
  if (loading && serials.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex gap-1 flex-wrap">
          {ALL_STATUSES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onStatusFilterChange(s === "all" ? undefined : s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${(s === "all" && !statusFilter) || s === statusFilter
                  ? "bg-brand-primary text-white"
                  : "bg-gray-100 text-brand-text-secondary hover:bg-gray-200"
                }`}
            >
              {s === "all" ? "Todos" : STATUS_LABELS[s]?.label ?? s}
            </button>
          ))}
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Buscar serial..."
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm flex-1 max-w-xs focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        />
      </div>

      {/* Tabla */}
      {serials.length === 0 ? (
        <div className="p-8 text-center text-brand-text-secondary">
          <span className="text-3xl block mb-2">🔢</span>
          <p className="text-sm">No se encontraron seriales</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-brand-text-secondary">
                <th className="py-2 px-3 font-medium">N° Serie</th>
                <th className="py-2 px-3 font-medium">Estado</th>
                <th className="py-2 px-3 font-medium hidden sm:table-cell">Fecha Compra</th>
                <th className="py-2 px-3 font-medium text-right hidden md:table-cell">Costo</th>
                <th className="py-2 px-3 font-medium hidden lg:table-cell">Garantía</th>
                <th className="py-2 px-3 font-medium hidden xl:table-cell">Venta</th>
              </tr>
            </thead>
            <tbody>
              {serials.map((serial) => {
                const st = STATUS_LABELS[serial.status] ?? {
                  label: serial.status,
                  color: "bg-gray-100 text-gray-700",
                };

                return (
                  <tr
                    key={serial.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="py-2 px-3">
                      <span className="font-mono text-xs font-medium text-brand-text-primary">
                        {serial.serial_number}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${st.color}`}>
                        {st.label}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-brand-text-secondary text-xs hidden sm:table-cell">
                      {serial.purchase_date
                        ? new Date(serial.purchase_date).toLocaleDateString("es-PE")
                        : "—"}
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-xs hidden md:table-cell">
                      {serial.cost_price != null ? fmtCurrency(serial.cost_price) : "—"}
                    </td>
                    <td className="py-2 px-3 hidden lg:table-cell">
                      {serial.warranty_expiry ? (
                        (() => {
                          const daysLeft = Math.ceil(
                            (new Date(serial.warranty_expiry).getTime() - Date.now()) /
                              (1000 * 60 * 60 * 24),
                          );
                          return (
                            <span
                              className={`text-xs ${
                                daysLeft <= 0
                                  ? "text-red-600"
                                  : daysLeft <= 30
                                    ? "text-yellow-600"
                                    : "text-green-600"
                              }`}
                            >
                              {daysLeft <= 0
                                ? "Vencida"
                                : `${daysLeft} días`}
                            </span>
                          );
                        })()
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3 hidden xl:table-cell">
                      {serial.sale_id ? (
                        <span className="text-xs text-brand-primary font-mono">
                          #{serial.sale_id}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
