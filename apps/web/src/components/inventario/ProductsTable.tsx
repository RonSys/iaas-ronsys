/**
 * ProductsTable — Tabla de productos con sort, search y filtros.
 *
 * DT-F0-009 HU-F0-009-02: Página CRUD de productos
 *
 * Props:
 * - products: Lista de productos a mostrar
 * - loading: Estado de carga
 * - onEdit: Callback al editar producto
 * - onDelete: Callback al eliminar producto
 * - onOpenSerials: Callback para abrir panel de seriales
 * - sortBy: Columna actual de ordenación
 * - sortOrder: Dirección de ordenación
 * - onSort: Callback al cambiar ordenación
 *
 * @module components/inventario/ProductsTable
 */

import type { ProductResponse } from "@/types";
import { fmtCurrency } from "@/components/dashboard/KPICard";

type SortField = "name" | "retail_price" | "current_stock" | "category_name";

interface ProductsTableProps {
  products: ProductResponse[];
  loading: boolean;
  onEdit: (product: ProductResponse) => void;
  onDelete: (product: ProductResponse) => void;
  onOpenSerials?: (product: ProductResponse) => void;
  sortBy: SortField;
  sortOrder: "asc" | "desc";
  onSort: (field: SortField) => void;
}

export function ProductsTable({
  products,
  loading,
  onEdit,
  onDelete,
  onOpenSerials,
  sortBy,
  sortOrder,
  onSort,
}: ProductsTableProps) {
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) {
      return <span className="text-gray-300 ml-1">⇅</span>;
    }
    return (
      <span className="text-brand-primary ml-1">
        {sortOrder === "asc" ? "↑" : "↓"}
      </span>
    );
  };

  const handleSort = (field: SortField) => {
    onSort(field);
  };

  if (loading && products.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-12 bg-gray-100 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="p-10 text-center text-brand-text-secondary">
        <span className="text-4xl block mb-3">📦</span>
        <p className="text-lg font-medium">No hay productos</p>
        <p className="text-sm mt-1">
          Usa "Nuevo Producto" para agregar productos al catálogo.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-brand-text-secondary">
            <th
              className="py-3 px-3 font-medium cursor-pointer hover:text-brand-text-primary select-none"
              onClick={() => handleSort("name")}
            >
              Producto <SortIcon field="name" />
            </th>
            <th
              className="py-3 px-3 font-medium cursor-pointer hover:text-brand-text-primary select-none hidden md:table-cell"
              onClick={() => handleSort("category_name")}
            >
              Categoría <SortIcon field="category_name" />
            </th>
            <th
              className="py-3 px-3 font-medium cursor-pointer hover:text-brand-text-primary select-none text-right"
              onClick={() => handleSort("retail_price")}
            >
              Precio Retail <SortIcon field="retail_price" />
            </th>
            <th className="py-3 px-3 font-medium text-right hidden sm:table-cell">
              Precio Mayor.
            </th>
            <th
              className="py-3 px-3 font-medium cursor-pointer hover:text-brand-text-primary select-none text-right hidden sm:table-cell"
              onClick={() => handleSort("current_stock")}
            >
              Stock <SortIcon field="current_stock" />
            </th>
            <th className="py-3 px-3 font-medium text-center hidden md:table-cell">
              Seriales
            </th>
            <th className="py-3 px-3 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr
              key={product.id}
              className={`border-b border-gray-100 hover:bg-gray-50 transition-colors
                ${product.active === false ? "opacity-50" : ""}`}
            >
              <td className="py-3 px-3">
                <div className="font-medium text-brand-text-primary">
                  {product.name}
                </div>
                {product.code && (
                  <div className="text-xs text-brand-text-secondary">
                    {product.code}
                  </div>
                )}
                {product.barcode && (
                  <div className="text-xs text-brand-text-secondary font-mono">
                    {product.barcode}
                  </div>
                )}
              </td>
              <td className="py-3 px-3 text-brand-text-secondary hidden md:table-cell">
                {product.category_name ?? (
                  <span className="text-gray-400 italic">Sin categoría</span>
                )}
              </td>
              <td className="py-3 px-3 text-right font-medium text-brand-text-primary tabular-nums">
                {fmtCurrency(product.retail_price)}
              </td>
              <td className="py-3 px-3 text-right hidden sm:table-cell">
                {product.wholesale_price != null ? (
                  <div className="tabular-nums">
                    <span className="text-brand-text-secondary">
                      {fmtCurrency(product.wholesale_price)}
                    </span>
                    {product.wholesale_min_qty != null && (
                      <div className="text-xs text-brand-text-secondary tabular-nums">
                        mín {product.wholesale_min_qty} unid
                      </div>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="py-3 px-3 text-right tabular-nums hidden sm:table-cell">
                <span
                  className={`font-medium ${
                    product.current_stock < 0
                      ? "text-red-600"
                      : product.current_stock === 0
                        ? "text-gray-400"
                        : "text-brand-text-primary"
                  }`}
                >
                  {product.has_serial
                    ? (product.serial_available_count ?? product.current_stock)
                    : product.current_stock}
                </span>
                {product.has_serial && (
                  <div className="text-xs text-brand-text-secondary">
                    {product.serial_available_count ?? 0} /{" "}
                    {product.serial_total_count ?? 0}
                  </div>
                )}
              </td>
              <td className="py-3 px-3 text-center hidden md:table-cell">
                {product.has_serial ? (
                  <button
                    type="button"
                    onClick={() => onOpenSerials?.(product)}
                    className="text-xs text-brand-primary hover:underline"
                    title={`${product.serial_available_count ?? 0} disponibles de ${product.serial_total_count ?? 0} totales`}
                  >
                    ✅ Sí
                  </button>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="py-3 px-3 text-right">
                <div className="flex items-center justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => onEdit(product)}
                    className="px-2 py-1 text-xs rounded hover:bg-gray-100 text-brand-text-secondary hover:text-brand-primary"
                    title="Editar producto"
                  >
                    ✏️
                  </button>
                  {product.has_serial && (
                    <button
                      type="button"
                      onClick={() => onOpenSerials?.(product)}
                      className="px-2 py-1 text-xs rounded hover:bg-gray-100 text-brand-text-secondary hover:text-brand-primary md:hidden"
                      title="Gestionar seriales"
                    >
                      🔢
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => onDelete(product)}
                    className="px-2 py-1 text-xs rounded hover:bg-red-50 text-brand-text-secondary hover:text-red-600"
                    title="Eliminar producto"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
