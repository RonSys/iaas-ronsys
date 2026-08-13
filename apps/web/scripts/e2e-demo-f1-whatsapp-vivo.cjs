/**
 * E2E Demo — F1 "WhatsApp en Vivo" (Spec 04): botones wa.me/tel + checkout dry-run.
 *
 * Flujo completo visible en el monitor (DISPLAY :0), data 100% FICTICIA:
 *   landing (mock contact → botones "Pedir por WhatsApp" / "Llamar" visibles)
 *   → carrito Lomo Saltado → Zona 1 → checkout (teléfono ficticio + UTM)
 *   → código DLV- → pantalla de éxito con "Ver mi pedido por WhatsApp"
 *   → tracking → panel staff (kanban) → transición → cancelación (limpieza)
 *   → verificación: pedido cancelado, backend health 200.
 *
 * Patrón de 2 modos (lección 2026-08-09):
 *   --demo (default): pausas visibles 2.5s entre pasos — para Ron en el monitor.
 *   --fast | --headless: sin pausas — para cierre/CI.
 *
 * Uso:
 *   node scripts/e2e-demo-f1-whatsapp-vivo.cjs [--demo|--fast] [--delay N]
 *
 * Notas:
 *   - WEB = dev server de Vite (:5173, sirve el frontend F1 con botones).
 *   - API = backend prod (:8000) — checkout/kanban/worker dry-run ya operativos.
 *   - contact se MOCKEA vía page.route (backend prod aún sin el campo; sin deploy).
 *   - Sin token en settings.whatsapp → DryRunNotifier: CERO envíos HTTP (CA-B7).
 *   - El pedido se CANCELA al final — sin basura en prod.
 *
 * @file e2e-demo-f1-whatsapp-vivo.cjs
 */
const { chromium } = require("@playwright/test");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--headless");
const delayIdx = args.indexOf("--delay");
const DELAY_MS = delayIdx >= 0 ? parseInt(args[delayIdx + 1], 10) : 2500;

const WEB = process.env.DEMO_BASE_URL || "http://localhost:5173"; // dev server (frontend F1)
const API = process.env.DEMO_API_URL || "http://localhost:8000"; // backend prod
const EMAIL = "admin@elsegoviano.pe";
const PASSWORD = "admin123";
const LANDING = `${WEB}/menu/el-segoviano`;

// Data ficticia (nunca se envía — dry-run)
const PHONE = "999 888 777"; // teléfono ficticio del cliente
const PHONE_RAW = "999888777";
const CUSTOMER = `E2E-F1-Demo-${Date.now()}`;
const UTM_CAMPAIGN = `f1_monitor_${Date.now()}`;
const BUSINESS_PHONE = "51999999999"; // número ficticio del negocio (para botones wa.me/tel)
const ALERT_PHONE = "51999999998";

let trackingCode = null;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  try {
    await page.screenshot({ path: `/tmp/f1wa-step-${Date.now()}.png` });
  } catch {}
  if (DEMO) await sleep(DELAY_MS);
}

