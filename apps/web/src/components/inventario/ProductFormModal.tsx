/**
 * ProductFormModal — Formulario completo de creación/edición de producto.
 *
 * DT-F0-009 HU-F0-009-02 / HU-F0-009-03: CRUD productos + precios mayorista/detal
 *
 * Campos:
 * - nombre, descripción
 * - categoría (dropdown de categorías activas)
 * - unidad de medida
 * - precios: retail, wholesale + cantidad mínima
 * - código de barras
 * - has_serial (toggle)
 * - meses de garantía, fabricante
 * - stock inicial (sin seriales)
 * - activo/inactivo
 *
 * @module components/inventario/ProductFormModal
 */

import { useState, useEffect, type FormEvent } from "react";
import type {
  ProductResponse,
  ProductCreateRequest,
  ProductUpdateRequest,
  ProductCategory,
  ProductUnit,
} from "@/types";

const UNIT_OPTIONS: { value: ProductUnit; label: string }[] = [
  { value: "unidad", label: "Unidad" },
  { value: "kg", label: "Kilogramo (kg)" },
  { value: "g", label: "Gramo (g)" },
  { value: "L", label: "Litro (L)" },
  { value: "mL", label: "Mililitro (mL)" },
  { value: "m", label: "Metro (m)" },
  { value: "cm", label: "Centímetro (cm)" },
  { value: "m²", label: "Metro cuadrado (m²)" },
  { value: "m³", label: "Metro cúbico (m³)" },
  { value: "caja", label: "Caja" },
  { value: "paquete", label: "Paquete" },
  { value: "docena", label: "Docena" },
  { value: "juego", label: "Juego" },
  { value: "par", label: "Par" },
  { value: "rollo", label: "Rollo" },
  { value: "plancha", label: "Plancha" },
  { value: "bolsa", label: "Bolsa" },
  { value: "galón", label: "Galón" },
  { value: "lata", label: "Lata" },
];

interface ProductFormModalProps {
  isOpen: boolean;
  product?: ProductResponse | null;
  categories: ProductCategory[];
  submitting: boolean;
  onClose: () => void;
  onSave: (data: ProductCreateRequest | ProductUpdateRequest) => void;
}

