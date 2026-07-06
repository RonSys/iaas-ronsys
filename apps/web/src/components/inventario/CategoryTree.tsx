/**
 * CategoryTree — Árbol recursivo colapsable de categorías.
 *
 * DT-F0-009 HU-F0-009-01: Jerarquía de categorías
 *
 * Props:
 * - nodes: Array de CategoryTreeNode (estructura anidada)
 * - onEdit: Callback al editar categoría
 * - onDelete: Callback al eliminar categoría
 * - onSelect: Callback al seleccionar categoría (para dropdown padre)
 * - selectedId: ID de la categoría actualmente seleccionada
 * - showActions: Mostrar botones editar/eliminar
 * - showProductCount: Mostrar badge con product_count
 *
 * @module components/inventario/CategoryTree
 */

import { useState, type ReactNode } from "react";
import type { CategoryTreeNode, ProductCategory } from "@/types";

interface CategoryTreeProps {
  nodes: CategoryTreeNode[];
  onEdit?: (cat: ProductCategory) => void;
  onDelete?: (cat: ProductCategory) => void;
  onSelect?: (cat: ProductCategory) => void;
  selectedId?: number | null;
  showActions?: boolean;
  showProductCount?: boolean;
  depth?: number;
}

export function CategoryTree({
  nodes,
  onEdit,
  onDelete,
  onSelect,
  selectedId,
  showActions = true,
  showProductCount = true,
  depth = 0,
}: CategoryTreeProps): ReactNode {
  if (!nodes || nodes.length === 0) return null;

  return (
    <ul className={depth === 0 ? "" : "ml-5 border-l-2 border-gray-200 pl-2"}>
      {nodes.map((node) => (
        <CategoryTreeItem
          key={node.id}
          node={node}
          onEdit={onEdit}
          onDelete={onDelete}
          onSelect={onSelect}
          selectedId={selectedId}
          showActions={showActions}
          showProductCount={showProductCount}
          depth={depth}
        />
      ))}
    </ul>
  );
}

function CategoryTreeItem({
  node,
  onEdit,
  onDelete,
  onSelect,
  selectedId,
  showActions,
  showProductCount,
  depth,
}: Omit<CategoryTreeProps, "nodes"> & { node: CategoryTreeNode }) {
  const [collapsed, setCollapsed] = useState(depth === 0 ? false : true);
  const hasChildren = node.children && node.children.length > 0;

  const isSelected = selectedId !== undefined && selectedId === node.id;

  return (
    <li>
      <div
        className={`flex items-center gap-2 py-2 px-3 rounded-lg group cursor-pointer
          transition-all
          ${isSelected ? "bg-brand-primary/10 ring-1 ring-brand-primary/30" : "hover:bg-gray-50"}
          ${!node.active ? "opacity-50" : ""}`}
        onClick={() => onSelect?.(node)}
      >
        {/* Toggle colapsar */}
        <button
          type="button"
          aria-label={collapsed ? "Expandir" : "Colapsar"}
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) setCollapsed(!collapsed);
          }}
          className={`w-5 h-5 flex items-center justify-center rounded transition-colors
            text-brand-text-secondary hover:bg-gray-200
            ${!hasChildren ? "invisible" : ""}`}
        >
          <span className={`text-xs transition-transform ${collapsed ? "" : "rotate-90"}`}>
            ▶
          </span>
        </button>

        {/* Icono de categoría */}
        <span className="text-base flex-shrink-0">
          {(depth ?? 0) === 0 ? "📁" : "🏷️"}
        </span>

        {/* Nombre */}
        <span className="flex-1 font-medium text-brand-text-primary text-sm">
          {node.name}
        </span>

        {/* Estado activo/inactivo */}
        {node.active === false && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 flex-shrink-0">
            Inactivo
          </span>
        )}

        {/* Badge product_count */}
        {showProductCount && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-brand-primary/10 text-brand-primary font-medium flex-shrink-0">
            {node.product_count ?? 0}
          </span>
        )}

        {/* Acciones */}
        {showActions && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
            <button
              type="button"
              aria-label="Editar categoría"
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(node);
              }}
              className="p-1 rounded hover:bg-gray-200 text-xs text-brand-text-secondary hover:text-brand-primary"
              title="Editar"
            >
              ✏️
            </button>
            <button
              type="button"
              aria-label="Eliminar categoría"
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.(node);
              }}
              className="p-1 rounded hover:bg-red-100 text-xs text-brand-text-secondary hover:text-red-600"
              title="Eliminar"
            >
              🗑️
            </button>
          </div>
        )}
      </div>

      {/* Hijos colapsables */}
      {hasChildren && !collapsed && (
        <CategoryTree
          nodes={node.children}
          onEdit={onEdit}
          onDelete={onDelete}
          onSelect={onSelect}
          selectedId={selectedId}
          showActions={showActions}
          showProductCount={showProductCount}
          depth={(depth ?? 0) + 1}
        />
      )}
    </li>
  );
}
