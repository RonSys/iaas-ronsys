/**
 * SerialPanel — Panel de gestión de seriales (modal/panel lateral).
 *
 * DT-F0-009 HU-F0-009-04: Gestión de seriales por producto
 *
 * Combina SerialTable + SerialBatchForm en un panel con tabs:
 * - "Ver Seriales": tabla con filtro por estado
 * - "Registrar Seriales": formulario de lote
 *
 * @module components/inventario/SerialPanel
 */

import { useState, useCallback, useEffect } from "react";
import type { ProductResponse, ProductSerial, SerialStatus, SerialCreateRequest } from "@/types";
import { getSerials, createSerialBatch } from "@/services/inventoryApi";
import { SerialTable } from "./SerialTable";
import { SerialBatchForm } from "./SerialBatchForm";

type Tab = "view" | "register";

interface SerialPanelProps {
  product: ProductResponse;
  isOpen: boolean;
  onClose: () => void;
}

export function SerialPanel({ product, isOpen, onClose }: SerialPanelProps) {
  const [tab, setTab] = useState<Tab>("view");
  const [serials, setSerials] = useState<ProductSerial[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SerialStatus | undefined>();
  const [searchQuery, setSearchQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchSerials = useCallback(async () => {
    if (!isOpen) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSerials(product.id, {
        status: statusFilter,
        search: searchQuery || undefined,
      });
      setSerials(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al cargar seriales");
      setSerials([]);
    } finally {
      setLoading(false);
    }
  }, [isOpen, product.id, statusFilter, searchQuery]);

  useEffect(() => {
    fetchSerials();
  }, [fetchSerials]);

  const handleRegisterSerial = async (data: SerialCreateRequest[]) => {
    setSubmitting(true);
    setError(null);
    try {
      await createSerialBatch(product.id, { serials: data });
      setTab("view");
      await fetchSerials();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al registrar seriales");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-[5vh] overflow-y-auto">
      <div className="bg-white rounded-xl p-6 w-full max-w-4xl mx-4 shadow-xl my-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-brand-text-primary">
              🔢 Seriales: {product.name}
            </h3>
            <p className="text-xs text-brand-text-secondary">
              {product.serial_total_count ?? serials.length} seriales totales ·{" "}
              {product.serial_available_count ?? serials.filter((s) => s.status === "available").length} disponibles
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-brand-text-secondary"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            ⚠️ {error}
            <button onClick={fetchSerials} className="ml-2 underline text-xs">
              Reintentar
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-4 border-b pb-2">
          <button
            type="button"
            onClick={() => setTab("view")}
            className={`px-3 py-1.5 rounded-t-lg text-sm font-medium transition-colors
              ${tab === "view"
                ? "bg-brand-primary/10 text-brand-primary border-b-2 border-brand-primary"
                : "text-brand-text-secondary hover:text-brand-text-primary"
              }`}
          >
            📋 Ver Seriales
          </button>
          <button
            type="button"
            onClick={() => setTab("register")}
            className={`px-3 py-1.5 rounded-t-lg text-sm font-medium transition-colors
              ${tab === "register"
                ? "bg-brand-primary/10 text-brand-primary border-b-2 border-brand-primary"
                : "text-brand-text-secondary hover:text-brand-text-primary"
              }`}
          >
            ➕ Registrar Seriales
          </button>
        </div>

        {/* Tab Content */}
        {tab === "view" && (
          <SerialTable
            serials={serials}
            loading={loading}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        )}

        {tab === "register" && (
          <SerialBatchForm
            productName={product.name}
            defaultWarrantyMonths={product.warranty_months ?? 0}
            submitting={submitting}
            onSave={handleRegisterSerial}
            onCancel={() => setTab("view")}
          />
        )}
      </div>
    </div>
  );
}
