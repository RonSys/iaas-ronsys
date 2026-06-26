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
import type {
  HealthResponse,
  BCSSResponse,
  IncomeStatementResponse,
  BalanceSheetResponse,
  RatioItem,
  KardexProduct,
  KardexRecord,
  WarehouseCloseResponse,
  CompanySettings,
  ColorPalette,
  InvestmentInput,
  FinancialReportResponse,
  CompanySettingsResponse,
  CashflowQueryParams,
  CashflowResponse,
  PosSession,
  PosSessionOpenRequest,
  PosSessionCloseResponse,
  PosSessionCloseRequest,
  Sale,
  SaleDetail,
  SaleCreateRequest,
  SaleListResponse,
  SaleFilters,
  TicketResponse,
  VoidSaleRequest,
  PaymentMethodsResponse,
  Scenario,
  ScenarioCreateRequest,
  ScenarioUpdateRequest,
} from "@/types";

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

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };

  if (!shouldSkipAuth(path)) {
    const token = authStore.getAccessToken();
    const tenantId = authStore.getTenantId();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (tenantId) headers["X-Tenant-ID"] = String(tenantId);
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401 && !shouldSkipRetry(path)) {
    const newToken = await getRefreshPromise();

    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      const tenantId = authStore.getTenantId();
      if (tenantId) headers["X-Tenant-ID"] = String(tenantId);
      res = await fetch(url, { ...options, headers });
    } else {
      authStore.triggerLogout();
      throw new Error("Sesión expirada");
    }
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const detail = errorData?.detail;

    if (res.status === 401 || res.status === 423 || res.status === 429) {
      throw new Error(`${res.status} ${detail ?? res.statusText}`);
    }

    if (detail) {
      throw new Error(detail);
    }

    const errorText = await res.text().catch(() => res.statusText);
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }

  return res.json() as Promise<T>;
}

// ═══════════════════════════════════════════════════════════
// Health
// ═══════════════════════════════════════════════════════════

export async function getHealth(): Promise<HealthResponse> {
  return request("/health");
}

// ═══════════════════════════════════════════════════════════
// Setup
// ═══════════════════════════════════════════════════════════

