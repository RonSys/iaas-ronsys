/**
 * RecipeModal — Gestión de recetas (insumos por plato).
 *
 * Caso 6: Recetas e Insumos
 * - Modal para crear/editar/visualizar recetas de ítems del menú
 * - Selector de productos del inventario con búsqueda
 * - Costo estimado en tiempo real (average_cost × quantity)
 * - Margen (precio venta - costo receta)
 *
 * @module components/restaurante/RecipeModal
 */
import { useState, useEffect, useMemo } from "react";
import { getRecipe, updateRecipe } from "@/services/restaurantApi";
import { getProducts } from "@/services/inventoryApi";
import type { ProductResponse } from "@/types/inventory";
import type { RecipeIngredient } from "@/types/restaurant";

interface RecipeModalProps {
  menuItemId: number;
  menuItemName: string;
  menuItemPrice: number;
  preparationArea: string;
  onClose: () => void;
  onSaved?: () => void;
}

interface IngredientEntry {
  _key: string;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_of_measure: string;
  average_cost: number;
}

const UNIT_ABBREVIATIONS: Record<string, string> = {
  kilogramo: "kg",
  kilo: "kg",
  gramo: "g",
  gramos: "g",
  litro: "L",
  litros: "L",
  mililitro: "mL",
  mililitros: "mL",
  unidad: "unidad",
  unidades: "unidad",
  caja: "caja",
  paquete: "paquete",
  docena: "docena",
};

function normalizeUnit(unit: string): string {
  return UNIT_ABBREVIATIONS[unit.toLowerCase()] ?? unit;
}

