/**
 * Tests for Simulator with scenario persistence (HU-SIM-002).
 */
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { Simulator } from "@/pages/Simulator";

jest.mock("@/services", () => {
  const fn = jest.fn().mockResolvedValue(null);
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
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
    getCompanySettings: fn, updateCompanySettings: fn,
    getCashflow: fn,
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn, getSales: fn, getSaleDetail: fn,
    getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: fn,
    getScenarios: jest.fn().mockResolvedValue([
      {
        id: 1, company_id: 1, name: "Realista",
        input_data: { price: 28, platesPerDay: 40, costPct: 40, rent: 2500, salaries: 5000, revenue: 25000, grossProfit: 15000, netIncome: 5000, payback: 18, van: 45000, tir: 0.22 },
        created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:00:00Z",
      },
      {
        id: 2, company_id: 1, name: "Optimista",
        input_data: { price: 35, platesPerDay: 60, costPct: 35, rent: 2500, salaries: 6000, revenue: 54600, grossProfit: 35490, netIncome: 12000, payback: 10, van: 85000, tir: 0.35 },
        created_at: "2026-06-01T01:00:00Z", updated_at: "2026-06-01T01:00:00Z",
      },
    ]),
    createScenario: fn,
    updateScenario: fn,
    deleteScenario: jest.fn().mockResolvedValue(undefined),
    __esModule: true,
  };
});

describe("Simulator — scenarios persistence", () => {
  it("shows loaded scenarios in comparison table", async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <Simulator />
        </AuthProvider>
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("🔍 Comparativa de Escenarios")).toBeInTheDocument();
    });
    expect(screen.getByText("Realista")).toBeInTheDocument();
    expect(screen.getByText("Optimista")).toBeInTheDocument();
  });

  it("shows delete button on each scenario", async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <Simulator />
        </AuthProvider>
      </BrowserRouter>,
    );
    await waitFor(() => {
      const deleteBtns = screen.getAllByTitle("Eliminar");
      expect(deleteBtns.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows 'Limpiar todo' button", async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <Simulator />
        </AuthProvider>
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("🗑️ Limpiar todo")).toBeInTheDocument();
    });
  });

  it("loads 4 scenarios and shows all in comparison table", async () => {
    const { getScenarios } = require("@/services");
    getScenarios.mockResolvedValue([
      { id: 1, company_id: 1, name: "S1", input_data: {}, created_at: "", updated_at: "" },
      { id: 2, company_id: 1, name: "S2", input_data: {}, created_at: "", updated_at: "" },
      { id: 3, company_id: 1, name: "S3", input_data: {}, created_at: "", updated_at: "" },
      { id: 4, company_id: 1, name: "S4", input_data: {}, created_at: "", updated_at: "" },
    ]);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Simulator />
        </AuthProvider>
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("S1")).toBeInTheDocument();
      expect(screen.getByText("S4")).toBeInTheDocument();
    });
    expect(screen.getAllByTitle("Eliminar")).toHaveLength(4);
  });
});
