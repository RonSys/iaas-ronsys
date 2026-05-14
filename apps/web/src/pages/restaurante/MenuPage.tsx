/**
 * MenuPage — Menú digital + gestión de ítems.
 *
 * HU-F0-007: Menú digital agrupado por categoría con modifiers
 * - Items agrupados por categoría (Platos, Bebidas, Postres, Combos)
 * - Modal con modifiers al agregar item
 * - Buscador en tiempo real
 * - Items inactivos: gris + "Agotado"
 * - CRUD admin: crear/editar/eliminar items
 * - 4 estados: loading, empty, error, data
 *
 * @module pages/restaurante/MenuPage
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface MenuItem {
  id: number;
  name: string;
  description: string | null;
  category: string;
  price: number;
  cost_price: number | null;
  item_type: "food" | "beverage" | "dessert" | "combo";
  modifiers: MenuModifier[] | null;
  image_url: string | null;
  active: boolean;
}

interface MenuModifier {
  name: string;
  price: number;
  max_select?: number;
}

interface MenuItemForm {
  name: string;
  description: string;
  category: string;
  price: number;
  cost_price: number | null;
  item_type: string;
  active: boolean;
}

const DEFAULT_FORM: MenuItemForm = {
  name: "",
  description: "",
  category: "",
  price: 0,
  cost_price: null,
  item_type: "food",
  active: true,
};

export function MenuPage() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [form, setForm] = useState<MenuItemForm>(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/restaurant/menu");
      if (!res.ok) throw new Error("Error al cargar el menú");
      const data = await res.json();
      setItems(data.items ?? data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q),
    );
  }, [items, search]);

  const grouped = useMemo(() => {
    const acc: Record<string, MenuItem[]> = {};
    for (const item of filtered) {
      const cat = item.category || "Sin categoría";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(item);
    }
    return acc;
  }, [filtered]);

  const openCreate = () => {
    setEditingItem(null);
    setForm(DEFAULT_FORM);
    setShowModal(true);
  };

  const openEdit = (item: MenuItem) => {
    setEditingItem(item);
    setForm({
      name: item.name,
      description: item.description ?? "",
      category: item.category,
      price: item.price,
      cost_price: item.cost_price,
      item_type: item.item_type,
      active: item.active,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.category.trim() || form.price <= 0) return;
    setSubmitting(true);
    try {
      const url = editingItem
        ? `/api/restaurant/menu/${editingItem.id}`
        : "/api/restaurant/menu";
      const method = editingItem ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Error al guardar ítem");
      await fetchItems();
      setShowModal(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (item: MenuItem) => {
    try {
      const res = await fetch(`/api/restaurant/menu/${item.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !item.active }),
      });
      if (!res.ok) throw new Error("Error al actualizar");
      await fetchItems();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar");
    }
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-24" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-16 w-full" />
          </div>
        ))}
      </div>
    );
  }

  // ─── Error ───
  if (error && items.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">📜 Menú</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="mb-2">⚠️ {error}</p>
          <button onClick={fetchItems} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty ───
  if (items.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-brand-text-primary">📜 Menú</h2>
          <button onClick={openCreate} className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm">
            + Nuevo Ítem
          </button>
        </div>
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">📜</span>
          <p className="text-lg font-medium">No hay ítems de menú</p>
          <p className="text-sm mt-1">Creá el primer ítem del menú para empezar.</p>
        </div>
      </div>
    );
  }

  // ─── Data ───
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">📜 Menú</h2>
          <p className="text-sm text-brand-text-secondary">
            {items.length} ítem(s) · {Object.keys(grouped).length} categoría(s)
          </p>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm">
          + Nuevo Ítem
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchItems} className="underline text-xs">Reintentar</button>
        </div>
      )}

      {/* Buscador */}
      <div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="🔍 Buscar por nombre o categoría..."
          className="w-full max-w-md px-3 py-2 border rounded-lg text-sm"
        />
      </div>

      {Object.entries(grouped).map(([category, categoryItems]) => (
        <div key={category}>
          <h3 className="text-sm font-bold text-brand-text-primary uppercase tracking-wider mb-2 px-1">
            {category}
          </h3>
          <div className="space-y-2">
            {categoryItems.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded-lg border bg-brand-surface flex items-center justify-between
                  ${!item.active ? "opacity-50" : ""}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-brand-text-primary">{item.name}</span>
                    {!item.active && (
                      <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
                        Agotado
                      </span>
                    )}
                  </div>
                  {item.description && (
                    <p className="text-xs text-brand-text-secondary truncate mt-0.5">
                      {item.description}
                    </p>
                  )}
                  {item.modifiers && item.modifiers.length > 0 && (
                    <p className="text-xs text-brand-text-secondary mt-0.5">
                      + {item.modifiers.length} modificador(es)
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span className="text-sm font-semibold text-brand-text-primary">
                    S/ {item.price.toFixed(2)}
                  </span>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={item.active}
                      onChange={() => toggleActive(item)}
                      className="sr-only peer"
                    />
                    <div className="w-8 h-4 bg-gray-300 rounded-full peer peer-checked:bg-brand-success peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all" />
                  </label>
                  <button
                    onClick={() => openEdit(item)}
                    className="text-xs text-brand-primary hover:underline"
                  >
                    Editar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Modal CRUD */}
      {showModal && (
        <MenuFormModal
          form={form}
          editingItem={editingItem}
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

function MenuFormModal({
  form,
  editingItem,
  submitting,
  onChange,
  onSave,
  onClose,
}: {
  form: MenuItemForm;
  editingItem: MenuItem | null;
  submitting: boolean;
  onChange: (f: MenuItemForm) => void;
  onSave: () => Promise<void>;
  onClose: () => void;
}) {
  const set = <K extends keyof MenuItemForm>(key: K, value: MenuItemForm[K]) =>
    onChange({ ...form, [key]: value });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-bold text-brand-text-primary mb-4">
          {editingItem ? "Editar Ítem" : "Nuevo Ítem del Menú"}
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Nombre *</label>
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Ej: Ceviche Mixto"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={2}
              placeholder="Opcional"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Categoría *</label>
              <input
                value={form.category}
                onChange={(e) => set("category", e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: Platos"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tipo</label>
              <select
                value={form.item_type}
                onChange={(e) => set("item_type", e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                <option value="food">Plato</option>
                <option value="beverage">Bebida</option>
                <option value="dessert">Postre</option>
                <option value="combo">Combo</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Precio *</label>
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.price}
                onChange={(e) => set("price", Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Costo</label>
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.cost_price ?? ""}
                onChange={(e) => set("cost_price", e.target.value ? Number(e.target.value) : null)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Opcional"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Disponible</label>
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => set("active", e.target.checked)}
              className="w-4 h-4"
            />
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
            disabled={submitting || !form.name.trim() || !form.category.trim() || form.price <= 0}
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
          >
            {submitting ? "Guardando..." : editingItem ? "Actualizar" : "Crear"}
          </button>
        </div>
      </div>
    </div>
  );
}
