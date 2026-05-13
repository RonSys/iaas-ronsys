// Manual mock for @/services — used by all page tests
const mockFn = jest.fn().mockResolvedValue(null);

const palette = {
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
};

const mockCompanySettings = {
  company_id: 1,
  business_type: "restaurant" as const,
  business_name: "Test Restaurant",
  features: {
    tables_enabled: true,
    tips_enabled: true,
    invoice_required: false,
    warranty_tracking: false,
    recipe_explosion: true,
    delivery_enabled: true,
    multi_waiter: false,
  },
  tax_config: {
    igv_included_in_price: true,
    igv_rate: 0.18,
    icb_perception_pct: 0,
  },
  palette,
  logo_url: null,
  favicon_url: null,
  date_format: "DD/MM/YYYY",
  currency: "PEN",
  timezone: "America/Lima",
};

const mockCashflow = {
  company_id: 1,
  from_date: "2026-01",
  to_date: "2026-06",
  view: "projected" as const,
  lines: [],
  opening_balance: 1000,
  net_cashflow: 500,
  closing_balance: 1500,
  alerts: [],
};

const mockPosSession = {
  id: 1,
  company_id: 1,
  user_id: 1,
  opened_at: "2026-01-15T08:00:00Z",
  closed_at: null,
  opening_cash: 500,
  closing_cash: null,
  expected_cash: null,
  difference: null,
  status: "open" as const,
  notes: null,
  total_sales: 1250.5,
  cash_sales: 800,
  card_sales: 450.5,
  yape_sales: 0,
  plin_sales: 0,
  transfer_sales: 0,
  sale_count: 5,
};

const mockPosCloseResult = {
  session: { ...mockPosSession, status: "closed" as const, closed_at: "2026-01-15T18:00:00Z" },
  total_sales: 1250.5,
  cash_expected: 1300,
  difference: -49.5,
};

const mockSale = {
  id: 1,
  company_id: 1,
  session_id: 1,
  user_id: 1,
  sale_number: "VTA-001",
  sale_date: "2026-01-15",
  sale_time: "14:30:00",
  customer_name: null,
  customer_doc: null,
  subtotal: 100,
  discount_total: 0,
  tax_total: 18,
  tip_amount: 0,
  total: 118,
  business_type: "retail" as const,
  is_voided: false,
  void_reason: null,
  journal_entry_id: null,
  cashier_name: "Admin",
  payment_methods: ["cash"],
  items: [],
  payments: [],
  restaurant_data: null,
  hardware_data: null,
};

export const getHealth = mockFn;
export const setupAccounting = mockFn;
export const getBCSS = jest.fn().mockResolvedValue({
  lines: [],
  total_debits: 0,
  total_credits: 0,
  is_balanced: true,
});
export const getIncomeStatement = jest.fn().mockResolvedValue(null);
export const getBalanceSheet = jest.fn().mockResolvedValue(null);
export const getRatios = jest.fn().mockResolvedValue([]);
export const getKardexInventory = jest.fn().mockResolvedValue([]);
export const getKardex = jest.fn().mockResolvedValue([]);
export const registerKardexEntry = mockFn;
export const registerKardexExit = mockFn;
export const registerProduct = mockFn;
export const warehouseClose = mockFn;
export const getSettings = jest.fn().mockResolvedValue({
  palette,
  logo_url: null,
  favicon_url: null,
  date_format: "DD/MM/YYYY",
  currency: "PEN",
  timezone: "America/Lima",
});
export const updateSettings = mockFn;
export const getPalette = jest.fn().mockResolvedValue(palette);
export const updatePalette = mockFn;

// ─── Nuevas funciones Fase 1 + 2 ───
export const getCompanySettings = jest.fn().mockResolvedValue(mockCompanySettings);
export const updateCompanySettings = mockFn;
export const getCashflow = jest.fn().mockResolvedValue(mockCashflow);
export const openPosSession = jest.fn().mockResolvedValue(mockPosSession);
export const getCurrentPosSession = jest.fn().mockResolvedValue(mockPosSession);
export const closePosSession = jest.fn().mockResolvedValue(mockPosCloseResult);
export const createSale = jest.fn().mockResolvedValue(mockSale);
export const getSales = jest.fn().mockResolvedValue({
  sales: [mockSale],
  total: 1,
  page: 1,
  limit: 20,
});
export const getSaleDetail = jest.fn().mockResolvedValue(mockSale);
export const getSaleTicket = jest.fn().mockResolvedValue({
  sale: mockSale,
  ticket_text: "=== TICKET ===\nVTA-001\nTotal: S/ 118",
  format: "text",
});
export const voidSale = jest.fn().mockResolvedValue({ ...mockSale, is_voided: true, void_reason: "Error" });
export const getPaymentMethods = jest.fn().mockResolvedValue({
  methods: ["cash", "card", "yape", "plin", "transfer"],
});
export const searchKardexProducts = jest.fn().mockResolvedValue([]);

// ─── Scenario CRUD (HU-SIM-002) ───
export const getScenarios = jest.fn().mockResolvedValue([]);
export const createScenario = jest.fn().mockResolvedValue({
  id: 1, company_id: 1, name: "Test",
  input_data: { price: 28, platesPerDay: 40, costPct: 40, rent: 2500, salaries: 5000 },
  created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:00:00Z",
});
export const updateScenario = jest.fn();
export const deleteScenario = jest.fn().mockResolvedValue(undefined);
