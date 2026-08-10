/**
 * Diagnóstico — Panel V2 contra stack local (sin pausas, headless).
 * Imprime estado real: data cargada, errores, estado del botón CSV, console errors.
 */
const { chromium } = require("@playwright/test");

const BASE_URL = "http://localhost:5173";
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/home/ron/.local/share/chrome-linux64/chrome",
    args: ["--no-first-run", "--no-default-browser-check", "--disable-infobars"],
    chromiumSandbox: false,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  page.on("pageerror", (err) => consoleErrors.push("PAGEERROR: " + err.message));

  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"], button:has-text("Ingresar")');
    await page.waitForURL("**/panel**", { timeout: 15000 }).catch(() => {});
    await page.goto(`${BASE_URL}/panel`, { waitUntil: "networkidle" });
    await page.waitForTimeout(4000);

    const state = await page.evaluate(() => {
      const btn = [...document.querySelectorAll("button")].find(b => (b.textContent || "").includes("Descargar CSV"));
      const bodyText = document.body.innerText;
      return {
        buttonDisabled: btn ? btn.disabled : "NO ENCONTRADO",
        hasVentas: bodyText.includes("Ventas"),
        hasSkeleton: bodyText.includes("Skeleton") || !!document.querySelector(".animate-pulse"),
        hasError: /⚠️/.test(bodyText) || bodyText.includes("Error al cargar"),
        hasHeatmap: bodyText.includes("Heatmap de demanda"),
        hasMargins: bodyText.includes("Margen por canal"),
        sample: bodyText.slice(0, 600),
      };
    });
    console.log("=== ESTADO PANEL ===");
    console.log(JSON.stringify(state, null, 2));
    console.log("=== CONSOLE ERRORS ===");
    console.log(consoleErrors.slice(0, 10).join("\n") || "ninguno");
  } catch (err) {
    console.error("ERROR:", err.message);
  } finally {
    await browser.close();
  }
})();
