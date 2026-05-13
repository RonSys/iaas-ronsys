/**
 * Tests for AppShell — layout principal.
 *
 * Updated: mock useCompanySettings to suppress async act warnings.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { AppShell } from "@/components/layout/AppShell";

jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  return {
    getCompanySettings: jest.fn().mockResolvedValue({
      company_id: 1, business_type: "retail", business_name: "Test",
      features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0 },
      palette, logo_url: null, favicon_url: null,
      date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
    }),
    __esModule: true,
  };
});

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    logout: jest.fn(),
    user: { email: "admin@elsegoviano.pe", role: "admin" },
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  __esModule: true,
}));

describe("AppShell", () => {
  it("renders the app title", async () => {
    render(<AppShell><p>Content</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText("El Segoviano")).toBeInTheDocument();
    });
  });

  it("renders children content", async () => {
    render(<AppShell><p>Test Content</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText("Test Content")).toBeInTheDocument();
    });
  });

  it("renders section title when provided", async () => {
    render(<AppShell title="Dashboard"><p>x</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("renders navigation links", async () => {
    render(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      for (const label of ["📊 Dashboard", "🏗️ Setup", "🎮 Simulador", "📋 Reportes", "📦 Kárdex", "⚙️ Ajustes"]) {
        expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(2);
      }
    });
  });

  it("renders footer with version", async () => {
    render(<AppShell><p>x</p></AppShell>);
    await waitFor(() => {
      expect(screen.getByText(/IaaS-RonSys/)).toBeInTheDocument();
    });
  });
});
