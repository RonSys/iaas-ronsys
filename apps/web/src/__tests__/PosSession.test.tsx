/**
 * Tests for POS Session components.
 *
 * HU-F2-008: UI de apertura y cierre de caja
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PosSessionOpen } from "@/components/pos/PosSessionOpen";
import { PosSessionStatus } from "@/components/pos/PosSessionStatus";
import { PosSessionClose } from "@/components/pos/PosSessionClose";
import type { PosSession, PosSessionCloseResponse } from "@/types";

const mockSession: PosSession = {
  id: 1,
  company_id: 1,
  user_id: 1,
  opened_at: "2026-06-01T08:00:00Z",
  closed_at: null,
  opening_cash: 500,
  closing_cash: null,
  expected_cash: null,
  difference: null,
  status: "open",
  notes: null,
  total_sales: 1250.5,
  cash_sales: 800,
  card_sales: 450.5,
  yape_sales: 0,
  plin_sales: 0,
  transfer_sales: 0,
  sale_count: 5,
};

describe("PosSessionOpen", () => {
  it("renders the open cash form", () => {
    render(
      <PosSessionOpen
        onSubmit={jest.fn()}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("Caja Cerrada")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("0.00")).toBeInTheDocument();
    expect(screen.getByText("🔓 Abrir Caja")).toBeInTheDocument();
  });

  it("validates empty amount", async () => {
    render(
      <PosSessionOpen
        onSubmit={jest.fn()}
        loading={false}
        error={null}
      />,
    );
    fireEvent.click(screen.getByText("🔓 Abrir Caja"));
    await waitFor(() => {
      expect(screen.getByText("El monto inicial es requerido")).toBeInTheDocument();
    });
  });

  it("validates negative amount", async () => {
    const onSubmit = jest.fn();
    render(
      <PosSessionOpen
        onSubmit={onSubmit}
        loading={false}
        error={null}
      />,
    );
    const input = screen.getByPlaceholderText("0.00");
    await userEvent.clear(input);
    await userEvent.type(input, "-50");
    await userEvent.click(screen.getByText("🔓 Abrir Caja"));
    expect(screen.getByText("El monto no puede ser negativo")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("validates zero amount", async () => {
    const onSubmit = jest.fn();
    render(
      <PosSessionOpen
        onSubmit={onSubmit}
        loading={false}
        error={null}
      />,
    );
    const input = screen.getByPlaceholderText("0.00");
    await userEvent.clear(input);
    await userEvent.type(input, "0");
    await userEvent.click(screen.getByText("🔓 Abrir Caja"));
    expect(screen.getByText("El monto no puede ser cero")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with correct amount", async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <PosSessionOpen
        onSubmit={onSubmit}
        loading={false}
        error={null}
      />,
    );
    const input = screen.getByPlaceholderText("0.00");
    fireEvent.change(input, { target: { value: "500" } });
    fireEvent.click(screen.getByText("🔓 Abrir Caja"));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(500);
    });
  });

  it("shows loading state", () => {
    render(
      <PosSessionOpen
        onSubmit={jest.fn()}
        loading={true}
        error={null}
      />,
    );
    expect(screen.getByText("Abriendo...")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(
      <PosSessionOpen
        onSubmit={jest.fn()}
        loading={false}
        error="409 Ya existe una sesión abierta"
      />,
    );
    expect(screen.getByText("409 Ya existe una sesión abierta")).toBeInTheDocument();
  });
});

describe("PosSessionStatus", () => {
  it("renders session info when open", () => {
    render(
      <PosSessionStatus
        session={mockSession}
        onCloseRequest={jest.fn()}
      />,
    );
    expect(screen.getByText("Caja Abierta")).toBeInTheDocument();
    expect(screen.getByText("S/ 500")).toBeInTheDocument();
    // fmtCurrency rounds 1250.5 → S/ 1,251 (maxFractionDigits: 0)
    expect(screen.getByText("S/ 1,251")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("🔒 Cerrar Caja")).toBeInTheDocument();
  });
});

describe("PosSessionClose", () => {
  it("renders arqueo modal", () => {
    render(
      <PosSessionClose
        expectedCash={1300}
        totalSales={1250.5}
        onSubmit={jest.fn()}
        loading={false}
        error={null}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByText("Arqueo de Caja")).toBeInTheDocument();
    // fmtCurrency rounds 1250.5 → S/ 1,251
    expect(screen.getByText("S/ 1,251")).toBeInTheDocument();
    expect(screen.getByText("S/ 1,300")).toBeInTheDocument();
    expect(screen.getByText("Confirmar Cierre")).toBeInTheDocument();
  });

  it("calls onSubmit with closingCash and notes", async () => {
    const onSubmit = jest.fn().mockResolvedValue({
      session: { ...mockSession, status: "closed" as const, closed_at: "2026-06-01T18:00:00Z" },
      total_sales: 1250.5,
      cash_expected: 1300,
      difference: -50,
    } as PosSessionCloseResponse);

    render(
      <PosSessionClose
        expectedCash={1300}
        totalSales={1250.5}
        onSubmit={onSubmit}
        loading={false}
        error={null}
        onCancel={jest.fn()}
      />,
    );

    const input = screen.getByPlaceholderText("0.00");
    fireEvent.change(input, { target: { value: "1250" } });
    fireEvent.click(screen.getByText("Confirmar Cierre"));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(1250, "");
    });
  });

  it("shows difference calculation", async () => {
    render(
      <PosSessionClose
        expectedCash={1300}
        totalSales={1250.5}
        onSubmit={jest.fn()}
        loading={false}
        error={null}
        onCancel={jest.fn()}
      />,
    );

    const input = screen.getByPlaceholderText("0.00");
    fireEvent.change(input, { target: { value: "1250" } });
    await waitFor(() => {
      expect(screen.getByText(/Faltante/)).toBeInTheDocument();
    });
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = jest.fn();
    render(
      <PosSessionClose
        expectedCash={1300}
        totalSales={1250.5}
        onSubmit={jest.fn()}
        loading={false}
        error={null}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByText("Cancelar"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("shows close result screen after successful close", async () => {
    const onSubmit = jest.fn().mockResolvedValue({
      session: { ...mockSession, status: "closed" as const, closed_at: "2026-06-01T18:00:00Z" },
      total_sales: 1250.5,
      cash_expected: 1300,
      difference: 50,
    } as PosSessionCloseResponse);

    render(
      <PosSessionClose
        expectedCash={1300}
        totalSales={1250.5}
        onSubmit={onSubmit}
        loading={false}
        error={null}
        onCancel={jest.fn()}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "1350" } });
    fireEvent.click(screen.getByText("Confirmar Cierre"));
    await waitFor(() => {
      expect(screen.getByText("Caja Cerrada")).toBeInTheDocument();
    });
  });
});