export function RecipeModal({
  menuItemId,
  menuItemName,
  menuItemPrice,
  preparationArea,
  onClose,
  onSaved,
}: RecipeModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ─── Recipe state ─────────────────────────────────────────
  const [ingredients, setIngredients] = useState<IngredientEntry[]>([]);
  const [originalRecipeId, setOriginalRecipeId] = useState<number | null>(null);

  // ─── Product search state ─────────────────────────────────
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [productSearch, setProductSearch] = useState("");
  const [showProductSelector, setShowProductSelector] = useState(false);

  // ─── Load existing recipe + products on mount ─────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [recipeData, productsData] = await Promise.all([
          getRecipe(menuItemId),
          getProducts({ active: true, limit: 200 }),
        ]);

        if (cancelled) return;

        if (recipeData) {
          setOriginalRecipeId(recipeData.id ?? null);
          setIngredients(
            (recipeData.ingredients ?? []).map((ing: RecipeIngredient) => ({
              _key: `ing_${ing.product_id}_${Date.now()}`,
              product_id: ing.product_id,
              product_name: ing.product_name ?? `Producto #${ing.product_id}`,
              quantity: ing.quantity,
              unit_of_measure: ing.unit_of_measure,
              average_cost: ing.average_cost ?? 0,
            })),
          );
        } else {
          setIngredients([]);
        }

        setProducts(productsData.products ?? []);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error al cargar datos");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [menuItemId]);

  // ─── Filtered products for selector ───────────────────────
  const filteredProducts = useMemo(() => {
    if (!productSearch.trim()) return products;
    const q = productSearch.toLowerCase();
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.code?.toLowerCase().includes(q) ||
        p.barcode?.toLowerCase().includes(q),
    );
  }, [products, productSearch]);

  // ─── Products already selected (to exclude from selector) ─
  const selectedProductIds = useMemo(
    () => new Set(ingredients.map((i) => i.product_id)),
    [ingredients],
  );

  // ─── Cost calculation ─────────────────────────────────────
  const totalCost = useMemo(() => {
    return ingredients.reduce(
      (sum, ing) => sum + ing.average_cost * ing.quantity,
      0,
    );
  }, [ingredients]);

  const margin = menuItemPrice - totalCost;

  // ─── Add ingredient ────────────────────────────────────────
  const addIngredient = (product: ProductResponse) => {
    const unit = normalizeUnit(product.unit ?? "unidad");
    setIngredients((prev) => [
      ...prev,
      {
        _key: `ing_${product.id}_${Date.now()}`,
        product_id: product.id,
        product_name: product.name,
        quantity: 1,
        unit_of_measure: unit,
        average_cost: product.average_cost ?? 0,
      },
    ]);
    setShowProductSelector(false);
    setProductSearch("");
  };

  // ─── Remove ingredient ────────────────────────────────────
  const removeIngredient = (key: string) => {
    setIngredients((prev) => prev.filter((i) => i._key !== key));
  };

  // ─── Update ingredient field ──────────────────────────────
  const updateIngredient = (
    key: string,
    field: "quantity" | "unit_of_measure",
    value: number | string,
  ) => {
    setIngredients((prev) =>
      prev.map((i) => (i._key === key ? { ...i, [field]: value } : i)),
    );
  };

  // ─── Save ─────────────────────────────────────────────────
  const handleSave = async () => {
    if (ingredients.length === 0) {
      setError("Agregá al menos un insumo a la receta.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateRecipe(menuItemId, {
        ingredients: ingredients.map((ing, idx) => ({
          product_id: ing.product_id,
          quantity: ing.quantity,
          unit_of_measure: ing.unit_of_measure,
          sort_order: idx + 1,
        })),
      });
      onSaved?.();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar receta");
    } finally {
      setSaving(false);
    }
  };

  // ─── Loading state ────────────────────────────────────────
  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl">
          <div className="flex items-center justify-center py-10">
            <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-center text-sm text-brand-text-secondary">Cargando receta...</p>
        </div>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
        {/* ── Header ── */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-brand-text-primary">
              📋 Receta: {menuItemName}
            </h3>
            <p className="text-xs text-brand-text-secondary mt-0.5">
              {preparationArea} · S/ {menuItemPrice.toFixed(2)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="p-3 mb-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* ── Recipe has no ingredients (empty state) ── */}
        {ingredients.length === 0 && !loading && (
          <div className="p-6 text-center text-brand-text-secondary rounded-lg border border-dashed border-gray-300 mb-4">
            <span className="text-3xl block mb-2">📋</span>
            <p className="font-medium">Sin receta configurada</p>
            <p className="text-xs mt-1">Agregá insumos para calcular el costo del plato.</p>
          </div>
        )}

        {/* ── Ingredient list ── */}
        {ingredients.length > 0 && (
          <div className="space-y-2 mb-4">
            <h4 className="text-sm font-semibold text-brand-text-primary">Insumos</h4>
            {ingredients.map((ing) => (
              <div
                key={ing._key}
                className="flex items-center gap-2 p-3 rounded-lg border border-gray-200"
              >
                {/* Product name (read-only) */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{ing.product_name}</p>
                  <p className="text-[10px] text-brand-text-secondary">
                    Costo unit: S/ {ing.average_cost.toFixed(2)} / {ing.unit_of_measure}
                  </p>
                </div>

                {/* Quantity */}
                <div className="w-20">
                  <input
                    type="number"
                    min={0.01}
                    step={0.1}
                    value={ing.quantity}
                    onChange={(e) =>
                      updateIngredient(
                        ing._key,
                        "quantity",
                        Math.max(0.01, Number(e.target.value)),
                      )
                    }
                    className="w-full px-2 py-1 border rounded text-xs text-center"
                  />
                </div>

                {/* Unit */}
                <div className="w-16">
                  <select
                    value={ing.unit_of_measure}
                    onChange={(e) =>
                      updateIngredient(ing._key, "unit_of_measure", e.target.value)
                    }
                    className="w-full px-1 py-1 border rounded text-xs"
                  >
                    <option value="g">g</option>
                    <option value="kg">kg</option>
                    <option value="unidad">unidad</option>
                    <option value="mL">mL</option>
                    <option value="L">L</option>
                    <option value="caja">caja</option>
                    <option value="paquete">paquete</option>
                    <option value="docena">docena</option>
                  </select>
                </div>

                {/* Subtotal */}
                <div className="w-16 text-right">
                  <span className="text-xs font-medium">
                    S/ {(ing.average_cost * ing.quantity).toFixed(2)}
                  </span>
                </div>

                {/* Remove */}
                <button
                  onClick={() => removeIngredient(ing._key)}
                  className="text-red-400 hover:text-red-600 text-sm ml-1"
                  title="Quitar insumo"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── Cost summary + margin ── */}
        {ingredients.length > 0 && (
          <div className="p-4 rounded-lg bg-gray-50 border border-gray-200 mb-4 space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-brand-text-secondary">Costo total receta:</span>
              <span className="font-semibold text-brand-text-primary">
                S/ {totalCost.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-brand-text-secondary">Precio venta:</span>
              <span className="font-semibold text-brand-text-primary">
                S/ {menuItemPrice.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm font-medium pt-1 border-t border-gray-200">
              <span>Margen:</span>
              <span className={margin >= 0 ? "text-green-600" : "text-red-600"}>
                S/ {margin.toFixed(2)}
                {margin >= 0
                  ? ` (${((margin / menuItemPrice) * 100).toFixed(0)}%)`
                  : ""}
              </span>
            </div>
          </div>
        )}

        {/* ── Product selector ── */}
        {showProductSelector && (
          <div className="p-4 rounded-lg border border-brand-primary/30 bg-brand-primary/5 mb-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-brand-text-primary">
                Agregar insumo
              </h4>
              <button
                onClick={() => {
                  setShowProductSelector(false);
                  setProductSearch("");
                }}
                className="text-xs text-brand-text-secondary hover:text-brand-text-primary"
              >
                ✕ Cerrar
              </button>
            </div>
            <input
              type="text"
              value={productSearch}
              onChange={(e) => setProductSearch(e.target.value)}
              placeholder="🔍 Buscar producto del inventario..."
              className="w-full px-3 py-2 border rounded-lg text-sm mb-2"
              autoFocus
            />
            <div className="max-h-40 overflow-y-auto space-y-1">
              {filteredProducts.length === 0 && (
                <p className="text-xs text-brand-text-secondary text-center py-3">
                  No se encontraron productos.
                </p>
              )}
              {filteredProducts
                .filter((p) => !selectedProductIds.has(p.id))
                .map((product) => (
                  <button
                    key={product.id}
                    onClick={() => addIngredient(product)}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-white hover:shadow-sm transition-colors flex items-center justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-medium truncate block">{product.name}</span>
                      <span className="text-[10px] text-brand-text-secondary">
                        {product.unit} · S/ {product.average_cost.toFixed(2)} / {normalizeUnit(product.unit)}
                      </span>
                    </div>
                    <span className="text-xs text-brand-primary font-medium ml-2">
                      + Agregar
                    </span>
                  </button>
                ))}
              {filteredProducts.filter((p) => !selectedProductIds.has(p.id)).length ===
                0 &&
                products.length > 0 && (
                  <p className="text-xs text-brand-text-secondary text-center py-2">
                    Todos los productos ya están en la receta.
                  </p>
                )}
            </div>
          </div>
        )}

        {/* ── Actions ── */}
        <div className="flex gap-2 justify-end mt-4">
          {!showProductSelector && (
            <button
              onClick={() => setShowProductSelector(true)}
              className="px-3 py-2 text-xs rounded-lg border border-brand-primary text-brand-primary hover:bg-brand-primary/5"
            >
              + Agregar insumo
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
            disabled={saving}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving || ingredients.length === 0}
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
          >
            {saving ? "Guardando..." : originalRecipeId ? "Actualizar receta" : "Guardar receta"}
          </button>
        </div>
      </div>
    </div>
  );
}
