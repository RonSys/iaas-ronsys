/**
 * Mock API responses for E2E tests.
 *
 * Todos los tests usan page.route() para interceptar llamadas al backend
 * y devolver datos mock. Así los tests son autónomos (no necesitan backend real).
 *
 * @module e2e/fixtures/mocks
 */

import type { Page } from "@playwright/test";

// ─── Auth ──────────────────────────────────────────────────

export const ADMIN_USER = {
  id: 1,
  email: "admin@elsegoviano.pe",
  full_name: "Admin Segoviano",
  role: "admin",
  company_id: 1,
};

export const FAKE_ACCESS_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOjEsImVtYWlsIjoiYWRtaW5AZWxzZWdvdmlhbm8ucGUiLCJuYW1lIjoiQWRtaW4iLCJyb2xlIjoiYWRtaW4iLCJjb21wYW55X2lkIjoxLCJleHAiOjk5OTk5OTk5OTl9.fake";

export const FAKE_REFRESH_TOKEN = "ref-abc123-def456";

/** Intercepta POST /api/auth/login y devuelve sesión mock */
export function mockLogin(page: Page, status = 200) {
  return page.route("**/api/auth/login", (route) => {
    if (status === 200) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: FAKE_ACCESS_TOKEN,
          refresh_token: FAKE_REFRESH_TOKEN,
          token_type: "bearer",
          user: ADMIN_USER,
        }),
      });
    } else if (status === 401) {
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Email o contraseña inválidos" }),
      });
    } else if (status === 429) {
      route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Demasiados intentos. Espere 30 segundos." }),
        headers: { "Retry-After": "30" },
      });
    } else if (status === 423) {
      route.fulfill({
        status: 423,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Cuenta bloqueada temporalmente." }),
      });
    }
  });
}

export function mockRefresh(page: Page, status = 200) {
  return page.route("**/api/auth/refresh", (route) => {
    if (status === 200) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: FAKE_ACCESS_TOKEN,
          refresh_token: "ref-rotated-xyz789",
        }),
      });
    } else {
      route.fulfill({ status: 401 });
    }
  });
}

export function mockLogout(page: Page) {
  return page.route("**/api/auth/logout", (route) => {
    route.fulfill({ status: 200, body: "{}" });
  });
}

// ─── Contabilidad ──────────────────────────────────────────

export function mockSetup(page: Page) {
  return page.route("**/api/accounting/setup", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        period_start: "2026-01-01",
        period_end: "2026-01-31",
        total_entries: 25,
        bcss: {
          lines: [
            { account_code: "10", account_name: "Efectivo", total_debit: 50000, total_credit: 0, balance: 50000, balance_nature: "D" },
            { account_code: "33", account_name: "Equipamiento", total_debit: 15000, total_credit: 0, balance: 15000, balance_nature: "D" },
            { account_code: "50", account_name: "Capital", total_debit: 0, total_credit: 50000, balance: 50000, balance_nature: "A" },
            { account_code: "45", account_name: "Préstamo", total_debit: 0, total_credit: 30000, balance: 30000, balance_nature: "A" },
          ],
          total_debits: 95000,
          total_credits: 95000,
          is_balanced: true,
        },
        income_statement: {
          period: "2026-01",
          revenue: 29120,
          cost_of_sales: 11648,
          gross_profit: 17472,
          gross_margin_pct: 0.60,
          operating_expenses: { rent: 2500, salaries: 5000, utilities: 800, marketing: 500 },
          depreciation: 300,
          financial_expenses: 312,
          ebitda: 8760,
          ebit: 8460,
          operating_margin_pct: 0.29,
          income_before_tax: 8148,
          income_tax: 2404,
          net_income: 5744,
          net_margin_pct: 0.197,
        },
        balance_sheet: {
          as_of: "2026-01-31",
          current_assets: { cash: 55744, inventory: 5000 },
          non_current_assets: { equipment: 15000, furniture: 5000, computers: 3000, software: 1000 },
          accumulated_depreciation: 300,
          total_assets: 84444,
          current_liabilities: { loan_current: 7500 },
          non_current_liabilities: { loan_long_term: 22500 },
          total_liabilities: 30000,
          capital: 50000,
          retained_earnings: 0,
          current_income: 4444,
          total_equity: 54444,
          total_liabilities_and_equity: 84444,
          is_balanced: true,
        },
        ratios: [
          { name: "Liquidez Corriente", value: 8.1, target: "> 1.5", traffic_light: "green", formula: "AC/PC" },
          { name: "Margen Bruto", value: 0.60, target: "> 50%", traffic_light: "green", formula: "UB/V" },
          { name: "Margen Neto", value: 0.197, target: "> 10%", traffic_light: "green", formula: "UN/V" },
          { name: "ROE", value: 0.105, target: "> 15%", traffic_light: "yellow", formula: "UN/Pat" },
          { name: "Endeudamiento", value: 0.55, target: "< 1.0", traffic_light: "green", formula: "P/Pat" },
          { name: "Payback", value: 18, target: "< 24 meses", traffic_light: "yellow", formula: "Inv/FC" },
          { name: "VAN", value: 45230, target: "> 0", traffic_light: "green", formula: "ΣFC/(1+i)^t" },
          { name: "TIR", value: 0.28, target: "> 15%", traffic_light: "green", formula: "VAN=0" },
        ],
        validations: { bcss_balanced: true, balance_balanced: true },
      }),
    });
  });
}

