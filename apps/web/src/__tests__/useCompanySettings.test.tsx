/**
 * Tests for useCompanySettings hook and feature-flag conditional rendering.
 *
 * HU-F1-003: UI adaptativa según business_type y feature flags
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useCompanySettings } from "@/hooks/useCompanySettings";

// Mock the api module
jest.mock("@/services", () => ({
  getCompanySettings: jest.fn(),
  __esModule: true,
}));

import { getCompanySettings } from "@/services";

const mockedGetCompanySettings = getCompanySettings as jest.MockedFunction<typeof getCompanySettings>;

describe("useCompanySettings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("returns default features when loading", () => {
    mockedGetCompanySettings.mockImplementation(() => new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useCompanySettings());
    expect(result.current.loading).toBe(true);
    expect(result.current.features.tables_enabled).toBe(false);
    expect(result.current.features.tips_enabled).toBe(false);
    expect(result.current.features.invoice_required).toBe(false);
    expect(result.current.businessType).toBe("retail");
    expect(result.current.taxConfig.igv_rate).toBe(0.18);
  });

  it("exposes restaurant features correctly", async () => {
    mockedGetCompanySettings.mockResolvedValue({
      company_id: 1,
      business_type: "restaurant",
      business_name: "Test Restaurant",
      features: {
        tables_enabled: true,
        tips_enabled: true,
        invoice_required: false,
        warranty_tracking: false,
        recipe_explosion: true,
        delivery_enabled: true,
        multi_waiter: false, multi_warehouse: false,
      },
      tax_config: { igv_included_in_price: true, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
      palette: { primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" },
      logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima", branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "" },
    });

    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.businessType).toBe("restaurant");
    expect(result.current.features.tables_enabled).toBe(true);
    expect(result.current.features.tips_enabled).toBe(true);
    expect(result.current.features.invoice_required).toBe(false);
    expect(result.current.taxConfig.igv_included_in_price).toBe(true);
  });

  it("exposes hardware features correctly", async () => {
    mockedGetCompanySettings.mockResolvedValue({
      company_id: 1,
      business_type: "hardware",
      business_name: "Test Hardware",
      features: {
        tables_enabled: false,
        tips_enabled: false,
        invoice_required: true,
        warranty_tracking: true,
        recipe_explosion: false,
        delivery_enabled: false,
        multi_waiter: false, multi_warehouse: false,
      },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0.03, withholding_tax_rate: 0 },
      palette: { primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" },
      logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima", branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "" },
    });

    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.businessType).toBe("hardware");
    expect(result.current.features.tables_enabled).toBe(false);
    expect(result.current.features.tips_enabled).toBe(false);
    expect(result.current.features.invoice_required).toBe(true);
    expect(result.current.features.warranty_tracking).toBe(true);
    expect(result.current.taxConfig.igv_included_in_price).toBe(false);
    expect(result.current.taxConfig.icb_perception_pct).toBe(0.03);
  });

  it("handles API error gracefully", async () => {
    mockedGetCompanySettings.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    await waitFor(() => {
      expect(result.current.error).toBe("Network error");
    });
    expect(result.current.features.tables_enabled).toBe(false);
  });

  it("refetch updates data", async () => {
    mockedGetCompanySettings.mockResolvedValueOnce({
      company_id: 1, business_type: "retail", business_name: "Test",
      features: { tables_enabled: false, tips_enabled: false, invoice_required: false, warranty_tracking: false, recipe_explosion: false, delivery_enabled: false, multi_waiter: false, multi_warehouse: false },
      tax_config: { igv_included_in_price: false, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
      palette: { primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" },
      logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima", branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "" },
    });

    const { result } = renderHook(() => useCompanySettings());
    await waitFor(() => expect(result.current.loading).toBe(false));

    mockedGetCompanySettings.mockResolvedValueOnce({
      company_id: 1, business_type: "restaurant", business_name: "Test",
      features: { tables_enabled: true, tips_enabled: true, invoice_required: true, warranty_tracking: true, recipe_explosion: true, delivery_enabled: true, multi_waiter: true, multi_warehouse: true },
      tax_config: { igv_included_in_price: true, igv_rate: 0.18, icb_perception_pct: 0, withholding_tax_rate: 0 },
      palette: { primary: "#111", secondary: "#222", accent: "#333", background: "#444", surface: "#555", text_primary: "#666", text_secondary: "#777", success: "#888", warning: "#999", error: "#aaa" },
      logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima", branding: { logo_url: null, favicon_url: null, primary_color: "#111", secondary_color: "#222", business_name: "" },
    });

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.businessType).toBe("restaurant");
    expect(result.current.features.tables_enabled).toBe(true);
  });
});
