import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Dashboard } from "@/pages/Dashboard";

// Mock the full api module so all hooks return empty state
jest.mock("@/services", () => {
  const mockFn = jest.fn().mockResolvedValue(null);
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  return {
    getHealth: mockFn, setupAccounting: mockFn,
    getBCSS: jest.fn().mockResolvedValue({ lines: [], total_debits: 0, total_credits: 0, is_balanced: true }),
    getIncomeStatement: jest.fn().mockResolvedValue(null),
    getBalanceSheet: jest.fn().mockResolvedValue(null),
    getRatios: jest.fn().mockResolvedValue([]),
    getKardexInventory: jest.fn().mockResolvedValue([]),
    getKardex: jest.fn().mockResolvedValue([]),
    registerKardexEntry: mockFn, registerKardexExit: mockFn,
    registerProduct: mockFn, warehouseClose: mockFn,
    getSettings: mockFn, updateSettings: mockFn,
    getPalette: jest.fn().mockResolvedValue(palette), updatePalette: mockFn,
    getCompanySettings: jest.fn().mockResolvedValue({
      company_id: 1, business_type: "retail", business_name: "Test",
      features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false, multi_warehouse: false },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
      branding: { logo_url: null, favicon_url: null, primary_color: "#1a365d", secondary_color: "#2b6cb0", business_name: "Test" },
      palette, logo_url: null, favicon_url: null,
      date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
    }),
    updateCompanySettings: mockFn,
    getCashflow: mockFn,
    openPosSession: mockFn, getCurrentPosSession: mockFn, closePosSession: mockFn,
    createSale: mockFn, getSales: mockFn, getSaleDetail: mockFn,
    getSaleTicket: mockFn, voidSale: mockFn, getPaymentMethods: mockFn,
    searchKardexProducts: mockFn,
    getScenarios: mockFn, createScenario: mockFn, updateScenario: mockFn, deleteScenario: mockFn,
    __esModule: true,
  };
});

describe("Dashboard", () => {
  it("renders the dashboard header", async () => {
    render(<BrowserRouter><Dashboard /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Panel de Control")).toBeInTheDocument();
    });
  });

  it("shows empty state message when no PYG data", async () => {
    render(<BrowserRouter><Dashboard /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Ejecutá una simulación en/)).toBeInTheDocument();
    });
  });

  it("renders section headers", async () => {
    render(<BrowserRouter><Dashboard /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🚦 Ratios Financieros")).toBeInTheDocument();
      expect(screen.getByText("🧾 Balance de Comprobación (BCSS)")).toBeInTheDocument();
    });
  });
});
