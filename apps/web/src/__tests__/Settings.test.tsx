import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Settings } from "@/pages/Settings";

jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  const fn = jest.fn().mockResolvedValue(null);
  return {
    getHealth: fn, setupAccounting: fn,
    getBCSS: fn, getIncomeStatement: fn, getBalanceSheet: fn, getRatios: fn,
    getKardexInventory: fn, getKardex: fn,
    registerKardexEntry: fn, registerKardexExit: fn, registerProduct: fn, warehouseClose: fn,
    getSettings: jest.fn().mockResolvedValue({ palette, logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima" }),
    updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette), updatePalette: jest.fn().mockResolvedValue(palette),
    getCompanySettings: jest.fn().mockResolvedValue({
      company_id: 1, business_type: "retail", business_name: "Test",
      features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0 },
      branding: { logo_url: null, favicon_url: null, primary_color: "#1a365d", secondary_color: "#2b6cb0", business_name: "Test" },
      palette, logo_url: null, favicon_url: null,
      date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
    }),
    updateCompanySettings: fn, getCashflow: fn,
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn, getSales: fn, getSaleDetail: fn, getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: fn,
    getScenarios: fn, createScenario: fn, updateScenario: fn, deleteScenario: fn,
    __esModule: true,
  };
});

describe("Settings", () => {
  it("renders the title", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("⚙️ Configuración")).toBeInTheDocument();
    });
  });

  it("renders palette section", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🎨 Paleta de Colores")).toBeInTheDocument();
    });
  });

  it("renders predefined palette presets", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Azul Marino")).toBeInTheDocument();
      expect(screen.getByText("Verde Bosque")).toBeInTheDocument();
      expect(screen.getByText("Rojizo Cálido")).toBeInTheDocument();
      expect(screen.getByText("Púrpura")).toBeInTheDocument();
    });
  });

  it("renders color pickers for all 10 palette keys", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Azul Marino")).toBeInTheDocument();
    });
    const colorInputs = document.querySelectorAll('input[type="color"]');
    expect(colorInputs.length).toBeGreaterThanOrEqual(10);
  });

  it("renders preview section", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("👁️ Vista Previa")).toBeInTheDocument();
    });
  });

  it("renders company info section", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🏢 Información de la Empresa")).toBeInTheDocument();
      expect(screen.getByText("PEN")).toBeInTheDocument();
      expect(screen.getByText("America/Lima")).toBeInTheDocument();
    });
  });
});
