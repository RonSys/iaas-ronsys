/**
 * Tests for useCompanySettings hook — feature flags & conditional rendering.
 *
 * HU-F1-003: UI adaptativa según business_type y feature flags
 */
import { renderHook, act, waitFor } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import { AppShell } from "@/components/layout/AppShell";

// ── Mock global fetch ──
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve([]),
  } as Response),
) as jest.Mock;

// ── Mock del módulo services ──
jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(),
  __esModule: true,
}));

import { getCompanySettings } from "@/services";
const mockedGetSettings = getCompanySettings as jest.MockedFunction<typeof getCompanySettings>;

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ logout: jest.fn(), user: { email: "admin@elsegoviano.pe", role: "admin" } }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  __esModule: true,
}));

const mockPalette = {
  primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
  background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
  text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
};

function makeSettings(overrides: Record<string, any> = {}): import("@/types").CompanySettingsResponse {
  return {
    company_id: 1,
    business_type: "retail" as const,
    business_name: "Test Co",
    features: {
      tables_enabled: false,
      tips_enabled: false,
      invoice_required: false,
      warranty_tracking: false,
      recipe_explosion: false,
      delivery_enabled: false,
      multi_waiter: false,
      multi_warehouse: false,
    },
    tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
    branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "Test Co" },
    palette: mockPalette,
    logo_url: null,
    favicon_url: null,
    date_format: "DD/MM/YYYY",
    currency: "PEN",
    timezone: "America/Lima",
    ...overrides,
  } as import("@/types").CompanySettingsResponse;
}

describe("useCompanySettings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("returns default features while loading (API never resolves)", () => {
    mockedGetSettings.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useCompanySettings());
    expect(result.current.loading).toBe(true);
    expect(result.current.features.tables_enabled).toBe(false);
    expect(result.current.features.tips_enabled).toBe(false);
    expect(result.current.businessType).toBe("retail");
  });

  it("exposes restaurant features when API returns restaurant config", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({
        business_type: "restaurant",
        features: {
          tables_enabled: true,
          tips_enabled: true,
          invoice_required: false,
          warranty_tracking: false,
          recipe_explosion: true,
          delivery_enabled: true,
          multi_waiter: true,
        },
        tax_config: { igv_included_in_price: true, igv_rate: 0.18, icb_perception_pct: 0 },
      }),
    );

    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.businessType).toBe("restaurant");
    expect(result.current.features.tables_enabled).toBe(true);
    expect(result.current.features.tips_enabled).toBe(true);
    expect(result.current.features.warranty_tracking).toBe(false);
    expect(result.current.taxConfig.igv_included_in_price).toBe(true);
  });

  it("exposes hardware features when API returns hardware config", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({
        business_type: "hardware",
        features: {
          tables_enabled: false,
          tips_enabled: false,
          invoice_required: true,
          warranty_tracking: true,
          recipe_explosion: false,
          delivery_enabled: false,
          multi_waiter: false,
        },
        tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0.03 },
      }),
    );

    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.businessType).toBe("hardware");
    expect(result.current.features.tables_enabled).toBe(false);
    expect(result.current.features.invoice_required).toBe(true);
    expect(result.current.features.warranty_tracking).toBe(true);
    expect(result.current.taxConfig.icb_perception_pct).toBe(0.03);
  });

  it("handles API error gracefully and returns defaults", async () => {
    mockedGetSettings.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.features.tables_enabled).toBe(false);
  });

  it("refetch updates data after initial load", async () => {
    mockedGetSettings.mockResolvedValueOnce(makeSettings({ business_type: "retail" }));
    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.businessType).toBe("retail");

    mockedGetSettings.mockResolvedValueOnce(makeSettings({ business_type: "restaurant" }));
    await act(async () => { await result.current.refetch(); });
    expect(result.current.businessType).toBe("restaurant");
  });
});

// ── AppShell feature-flag rendering ──

describe("AppShell — conditional navigation by feature flags", () => {
  /** Helper: expand a sidebar section by clicking its toggle button */
  const expandSection = async (label: string) => {
    await act(async () => {
      const buttons = screen.getAllByRole("button", { name: new RegExp(label, "i") });
      for (const btn of buttons) {
        if (btn.querySelector("svg")) {
          btn.click();
          await new Promise((r) => setTimeout(r, 50));
        }
      }
    });
  };

  it("shows 'Mesas' link when tables_enabled is true", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "restaurant", features: { tables_enabled: true } }),
    );
    await act(async () => {
      render(
        <BrowserRouter>
          <AppShell title="Test">
            <p>content</p>
          </AppShell>
        </BrowserRouter>,
      );
    });
    await waitFor(() => expect(screen.getByText("content")).toBeInTheDocument());
    // Expand ERP → Restaurante sections
    await expandSection("ERP");
    await expandSection("Restaurante");
    await waitFor(() => {
      expect(screen.getAllByText("Mesas").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("hides 'Mesas' link when tables_enabled is false", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "retail", features: { tables_enabled: false } }),
    );
    render(
      <BrowserRouter>
        <AppShell title="Test">
          <p>content</p>
        </AppShell>
      </BrowserRouter>,
    );
    await waitFor(() => expect(screen.getByText("content")).toBeInTheDocument());
    await waitFor(() => expect(screen.queryByText("Mesas")).toBeNull());
  });

  it("shows 'Ventas' link (always visible)", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "hardware", features: { invoice_required: true } }),
    );
    await act(async () => {
      render(
        <BrowserRouter>
          <AppShell title="Test">
            <p>content</p>
          </AppShell>
        </BrowserRouter>,
      );
    });
    // Expand ERP section
    await expandSection("ERP");
    await waitFor(() => {
      expect(screen.getAllByText(/Ventas/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows 'Ventas' even when invoice_required is false", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ features: { invoice_required: false } }),
    );
    await act(async () => {
      render(
        <BrowserRouter>
          <AppShell title="Test">
            <p>content</p>
          </AppShell>
        </BrowserRouter>,
      );
    });
    await expandSection("ERP");
    await waitFor(() => {
      const links = screen.getAllByText(/Ventas/i);
      expect(links.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows POS access link", async () => {
    mockedGetSettings.mockResolvedValue(makeSettings());
    await act(async () => {
      render(
        <BrowserRouter>
          <AppShell title="Test">
            <p>content</p>
          </AppShell>
        </BrowserRouter>,
      );
    });
    await waitFor(() => expect(screen.getByText("content")).toBeInTheDocument());
    // Expand ERP → Ventas sections
    await expandSection("ERP");
    await expandSection("Ventas");
    await waitFor(() => {
      expect(screen.getAllByText(/Caja/i).length).toBeGreaterThanOrEqual(1);
    });
  });
});
