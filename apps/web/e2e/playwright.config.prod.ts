import { defineConfig } from "@playwright/test";

/**
 * Playwright E2E — Config PRODUCCIÓN (Camino C: Trace Viewer + monitor).
 *
 * Ejecuta los specs de DELIVERY contra https://www.ronsyserp.com usando el
 * Chrome for Testing 151 del .35 (Playwright npm no soporta ubuntu26.04-x64,
 * por eso apuntamos el binario directo con launchOptions.executablePath).
 *
 * Ejecución:
 *   npm run test:e2e:prod                 # todos los delivery specs (prod)
 *   npx playwright test --config=e2e/playwright.config.prod.ts -g "menú"
 *   npm run test:e2e:prod:report          # reporte HTML servido para la .39
 *
 * Notas:
 *   - Sin webServer: los tests van contra prod real (no vite dev).
 *   - workers=1 + fullyParallel=false: evita el rate limit de login (5/min)
 *     y el choque de pedidos de prueba en el checkout.
 *   - chromiumSandbox:false: requerido por apparmor userns=1 en Ubuntu 26.04.
 *   - trace/video/screenshot ON: Ron revisa flujos completos en Trace Viewer.
 */
export default defineConfig({
  // El config vive en e2e/ → testDir relativo al archivo
  testDir: ".",
  timeout: 45_000,
  expect: { timeout: 15_000 },
  retries: 0,
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["html", { outputFolder: "playwright-report-prod", open: "never" }],
    ["list"],
  ],
  use: {
    baseURL: "https://www.ronsyserp.com",
    headless: true,
    screenshot: "on",
    video: "on",
    trace: "on",
    launchOptions: {
      // Chrome for Testing 151 (Playwright no soporta el OS para bajar el suyo)
      executablePath: "/home/ron/.local/share/chrome-linux64/chrome",
    },
    chromiumSandbox: false,
  },
  projects: [
    {
      name: "delivery-staff",
      testMatch: /delivery-staff\.spec\.ts/,
    },
    {
      name: "delivery-landing",
      testMatch: /delivery-landing\.spec\.ts/,
    },
  ],
});
