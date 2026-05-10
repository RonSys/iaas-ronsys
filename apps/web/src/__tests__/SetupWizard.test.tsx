import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { SetupWizard } from "@/pages/SetupWizard";

jest.mock("@/services", () => {
  const mockFn = jest.fn().mockResolvedValue(null);
  return {
    getHealth: mockFn,
    setupAccounting: mockFn,
    getBCSS: mockFn,
    getIncomeStatement: mockFn,
    getBalanceSheet: mockFn,
    getRatios: mockFn,
    getKardexInventory: mockFn,
    getKardex: mockFn,
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

describe("SetupWizard", () => {
  it("renders the title", () => {
    render(
      <BrowserRouter>
        <SetupWizard />
      </BrowserRouter>,
    );
    expect(screen.getByText("🏗️ Configuración Inicial")).toBeInTheDocument();
  });

  it("renders all form sections", () => {
    render(
      <BrowserRouter>
        <SetupWizard />
      </BrowserRouter>,
    );
    expect(screen.getByText("📌 Inversión Inicial")).toBeInTheDocument();
    expect(screen.getByText("🏪 Gastos de Instalación")).toBeInTheDocument();
    expect(screen.getByText("💳 Gastos Fijos Mensuales")).toBeInTheDocument();
    expect(screen.getByText("💵 Proyección de Ventas")).toBeInTheDocument();
    expect(screen.getByText("⏳ Vida Útil de Activos (años)")).toBeInTheDocument();
  });

  it("renders the SIMULAR button", () => {
    render(
      <BrowserRouter>
        <SetupWizard />
      </BrowserRouter>,
    );
    expect(screen.getByText("📊 SIMULAR")).toBeInTheDocument();
  });

  it("has investment form fields with default values", () => {
    render(
      <BrowserRouter>
        <SetupWizard />
      </BrowserRouter>,
    );
    // Check for capital field (50,000 default)
    const capitalInput = screen.getByDisplayValue("50000");
    expect(capitalInput).toBeInTheDocument();
  });
});
