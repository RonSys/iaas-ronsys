/**
 * Tests for CashflowChart component and CashflowPage.
 *
 * HU-F1-007: UI de Flujo de Caja con selector de período/vista
 */
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { CashflowPage } from "@/pages/finanzas/CashflowPage";

// Mock full api module
jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };

  const mockCashflow = {
    company_id: 1,
    from_date: "2026-01",
    to_date: "2026-06",
    view: "projected",
    lines: [
      { month: 1, year: 2026, concept: "Ventas", category: "income", projected: 5000, actual: 0, difference: 0 },
      { month: 1, year: 2026, concept: "Costo Ventas", category: "expense", projected: 2000, actual: 0, difference: 0 },
      { month: 2, year: 2026, concept: "Ventas", category: "income", projected: 5200, actual: 0, difference: 0 },
      { month: 2, year: 2026, concept: "Costo Ventas", category: "expense", projected: 2100, actual: 0, difference: 0 },
    ],
    opening_balance: 1000,
    net_cashflow: 3100,
    closing_balance: 4100,
    alerts: [],
  };

  const mockFn = jest.fn().mockResolvedValue(null);

  return {
    getHealth: mockFn,
    setupAccounting: mockFn,
    getBCSS: jest.fn().mockResolvedValue({ lines: [], total_debits: 0, total_credits: 0, is_balanced: true }),
    getIncomeStatement: jest.fn().mockResolvedValue(null),
    getBalanceSheet: jest.fn().mockResolvedValue(null),
    getRatios: jest.fn().mockResolvedValue([]),
    getKardexInventory: jest.fn().mockResolvedValue([]),
    getKardex: jest.fn().mockResolvedValue([]),
    registerKardexEntry: mockFn,
    registerKardexExit: mockFn,
    registerProduct: mockFn,
    warehouseClose: mockFn,
    getSettings: mockFn,
    updateSettings: mockFn,
    getPalette: jest.fn().mockResolvedValue(palette),
    updatePalette: mockFn,
    getCompanySettings: mockFn,
    updateCompanySettings: mockFn,
    getCashflow: jest.fn().mockResolvedValue(mockCashflow),
    openPosSession: mockFn,
    getCurrentPosSession: mockFn,
    closePosSession: mockFn,
    createSale: mockFn,
    getSales: mockFn,
    getSaleDetail: mockFn,
    getSaleTicket: mockFn,
    voidSale: mockFn,
    getPaymentMethods: mockFn,
    searchKardexProducts: mockFn,
    __esModule: true,
  };
});

describe("CashflowPage", () => {
  it("renders the page title", async () => {
    render(
      <BrowserRouter>
        <CashflowPage />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("💰 Flujo de Caja")).toBeInTheDocument();
    });
  });

  it("renders view selector with Proyectado, Real, Comparativa", async () => {
    render(
      <BrowserRouter>
        <CashflowPage />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Proyectado")).toBeInTheDocument();
    });
    // The select element should have Proyectado as default
    const viewSelect = screen.getByRole("combobox", { name: "Vista" }) as HTMLSelectElement;
    expect(viewSelect.value).toBe("projected");
  });

  it("renders period selectors (year and month)", async () => {
    render(
      <BrowserRouter>
        <CashflowPage />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Desde")).toBeInTheDocument();
      expect(screen.getByText("Hasta")).toBeInTheDocument();
    });
  });

  // Note: View change and period change tests interact with recharts
  // which renders SVG. Those are integration-level tests better
  // suited for Playwright/E2E. Limited testing here.
});
