/**
 * ProductSearch — Buscador de productos con sugerencias, precio y stock.
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F0-015: Precios mayoristas visibles en resultados de búsqueda
 * - Muestra precio retail + mayorista si está configurado
 * - Stock visible en cada resultado
 * - Filtro por categoría
 *
 * @module components/sales/ProductSearch
 */
import { useState, useEffect, useRef } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import type { KardexProduct } from "@/types";

interface Category {
  id: number;
  name: string;
}

interface ProductSearchProps {
  onSelect: (product: KardexProduct) => void;
  disabled?: boolean;
}

export function ProductSearch({ onSelect, disabled }: ProductSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KardexProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Load categories
  useEffect(() => {
    fetch("/api/inventory/categories")
      .then((r) => r.json())
      .then((data) => setCategories(data.categories ?? data))
      .catch(() => {});
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Search products
  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ search: query });
        if (selectedCategory) params.set("category_id", selectedCategory);
        const res = await fetch(`/api/accounting/kardex/products?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setResults(data);
          setShowResults(true);
        }
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, selectedCategory]);

  const handleSelect = (product: KardexProduct) => {
    onSelect(product);
    setQuery("");
    setResults([]);
    setShowResults(false);
  };

  /** Formatea el precio retail + mayorista si existe */
  const getPriceLabel = (product: KardexProduct): string => {
    const retail = product.unit_price ?? product.average_cost;
    const wholesale = product.wholesale_price;
    if (wholesale && product.wholesale_min_qty) {
      return `Men: ${fmtCurrency(retail)} / May: ${fmtCurrency(wholesale)} (${product.wholesale_min_qty}+)`;
    }
    return fmtCurrency(retail);
  };

  return (
    <div ref={wrapperRef} className="space-y-2">
      {/* Category filter + Search */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Buscar Producto
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setShowResults(true)}
            placeholder="Escribí código o nombre..."
            disabled={disabled}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm
              focus:outline-none focus:ring-2 focus:ring-brand-primary/20
              disabled:opacity-50"
            autoComplete="off"
          />
        </div>
        {categories.length > 0 && (
          <div className="w-36">
            <label className="block text-xs font-medium text-brand-text-secondary mb-1">
              Categoría
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              disabled={disabled}
              className="w-full px-2 py-2 rounded-lg border border-gray-300 text-sm
                focus:outline-none focus:ring-2 focus:ring-brand-primary/20
                disabled:opacity-50"
            >
              <option value="">Todas</option>
              {categories.map((cat) => (
                <option key={cat.id} value={String(cat.id)}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading && (
        <div className="absolute right-3 top-9">
          <div className="w-4 h-4 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {showResults && results.length > 0 && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {results.map((p) => (
            <button
              key={p.code}
              type="button"
              onClick={() => handleSelect(p)}
              className="w-full text-left px-3 py-2.5 hover:bg-gray-50 border-b border-gray-100 last:border-0"
            >
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-sm font-medium text-brand-text-primary">
                    {p.name}
                  </span>
                  <span className="ml-2 text-xs text-brand-text-secondary">
                    {p.code}
                  </span>
                  {p.category_name && (
                    <span className="ml-2 text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                      {p.category_name}
                    </span>
                  )}
                </div>
                <span className="text-sm font-bold text-brand-text-primary">
                  {getPriceLabel(p)}
                </span>
              </div>
              <div className="flex justify-between mt-0.5">
                <span className="text-xs text-brand-text-secondary">
                  {p.unit}
                  {p.wholesale_min_qty && (
                    <span className="ml-2 text-brand-primary font-medium">
                      May: {p.wholesale_min_qty}+
                    </span>
                  )}
                </span>
                <span
                  className={`text-xs ${p.current_stock > 0 ? "text-brand-success" : "text-brand-error"}`}
                >
                  Stock: {p.current_stock}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {showResults && query.length >= 2 && !loading && results.length === 0 && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-center text-sm text-brand-text-secondary">
          No se encontraron productos
        </div>
      )}
    </div>
  );
}
