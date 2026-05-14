/**
 * Tests for AppShell — layout principal.
 *
 * Updated: complete mock with all required fields, suppress act warnings
 * via proper async handling with waitFor.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";

const palette = {
  primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
  background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
  text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
};

const defaultFeatures = {
  tables_enabled: false, tips_enabled: false, invoice_required: false,
  warranty_tracking: false, recipe_explosion: false, delivery_enabled: false,
  multi_waiter: false, multi_warehouse: false,
};

const defaultTaxConfig = {
  igv_included_in_price: false, igv_rate: 0.18,
  icb_perception_pct: 0, withholding_tax_rate: 0,
};

const defaultBranding = {
  logo_url: null, favicon_url: null,
  primary_color: "#1a365d", secondary_color: "#2b6cb0", business_name: "Test",
};

const companySettings = {
  company_id: 1, business_type: "retail", business_name: "Test",
  features: defaultFeatures, tax_config: defaultTaxConfig,
  branding: defaultBranding, palette,
  logo_url: null, favicon_url: null,
  date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
};

jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(() => Promise.resolve(companySettings)),
  getSettings: jest.fn(() => Promise.resolve({ palette, logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima" })),
  getPalette: jest.fn(() => Promise.resolve(palette)),
  __esModule: true,
}));

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    logout: jest.fn(),
    user: { email: "admin@elsegoviano.pe", role: "admin" },
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  __esModule: true,
}));

describe("AppShell", () => {
  const renderWithRouter = (ui: React.ReactElement) =>
    render(<MemoryRouter>{ui}</MemoryRouter>);

  it("renders the app title", async () => {
    renderWithRouter(<AppShell><p>Content</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText("El Segoviano")).toBeInTheDocument();
    });
  });

  it("renders children content", async () => {
    renderWithRouter(<AppShell><p>Test Content</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText("Test Content")).toBeInTheDocument();
    });
  });

  it("renders section title when provided", async () => {
    renderWithRouter(<AppShell title="Dashboard"><p>x</p></AppShell>);
    await waitFor(() => {
      const elements = screen.getAllByText("Dashboard");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders navigation links", async () => {
    renderWithRouter(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      for (const label of ["Dashboard", "Setup", "Simulador", "Reportes Financieros"]) {
        expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
      }
    });
  });

  it("renders footer with version", async () => {
    renderWithRouter(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText(/IaaS-RonSys/)).toBeInTheDocument();
    });
  });
});
