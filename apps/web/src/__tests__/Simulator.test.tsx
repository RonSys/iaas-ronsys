import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
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
    getBCSS: fn, getIncomeStatement: fn, getBalanceSheet: fn, getRatios: fn,
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
    getScenarios: jest.fn().mockResolvedValue([]),
    createScenario: fn, updateScenario: fn, deleteScenario: fn,
    __esModule: true,
  };
});

// Mock auth
jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "test@test.com", full_name: "Test", role: "admin", company_id: 1 },
    isAuthenticated: true, isLoading: false,
    login: jest.fn(), logout: jest.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("Simulator", () => {
  it("renders the title", async () => {
    render(<BrowserRouter><Simulator /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🎮 Simulador — ¿Qué pasa si...?")).toBeInTheDocument();
    });
  });

  it("renders all 5 sliders", async () => {
    render(<BrowserRouter><Simulator /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("💵 Precio promedio por plato")).toBeInTheDocument();
    });
    expect(screen.getByText("🍽️ Platos vendidos por día")).toBeInTheDocument();
    expect(screen.getByText("🥘 Costo de insumos (% de ventas)")).toBeInTheDocument();
    expect(screen.getByText("🏠 Alquiler mensual")).toBeInTheDocument();
    expect(screen.getByText("👥 Sueldos totales")).toBeInTheDocument();
  });

  it("renders manual Simular button", async () => {
    render(<BrowserRouter><Simulator /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🔄 Simular Ahora")).toBeInTheDocument();
    });
  });

  it("shows empty state message when no simulation has run", async () => {
    render(<BrowserRouter><Simulator /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Mové los sliders/)).toBeInTheDocument();
    });
  });
});
