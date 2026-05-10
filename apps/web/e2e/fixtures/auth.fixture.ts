/**
 * Auth fixture — Login automático para tests que requieren sesión.
 *
 * Uso:
 *   test("algo", async ({ authenticatedPage }) => { ... });
 *
 * Estrategia: en lugar de llenar el formulario en cada test,
 * setea el refresh_token en sessionStorage y mockea la respuesta
 * de refresh para restaurar la sesión automáticamente.
 */

import { test as base, type Page } from "@playwright/test";
import { setupAllMocks } from "./mocks";

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    // Instalar todos los mocks de API
    await setupAllMocks(page);

    // Simular sesión existente vía refresh token en sessionStorage
    await page.goto("/");
    await page.evaluate(() => {
      sessionStorage.setItem("refresh_token", "ref-abc123-def456");
    });

    // Recargar para que AuthContext detecte el refresh token
    await page.reload();
    await page.waitForURL("/");

    await use(page);
  },
});

export { expect } from "@playwright/test";
