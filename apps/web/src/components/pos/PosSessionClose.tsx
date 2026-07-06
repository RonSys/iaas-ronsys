/**
 * PosSessionClose — Modal de arqueo y cierre de caja.
 *
 * Muestra:
 * - Efectivo esperado (calculado por el backend)
 * - Campo para efectivo real contado
 * - Diferencia automática
 * - Notas opcionales
 * - Botón confirmar cierre
 *
 * HU-F2-008: UI de apertura y cierre de caja
 *
 * @module components/pos/PosSessionClose
 */

import { useState, useMemo, type FormEvent } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import type { PosSessionCloseResponse } from "@/types";

interface PosSessionCloseProps {
  expectedCash: number;
  totalSales: number;
  onSubmit: (closingCash: number, notes: string) => Promise<PosSessionCloseResponse>;
  loading: boolean;
  error: string | null;
  onCancel: () => void;
}

export function PosSessionClose({
  expectedCash,
  totalSales,
  onSubmit,
  loading,
  error,
  onCancel,
}: PosSessionCloseProps) {
  const [actualCash, setActualCash] = useState("");
  const [notes, setNotes] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [closeResult, setCloseResult] = useState<PosSessionCloseResponse | null>(null);

  const difference = useMemo(() => {
    const n = Number(actualCash);
    if (isNaN(n) || actualCash === "") return null;
    return n - expectedCash;
  }, [actualCash, expectedCash]);

  const validate = (): string | null => {
    if (!actualCash.trim()) return "Ingrese el efectivo contado";
    const n = Number(actualCash);
    if (isNaN(n)) return "Ingrese un número válido";
    if (n < 0) return "El monto no puede ser negativo";
    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const vErr = validate();
    setValidationError(vErr);
    if (vErr) return;

    try {
      const result = await onSubmit(Number(actualCash), notes);
      setCloseResult(result);
    } catch {
      // error handled by parent
    }
  };

  // Show close result if available
  if (closeResult) {
    const closedAt = closeResult.session.closed_at
      ? new Date(closeResult.session.closed_at).toLocaleString("es-PE", {
          dateStyle: "medium",
          timeStyle: "short",
        })
      : "--";

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
        <div className="card max-w-md w-full">
          <div className="text-center">
            <span className="text-4xl">✅</span>
            <h3 className="text-xl font-bold text-brand-text-primary mt-2">
              Caja Cerrada
            </h3>
            <p className="text-sm text-brand-text-secondary mt-1">
              Turno finalizado exitosamente
            </p>
          </div>

          <div className="border-t border-gray-100 mt-4 pt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-brand-text-secondary">Total ventas:</span>
              <span className="font-bold">{fmtCurrency(closeResult.total_sales)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-brand-text-secondary">Efectivo esperado:</span>
              <span>{fmtCurrency(closeResult.cash_expected)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-brand-text-secondary">Diferencia:</span>
              <span
                className={`font-bold ${closeResult.difference === 0 ? "text-brand-success" : closeResult.difference > 0 ? "text-brand-success" : "text-brand-error"}`}
              >
                {closeResult.difference > 0 ? "+" : ""}
                {fmtCurrency(closeResult.difference)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-brand-text-secondary">Hora cierre:</span>
              <span>{closedAt}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="card max-w-md w-full">
        <h3 className="text-lg font-bold text-brand-text-primary mb-1">
          Arqueo de Caja
        </h3>
        <p className="text-sm text-brand-text-secondary mb-4">
          Contá el efectivo en caja y registrá el monto real.
        </p>

        {/* Summary */}
        <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 text-sm mb-4">
          <div className="flex justify-between">
            <span className="text-brand-text-secondary">Total ventas del turno:</span>
            <span className="font-bold text-brand-text-primary">
              {fmtCurrency(totalSales)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-text-secondary">Efectivo esperado:</span>
            <span className="font-bold text-brand-text-primary">
              {fmtCurrency(expectedCash)}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Efectivo real */}
          <div>
            <label className="block text-xs font-medium text-brand-text-secondary mb-1">
              Efectivo Real Contado (S/)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={actualCash}
              onChange={(e) => {
                setActualCash(e.target.value);
                setValidationError(null);
              }}
              placeholder="0.00"
              disabled={loading}
              className={`w-full px-3 py-2.5 rounded-lg border text-brand-text-primary text-lg text-center
                focus:outline-none focus:ring-2 focus:ring-brand-primary/20
                ${validationError ? "border-red-400" : "border-gray-300"}`}
              autoFocus
            />
            {validationError && (
              <p className="mt-1 text-xs text-red-500">{validationError}</p>
            )}
          </div>

          {/* Diferencia */}
          {difference !== null && (
            <div
              className={`p-3 rounded-lg text-center text-sm font-medium ${
                difference === 0
                  ? "bg-green-50 text-green-700"
                  : difference > 0
                    ? "bg-green-50 text-green-700"
                    : "bg-red-50 text-red-700"
              }`}
            >
              {difference === 0
                ? "✅ Caja cuadrada — sin diferencia"
                : difference > 0
                  ? `🟢 Sobrante: +${fmtCurrency(difference)}`
                  : `🔴 Faltante: ${fmtCurrency(difference)}`}
            </div>
          )}

          {/* Notas */}
          <div>
            <label className="block text-xs font-medium text-brand-text-secondary mb-1">
              Notas (opcional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ej: La diferencia se debe a..."
              disabled={loading}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm
                focus:outline-none focus:ring-2 focus:ring-brand-primary/20
                resize-none"
            />
          </div>

          {error && (
            <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 py-2.5 rounded-lg font-medium text-sm border border-gray-300
                text-brand-text-primary hover:bg-gray-50 transition-colors
                disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 rounded-lg font-medium text-sm transition-all
                bg-brand-primary text-white hover:opacity-90
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Cerrando...
                </span>
              ) : (
                "Confirmar Cierre"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
