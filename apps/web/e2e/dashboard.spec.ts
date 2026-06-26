/**
 * E2E: Dashboard — KPIs, gráficos, secciones.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Dashboard", () => {
  test("carga KPIs después del login", async ({ authenticatedPage: page }) => {
    await expect(page.locator("h2")).toContainText("Panel de Control");
  });

  test("muestra tarjetas KPI con valores", async ({ authenticatedPage: page }) => {
    // KPICards deben renderizarse con valores
    await expect(page.getByText("💰")).toBeVisible();
    await expect(page.getByText("📈")).toBeVisible();
    await expect(page.getByText("💎")).toBeVisible();
    await expect(page.getByText("🏦")).toBeVisible();
  });

  test("sección de ratios con semáforo visible", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("🚦 Ratios Financieros")).toBeVisible();
    // Debe haber al menos 3 ratios con valores
    const ratioCards = page.locator(".card .grid > div");
    await expect(ratioCards.first()).toBeVisible();
  });

  test("gráfico de flujo de caja visible", async ({ authenticatedPage: page }) => {
    // Los gráficos Recharts se renderizan como SVG
    const svgCharts = page.locator(".recharts-surface");
    await expect(svgCharts.first()).toBeVisible({ timeout: 15000 });
  });

  test("sección BCSS muestra totales", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("🧾 Balance de Comprobación (BCSS)")).toBeVisible();
    await expect(page.getByText("✅ Sí")).toBeVisible(); // is_balanced
  });
});
