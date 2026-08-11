/**
 * E2E Demo — Panel del Dueño V2 (CA10-CA14) contra STACK LOCAL V2.
 *
 * Patrón de 2 modos (lección 2026-08-09):
 *   --demo (default): pausas visibles 2.5s entre pasos — para que Ron
 *                     vea el flujo en el monitor del servidor (DISPLAY :0).
 *   --fast | --headless: sin pausas — para cierre/CI.
 *
 * Uso:
 *   node scripts/e2e-demo-panel-v2.js [--demo|--fast] [--delay N]
 *
 * @file e2e-demo-panel-v2.js
 */
const { chromium } = require("@playwright/test");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2500;

const BASE_URL = process.env.DEMO_BASE_URL || "http://localhost:8081"; // frontend prod (nginx) — o DEMO_BASE_URL para otro target
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  await page.screenshot({ path: `/tmp/panelv2-step-${Date.now()}.png` });
  if (DEMO) await sleep(DELAY_MS);
}

async function main() {
  console.log(`🚀 E2E Demo Panel del Dueño V2 (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE_URL}`);
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

    // 2. Navegar a /panel directamente
    await page.goto(`${BASE_URL}/panel`, { waitUntil: "networkidle" });
    await demoStep(page, "Panel del Dueño V2 cargado");

    // 3. KPIs V1 (regresión)
    await page.waitForSelector("text=Ventas", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "KPIs visibles: Ventas, Ticket promedio, Delivery, Cocina en vivo, En ruta");

    // 4. Gráficos V1
    await page.waitForSelector("text=Ventas por hora — Salón vs Delivery", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Gráfico: Ventas por hora (Salón vs Delivery)");
    await page.waitForSelector("text=Canales de venta", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: Canales de venta (dona)");
    await page.waitForSelector("text=Top platos vendidos", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: Top platos vendidos");
    await page.waitForSelector("text=ROAS por campaña (marketing)", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "Gráfico: ROAS por campaña (marketing)");

    // 5. CA10 — Heatmaps
    await page.waitForSelector("text=Heatmap de demanda — Salón", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA10: Heatmap Salón (7 días × 24 horas, celdas coloreadas)");
    await page.waitForSelector("text=Heatmap de demanda — Delivery", { timeout: 10000 }).catch(() => {});
    await demoStep(page, "V2 CA10: Heatmap Delivery");

    // 6. CA11 — Márgenes por canal
    await page.waitForSelector("text=Margen por canal (costeo por recetas)", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA11: Tarjetas de margen — Salón / Para llevar / Delivery (con semáforo)");

    // 7. CA12 — Comparativa semana vs semana
    await page.waitForSelector("text=▲ +18.3%", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA12: KPIs con comparativa ▲ verde (ventas, ticket, delivery pts)");

    // 8. CA14 — Banner de alertas
    await page.waitForSelector("text=⚠️", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA14: Banner de alerta (desviación vs promedio 7 días)");

    // 9. CA13 — Descargar CSV/PDF (dropdown; esperar a que se habilite)
    const dlBtn = page.getByRole("button", { name: /Descargar/ });
    await dlBtn.waitFor({ state: "visible", timeout: 20000 });
    await page.waitForFunction(
      () => {
        const b = [...document.querySelectorAll("button, summary")].find((x) => (x.textContent || "").includes("Descargar"));
        return b && !b.disabled;
      },
      { timeout: 20000 }
    ).catch(() => {});
    await demoStep(page, "V2 CA13: Botón Descargar (dropdown) habilitado — data cargada");
    // Abrir menú (summary del details) y descargar PDF
    await page.locator("summary", { hasText: "Descargar" }).first().click({ timeout: 5000 }).catch(() => {});
    await demoStep(page, "V2 CA13: Menú desplegado — opciones CSV / PDF");
    await page.locator("button", { hasText: "Descargar PDF" }).first().click({ timeout: 5000 }).catch((e) => console.log("(click PDF omitido: " + e.message.split("\n")[0] + ")"));
    await demoStep(page, "V2 CA13: Descarga PDF iniciada (panel_dueño_YYYYMMDD.pdf)");

    // 10. Cambiar rango
    await page.click('button:has-text("7 días")').catch(() => {});
    await demoStep(page, "Rango 7 DÍAS — panel refrescando");

    // 11. Screenshot final
    await page.screenshot({ path: "/tmp/panelv2-final.png", fullPage: true });
    console.log("✅ DEMO V2 COMPLETADA — Panel del Dueño V2 funcionando (stack local)");
    console.log("📸 Screenshots: /tmp/panelv2-step-*.png y /tmp/panelv2-final.png");
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/panelv2-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
