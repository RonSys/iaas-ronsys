/**
 * Tests for SectionsManagement — CRUD de secciones del restaurante.
 *
 * @module __tests__/SectionsManagement
 */
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { SectionsManagement } from "@/pages/restaurante/SectionsManagement";

// Mock authFetch
const mockAuthFetch = jest.fn();
jest.mock("@/services/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

// Mock useCompanySettings (needed by Sidebar/AppShell but SectionsManagement doesn't use directly)
jest.mock("@/hooks/useCompanySettings", () => ({
  useCompanySettings: () => ({
    businessType: "restaurant",
    features: { tables_enabled: true },
    loading: false,
    error: null,
  }),
}));

// Mock hooks used by Suspense fallback or app shell
jest.mock("@/hooks/usePalette", () => ({
  usePalette: () => ({ loading: false, palette: null }),
}));

describe("SectionsManagement", () => {
  const mockSections = [
    { id: 1, name: "Terraza", description: "Zona exterior", sort_order: 1, table_count: 4 },
    { id: 2, name: "Salón Principal", description: "Interior del local", sort_order: 2, table_count: 0 },
    { id: 3, name: "VIP", description: "", sort_order: 3, table_count: 2 },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sections: mockSections }),
    });
  });

  it("renders the page title", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("📋 Secciones")).toBeInTheDocument();
    });
  });

  it("displays sections in a table", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Terraza")).toBeInTheDocument();
      expect(screen.getByText("Salón Principal")).toBeInTheDocument();
      expect(screen.getByText("VIP")).toBeInTheDocument();
    });

    // Check description column
    expect(screen.getByText("Zona exterior")).toBeInTheDocument();
    expect(screen.getByText("Interior del local")).toBeInTheDocument();
  });

  it("shows table count badges", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      // There should be 3 badges with counts
      const badges = screen.getAllByText(/^[0-9]+$/);
      expect(badges.length).toBe(3);
    });
  });

  it("has a 'Nueva Sección' button", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("➕ Nueva Sección")).toBeInTheDocument();
    });
  });

  it("opens the create modal when clicking 'Nueva Sección'", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("➕ Nueva Sección")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("➕ Nueva Sección"));

    await waitFor(() => {
      expect(screen.getByText("Nueva Sección")).toBeInTheDocument();
    });
  });

  it("shows error toast when trying to delete section with tables", async () => {
    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Terraza")).toBeInTheDocument();
    });

    // Find all delete buttons and click the first one (Terraza, table_count=4)
    const deleteButtons = screen.getAllByTitle("Tiene mesas asignadas");
    expect(deleteButtons.length).toBeGreaterThan(0);
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText(/No se puede eliminar/),
      ).toBeInTheDocument();
    });
  });

  it("allows creating a new section", async () => {
    // Mock successful create
    mockAuthFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ sections: mockSections }) }) // initial fetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ id: 4, name: "Bar", description: "", sort_order: 4, table_count: 0 }) }) // create
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ sections: [...mockSections, { id: 4, name: "Bar", description: "", sort_order: 4, table_count: 0 }] }) }); // refetch

    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("➕ Nueva Sección")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("➕ Nueva Sección"));

    await waitFor(() => {
      expect(screen.getByText("Nueva Sección")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ej: Terraza, Salón Principal");
    fireEvent.change(nameInput, { target: { value: "Bar" } });

    fireEvent.click(screen.getByText("Crear Sección"));

    await waitFor(() => {
      expect(mockAuthFetch).toHaveBeenCalledWith(
        "/api/v1/restaurant/sections",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("shows empty state when no sections exist", async () => {
    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sections: [] }),
    });

    render(
      <BrowserRouter>
        <SectionsManagement />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("No hay secciones configuradas.")).toBeInTheDocument();
    });
  });
});
