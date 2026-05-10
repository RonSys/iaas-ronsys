/**
 * E2E: Simulador interactivo — Sliders, resultados, escenarios.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Simulador", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/simulador");
    await page.waitForSelector("h2");
  });

  test("sliders visibles y con valores default", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("💵 Precio promedio por plato")).toBeVisible();
    await expect(page.getByText("🍽️ Platos vendidos por día")).toBeVisible();
    await expect(page.getByText("🥘 Costo de insumos")).toBeVisible();
    await expect(page.getByText("🏠 Alquiler mensual")).toBeVisible();
    await expect(page.getByText("👥 Sueldos totales")).toBeVisible();
  });

  test("botón Simular Ahora visible", async ({ authenticatedPage: page }) => {
    await expect(page.getByRole("button", { name: /Simular Ahora/ })).toBeVisible();
  });

  test("resultados se actualizan al hacer clic en Simular", async ({ authenticatedPage: page }) => {
    // Hacer clic en el botón manual
    await page.getByRole("button", { name: /Simular Ahora/ }).click();

    // Debe aparecer la sección de resultados
    await expect(page.getByText("📊 Resultados en Vivo")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Ventas mensuales")).toBeVisible();
    await expect(page.getByText("Utilidad Neta")).toBeVisible();
  });

  test("botón Guardar Escenario agrega a la comparativa", async ({ authenticatedPage: page }) => {
    // Ejecutar simulación
    await page.getByRole("button", { name: /Simular Ahora/ }).click();
    await expect(page.getByText("📊 Resultados en Vivo")).toBeVisible({ timeout: 15000 });

    // Guardar escenario
    await page.getByRole("button", { name: /Guardar Escenario/ }).click();

    // Debe aparecer la tabla de comparativa
    await expect(page.getByText("🔍 Comparativa de Escenarios")).toBeVisible();
    await expect(page.getByText("Realista")).toBeVisible();
  });

  test("tabla de comparativa muestra columnas correctas", async ({ authenticatedPage: page }) => {
    await page.getByRole("button", { name: /Simular Ahora/ }).click();
    await expect(page.getByText("📊 Resultados en Vivo")).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: /Guardar Escenario/ }).click();

    // Verificar columnas de la tabla
    await expect(page.getByText("Precio por plato")).toBeVisible();
    await expect(page.getByText("Ventas / mes")).toBeVisible();
    await expect(page.getByText("Utilidad Neta")).toBeVisible();
    await expect(page.getByText("Payback")).toBeVisible();
    await expect(page.getByText("VAN")).toBeVisible();
  });
});
