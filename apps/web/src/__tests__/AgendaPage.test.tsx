/**
 * Tests de AgendaPage — Spec 07 F6 (Agenda de Citas).
 *
 * Render + llamadas API mockeadas: lista del día, badges de estado/fuente,
 * acción rápida (confirmar → PATCH) y modal Nueva cita con disponibilidad real
 * (GET availability → POST create con source="in_person").
 *
 * ⚠️ REQUISITO RON: los fixtures/mocks usan tenant-id = 3.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AgendaPage } from "@/pages/restaurante/AgendaPage";
import {
  todayLocal,
  appointmentStartsAt,
  DEFAULT_APPOINTMENT_SETTINGS,
} from "@/services/appointmentsApi";

// ── Mocks de appointmentsApi (solo las funciones; constantes reales) ──
const mockListAppointments = jest.fn();
const mockGetAvailability = jest.fn();
const mockCreateAppointment = jest.fn();
const mockPatchAppointment = jest.fn();
const mockRemindAppointment = jest.fn();
const mockGetAppointmentSettings = jest.fn();

jest.mock("@/services/appointmentsApi", () => {
  const actual = jest.requireActual("@/services/appointmentsApi");
  return {
    ...actual,
    listAppointments: (...a: unknown[]) => mockListAppointments(...a),
    getAvailability: (...a: unknown[]) => mockGetAvailability(...a),
    createAppointment: (...a: unknown[]) => mockCreateAppointment(...a),
    patchAppointment: (...a: unknown[]) => mockPatchAppointment(...a),
    remindAppointment: (...a: unknown[]) => mockRemindAppointment(...a),
    getAppointmentSettings: (...a: unknown[]) => mockGetAppointmentSettings(...a),
  };
});

// ─── Fixtures (tenant-id = 3 — REQUISITO RON) ───────────────

const confirmada = {
  id: 11,
  tenant_id: 3, // ⚠️ REQUISITO RON: tenant-id = 3
  table_id: 4,
  table_number: "4",
  section: "Salón",
  customer_name: "María García",
  customer_phone: "+51999000001",
  guests: 4,
  starts_at: appointmentStartsAt("2026-08-15", "20:00"), // TZ-independiente
  duration_min: 90,
  status: "confirmada" as const,
  source: "voice_ai" as const,
  notes: null,
  call_id: "CALL-ABC-1",
};

const solicitada = {
  id: 12,
  tenant_id: 3, // ⚠️ REQUISITO RON: tenant-id = 3
  table_id: 7,
  table_number: "7",
  section: "Terraza",
  customer_name: "Carlos Ruiz",
  customer_phone: null,
  guests: 2,
  starts_at: appointmentStartsAt("2026-08-15", "21:00"),
  duration_min: 60,
  status: "solicitada" as const,
  source: "in_person" as const,
  notes: "Mesa cerca de la ventana",
  call_id: null,
};

const settingsEnabled = {
  ...DEFAULT_APPOINTMENT_SETTINGS,
  enabled: true,
};

beforeEach(() => {
  jest.clearAllMocks();
  mockListAppointments.mockResolvedValue({ items: [confirmada, solicitada], total: 2 });
  mockGetAppointmentSettings.mockResolvedValue(settingsEnabled);
});

describe("AgendaPage — vista del día", () => {
  it("renderiza el título y carga la agenda de hoy", async () => {
    render(<AgendaPage />);
    expect(await screen.findByText("📅 Agenda de Citas")).toBeInTheDocument();
    await waitFor(() => {
      expect(mockListAppointments).toHaveBeenCalledWith({
        date: todayLocal(),
        status: "",
        source: "",
      });
    });
    expect(await screen.findByText("María García")).toBeInTheDocument();
    expect(screen.getByText("Carlos Ruiz")).toBeInTheDocument();
  });

  it("muestra badges de estado y fuente (patrón F3)", async () => {
    render(<AgendaPage />);
    // esperar la lista cargada ("Confirmada"/"Solicitada" también existen en el
    // filtro y en los chips del resumen — no son señal de carga)
    await screen.findByText("María García");
    // badge de estado (opción del filtro + badge = ≥2)
    expect(screen.getAllByText("Confirmada").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Solicitada").length).toBeGreaterThanOrEqual(2);
    // fuente: voice_ai → "🤖 Voz" · in_person → "🧑‍💼 Staff"
    expect(screen.getByText("🤖 Voz")).toBeInTheDocument();
    expect(screen.getByText("🧑‍💼 Staff")).toBeInTheDocument();
    // mesa + sección (la sección vive en un span anidado)
    expect(screen.getByText(/🪑 4/)).toBeInTheDocument();
    expect(screen.getByText(/🪑 7/)).toBeInTheDocument();
    expect(screen.getByText("· Salón")).toBeInTheDocument();
    expect(screen.getByText("· Terraza")).toBeInTheDocument();
    // hora del rango (ISO → HH:MM local; 20:00 + duración 90 = 21:30)
    expect(screen.getByText(/20:00–21:30/)).toBeInTheDocument();
  });

  it("avisa cuando la agenda está desactivada (D3)", async () => {
    mockGetAppointmentSettings.mockResolvedValue(DEFAULT_APPOINTMENT_SETTINGS); // enabled: false
    render(<AgendaPage />);
    expect(
      await screen.findByText(/La agenda de citas está desactivada/),
    ).toBeInTheDocument();
  });

  it("filtra por estado y fuente (recarga con los filtros)", async () => {
    render(<AgendaPage />);
    await screen.findByText("María García");
    fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "confirmada" } });
    await waitFor(() => {
      expect(mockListAppointments).toHaveBeenLastCalledWith({
        date: todayLocal(),
        status: "confirmada",
        source: "",
      });
    });
    fireEvent.change(screen.getByLabelText("Fuente"), { target: { value: "voice_ai" } });
    await waitFor(() => {
      expect(mockListAppointments).toHaveBeenLastCalledWith({
        date: todayLocal(),
        status: "confirmada",
        source: "voice_ai",
      });
    });
  });
});

describe("AgendaPage — acciones rápidas (transiciones R5)", () => {
  it("confirmar una cita solicitada llama PATCH con status confirmada", async () => {
    mockPatchAppointment.mockResolvedValue({ ...solicitada, status: "confirmada" });
    render(<AgendaPage />);
    await screen.findByText("Carlos Ruiz");

    const confirmButtons = screen.getAllByText("✅ Confirmar");
    fireEvent.click(confirmButtons[0]);

    await waitFor(() => {
      expect(mockPatchAppointment).toHaveBeenCalledWith(12, { status: "confirmada" });
    });
    // mensaje de éxito
    expect(await screen.findByText(/Cita de Carlos Ruiz → Confirmada/)).toBeInTheDocument();
  });

  it("una cita confirmada ofrece cumplir / no show / cancelar", async () => {
    render(<AgendaPage />);
    await screen.findByText("María García");
    expect(screen.getByText("🍽️ Cumplir")).toBeInTheDocument();
    expect(screen.getByText("🚫 No show")).toBeInTheDocument();
    expect(screen.getAllByText("✕ Cancelar").length).toBeGreaterThanOrEqual(1);
    // ambas citas son recordables → dos botones 🔔
    expect(screen.getAllByText("🔔 Recordar").length).toBe(2);
  });

  it("recordatorio manual llama POST remind", async () => {
    mockRemindAppointment.mockResolvedValue({ ok: true, message: "Recordatorio programado" });
    render(<AgendaPage />);
    await screen.findByText("María García");
    // la primera 🔔 (cita 20:00, id 11) — la lista ordena por hora
    fireEvent.click(screen.getAllByText("🔔 Recordar")[0]);
    await waitFor(() => {
      expect(mockRemindAppointment).toHaveBeenCalledWith(11);
    });
    expect(await screen.findByText(/Recordatorio programado/)).toBeInTheDocument();
  });
});

describe("AgendaPage — modal Nueva cita (disponibilidad real, D4)", () => {
  it("abre el modal, consulta availability y crea con source in_person", async () => {
    mockGetAvailability.mockResolvedValue([
      {
        table_id: 4,
        table_number: "4",
        section: "Salón",
        capacity: 6,
        start: "12:00",
        end: "13:00",
      },
    ]);
    mockCreateAppointment.mockResolvedValue({ ...solicitada, id: 99 });

    render(<AgendaPage />);
    await screen.findByText("María García");
    fireEvent.click(screen.getByText("＋ Nueva cita"));

    // Selector de mesas libres basado en availability real
    expect(await screen.findByText(/Mesa 4/)).toBeInTheDocument();
    expect(screen.getByText(/capacidad 6/)).toBeInTheDocument();

    // availability consultada con hora/duratión default (12:00 + 60min)
    await waitFor(() => {
      expect(mockGetAvailability).toHaveBeenCalledWith({
        date: todayLocal(),
        guests: 2,
        from: "12:00",
        to: "13:00",
      });
    });

    fireEvent.change(screen.getByLabelText("Nombre del cliente *"), {
      target: { value: "Ana Torres" },
    });
    fireEvent.click(screen.getByText("Reservar mesa"));

    await waitFor(() => {
      expect(mockCreateAppointment).toHaveBeenCalledWith({
        table_id: 4,
        date: todayLocal(),
        time: "12:00",
        guests: 2,
        customer_name: "Ana Torres",
        customer_phone: null,
        notes: null,
        source: "in_person", // D7: solo staff + voz en F6
      });
    });
  });

  it("muestra aviso sin mesas libres y deshabilita guardar", async () => {
    mockGetAvailability.mockResolvedValue([]);
    render(<AgendaPage />);
    await screen.findByText("María García");
    fireEvent.click(screen.getByText("＋ Nueva cita"));

    expect(
      await screen.findByText(/Sin mesas libres en ese horario/),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nombre del cliente *"), {
      target: { value: "Ana Torres" },
    });
    const saveBtn = screen.getByText("Reservar mesa") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);
  });

  it("advierte cuando el rango queda fuera de la ventana (R3)", async () => {
    mockGetAvailability.mockResolvedValue([]);
    render(<AgendaPage />);
    await screen.findByText("María García");
    fireEvent.click(screen.getByText("＋ Nueva cita"));

    // cambiar hora a 22:00 → 22:00+60 = 23:00 (dentro); 22:30+60 = 23:30 (fuera)
    fireEvent.change(screen.getByLabelText("Hora *"), { target: { value: "22:30" } });
    expect(
      await screen.findByText(/fuera de la ventana de reservas/),
    ).toBeInTheDocument();
  });
});
