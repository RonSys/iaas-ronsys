/**
 * ProductsPage — CRUD completo de productos.
 *
 * DT-F0-009 HU-F0-009-02: Página CRUD de productos
 *
 * Features:
 * - Tabla con sort (server-side), search, filtros (categoría, activo/inactivo)
 * - Botones Crear/Editar/Eliminar
 * - Indicador de has_serial (icono) y serial_count
 * - Búsqueda por código de barras
 * - Panel de seriales vía SerialPanel
 *
 * @module pages/inventario/ProductsPage
 */

import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import { ProductsTable } from "@/components/inventario/ProductsTable";
import { ProductFormModal } from "@/components/inventario/ProductFormModal";
import { SerialPanel } from "@/components/inventario/SerialPanel";
import { SerialTraceabilityPanel } from "@/components/inventario/SerialTraceabilityPanel";
import {
  getProducts,
  getCategories,
  createProduct,
  updateProduct,
  deleteProduct,
} from "@/services/inventoryApi";
import type {
  ProductResponse,
  ProductCategory,
  ProductCreateRequest,
  ProductUpdateRequest,
} from "@/types";

type SortField = "name" | "retail_price" | "current_stock" | "category_name";

export function ProductsPage() {
  // Data
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // Filters
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [activeFilter, setActiveFilter] = useState<boolean | "">("");
  const [sortBy, setSortBy] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Modals
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductResponse | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Serial panel
  const [serialPanelProduct, setSerialPanelProduct] = useState<ProductResponse | null>(null);
  const [traceabilityPanelOpen, setTraceabilityPanelOpen] = useState(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getProducts({
        search: search || undefined,
        category_id: categoryFilter || undefined,
        active: activeFilter === "" ? undefined : activeFilter,
        sort_by: sortBy,
        order: sortOrder,
      });
      setProducts(result.products ?? []);
      setTotal(result.total ?? (result.products?.length ?? 0));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al cargar productos");
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, activeFilter, sortBy, sortOrder]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Auto-clear success toast after 3s
  useEffect(() => {
    if (!success) return;
    const t = setTimeout(() => setSuccess(null), 3000);
    return () => clearTimeout(t);
  }, [success]);

  useEffect(() => {
    getCategories()
      .then((data) => setCategories(Array.isArray(data) ? data : []))
      .catch(() => setCategories([]));
  }, []);

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("asc");
    }
  };

  const openCreate = () => {
    setEditingProduct(null);
    setFormModalOpen(true);
  };

  const openEdit = (product: ProductResponse) => {
    setEditingProduct(product);
    setFormModalOpen(true);
  };

  const handleSave = async (data: ProductCreateRequest | ProductUpdateRequest) => {
    setFormSubmitting(true);
    try {
      if (editingProduct) {
        await updateProduct(editingProduct.id, data as ProductUpdateRequest);
      } else {
        await createProduct(data as ProductCreateRequest);
      }
      setFormModalOpen(false);
      await fetchProducts();
      // Also refresh categories to update product_counts
      getCategories()
        .then((d) => setCategories(Array.isArray(d) ? d : []))
        .catch(() => {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar producto");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDelete = async (product: ProductResponse) => {
    const warning =
      product.has_serial && (product.serial_total_count ?? 0) > 0
        ? `Producto tiene seriales registrados.\n\nSe desactivará pero no se eliminará físicamente.\n\n¿Desactivar "${product.name}"?`
        : `¿Eliminar "${product.name}"?`;
    if (!window.confirm(warning)) return;
    try {
      setError(null);
      const result = await deleteProduct(product.id);
      const warnings = result.warnings as string[] | undefined;
      if (warnings && warnings.length > 0) {
        setSuccess(warnings.join(" "));
      } else {
        setSuccess(`✅ Producto "${product.name}" desactivado`);
      }
      await fetchProducts();
    } catch (err: unknown) {
      setSuccess(null);
      setError(err instanceof Error ? err.message : "Error al eliminar producto");
    }
  };

  const handleOpenSerials = (product: ProductResponse) => {
    setSerialPanelProduct(product);
  };

  const handleCloseSerials = () => {
    setSerialPanelProduct(null);
    // Refresh products to update serial counts
    fetchProducts();
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">📦 Productos</h2>
          <p className="text-sm text-brand-text-secondary">
            {total} producto(s) en catálogo
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTraceabilityPanelOpen(true)}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
            title="Trazabilidad de seriales"
          >
            🔍 Trazabilidad
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
          >
            + Nuevo Producto
          </button>
        </div>
      </div>

      {/* Success toast */}
      {success && (
        <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          ✅ {success}
          <button onClick={() => setSuccess(null)} className="ml-2 underline text-xs">
            Cerrar
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          ⚠️ {error}
          <button onClick={fetchProducts} className="ml-2 underline text-xs">
            Reintentar
          </button>
        </div>
      )}

      {/* Filters toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 p-3 bg-white rounded-lg border">
        <div className="flex-1 relative">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar por nombre, código de barra..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          />
          <span className="absolute left-3 top-2.5 text-sm text-gray-400">🔍</span>
        </div>
        <select
          value={categoryFilter}
          onChange={(e) =>
            setCategoryFilter(e.target.value ? Number(e.target.value) : "")
          }
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          <option value="">Todas las categorías</option>
          {categories
            .filter((c) => c.active !== false)
            .map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name} {cat.product_count !== undefined ? `(${cat.product_count})` : ""}
              </option>
            ))}
        </select>
        <select
          value={activeFilter === "" ? "" : String(activeFilter)}
          onChange={(e) => {
            const val = e.target.value;
            setActiveFilter(val === "" ? "" : val === "true");
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          <option value="">Todos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </div>

      {/* Loading skeleton (initial) */}
      {loading && products.length === 0 ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg border">
          <ProductsTable
            products={products}
            loading={loading}
            onEdit={openEdit}
            onDelete={handleDelete}
            onOpenSerials={handleOpenSerials}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
        </div>
      )}

      {/* Product Form Modal */}
      <ProductFormModal
        isOpen={formModalOpen}
        product={editingProduct}
        categories={categories}
        submitting={formSubmitting}
        onClose={() => setFormModalOpen(false)}
        onSave={handleSave}
      />

      {/* Serial Panel */}
      {serialPanelProduct && (
        <SerialPanel
          product={serialPanelProduct}
          isOpen={!!serialPanelProduct}
          onClose={handleCloseSerials}
        />
      )}

      {/* Traceability Panel */}
      <SerialTraceabilityPanel
        isOpen={traceabilityPanelOpen}
        onClose={() => setTraceabilityPanelOpen(false)}
      />
    </div>
  );
}
