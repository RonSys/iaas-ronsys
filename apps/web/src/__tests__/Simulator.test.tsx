import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Simulator } from "@/pages/Simulator";

// Mock API services
jest.mock("@/services");

// Mock auth — usuario autenticado
const mockUseAuth = jest.fn().mockReturnValue({
  user: { id: 1, email: "test@test.com", full_name: "Test", role: "admin", company_id: 1 },
  tenant: { id: 1 },
  isAuthenticated: true,
  isLoading: false,
  login: jest.fn(),
  logout: jest.fn(),
  refreshSession: jest.fn(),
});

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe("Simulator", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { id: 1, email: "test@test.com", full_name: "Test", role: "admin", company_id: 1 },
      tenant: { id: 1 },
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      logout: jest.fn(),
      refreshSession: jest.fn(),
    });
  });

  it("renders the title", () => {
    render(
      <BrowserRouter>
        <Simulator />
      </BrowserRouter>,
    );
    expect(screen.getByText("🎮 Simulador — ¿Qué pasa si...?")).toBeInTheDocument();
  });

  it("renders all 5 sliders", () => {
    render(
      <BrowserRouter>
        <Simulator />
      </BrowserRouter>,
    );
    expect(screen.getByText("💵 Precio promedio por plato")).toBeInTheDocument();
    expect(screen.getByText("🍽️ Platos vendidos por día")).toBeInTheDocument();
    expect(screen.getByText("🥘 Costo de insumos (% de ventas)")).toBeInTheDocument();
    expect(screen.getByText("🏠 Alquiler mensual")).toBeInTheDocument();
    expect(screen.getByText("👥 Sueldos totales")).toBeInTheDocument();
  });

  it("renders manual Simular button", () => {
    render(
      <BrowserRouter>
        <Simulator />
      </BrowserRouter>,
    );
    expect(screen.getByText("🔄 Simular Ahora")).toBeInTheDocument();
  });

  it("shows empty state message when no simulation has run", () => {
    render(
      <BrowserRouter>
        <Simulator />
      </BrowserRouter>,
    );
    expect(
      screen.getByText(/Mové los sliders/),
    ).toBeInTheDocument();
  });
});
