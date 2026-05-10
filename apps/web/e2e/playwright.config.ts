import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config — IaaS-RonSys Web.
 *
 * Ejecución:
 *   npx playwright test              # Todos los tests
 *   npx playwright test --ui         # UI mode
 *   npx playwright test login.spec   # Solo un archivo
 *   npx playwright show-report       # Reporte HTML
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 10000 },
  retries: 1,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["list"],
  ],
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev -- --host 0.0.0.0",
    port: 5173,
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },
});
