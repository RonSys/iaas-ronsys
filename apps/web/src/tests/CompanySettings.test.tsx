/**
 * Tests for useCompanySettings hook + Sidebar conditional rendering.
 *
 * HU-F1-003: UI adaptativa según business_type y feature flags
 * HU-F0-011: Sidebar jerárquico colapsable
 */
import { renderHook, waitFor } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import { AppShell } from "@/components/layout/AppShell";

global.fetch = jest.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response),
) as jest.Mock;

jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(),
  getPalette: jest.fn(() => Promise.resolve({ primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" })),
  getSettings: jest.fn(() => Promise.resolve(null)),
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
  primary: "#111", secondary: "#222", accent: "#333", background: "#444",
  surface: "#555", text_primary: "#666", text_secondary: "#777",
  success: "#888", warning: "#999", error: "#aaa",
};

function makeSettings(overrides: Record<string, any> = {}): import("@/types").CompanySettingsResponse {
  return {
    company_id: 1, business_type: "retail" as const, business_name: "Test Co",
    features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false },
    tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0 },
    branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "Test Co" },
    palette: mockPalette, logo_url: null, favicon_url: null,
    date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
    ...overrides,
  } as import("@/types").CompanySettingsResponse;
}

describe("useCompanySettings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("returns default features while loading", () => {
    mockedGetSettings.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useCompanySettings());
    expect(result.current.loading).toBe(true);
    expect(result.current.features.tables_enabled).toBe(false);
    expect(result.current.businessType).toBe("retail");
    expect(result.current.taxConfig.igv_rate).toBe(0.18);
  });

  it("exposes restaurant features when API returns restaurant config", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "restaurant", features: { tables_enabled: true, tips_enabled: true } }),
    );
    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.businessType).toBe("restaurant");
    expect(result.current.features.tables_enabled).toBe(true);
  });

  it("handles API error gracefully", async () => {
    mockedGetSettings.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
  });
});

// ── Sidebar conditional rendering ──

describe("AppShell — conditional navigation by feature flags", () => {
  beforeEach(() => {
    // Pre-expand sidebar sections so nav links are visible
    sessionStorage.setItem("sidebar:ventas", "true");
    sessionStorage.setItem("sidebar:restaurante", "true");
    sessionStorage.setItem("sidebar:inventario", "true");
    sessionStorage.setItem("sidebar:finanzas", "true");
    sessionStorage.setItem("sidebar:config", "true");
  });

  afterEach(() => sessionStorage.clear());

  it("shows 'Mesas' link when business_type is restaurant", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "restaurant", features: { tables_enabled: true } }),
    );
    render(<BrowserRouter><AppShell title="Test"><p>content</p></AppShell></BrowserRouter>);
    await waitFor(() => {
      const elements = screen.getAllByText("Mesas");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("hides 'Mesas' link when business_type is retail", async () => {
    mockedGetSettings.mockResolvedValue(
      makeSettings({ business_type: "retail", features: { tables_enabled: false } }),
    );
    render(<BrowserRouter><AppShell title="Test"><p>content</p></AppShell></BrowserRouter>);
    // Need to wait for useCompanySettings to resolve and re-render
    await waitFor(() => expect(screen.getByText("content")).toBeInTheDocument());
    // Restaurant section not rendered at all for retail
    expect(screen.queryByText("Mesas")).toBeNull();
  });

  it("shows 'Ventas / POS' section (always visible)", async () => {
    mockedGetSettings.mockResolvedValue(makeSettings({ business_type: "hardware" }));
    render(<BrowserRouter><AppShell title="Test"><p>content</p></AppShell></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Ventas / POS")).toBeInTheDocument();
    });
  });

  it("shows 'Caja / POS' nav item in Ventas section", async () => {
    mockedGetSettings.mockResolvedValue(makeSettings());
    render(<BrowserRouter><AppShell title="Test"><p>content</p></AppShell></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Caja / POS")).toBeInTheDocument();
    });
  });

  it("shows logout button always visible", async () => {
    mockedGetSettings.mockResolvedValue(makeSettings());
    render(<BrowserRouter><AppShell title="Test"><p>content</p></AppShell></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Cerrar Sesión")).toBeInTheDocument();
    });
  });
});
