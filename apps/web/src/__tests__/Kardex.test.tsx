import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { KardexPage } from "@/pages/Kardex";

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
    getKardexInventory: jest.fn().mockResolvedValue([]),
    getKardex: jest.fn().mockResolvedValue([]),
    registerKardexEntry: fn, registerKardexExit: fn, registerProduct: fn, warehouseClose: fn,
    getSettings: fn, updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette), updatePalette: fn,
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

describe("KardexPage", () => {
  it("renders the title", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("📦 Kárdex — Inventario")).toBeInTheDocument();
    });
  });

  it("renders action buttons", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("+ Producto")).toBeInTheDocument();
      expect(screen.getByText("+ Entrada")).toBeInTheDocument();
      expect(screen.getByText("- Salida")).toBeInTheDocument();
    });
  });

  it("shows empty inventory message when no products", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText(/No hay productos registrados/)).toBeInTheDocument();
    });
  });

  it("opens new product modal when button clicked", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => expect(screen.getByText("+ Producto")).toBeInTheDocument());
    fireEvent.click(screen.getByText("+ Producto"));
    await waitFor(() => {
      expect(screen.getByText("📦 Nuevo Producto")).toBeInTheDocument();
      expect(screen.getByText("Crear Producto")).toBeInTheDocument();
    });
  });

  it("closes new product modal on Cancelar", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => expect(screen.getByText("+ Producto")).toBeInTheDocument());
    fireEvent.click(screen.getByText("+ Producto"));
    await waitFor(() => expect(screen.getByText("📦 Nuevo Producto")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Cancelar"));
    await waitFor(() => {
      expect(screen.queryByText("📦 Nuevo Producto")).not.toBeInTheDocument();
    });
  });

  it("entry and exit buttons are disabled when no product selected", async () => {
    render(<BrowserRouter><KardexPage /></BrowserRouter>);
    await waitFor(() => {
      const entryBtn = screen.getByText("+ Entrada").closest("button");
      const exitBtn = screen.getByText("- Salida").closest("button");
      expect(entryBtn).toBeDisabled();
      expect(exitBtn).toBeDisabled();
    });
  });
});