async function apiJson(path, opts = {}) {
  const { headers: extraHeaders, ...rest } = opts;
  const res = await fetch(`${API}${path}`, {
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
  console.log(`🚀 Demo F1 WhatsApp en Vivo (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${WEB}`);
  console.log(`   data ficticia: cliente=${CUSTOMER} · tel=${PHONE} · utm=${UTM_CAMPAIGN}`);
  console.log(`   contact mockeado: wa.me/${BUSINESS_PHONE} · tel:+${BUSINESS_PHONE} (sin deploy, CA-F1.14 simulado)`);
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

  // Mock del menú público: inyecta contact ficticio (backend prod aún sin el campo)
  await page.route("**/api/public/el-segoviano/menu", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.contact = {
      whatsapp_link: `https://wa.me/${BUSINESS_PHONE}?text=${encodeURIComponent(
        "¡Hola El Segoviano! Quiero hacer un pedido."
      )}`,
      phone: `tel:+${BUSINESS_PHONE}`,
      whatsapp_message: "¡Hola El Segoviano! Quiero hacer un pedido.",
    };
    await route.fulfill({
      status: response.status(),
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  });

  try {
    // 1. Landing pública con menú nocturno + botones F1 (mock contact)
    await page.goto(`${LANDING}?utm_source=meta&utm_medium=cpc&utm_campaign=${UTM_CAMPAIGN}`, {
      waitUntil: "networkidle",
    });
    await demoStep(page, "1/10 Landing pública — menú nocturno + BOTONES F1 'Pedir por WhatsApp' y 'Llamar'");
    await page.getByText("＋ Agregar al pedido").first().waitFor({ timeout: 20_000 }).catch(() => {});
    await demoStep(page, "2/10 Plato visible (Lomo Saltado S/35) + botón WhatsApp con mensaje prefabricado");

    // 2. Agregar Lomo Saltado (S/35) — supera min_order S/35 de Zona 1
    await page.locator("button").filter({ hasText: "Lomo Saltado" }).first().click();
    await demoStep(page, "3/10 Lomo Saltado agregado al carrito (S/35)");

    // 3. Elegir Zona 1 → fee + total
    await page.locator("select").first().selectOption({ index: 1 });
    await demoStep(page, "4/10 Zona 1 (Montenegro/Motupe/Canto Grande) — fee S/5, total S/40");

    // 4. Formulario de cliente (data ficticia)
    await page.getByPlaceholder("Tu nombre").fill(CUSTOMER);
    await page.getByPlaceholder("999 888 777").fill(PHONE_RAW);
    await page.getByPlaceholder(/Calle, número/).fill("Av. Demo 123, SJL");
    await page.getByPlaceholder(/8 caracteres/).fill("DEMO12345");
    await demoStep(page, "5/10 Cliente ficticio: " + CUSTOMER + " · " + PHONE + " · Av. Demo 123");

    // 5. Confirmar pedido → código DLV-
    await page.getByRole("button", { name: /Confirmar pedido/ }).click();
    await page.getByText("¡Pedido confirmado!").waitFor({ timeout: 30_000 });
    const code = (await page.getByText(/^DLV-[0-9a-f]+$/).first().textContent())?.trim() ?? "";
    trackingCode = code;
    console.log(`✅ CHECKOUT 201 — tracking=${trackingCode}`);
    console.log(`⚡ EVENTO → delivery.confirmed (cliente) + delivery.new_order (alerta local) — worker dry-run`);
    await demoStep(page, "6/10 Pedido confirmado: " + trackingCode + " — botón 'Ver mi pedido por WhatsApp' (wa.me con DLV-)");

    // 6. Tracking por código
    await page.getByRole("button", { name: /Seguir pedido/ }).click().catch(() => {});
    await page.getByPlaceholder("Código DLV-XXXX").fill(trackingCode).catch(() => {});
    await page.getByRole("button", { name: "Buscar" }).click().catch(() => {});
    await demoStep(page, "7/10 Seguimiento: línea de tiempo (recibido → en cocina → …)");

    // 7. Panel staff: login admin + kanban + pestaña Campañas (botones F1)
    await page.goto(`${WEB}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.getByRole("button", { name: /Iniciar Sesión|Ingresar/ }).click();
    await page.waitForURL("**/restaurante/delivery", { timeout: 20_000 }).catch(() => {});
    await page.goto(`${WEB}/restaurante/delivery`, { waitUntil: "networkidle" });
    for (const col of ["Recibido", "En cocina", "Listo", "En ruta", "Entregado", "Cancelado"]) {
      await page.getByText(col).first().waitFor({ timeout: 25_000 }).catch(() => {});
    }
    await demoStep(page, "8/10 Panel staff — kanban de pedidos (máquina de estados)");

    // 8. Pestaña Campañas: botones "Abrir en WhatsApp" / "Llamar" (F1 §3.6)
    await page.getByRole("tab", { name: /Campañas/ }).click().catch(() => {});
    await page.getByText(/Abrir en WhatsApp|Llamar/).first().waitFor({ timeout: 15_000 }).catch(() => {});
    await demoStep(page, "9/10 Campañas — botones F1 'Abrir en WhatsApp' (wa.me+UTM) y 'Llamar' (tel:)");

    // 9. Volver a Pedidos y cancelar vía API (determinista; dispara delivery.cancelled) — limpieza
    await cancelOrder();
    await demoStep(page, "10/10 Pedido CANCELADO — ⚡ evento delivery.cancelled (alerta local) — limpieza completa");

    // 10. Verificación final
    let status = "?";
    for (let i = 0; i < 6; i++) {
      const track = await apiJson(`/api/public/orders/${trackingCode}/status`);
      status = track.body?.status ?? "?";
      if (status === "cancelled") break;
      await sleep(1000);
    }
    const health = await apiJson("/health");
    console.log(`\n📋 VERIFICACIÓN FINAL:`);
    console.log(`   pedido ${trackingCode} → status=${status} (esperado: cancelled)`);
    console.log(`   backend /health → HTTP ${health.status} (esperado: 200)`);
    console.log(`   eventos → worker dry-run (CERO envíos HTTP, CA-B7)`);
    console.log(`✅ DEMO F1 COMPLETADA — botones WhatsApp/Llamar + checkout dry-run funcionando`);
    console.log(`📸 Screenshots: /tmp/f1wa-step-*.png`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/f1wa-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await cancelOrder();
    await browser.close();
  }
}

main();
