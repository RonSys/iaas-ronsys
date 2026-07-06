/**
 * SerialTraceabilityPanel — Timeline de trazabilidad de un serial.
 *
 * DT-F0-009 HU-F0-009-06: Trazabilidad de seriales
 *
 * Muestra el ciclo de vida completo de un serial:
 * - Línea de tiempo cronológica (registrado → vendido → anulado → ...)
 * - Garantía vigente/vencida
 * - Botón de búsqueda por número de serie
 *
 * @module components/inventario/SerialTraceabilityPanel
 */

import { useState, type FormEvent } from "react";
import type { SerialTraceability } from "@/types";
import { getSerialTraceability } from "@/services/inventoryApi";

interface SerialTraceabilityPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SerialTraceabilityPanel({
  isOpen,
  onClose,
}: SerialTraceabilityPanelProps) {
  const [serialNumber, setSerialNumber] = useState("");
  const [trace, setTrace] = useState<SerialTraceability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!serialNumber.trim()) return;

    setLoading(true);
    setError(null);
    setTrace(null);
    try {
      const data = await getSerialTraceability(serialNumber.trim());
      setTrace(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "No se encontró el serial");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Calcular días de garantía
  const warrantyDays = trace?.warranty_expiry
    ? Math.ceil(
        (new Date(trace.warranty_expiry).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24),
      )
    : null;

  const isWarrantyActive = warrantyDays !== null && warrantyDays > 0;
  const isWarrantyExpiringSoon = warrantyDays !== null && warrantyDays > 0 && warrantyDays <= 30;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-[5vh] overflow-y-auto">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl my-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-brand-text-primary">
            🔍 Trazabilidad de Serial
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-brand-text-secondary"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <input
            type="text"
            value={serialNumber}
            onChange={(e) => setSerialNumber(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
            placeholder="Buscar número de serie..."
            autoFocus
          />
          <button
            type="submit"
            disabled={loading || !serialNumber.trim()}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary disabled:opacity-50"
          >
            {loading ? "..." : "Buscar"}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3 py-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {/* Result */}
        {trace && (
          <div className="space-y-4">
            {/* Info header */}
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-brand-text-secondary">Producto:</span>
                  <p className="font-medium text-brand-text-primary">{trace.product_name}</p>
                </div>
                <div>
                  <span className="text-brand-text-secondary">N° Serie:</span>
                  <p className="font-mono text-xs font-medium text-brand-text-primary">
                    {trace.serial_number}
                  </p>
                </div>
                {trace.manufacturer && (
                  <div>
                    <span className="text-brand-text-secondary">Fabricante:</span>
                    <p className="text-brand-text-primary">{trace.manufacturer}</p>
                  </div>
                )}
                <div>
                  <span className="text-brand-text-secondary">Estado:</span>
                  <p className="font-medium text-brand-text-primary capitalize">
                    {trace.current_status}
                  </p>
                </div>
              </div>

              {/* Garantía */}
              <div className="mt-3 pt-3 border-t border-gray-200">
                {warrantyDays !== null ? (
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium
                        ${isWarrantyExpiringSoon
                          ? "bg-yellow-100 text-yellow-700"
                          : isWarrantyActive
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                    >
                      {isWarrantyExpiringSoon
                        ? `⚠️ ${warrantyDays} días restantes`
                        : isWarrantyActive
                          ? `✅ Vigente (${warrantyDays} días)`
                          : "❌ Vencida"}
                    </span>
                    <span className="text-xs text-brand-text-secondary">
                      Hasta: {new Date(trace.warranty_expiry!).toLocaleDateString("es-PE")}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-brand-text-secondary">Sin garantía</span>
                )}
              </div>
            </div>

            {/* Timeline */}
            <div>
              <h4 className="text-sm font-medium text-brand-text-primary mb-3">
                📅 Historial
              </h4>
              <div className="relative pl-6">
                {/* Línea vertical */}
                <div className="absolute left-2.5 top-1 bottom-1 w-0.5 bg-gray-200" />

                <div className="space-y-4">
                  {trace.events.map((event, idx) => (
                    <div key={idx} className="relative">
                      {/* Punto en la línea */}
                      <div
                        className={`absolute -left-[calc(1.5rem-3px)] top-1 w-3 h-3 rounded-full border-2 border-white
                          ${event.event_type === "registered"
                            ? "bg-blue-500"
                            : event.event_type === "sold"
                              ? "bg-green-500"
                              : event.event_type === "voided"
                                ? "bg-red-500"
                                : event.event_type === "returned"
                                  ? "bg-orange-500"
                                  : "bg-purple-500"
                          }`}
                      />

                      <div className="ml-1">
                        <div className="text-xs text-brand-text-secondary">
                          {new Date(event.timestamp).toLocaleString("es-PE", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })}
                        </div>
                        <p className="text-sm text-brand-text-primary font-medium">
                          {event.description}
                        </p>
                        <div className="flex gap-3 text-xs text-brand-text-secondary mt-0.5">
                          {event.sale_number && (
                            <span>
                              Venta:{" "}
                              <span className="font-mono text-brand-primary">
                                {event.sale_number}
                              </span>
                            </span>
                          )}
                          {event.customer_name && (
                            <span>
                              Cliente: {event.customer_name}
                            </span>
                          )}
                          {event.user_name && (
                            <span>
                              Usuario: {event.user_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!trace && !loading && !error && (
          <div className="p-8 text-center text-brand-text-secondary">
            <span className="text-4xl block mb-3">🔢</span>
            <p className="text-sm">Ingresa un número de serie para ver su trazabilidad</p>
          </div>
        )}
      </div>
    </div>
  );
}
