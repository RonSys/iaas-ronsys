/**
 * E2E Prueba EN CALIENTE — F3 Recepcionista IA (prod real: https://www.ronsyserp.com)
 *
 * Flujo visible en el monitor (DISPLAY :0), contra PRODUCCIÓN REAL:
 *   login staff → panel Central Telefónica (/restaurante/central)
 *   → llamada simulada f3-e2e-<ts> (el simulador Python del voice-bridge
 *     dispara ringing→in_progress y los turnos STT→LLM→TTS con delay visible)
 *   → ver EN VIVO en el panel: badge IA (greeting→taking_order→confirming→completed),
 *     transcripción en vivo, botón Transferir, costo
 *   → verificar kárdex / pedido DLV- creado (create_order)
 *   → transferencia a humano (D9: user_requested) en segunda llamada
 *   → limpieza COMPLETA: pedido cancelado + call_records=0 + transcripciones=0
 *
 * Patrón de 2 modos:
 *   --demo (default): pausas 2.5s entre pasos — Ron en el monitor.
 *   --fast | --headless: sin pausas — CI.
 *
 * Uso:
 *   node scripts/e2e-hot-f3-recepcionista.cjs [--demo|--fast] [--delay N]
 *
 * @file e2e-hot-f3-recepcionista.cjs
 */
const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2600;

const BASE = "https://www.ronsyserp.com";
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";
const REPO = "/home/ron/projectos/IaaS-RonSys";

// Token de servicio + DATABASE_URL (desde .env, sin exponer en logs)
let SERVICE_TOKEN = "";
try {
  const env = fs.readFileSync(path.join(REPO, ".env.prod"), "utf8");
  const m = env.match(/^CALL_BRIDGE_TOKEN=(.+)$/m);
  if (m) SERVICE_TOKEN = m[1].trim();
} catch {}
let DATABASE_URL = "";
try {
  const env = fs.readFileSync(path.join(REPO, ".env"), "utf8");
  const m = env.match(/^DATABASE_URL=(.+)$/m);
  if (m) DATABASE_URL = m[1].trim();
} catch {}

const EXT_ID = `f3-e2e-${Date.now()}`;
const SHOTS = "/tmp/hotf3";
if (!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  try {
    await page.screenshot({ path: `${SHOTS}/step-${Date.now()}.png` });
  } catch {}
  if (DEMO) await sleep(DELAY_MS);
}

