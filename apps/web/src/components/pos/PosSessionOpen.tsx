/**
 * PosSessionOpen — Formulario de apertura de caja.
 *
 * HU-F2-008: UI de apertura y cierre de caja
 *
 * @module components/pos/PosSessionOpen
 */

import { useState, type FormEvent } from "react";

interface PosSessionOpenProps {
  onSubmit: (openingCash: number) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function PosSessionOpen({ onSubmit, loading, error }: PosSessionOpenProps) {
  const [amount, setAmount] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const validate = (value: string): string | null => {
    if (!value.trim()) return "El monto inicial es requerido";
    const n = Number(value);
    if (isNaN(n)) return "Ingrese un número válido";
    if (n < 0) return "El monto no puede ser negativo";
    if (n === 0) return "El monto no puede ser cero";
    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const vErr = validate(amount);
    setValidationError(vErr);
    if (vErr) return;

    try {
      await onSubmit(Number(amount));
    } catch {
      // error handled by parent
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="card text-center">
        <span className="text-4xl">🔓</span>
        <h2 className="text-xl font-bold text-brand-text-primary mt-3">
          Caja Cerrada
        </h2>
        <p className="text-sm text-brand-text-secondary mt-1">
          Ingresá el monto inicial para abrir la caja
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-brand-text-secondary mb-1 text-left">
              Monto Inicial (S/)
            </label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                setValidationError(null);
              }}
              placeholder="0.00"
              disabled={loading}
              className={`w-full px-3 py-2.5 rounded-lg border text-brand-text-primary text-lg text-center
                focus:outline-none focus:ring-2 focus:ring-brand-primary/20
                disabled:opacity-50
                ${validationError ? "border-red-400" : "border-gray-300"}`}
              autoFocus
            />
            {validationError && (
              <p className="mt-1 text-xs text-red-500">{validationError}</p>
            )}
          </div>

          {error && (
            <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg font-medium text-sm transition-all
              bg-brand-primary text-white hover:opacity-90
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Abriendo...
              </span>
            ) : (
              "🔓 Abrir Caja"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
