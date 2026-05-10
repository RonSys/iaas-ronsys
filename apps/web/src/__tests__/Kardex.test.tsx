import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { KardexPage } from "@/pages/Kardex";

jest.mock("@/services");

describe("KardexPage", () => {
  it("renders the title", () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    expect(screen.getByText("📦 Kárdex — Inventario")).toBeInTheDocument();
  });

  it("renders action buttons", () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    expect(screen.getByText("+ Producto")).toBeInTheDocument();
    expect(screen.getByText("+ Entrada")).toBeInTheDocument();
    expect(screen.getByText("- Salida")).toBeInTheDocument();
  });

  it("shows empty inventory message when no products", async () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    expect(
      await screen.findByText(/No hay productos registrados/),
    ).toBeInTheDocument();
  });

  it("opens new product modal when button clicked", async () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByText("+ Producto"));
    expect(await screen.findByText("📦 Nuevo Producto")).toBeInTheDocument();
    expect(screen.getByText("Crear Producto")).toBeInTheDocument();
  });

  it("closes new product modal on Cancelar", async () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByText("+ Producto"));
    expect(await screen.findByText("📦 Nuevo Producto")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancelar"));
    // Modal should close
    expect(screen.queryByText("📦 Nuevo Producto")).not.toBeInTheDocument();
  });

  it("entry and exit buttons are disabled when no product selected", () => {
    render(
      <BrowserRouter>
        <KardexPage />
      </BrowserRouter>,
    );
    const entryBtn = screen.getByText("+ Entrada").closest("button");
    const exitBtn = screen.getByText("- Salida").closest("button");
    expect(entryBtn).toBeDisabled();
    expect(exitBtn).toBeDisabled();
  });
});
