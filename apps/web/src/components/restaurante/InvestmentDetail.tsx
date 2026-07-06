/**
 * InvestmentDetail — Vista detalle de un bien de inversión.
 *
 * Escenario 7 del Caso 7:
 * - Muestra nombre, categoría, costos, recibo, ahorro/exceso, estado
 * - Se abre como overlay lateral o modal
 *
 * @module components/restaurante/InvestmentDetail
 */
import type { InvestmentItem } from "@/types";
import { CATEGORIES } from "./InvestmentModal";

function formatCurrency(value: number): string {
  const absValue = Math.abs(value);
  const formatted = absValue.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return value < 0 ? `-S/${formatted}` : `S/${formatted}`;
}

function getCategoryLabel(value: string): string {
  const cat = CATEGORIES.find((c) => c.value === value);
  return cat ? cat.label : value;
}

interface InvestmentDetailProps {
  item: InvestmentItem;
  onClose: () => void;
}

export function InvestmentDetail({ item, onClose }: InvestmentDetailProps) {
  const difference =
    item.actual_cost !== null
      ? item.estimated_cost - item.actual_cost
      : null;

  const isAhorro = difference !== null && difference >= 0;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-brand-text-primary">
            {item.name}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3">
          {/* Categoría */}
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-brand-text-secondary">Categoría</span>
            <span className="text-sm font-medium">
              {getCategoryLabel(item.category)}
            </span>
          </div>

          {/* Costo estimado */}
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-brand-text-secondary">
              Costo estimado
            </span>
            <span className="text-sm font-medium">
              {formatCurrency(item.estimated_cost)}
            </span>
          </div>

          {/* Costo real */}
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-brand-text-secondary">
              Costo real
            </span>
            <span className="text-sm font-medium">
              {item.actual_cost !== null
                ? formatCurrency(item.actual_cost)
                : "—"}
            </span>
          </div>

          {/* Ahorro / Exceso */}
          {difference !== null && (
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-brand-text-secondary">
                {isAhorro ? "Ahorro" : "Exceso"}
              </span>
              <span
                className={`text-sm font-medium ${
                  isAhorro ? "text-green-600" : "text-red-600"
                }`}
              >
                {isAhorro ? "-" : "+"}
                {formatCurrency(Math.abs(difference))}
                {isAhorro ? " (ahorro)" : " (exceso)"}
              </span>
            </div>
          )}

          {/* Recibo */}
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-brand-text-secondary">
              Código recibo
            </span>
            <span className="text-sm font-medium">
              {item.receipt_code || "—"}
            </span>
          </div>

          {/* Estado */}
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-brand-text-secondary">Estado</span>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                item.status === "acquired"
                  ? "bg-green-50 text-green-700"
                  : "bg-yellow-50 text-yellow-700"
              }`}
            >
              {item.status === "acquired" ? "🟢 Adquirido" : "🟡 Pendiente"}
            </span>
          </div>

          {/* Notas */}
          <div className="py-2">
            <span className="text-sm text-brand-text-secondary block mb-1">
              Notas
            </span>
            <p className="text-sm font-medium text-brand-text-primary whitespace-pre-wrap">
              {item.notes || "—"}
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-5 px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
