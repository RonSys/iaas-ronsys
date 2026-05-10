import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Settings } from "@/pages/Settings";

jest.mock("@/services");

describe("Settings", () => {
  it("renders the title", () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    expect(screen.getByText("⚙️ Configuración")).toBeInTheDocument();
  });

  it("renders palette section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    expect(
      await screen.findByText("🎨 Paleta de Colores"),
    ).toBeInTheDocument();
  });

  it("renders predefined palette presets", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    expect(await screen.findByText("Azul Marino")).toBeInTheDocument();
    expect(screen.getByText("Verde Bosque")).toBeInTheDocument();
    expect(screen.getByText("Rojizo Cálido")).toBeInTheDocument();
    expect(screen.getByText("Púrpura")).toBeInTheDocument();
  });

  it("renders color pickers for all 10 palette keys", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    // Wait for palette to load
    await screen.findByText("Azul Marino");

    // Color inputs use type="color" — query DOM directly
    const colorInputs = document.querySelectorAll('input[type="color"]');
    // We should have 10 color inputs (primary, secondary, accent, background,
    // surface, text_primary, text_secondary, success, warning, error)
    expect(colorInputs.length).toBeGreaterThanOrEqual(10);
  });

  it("renders preview section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    expect(
      await screen.findByText("👁️ Vista Previa"),
    ).toBeInTheDocument();
  });

  it("renders company info section", async () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>,
    );
    expect(
      await screen.findByText("🏢 Información de la Empresa"),
    ).toBeInTheDocument();
    expect(screen.getByText("PEN")).toBeInTheDocument();
    expect(screen.getByText("America/Lima")).toBeInTheDocument();
  });
});
