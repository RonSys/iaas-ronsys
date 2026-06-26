/**
 * InvestmentModal — Modal para crear/editar bienes de inversión.
 *
 * Escenarios 2, 3, 4 del Caso 7:
 * - Formulario con nombre, categoría, costo estimado/real, recibo, estado
 * - 9 categorías disponibles (Escenario 3)
 * - Validación de campos requeridos
 * - Feedback de error inline
 *
 * @module components/restaurante/InvestmentModal
 */
import { useState, useEffect, useCallback } from "react";
import type {
  InvestmentItem,
  InvestmentFormData,
  InvestmentCategory,
} from "@/types";

export const CATEGORIES: { value: InvestmentCategory; label: string }[] = [
  { value: "infraestructura", label: "\uD83C\uDFD7\uFE0F Infraestructura" },
  { value: "mobiliario", label: "\uD83E\uDE91 Mobiliario" },
  { value: "equipamiento_cocina", label: "\uD83D\uDD25 Equipamiento Cocina" },
  { value: "instalaciones", label: "\uD83D\uDEE0\uFE0F Instalaciones" },
  { value: "vestimenta", label: "\uD83D\uDC55 Vestimenta" },
  { value: "dyl", label: "\uD83D\uDCCB DyL (Decoración y Logística)" },
  { value: "tecnologia", label: "\uD83D\uDCF1 Tecnología" },
  { value: "marketing", label: "\uD83D\uDCE3 Marketing" },
  { value: "gastos_operativos", label: "\uD83D\uDCB0 Gastos Operativos" },
];

interface InvestmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: InvestmentFormData) => Promise<void>;
  item?: InvestmentItem | null;
}

const emptyForm: InvestmentFormData = {
  name: "",
  category: "equipamiento_cocina",
  estimated_cost: 0,
  actual_cost: null,
  receipt_code: "",
  status: "pending",
  notes: null,
};

export function InvestmentModal({
  isOpen,
  onClose,
  onSave,
  item,
}: InvestmentModalProps) {
  const [formData, setFormData] = useState<InvestmentFormData>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (item) {
      setFormData({
        name: item.name,
        category: item.category,
        estimated_cost: item.estimated_cost,
        actual_cost: item.actual_cost,
        receipt_code: item.receipt_code ?? "",
        status: item.status,
        notes: item.notes ?? null,
      });
    } else {
      setFormData(emptyForm);
    }
    setFormError(null);
  }, [item, isOpen]);

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      setFormError("El nombre del bien es obligatorio");
      return;
    }
    if (!formData.estimated_cost || formData.estimated_cost < 0) {
      setFormError("El costo estimado debe ser un número mayor o igual a 0");
      return;
    }
    if (
      formData.actual_cost !== null &&
      formData.actual_cost !== undefined &&
      formData.actual_cost < 0
    ) {
      setFormError("El costo real no puede ser negativo");
      return;
    }
    setFormError(null);
    setSubmitting(true);
    try {
      await onSave({
        ...formData,
        name: formData.name.trim(),
      });
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Error al guardar",
      );
    } finally {
      setSubmitting(false);
    }
  };

  // ─── Keyboard handlers ───
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) {
        setFormError(null);
        onClose();
      }
      if (e.key === "Enter" && !e.shiftKey && !submitting) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [onClose, submitting],
  );

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={submitting ? undefined : onClose}
      onKeyDown={handleKeyDown}
    >
      <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-brand-text-primary mb-4">
          {item ? "Editar Bien" : "Agregar Bien"}
        </h3>

        {formError && (
          <div className="mb-3 p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
            {formError}
          </div>
        )}

        <div className="space-y-3">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Nombre del bien <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Ej: Cocina Industrial"
              autoFocus
            />
          </div>

          {/* Categoría */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Categoría <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.category}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  category: e.target.value as InvestmentCategory,
                })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Costo estimado */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Costo estimado (S/) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min={0}
              step={0.01}
              value={formData.estimated_cost || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  estimated_cost: parseFloat(e.target.value) || 0,
                })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="0.00"
            />
          </div>

          {/* Costo real */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Costo real (S/) <span className="text-gray-400">(opcional)</span>
            </label>
            <input
              type="number"
              min={0}
              step={0.01}
              value={
                formData.actual_cost !== null && formData.actual_cost !== undefined
                  ? formData.actual_cost
                  : ""
              }
              onChange={(e) =>
                setFormData({
                  ...formData,
                  actual_cost: e.target.value
                    ? parseFloat(e.target.value)
                    : null,
                })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Dejar vacío si pendiente"
            />
          </div>

          {/* Código recibo */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Código recibo/factura{" "}
              <span className="text-gray-400">(opcional)</span>
            </label>
            <input
              type="text"
              value={formData.receipt_code}
              onChange={(e) =>
                setFormData({ ...formData, receipt_code: e.target.value })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Ej: FAC-001"
            />
          </div>

          {/* Estado */}
          <div>
            <label className="block text-sm font-medium mb-1">Estado</label>
            <select
              value={formData.status}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  status: e.target.value as "pending" | "acquired",
                })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              <option value="pending">Pendiente</option>
              <option value="acquired">Adquirido</option>
            </select>
          </div>

          {/* Notas (opcional) */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Notas <span className="text-gray-400">(opcional)</span>
            </label>
            <textarea
              value={formData.notes ?? ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  notes: e.target.value || null,
                })
              }
              className="w-full px-3 py-2 border rounded-lg text-sm resize-vertical"
              rows={3}
              placeholder="Observaciones, especificaciones, etc."
            />
          </div>
        </div>

        <div className="flex gap-2 justify-end mt-6">
          <button
            onClick={() => {
              setFormError(null);
              onClose();
            }}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
            disabled={submitting}
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={
              submitting || !formData.name.trim() || !formData.estimated_cost
            }
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50 flex items-center gap-2"
          >
            {submitting && (
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            )}
            {submitting ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  );
}
