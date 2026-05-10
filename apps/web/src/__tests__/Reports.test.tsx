import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Reports } from "@/pages/Reports";

jest.mock("@/services");

describe("Reports", () => {
  it("renders the title", () => {
    render(
      <BrowserRouter>
        <Reports />
      </BrowserRouter>,
    );
    expect(screen.getByText("📋 Reportes Financieros")).toBeInTheDocument();
  });

  it("renders all 4 tabs", () => {
    render(
      <BrowserRouter>
        <Reports />
      </BrowserRouter>,
    );
    expect(screen.getByText("📄 PYG")).toBeInTheDocument();
    expect(screen.getByText("⚖️ Balance")).toBeInTheDocument();
    expect(screen.getByText("🧾 BCSS")).toBeInTheDocument();
    expect(screen.getByText("🚦 Ratios")).toBeInTheDocument();
  });

  it("shows PYG tab by default with empty state", async () => {
    render(
      <BrowserRouter>
        <Reports />
      </BrowserRouter>,
    );
    // Default tab is PYG, income statement is null → shows empty message
    expect(
      await screen.findByText(/Ejecutá el Setup/),
    ).toBeInTheDocument();
  });

  it("switches to BCSS tab when clicked", async () => {
    render(
      <BrowserRouter>
        <Reports />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByText("🧾 BCSS"));
    // BCSS mock returns data with is_balanced: true
    expect(
      await screen.findByText(/Balance de Comprobaci/),
    ).toBeInTheDocument();
    expect(screen.getByText("✅ Cuadrado")).toBeInTheDocument();
  });

  it("switches to Ratios tab and shows empty state", async () => {
    render(
      <BrowserRouter>
        <Reports />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByText("🚦 Ratios"));
    // Ratios array is empty
    expect(
      await screen.findByText("Sin ratios calculados."),
    ).toBeInTheDocument();
  });
});
