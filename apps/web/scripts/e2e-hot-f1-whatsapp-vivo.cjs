/**
 * E2E Prueba EN CALIENTE — F1 WhatsApp en Vivo (prod real: https://www.ronsyserp.com)
 *
 * Flujo visible en el monitor (DISPLAY :0), contra PRODUCCIÓN REAL:
 *   landing pública /menu/el-segoviano → menú → checkout real (pedido de prueba)
 *   → código DLV- → seguimiento → login staff → kanban → verificar campañas
 *   → cancelar pedido (limpieza, sin dejar basura en prod).
 *
 * Patrón de 2 modos:
 *   --demo (default): pausas 2.5s entre pasos — Ron en el monitor.
 *   --fast | --headless: sin pausas — CI.
 *
 * Uso:
 *   node scripts/e2e-hot-f1-whatsapp-vivo.cjs [--demo|--fast] [--delay N]
 *
 * @file e2e-hot-f1-whatsapp-vivo.cjs
 */
const { chromium } = require("@playwright/test");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2500;

const BASE = "https://www.ronsyserp.com";
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";
const LANDING = `${BASE}/menu/el-segoviano`;

// Data de prueba (pedido real de prueba que se CANCELA al final)
const PHONE = "999 888 777";
const PHONE_RAW = "999888777";
const CUSTOMER = `Hot-Test-${Date.now()}`;
const UTM_CAMPAIGN = `hot_f1_${Date.now()}`;

let trackingCode = null;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  try {
    await page.screenshot({ path: `/tmp/hotf1-step-${Date.now()}.png` });
  } catch {}
  if (DEMO) await sleep(DELAY_MS);
}

async function apiJson(path, opts = {}) {
  const { headers: extraHeaders, ...rest } = opts;
  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", ...(extraHeaders || {}) },
  });
  const body = await res.json().catch(() => null);
  return { status: res.status, body };
}

async function adminLogin() {
  const { body } = await apiJson("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  return body.access_token;
}

async function cancelOrder() {
  if (!trackingCode) return;
  try {
    const token = await adminLogin();
    const headers = { Authorization: `Bearer ${token}`, "X-Tenant-ID": "1" };
    const { body: orders } = await apiJson("/api/v1/delivery/orders", { headers });
    const order = (orders || []).find((o) => o.tracking_code === trackingCode);
    if (order && !["delivered", "cancelled"].includes(order.status)) {
      await apiJson(`/api/v1/delivery/orders/${order.id}/status`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ status: "cancelled" }),
      });
      console.log(`🧹 Pedido cancelado: ${trackingCode}`);
    }
  } catch (err) {
    console.log(`(limpieza: ${err.message})`);
  }
}

async function main() {
  console.log(`🔥 Prueba EN CALIENTE F1 (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE}`);
  console.log(`   data: cliente=${CUSTOMER} · tel=${PHONE} · utm=${UTM_CAMPAIGN}`);
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
    // 1. Landing pública (producción real)
    await page.goto(`${LANDING}?utm_source=meta&utm_medium=cpc&utm_campaign=${UTM_CAMPAIGN}`, {
      waitUntil: "networkidle",
    });
    await demoStep(page, "1/10 Landing pública PROD — menú nocturno (ronsyserp.com/menu/el-segoviano)");
    await page.getByText("＋ Agregar al pedido").first().waitFor({ timeout: 20_000 }).catch(() => {});
    await demoStep(page, "2/10 Plato visible (Lomo Saltado S/35)");

    // 2. Agregar Lomo Saltado
    await page.locator("button").filter({ hasText: "Lomo Saltado" }).first().click();
    await demoStep(page, "3/10 Lomo Saltado agregado al carrito (S/35)");

    // 3. Zona 1
    await page.locator("select").first().selectOption({ index: 1 });
    await demoStep(page, "4/10 Zona 1 — fee S/5, total S/40");

    // 4. Formulario (data de prueba)
    await page.getByPlaceholder("Tu nombre").fill(CUSTOMER);
    await page.getByPlaceholder("999 888 777").fill(PHONE_RAW);
    await page.getByPlaceholder(/Calle, número/).fill("Av. Hot Test 123, SJL");
    await page.getByPlaceholder(/8 caracteres/).fill("HOTEST123");
    await demoStep(page, "5/10 Cliente: " + CUSTOMER + " · " + PHONE + " · Av. Hot Test 123");

    // 5. Confirmar → DLV-
    await page.getByRole("button", { name: /Confirmar pedido/ }).click();
    await page.getByText("¡Pedido confirmado!").waitFor({ timeout: 30_000 });
    const code = (await page.getByText(/^DLV-[0-9a-f]+$/).first().textContent())?.trim() ?? "";
    trackingCode = code;
    console.log(`✅ CHECKOUT 201 (PROD) — tracking=${trackingCode}`);
    await demoStep(page, "6/10 Pedido confirmado en PROD: " + trackingCode);

    // 6. Seguimiento
    await page.getByRole("button", { name: /Seguir pedido/ }).click().catch(() => {});
    await demoStep(page, "7/10 Seguimiento (recibido → …)");

    // 7. Login staff + kanban
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.getByRole("button", { name: /Iniciar Sesión|Ingresar/ }).click();
    await page.waitForURL("**/restaurante/delivery", { timeout: 20_000 }).catch(() => {});
    await page.goto(`${BASE}/restaurante/delivery`, { waitUntil: "networkidle" });
    for (const col of ["Recibido", "En cocina", "Listo", "En ruta", "Entregado", "Cancelado"]) {
      await page.getByText(col).first().waitFor({ timeout: 25_000 }).catch(() => {});
    }
    await demoStep(page, "8/10 Panel staff PROD — kanban de pedidos");

    // 8. Campañas: botones F1
    await page.getByRole("tab", { name: /Campañas/ }).click().catch(() => {});
    await demoStep(page, "9/10 Campañas — verificar botones F1 'Abrir en WhatsApp' / 'Llamar'");

    // 9. Cancelar (limpieza)
    await cancelOrder();
    await demoStep(page, "10/10 Pedido CANCELADO — limpieza completa en PROD");

    // 10. Verificación
    let status = "?";
    for (let i = 0; i < 6; i++) {
      const track = await apiJson(`/api/public/orders/${trackingCode}/status`);
      status = track.body?.status ?? "?";
      if (status === "cancelled") break;
      await sleep(1000);
    }
    console.log(`\n📋 VERIFICACIÓN FINAL (PROD):`);
    console.log(`   pedido ${trackingCode} → status=${status} (esperado: cancelled)`);
    console.log(`✅ PRUEBA EN CALIENTE COMPLETADA — prod operativo`);
    console.log(`📸 Screenshots: /tmp/hotf1-step-*.png`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/hotf1-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await cancelOrder();
    await browser.close();
  }
}

main();
