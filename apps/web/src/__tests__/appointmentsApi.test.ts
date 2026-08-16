/**
 * Tests de appointmentsApi — Spec 07 F6 (Agenda de Citas).
 *
 * Cubre: helpers puros (fecha/hora locales), normalizadores, merge de settings
 * y las 7 funciones API (availability / create / list / patch / remind /
 * settings get+patch) con authFetch mockeado.
 *
 * ⚠️ REQUISITO RON: los fixtures/mocks usan tenant-id = 3.
 */
import {
  todayLocal,
  appointmentStartsAt,
  formatAppointmentTime,
  formatAppointmentEnd,
  addMinutesToTime,
  normalizeAppointments,
  normalizeSlots,
  mergeAppointmentSettings,
  getAvailability,
  createAppointment,
  listAppointments,
  patchAppointment,
  remindAppointment,
  getAppointmentSettings,
  patchAppointmentSettings,
  DEFAULT_APPOINTMENT_SETTINGS,
  ApiError,
  APPOINTMENT_STATUS_LABEL,
  APPOINTMENT_SOURCE_LABEL,
} from "@/services/appointmentsApi";

const mockAuthFetch = jest.fn();
jest.mock("@/services/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

function okResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  });
}

// ─── Fixtures (tenant-id = 3 — REQUISITO RON) ───────────────

const appointmentFixture = {
  id: 11,
  tenant_id: 3, // ⚠️ REQUISITO RON: tenant-id = 3
  table_id: 4,
  table_number: "4",
  section: "Salón",
  customer_name: "María García",
  customer_phone: "+51999000001",
  guests: 4,
  starts_at: "2026-08-15T20:00:00.000Z",
  duration_min: 90,
  status: "confirmada" as const,
  source: "voice_ai" as const,
  notes: null,
  call_id: "CALL-ABC-1",
};

const slotFixture = {
  table_id: 4,
  table_number: "4",
  section: "Salón",
  capacity: 6,
  start: "20:00",
  end: "21:30",
};

