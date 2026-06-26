/**
 * PosSessionStatus — Resumen de sesión abierta.
 *
 * Muestra hora de apertura, totales acumulados del turno,
 * y botón para cerrar caja que abre el modal de arqueo.
 *
 * HU-F2-008: UI de apertura y cierre de caja
 *
 * @module components/pos/PosSessionStatus
 */

import { fmtCurrency } from "../dashboard/KPICard";
import type { PosSession } from "@/types";

interface PosSessionStatusProps {
  session: PosSession;
  onCloseRequest: () => void;
}

export function PosSessionStatus({
  session,
  onCloseRequest,
}: PosSessionStatusProps) {
  const openedAt = new Date(session.opened_at).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div className="max-w-lg mx-auto">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-2xl mr-2">🔒</span>
            <span className="text-lg font-bold text-brand-success">Caja Abierta</span>
          </div>
          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
            Activo
          </span>
        </div>

        <div className="border-t border-gray-100 pt-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-brand-text-secondary">Apertura:</span>
            <span className="text-brand-text-primary font-medium">{openedAt}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-brand-text-secondary">Monto inicial:</span>
            <span className="text-brand-text-primary font-medium">
              {fmtCurrency(session.opening_cash)}
            </span>
          </div>
          {session.total_sales !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-brand-text-secondary">Total ventas:</span>
              <span className="text-brand-text-primary font-bold">
                {fmtCurrency(session.total_sales)}
              </span>
            </div>
          )}
          {session.sale_count !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-brand-text-secondary">Ventas del turno:</span>
              <span className="text-brand-text-primary font-medium">
                {session.sale_count}
              </span>
            </div>
          )}
        </div>

        {/* Desglose por método de pago */}
        <div className="border-t border-gray-100 pt-3 mt-3">
          <h4 className="text-xs font-semibold text-brand-text-secondary uppercase tracking-wider mb-2">
            Ventas por método de pago
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {session.cash_sales !== undefined && session.cash_sales > 0 && (
              <div className="flex justify-between">
                <span>💰 Efectivo</span>
                <span className="font-medium">{fmtCurrency(session.cash_sales)}</span>
              </div>
            )}
            {session.card_sales !== undefined && session.card_sales > 0 && (
              <div className="flex justify-between">
                <span>💳 Tarjeta</span>
                <span className="font-medium">{fmtCurrency(session.card_sales)}</span>
              </div>
            )}
            {session.yape_sales !== undefined && session.yape_sales > 0 && (
              <div className="flex justify-between">
                <span>📱 Yape</span>
                <span className="font-medium">{fmtCurrency(session.yape_sales)}</span>
              </div>
            )}
            {session.plin_sales !== undefined && session.plin_sales > 0 && (
              <div className="flex justify-between">
                <span>📱 Plin</span>
                <span className="font-medium">{fmtCurrency(session.plin_sales)}</span>
              </div>
            )}
            {session.transfer_sales !== undefined && session.transfer_sales > 0 && (
              <div className="flex justify-between">
                <span>🏦 Transferencia</span>
                <span className="font-medium">{fmtCurrency(session.transfer_sales)}</span>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={onCloseRequest}
          className="w-full mt-4 py-2.5 rounded-lg font-medium text-sm transition-all
            bg-brand-error text-white hover:opacity-90"
        >
          🔒 Cerrar Caja
        </button>
      </div>
    </div>
  );
}
