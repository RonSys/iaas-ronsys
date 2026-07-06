import { useState, useCallback, useEffect } from "react";
import {
  getBCSS,
  getIncomeStatement,
  getBalanceSheet,
  getRatios,
  getKardexInventory,
  getKardex,
  setupAccounting,
  getCashflow,
} from "@/services";
import type {
  BCSSResponse,
  IncomeStatementResponse,
  BalanceSheetResponse,
  RatioItem,
  KardexProduct,
  KardexRecord,
  FinancialReportResponse,
  InvestmentInput,
  CashflowResponse,
  CashflowQueryParams,
} from "@/types";

/**
 * Hook genérico para fetch con loading/error/refetch.
 */
function useFetch<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  return { data, loading, error, refetch: fetch };
}

export function useBCSS() {
  return useFetch(getBCSS);
}

export function useIncomeStatement() {
  return useFetch(getIncomeStatement);
}

export function useBalanceSheet() {
  return useFetch(getBalanceSheet);
}

export function useRatios() {
  return useFetch(getRatios);
}

export function useKardexInventory() {
  return useFetch(getKardexInventory);
}

export function useKardex(productCode: string) {
  return useFetch(() => getKardex(productCode));
}

/**
 * Hook para ejecutar una simulación (POST /setup).
 */
export function useSimulation() {
  const [result, setResult] = useState<FinancialReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const simulate = useCallback(async (input: InvestmentInput) => {
    setLoading(true);
    setError(null);
    try {
      const res = await setupAccounting(input);
      setResult(res);
      return res;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error en simulación";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, simulate };
}

// ═══════════════════════════════════════════════════════════
// Cashflow (HU-F1-007)
// ═══════════════════════════════════════════════════════════

/**
 * Hook para consultar flujo de caja con parámetros de vista y período.
 */
export function useCashflow(initialParams?: CashflowQueryParams) {
  const [data, setData] = useState<CashflowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<CashflowQueryParams>(
    initialParams ?? { view: "projected" },
  );

  const fetch = useCallback(async (p?: CashflowQueryParams) => {
    const queryParams = p ?? params;
    setLoading(true);
    setError(null);
    try {
      const result = await getCashflow(queryParams);
      setData(result);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando cashflow";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const changeParams = useCallback((p: CashflowQueryParams) => {
    setParams(p);
    fetch(p);
  }, [fetch]);

  return { data, loading, error, params, refetch: fetch, changeParams };
}

// Re-export types for convenience
export type {
  BCSSResponse,
  IncomeStatementResponse,
  BalanceSheetResponse,
  RatioItem,
  KardexProduct,
  KardexRecord,
  FinancialReportResponse,
  CashflowResponse,
  CashflowQueryParams,
};
