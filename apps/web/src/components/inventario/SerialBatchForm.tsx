/**
 * SerialBatchForm — Formulario de registro masivo de seriales.
 *
 * DT-F0-009 HU-F0-009-04: Registro masivo de seriales
 *
 * Tabla editable con columnas: Serial Number, Fecha Compra, Precio Costo, Notas
 * Botón "+ Agregar fila" para añadir más seriales en lote.
 *
 * @module components/inventario/SerialBatchForm
 */

import { useState, type FormEvent } from "react";
import type { SerialCreateRequest } from "@/types";

interface SerialBatchFormProps {
  productName: string;
  defaultWarrantyMonths: number;
  submitting: boolean;
  onSave: (serials: SerialCreateRequest[]) => void;
  onCancel: () => void;
}

interface SerialRow {
  key: string;
  serialNumber: string;
  purchaseDate: string;
  costPrice: string;
  notes: string;
}

let rowCounter = 0;
function nextKey(): string {
  rowCounter += 1;
  return `row-${Date.now()}-${rowCounter}`;
}

export function SerialBatchForm({
  productName,
  defaultWarrantyMonths,
  submitting,
  onSave,
  onCancel,
}: SerialBatchFormProps) {
  const todayStr = new Date().toISOString().slice(0, 10);

  const [rows, setRows] = useState<SerialRow[]>([
    { key: nextKey(), serialNumber: "", purchaseDate: todayStr, costPrice: "", notes: "" },
  ]);
  const [error, setError] = useState<string | null>(null);

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      { key: nextKey(), serialNumber: "", purchaseDate: todayStr, costPrice: "", notes: "" },
    ]);
    setError(null);
  };

  const removeRow = (key: string) => {
    if (rows.length <= 1) return;
    setRows((prev) => prev.filter((r) => r.key !== key));
  };

  const updateRow = (key: string, field: keyof SerialRow, value: string) => {
    setRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, [field]: value } : r)),
    );
    setError(null);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    // Validar
    const emptySerials = rows.filter((r) => !r.serialNumber.trim());
    if (emptySerials.length > 0) {
      setError("Todos los números de serie son obligatorios");
      return;
    }

    // Check duplicates
    const numbers = rows.map((r) => r.serialNumber.trim());
    const unique = new Set(numbers);
    if (unique.size !== numbers.length) {
      setError("Hay números de serie duplicados en el lote");
      return;
    }

    const serials: SerialCreateRequest[] = rows.map((r) => ({
      serial_number: r.serialNumber.trim(),
      purchase_date: r.purchaseDate || todayStr,
      cost_price: r.costPrice.trim() ? Number(r.costPrice) : 0,
      notes: r.notes.trim() || undefined,
    }));

    onSave(serials);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="text-sm text-brand-text-secondary">
        Registrando seriales para: <strong className="text-brand-text-primary">{productName}</strong>
        {defaultWarrantyMonths > 0 && (
          <span className="ml-2 text-xs">
            · Garantía: {defaultWarrantyMonths} meses
          </span>
        )}
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          ⚠️ {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-brand-text-secondary">
              <th className="py-2 px-2 font-medium w-8">#</th>
              <th className="py-2 px-2 font-medium required">Número de Serie</th>
              <th className="py-2 px-2 font-medium hidden sm:table-cell">Fecha Compra</th>
              <th className="py-2 px-2 font-medium hidden md:table-cell text-right">Precio Costo</th>
              <th className="py-2 px-2 font-medium hidden lg:table-cell">Notas</th>
              <th className="py-2 px-2 font-medium w-10"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={row.key} className="border-b border-gray-100">
                <td className="py-1.5 px-2 text-brand-text-secondary text-xs">
                  {idx + 1}
                </td>
                <td className="py-1.5 px-2">
                  <input
                    type="text"
                    value={row.serialNumber}
                    onChange={(e) => updateRow(row.key, "serialNumber", e.target.value)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                    placeholder="SN-001"
                    autoFocus={idx === 0}
                  />
                </td>
                <td className="py-1.5 px-2 hidden sm:table-cell">
                  <input
                    type="date"
                    value={row.purchaseDate}
                    onChange={(e) => updateRow(row.key, "purchaseDate", e.target.value)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                  />
                </td>
                <td className="py-1.5 px-2 hidden md:table-cell">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={row.costPrice}
                    onChange={(e) => updateRow(row.key, "costPrice", e.target.value)}
                    className="w-24 px-2 py-1.5 border border-gray-300 rounded text-xs text-right focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                    placeholder="0.00"
                  />
                </td>
                <td className="py-1.5 px-2 hidden lg:table-cell">
                  <input
                    type="text"
                    value={row.notes}
                    onChange={(e) => updateRow(row.key, "notes", e.target.value)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                    placeholder="Opcional"
                  />
                </td>
                <td className="py-1.5 px-2">
                  <button
                    type="button"
                    onClick={() => removeRow(row.key)}
                    disabled={rows.length <= 1}
                    className="p-1 rounded hover:bg-red-100 text-xs text-gray-400 hover:text-red-600 disabled:opacity-30"
                    title="Eliminar fila"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={addRow}
        className="text-sm text-brand-primary hover:underline flex items-center gap-1"
      >
        <span>+</span> Agregar fila
      </button>

      <div className="flex gap-3 justify-end pt-3 border-t">
        <button
          type="button"
          onClick={onCancel}
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
            : `Registrar ${rows.length} serial${rows.length > 1 ? "es" : ""}`}
        </button>
      </div>
    </form>
  );
}
