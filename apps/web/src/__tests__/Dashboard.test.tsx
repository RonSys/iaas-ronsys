import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Dashboard } from "@/pages/Dashboard";

// Mock the full api module so all hooks return empty state
jest.mock("@/services", () => {
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
    getPalette: jest.fn().mockResolvedValue({
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
    updatePalette: mockFn,
  };
});

describe("Dashboard", () => {
  it("renders the dashboard header", () => {
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>,
    );
    expect(screen.getByText("Panel de Control")).toBeInTheDocument();
  });

  it("shows empty state message when no PYG data", async () => {
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>,
    );
    expect(
      await screen.findByText(/Ejecutá una simulación en/),
    ).toBeInTheDocument();
  });

  it("renders section headers", () => {
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>,
    );
    expect(screen.getByText("🚦 Ratios Financieros")).toBeInTheDocument();
    expect(
      screen.getByText("🧾 Balance de Comprobación (BCSS)"),
    ).toBeInTheDocument();
  });
});
