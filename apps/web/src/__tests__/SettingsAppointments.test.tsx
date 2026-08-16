/**
 * Tests de Settings — Sección "Agenda de Citas" (Spec 07 F6, D3).
 *
 * - Solo visible para business_type = restaurant.
 * - Carga companies.settings.appointments (getAppointmentSettings).
 * - Persiste vía PATCH /api/settings → patchAppointmentSettings (patrón voice_ai).
 * - Valida horas open < close antes de guardar.
 *
 * ⚠️ REQUISITO RON: los fixtures/mocks usan tenant-id = 3.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Settings } from "@/pages/Settings";

// ── business_type mutable por test ─────────────────────────
let mockBusinessType: "restaurant" | "retail" = "restaurant";

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
    getKardexInventory: fn, getKardex: fn,
    registerKardexEntry: fn, registerKardexExit: fn, registerProduct: fn, warehouseClose: fn,
    getSettings: jest.fn().mockResolvedValue({ palette, logo_url: null, favicon_url: null, date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima" }),
    updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette), updatePalette: jest.fn().mockResolvedValue(palette),
    getCompanySettings: jest.fn(() =>
      Promise.resolve({
        company_id: 3, // ⚠️ REQUISITO RON: tenant-id = 3
        business_type: mockBusinessType,
        business_name: "El Segoviano",
        features: { tables_enabled: true, tips_enabled: true, invoice_required: false, warranty_tracking: false, recipe_explosion: true, delivery_enabled: true, multi_waiter: false },
        tax_config: { igv_included_in_price: true, igv_rate: 0.18, icb_perception_pct: 0 },
        branding: { logo_url: null, favicon_url: null, primary_color: "#1a365d", secondary_color: "#2b6cb0", business_name: "El Segoviano" },
        palette, logo_url: null, favicon_url: null,
        date_format: "DD/MM/YYYY", currency: "PEN", timezone: "America/Lima",
      }),
    ),
    updateCompanySettings: fn, getCashflow: fn,
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn, getSales: fn, getSaleDetail: fn, getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: fn,
    getScenarios: fn, createScenario: fn, updateScenario: fn, deleteScenario: fn,
    __esModule: true,
  };
});

// ── Mock appointmentsApi (D3: get + patch /api/settings) ──
const mockGetAppointmentSettings = jest.fn();
const mockPatchAppointmentSettings = jest.fn();

jest.mock("@/services/appointmentsApi", () => ({
  getAppointmentSettings: (...a: unknown[]) => mockGetAppointmentSettings(...a),
  patchAppointmentSettings: (...a: unknown[]) => mockPatchAppointmentSettings(...a),
  DEFAULT_APPOINTMENT_SETTINGS: {
    enabled: false,
    hours: { open: "12:00", close: "23:00" },
    duration_min_default: 60,
    slot_granularity_min: 30,
    max_guests_per_table: 12,
    reminder_hours_before: 24,
    templates: { appointment_confirmed: "appointment_confirmed", appointment_reminder: "appointment_reminder" },
  },
}));

const loadedSettings = {
  enabled: true,
  hours: { open: "12:00", close: "23:00" },
  duration_min_default: 90,
  slot_granularity_min: 30,
  max_guests_per_table: 12,
  reminder_hours_before: 24,
  templates: { appointment_confirmed: "appointment_confirmed", appointment_reminder: "appointment_reminder" },
};

beforeEach(() => {
  jest.clearAllMocks();
  mockBusinessType = "restaurant";
  mockGetAppointmentSettings.mockResolvedValue(loadedSettings);
});

describe("Settings — Agenda de Citas (Spec 07 D3)", () => {
  it("carga y muestra la sección para restaurante", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    expect(await screen.findByText("📅 Agenda de Citas")).toBeInTheDocument();
    // esperar a que cargue companies.settings.appointments
    const checkbox = (await screen.findByLabelText("Agenda de citas habilitada")) as HTMLInputElement;
    expect(mockGetAppointmentSettings).toHaveBeenCalledTimes(1);
    expect(checkbox.checked).toBe(true);
    expect(screen.getByLabelText("Apertura de reservas")).toHaveValue("12:00");
    expect(screen.getByLabelText("Cierre de reservas")).toHaveValue("23:00");
    expect(screen.getByLabelText("Duración default (min)")).toHaveValue(90);
    expect(screen.getByLabelText("Recordatorio (horas antes)")).toHaveValue(24);
  });

  it("persiste los cambios vía patchAppointmentSettings (PATCH /api/settings)", async () => {
    mockPatchAppointmentSettings.mockResolvedValue({ ...loadedSettings, hours: { open: "13:00", close: "23:30" } });
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await screen.findByText("📅 Agenda de Citas");
    await screen.findByLabelText("Apertura de reservas");

    fireEvent.change(screen.getByLabelText("Apertura de reservas"), { target: { value: "13:00" } });
    fireEvent.change(screen.getByLabelText("Cierre de reservas"), { target: { value: "23:30" } });
    fireEvent.change(screen.getByLabelText("Duración default (min)"), { target: { value: "120" } });
    fireEvent.change(screen.getByLabelText("Recordatorio (horas antes)"), { target: { value: "2" } });
    fireEvent.click(screen.getByText("Guardar agenda"));

    await waitFor(() => {
      expect(mockPatchAppointmentSettings).toHaveBeenCalledWith({
        enabled: true,
        hours: { open: "13:00", close: "23:30" },
        duration_min_default: 120,
        reminder_hours_before: 2,
      });
    });
    expect(await screen.findByText("Configuración de agenda guardada")).toBeInTheDocument();
  });

  it("valida open < close antes de guardar", async () => {
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await screen.findByText("📅 Agenda de Citas");
    await screen.findByLabelText("Apertura de reservas");

    fireEvent.change(screen.getByLabelText("Apertura de reservas"), { target: { value: "23:00" } });
    fireEvent.change(screen.getByLabelText("Cierre de reservas"), { target: { value: "12:00" } });
    fireEvent.click(screen.getByText("Guardar agenda"));

    expect(
      await screen.findByText("La hora de apertura debe ser anterior al cierre"),
    ).toBeInTheDocument();
    expect(mockPatchAppointmentSettings).not.toHaveBeenCalled();
  });

  it("no muestra la sección para business_type retail", async () => {
    mockBusinessType = "retail";
    render(<BrowserRouter><Settings /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🎨 Paleta de Colores")).toBeInTheDocument();
    });
    expect(screen.queryByText("📅 Agenda de Citas")).toBeNull();
    expect(mockGetAppointmentSettings).not.toHaveBeenCalled();
  });
});