describe("appointmentsApi — helpers puros", () => {
  it("todayLocal devuelve YYYY-MM-DD local", () => {
    expect(todayLocal(new Date(2026, 7, 15))).toBe("2026-08-15");
    expect(todayLocal(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  it("appointmentStartsAt combina fecha + hora en ISO local", () => {
    const iso = appointmentStartsAt("2026-08-15", "20:30");
    const d = new Date(iso);
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(7); // agosto
    expect(d.getDate()).toBe(15);
    expect(d.getHours()).toBe(20);
    expect(d.getMinutes()).toBe(30);
  });

  it("formatAppointmentTime / formatAppointmentEnd", () => {
    const iso = appointmentStartsAt("2026-08-15", "20:30");
    expect(formatAppointmentTime(iso)).toBe("20:30");
    expect(formatAppointmentEnd(iso, 90)).toBe("22:00");
    expect(formatAppointmentEnd(iso, 0)).toBe("20:30");
  });

  it("addMinutesToTime suma minutos con wrap 24h", () => {
    expect(addMinutesToTime("12:00", 90)).toBe("13:30");
    expect(addMinutesToTime("20:00", 60)).toBe("21:00");
    expect(addMinutesToTime("23:00", 90)).toBe("00:30"); // pasa de medianoche
    expect(addMinutesToTime("13:30", 0)).toBe("13:30");
  });

  it("normalizeAppointments acepta {items} y array plano", () => {
    expect(normalizeAppointments({ items: [appointmentFixture] })).toHaveLength(1);
    expect(normalizeAppointments([appointmentFixture])).toHaveLength(1);
    expect(normalizeAppointments(null)).toEqual([]);
    expect(normalizeAppointments({ items: undefined })).toEqual([]);
  });

  it("normalizeSlots acepta {slots} y array plano", () => {
    expect(normalizeSlots({ slots: [slotFixture] })).toHaveLength(1);
    expect(normalizeSlots([slotFixture])).toHaveLength(1);
    expect(normalizeSlots({})).toEqual([]);
  });

  it("mergeAppointmentSettings completa configs parciales con defaults", () => {
    const merged = mergeAppointmentSettings({
      enabled: true,
      hours: { open: "13:00" },
    });
    expect(merged.enabled).toBe(true);
    expect(merged.hours.open).toBe("13:00");
    expect(merged.hours.close).toBe("23:00"); // default preservado
    expect(merged.duration_min_default).toBe(60);
    expect(mergeAppointmentSettings(null)).toEqual(DEFAULT_APPOINTMENT_SETTINGS);
    expect(mergeAppointmentSettings(undefined)).toEqual(DEFAULT_APPOINTMENT_SETTINGS);
  });

  it("labels de estado y fuente (contrato Spec 07)", () => {
    expect(APPOINTMENT_STATUS_LABEL).toEqual({
      solicitada: "Solicitada",
      confirmada: "Confirmada",
      cumplida: "Cumplida",
      cancelada: "Cancelada",
      no_show: "No show",
    });
    expect(APPOINTMENT_SOURCE_LABEL.in_person).toBe("Staff");
    expect(APPOINTMENT_SOURCE_LABEL.voice_ai).toBe("Voz");
  });
});

describe("appointmentsApi — funciones API", () => {
  beforeEach(() => mockAuthFetch.mockReset());

  it("getAvailability consulta con date/guests/from/to y normaliza slots", async () => {
    mockAuthFetch.mockImplementation(() => okResponse({ slots: [slotFixture] }));
    const slots = await getAvailability({ date: "2026-08-15", guests: 4, from: "20:00", to: "21:30" });
    expect(slots).toEqual([slotFixture]);
    // URLSearchParams codifica ':' como %3A
    expect(mockAuthFetch).toHaveBeenCalledWith(
      "/api/v1/appointments/availability?date=2026-08-15&guests=4&from=20%3A00&to=21%3A30",
    );
  });

  it("getAvailability acepta respuesta en array plano", async () => {
    mockAuthFetch.mockImplementation(() => okResponse([slotFixture]));
    const slots = await getAvailability({ date: "2026-08-15", guests: 2, from: "12:00", to: "13:00" });
    expect(slots).toHaveLength(1);
  });

  it("createAppointment hace POST con el payload de la spec (source staff)", async () => {
    mockAuthFetch.mockImplementation(() => okResponse(appointmentFixture, 201));
    const created = await createAppointment({
      table_id: 4,
      date: "2026-08-15",
      time: "20:00",
      guests: 4,
      customer_name: "María García",
      customer_phone: "+51999000001",
      notes: "Cumpleaños",
      source: "in_person",
    });
    expect(created.id).toBe(11);
    const [url, init] = mockAuthFetch.mock.calls[0];
    expect(url).toBe("/api/v1/appointments");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      table_id: 4,
      date: "2026-08-15",
      time: "20:00",
      guests: 4,
      customer_name: "María García",
      customer_phone: "+51999000001",
      notes: "Cumpleaños",
      source: "in_person",
    });
  });

  it("listAppointments arma query con date/status/source y normaliza {items,total}", async () => {
    mockAuthFetch.mockImplementation(() =>
      okResponse({ items: [appointmentFixture], total: 1 }),
    );
    const res = await listAppointments({ date: "2026-08-15", status: "confirmada", source: "voice_ai" });
    expect(res.items).toHaveLength(1);
    expect(res.total).toBe(1);
    expect(mockAuthFetch).toHaveBeenCalledWith(
      "/api/v1/appointments?date=2026-08-15&status=confirmada&source=voice_ai",
    );
  });

  it("listAppointments acepta array plano y sin parámetros", async () => {
    mockAuthFetch.mockImplementation(() => okResponse([appointmentFixture]));
    const res = await listAppointments();
    expect(res.items).toHaveLength(1);
    expect(res.total).toBe(1);
    expect(mockAuthFetch).toHaveBeenCalledWith("/api/v1/appointments");
  });

  it("patchAppointment hace PATCH con la transición de estado (R5)", async () => {
    mockAuthFetch.mockImplementation(() => okResponse({ ...appointmentFixture, status: "cumplida" }));
    const updated = await patchAppointment(11, { status: "cumplida" });
    expect(updated.status).toBe("cumplida");
    const [url, init] = mockAuthFetch.mock.calls[0];
    expect(url).toBe("/api/v1/appointments/11");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ status: "cumplida" });
  });

  it("remindAppointment hace POST al endpoint de recordatorio", async () => {
    mockAuthFetch.mockImplementation(() =>
      okResponse({ ok: true, message: "Recordatorio programado" }, 202),
    );
    const res = await remindAppointment(11);
    expect(res.message).toBe("Recordatorio programado");
    const [url, init] = mockAuthFetch.mock.calls[0];
    expect(url).toBe("/api/v1/appointments/11/remind");
    expect(init.method).toBe("POST");
  });

  it("getAppointmentSettings mergea con defaults (patrón voice_ai)", async () => {
    mockAuthFetch.mockImplementation(() =>
      okResponse({ appointments: { enabled: true, hours: { open: "13:00" } } }),
    );
    const s = await getAppointmentSettings();
    expect(s.enabled).toBe(true);
    expect(s.hours.open).toBe("13:00");
    expect(s.hours.close).toBe("23:00");
    expect(s.duration_min_default).toBe(60);
    expect(mockAuthFetch).toHaveBeenCalledWith("/api/settings");
  });

  it("getAppointmentSettings devuelve defaults si el backend aún no expone appointments", async () => {
    mockAuthFetch.mockImplementation(() => okResponse({ palette: { primary: "#000" } }));
    const s = await getAppointmentSettings();
    expect(s).toEqual(DEFAULT_APPOINTMENT_SETTINGS);
  });

  it("patchAppointmentSettings hace PATCH /api/settings con { appointments }", async () => {
    mockAuthFetch.mockImplementation(() =>
      okResponse({ appointments: { enabled: true, hours: { open: "12:00", close: "23:00" } } }),
    );
    const s = await patchAppointmentSettings({ enabled: true });
    expect(s.enabled).toBe(true);
    const [url, init] = mockAuthFetch.mock.calls[0];
    expect(url).toBe("/api/settings");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ appointments: { enabled: true } });
  });

  it("lanza ApiError con status y detalle (409 doble reserva)", async () => {
    mockAuthFetch.mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ detail: "Mesa ya reservada en ese horario" }),
      }),
    );
    const err = await getAvailability({ date: "2026-08-15", guests: 2, from: "20:00", to: "21:00" }).catch(
      (e: unknown) => e,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect((err as ApiError).message).toBe("Mesa ya reservada en ese horario");
  });
});
