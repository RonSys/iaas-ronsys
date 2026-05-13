/**
 * Tests for CashflowPage — Flujo de Caja con selectores.
 *
 * HU-F1-007: UI de Flujo de Caja con selector de período/vista
 */
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { CashflowPage } from "@/pages/Cashflow";

// ── Mock completo de @/services ──
jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  const fn = jest.fn().mockResolvedValue(null);

  return {
    getHealth: fn, setupAccounting: fn,
    getBCSS: jest.fn().mockResolvedValue({ lines: [], total_debits: 0, total_credits: 0, is_balanced: true }),
    getIncomeStatement: jest.fn().mockResolvedValue(null),
    getBalanceSheet: jest.fn().mockResolvedValue(null),
    getRatios: jest.fn().mockResolvedValue([]),
    getKardexInventory: jest.fn().mockResolvedValue([]),
    getKardex: jest.fn().mockResolvedValue([]),
    registerKardexEntry: fn, registerKardexExit: fn,
    registerProduct: fn, warehouseClose: fn,
    getSettings: fn, updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette),
    updatePalette: fn,
    getCompanySettings: fn,
    updateCompanySettings: fn,
    getCashflow: jest.fn().mockResolvedValue({
      company_id: 1, from_date: "2026-01", to_date: "2026-06",
      view: "projected",
      lines: [
        { month: 1, year: 2026, concept: "Ventas", category: "income", projected: 5000, actual: 0, difference: 0 },
        { month: 1, year: 2026, concept: "Costo", category: "expense", projected: 2000, actual: 0, difference: 0 },
        { month: 2, year: 2026, concept: "Ventas", category: "income", projected: 5200, actual: 0, difference: 0 },
        { month: 2, year: 2026, concept: "Costo", category: "expense", projected: 2100, actual: 0, difference: 0 },
      ],
      opening_balance: 1000, net_cashflow: 3100, closing_balance: 4100, alerts: [],
    }),
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn, getSales: fn, getSaleDetail: fn,
    getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: fn,
    __esModule: true,
  };
});

describe("CashflowPage", () => {
  it("renders the page title", async () => {
    render(<BrowserRouter><CashflowPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("💰 Flujo de Caja")).toBeInTheDocument();
    });
  });

  it("shows view selector with default 'Proyectado'", async () => {
    render(<BrowserRouter><CashflowPage /></BrowserRouter>);
    await waitFor(() => {
      const select = document.getElementById("cf-view") as HTMLSelectElement;
      expect(select).not.toBeNull();
      expect(select.value).toBe("projected");
    });
  });

  it("renders label 'Desde' and 'Hasta' period selectors", async () => {
    render(<BrowserRouter><CashflowPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Desde")).toBeInTheDocument();
      expect(screen.getByText("Hasta")).toBeInTheDocument();
    });
  });

  it("renders summary KPIs when data is loaded", async () => {
    render(<BrowserRouter><CashflowPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Saldo Inicial")).toBeInTheDocument();
      expect(screen.getByText("Flujo Neto")).toBeInTheDocument();
      expect(screen.getByText("Saldo Final")).toBeInTheDocument();
    });
  });
});
