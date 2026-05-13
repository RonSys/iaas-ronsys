/**
 * Tests for AlertsBanner — coverage boost for severity rendering,
 * empty state, multiple alerts, and ordering.
 *
 * QA-03: Baja cobertura en AlertsBanner.tsx (42.85%)
 */
import { render, screen } from "@testing-library/react";
import { AlertsBanner } from "@/components/ui/AlertsBanner";
import type { CashflowAlert } from "@/components/ui/AlertsBanner";

describe("AlertsBanner", () => {
  // ─── Estado sin alertas ──────────────────────────────
  it("renders nothing when alerts array is empty", () => {
    const { container } = render(<AlertsBanner alerts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when alerts is null/undefined", () => {
    const { container } = render(<AlertsBanner alerts={null as any} />);
    expect(container.firstChild).toBeNull();
  });

  // ─── Severidades individuales ────────────────────────
  it("renders a red/critical alert with correct styling", () => {
    const alerts: CashflowAlert[] = [
      { severity: "red", message: "Ventas 30% bajo lo proyectado" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(screen.getByText("🔴")).toBeInTheDocument();
    expect(screen.getByText("Ventas 30% bajo lo proyectado")).toBeInTheDocument();
    expect(alert.firstElementChild).toHaveClass("bg-red-50");
  });

  it("renders a yellow/warning alert with correct styling", () => {
    const alerts: CashflowAlert[] = [
      { severity: "yellow", message: "Costo 12% sobre proyectado" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText("⚠️")).toBeInTheDocument();
    expect(screen.getByText("Costo 12% sobre proyectado")).toBeInTheDocument();
    const container = screen.getByRole("alert");
    expect(container.firstElementChild).toHaveClass("bg-yellow-50");
  });

  it("renders a green/info alert with correct styling", () => {
    const alerts: CashflowAlert[] = [
      { severity: "green", message: "Flujo de caja dentro del margen esperado" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText("✅")).toBeInTheDocument();
    expect(screen.getByText("Flujo de caja dentro del margen esperado")).toBeInTheDocument();
    const container = screen.getByRole("alert");
    expect(container.firstElementChild).toHaveClass("bg-green-50");
  });

  // ─── Múltiples alertas simultáneas ───────────────────
  it("renders multiple alerts of different severities", () => {
    const alerts: CashflowAlert[] = [
      { severity: "red", message: "Liquidez crítica" },
      { severity: "yellow", message: "Costo elevado" },
      { severity: "green", message: "Ingresos estables" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText("🔴")).toBeInTheDocument();
    expect(screen.getByText("⚠️")).toBeInTheDocument();
    expect(screen.getByText("✅")).toBeInTheDocument();
    expect(screen.getByText("Liquidez crítica")).toBeInTheDocument();
    expect(screen.getByText("Costo elevado")).toBeInTheDocument();
    expect(screen.getByText("Ingresos estables")).toBeInTheDocument();
  });

  it("renders multiple red alerts", () => {
    const alerts: CashflowAlert[] = [
      { severity: "red", message: "Ventas caen" },
      { severity: "red", message: "Margen negativo" },
      { severity: "red", message: "Caja insuficiente" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    const icons = screen.getAllByText("🔴");
    expect(icons).toHaveLength(3);
  });

  it("renders all alert messages in order", () => {
    const alerts: CashflowAlert[] = [
      { severity: "green", message: "Primero" },
      { severity: "yellow", message: "Segundo" },
      { severity: "red", message: "Tercero" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    const messages = screen.getAllByText(/Primero|Segundo|Tercero/);
    expect(messages).toHaveLength(3);
    expect(messages[0].textContent).toBe("Primero");
    expect(messages[1].textContent).toBe("Segundo");
    expect(messages[2].textContent).toBe("Tercero");
  });

  it("has role='alert' for accessibility", () => {
    const alerts: CashflowAlert[] = [
      { severity: "red", message: "Error" },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  // ─── Large volume ────────────────────────────────────
  it("renders 10+ alerts without crashing", () => {
    const alerts: CashflowAlert[] = Array.from({ length: 12 }, (_, i) => ({
      severity: (["red", "yellow", "green"] as const)[i % 3],
      message: `Alerta número ${i + 1}`,
    }));
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(screen.getByText("Alerta número 12")).toBeInTheDocument();
  });
});
