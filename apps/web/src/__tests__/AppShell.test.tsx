import { render, screen } from "@testing-library/react";
import { AppShell } from "@/components/layout/AppShell";

describe("AppShell", () => {
  it("renders the app title", () => {
    render(<AppShell><p>Content</p></AppShell>);
    expect(screen.getByText("El Segoviano")).toBeInTheDocument();
  });

  it("renders children content", () => {
    render(<AppShell><p>Test Content</p></AppShell>);
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("renders section title when provided", () => {
    render(<AppShell title="Dashboard"><p>x</p></AppShell>);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    render(<AppShell><p>x</p></AppShell>);
    // Both desktop and mobile nav render the same links
    for (const label of ["📊 Dashboard", "🏗️ Setup", "🎮 Simulador", "📋 Reportes", "📦 Kárdex", "⚙️ Ajustes"]) {
      expect(screen.getAllByText(label)).toHaveLength(2);
    }
  });

  it("renders footer with version", () => {
    render(<AppShell><p>x</p></AppShell>);
    expect(screen.getByText(/IaaS-RonSys/)).toBeInTheDocument();
  });
});
