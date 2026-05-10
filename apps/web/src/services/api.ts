/**
 * API Client — Fetch wrapper con interceptors de auth.
 *
 * - Inyecta Authorization: Bearer + X-Tenant-ID en cada request
 * - Detecta 401, refresca token automáticamente y reintenta
 * - Maneja requests concurrentes: solo UN refresh en vuelo a la vez
 * - Excluye /auth/* y /health del interceptor (evita bucles)
 *
 * US-19: Interceptor 401 con Refresh Automático
 *
 * @module services/api
 */

import { authStore } from "./authStore";

const BASE = "/api";

/** Rutas que NO deben pasar por el interceptor de auth */
const SKIP_AUTH = ["/auth/", "/health"];

/** Rutas que NO deben reintentarse en caso de 401 */
const SKIP_RETRY = ["/auth/login", "/auth/refresh", "/auth/logout"];

// ─── Refresh queue (evita race condition) ────────────────

let refreshPromise: Promise<string | null> | null = null;

function getRefreshPromise(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = authStore.refresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

// ─── Core ─────────────────────────────────────────────────

function shouldSkipAuth(path: string): boolean {
  return SKIP_AUTH.some((prefix) => path.startsWith(prefix));
}

function shouldSkipRetry(path: string): boolean {
  return SKIP_RETRY.some((p) => path === p);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE}${path}`;

  // Headers base
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };

  // Inyectar auth headers (excepto rutas excluidas)
  if (!shouldSkipAuth(path)) {
    const token = authStore.getAccessToken();
    const tenantId = authStore.getTenantId();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (tenantId) headers["X-Tenant-ID"] = String(tenantId);
  }

  let res = await fetch(url, { ...options, headers });

  // ─── Interceptor 401 ──────────────────────────────────
  if (res.status === 401 && !shouldSkipRetry(path)) {
    const newToken = await getRefreshPromise();

    if (newToken) {
      // Reintentar con nuevo token
      headers["Authorization"] = `Bearer ${newToken}`;
      const tenantId = authStore.getTenantId();
      if (tenantId) headers["X-Tenant-ID"] = String(tenantId);

      res = await fetch(url, { ...options, headers });
    } else {
      // Refresh falló → logout
      authStore.triggerLogout();
      throw new Error("Sesión expirada");
    }
  }

  // ─── Error handling ───────────────────────────────────
  if (!res.ok) {
    // Para errores de auth, incluir el status en el mensaje
    // para que LoginPage pueda parsearlo
    if (res.status === 401 || res.status === 423 || res.status === 429) {
      const errorData = await res.json().catch(() => ({}));
      const detail = errorData.detail ?? res.statusText;
      throw new Error(`${res.status} ${detail}`);
    }
    const errorText = await res.text().catch(() => res.statusText);
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }

  return res.json() as Promise<T>;
}

// ═══════════════════════════════════════════════════════════
// Health
// ═══════════════════════════════════════════════════════════

export async function getHealth(): Promise<{ status: string; service: string; version: string }> {
  return request("/health");
}

// ═══════════════════════════════════════════════════════════
// Setup
// ═══════════════════════════════════════════════════════════

export async function setupAccounting(
  data: import("@/types").InvestmentInput,
): Promise<import("@/types").FinancialReportResponse> {
  return request("/accounting/setup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ═══════════════════════════════════════════════════════════
// Consultas Contables
// ═══════════════════════════════════════════════════════════

export async function getBCSS(): Promise<import("@/types").BCSSResponse> {
  return request("/accounting/bcss");
}

export async function getIncomeStatement(): Promise<import("@/types").IncomeStatementResponse> {
  return request("/accounting/pyg");
}

export async function getBalanceSheet(): Promise<import("@/types").BalanceSheetResponse> {
  return request("/accounting/balance");
}

export async function getRatios(): Promise<import("@/types").RatioItem[]> {
  return request("/accounting/ratios");
}

// ═══════════════════════════════════════════════════════════
// Kárdex
// ═══════════════════════════════════════════════════════════

export async function getKardexInventory(): Promise<import("@/types").KardexProduct[]> {
  return request("/accounting/kardex/inventory/summary");
}

export async function getKardex(
  productCode: string,
): Promise<import("@/types").KardexRecord[]> {
  return request(`/accounting/kardex/${encodeURIComponent(productCode)}`);
}

export async function registerKardexEntry(data: {
  product_code: string;
  quantity: number;
  unit_cost: number;
  concept: string;
  date: string;
  reference_type?: string;
}): Promise<import("@/types").KardexRecord> {
  return request("/accounting/kardex/entry", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function registerKardexExit(data: {
  product_code: string;
  quantity: number;
  concept: string;
  date: string;
  reference_type?: string;
}): Promise<import("@/types").KardexRecord> {
  return request("/accounting/kardex/exit", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function registerProduct(data: {
  code: string;
  name: string;
  unit?: string;
  initial_stock?: number;
  initial_cost?: number;
}): Promise<import("@/types").KardexProduct> {
  return request("/accounting/kardex/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function warehouseClose(
  accountingBalance: number,
): Promise<import("@/types").WarehouseCloseResponse> {
  return request(
    `/accounting/kardex/warehouse-close?accounting_balance=${accountingBalance}`,
    { method: "POST" },
  );
}

// ═══════════════════════════════════════════════════════════
// Configuración / Branding
// ═══════════════════════════════════════════════════════════

export async function getSettings(): Promise<import("@/types").CompanySettings> {
  return request("/settings");
}

export async function updateSettings(
  data: Partial<import("@/types").CompanySettings>,
): Promise<import("@/types").CompanySettings> {
  return request("/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getPalette(): Promise<import("@/types").ColorPalette> {
  return request("/settings/palette");
}

export async function updatePalette(
  palette: import("@/types").ColorPalette,
): Promise<import("@/types").ColorPalette> {
  return request("/settings/palette", {
    method: "PATCH",
    body: JSON.stringify(palette),
  });
}
