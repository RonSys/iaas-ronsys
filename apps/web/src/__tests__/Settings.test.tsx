import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Settings } from "@/pages/config/SettingsPage";

const palette = {
  primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
  background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
  text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
};

const companySettings = {
  company_id: 1, business_type: "retail", business_name: "Test Co",
  features: {
    tables_enabled: false, tips_enabled: false, invoice_required: false,
    warranty_tracking: false, recipe_explosion: false, delivery_enabled: false,
    multi_waiter: false, multi_warehouse: false,
  },
  tax_config: {
    igv_included_in_price: false, igv_rate: 0.18,
    icb_perception_pct: 0, withholding_tax_rate: 0,
  },
  branding: {
    logo_url: null, favicon_url: null,
    primary_color: "#1a365d", secondary_color: "#2b6cb0", business_name: "Test Co",
  },
  palette, logo_url: null, favicon_url: null,
  date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
};

jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(() => Promise.resolve(companySettings)),
  getSettings: jest.fn(() => Promise.resolve({ palette, logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima" })),
  getPalette: jest.fn(() => Promise.resolve(palette)),
  updatePalette: jest.fn(() => Promise.resolve(palette)),
  updateCompanySettings: jest.fn(() => Promise.resolve(companySettings)),
  __esModule: true,
}));

describe("Settings", () => {
  it("renders the title", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("⚙️ Configuración")).toBeInTheDocument();
    });
  });

  it("renders palette section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("🎨 Paleta de Colores")).toBeInTheDocument();
    });
  });

  it("renders predefined palette presets", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Azul Marino")).toBeInTheDocument();
    });
    expect(screen.getByText("Verde Bosque")).toBeInTheDocument();
    expect(screen.getByText("Rojizo Cálido")).toBeInTheDocument();
    expect(screen.getByText("Púrpura")).toBeInTheDocument();
  });

  it("renders color pickers for all 10 palette keys", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Azul Marino")).toBeInTheDocument();
    });
    const colorInputs = document.querySelectorAll('input[type="color"]');
    expect(colorInputs.length).toBeGreaterThanOrEqual(10);
  });

  it("renders preview section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("👁️ Vista Previa")).toBeInTheDocument();
    });
  });

  it("renders company info section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("🏢 Información de la Empresa")).toBeInTheDocument();
    });
    expect(screen.getByText("PEN")).toBeInTheDocument();
    expect(screen.getByText("America/Lima")).toBeInTheDocument();
  });
});