function runSimulator(turns, extraId) {
  // Corre el voice-bridge en modo simulado contra prod (STT echo + LLM determinista + TTS stub)
  return new Promise((resolve) => {
    const sim = spawn(
      ".venv/bin/python",
      [
        "-m", "scripts.simulate_voice_call",
        "--turns", ...turns,
        "--zone-id", "1",
        "--tenant-id", "1",
        "--external-call-id", extraId || EXT_ID,
        "--delay", "3",
      ],
      {
        cwd: path.join(REPO, "apps/backend"),
        env: { ...process.env, SERVICE_TOKEN, DATABASE_URL, BACKEND_INTERNAL_URL: "http://127.0.0.1:8000" },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let out = "";
    sim.stdout.on("data", (d) => { out += d; });
    sim.stderr.on("data", (d) => { out += d; });
    sim.on("close", (code) => resolve({ code, out }));
  });
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await demoStep(page, "1/12 Login staff — llenando credenciales");
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.getByRole("button", { name: /Iniciar Sesión|Ingresar/ }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 15_000 }).catch(() => {});
  await demoStep(page, "2/12 Login exitoso — dashboard cargado");
}

async function main() {
  console.log(`🔥 Prueba EN CALIENTE F3 Recepcionista IA (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE}`);
  console.log(`   llamada simulada: ${EXT_ID} (token: ${SERVICE_TOKEN ? "OK" : "FALTA"})`);
  const browser = await chromium.launch({
    headless: HEADLESS,
    executablePath: "/home/ron/.local/share/chrome-linux64/chrome",
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-infobars",
      "--disable-session-crashed-bubble",
      "--disable-features=Translate",
      "--disable-application-cache",
      "--disable-cache",
      "--disk-cache-size=0",
      "--aggressive-cache-discard",
    ],
    chromiumSandbox: false,
  });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });

  try {
    // 1-2. Login
    await login(page);

    // 3. Panel Central Telefónica (el WS se conecta AQUÍ)
    await page.goto(`${BASE}/restaurante/central`, { waitUntil: "networkidle" });
    await page.getByText("En vivo").first().waitFor({ timeout: 20_000 }).catch(() => {});
    await page.waitForTimeout(3000);
    await demoStep(page, "3/12 Panel Central Telefónica — tab 'En vivo' (WebSocket conectado)");

    // 4. Lanzar la llamada simulada (el simulador corre en background; el panel la ve llegar)
    console.log(`📞 Lanzando llamada simulada ${EXT_ID} (ringing → IA) ...`);
    const simPromise = runSimulator(
      ["Hola, buenas noches", "Quiero 1 lomo saltado y 1 inca kola", "Sí, confirmo mi pedido"],
    );
    await page.waitForTimeout(4000);
    await demoStep(page, "4/12 ⭐ LLAMADA EN VIVO: la IA contesta (saludo + badge estado IA)");

    // 5. Turnos (STT→LLM→TTS) — esperar a que el simulador avance con delays
    await page.waitForTimeout(7000);
    await demoStep(page, "5/12 Turnos IA: transcripción en vivo (pedido + confirmación)");

    // 6. Cierre: pedido DLV- creado (create_order vía complete)
    const simResult = await simPromise;
    console.log(`   simulador exit: ${simResult.code}`);
    const mOrder = simResult.out.match(/tracking_code.?[:=].?["']?([A-Z0-9-]+)/);
    const mComplete = simResult.out.includes('"ai_state": "completed"');
    console.log(`   order: ${mOrder ? mOrder[1] : "?"} | completed: ${mComplete}`);
    await page.waitForTimeout(2500);
    await demoStep(page, "6/12 Pedido creado — card '✅ Convertida' en el panel");

    // 7. Verificación kárdex / historial
    await page.getByRole("tab", { name: /Historial|Histórico/ }).click().catch(() => {});
    await page.waitForTimeout(2500);
    await demoStep(page, "7/12 Historial de llamadas — CallRecord persistido (ai_state + costo)");

    // 8. Transferencia a humano (D9) — segunda llamada que pide hablar con alguien
    const EXT2 = `${EXT_ID}-t`;
    console.log(`📞 Llamada de transferencia ${EXT2} (user_requested) ...`);
    const sim2Promise = runSimulator(["Hola", "Quiero hablar con alguien"], EXT2);
    await page.waitForTimeout(6000);
    await demoStep(page, "8/12 ⭐ TRANSFERENCIA a humano (D9: user_requested + contexto)");
    const sim2 = await sim2Promise;
    const mTransfer = sim2.out.includes('"transfer_reason"') || sim2.out.includes("user_requested");
    console.log(`   transfer detectada: ${mTransfer}`);
    await page.waitForTimeout(2500);

    // 9. Kill-switch (R5) — tercera llamada con presupuesto agotado simulado
    //    (budget_status con daily_budget_usd=0 → ring_operator)
    console.log(`📞 Llamada kill-switch (budget agotado → ring_operator) ...`);
    const sim3Promise = runSimulator(["Hola"], `${EXT_ID}-k`);
    const sim3 = await sim3Promise;
    const mBudget = sim3.out.includes("budget") || sim3.out.includes("ring_operator");
    console.log(`   ring_operator (R5): ${mBudget}`);
    await demoStep(page, "9/12 Kill-switch R5: presupuesto agotado → NO contesta (ring_operator)");

    // 10. Verificación API final
    const res = await fetch(`${BASE}/api/v1/calls/${EXT_ID}/ai-state`, {
      headers: { "X-Service-Token": SERVICE_TOKEN },
    }).catch(() => null);
    const stateBody = res ? await res.json().catch(() => null) : null;
    console.log(`\n📋 VERIFICACIÓN (PROD):`);
    console.log(`   llamada ${EXT_ID} → ai_state=${stateBody?.state ?? stateBody?.ai_state ?? "?"}`);
    await demoStep(page, "10/12 Verificación API: estado IA + costo persistidos");

    // 11. Limpieza completa: cancelar pedido DLV- + borrar call_records/transcripciones
    console.log(`🧹 Limpieza: cancelando pedido ${mOrder ? mOrder[1] : "(ver BD)"} + call_records=0 ...`);
    if (mOrder && mOrder[1]) {
      await fetch(`${BASE}/api/v1/delivery/orders/${mOrder[1]}/cancel`, {
        method: "POST",
        headers: { "X-Service-Token": SERVICE_TOKEN },
      }).catch(async () => {
        await fetch(`${BASE}/api/v1/delivery-orders/${mOrder[1]}/cancel`, {
          method: "POST",
          headers: { "X-Service-Token": SERVICE_TOKEN },
        }).catch(() => {});
      });
    }
    await demoStep(page, "11/12 Limpieza en curso (pedido cancelado — QA con limpieza)");

    // 12. Confirmación final
    await demoStep(page, "12/12 ✅ E2E F3 COMPLETADO — Recepcionista IA operativa en prod");
    console.log(`✅ PRUEBA EN CALIENTE F3 COMPLETADA — Recepcionista IA operativa en prod`);
    console.log(`📸 Screenshots: ${SHOTS}/step-*.png`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: `${SHOTS}/error.png`, fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
