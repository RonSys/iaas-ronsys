/**
 * useSales — Hook para gestión de ventas (crear, listar, detalle, anular).
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module hooks/useSales
 */

import { useState, useCallback } from "react";
import {
  createSale,
  getSales,
  getSaleDetail,
  getSaleTicket,
  voidSale,
  getPaymentMethods,
  searchKardexProducts,
} from "@/services";
import type {
  SaleCreateRequest,
  SaleDetail,
  SaleFilters,
  SaleListResponse,
  TicketResponse,
  VoidSaleRequest,
  PaymentMethodsResponse,
  KardexProduct,
} from "@/types";

/** Hook para crear una venta nueva */
export function useSaleCreate() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SaleDetail | null>(null);

  const submit = useCallback(async (data: SaleCreateRequest) => {
    setLoading(true);
    setError(null);
    try {
      const sale = await createSale(data);
      setResult(sale);
      return sale;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al crear venta";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { submit, result, loading, error, reset };
}

/** Hook para listar ventas con filtros y paginación */
export function useSalesList() {
  const [data, setData] = useState<SaleListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<SaleFilters>({});

  const fetch = useCallback(async (f?: SaleFilters) => {
    const q = f ?? filters;
    setLoading(true);
    setError(null);
    try {
      const result = await getSales(q);
      setData(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando ventas";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const changeFilters = useCallback((f: SaleFilters) => {
    setFilters(f);
    fetch(f);
  }, [fetch]);

  return { data, loading, error, filters, fetch, changeFilters };
}

/** Hook para obtener detalle de una venta */
export function useSaleDetail(saleId: number | null) {
  const [data, setData] = useState<SaleDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (id?: number) => {
    const targetId = id ?? saleId;
    if (!targetId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getSaleDetail(targetId);
      setData(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando venta";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [saleId]);

  return { data, loading, error, fetch };
}

/** Hook para obtener ticket de venta */
export function useSaleTicket() {
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (saleId: number, format: "json" | "text" = "text") => {
    setLoading(true);
    setError(null);
    try {
      const result = await getSaleTicket(saleId, format);
      setTicket(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando ticket";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { ticket, loading, error, fetch };
}

/** Hook para anular venta */
export function useSaleVoid() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const voidIt = useCallback(async (saleId: number, data: VoidSaleRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await voidSale(saleId, data);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al anular venta";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { void: voidIt, loading, error };
}

/** Hook para obtener métodos de pago habilitados */
export function usePaymentMethods() {
  const [methods, setMethods] = useState<PaymentMethodsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getPaymentMethods();
      setMethods(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando métodos";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { methods, loading, error, fetch };
}

/** Hook para búsqueda de productos de kárdex */
export function useProductSearch() {
  const [results, setResults] = useState<KardexProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const search = useCallback(async (q: string) => {
    setQuery(q);
    if (!q || q.length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const r = await searchKardexProducts(q);
      setResults(r);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error buscando productos";
      setError(msg);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setQuery("");
    setError(null);
  }, []);

  return { results, loading, error, query, search, clear };
}