export async function setupAccounting(
  data: InvestmentInput,
): Promise<FinancialReportResponse> {
  return request("/accounting/setup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ═══════════════════════════════════════════════════════════
// Consultas Contables
// ═══════════════════════════════════════════════════════════

export async function getBCSS(): Promise<BCSSResponse> {
  return request("/accounting/bcss");
}

export async function getIncomeStatement(): Promise<IncomeStatementResponse> {
  return request("/accounting/pyg");
}

export async function getBalanceSheet(): Promise<BalanceSheetResponse> {
  return request("/accounting/balance");
}

export async function getRatios(): Promise<RatioItem[]> {
  return request("/accounting/ratios");
}

// ═══════════════════════════════════════════════════════════
// Kárdex
// ═══════════════════════════════════════════════════════════

export async function getKardexInventory(): Promise<KardexProduct[]> {
  return request("/accounting/kardex/inventory/summary");
}

export async function getKardex(
  productCode: string,
): Promise<KardexRecord[]> {
  return request(`/accounting/kardex/${encodeURIComponent(productCode)}`);
}

export async function registerKardexEntry(data: {
  product_code: string;
  quantity: number;
  unit_cost: number;
  concept: string;
  date: string;
  reference_type?: string;
}): Promise<KardexRecord> {
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
}): Promise<KardexRecord> {
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
}): Promise<KardexProduct> {
  return request("/accounting/kardex/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function warehouseClose(
  accountingBalance: number,
): Promise<WarehouseCloseResponse> {
  return request(
    `/accounting/kardex/warehouse-close?accounting_balance=${accountingBalance}`,
    { method: "POST" },
  );
}

// ═══════════════════════════════════════════════════════════
// Configuración / Branding
// ═══════════════════════════════════════════════════════════

export async function getSettings(): Promise<CompanySettings> {
  return request("/settings");
}

export async function updateSettings(
  data: Partial<CompanySettings>,
): Promise<CompanySettings> {
  return request("/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getPalette(): Promise<ColorPalette> {
  return request("/settings/palette");
}

export async function updatePalette(
  palette: ColorPalette,
): Promise<ColorPalette> {
  return request("/settings/palette", {
    method: "PATCH",
    body: JSON.stringify(palette),
  });
}

// ═══════════════════════════════════════════════════════════
// Company Settings (feature flags + tax config)
// ═══════════════════════════════════════════════════════════

export async function getCompanySettings(): Promise<CompanySettingsResponse> {
  return request("/admin/company/settings");
}

export async function updateCompanySettings(
  data: Partial<Pick<CompanySettingsResponse, "features" | "tax_config">>,
): Promise<CompanySettingsResponse> {
  return request("/admin/company/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ═══════════════════════════════════════════════════════════
// Cashflow
// ═══════════════════════════════════════════════════════════

export async function getCashflow(
  params: CashflowQueryParams,
): Promise<CashflowResponse> {
  const searchParams = new URLSearchParams();
  if (params.view) searchParams.set("view", params.view);
  if (params.from) searchParams.set("from", params.from);
  if (params.to) searchParams.set("to", params.to);
  if (params.year) searchParams.set("year", String(params.year));
  const qs = searchParams.toString();
  return request(`/accounting/cashflow${qs ? `?${qs}` : ""}`);
}

// ═══════════════════════════════════════════════════════════
// POS Sessions
// ═══════════════════════════════════════════════════════════

export async function openPosSession(
  data: PosSessionOpenRequest,
): Promise<PosSession> {
  return request("/sales/sessions/open", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCurrentPosSession(): Promise<PosSession> {
  return request("/sales/sessions/current");
}

export async function closePosSession(
  sessionId: number,
  data: PosSessionCloseRequest,
): Promise<PosSessionCloseResponse> {
  return request(`/sales/sessions/${sessionId}/close`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ═══════════════════════════════════════════════════════════
// Sales
// ═══════════════════════════════════════════════════════════

export async function createSale(
  data: SaleCreateRequest,
): Promise<SaleDetail> {
  return request("/sales/sale", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getSales(
  filters: SaleFilters = {},
): Promise<SaleListResponse> {
  const sp = new URLSearchParams();
  if (filters.from) sp.set("from", filters.from);
  if (filters.to) sp.set("to", filters.to);
  if (filters.business_type) sp.set("business_type", filters.business_type);
  if (filters.session_id) sp.set("session_id", String(filters.session_id));
  if (filters.is_voided !== undefined) sp.set("is_voided", String(filters.is_voided));
  if (filters.payment_method) sp.set("payment_method", filters.payment_method);
  if (filters.page) sp.set("page", String(filters.page));
  if (filters.limit) sp.set("limit", String(filters.limit));
  const qs = sp.toString();
  const raw: any = await request(`/sales/sales${qs ? `?${qs}` : ""}`);
  // Backend devuelve "items" pero frontend espera "sales" — normalizar
  return {
    sales: raw.items ?? raw.sales ?? [],
    total: raw.total ?? 0,
    page: raw.page ?? 1,
    limit: raw.limit ?? 20,
  };
}

export async function getSaleDetail(saleId: number): Promise<SaleDetail> {
  return request(`/sales/sale/${saleId}`);
}

export async function getSaleTicket(
  saleId: number,
  format: "json" | "text" = "text",
): Promise<TicketResponse> {
  return request(`/sales/sale/${saleId}/ticket?format=${format}`);
}

export async function voidSale(
  saleId: number,
  data: VoidSaleRequest,
): Promise<Sale> {
  return request(`/sales/sale/${saleId}/void`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getPaymentMethods(): Promise<PaymentMethodsResponse> {
  return request("/sales/payment-methods");
}

// ═══════════════════════════════════════════════════════════
// Kárdex Products (for product search in POS)
// ═══════════════════════════════════════════════════════════

export async function searchKardexProducts(
  query: string,
): Promise<KardexProduct[]> {
  return request(
    `/accounting/kardex/products?search=${encodeURIComponent(query)}`,
  );
}

// ═══════════════════════════════════════════════════════════
// Simulator Scenarios (HU-SIM-002)
// ═══════════════════════════════════════════════════════════

export async function getScenarios(): Promise<Scenario[]> {
  const data = await request<{ scenarios: Scenario[]; total: number; max_allowed: number }>("/simulator/scenarios");
  return data.scenarios;
}

export async function createScenario(
  data: ScenarioCreateRequest,
): Promise<Scenario> {
  return request("/simulator/scenarios", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateScenario(
  id: number,
  data: ScenarioUpdateRequest,
): Promise<Scenario> {
  return request(`/simulator/scenarios/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteScenario(id: number): Promise<void> {
  return request(`/simulator/scenarios/${id}`, { method: "DELETE" });
}


// ═══════════════════════════════════════════════════════════
// Superadmin
// ═══════════════════════════════════════════════════════════

export async function getSuperadminDashboard(): Promise<any> {
  return request("/superadmin/dashboard");
}

export async function getSuperadminCompanies(): Promise<any> {
  return request("/superadmin/companies");
}

export async function createSuperadminCompany(data: {
  name: string;
  ruc: string;
  address?: string;
  economic_activity?: string;
  business_type: string;
}): Promise<any> {
  return request("/superadmin/companies", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteSuperadminCompany(id: number): Promise<void> {
  return request(`/superadmin/companies/${id}`, { method: "DELETE" });
}

export async function getSuperadminUsers(params?: {
  tenant_id?: number;
  role?: string;
}): Promise<any> {
  let path = "/superadmin/users";
  const qs = new URLSearchParams();
  if (params?.tenant_id) qs.set("tenant_id", String(params.tenant_id));
  if (params?.role) qs.set("role", params.role);
  const q = qs.toString();
  if (q) path += "?" + q;
  return request(path);
}

export async function createSuperadminUser(data: {
  email: string;
  full_name: string;
  password: string;
  role: string;
  tenant_id: number;
  is_verified?: boolean;
}): Promise<any> {
  return request("/superadmin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteSuperadminUser(id: number): Promise<any> {
  return request(`/superadmin/users/${id}`, { method: "DELETE" });
}

export async function activateSuperadminUser(id: number): Promise<any> {
  return request(`/superadmin/users/${id}/activate`, { method: "POST" });
}
