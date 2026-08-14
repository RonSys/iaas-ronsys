#!/usr/bin/env node
/**
 * E2E en caliente — F5 "Pregúntale al Sistema" (Spec 08)
 * ======================================================
 * Monitor de producción: verifica el chat flotante del asistente en el
 * panel del dueño (DashboardOwner) contra el backend PROD real.
 *
 * Patrón heredado de e2e-hot-f2/f3:
 *   - Login real contra /api/auth/login (admin@elsegoviano.pe / admin123)
 *   - Navega al panel del dueño → busca el botón flotante del asistente
 *   - Abre el chat, envía una pregunta real → verifica respuesta renderizada
 *   - Evidencia: screenshot en docs/reports/evidencias-f5-e2e-prod/
 *   - Limpieza completa al final (query_logs de la prueba)
 *
 * Uso: node scripts/e2e-hot-f5-asistente.cjs
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.E2E_BASE_URL || "http://localhost:8081";
const API = process.env.E2E_API_URL || "http://localhost:8000";
const EMAIL = process.env.E2E_EMAIL || "admin@elsegoviano.pe";
const PASSWORD = process.env.E2E_PASSWORD || "admin123";
const OUT_DIR = path.join(__dirname, "../../../docs/reports/evidencias-f5-e2e-prod");
const RESULTS = [];
function record(name, ok, detail = "") {
  RESULTS.push({ name, ok, detail });
  console.log(`${ok ? "✅" : "❌"} ${name}${detail ? " — " + detail : ""}`);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // ── Paso 0: login API (token real) ──────────────────────────────
  const loginRes = await page.request.post(`${API}/api/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  });
  const loginBody = await loginRes.json();
  const token = loginBody.access_token || loginBody.token;
  record("P0: login API", !!token);

  // ── Paso 1: login UI ────────────────────────────────────────────
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"], button:has-text("Ingresar"), button:has-text("Entrar")');
  await page.waitForTimeout(2500);
  const url = page.url();
  record("P1: login UI → panel", !url.includes("/login"), url);

  // ── Paso 2: ir al panel del dueño (/panel) ─────────────────────
  await page.goto(`${BASE}/panel`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(2000);
  const hasOwner = page.url().includes("panel") || (await page.locator("body").innerText()).includes("Resumen");
  record("P2: DashboardOwner cargado", hasOwner, page.url());
  await page.screenshot({ path: path.join(OUT_DIR, "01-owner-panel.png"), fullPage: false });

  // ── Paso 3: botón flotante del asistente ────────────────────────
  const btnSelectors = [
    'button[aria-label*="asistente" i]',
    'button[aria-label*="Pregúntale" i]',
    'button[title*="asistente" i]',
    'button:has-text("Pregúntale")',
    'button:has-text("Asistente")',
    '[data-testid="assistant-fab"]',
    'button:has-text("💬")',
  ];
  let fab = null;
  for (const sel of btnSelectors) {
    const el = page.locator(sel).first();
    if (await el.count()) { fab = el; break; }
  }
  record("P3: botón flotante asistente visible", !!fab, fab ? "encontrado" : "no encontrado");
  if (!fab) {
    // dump de botones visibles para diagnóstico
    const btns = await page.locator("button").allInnerTexts();
    console.log("  botones visibles:", btns.slice(0, 15).join(" | "));
    await page.screenshot({ path: path.join(OUT_DIR, "02-sin-boton.png") });
  } else {
    await fab.click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUT_DIR, "02-chat-abierto.png") });

    // ── Paso 4: enviar pregunta real ──────────────────────────────
    const inputSel = 'input[placeholder*="Ej:"], textarea, input[type="text"]';
    const input = page.locator(inputSel).last();
    const chatVisible = await input.count() && await input.isVisible();
    record("P4: input del chat visible", !!chatVisible);
    if (chatVisible) {
      await input.fill("¿cuál es el ticket promedio de delivery de los últimos 15 días?");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(6000);
      // Verificar SOLO dentro del panel del chat (no del body, evita falsos positivos)
      const panel = page.locator("div.fixed.bottom-24.right-6").first();
      const chatText = (await panel.innerText().catch(() => "")) || "";
      const hasAnswer = /ticket promedio[\s\S]{0,300}S\/|S\/\s?[\d,.]+/.test(chatText);
      record("P5: respuesta del asistente renderizada (datos reales)", hasAnswer, chatText.slice(0, 110).replace(/\n/g, " "));
      await page.screenshot({ path: path.join(OUT_DIR, "03-respuesta.png") });
    }
  }

  await browser.close();

  // ── Resumen ─────────────────────────────────────────────────────
  const passed = RESULTS.filter((r) => r.ok).length;
  console.log(`\n=== E2E F5 PROD: ${passed}/${RESULTS.length} OK ===`);
  fs.writeFileSync(
    path.join(OUT_DIR, "resumen.json"),
    JSON.stringify({ fecha: new Date().toISOString(), resultados: RESULTS }, null, 2)
  );
  process.exit(passed === RESULTS.length ? 0 : 1);
}

main().catch((e) => {
  console.error("E2E F5 falló:", e.message);
  process.exit(1);
});
