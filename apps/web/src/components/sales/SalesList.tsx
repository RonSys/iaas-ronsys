/**
 * SalesList — Tabla paginada de ventas con filtros.
 *
 * Fila clickeable → abre SaleDetail drawer.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module components/sales/SalesList
 */
import { useState, useCallback } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import { SaleFilters } from "./SaleFilters";
import { SaleDetail } from "./SaleDetail";
import { TicketPreview } from "./TicketPreview";
import type { Sale, SaleFilters as SaleFiltersType } from "@/types";

interface SalesListProps {
  sales: Sale[];
  total: number;
  page: number;
  limit: number;
  loading: boolean;
  error: string | null;
  filters: SaleFiltersType;
  onFiltersChange: (filters: SaleFiltersType) => void;
  onFetchDetail: (saleId: number) => Promise<any>;
  onFetchTicket: (saleId: number) => Promise<{ ticket_text: string }>;
  onVoidSale: (saleId: number, reason: string) => Promise<any>;
  detailLoading: boolean;
  detailError: string | null;
  ticketLoading: boolean;
  ticketError: string | null;
  voidLoading: boolean;
}

export function SalesList({
  sales,
  total,
  page,
  limit,
  loading,
  error,
  filters,
  onFiltersChange,
  onFetchDetail,
  onFetchTicket,
  onVoidSale,
  detailLoading,
  detailError,
  ticketLoading,
  ticketError,
  voidLoading,
}: SalesListProps) {
  const [selectedSaleId, setSelectedSaleId] = useState<number | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [showTicket, setShowTicket] = useState(false);
  const [ticketText, setTicketText] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  const totalPages = Math.ceil(total / limit);

  const handleRowClick = useCallback(
    async (saleId: number) => {
      setSelectedSaleId(saleId);
      setShowDetail(true);
      setShowTicket(false);
      try {
        const d = await onFetchDetail(saleId);
        setDetail(d);
      } catch {
        // handled by parent
      }
    },
    [onFetchDetail],
  );

  const handleShowTicket = useCallback(async () => {
    if (!selectedSaleId) return;
    setShowTicket(true);
    try {
      const t = await onFetchTicket(selectedSaleId);
      setTicketText(t.ticket_text);
    } catch {
      // handled
    }
  }, [selectedSaleId, onFetchTicket]);

  const handleVoid = useCallback(
    async (reason: string) => {
      if (!selectedSaleId) return;
      const result = await onVoidSale(selectedSaleId, reason);
      setDetail((prev: any) => (prev ? { ...prev, is_voided: true, void_reason: reason } : prev));
      // Refresh list
      onFiltersChange({ ...filters, page });
      return result;
    },
    [selectedSaleId, onVoidSale, onFiltersChange, filters, page],
  );

  const handleCloseDrawer = () => {
    setShowDetail(false);
    setShowTicket(false);
    setDetail(null);
    setTicketText(null);
  };

  const handlePageChange = (newPage: number) => {
    onFiltersChange({ ...filters, page: newPage });
  };

  const formatDateTime = (date: string, time: string) => {
    return `${date} ${time?.slice(0, 5) ?? ""}`;
  };

  return (
    <div>
      <SaleFilters filters={filters} onChange={onFiltersChange} loading={loading} />

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-brand-text-secondary uppercase tracking-wider">
              <th className="py-3 text-left"># Venta</th>
              <th className="py-3 text-left">Fecha/Hora</th>
              <th className="py-3 text-right">Total</th>
              <th className="py-3 text-left">Pago</th>
              <th className="py-3 text-left">Estado</th>
              <th className="py-3 text-left">Cajero</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }, (_, i) => (
                <tr key={i} className="border-b border-gray-50">
                  {Array.from({ length: 6 }, (_, j) => (
                    <td key={j} className="py-3 px-1">
                      <div className="h-4 bg-gray-200 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : sales.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-brand-text-secondary">
                  No se encontraron ventas
                </td>
              </tr>
            ) : (
              sales.map((sale) => (
                <tr
                  key={sale.id}
                  onClick={() => handleRowClick(sale.id)}
                  className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="py-3 font-medium text-brand-primary">
                    {sale.sale_number}
                  </td>
                  <td className="py-3 text-xs">
                    {formatDateTime(sale.sale_date, sale.sale_time)}
                  </td>
                  <td className="py-3 text-right font-bold">
                    {fmtCurrency(sale.total)}
                  </td>
                  <td className="py-3 text-xs">
                    {sale.payment_methods?.join(", ") ?? "--"}
                  </td>
                  <td className="py-3">
                    {sale.is_voided ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
                        Anulada
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
                        Activa
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-xs">{sale.cashier_name ?? "--"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm">
          <span className="text-brand-text-secondary">
            {total} ventas · Página {page} de {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1 || loading}
              className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-50
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ← Ant
            </button>
            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages || loading}
              className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-50
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Sig →
            </button>
          </div>
        </div>
      )}

      {/* Drawers */}
      {showDetail && !showTicket && (
        <SaleDetail
          sale={detail}
          loading={detailLoading}
          error={detailError}
          onShowTicket={handleShowTicket}
          onVoid={handleVoid}
          voidLoading={voidLoading}
          onClose={handleCloseDrawer}
        />
      )}

      {showTicket && (
        <TicketPreview
          ticketText={ticketText}
          loading={ticketLoading}
          error={ticketError}
          onClose={handleCloseDrawer}
        />
      )}
    </div>
  );
}
