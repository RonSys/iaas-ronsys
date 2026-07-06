/**
 * Tests for SalesListPage — listado de ventas con filtros.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 */
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { SalesListPage } from "@/pages/SalesListPage";

jest.mock("@/services", () => {
  const palette = {
    primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e",
    background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c",
    text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e",
  };
  const fn = jest.fn().mockResolvedValue(null);

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
    getCompanySettings: fn, updateCompanySettings: fn,
    getCashflow: fn,
    openPosSession: fn, getCurrentPosSession: fn, closePosSession: fn,
    createSale: fn,
    getSales: jest.fn().mockResolvedValue({
      sales: [
        {
          id: 1, company_id: 1, session_id: 1, user_id: 1,
          sale_number: "VTA-001", sale_date: "2026-06-01", sale_time: "14:30:00",
          customer_name: "Cliente 1", customer_doc: null,
          subtotal: 100, discount_total: 0, tax_total: 18, tip_amount: 0,
          total: 118, business_type: "retail" as const,
          is_voided: false, void_reason: null, journal_entry_id: null,
          cashier_name: "Admin", payment_methods: ["cash"],
        },
        {
          id: 2, company_id: 1, session_id: 1, user_id: 1,
          sale_number: "VTA-002", sale_date: "2026-06-01", sale_time: "15:00:00",
          customer_name: "Cliente 2", customer_doc: null,
          subtotal: 200, discount_total: 0, tax_total: 36, tip_amount: 0,
          total: 236, business_type: "restaurant" as const,
          is_voided: true, void_reason: "Error en pedido", journal_entry_id: null,
          cashier_name: "Admin", payment_methods: ["card"],
        },
      ],
      total: 2, page: 1, limit: 20,
    }),
    getSaleDetail: jest.fn().mockResolvedValue({
      id: 1, company_id: 1, session_id: 1, user_id: 1,
      sale_number: "VTA-001", sale_date: "2026-06-01", sale_time: "14:30:00",
      customer_name: "Cliente 1", customer_doc: null,
      subtotal: 100, discount_total: 0, tax_total: 18, tip_amount: 0,
      total: 118, business_type: "retail" as const,
      is_voided: false, void_reason: null, journal_entry_id: null,
      cashier_name: "Admin", payment_methods: ["cash"],
      items: [{ product_id: "P001", item_name: "Producto A", item_type: "product", quantity: 2, unit_of_measure: "un", unit_price: 50, discount_pct: 0, discount_amount: 0, tax_pct: 0.18, tax_amount: 18, total: 118 }],
      payments: [{ payment_method: "cash", amount: 118, reference: null }],
      restaurant_data: null, hardware_data: null,
    }),
    getSaleTicket: jest.fn().mockResolvedValue({
      sale: {}, ticket_text: "=== TICKET ===\nVTA-001\nTotal: 118", format: "text",
    }),
    voidSale: jest.fn().mockResolvedValue({}),
    getPaymentMethods: fn, searchKardexProducts: fn,
    __esModule: true,
  };
});

describe("SalesListPage", () => {
  it("renders the page title", async () => {
    render(<BrowserRouter><SalesListPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("📋 Ventas")).toBeInTheDocument();
    });
  });

  it("shows total count of sales", async () => {
    render(<BrowserRouter><SalesListPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("2 ventas registradas")).toBeInTheDocument();
    });
  });

  it("renders filter controls", async () => {
    render(<BrowserRouter><SalesListPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("Desde")).toBeInTheDocument();
      expect(screen.getByText("Hasta")).toBeInTheDocument();
      expect(screen.getByText("Tipo Negocio")).toBeInTheDocument();
      // "Pago" label + option both exist
      const pagoLabels = screen.getAllByText("Pago");
      expect(pagoLabels.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders sales table with sale numbers", async () => {
    render(<BrowserRouter><SalesListPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("VTA-001")).toBeInTheDocument();
      expect(screen.getByText("VTA-002")).toBeInTheDocument();
    });
  });

  it("shows total amounts", async () => {
    render(<BrowserRouter><SalesListPage /></BrowserRouter>);
    await waitFor(() => {
      expect(screen.getByText("S/ 118.00")).toBeInTheDocument();
      expect(screen.getByText("S/ 236.00")).toBeInTheDocument();
    });
  });
});
