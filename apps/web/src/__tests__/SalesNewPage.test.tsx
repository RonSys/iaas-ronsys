/**
 * Tests for SalesNewPage — registro de venta con feature flags.
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-010: UI de venta especializada por tipo de negocio
 */
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { SalesNewPage } from "@/pages/ventas/SalesNewPage";

// Mock global.fetch for ProductSearch category fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve([]),
  } as Response),
) as jest.Mock;

jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  const fn = jest.fn().mockResolvedValue(null);

  const restaurantSettings = {
    company_id: 1,
    business_type: "restaurant" as const,
    business_name: "El Segoviano",
    features: {
      tables_enabled: true, tips_enabled: true,
      invoice_required: false, warranty_tracking: false,
      recipe_explosion: true, delivery_enabled: true, multi_waiter: true,
    },
    tax_config: { igv_included_in_price: true, igv_rate: 0.18, icb_perception_pct: 0 },
    palette, logo_url: null, favicon_url: null,
    date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
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
    getCompanySettings: jest.fn().mockResolvedValue(restaurantSettings),
    updateCompanySettings: fn,
    getCashflow: fn,
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn, getSales: fn, getSaleDetail: fn,
    getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: jest.fn().mockResolvedValue([]),
    __esModule: true,
  };
});

describe("SalesNewPage", () => {
  it("renders the page title 'Nueva Venta'", async () => {
    render(<BrowserRouter><SalesNewPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🛒 Nueva Venta")).toBeInTheDocument();
    });
  });

  it("shows business type from company settings (restaurant)", async () => {
    render(<BrowserRouter><SalesNewPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Restaurante")).toBeInTheDocument();
    });
  });

  it("renders ProductSearch placeholder", async () => {
    render(<BrowserRouter><SalesNewPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Escribí código o nombre...")).toBeInTheDocument();
    });
  });

  it("renders payment section", async () => {
    render(<BrowserRouter><SalesNewPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Método de Pago")).toBeInTheDocument();
    });
  });

  it("renders 'Cobrar' button", async () => {
    render(<BrowserRouter><SalesNewPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("💵 Cobrar")).toBeInTheDocument();
    });
  });
});
