/**
 * Tests for Sales list components (HU-F2-011).
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { SaleFilters } from "@/components/sales/SaleFilters";
import { TicketPreview } from "@/components/sales/TicketPreview";
import type { SaleFilters as SaleFiltersType } from "@/types";

describe("SaleFilters", () => {
  const defaultFilters: SaleFiltersType = { page: 1, limit: 20 };

  it("renders all filter controls", () => {
    render(
      <SaleFilters
        filters={defaultFilters}
        onChange={jest.fn()}
        loading={false}
      />,
    );
    expect(screen.getByText("Desde")).toBeInTheDocument();
    expect(screen.getByText("Hasta")).toBeInTheDocument();
    expect(screen.getByText("Tipo Negocio")).toBeInTheDocument();
    expect(screen.getByText("Sesión #")).toBeInTheDocument();
    expect(screen.getByText("Estado")).toBeInTheDocument();
    expect(screen.getByText("Filtrar")).toBeInTheDocument();
    expect(screen.getByText("Limpiar")).toBeInTheDocument();
  });

  it("calls onChange when Filter is clicked", () => {
    const onChange = jest.fn();
    render(
      <SaleFilters
        filters={defaultFilters}
        onChange={onChange}
        loading={false}
      />,
    );
    fireEvent.click(screen.getByText("Filtrar"));
    expect(onChange).toHaveBeenCalledWith({ page: 1, limit: 20 });
  });

  it("clears filters when Limpiar is clicked", () => {
    const onChange = jest.fn();
    render(
      <SaleFilters
        filters={{ page: 1, limit: 20, business_type: "restaurant" }}
        onChange={onChange}
        loading={false}
      />,
    );
    fireEvent.click(screen.getByText("Limpiar"));
    expect(onChange).toHaveBeenCalledWith({ page: 1, limit: 20 });
  });

  it("disables inputs when loading", () => {
    render(
      <SaleFilters
        filters={defaultFilters}
        onChange={jest.fn()}
        loading={true}
      />,
    );
    const filterBtn = screen.getByText("Filtrar") as HTMLButtonElement;
    expect(filterBtn.disabled).toBe(true);
  });
});

describe("TicketPreview", () => {
  it("shows loading state", () => {
    render(
      <TicketPreview
        ticketText={null}
        loading={true}
        error={null}
        onClose={jest.fn()}
      />,
    );
    // Should show spinner
  });

  it("renders ticket text in <pre>", () => {
    const ticketText =
      "╔═══════════════════╗\n║  EL SEGOVIANO     ║\n╠═══════════════════╣\n║ VTA-001           ║\n║ Total: S/ 118.00  ║\n╚═══════════════════╝";

    render(
      <TicketPreview
        ticketText={ticketText}
        loading={false}
        error={null}
        onClose={jest.fn()}
      />,
    );
    expect(screen.getByText("🧾 Ticket")).toBeInTheDocument();
    expect(screen.getByText("🖨️ Imprimir")).toBeInTheDocument();
    // The ticket text should be rendered
    expect(screen.getByText(/EL SEGOVIANO/)).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(
      <TicketPreview
        ticketText={null}
        loading={false}
        error="Error al cargar ticket"
        onClose={jest.fn()}
      />,
    );
    expect(screen.getByText("Error al cargar ticket")).toBeInTheDocument();
  });

  it("calls onClose when cerrar clicked", () => {
    const onClose = jest.fn();
    render(
      <TicketPreview
        ticketText={null}
        loading={false}
        error={null}
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByText("Cerrar"));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows empty message when no ticket", () => {
    render(
      <TicketPreview
        ticketText={null}
        loading={false}
        error={null}
        onClose={jest.fn()}
      />,
    );
    expect(screen.getByText("No hay ticket disponible")).toBeInTheDocument();
  });
});