export function mockBCSS(page: Page) {
  return page.route("**/api/accounting/bcss", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        lines: [
          { account_code: "10", account_name: "Efectivo", total_debit: 50000, total_credit: 0, balance: 50000, balance_nature: "D" },
          { account_code: "50", account_name: "Capital", total_debit: 0, total_credit: 50000, balance: 50000, balance_nature: "A" },
        ],
        total_debits: 50000,
        total_credits: 50000,
        is_balanced: true,
      }),
    });
  });
}

export function mockPYG(page: Page) {
  return page.route("**/api/accounting/pyg", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        period: "2026-01",
        revenue: 29120,
        cost_of_sales: 11648,
        gross_profit: 17472,
        gross_margin_pct: 0.60,
        operating_expenses: { rent: 2500, salaries: 5000, utilities: 800, marketing: 500 },
        depreciation: 300,
        financial_expenses: 312,
        ebitda: 8760,
        ebit: 8460,
        operating_margin_pct: 0.29,
        income_before_tax: 8148,
        income_tax: 2404,
        net_income: 5744,
        net_margin_pct: 0.197,
      }),
    });
  });
}

export function mockBalance(page: Page) {
  return page.route("**/api/accounting/balance", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        as_of: "2026-01-31",
        current_assets: { cash: 55744 },
        non_current_assets: { equipment: 24000 },
        accumulated_depreciation: 300,
        total_assets: 79444,
        current_liabilities: {},
        non_current_liabilities: { loan: 30000 },
        total_liabilities: 30000,
        capital: 50000,
        retained_earnings: 0,
        current_income: -556,
        total_equity: 49444,
        total_liabilities_and_equity: 79444,
        is_balanced: true,
      }),
    });
  });
}

export function mockRatios(page: Page) {
  return page.route("**/api/accounting/ratios", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { name: "Liquidez Corriente", value: 8.1, target: "> 1.5", traffic_light: "green", formula: "AC/PC" },
        { name: "Margen Bruto", value: 0.60, target: "> 50%", traffic_light: "green", formula: "UB/V" },
        { name: "ROE", value: 0.105, target: "> 15%", traffic_light: "yellow", formula: "UN/Pat" },
      ]),
    });
  });
}

// ─── Kárdex ────────────────────────────────────────────────