export function ProductFormModal({
  isOpen,
  product,
  categories,
  submitting,
  onClose,
  onSave,
}: ProductFormModalProps) {
  const isEditing = !!product;

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [unit, setUnit] = useState<ProductUnit>("unidad");
  const [retailPrice, setRetailPrice] = useState("");
  const [wholesalePrice, setWholesalePrice] = useState("");
  const [wholesaleMinQty, setWholesaleMinQty] = useState("");
  const [barcode, setBarcode] = useState("");
  const [hasSerial, setHasSerial] = useState(false);
  const [warrantyMonths, setWarrantyMonths] = useState("0");
  const [manufacturer, setManufacturer] = useState("");
  const [initialStock, setInitialStock] = useState("");
  const [active, setActive] = useState(true);

  // Validation
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warning, setWarning] = useState<string | null>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (!isOpen) return;

    if (product) {
      setName(product.name);
      setDescription(product.description ?? "");
      setCategoryId(product.category_id ?? null);
      setUnit((product.unit as ProductUnit) || "unidad");
      setRetailPrice(String(product.retail_price));
      setWholesalePrice(product.wholesale_price != null ? String(product.wholesale_price) : "");
      setWholesaleMinQty(product.wholesale_min_qty != null ? String(product.wholesale_min_qty) : "");
      setBarcode(product.barcode ?? "");
      setHasSerial(product.has_serial);
      setWarrantyMonths(String(product.warranty_months ?? 0));
      setManufacturer(product.manufacturer ?? "");
      setInitialStock("");
      setActive(product.active !== false);
    } else {
      setName("");
      setDescription("");
      setCategoryId(null);
      setUnit("unidad");
      setRetailPrice("");
      setWholesalePrice("");
      setWholesaleMinQty("");
      setBarcode("");
      setHasSerial(false);
      setWarrantyMonths("0");
      setManufacturer("");
      setInitialStock("");
      setActive(true);
    }
    setErrors({});
    setWarning(null);
  }, [isOpen, product]);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!name.trim()) errs.name = "El nombre es obligatorio";
    if (!retailPrice.trim() || isNaN(Number(retailPrice)) || Number(retailPrice) <= 0) {
      errs.retailPrice = "El precio retail debe ser un número positivo";
    }

    // Validación wholesale_price > retail_price
    if (wholesalePrice.trim() && !isNaN(Number(wholesalePrice))) {
      const wp = Number(wholesalePrice);
      const rp = Number(retailPrice);
      if (wp > rp) {
        setWarning("Precio mayorista es mayor que el minorista. ¿Está seguro?");
      } else {
        setWarning(null);
      }
    } else {
      setWarning(null);
    }

    if (barcode.trim() && barcode.trim().length < 3) {
      errs.barcode = "Código de barras muy corto";
    }

    if (isEditing && hasSerial === false && product?.has_serial === true) {
      errs.hasSerial = "No puede desactivar seriales si el producto tiene seriales registrados";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const baseData = {
      code: null,  // Backend auto-genera el código
      name: name.trim(),
      description: description.trim() || undefined,
      category_id: categoryId,
      unit_of_measure: unit,
      retail_price: Number(retailPrice),
      wholesale_price: wholesalePrice.trim() ? Number(wholesalePrice) : null,
      wholesale_min_qty: wholesaleMinQty.trim() ? Number(wholesaleMinQty) : null,
      barcode: barcode.trim() || null,
      has_serial: hasSerial,
      warranty_months: Number(warrantyMonths) || 0,
      manufacturer: manufacturer.trim() || null,
    };

    if (isEditing) {
      onSave({
        ...baseData,
        active,
      } as ProductUpdateRequest);
    } else {
      onSave({
        ...baseData,
        current_stock: hasSerial ? undefined : (initialStock.trim() ? Number(initialStock) : 0),
      } as ProductCreateRequest);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-[5vh] overflow-y-auto">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl my-4">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-brand-text-primary">
            {isEditing ? "Editar Producto" : "Nuevo Producto"}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-brand-text-secondary"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {warning && (
          <div className="mb-4 p-3 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-700 text-sm">
            ⚠️ {warning}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium mb-1 required">
              Nombre
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.name ? "border-red-400" : "border-gray-300"} focus:outline-none focus:ring-2 focus:ring-brand-primary/20`}
              placeholder="Ej: Cemento Sol 42.5kg"
              autoFocus
            />
            {errors.name && (
              <p className="text-red-500 text-xs mt-1">{errors.name}</p>
            )}
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Descripción
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
              placeholder="Descripción opcional del producto"
              rows={2}
            />
          </div>

          {/* Categoría */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Categoría
            </label>
            <select
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
            >
              <option value="">Sin categoría</option>
              {categories
                .filter((c) => c.active !== false)
                .map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.parent_id ? "  ↳ " : ""}{cat.name}
                  </option>
                ))}
            </select>
          </div>

          {/* Unidad + Código de Barras (2 cols) */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">
                Unidad de medida
              </label>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value as ProductUnit)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
              >
                {UNIT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Código de Barras
              </label>
              <input
                value={barcode}
                onChange={(e) => setBarcode(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg text-sm font-mono ${errors.barcode ? "border-red-400" : "border-gray-300"} focus:outline-none focus:ring-2 focus:ring-brand-primary/20`}
                placeholder="7751234567890"
              />
              {errors.barcode && (
                <p className="text-red-500 text-xs mt-1">{errors.barcode}</p>
              )}
            </div>
          </div>

          {/* Precios (3 cols) */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1 required">
                Precio Retail
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={retailPrice}
                onChange={(e) => setRetailPrice(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg text-sm text-right ${errors.retailPrice ? "border-red-400" : "border-gray-300"} focus:outline-none focus:ring-2 focus:ring-brand-primary/20`}
                placeholder="0.00"
              />
              {errors.retailPrice && (
                <p className="text-red-500 text-xs mt-1">{errors.retailPrice}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Precio Mayorista
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={wholesalePrice}
                onChange={(e) => setWholesalePrice(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-right focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Cant. Mín. Mayorista
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={wholesaleMinQty}
                onChange={(e) => setWholesaleMinQty(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-right focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                placeholder="10"
              />
            </div>
          </div>

          {/* Toggle has_serial */}
          <div className="flex items-center gap-3 py-2">
            <label className="text-sm font-medium">Control por Seriales</label>
            <button
              type="button"
              role="switch"
              aria-checked={hasSerial}
              onClick={() => {
                if (isEditing && hasSerial === true && (product?.serial_total_count ?? 0) > 0) {
                  setErrors({ hasSerial: "No puede desactivar seriales si el producto tiene seriales registrados" });
                  return;
                }
                setHasSerial(!hasSerial);
                if (errors.hasSerial) {
                  setErrors((prev) => {
                    const { hasSerial: _, ...rest } = prev;
                    return rest;
                  });
                }
              }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0
                ${hasSerial ? "bg-brand-primary" : "bg-gray-300"}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${hasSerial ? "translate-x-6" : "translate-x-1"}`}
              />
            </button>
            <span className="text-xs text-brand-text-secondary">
              {hasSerial ? "Stock por seriales" : "Stock numérico"}
            </span>
            {errors.hasSerial && (
              <p className="text-red-500 text-xs">{errors.hasSerial}</p>
            )}
          </div>

          {/* Garantía + Fabricante (condicional has_serial) */}
          {hasSerial && (
            <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Meses de Garantía
                </label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={warrantyMonths}
                  onChange={(e) => setWarrantyMonths(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                  placeholder="12"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Fabricante
                </label>
                <input
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                  placeholder="Ej: Bosch"
                />
              </div>
            </div>
          )}

          {/* Stock inicial (solo creación, sin serial) */}
          {!isEditing && !hasSerial && (
            <div>
              <label className="block text-sm font-medium mb-1">
                Stock Inicial
              </label>
              <input
                type="number"
                min="0"
                value={initialStock}
                onChange={(e) => setInitialStock(e.target.value)}
                className="w-40 px-3 py-2 border border-gray-300 rounded-lg text-sm text-right focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                placeholder="0"
              />
              <p className="text-xs text-brand-text-secondary mt-1">
                Stock en {unit}
              </p>
            </div>
          )}

          {/* Toggle activo (solo edición) */}
          {isEditing && (
            <div className="flex items-center gap-3 py-2">
              <label className="text-sm font-medium">Activo</label>
              <button
                type="button"
                role="switch"
                aria-checked={active}
                onClick={() => setActive(!active)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0
                  ${active ? "bg-brand-primary" : "bg-gray-300"}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    ${active ? "translate-x-6" : "translate-x-1"}`}
                />
              </button>
            </div>
          )}

          {/* Botones */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
            >
              {submitting
                ? "Guardando..."
                : isEditing
                  ? "Actualizar"
                  : "Crear Producto"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
