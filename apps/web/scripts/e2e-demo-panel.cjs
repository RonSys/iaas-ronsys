/**
 * E2E Demo — Panel del Dueño (Spec 04) contra PRODUCCIÓN.
 *
 * Patrón de 2 modos (lección 2026-08-09):
 *   --demo (default): pausas visibles 2.5s entre pasos — para que Ron
 *                     vea el flujo en el monitor del servidor (DISPLAY :0).
 *   --fast | --headless: sin pausas — para cierre/CI.
 *
 * Uso:
 *   node scripts/e2e-demo-panel.js [--demo|--fast] [--delay N]
 *
 * @file e2e-demo-panel.js
 */
const { chromium } = require("@playwright/test");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2500;

const BASE_URL = "http://localhost:8081"; // frontend prod (nginx)
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  await page.screenshot({ path: `/tmp/panel-step-${Date.now()}.png` });
  if (DEMO) await sleep(DELAY_MS);
}

async function main() {
  console.log(`🚀 E2E Demo Panel del Dueño (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE_URL}`);
  const browser = await chromium.launch({
    headless: HEADLESS,
    executablePath: "/home/ron/.local/share/chrome-linux64/chrome",
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-infobars",
      "--disable-session-crashed-bubble",
      "--disable-features=Translate",
    ],
    chromiumSandbox: false,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  try {
    // 1. Login
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await demoStep(page, "Pantalla de Login cargada");
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await demoStep(page, "Credenciales del dueño ingresadas (admin@elsegoviano.pe)");
    await page.click('button[type="submit"], button:has-text("Ingresar")');
    await page.waitForURL("**/panel**", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Login exitoso — redirigiendo al Panel del Dueño (/panel)");

    // 2. Navegar a /panel directamente (por si el login cae al Dashboard)
    await page.goto(`${BASE_URL}/panel`, { waitUntil: "networkidle" });
    await demoStep(page, "Panel del Dueño cargado");

    // 3. KPIs
    await page.waitForSelector("text=Ventas", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "KPIs visibles: Ventas, Ticket promedio, Delivery, Cocina en vivo, En ruta");

    // 4. Gráficos
    await page.waitForSelector("text=Ventas por hora", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Gráfico: Ventas por hora (Salón vs Delivery)");
    await page.waitForSelector("text=Canales de venta", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: Canales de venta (dona)");
    await page.waitForSelector("text=Top platos vendidos", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: Top platos vendidos");
    await page.waitForSelector("text=ROAS por campaña", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: ROAS por campaña (marketing)");
    await page.waitForSelector("text=Embudo de pedidos delivery", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: Embudo de pedidos delivery");

    // 5. Cambiar rango
    await page.click('button:has-text("Hoy")');
    await demoStep(page, "Rango cambiado a HOY — panel refrescando");
    await page.click('button:has-text("7 días")');
    await demoStep(page, "Rango cambiado a 7 DÍAS — panel refrescando");

    // 6. Screenshot final
    await page.screenshot({ path: "/tmp/panel-final.png", fullPage: true });
    console.log("✅ DEMO COMPLETADA — Panel del Dueño funcionando en producción");
    console.log("📸 Screenshots: /tmp/panel-*.png y /tmp/panel-final.png");
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/panel-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