export function mockKardexInventory(page: Page) {
  return page.route("**/api/accounting/kardex/inventory/summary", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { code: "INS-001", name: "Arroz", unit: "kg", current_stock: 50, average_cost: 4.5, total_value: 225 },
        { code: "INS-002", name: "Pollo", unit: "kg", current_stock: 30, average_cost: 12, total_value: 360 },
      ]),
    });
  });
}

export function mockKardexDetail(page: Page) {
  return page.route("**/api/accounting/kardex/*", (route) => {
    const url = route.request().url();
    // Solo mockear GET (movimientos), no POST (entrada/salida)
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { product_code: "INS-001", movement_type: "entrada", concept: "Compra inicial", quantity: 100, unit_cost: 4, total: 400, balance_quantity: 100, balance_avg_cost: 4, balance_total: 400, date: "2026-01-05" },
          { product_code: "INS-001", movement_type: "salida", concept: "Consumo semanal", quantity: 50, unit_cost: 4, total: 200, balance_quantity: 50, balance_avg_cost: 4, balance_total: 200, date: "2026-01-12" },
        ]),
      });
    } else if (route.request().method() === "POST" && url.includes("/entry")) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ product_code: "INS-001", movement_type: "entrada", concept: "Compra", quantity: 10, unit_cost: 5, total: 50, balance_quantity: 60, balance_avg_cost: 4.17, balance_total: 250, date: "2026-01-20" }),
      });
    } else if (route.request().method() === "POST" && url.includes("/exit")) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ product_code: "INS-001", movement_type: "salida", concept: "Venta", quantity: 5, unit_cost: 4.17, total: 20.85, balance_quantity: 55, balance_avg_cost: 4.17, balance_total: 229.15, date: "2026-01-21" }),
      });
    } else if (route.request().method() === "POST" && url.includes("/products")) {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ code: "INS-003", name: "Cebolla", unit: "kg", current_stock: 0, average_cost: 0, total_value: 0 }),
      });
    }
  });
}

// ─── Settings / Palette ────────────────────────────────────

export function mockPalette(page: Page) {
  return page.route("**/api/settings/palette", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        primary: "#1a365d",
        secondary: "#2b6cb0",
        accent: "#e53e3e",
        background: "#f7fafc",
        surface: "#ffffff",
        text_primary: "#1a202c",
        text_secondary: "#718096",
        success: "#38a169",
        warning: "#d69e2e",
        error: "#e53e3e",
      }),
    });
  });
}

export function mockSettings(page: Page) {
  return page.route("**/api/settings", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        palette: {
          primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
          background: "#f7fafc", surface: "#ffffff",
          text_primary: "#1a202c", text_secondary: "#718096",
          success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
        },
        logo_url: null,
        favicon_url: null,
        date_format: "DD/MM/YYYY",
        currency: "PEN",
        timezone: "America/Lima",
      }),
    });
  });
}

export function mockHealth(page: Page) {
  return page.route("**/api/health", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", service: "iaas-ronsys", version: "0.1.0" }),
    });
  });
}

// ─── Setup all mocks ───────────────────────────────────────

/** Instala todos los mocks de API necesarios para las páginas protegidas */
export async function setupAllMocks(page: Page) {
  await mockLogin(page);
  await mockRefresh(page);
  await mockLogout(page);
  await mockSetup(page);
  await mockBCSS(page);
  await mockPYG(page);
  await mockBalance(page);
  await mockRatios(page);
  await mockKardexInventory(page);
  await mockKardexDetail(page);
  await mockPalette(page);
  await mockSettings(page);
  await mockHealth(page);
}

/** Mock de health solamente (para la pantalla de loading) */
export async function setupMinimalMocks(page: Page) {
  await mockPalette(page);
  await mockHealth(page);
}

/** Mock de auth + contables (para páginas protegidas) */
export async function setupAuthMocks(page: Page) {
  await mockLogin(page);
  await mockRefresh(page);
  await mockLogout(page);
  await mockPalette(page);
  await mockHealth(page);
}
