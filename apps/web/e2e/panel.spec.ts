/**
 * E2E: Panel del Dueño (Spec 04) — KPIs, gráficos, rangos.
 *
 * Data: GET /api/v1/dashboard/owner?date_from=&date_to= (mockeado).
 * Contrato: src/types/dashboard.ts → OwnerDashboardResponse.
 */
import { test, expect } from "./fixtures/auth.fixture";
import { mockOwnerDashboard } from "./fixtures/mocks";

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
    // GMV delivery del mock (S/ 1,780.50). Se acota a la tarjeta GMV porque
    // V2 (CA11) renderiza el mismo importe en la tarjeta de márgenes del
    // canal Delivery (Ingresos) — getByText global sería ambiguo.
    const gmvCard = page.locator(".card", { hasText: "GMV delivery (entregados)" });
    await expect(gmvCard.getByText("S/ 1,780.50")).toBeVisible();
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
    // Sin banner de error. El ⚠️ amarillo del banner de alertas V2 (CA14) es
    // esperado; el banner de error se identifica por su clase text-red-300.
    await expect(page.locator("div.text-red-300")).toHaveCount(0);
    // Volver a 7 días
    await page.getByRole("button", { name: "7 días" }).click();
    await expect(kpiVentas).toBeVisible();
  });
});

// ─── V2 (CA10-CA14): heatmap, márgenes, comparativa ▲▼, alertas, export ──

test.describe("Panel del Dueño — V2 (CA10-CA14)", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/panel");
    await expect(page.locator("h2").first()).toContainText("Panel del Dueño", {
      timeout: 15000,
    });
  });

  test("heatmap hora×día visible en Salón y Delivery (CA10)", async ({
    authenticatedPage: page,
  }) => {
    await expect(page.getByText("Heatmap de demanda — Salón")).toBeVisible();
    await expect(page.getByText("Heatmap de demanda — Delivery")).toBeVisible();
    // Celdas coloreadas (con importe > 0): el title de la celda es
    // "Lun 12:00 — S/ 320.50"; las vacías son "S/ 0.00".
    const coloredCells = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("div[title]")].filter(
        (el) => el.title.includes("— S/") && !el.title.includes("S/ 0.00"),
      ).length,
    );
    expect(coloredCells).toBeGreaterThanOrEqual(10);
  });

  test("tarjetas de margen por canal con % y nota de costeabilidad (CA11)", async ({
    authenticatedPage: page,
  }) => {
    const marginsCard = page.locator(".card", { hasText: "Margen por canal" });
    await expect(marginsCard.getByText("Margen por canal (costeo por recetas)")).toBeVisible();
    // 3 canales del mock: Salón 60.0%, Para llevar 50.0%, Delivery 50.0%
    await expect(marginsCard.getByText("Salón", { exact: true })).toBeVisible();
    await expect(marginsCard.getByText("Para llevar")).toBeVisible();
    await expect(marginsCard.getByText("Delivery")).toBeVisible();
    await expect(marginsCard.getByText("60.0%")).toBeVisible();
    await expect(marginsCard.getByText("50.0%")).toHaveCount(2);
    // Nota de costeabilidad (R2)
    await expect(
      marginsCard.getByText(/Margen calculado solo sobre ítems con receta/),
    ).toBeVisible();
  });

  test("KPIs muestran comparativa semana vs semana ▲ verde (CA12)", async ({
    authenticatedPage: page,
  }) => {
    // Mock: sales_total +18.3%, avg_ticket +7.0%, delivery +4.5 pts
    await expect(page.getByText("▲ +18.3%")).toBeVisible();
    await expect(page.getByText("▲ +7.0%")).toBeVisible();
    await expect(page.getByText("▲ +4.5 pts")).toBeVisible();
  });

  test("banner de alerta amarillo visible (CA14)", async ({
    authenticatedPage: page,
  }) => {
    const alertBanner = page.locator("div.text-yellow-300", {
      hasText: "Hoy Ventas -12% vs promedio últimos 7 días",
    });
    await expect(alertBanner).toBeVisible();
    await expect(alertBanner.getByText("⚠️")).toBeVisible();
  });

  test("dropdown: Descargar CSV dispara descarga del export (CA13)", async ({
    authenticatedPage: page,
  }) => {
    const exportReqPromise = page.waitForRequest((req) =>
      req.url().includes("/api/v1/dashboard/owner/export"),
    );
    const downloadPromise = page.waitForEvent("download");
    // Abrir el dropdown (CA13-b) y elegir CSV
    await page.getByRole("button", { name: /Descargar$/ }).click();
    await page.getByRole("button", { name: /Descargar CSV/ }).click();
    const exportReq = await exportReqPromise;
    const download = await downloadPromise;
    expect(exportReq.url()).toContain("format=csv");
    // filename con ñ vía RFC 5987 (Content-Disposition)
    expect(download.suggestedFilename()).toContain("panel_dueño");
    expect(download.suggestedFilename()).toMatch(/\.csv$/);
  });

  test("dropdown: Descargar PDF dispara descarga del export format=pdf (CA13-b)", async ({
    authenticatedPage: page,
  }) => {
    const exportReqPromise = page.waitForRequest((req) =>
      req.url().includes("/api/v1/dashboard/owner/export"),
    );
    const downloadPromise = page.waitForEvent("download");
    // Abrir el dropdown y elegir PDF
    await page.getByRole("button", { name: /Descargar$/ }).click();
    await page.getByRole("button", { name: /Descargar PDF/ }).click();
    const exportReq = await exportReqPromise;
    const download = await downloadPromise;
    expect(exportReq.url()).toContain("format=pdf");
    // filename con ñ vía RFC 5987, extensión .pdf
    expect(download.suggestedFilename()).toContain("panel_dueño");
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });
});

// Delta negativo: requiere mock con comparativa override ANTES de navegar
// (el beforeEach del describe ya habría disparado el fetch con el mock base).
test("KPI con delta negativo muestra ▼ roja (CA12)", async ({
  authenticatedPage: page,
}) => {
  await mockOwnerDashboard(page, {
    comparison: {
      current: { sales_total: 4850.5, orders_count: 42, avg_ticket: 115.5, delivery_pct: 35.7 },
      previous: { sales_total: 5118.0, orders_count: 44, avg_ticket: 113.8, delivery_pct: 33.0 },
      deltas: { sales_total_pct: -5.2, orders_count_pct: -4.5, avg_ticket_pct: 1.5, delivery_pct_delta: 2.7 },
    },
  });
  await page.goto("/panel");
  await expect(page.locator("h2").first()).toContainText("Panel del Dueño", {
    timeout: 15000,
  });
  await expect(page.getByText("▼ -5.2%")).toBeVisible();
});
