/**
 * E2E: Settings — Paleta de colores, presets, información empresa.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Settings", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/settings");
    await page.waitForSelector("h2");
  });

  test("paleta de colores visible con presets", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("🎨 Paleta de Colores")).toBeVisible({ timeout: 10000 });

    // Presets visibles
    await expect(page.getByText("Azul Marino")).toBeVisible();
    await expect(page.getByText("Verde Bosque")).toBeVisible();
    await expect(page.getByText("Rojizo Cálido")).toBeVisible();
    await expect(page.getByText("Púrpura")).toBeVisible();
  });

  test("color pickers existen para todos los colores", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("Azul Marino")).toBeVisible({ timeout: 10000 });

    // Debe haber 10 inputs type="color"
    const colorInputs = page.locator('input[type="color"]');
    await expect(colorInputs).toHaveCount(10);
  });

  test("vista previa de colores visible", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("👁️ Vista Previa")).toBeVisible({ timeout: 10000 });

    // Labels de los colores en preview
    await expect(page.getByText("Primario")).toBeVisible();
    await expect(page.getByText("Acento")).toBeVisible();
    await expect(page.getByText("Éxito")).toBeVisible();
    await expect(page.getByText("Error")).toBeVisible();
  });

  test("información de empresa visible", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("🏢 Información de la Empresa")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("PEN")).toBeVisible();
    await expect(page.getByText("America/Lima")).toBeVisible();
  });
});
