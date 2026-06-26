/**
 * E2E: Kárdex — Inventario, productos, movimientos entrada/salida.
 */
import { test, expect } from "./fixtures/auth.fixture";

test.describe("Kárdex", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto("/kardex");
    await page.waitForSelector("h2");
  });

  test("lista de productos visible", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("📦 Kárdex — Inventario")).toBeVisible();
    // Deben aparecer los productos mock
    await expect(page.getByText("Arroz")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Pollo")).toBeVisible();
  });

  test("seleccionar producto muestra movimientos", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("Arroz")).toBeVisible({ timeout: 10000 });
    await page.getByText("Arroz").click();

    // Debe aparecer la tabla de movimientos
    await expect(page.getByText("📋 Movimientos:")).toBeVisible();
    await expect(page.getByText("Compra inicial")).toBeVisible({ timeout: 10000 });
  });

  test("modal de nuevo producto se abre y cierra", async ({ authenticatedPage: page }) => {
    await page.getByRole("button", { name: "+ Producto" }).click();

    await expect(page.getByText("📦 Nuevo Producto")).toBeVisible();
    await expect(page.getByText("Crear Producto")).toBeVisible();

    // Cerrar con Cancelar
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByText("📦 Nuevo Producto")).not.toBeVisible();
  });

  test("botones entrada/salida deshabilitados sin producto seleccionado", async ({ authenticatedPage: page }) => {
    const entryBtn = page.getByRole("button", { name: "+ Entrada" });
    const exitBtn = page.getByRole("button", { name: "- Salida" });

    await expect(entryBtn).toBeDisabled();
    await expect(exitBtn).toBeDisabled();
  });

  test("registrar entrada de inventario", async ({ authenticatedPage: page }) => {
    // Seleccionar producto primero
    await expect(page.getByText("Arroz")).toBeVisible({ timeout: 10000 });
    await page.getByText("Arroz").click();

    // Botón entrada ahora debería estar habilitado
    const entryBtn = page.getByRole("button", { name: "+ Entrada" });
    await expect(entryBtn).toBeEnabled();
    await entryBtn.click();

    // Modal de entrada visible
    await expect(page.getByText(/Registrar Entrada/)).toBeVisible();

    // Llenar y enviar
    await page.locator("input[type=number]").first().fill("10");
    await page.locator("input[type=number]").nth(1).fill("5");
    await page.getByRole("button", { name: "Registrar Entrada" }).click();

    // Modal se cierra después del registro
    await expect(page.getByText(/Registrar Entrada/)).not.toBeVisible({ timeout: 5000 });
  });

  test("registrar salida de inventario", async ({ authenticatedPage: page }) => {
    await expect(page.getByText("Arroz")).toBeVisible({ timeout: 10000 });
    await page.getByText("Arroz").click();

    const exitBtn = page.getByRole("button", { name: "- Salida" });
    await expect(exitBtn).toBeEnabled();
    await exitBtn.click();

    await expect(page.getByText(/Registrar Salida/)).toBeVisible();

    await page.locator("input[type=number]").first().fill("5");
    await page.getByRole("button", { name: "Registrar Salida" }).click();

    await expect(page.getByText(/Registrar Salida/)).not.toBeVisible({ timeout: 5000 });
  });
});
