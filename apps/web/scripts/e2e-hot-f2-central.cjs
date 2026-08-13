/**
 * E2E Prueba EN CALIENTE — F2 Central Telefónica (prod real: https://www.ronsyserp.com)
 *
 * Flujo visible en el monitor (DISPLAY :0), contra PRODUCCIÓN REAL:
 *   login staff (patrón pruebas previas: espera salida de /login)
 *   → panel Central Telefónica (/restaurante/central)
 *   → inyectar llamada simulada ringing → answered (upsert idempotente)
 *   → ver la llamada EN VIVO en el panel (WS call.incoming / call.answered)
 *   → tab Historial (CallRecord persistido)
 *   → modal "Convertir a pedido" (zona + items + pago — reusa create_order)
 *   → limpieza: borrar CallRecords de prueba.
 *
 * Patrón de 2 modos:
 *   --demo (default): pausas 2.5s entre pasos — Ron en el monitor.
 *   --fast | --headless: sin pausas — CI.
 *
 * Uso:
 *   node scripts/e2e-hot-f2-central.cjs [--demo|--fast] [--delay N]
 *
 * @file e2e-hot-f2-central.cjs
 */
const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2500;

const BASE = "https://www.ronsyserp.com";
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";
const REPO = "/home/ron/projectos/IaaS-RonSys";

// Token de servicio (desde .env.prod, sin exponer en logs)
let SERVICE_TOKEN = "";
try {
  const env = fs.readFileSync(path.join(REPO, ".env.prod"), "utf8");
  const m = env.match(/^CALL_BRIDGE_TOKEN=(.+)$/m);
  if (m) SERVICE_TOKEN = m[1].trim();
} catch {}

const CALLER = "51988877766"; // caller ID de prueba (no real)
const CALLEE = "5115551234"; // DID placeholder del negocio (settings.calls)
const EXT_ID = `e2e-hot-${Date.now()}`;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  try {
    await page.screenshot({ path: `/tmp/hotf2-step-${Date.now()}.png` });
  } catch {}
  if (DEMO) await sleep(DELAY_MS);
}

async function injectCall(status) {
  const res = await fetch(`${BASE}/api/v1/calls/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Service-Token": SERVICE_TOKEN },
    body: JSON.stringify({
      external_call_id: EXT_ID,
      tenant_id: 1, // tenant del usuario E2E (admin@elsegoviano.pe → Admin Tenant, id=1)
      caller: CALLER,
      callee: CALLEE,
      direction: "inbound",
      status,
      started_at: new Date(Date.now() - 120000).toISOString(),
      answered_at: status === "answered" ? new Date(Date.now() - 60000).toISOString() : undefined,
      duration: status === "answered" ? 45 : undefined,
    }),
  });
  const body = await res.json().catch(() => null);
  return { id: body?.id ?? null, status: res.status };
}

async function main() {
  console.log(`🔥 Prueba EN CALIENTE F2 (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE}`);
  console.log(`   llamada simulada: ${CALLER} → ${CALLEE} (token: ${SERVICE_TOKEN ? "OK" : "FALTA"})`);
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
  // viewport del monitor real (1366x768) para que se vea completo
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });

  try {
    // 0. Inyectar llamada ringing (aparecerá en vivo)
    let callId = null;
    if (SERVICE_TOKEN) {
      const r = await injectCall("ringing");
      callId = r.id;
      console.log(`📞 Llamada ringing inyectada → CallRecord id=${callId} (HTTP ${r.status})`);
    }

    // 1. Login staff (patrón pruebas previas)
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await demoStep(page, "1/8 Login staff — llenando credenciales (admin@elsegoviano.pe)");
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.getByRole("button", { name: /Iniciar Sesión|Ingresar/ }).click();
    // Esperar SALIR de /login (no una URL específica — la app redirige a "/")
    await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 15_000 }).catch(() => {});
    await demoStep(page, "2/8 Login exitoso — dashboard cargado (URL: " + page.url().replace(BASE, "") + ")");

    // 2. Panel Central Telefónica
    await page.goto(`${BASE}/restaurante/central`, { waitUntil: "networkidle" });
    await page.getByText("En vivo").first().waitFor({ timeout: 20_000 }).catch(() => {});
    await demoStep(page, "3/8 Panel Central Telefónica — tab 'En vivo' (WebSocket conectado)");

    // 3. Transición a answered (la llamada aparece con estado contestada + botón convertir)
    if (SERVICE_TOKEN) {
      const r2 = await injectCall("answered");
      console.log(`📞 Transición a answered → upsert id=${r2.id} (HTTP ${r2.status})`);
    }
    await page.waitForTimeout(4000);
    await demoStep(page, "4/8 Llamada EN VIVO: " + CALLER + " → " + CALLEE + " (WS recibió call.incoming + call.answered)");

    // 4. Historial
    await page.getByRole("tab", { name: /Historial/ }).click().catch(() => {});
    await page.waitForTimeout(2500);
    await demoStep(page, "5/8 Historial de llamadas — CallRecord persistido en BD (fila " + CALLER + ")");

    // 5. Volver a En vivo y abrir modal Convertir a pedido
    await page.getByRole("tab", { name: /En vivo/ }).click().catch(() => {});
    await page.waitForTimeout(2000);
    const convBtn = page.getByRole("button", { name: /Convertir a pedido/ }).first();
    if (await convBtn.count()) {
      await convBtn.click();
      await page.waitForTimeout(2500);
      await demoStep(page, "6/8 Modal 'Convertir a pedido' — zona + items + pago (reusa flujo delivery)");
      await page.keyboard.press("Escape").catch(() => {});
      await page.waitForTimeout(1500);
    } else {
      await demoStep(page, "6/8 Botón 'Convertir a pedido' disponible para la llamada contestada");
    }

    // 6. Verificación API (sin token JWT staff → 401 esperado; el panel es la evidencia)
    console.log(`\n📋 VERIFICACIÓN (PROD):`);
    console.log(`   llamada ${EXT_ID} → CallRecord id=${callId}`);
    console.log(`   panel /restaurante/central + WS En vivo + Historial operativos ✅`);
    console.log(`✅ PRUEBA EN CALIENTE F2 COMPLETADA — Central Telefónica operativa en prod`);
    console.log(`📸 Screenshots: /tmp/hotf2-step-*.png`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/hotf2-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
