/**
 * Test de renderizado — DashboardOwner (Spec 04, Panel del Dueño V1+V2).
 *
 * Verifica que la página renderiza los bloques V2 (CA10-CA14):
 * alertas, KPIs con comparativa, heatmaps, márgenes y botón de descarga.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { DashboardOwner } from "@/pages/DashboardOwner";
import type { OwnerDashboardResponse } from "@/types";

const PAYLOAD: OwnerDashboardResponse = {
  period: { date_from: "2026-08-04", date_to: "2026-08-10" },
  kpis: {
    sales_total: 4850.5,
    orders_count: 42,
    avg_ticket: 115.5,
    orders_delivery: 15,
    orders_dine_in: 22,
    orders_takeout: 5,
    delivery_pct: 35.7,
    kitchen_open: 6,
    delivery_in_route: 3,
  },
  sales_by_hour: [
    { hour: 12, dine_in: 850.0, delivery: 420.0 },
    { hour: 13, dine_in: 1100.0, delivery: 380.0 },
  ],
  sales_by_weekday: [{ weekday: 1, total: 3200.0 }],
  channels: { dine_in: 2450.0, takeout: 620.0, delivery: 1780.5 },
  top_platos: [{ name: "Ceviche Clásico", qty: 18, total: 720.0 }],
  payments: { yape: 1800.0, plin: 950.0, cash: 1200.0, card: 700.5, transfer: 200.0 },
  delivery: {
    orders_by_zone: [{ zone: "Norte", orders: 6 }],
    funnel: { received: 15, preparing: 11, ready: 8, out_for_delivery: 3, delivered: 12, cancelled: 1 },
    avg_delivery_min: 32,
    gmv: 1780.5,
    fee_total: 89.0,
  },
  campaigns: [
    { campaign_id: 1, name: "Lanzamiento", channel: "meta", spend: 150.0, orders: 12, gmv: 900.0, aov: 75.0, roas: 6.0 },
  ],
  // V2
  heatmap: {
    dine_in: { rows: [{ hour: 12, weekday: 1, total: 320.5 }] },
    delivery: { rows: [{ hour: 12, weekday: 1, total: 210.0 }] },
  },
  margins: {
    by_channel: [
      { channel: "dine_in", revenue: 2450.0, cost: 980.0, margin_pct: 60.0 },
      { channel: "takeout", revenue: 620.0, cost: 310.0, margin_pct: 50.0 },
      { channel: "delivery", revenue: 1780.5, cost: 890.25, margin_pct: 50.0 },
    ],
    costable_note: "Margen calculado solo sobre ítems con receta (average_cost); ventas sin receta no aportan costo (decisión R2)",
  },
  comparison: {
    current: { sales_total: 4850.5, orders_count: 42, avg_ticket: 115.5, delivery_pct: 35.7 },
    previous: { sales_total: 4100.0, orders_count: 38, avg_ticket: 107.9, delivery_pct: 31.2 },
    deltas: { sales_total_pct: 18.3, orders_count_pct: 10.5, avg_ticket_pct: 7.0, delivery_pct_delta: 4.5 },
  },
  alerts: [{ severity: "yellow", metric: "sales_total", message: "Hoy Ventas -12% vs promedio últimos 7 días" }],
};

jest.mock("@/services/dashboardApi", () => ({
  getOwnerDashboard: jest.fn(),
  exportOwnerDashboardCsv: jest.fn(),
  exportOwnerDashboardPdf: jest.fn(),
}));

import { exportOwnerDashboardCsv, exportOwnerDashboardPdf, getOwnerDashboard } from "@/services/dashboardApi";

beforeEach(() => {
  jest.clearAllMocks();
  (getOwnerDashboard as jest.Mock).mockResolvedValue(PAYLOAD);
  (exportOwnerDashboardCsv as jest.Mock).mockResolvedValue({
    blob: new Blob(["# kpis\n"]),
    filename: "panel_dueño_20260810.csv",
  });
  (exportOwnerDashboardPdf as jest.Mock).mockResolvedValue({
    blob: new Blob(["%PDF-1.4"]),
    filename: "panel_dueño_20260810.pdf",
  });
  // jsdom no implementa URL.createObjectURL → stub para el flujo de descarga
  Object.defineProperty(URL, "createObjectURL", {
    writable: true,
    configurable: true,
    value: jest.fn(() => "blob:mock"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    writable: true,
    configurable: true,
    value: jest.fn(),
  });
});

describe("DashboardOwner", () => {
  it("renders el header con botón de descarga CSV (CA13)", async () => {
    render(
      <BrowserRouter>
        <DashboardOwner />
      </BrowserRouter>,
    );
    expect(screen.getByText("Panel del Dueño")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Descargar CSV/ })).toBeInTheDocument();
  });

  it("muestra el banner de alertas (CA14) y los KPIs con comparativa (CA12)", async () => {
    render(
      <BrowserRouter>
        <DashboardOwner />
      </BrowserRouter>,
    );
    // Alerta amarilla con mensaje del backend
    expect(await screen.findByText("Hoy Ventas -12% vs promedio últimos 7 días")).toBeInTheDocument();
    // Deltas: ▲ verde para sales_total (+18.3%), ▲ verde para delivery (+4.5 pts)
    expect(screen.getByText("▲ +18.3%")).toBeInTheDocument();
    expect(screen.getByText("▲ +4.5 pts")).toBeInTheDocument();
    // KPI base
    expect(screen.getByText("Ventas")).toBeInTheDocument();
  });

  it("renderiza heatmaps (CA10) y márgenes por canal (CA11)", async () => {
    render(
      <BrowserRouter>
        <DashboardOwner />
      </BrowserRouter>,
    );
    expect(await screen.findByText("Heatmap de demanda — Salón")).toBeInTheDocument();
    expect(screen.getByText("Heatmap de demanda — Delivery")).toBeInTheDocument();
    expect(screen.getByText("Margen por canal (costeo por recetas)")).toBeInTheDocument();
    // Nota de costeabilidad visible (R2)
    expect(screen.getByText(/decisión R2/)).toBeInTheDocument();
  });

  it("dropdown de descarga ofrece CSV y PDF, y PDF llama a exportOwnerDashboardPdf (CA13-b)", async () => {
    render(
      <BrowserRouter>
        <DashboardOwner />
      </BrowserRouter>,
    );
    // Trigger del dropdown (summary con rol button) visible
    expect(await screen.findByRole("button", { name: /Descargar$/ })).toBeInTheDocument();
    // Ambas opciones presentes en el menú (jsdom no oculta el contenido de <details>)
    expect(screen.getByRole("button", { name: /Descargar CSV/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Descargar PDF/ })).toBeInTheDocument();
    // Elegir PDF → llama al API client PDF con el rango seleccionado (CA13-b)
    fireEvent.click(screen.getByRole("button", { name: /Descargar PDF/ }));
    await waitFor(() => {
      expect(exportOwnerDashboardPdf).toHaveBeenCalledTimes(1);
      expect(exportOwnerDashboardPdf).toHaveBeenCalledWith(
        expect.objectContaining({ date_from: expect.any(String), date_to: expect.any(String) }),
      );
    });
    // El CSV NO se dispara al elegir PDF
    expect(exportOwnerDashboardCsv).not.toHaveBeenCalled();
  });
});
