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
