/**
 * CategoriesPage — Gestión de categorías de productos con árbol jerárquico.
 *
 * DT-F0-009 HU-F0-009-01: Categorías — CRUD, jerarquía y contador
 *
 * Features:
 * - Vista de árbol colapsable con jerarquía (parent_id)
 * - Badge de product_count por categoría
 * - Dropdown de categoría padre al crear/editar
 * - Indicador visual de activo/inactivo
 * - 4 estados: loading, empty, error, data
 *
 * @module pages/ferreteria/CategoriesPage
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import { CategoryTree } from "@/components/inventario/CategoryTree";
import { getCategories, getCategoryTree, createCategory, updateCategory, deleteCategory } from "@/services/inventoryApi";
import type { ProductCategory, CategoryTreeNode } from "@/types";

export function CategoriesPage() {
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [treeNodes, setTreeNodes] = useState<CategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useTreeView, setUseTreeView] = useState(true);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ProductCategory | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [categoryDescription, setCategoryDescription] = useState("");
  const [categoryParentId, setCategoryParentId] = useState<number | null>(null);
  const [categorySortOrder, setCategorySortOrder] = useState<number>(0);
  const [categoryActive, setCategoryActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (useTreeView) {
        const tree = await getCategoryTree();
        setTreeNodes(Array.isArray(tree) ? tree : []);
        // Flatten tree para flat list también
        const flat: ProductCategory[] = [];
        const flatten = (nodes: CategoryTreeNode[]) => {
          for (const node of nodes) {
            flat.push(node);
            if (node.children) flatten(node.children);
          }
        };
        flatten(Array.isArray(tree) ? tree : []);
        setCategories(flat);
      } else {
        const data = await getCategories();
        setCategories(Array.isArray(data) ? data : []);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
      setCategories([]);
      setTreeNodes([]);
    } finally {
      setLoading(false);
    }
  }, [useTreeView]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Filter active categories for parent dropdown
  const activeCategoriesForDropdown = useMemo(
    () => categories.filter((c) => c.active !== false),
    [categories],
  );

  // Exclude self + descendants when editing (anti-ciclos)
  const parentDropdownOptions = useMemo(() => {
    if (!editing) return activeCategoriesForDropdown;
    // Exclude self and immediate children to prevent cycles
    const excludeIds = new Set<number>([editing.id]);
    // Simple approach: exclude self only (backend handles depth validation)
    return activeCategoriesForDropdown.filter((c) => !excludeIds.has(c.id));
  }, [editing, activeCategoriesForDropdown]);

  const openCreate = () => {
    setEditing(null);
    setCategoryName("");
    setCategoryDescription("");
    setCategoryParentId(null);
    setCategorySortOrder(0);
    setCategoryActive(true);
    setShowModal(true);
  };

  const openEdit = (cat: ProductCategory) => {
    setEditing(cat);
    setCategoryName(cat.name);
    setCategoryDescription(cat.description ?? "");
    setCategoryParentId(cat.parent_id ?? null);
    setCategorySortOrder(cat.sort_order ?? 0);
    setCategoryActive(cat.active !== false);
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!categoryName.trim()) return;
    setSubmitting(true);
    try {
      const body = {
        name: categoryName.trim(),
        description: categoryDescription.trim() || undefined,
        parent_id: categoryParentId,
        sort_order: categorySortOrder,
        active: editing ? categoryActive : undefined,
      };

      if (editing) {
        await updateCategory(editing.id, body);
      } else {
        await createCategory(body as any);
      }
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
      await deleteCategory(cat.id);
      await fetchCategories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  // ─── Category Modal ───
  const categoryModal = showModal && (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
        <h3 className="text-lg font-bold text-brand-text-primary mb-4">
          {editing ? "Editar Categoría" : "Nueva Categoría"}
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Nombre <span className="text-red-500">*</span>
            </label>
            <input
              value={categoryName}
              onChange={(e) => setCategoryName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
              placeholder="Ej: Fierros"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descripción</label>
            <input
              value={categoryDescription}
              onChange={(e) => setCategoryDescription(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
              placeholder="Opcional"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Categoría Padre</label>
            <select
              value={categoryParentId ?? ""}
              onChange={(e) =>
                setCategoryParentId(e.target.value ? Number(e.target.value) : null)
              }
              className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
            >
              <option value="">— Ninguna (raíz) —</option>
              {parentDropdownOptions.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Orden</label>
            <input
              type="number"
              min="0"
              value={categorySortOrder}
              onChange={(e) => setCategorySortOrder(Number(e.target.value) || 0)}
              className="w-24 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
            />
          </div>
          {editing && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium">Activo</label>
              <button
                type="button"
                role="switch"
                aria-checked={categoryActive}
                onClick={() => setCategoryActive(!categoryActive)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  ${categoryActive ? "bg-brand-primary" : "bg-gray-300"}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    ${categoryActive ? "translate-x-6" : "translate-x-1"}`}
                />
              </button>
            </div>
          )}
        </div>
        <div className="flex gap-2 justify-end mt-5 pt-4 border-t">
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
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
          >
            {submitting ? "Guardando..." : editing ? "Actualizar" : "Crear"}
          </button>
        </div>
      </div>
    </div>
  );

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  // ─── Error ───
  if (error && categories.length === 0 && treeNodes.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🏷️ Categorías</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="mb-2">⚠️ {error}</p>
          <button
            onClick={fetchCategories}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty ───
  const isEmpty =
    (useTreeView && treeNodes.length === 0) ||
    (!useTreeView && categories.length === 0);

  if (isEmpty) {
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
          <p className="text-sm mt-1">
            Creá categorías para organizar tus productos.
          </p>
        </div>
        {categoryModal}
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
            {categories.length} categoría(s) ·{" "}
            <button
              onClick={() => setUseTreeView(!useTreeView)}
              className="text-brand-primary hover:underline text-xs"
            >
              {useTreeView ? "Ver lista plana" : "Ver árbol"}
            </button>
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
          <button onClick={fetchCategories} className="ml-2 underline text-xs">
            Reintentar
          </button>
        </div>
      )}

      {useTreeView ? (
        <div className="border rounded-lg bg-white p-2">
          <CategoryTree
            nodes={treeNodes}
            onEdit={openEdit}
            onDelete={handleDelete}
            showActions
            showProductCount
          />
        </div>
      ) : (
        <div className="space-y-1">
          {categories.map((cat) => (
            <div
              key={cat.id}
              className="p-3 rounded-lg border bg-brand-surface flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-brand-text-primary font-medium">
                  {cat.parent_id ? "  ↳ " : "📁 "}{cat.name}
                </span>
                {cat.description && (
                  <span className="text-xs text-brand-text-secondary hidden sm:inline">
                    — {cat.description}
                  </span>
                )}
                {cat.active === false && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                    Inactivo
                  </span>
                )}
                {cat.product_count !== undefined && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-brand-primary/10 text-brand-primary font-medium">
                    {cat.product_count} prod.
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
      )}

      {categoryModal}
    </div>
  );
}
