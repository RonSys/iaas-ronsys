/**
 * InvestmentPage — Módulo de Inversión: Puesta en Marcha.
 *
 * Caso 7: Escenarios 1-7
 * - Dashboard con resumen (total estimado, real, diferencia, adquiridos)
 * - Listado de bienes agrupados por categoría
 * - CRUD completo (crear, editar, eliminar)
 * - Vista detalle de cada bien
 * - Solo accesible para admin (protegido en router + sidebar)
 *
 * APIs (vía authFetch):
 *   GET    /api/v1/restaurant/investment
 *   GET    /api/v1/restaurant/investment/summary
 *   POST   /api/v1/restaurant/investment
 *   PUT    /api/v1/restaurant/investment/{id}
 *   DELETE /api/v1/restaurant/investment/{id}
 *
 * @module pages/restaurante/InvestmentPage
 */
import { useState, useEffect, useCallback } from "react";
import { authFetch } from "@/services/authFetch";
import { Skeleton } from "@/components/dashboard/KPICard";
import { InvestmentModal } from "@/components/restaurante/InvestmentModal";
import { InvestmentDetail } from "@/components/restaurante/InvestmentDetail";
import { CATEGORIES } from "@/components/restaurante/InvestmentModal";
import type {
  InvestmentItem,
  InvestmentSummary,
  InvestmentFormData,
} from "@/types";

type ToastType = "success" | "error";

function formatCurrency(value: number): string {
  const absValue = Math.abs(value);
  const formatted = absValue.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return value < 0 ? `-S/${formatted}` : `S/${formatted}`;
}

function getCategoryLabel(value: string): string {
  const cat = CATEGORIES.find((c) => c.value === value);
  return cat ? cat.label.split(" ").slice(1).join(" ") : value;
}

function getCategoryEmoji(value: string): string {
  const cat = CATEGORIES.find((c) => c.value === value);
  return cat ? cat.label.split(" ")[0] : "📦";
}

const defaultSummary: InvestmentSummary = {
  total_estimated: 0,
  total_actual: 0,
  difference: 0,
  acquired_count: 0,
  pending_count: 0,
  total_count: 0,
};

