/**
 * PaymentSection — Sección de pagos múltiples.
 *
 * Permite registrar múltiples métodos de pago, muestra
 * el total pagado y el saldo pendiente.
 *
 * HU-F2-009: UI de registro de venta base
 *
 * @module components/sales/PaymentSection
 */
import { useState, useMemo } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import type { SalePayment, PaymentMethod } from "@/types";

const METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: "💰 Efectivo",
  card: "💳 Tarjeta",
  yape: "📱 Yape",
  plin: "📱 Plin",
  transfer: "🏦 Transferencia",
};

const ALL_METHODS: PaymentMethod[] = ["cash", "card", "yape", "plin", "transfer"];

interface PaymentSectionProps {
  total: number;
  payments: SalePayment[];
  onAddPayment: (payment: SalePayment) => void;
  onRemovePayment: (index: number) => void;
  error?: string | null;
}

export function PaymentSection({
  total,
  payments,
  onAddPayment,
  onRemovePayment,
  error,
}: PaymentSectionProps) {
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [amount, setAmount] = useState("");
  const [ref, setRef] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const paid = useMemo(
    () => payments.reduce((sum, p) => sum + p.amount, 0),
    [payments],
  );

  const pending = total - paid;
  const isComplete = pending <= 0.005; // floating tolerance

  const handleAdd = () => {
    const n = Number(amount);
    if (!amount || isNaN(n) || n <= 0) {
      setValidationError("Ingrese un monto válido");
      return;
    }
    setValidationError(null);
    onAddPayment({
      payment_method: method,
      amount: n,
      reference: ref.trim() || null,
    });
    setAmount("");
    setRef("");
  };

  return (
    <div>
      <h4 className="text-sm font-semibold text-brand-text-primary mb-2">
        Método de Pago
      </h4>

      {/* Existing payments */}
      {payments.length > 0 && (
        <div className="space-y-1 mb-3">
          {payments.map((p, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-1.5 text-sm"
            >
              <span>{METHOD_LABELS[p.payment_method]}</span>
              <div className="flex items-center gap-2">
                <span className="font-medium">{fmtCurrency(p.amount)}</span>
                {p.reference && (
                  <span className="text-xs text-brand-text-secondary">
                    Ref: {p.reference}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemovePayment(i)}
                  className="text-red-400 hover:text-red-600"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add payment */}
      {!isComplete && (
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="block text-xs text-brand-text-secondary mb-0.5">
              Método
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as PaymentMethod)}
              className="px-2 py-1.5 text-sm rounded-lg border border-gray-300"
            >
              {ALL_METHODS.map((m) => (
                <option key={m} value={m}>
                  {METHOD_LABELS[m]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-brand-text-secondary mb-0.5">
              Monto
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={pending}
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                setValidationError(null);
              }}
              placeholder="0.00"
              className="w-24 px-2 py-1.5 text-sm rounded-lg border border-gray-300 text-right
                focus:outline-none focus:ring-1 focus:ring-brand-primary/20"
            />
          </div>
          <div>
            <label className="block text-xs text-brand-text-secondary mb-0.5">
              Ref
            </label>
            <input
              type="text"
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              placeholder="#"
              className="w-20 px-2 py-1.5 text-sm rounded-lg border border-gray-300
                focus:outline-none focus:ring-1 focus:ring-brand-primary/20"
            />
          </div>
          <button
            type="button"
            onClick={handleAdd}
            className="px-3 py-1.5 text-sm rounded-lg bg-brand-primary text-white hover:opacity-90"
          >
            + Agregar
          </button>
        </div>
      )}

      {validationError && (
        <p className="mt-1 text-xs text-red-500">{validationError}</p>
      )}

      {/* Summary */}
      <div className="flex justify-between items-center mt-3 pt-2 border-t text-sm">
        <span className="text-brand-text-secondary">Pagado</span>
        <span className={`font-bold ${isComplete ? "text-brand-success" : "text-brand-text-primary"}`}>
          {fmtCurrency(paid)}
        </span>
      </div>
      {!isComplete && (
        <div className="flex justify-between items-center text-sm mt-1">
          <span className="text-brand-error font-medium">Pendiente</span>
          <span className="font-bold text-brand-error">{fmtCurrency(pending)}</span>
        </div>
      )}
      {isComplete && payments.length > 0 && (
        <div className="text-xs text-brand-success mt-1">✅ Pago completo</div>
      )}

      {error && (
        <div className="mt-2 p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
          {error}
        </div>
      )}
    </div>
  );
}
