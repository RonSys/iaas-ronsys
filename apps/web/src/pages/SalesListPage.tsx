/**
 * SalesListPage — Página de listado de ventas con filtros.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module pages/SalesList
 */
import { useEffect, useState, useCallback } from "react";
import { useSalesList, useSaleVoid } from "@/hooks/useSales";
import { SalesList } from "@/components/sales/SalesList";
import { Skeleton } from "@/components/dashboard/KPICard";
import type { SaleFilters, SaleDetail as SaleDetailType } from "@/types";

const DEFAULT_FILTERS: SaleFilters = { page: 1, limit: 20 };

export function SalesListPage() {
  const { data, loading, error, filters, changeFilters } = useSalesList();
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [ticketLoading, setTicketLoading] = useState(false);
  const [ticketError, setTicketError] = useState<string | null>(null);
  const voidOp = useSaleVoid();

  // Fetch initial list
  useEffect(() => {
    changeFilters(DEFAULT_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFetchDetail = useCallback(async (saleId: number): Promise<SaleDetailType> => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const response = await fetch(`/api/sales/sale/${saleId}`);
      if (!response.ok) throw new Error("Error cargando detalle");
      const d = await response.json();
      return d;
    } catch (err: any) {
      setDetailError(err.message);
      throw err;
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleFetchTicket = useCallback(async (saleId: number) => {
    setTicketLoading(true);
    setTicketError(null);
    try {
      const response = await fetch(`/api/sales/sale/${saleId}/ticket?format=text`);
      if (!response.ok) throw new Error("Error cargando ticket");
      return await response.json();
    } catch (err: any) {
      setTicketError(err.message);
      throw err;
    } finally {
      setTicketLoading(false);
    }
  }, []);

  const handleVoid = useCallback(
    async (saleId: number, reason: string) => {
      await voidOp.void(saleId, { reason });
      // Re-fetch list
      changeFilters({ ...filters });
    },
    [voidOp, changeFilters, filters],
  );

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            📋 Ventas
          </h2>
          <p className="text-sm text-brand-text-secondary">
            {data?.total ?? 0} ventas registradas
          </p>
        </div>
      </div>

      <SalesList
        sales={data?.sales ?? []}
        total={data?.total ?? 0}
        page={filters.page ?? 1}
        limit={filters.limit ?? 20}
        loading={loading}
        error={error}
        filters={filters}
        onFiltersChange={changeFilters}
        onFetchDetail={handleFetchDetail}
        onFetchTicket={handleFetchTicket}
        onVoidSale={handleVoid}
        detailLoading={detailLoading}
        detailError={detailError}
        ticketLoading={ticketLoading}
        ticketError={ticketError}
        voidLoading={voidOp.loading}
      />
    </div>
  );
}
