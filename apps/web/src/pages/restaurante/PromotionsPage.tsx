/**
 * PromotionsPage — Gestión de promociones.
 *
 * HU-F0-009: CRUD de promociones con tipos combo, descuento %, fijo, BOGOF
 * - Listado de promociones activas con vigencia
 * - Formulario de creación/edición
 * - Desactivar promoción
 *
 * @module pages/restaurante/PromotionsPage
 */
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface Promotion {
  id: number;
  name: string;
  description: string | null;
  promo_type: "combo" | "discount_pct" | "discount_fixed" | "bogof";
  rules: Record<string, unknown> | null;
  discount_value: number;
  valid_from: string;
  valid_to: string;
  active: boolean;
}

const PROMO_TYPE_LABELS: Record<Promotion["promo_type"], string> = {
  combo: "Combo",
  discount_pct: "Descuento %",
  discount_fixed: "Descuento Fijo",
  bogof: "2x1 (BOGOF)",
};

export function PromotionsPage() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Promotion | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    promo_type: "discount_pct" as Promotion["promo_type"],
    discount_value: 0,
    valid_from: new Date().toISOString().split("T")[0],
    valid_to: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchPromotions = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/restaurant/promotions");
      if (!res.ok) throw new Error("Error al cargar promociones");
      const data = await res.json();
      setPromotions(data.promotions ?? data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPromotions();
  }, [fetchPromotions]);

  const openCreate = () => {
    setEditing(null);
    setForm({
      name: "",
      description: "",
      promo_type: "discount_pct",
      discount_value: 0,
      valid_from: new Date().toISOString().split("T")[0],
      valid_to: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
    });
    setShowModal(true);
  };

  const openEdit = (p: Promotion) => {
    setEditing(p);
    setForm({
      name: p.name,
      description: p.description ?? "",
      promo_type: p.promo_type,
      discount_value: p.discount_value,
      valid_from: p.valid_from,
      valid_to: p.valid_to,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSubmitting(true);
    try {
      const url = editing
        ? `/api/v1/restaurant/promotions/${editing.id}`
        : "/api/v1/restaurant/promotions";
      const method = editing ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Error al guardar");
      await fetchPromotions();
      setShowModal(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (p: Promotion) => {
    try {
      const res = await fetch(`/api/v1/restaurant/promotions/${p.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !p.active }),
      });
      if (!res.ok) throw new Error("Error al actualizar");
      await fetchPromotions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    }
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Promociones</h2>
          <p className="text-sm text-brand-text-secondary">
            {promotions.filter((p) => p.active).length} activas · {promotions.length} total
          </p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          + Nueva Promoción
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchPromotions} className="underline text-xs">Reintentar</button>
        </div>
      )}

      {promotions.length === 0 ? (
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🏷️</span>
          <p className="text-lg font-medium">No hay promociones</p>
          <p className="text-sm mt-1">Creá promociones para combos, descuentos y ofertas.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {promotions.map((p) => (
            <div
              key={p.id}
              className={`p-4 rounded-lg border bg-brand-surface flex items-center justify-between
                ${!p.active ? "opacity-50" : ""}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-brand-text-primary">{p.name}</span>
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                    {PROMO_TYPE_LABELS[p.promo_type]}
                  </span>
                  {!p.active && (
                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                      Inactiva
                    </span>
                  )}
                </div>
                {p.description && (
                  <p className="text-xs text-brand-text-secondary mt-0.5">{p.description}</p>
                )}
                <p className="text-xs text-brand-text-secondary mt-0.5">
                  {p.promo_type === "discount_pct"
                    ? `${p.discount_value}% descuento`
                    : p.promo_type === "discount_fixed"
                      ? `S/ ${p.discount_value.toFixed(2)} descuento`
                      : p.promo_type === "combo"
                        ? `Precio combo: S/ ${p.discount_value.toFixed(2)}`
                        : "2x1"}
                  {" · "}
                  {formatDate(p.valid_from)} → {formatDate(p.valid_to)}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => toggleActive(p)}
                  className={`text-xs px-2 py-1 rounded ${
                    p.active
                      ? "bg-red-100 text-red-600 hover:bg-red-200"
                      : "bg-green-100 text-green-600 hover:bg-green-200"
                  }`}
                >
                  {p.active ? "Desactivar" : "Activar"}
                </button>
                <button
                  onClick={() => openEdit(p)}
                  className="text-xs text-brand-primary hover:underline"
                >
                  Editar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              {editing ? "Editar Promoción" : "Nueva Promoción"}
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Nombre *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Ej: Happy Hour"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Descripción</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Opcional"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Tipo</label>
                <select
                  value={form.promo_type}
                  onChange={(e) =>
                    setForm({ ...form, promo_type: e.target.value as Promotion["promo_type"] })
                  }
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                >
                  {Object.entries(PROMO_TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  {form.promo_type === "discount_pct"
                    ? "Porcentaje de Descuento"
                    : form.promo_type === "combo"
                      ? "Precio del Combo (S/)"
                      : "Valor del Descuento (S/)"}
                </label>
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  value={form.discount_value}
                  onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Desde</label>
                  <input
                    type="date"
                    value={form.valid_from}
                    onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Hasta</label>
                  <input
                    type="date"
                    value={form.valid_to}
                    onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={submitting || !form.name.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
              >
                {submitting ? "Guardando..." : editing ? "Actualizar" : "Crear"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
