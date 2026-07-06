/**
 * SaleDetail — Drawer/modal con detalle completo de venta.
 *
 * Muestra ítems, pagos, datos especializados (restaurante/ferretería).
 * Incluye botones para ticket y anulación.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module components/sales/SaleDetail
 */
import { useState } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import type { SaleDetail as SaleDetailType } from "@/types";

interface SaleDetailProps {
  sale: SaleDetailType | null;
  loading: boolean;
  error: string | null;
  onShowTicket: () => void;
  onVoid: (reason: string) => Promise<void>;
  voidLoading: boolean;
  onClose: () => void;
}

export function SaleDetail({
  sale,
  loading,
  error,
  onShowTicket,
  onVoid,
  voidLoading,
  onClose,
}: SaleDetailProps) {
  const [voidReason, setVoidReason] = useState("");
  const [showVoidConfirm, setShowVoidConfirm] = useState(false);

  const handleVoid = async () => {
    if (!voidReason.trim()) return;
    try {
      await onVoid(voidReason);
      setShowVoidConfirm(false);
    } catch {
      // handled by parent
    }
  };

  if (!sale && !loading) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full md:w-[480px] bg-white shadow-2xl border-l overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between z-10">
        <div>
          <h3 className="font-bold text-brand-text-primary">
            Venta #{sale?.sale_number ?? "--"}
          </h3>
          <p className="text-xs text-brand-text-secondary">
            {sale?.sale_date} · {sale?.sale_time}
          </p>
        </div>
        <div className="flex gap-2">
          {sale?.is_voided && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
              Anulada
            </span>
          )}
          <button
            onClick={onClose}
            className="px-3 py-1 text-xs rounded-lg border border-gray-300 text-brand-text-secondary hover:bg-gray-50"
          >
            Cerrar
          </button>
        </div>
      </div>

      <div className="p-4">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            {error}
          </div>
        )}

        {sale && (
          <div className="space-y-4">
            {/* Info general */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-xs text-brand-text-secondary">Cajero</span>
                <p className="font-medium">{sale.cashier_name ?? "--"}</p>
              </div>
              <div>
                <span className="text-xs text-brand-text-secondary">Tipo</span>
                <p className="font-medium">{sale.business_type}</p>
              </div>
              <div>
                <span className="text-xs text-brand-text-secondary">Cliente</span>
                <p className="font-medium">{sale.customer_name ?? "--"}</p>
              </div>
              <div>
                <span className="text-xs text-brand-text-secondary">Doc</span>
                <p className="font-medium">{sale.customer_doc ?? "--"}</p>
              </div>
            </div>

            {/* Items */}
            <div>
              <h4 className="text-xs font-semibold text-brand-text-secondary uppercase tracking-wider mb-2">
                Ítems
              </h4>
              <div className="space-y-1">
                {sale.items?.map((item, i) => (
                  <div
                    key={i}
                    className="flex justify-between text-sm bg-gray-50 rounded px-3 py-2"
                  >
                    <div>
                      <span className="font-medium">{item.item_name}</span>
                      <span className="text-brand-text-secondary ml-2">
                        ×{item.quantity}
                      </span>
                    </div>
                    <span>{fmtCurrency(item.total)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Payments */}
            <div>
              <h4 className="text-xs font-semibold text-brand-text-secondary uppercase tracking-wider mb-2">
                Pagos
              </h4>
              <div className="space-y-1">
                {sale.payments?.map((p, i) => (
                  <div
                    key={i}
                    className="flex justify-between text-sm bg-gray-50 rounded px-3 py-2"
                  >
                    <span className="capitalize">{p.payment_method}</span>
                    <span className="font-medium">{fmtCurrency(p.amount)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Restaurant data */}
            {sale.restaurant_data && (
              <div className="border border-orange-200 bg-orange-50/30 rounded-lg p-3">
                <h4 className="text-xs font-semibold text-orange-800 mb-2">🍽️ Datos Restaurante</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>Mesa: <strong>{sale.restaurant_data.table_number}</strong></div>
                  <div>Comensales: <strong>{sale.restaurant_data.guests}</strong></div>
                  <div>Tipo: <strong>{sale.restaurant_data.order_type}</strong></div>
                  <div>Mesero: <strong>{sale.restaurant_data.waiter_name}</strong></div>
                  {sale.restaurant_data.tip_amount > 0 && (
                    <div>Propina: <strong>{fmtCurrency(sale.restaurant_data.tip_amount)}</strong></div>
                  )}
                </div>
              </div>
            )}

            {/* Hardware data */}
            {sale.hardware_data && (
              <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-3">
                <h4 className="text-xs font-semibold text-blue-800 mb-2">🔧 Datos Ferretería</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>Comprobante: <strong>{sale.hardware_data.invoice_type}</strong></div>
                  <div>Doc: <strong>{sale.hardware_data.customer_doc}</strong></div>
                  {sale.hardware_data.warranty_months > 0 && (
                    <div>Garantía: <strong>{sale.hardware_data.warranty_months} meses</strong></div>
                  )}
                  {sale.hardware_data.requires_install && <div>Instalación: <strong>Sí</strong></div>}
                </div>
              </div>
            )}

            {/* Totals */}
            <div className="border-t pt-3 space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-brand-text-secondary">Subtotal</span>
                <span>{fmtCurrency(sale.subtotal)}</span>
              </div>
              {sale.discount_total > 0 && (
                <div className="flex justify-between text-brand-error">
                  <span>Descuento</span>
                  <span>-{fmtCurrency(sale.discount_total)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-brand-text-secondary">IGV</span>
                <span>{fmtCurrency(sale.tax_total)}</span>
              </div>
              {sale.tip_amount > 0 && (
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Propina</span>
                  <span>{fmtCurrency(sale.tip_amount)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-lg pt-2 border-t">
                <span>Total</span>
                <span>{fmtCurrency(sale.total)}</span>
              </div>
            </div>

            {/* Actions */}
            {!sale.is_voided && (
              <div className="flex gap-2 pt-2">
                <button
                  onClick={onShowTicket}
                  className="flex-1 py-2 rounded-lg text-sm border border-gray-300
                    text-brand-text-primary hover:bg-gray-50"
                >
                  🧾 Ver Ticket
                </button>
                <button
                  onClick={() => setShowVoidConfirm(true)}
                  className="flex-1 py-2 rounded-lg text-sm border border-red-300
                    text-red-600 hover:bg-red-50"
                >
                  ❌ Anular
                </button>
              </div>
            )}

            {/* Void reason */}
            {sale.is_voided && sale.void_reason && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                <strong>Motivo anulación:</strong> {sale.void_reason}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Void Confirmation Modal */}
      {showVoidConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
          <div className="bg-white rounded-xl shadow-2xl p-6 max-w-sm w-full">
            <h4 className="font-bold text-brand-text-primary mb-1">Anular Venta</h4>
            <p className="text-sm text-brand-text-secondary mb-3">
              Esta acción no se puede deshacer. Ingresá el motivo:
            </p>
            <textarea
              value={voidReason}
              onChange={(e) => setVoidReason(e.target.value)}
              placeholder="Motivo de la anulación"
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300
                focus:outline-none focus:ring-2 focus:ring-brand-primary/20 resize-none"
              autoFocus
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setShowVoidConfirm(false)}
                className="flex-1 py-2 rounded-lg text-sm border border-gray-300
                  text-brand-text-primary hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleVoid}
                disabled={!voidReason.trim() || voidLoading}
                className="flex-1 py-2 rounded-lg text-sm bg-red-600 text-white
                  hover:opacity-90 disabled:opacity-50"
              >
                {voidLoading ? "Anulando..." : "Confirmar Anulación"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

