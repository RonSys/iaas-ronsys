/**
 * PromotionsPage — Gestión de promociones del restaurante.
 *
 * HU-F0-014: Listado y CRUD de promociones
 * - Combos, descuentos fijos y porcentuales
 * - Toggle activar/desactivar
 * - Modal de creación/edición
 *
 * @module pages/restaurant/PromotionsPage
 */
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

type PromotionType = "combo" | "fixed_discount" | "percentage_discount" | "happy_hour";

interface Promotion {
  id: number;
  name: string;
  type: PromotionType;
  discount_value: number;
  conditions: {
    min_items?: number;
    min_amount?: number;
    applicable_categories?: string[];
    applicable_menu_item_ids?: number[];
  };
  start_date: string;
  end_date: string | null;
  active: boolean;
  max_uses: number | null;
  current_uses: number;
}

interface PromotionForm {
  name: string;
  type: PromotionType;
  discount_value: number;
  conditions: string;
  start_date: string;
  end_date: string;
  active: boolean;
  max_uses: number | null;
}

const TYPE_LABELS: Record<PromotionType, string> = {
  combo: "Combo",
  fixed_discount: "Descuento Fijo",
  percentage_discount: "Descuento %",
  happy_hour: "Happy Hour",
};

const INITIAL_FORM: PromotionForm = {
  name: "",
  type: "fixed_discount",
  discount_value: 0,
  conditions: "",
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  active: true,
  max_uses: null,
};

export function PromotionsPage() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Promotion | null>(null);
  const [form, setForm] = useState<PromotionForm>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);

  const fetchPromotions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/restaurant/promotions");
      if (!res.ok) throw new Error("Error al cargar promociones");
      const data = await res.json();
      setPromotions(data.promotions ?? data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
      setPromotions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPromotions();
  }, [fetchPromotions]);

  const openCreate = () => {
    setEditing(null);
    setForm(INITIAL_FORM);
    setShowModal(true);
  };

  const openEdit = (p: Promotion) => {
    setEditing(p);
    setForm({
      name: p.name,
      type: p.type,
      discount_value: p.discount_value,
      conditions: JSON.stringify(p.conditions, null, 2),
      start_date: p.start_date.slice(0, 10),
      end_date: p.end_date ? p.end_date.slice(0, 10) : "",
      active: p.active,
      max_uses: p.max_uses,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || form.discount_value <= 0) return;
    setSubmitting(true);
    try {
      let conditions: Record<string, unknown> = {};
      try {
        conditions = JSON.parse(form.conditions || "{}");
      } catch {
        conditions = {};
      }

      const payload = {
        ...form,
        conditions,
        end_date: form.end_date || null,
        max_uses: form.max_uses,
      };

      const url = editing
        ? `/api/v1/restaurant/promotions/${editing.id}`
        : "/api/v1/restaurant/promotions";
      const method = editing ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !p.active }),
      });
      if (!res.ok) throw new Error("Error al cambiar estado");
      await fetchPromotions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar");
    }
  };

  const isExpired = (p: Promotion) =>
    p.end_date && new Date(p.end_date) < new Date();

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  // ─── Error ───
  if (error && promotions.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Promociones</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="text-lg mb-2">⚠️ {error}</p>
          <button onClick={fetchPromotions} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty ───
  if (promotions.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Promociones</h2>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
          >
            + Nueva Promoción
          </button>
        </div>
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🏷️</span>
          <p className="text-lg font-medium">No hay promociones</p>
          <p className="text-sm mt-1">Creá la primera promoción para empezar.</p>
        </div>
      </div>
    );
  }

  // ─── Data ───
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Promociones</h2>
          <p className="text-sm text-brand-text-secondary">
            {promotions.filter((p) => p.active && !isExpired(p)).length} activa(s)
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
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-2">
        {promotions.map((p) => {
          const expired = isExpired(p);
          return (
            <div
              key={p.id}
              className={`p-4 rounded-lg border bg-brand-surface flex items-center justify-between gap-3
                ${!p.active || expired ? "opacity-60" : ""}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-brand-text-primary">{p.name}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                    {TYPE_LABELS[p.type]}
                  </span>
                  {expired && (
                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                      Expirada
                    </span>
                  )}
                </div>
                <div className="text-xs text-brand-text-secondary mt-1">
                  {p.type === "percentage_discount"
                    ? `${p.discount_value}% de descuento`
                    : `S/ ${p.discount_value.toFixed(2)} de descuento`}
                  {" · "}
                  {new Date(p.start_date).toLocaleDateString("es-PE")}
                  {p.end_date
                    ? ` → ${new Date(p.end_date).toLocaleDateString("es-PE")}`
                    : " · Sin fecha fin"}
                  {p.max_uses && ` · ${p.current_uses}/${p.max_uses} usos`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={p.active}
                    onChange={() => toggleActive(p)}
                    className="sr-only peer"
                  />
                  <div className="w-8 h-4 bg-gray-300 rounded-full peer peer-checked:bg-brand-success peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all" />
                </label>
                <button
                  onClick={() => openEdit(p)}
                  className="text-xs text-brand-primary hover:underline"
                >
                  Editar
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal */}
      {showModal && (
        <PromotionFormModal
          form={form}
          editing={editing}
          submitting={submitting}
          onChange={setForm}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}

// ─── Modal ───

function PromotionFormModal({
  form,
  editing,
  submitting,
  onChange,
  onSave,
  onClose,
}: {
  form: PromotionForm;
  editing: Promotion | null;
  submitting: boolean;
  onChange: (f: PromotionForm) => void;
  onSave: () => Promise<void>;
  onClose: () => void;
}) {
  const set = <K extends keyof PromotionForm>(key: K, value: PromotionForm[K]) =>
    onChange({ ...form, [key]: value });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-bold text-brand-text-primary mb-4">
          {editing ? "Editar Promoción" : "Nueva Promoción"}
        </h3>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Nombre *</label>
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Ej: 2x1 en Ceviche"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tipo</label>
            <select
              value={form.type}
              onChange={(e) => set("type", e.target.value as PromotionType)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              {Object.entries(TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Valor del descuento {form.type === "percentage_discount" ? "(%)" : "(S/)"} *
            </label>
            <input
              type="number"
              step="0.01"
              min={0}
              value={form.discount_value}
              onChange={(e) => set("discount_value", Number(e.target.value))}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Fecha inicio *</label>
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => set("start_date", e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fecha fin</label>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => set("end_date", e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Límite de usos (vacío = sin límite)
            </label>
            <input
              type="number"
              min={1}
              value={form.max_uses ?? ""}
              onChange={(e) =>
                set("max_uses", e.target.value ? Number(e.target.value) : null)
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Condiciones (JSON)
            </label>
            <textarea
              value={form.conditions}
              onChange={(e) => set("conditions", e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm font-mono text-xs"
              rows={3}
              placeholder='{"min_items": 2, "min_amount": 50}'
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => set("active", e.target.checked)}
              className="w-4 h-4"
            />
            <label className="text-sm font-medium">Activa</label>
          </div>
        </div>

        <div className="flex gap-2 justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
            disabled={submitting}
          >
            Cancelar
          </button>
          <button
            onClick={onSave}
            disabled={submitting || !form.name.trim() || form.discount_value <= 0}
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
              hover:bg-brand-secondary disabled:opacity-50"
          >
            {submitting ? "Guardando..." : editing ? "Actualizar" : "Crear"}
          </button>
        </div>
      </div>
    </div>
  );
}
