/**
 * Tests for PosPage — full POS session lifecycle.
 *
 * HU-F2-008: UI de apertura y cierre de caja
 * HU-F0-016: Búsqueda de producto en venta mostrador
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { PosPage } from "@/pages/ventas/PosPage";

// Mock global fetch for ProductSearch categories call
beforeAll(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([]),
  }) as jest.Mock;
});

afterAll(() => {
  delete (global as any).fetch;
});

jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  const fn = jest.fn().mockResolvedValue(null);

  const mockSessionOpen = {
    id: 1, company_id: 1, user_id: 1,
    opened_at: "2026-06-01T08:00:00Z", closed_at: null,
    opening_cash: 500, closing_cash: null, expected_cash: null,
    difference: null, status: "open" as const, notes: null,
    total_sales: 1250, cash_sales: 800, card_sales: 450,
    yape_sales: 0, plin_sales: 0, transfer_sales: 0, sale_count: 5,
  };

  const mockSessionClose = {
    ...mockSessionOpen,
    status: "closed" as const,
    closed_at: "2026-06-01T18:00:00Z",
  };

  return {
    getHealth: fn, setupAccounting: fn,
    getBCSS: jest.fn().mockResolvedValue({ lines: [], total_debits: 0, total_credits: 0, is_balanced: true }),
    getIncomeStatement: jest.fn().mockResolvedValue(null),
    getBalanceSheet: jest.fn().mockResolvedValue(null),
    getRatios: jest.fn().mockResolvedValue([]),
    getKardexInventory: jest.fn().mockResolvedValue([]),
    getKardex: jest.fn().mockResolvedValue([]),
    registerKardexEntry: fn, registerKardexExit: fn,
    registerProduct: fn, warehouseClose: fn,
    getSettings: fn, updateSettings: fn,
    getPalette: jest.fn().mockResolvedValue(palette),
    updatePalette: fn,
    getCompanySettings: fn,
    updateCompanySettings: fn,
    getCashflow: fn,
    getCurrentPosSession: jest.fn().mockResolvedValue(mockSessionOpen),
    openPosSession: jest.fn().mockResolvedValue(mockSessionOpen),
    closePosSession: jest.fn().mockResolvedValue({
      session: mockSessionClose,
      total_sales: 1250,
      cash_expected: 1300,
      difference: -50,
    }),
    createSale: fn, getSales: fn, getSaleDetail: fn,
    getSaleTicket: fn, voidSale: fn, getPaymentMethods: fn,
    searchKardexProducts: fn,
    __esModule: true,
  };
});

describe("PosPage", () => {
  it("renders with session open status", async () => {
    render(<BrowserRouter><PosPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Caja Abierta")).toBeInTheDocument();
    });
    expect(screen.getByText("Sesión de caja activa")).toBeInTheDocument();
    expect(screen.getByText("🔒 Cerrar Caja")).toBeInTheDocument();
  });

  it("shows close modal when 'Cerrar Caja' is clicked", async () => {
    render(<BrowserRouter><PosPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("🔒 Cerrar Caja")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText("🔒 Cerrar Caja"));
    await waitFor(() => {
      expect(screen.getByText("Arqueo de Caja")).toBeInTheDocument();
    });
  });

  it("renders header with title", async () => {
    render(<BrowserRouter><PosPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("💰 Caja")).toBeInTheDocument();
    });
  });
});
