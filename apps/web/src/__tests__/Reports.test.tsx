import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Reports } from "@/pages/Reports";

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
    getKardexInventory: fn, getKardex: fn,
    registerKardexEntry: fn, registerKardexExit: fn, registerProduct: fn, warehouseClose: fn,
    getSettings: fn, updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette), updatePalette: fn,
    getCompanySettings: jest.fn().mockResolvedValue({
      company_id: 1, business_type: "retail", business_name: "Test",
      features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false, multi_warehouse: false },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
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

describe("Reports", () => {
  it("renders the title", async () => {
    render(<BrowserRouter><Reports /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("📋 Reportes Financieros")).toBeInTheDocument();
    });
  });

  it("renders all 4 tabs", async () => {
    render(<BrowserRouter><Reports /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("📄 PYG")).toBeInTheDocument();
    });
    expect(screen.getByText("⚖️ Balance")).toBeInTheDocument();
    expect(screen.getByText("🧾 BCSS")).toBeInTheDocument();
    expect(screen.getByText("🚦 Ratios")).toBeInTheDocument();
  });

  it("shows PYG tab by default with empty state", async () => {
    render(<BrowserRouter><Reports /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Ejecutá el Setup/)).toBeInTheDocument();
    });
  });

  it("switches to BCSS tab when clicked", async () => {
    render(<BrowserRouter><Reports /></BrowserRouter>);
    await waitFor(() => expect(screen.getByText("🧾 BCSS")).toBeInTheDocument());
    fireEvent.click(screen.getByText("🧾 BCSS"));
    await waitFor(() => {
      expect(screen.getByText(/Balance de Comprobaci/)).toBeInTheDocument();
      expect(screen.getByText("✅ Cuadrado")).toBeInTheDocument();
    });
  });

  it("switches to Ratios tab and shows empty state", async () => {
    render(<BrowserRouter><Reports /></BrowserRouter>);
    await waitFor(() => expect(screen.getByText("🚦 Ratios")).toBeInTheDocument());
    fireEvent.click(screen.getByText("🚦 Ratios"));
    await waitFor(() => {
      expect(screen.getByText("Sin ratios calculados.")).toBeInTheDocument();
    });
  });
});
