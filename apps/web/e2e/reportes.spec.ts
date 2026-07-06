/**
 * E2E: Reportes — PYG, Balance, BCSS, Ratios con navegación por tabs.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Reportes", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/reportes");
    await page.waitForSelector("h2");
  });

  test("todos los tabs están visibles", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("📄 PYG")).toBeVisible();
    await expect(page.getByText("⚖️ Balance")).toBeVisible();
    await expect(page.getByText("🧾 BCSS")).toBeVisible();
    await expect(page.getByText("🚦 Ratios")).toBeVisible();
  });

  test("tab PYG muestra Estado de Resultados", async ({ authenticatedPage: page }) => {
    // El PYG se muestra por defecto
    await expect(page.getByText("Estado de Resultados")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Utilidad Bruta")).toBeVisible();
    await expect(page.getByText("EBITDA")).toBeVisible();
    await expect(page.getByText("UTILIDAD NETA")).toBeVisible();
  });

  test("tab Balance General muestra activo/pasivo/patrimonio", async ({ authenticatedPage: page }) => {
    await page.getByText("⚖️ Balance").click();

    await expect(page.getByText("ACTIVOS")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("PASIVO + PATRIMONIO")).toBeVisible();
    await expect(page.getByText("TOTAL ACTIVOS")).toBeVisible();
  });

  test("tab Ratios muestra indicadores con semáforo", async ({ authenticatedPage: page }) => {
    await page.getByText("🚦 Ratios").click();

    await expect(page.getByText("Ratios Financieros")).toBeVisible({ timeout: 10000 });
    // Debe haber filas con valores de ratios
    await expect(page.getByText("Liquidez Corriente")).toBeVisible();
    await expect(page.getByText("Margen Bruto")).toBeVisible();
    await expect(page.getByText("ROE")).toBeVisible();
  });
});
