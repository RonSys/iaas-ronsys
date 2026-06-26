/**
 * Tests for TablesMap — Modal de apertura de mesa con autocompletado de mesero.
 *
 * HU-F0-006: Mapa visual de mesas + CRUD + apertura/cierre
 * - El campo "Nombre del Mesero" es un combobox con el nombre del usuario logueado preseleccionado
 * - Opción "Otro..." permite ingresar un nombre manual
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { act } from "react";

// ── Mock useAuth ───────────────────────────────────────────
const mockUseAuth = jest.fn();

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
  __esModule: true,
}));

// ── Mock authFetch — retorna distinto según la URL ──────
const mockAuthFetch = jest.fn().mockImplementation((url: string) => {
  if (url.includes("/sections")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ sections: [] }),
    });
  }
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve([]),
  });
});

jest.mock("@/services/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

// ── Mock WebSocket (no necesario en test) ─────────────────
beforeEach(() => {
  jest.spyOn(global, "WebSocket").mockImplementation(() => ({
    close: jest.fn(),
    send: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    onopen: null,
    onclose: null,
    onmessage: null,
    onerror: null,
    readyState: WebSocket.OPEN,
    binaryType: "blob",
    bufferedAmount: 0,
    extensions: "",
    protocol: "",
    url: "",
  } as unknown as WebSocket));
});

afterEach(() => {
  jest.restoreAllMocks();
  jest.clearAllMocks();
});

// Helper: renderizar TablesMap con datos mock
import { TablesMap } from "@/pages/restaurante/TablesMap";

async function renderWithTables(tables: Record<string, unknown>[] = []) {
  // Resetear mock de authFetch antes del render
  mockAuthFetch.mockClear();
  mockAuthFetch.mockImplementation((url: string) => {
    if (url.includes("/sections")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ sections: [] }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(tables),
    });
  });

  let container: ReturnType<typeof render>;
  await act(async () => {
    container = render(<TablesMap />);
  });

  // Esperar a que se resuelvan los fetches
  await waitFor(() => {
    expect(mockAuthFetch).toHaveBeenCalledWith("/api/v1/restaurant/tables");
  });

  return container!;
}

describe("TablesMap — Nombre del Mesero (autocompletado)", () => {
  // ── Mock de mesas para apertura ──
  const mockTables = [
    { id: 1, number: "1", capacity: 4, status: "available", section: "Salón" },
  ];

  describe("Con usuario logueado", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 1, email: "carlos@rest.com", full_name: "Carlos Pérez", role: "admin", company_id: 1 },
        tenant: { id: 1 },
        isAuthenticated: true,
        isLoading: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshSession: jest.fn(),
      });
    });

    it("renderiza el combobox con el nombre del usuario preseleccionado al abrir mesa", async () => {
      await renderWithTables(mockTables);

      // Hacer click en la mesa para abrir el modal
      const tableButton = screen.getByText("1");
      fireEvent.click(tableButton);

      // Verificar que el modal se abrió
      await waitFor(() => {
        expect(screen.getByText(/Nombre del Mesero/)).toBeInTheDocument();
      });

      // Verificar que el select tiene el nombre del usuario preseleccionado
      // (el primer combobox es el filtro de sección, el segundo es el del mesero)
      const selects = screen.getAllByRole("combobox") as HTMLSelectElement[];
      const waiterSelect = selects[selects.length - 1];
      expect(waiterSelect).not.toBeNull();
      expect(waiterSelect.value).toBe("Carlos Pérez");

      // Verificar que la opción con el nombre existe
      expect(screen.getByText("Carlos Pérez")).toBeInTheDocument();
    });

    it("no muestra el input manual cuando está seleccionado el nombre del usuario", async () => {
      await renderWithTables(mockTables);

      const tableButton = screen.getByText("1");
      fireEvent.click(tableButton);

      await waitFor(() => {
        expect(screen.getByText(/Nombre del Mesero/)).toBeInTheDocument();
      });

      // No debe haber input adicional porque seleccionamos "Carlos Pérez"
      expect(screen.queryByPlaceholderText("Escribir otro nombre")).toBeNull();
    });

    it("cambia a 'Otro...' y permite escribir manualmente", async () => {
      await renderWithTables(mockTables);

      const tableButton = screen.getByText("1");
      fireEvent.click(tableButton);

      await waitFor(() => {
        expect(screen.getByText(/Nombre del Mesero/)).toBeInTheDocument();
      });

      // Cambiar a "Otro..."
      const selects = screen.getAllByRole("combobox") as HTMLSelectElement[];
      const waiterSelect = selects[selects.length - 1];
      fireEvent.change(waiterSelect, { target: { value: "__other__" } });

      // Ahora debe aparecer el input manual
      const manualInput = screen.getByPlaceholderText("Escribir otro nombre");
      expect(manualInput).toBeInTheDocument();

      // Escribir un nombre manual
      fireEvent.change(manualInput, { target: { value: "María García" } });
      expect(manualInput).toHaveValue("María García");
    });
  });

  describe("Sin usuario logueado (user = null)", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: null,
        tenant: null,
        isAuthenticated: false,
        isLoading: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshSession: jest.fn(),
      });
    });

    it("el combobox muestra 'Sin nombre' y el valor está vacío", async () => {
      await renderWithTables(mockTables);

      const tableButton = screen.getByText("1");
      fireEvent.click(tableButton);

      await waitFor(() => {
        expect(screen.getByText(/Nombre del Mesero/)).toBeInTheDocument();
      });

      // Con user null, openWaiter es "" y el select muestra "Sin nombre"
      const selects = screen.getAllByRole("combobox") as HTMLSelectElement[];
      const waiterSelect = selects[selects.length - 1];
      expect(waiterSelect.value).toBe("");

      // Debe mostrar "Sin nombre" como texto de la opción
      expect(screen.getByText("Sin nombre")).toBeInTheDocument();
    });

    it("el botón 'Abrir Mesa' está deshabilitado porque openWaiter está vacío", async () => {
      await renderWithTables(mockTables);

      const tableButton = screen.getByText("1");
      fireEvent.click(tableButton);

      await waitFor(() => {
        expect(screen.getByText(/Nombre del Mesero/)).toBeInTheDocument();
      });

      // Botón debe estar deshabilitado porque openWaiter está vacío
      const openButton = screen.getByText("🔓 Abrir Mesa") as HTMLButtonElement;
      expect(openButton.disabled).toBe(true);
    });
  });
});
