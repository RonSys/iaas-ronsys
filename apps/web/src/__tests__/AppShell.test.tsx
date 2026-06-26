/**
 * Tests for AppShell — layout principal con sidebar jerárquico.
 *
 * HU-F0-011: Sidebar jerárquico colapsable
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";

const companySettings = {
  company_id: 1, business_type: "retail", business_name: "Test",
  features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false },
  tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0 },
  palette: { primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" },
  branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "Test" },
  logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
};

jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(() => Promise.resolve(companySettings)),
  getSettings: jest.fn(() => Promise.resolve({ palette: companySettings.palette, logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima" })),
  getPalette: jest.fn(() => Promise.resolve(companySettings.palette)),
  __esModule: true,
}));

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ logout: jest.fn(), user: { email: "admin@elsegoviano.pe", role: "admin" } }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  __esModule: true,
}));

describe("AppShell", () => {
  const renderWithRouter = (ui: React.ReactElement) =>
    render(<MemoryRouter>{ui}</MemoryRouter>);

  it("renders the app title in sidebar", async () => {
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

  it("renders section title in header breadcrumb", async () => {
    renderWithRouter(<AppShell title="Dashboard"><p>x</p></AppShell>);
    await waitFor(() => {
      const elements = screen.getAllByText("Dashboard");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders sidebar navigation links", async () => {
    renderWithRouter(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      // Check key elements are present (sidebar logo + logout + investment section)
      expect(screen.getByText("El Segoviano")).toBeInTheDocument();
      expect(screen.getByText("Cerrar Sesión")).toBeInTheDocument();
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("renders footer with version", async () => {
    renderWithRouter(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText(/IaaS-RonSys/)).toBeInTheDocument();
    });
  });
});
