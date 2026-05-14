/**
 * CategoriesPage — Gestión de categorías de productos.
 *
 * HU-F0-013 / F0-015: CRUD de categorías con soporte jerárquico
 * - Crear, editar, eliminar categorías
 * - Validación: no eliminar si tiene productos asignados
 * - Soporte para parent_id (jerarquía futura)
 * - 4 estados: loading, empty, error, data
 *
 * @module pages/ferreteria/CategoriesPage
 */
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface ProductCategory {
  id: number;
  name: string;
  description?: string | null;
  parent_id?: number | null;
  active?: boolean;
  sort_order?: number;
  product_count?: number;
}

export function CategoriesPage() {
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ProductCategory | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [categoryDescription, setCategoryDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/inventory/categories");
      if (!res.ok) throw new Error("Error al cargar categorías");
      const data = await res.json();
      setCategories(data.categories ?? data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const openCreate = () => {
    setEditing(null);
    setCategoryName("");
    setCategoryDescription("");
    setShowModal(true);
  };

  const openEdit = (cat: ProductCategory) => {
    setEditing(cat);
    setCategoryName(cat.name);
    setCategoryDescription(cat.description ?? "");
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!categoryName.trim()) return;
    setSubmitting(true);
    try {
      const url = editing
        ? `/api/v1/inventory/categories/${editing.id}`
        : "/api/v1/inventory/categories";
      const method = editing ? "PATCH" : "POST";
      const body: Record<string, unknown> = { name: categoryName.trim() };
      if (categoryDescription.trim()) {
        body.description = categoryDescription.trim();
      }
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Error al guardar");
      await fetchCategories();
      setShowModal(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (cat: ProductCategory) => {
    if (!window.confirm(`¿Eliminar categoría "${cat.name}"?`)) return;
    try {
      const res = await fetch(`/api/v1/inventory/categories/${cat.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        if (res.status === 409) {
          setError("Categoría con productos asignados");
          return;
        }
        throw new Error("Error al eliminar");
      }
      await fetchCategories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  // ─── Error ───
  if (error && categories.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Categorías</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="mb-2">⚠️ {error}</p>
          <button onClick={fetchCategories} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty ───
  if (categories.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Categorías</h2>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
          >
            + Nueva Categoría
          </button>
        </div>
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🏷️</span>
          <p className="text-lg font-medium">No hay categorías</p>
          <p className="text-sm mt-1">Creá categorías para organizar tus productos.</p>
        </div>
      </div>
    );
  }

  // ─── Data ───
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Categorías</h2>
          <p className="text-sm text-brand-text-secondary">
            {categories.length} categoría(s)
          </p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          + Nueva Categoría
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-1">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className="p-3 rounded-lg border bg-brand-surface flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <span className="text-brand-text-primary font-medium">
                {cat.name}
              </span>
              {cat.description && (
                <span className="text-xs text-brand-text-secondary">
                  — {cat.description}
                </span>
              )}
              {cat.product_count !== undefined && (
                <span className="text-xs text-brand-text-secondary">
                  {cat.product_count} producto(s)
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => openEdit(cat)}
                className="text-xs text-brand-primary hover:underline"
              >
                Editar
              </button>
              <button
                onClick={() => handleDelete(cat)}
                className="text-xs text-red-600 hover:underline"
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              {editing ? "Editar Categoría" : "Nueva Categoría"}
            </h3>
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1">Nombre *</label>
              <input
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: Fierros"
                autoFocus
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Descripción</label>
              <input
                value={categoryDescription}
                onChange={(e) => setCategoryDescription(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Opcional"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={submitting || !categoryName.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
                  hover:bg-brand-secondary disabled:opacity-50"
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
