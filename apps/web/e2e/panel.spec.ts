/**
 * E2E: Panel del Dueño (Spec 04) — KPIs, gráficos, rangos.
 *
 * Data: GET /api/v1/dashboard/owner?date_from=&date_to= (mockeado).
 * Contrato: src/types/dashboard.ts → OwnerDashboardResponse.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Panel del Dueño", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/panel");
    // Esperar a que cargue el header del panel (no skeleton)
    await expect(page.locator("h2").first()).toContainText("Panel del Dueño", {
      timeout: 15000,
    });
  });

  test("carga KPIs del día tras el login", async ({ authenticatedPage: page }) => {
    // Títulos de KPIs: span.uppercase (evita leyendas de Recharts con el mismo texto)
    const kpiTitle = (t: string) =>
      page.locator("span.text-xs.font-semibold.uppercase", { hasText: t }).first();
    await expect(kpiTitle("Ventas")).toBeVisible();
    await expect(kpiTitle("Ticket promedio")).toBeVisible();
    await expect(kpiTitle("Delivery")).toBeVisible();
    await expect(kpiTitle("Cocina en vivo")).toBeVisible();
    await expect(kpiTitle("En ruta")).toBeVisible();
  });

  test("muestra valores de KPIs del mock", async ({ authenticatedPage: page }) => {
    // Ventas = S/ 4,850.50 (mock) — se renderiza formateado
    await expect(page.getByText("S/ 4,850.50")).toBeVisible();
    // Ticket promedio
    await expect(page.getByText("S/ 115.50")).toBeVisible();
    // Delivery 35.7% + 15 pedidos
    await expect(page.getByText("35.7%")).toBeVisible();
    await expect(page.getByText("15 pedidos")).toBeVisible();
    // Cocina en vivo 6 pedidos activos
    await expect(page.locator("div.text-2xl.font-bold", { hasText: "6" }).first()).toBeVisible();
  });

  test("renderiza secciones de gráficos", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("Ventas por hora — Salón vs Delivery")).toBeVisible();
    await expect(page.getByText("Ventas por día de la semana")).toBeVisible();
    await expect(page.getByText("Canales de venta")).toBeVisible();
    await expect(page.getByText("Top platos vendidos")).toBeVisible();
    await expect(page.getByText("Métodos de pago")).toBeVisible();
  });

  test("sección delivery: embudo, zonas y ROAS", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("Pedidos por zona")).toBeVisible();
    await expect(page.getByText("Embudo de pedidos delivery")).toBeVisible();
    await expect(page.getByText("ROAS por campaña (marketing)")).toBeVisible();
    // GMV delivery del mock (S/ 1,780.50)
    await expect(page.getByText("S/ 1,780.50")).toBeVisible();
  });

  test("gráficos Recharts renderizados como SVG", async ({ authenticatedPage: page }) => {
    const svgCharts = page.locator(".recharts-surface");
    await expect(svgCharts.first()).toBeVisible({ timeout: 15000 });
    // Varios gráficos: por hora, por día, canales, pagos, embudo, ROAS
    expect(await svgCharts.count()).toBeGreaterThanOrEqual(3);
  });

  test("cambiar rango a Hoy refresca sin error", async ({ authenticatedPage: page }) => {
    // Click en el rango "Hoy"
    await page.getByRole("button", { name: "Hoy" }).click();
    // El panel debe seguir mostrando KPIs (sin error visible)
    const kpiVentas = page
      .locator("span.text-xs.font-semibold.uppercase", { hasText: "Ventas" })
      .first();
    await expect(kpiVentas).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=⚠️")).toHaveCount(0);
    // Volver a 7 días
    await page.getByRole("button", { name: "7 días" }).click();
    await expect(kpiVentas).toBeVisible();
  });
});