export function InvestmentPage() {
  const [items, setItems] = useState<InvestmentItem[]>([]);
  const [summary, setSummary] = useState<InvestmentSummary>(defaultSummary);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    type: ToastType;
    message: string;
  } | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<InvestmentItem | null>(null);

  // Detail state
  const [detailItem, setDetailItem] = useState<InvestmentItem | null>(null);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<InvestmentItem | null>(null);

  // ─── Toast helper ───
  const showToast = useCallback((type: ToastType, message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  }, []);

  // ─── Fetch items & summary ───
  const fetchData = useCallback(async () => {
    try {
      const [itemsRes, summaryRes] = await Promise.all([
        authFetch("/api/v1/restaurant/investment"),
        authFetch("/api/v1/restaurant/investment/summary"),
      ]);

      if (itemsRes.ok) {
        const data = await itemsRes.json();
        setItems(data.items ?? data ?? []);
      } else {
        const err = await itemsRes.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al cargar bienes");
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
      setError(null);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Error de conexión",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Open create modal ───
  const openCreateModal = () => {
    setEditingItem(null);
    setShowModal(true);
  };

  // ─── Open edit modal ───
  const openEditModal = (item: InvestmentItem) => {
    setEditingItem(item);
    setShowModal(true);
  };

  // ─── Handle save (create / update) ───
  const handleSave = async (data: InvestmentFormData) => {
    if (editingItem) {
      // Update
      const res = await authFetch(
        `/api/v1/restaurant/investment/${editingItem.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al actualizar bien");
      }
      setShowModal(false);
      setEditingItem(null);
      await fetchData();
      showToast("success", `✅ Bien "${data.name}" actualizado`);
    } else {
      // Create
      const res = await authFetch("/api/v1/restaurant/investment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al crear bien");
      }
      setShowModal(false);
      await fetchData();
      showToast("success", `✅ Bien "${data.name}" registrado`);
    }
  };

  // ─── Handle delete ───
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      const res = await authFetch(
        `/api/v1/restaurant/investment/${deleteTarget.id}`,
        { method: "DELETE" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al eliminar bien");
      }
      setDeleteTarget(null);
      await fetchData();
      showToast("success", `🗑️ Bien "${deleteTarget.name}" eliminado`);
    } catch (err: unknown) {
      showToast(
        "error",
        `❌ ${
          err instanceof Error ? err.message : "Error al eliminar"
        }`,
      );
      setDeleteTarget(null);
    }
  };

  // ─── Group items by category ───
  const groupedItems = items.reduce<
    Record<string, InvestmentItem[]>
  >((acc, item) => {
    if (!acc[item.category]) acc[item.category] = [];
    acc[item.category].push(item);
    return acc;
  }, {});

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ─── Toast ─── */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-[100] max-w-sm p-3 rounded-lg shadow-lg text-sm ${
            toast.type === "success"
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* ─── Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            📊 Inversión — Puesta en Marcha
          </h2>
          <p className="text-sm text-brand-text-secondary">
            {items.length}{" "}
            {items.length === 1 ? "bien registrado" : "bienes registrados"}
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          ➕ Agregar Bien
        </button>
      </div>

      {/* ─── Summary Cards ─── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-brand-text-secondary font-medium uppercase tracking-wider">
            Estimado
          </p>
          <p className="text-2xl font-bold text-brand-text-primary mt-1">
            {formatCurrency(summary.total_estimated)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-brand-text-secondary font-medium uppercase tracking-wider">
            Real
          </p>
          <p className="text-2xl font-bold text-brand-text-primary mt-1">
            {formatCurrency(summary.total_actual)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-brand-text-secondary font-medium uppercase tracking-wider">
            Diferencia
          </p>
          <p
            className={`text-2xl font-bold mt-1 ${
              summary.difference >= 0
                ? "text-green-600"
                : "text-red-600"
            }`}
          >
            {formatCurrency(summary.difference)}
          </p>
          <p
            className={`text-xs mt-1 ${
              summary.difference >= 0
                ? "text-green-500"
                : "text-red-500"
            }`}
          >
            {summary.difference >= 0 ? "(ahorro)" : "(exceso)"}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-brand-text-secondary font-medium uppercase tracking-wider">
            Adquiridos
          </p>
          <p className="text-2xl font-bold text-brand-text-primary mt-1">
            {summary.acquired_count} de {summary.total_count}
          </p>
        </div>
      </div>

      {/* ─── Error banner ─── */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button
            onClick={() => setError(null)}
            className="text-xs underline"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* ─── Empty state ─── */}
      {items.length === 0 && !loading && !error && (
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">📦</span>
          <p>No hay bienes registrados. Agrega el primer bien.</p>
          <button
            onClick={openCreateModal}
            className="mt-3 px-4 py-2 bg-brand-primary text-white rounded-lg text-sm"
          >
            ➕ Agregar Primer Bien
          </button>
        </div>
      )}

      {/* ─── Items grouped by category ─── */}
      {items.length > 0 && (
        <div className="space-y-6">
          {Object.entries(groupedItems).map(
            ([category, categoryItems]) => (
              <div key={category}>
                <h3 className="text-sm font-semibold text-brand-text-primary mb-2 flex items-center gap-2">
                  <span>{getCategoryEmoji(category)}</span>
                  <span>{getCategoryLabel(category)}</span>
                  <span className="text-xs text-brand-text-secondary font-normal">
                    ({categoryItems.length})
                  </span>
                </h3>
                <div className="space-y-2">
                  {categoryItems.map((item) => (
                    <div
                      key={item.id}
                      className="bg-white rounded-lg border border-gray-200 p-3 flex items-center justify-between hover:border-brand-primary/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <button
                          onClick={() => setDetailItem(item)}
                          className="text-sm font-medium text-brand-text-primary hover:text-brand-primary text-left"
                        >
                          {item.name}
                        </button>
                        <div className="flex items-center gap-3 mt-1 text-xs text-brand-text-secondary">
                          <span>
                            Est: {formatCurrency(item.estimated_cost)}
                          </span>
                          <span>
                            Real:{" "}
                            {item.actual_cost !== null
                              ? formatCurrency(item.actual_cost)
                              : "—"}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${
                              item.status === "acquired"
                                ? "bg-green-50 text-green-700"
                                : "bg-yellow-50 text-yellow-700"
                            }`}
                          >
                            {item.status === "acquired"
                              ? "🟢 Adquirido"
                              : "🟡 Pendiente"}
                          </span>
                          {item.receipt_code && (
                            <span className="text-gray-400">
                              #{item.receipt_code}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 ml-3 flex-shrink-0">
                        <button
                          onClick={() => openEditModal(item)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-brand-primary transition-colors"
                          title="Editar bien"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => setDeleteTarget(item)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors"
                          title="Eliminar bien"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ),
          )}
        </div>
      )}

      {/* ─── Modal: Create / Edit ─── */}
      <InvestmentModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingItem(null);
        }}
        onSave={handleSave}
        item={editingItem}
      />

      {/* ─── Detail overlay ─── */}
      {detailItem && (
        <InvestmentDetail
          item={detailItem}
          onClose={() => setDetailItem(null)}
        />
      )}

      {/* ─── Delete confirmation ─── */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onKeyDown={(e) => {
            if (e.key === "Escape") setDeleteTarget(null);
            if (e.key === "Enter") handleDeleteConfirm();
          }}
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-brand-text-primary mb-2">
              Confirmar eliminación
            </h3>
            <p className="text-sm text-brand-text-secondary mb-6">
              ¿Eliminar "{deleteTarget.name}"? Esta acción no se puede
              deshacer.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
                autoFocus
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
