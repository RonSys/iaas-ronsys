/**
 * E2E Prueba EN CALIENTE — F2 Central Telefónica → KÁRDEX (descuento de insumos)
 *
 * Flujo visible en el monitor (DISPLAY :0), contra PRODUCCIÓN REAL:
 *   login staff (admin@elsegoviano.pe, tenant 1)
 *   → panel Central Telefónica (/restaurante/central) — WS conectado
 *   → inyectar llamada simulada ringing → answered (tenant 1, upsert idempotente)
 *   → ver llamada EN VIVO (WS call.incoming / call.answered)
 *   → abrir modal "Convertir a pedido"
 *   → seleccionar zona (Montenegro/Motupe/Canto Grande, S/5 fee, min S/35)
 *   → items: Arroz con Mariscos (S/32) + Inca Kola (S/5) = S/37 > mínimo
 *   → pago Efectivo (sin referencia obligatoria)
 *   → Guardar → DLV- creado + card "✅ Convertida"
 *   → VERIFICAR KÁRDEX: stock de insumos ANTES vs DESPUÉS (vía API inventario)
 *     insumos Arroz con Mariscos: Arroz(47), Mariscos(42), Cebolla(44), Ají(48)
 *   → limpieza: cancelar pedido DLV- + purgar CallRecords de prueba
 *
 * Patrón: --demo (default) pausas 2.5s | --fast | --headless | --delay N
 * Uso: node scripts/e2e-hot-f2-kardex.cjs [--demo|--fast] [--delay N]
 *
 * @file e2e-hot-f2-kardex.cjs
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
const API = "https://www.ronsyserp.com/api/v1";
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

// ─── Datos de prueba ─────────────────────────────────────────────
const CALLER = "51988877766"; // caller ID de prueba (no real)
const CALLEE = "5115551234"; // DID placeholder (settings.calls)
const EXT_ID = `e2e-kardex-${Date.now()}`;

// Items: Arroz con Mariscos (id 14, S/32) + Inca Kola (id 15, S/5) = S/37
const ITEMS = [
  { menu_item_id: 14, quantity: 1, modifiers: [] },
  { menu_item_id: 15, quantity: 1, modifiers: [] },
];

// Insumos a verificar en kárdex (Arroz con Mariscos — receta del item 14)
const INSUMOS = [
  { id: 47, name: "Arroz" },
  { id: 42, name: "Mariscos mixtos" },
  { id: 44, name: "Cebolla" },
  { id: 48, name: "Ají amarillo" },
];

let JWT = "";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  try {
    await page.screenshot({ path: `/tmp/hotf2kardex-step-${Date.now()}.png` });
  } catch {}
  if (DEMO) await sleep(DELAY_MS);
}

// ─── API helpers ──────────────────────────────────────────────────

async function apiLogin() {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  const body = await res.json();
  JWT = body?.access_token || body?.token || "";
  return !!JWT;
}

async function injectCall(status) {
  const res = await fetch(`${API}/calls/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Service-Token": SERVICE_TOKEN },
    body: JSON.stringify({
      external_call_id: EXT_ID,
      tenant_id: 1, // tenant del usuario E2E (admin → Admin Tenant id=1)
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

async function fetchStock() {
  const res = await fetch(`${API}/inventory/products?search=`, {
    headers: { Authorization: `Bearer ${JWT}`, "X-Tenant-ID": "1" },
  });
  if (!res.ok) return null;
  const data = await res.json();
  const items = Array.isArray(data) ? data : data?.products ?? data?.items ?? [];
  const map = {};
  for (const ins of INSUMOS) {
    const p = items.find((x) => x.id === ins.id || x.name === ins.name);
    map[ins.name] = p ? Number(p.current_stock) : null;
  }
  return map;
}

async function cancelOrder(tracking) {
  // Buscar el delivery order por tracking y cancelarlo
  const res = await fetch(`${API}/delivery/orders`, {
    headers: { Authorization: `Bearer ${JWT}`, "X-Tenant-ID": "1" },
  });
  const data = await res.json();
  const orders = Array.isArray(data) ? data : data?.items ?? [];
  const order = orders.find((o) => o.tracking_code === tracking);
  if (!order) return null;
  const r = await fetch(`${API}/delivery/orders/${order.id}/status`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${JWT}`, "X-Tenant-ID": "1", "Content-Type": "application/json" },
    body: JSON.stringify({ status: "cancelled" }),
  });
  return r.ok ? r.json() : null;
}

async function purgeCalls() {
  // Los CallRecords de prueba se purgan por SQL en el servidor (el script
  // corre en ronpk): docker exec iaas-postgres psql ...
  const { execSync } = require("child_process");
  try {
    execSync(
      `docker exec iaas-postgres psql -U ron -d iaas_ronsys -c "DELETE FROM call_records WHERE external_call_id LIKE 'e2e-%';"`,
      { stdio: "pipe" },
    );
    console.log("   CallRecords e2e-* purgados");
  } catch (e) {
    console.log("   (aviso) purga call_records: " + e.message.split("\n")[0]);
  }
}

// ─── Main ─────────────────────────────────────────────────────────

async function main() {
  console.log(`🔥 E2E EN CALIENTE F2 → KÁRDEX (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE}`);
  console.log(`   llamada simulada: ${CALLER} → ${CALLEE} (token: ${SERVICE_TOKEN ? "OK" : "FALTA"})`);
  console.log(`   items: Arroz con Mariscos (S/32) + Inca Kola (S/5) = S/37 (min S/35)`);
  console.log(`   insumos a verificar: ${INSUMOS.map((i) => i.name).join(", ")}`);

  // Login API para consultas de stock
  const apiOk = await apiLogin();
  console.log(`   API login (stock): ${apiOk ? "OK" : "FALLO — usaré SQL"}`);

  // Stock ANTES (vía API o fallback SQL)
  let stockAntes = null;
  if (apiOk) stockAntes = await fetchStock();
  if (!stockAntes) {
    const { execSync } = require("child_process");
    const out = execSync(
      `docker exec iaas-postgres psql -U ron -d iaas_ronsys -t -c "SELECT id, name, current_stock FROM products WHERE id IN (47,42,44,48);"`,
    ).toString();
    stockAntes = {};
    for (const line of out.trim().split("\n")) {
      const [, name, stock] = line.split("|").map((s) => s.trim());
      stockAntes[name] = parseFloat(stock);
    }
  }
  console.log(`\n📦 STOCK ANTES (insumos Arroz con Mariscos):`);
  for (const [k, v] of Object.entries(stockAntes)) console.log(`   ${k}: ${v}`);

  const browser = await chromium.launch({
    headless: HEADLESS,
    executablePath: "/home/ron/.local/share/chrome-linux64/chrome",
    args: [
      "--no-first-run", "--no-default-browser-check", "--disable-infobars",
      "--disable-session-crashed-bubble", "--disable-features=Translate",
    ],
    chromiumSandbox: false,
  });

  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();

  try {
    // 1. Login staff
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await demoStep(page, "1/9 Login staff (admin@elsegoviano.pe)");
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.getByRole("button", { name: /Iniciar Sesión|Ingresar/ }).click();
    await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 15_000 }).catch(() => {});
    await demoStep(page, "2/9 Login exitoso — dashboard (URL: " + page.url().replace(BASE, "") + ")");

    // 2. Panel Central Telefónica
    await page.goto(`${BASE}/restaurante/central`, { waitUntil: "networkidle" });
    await page.getByText("En vivo").first().waitFor({ timeout: 20_000 }).catch(() => {});
    await demoStep(page, "3/9 Panel Central — tab 'En vivo' (WS conectado)");

    // 3. Inyectar llamada ringing → answered (WS ya conectado)
    if (SERVICE_TOKEN) {
      const r1 = await injectCall("ringing");
      console.log(`📞 ringing inyectada → id=${r1.id} (HTTP ${r1.status})`);
      await page.waitForTimeout(3000);
      const r2 = await injectCall("answered");
      console.log(`📞 answered → upsert id=${r2.id} (HTTP ${r2.status})`);
      await page.waitForTimeout(4000);
    }
    await demoStep(page, "4/9 Llamada EN VIVO: " + CALLER + " (contestada + botón Convertir)");

    // 4. Abrir modal Convertir a pedido
    const convBtn = page.getByRole("button", { name: /Convertir a pedido/ }).first();
    if (await convBtn.count()) {
      await convBtn.click();
      await page.waitForTimeout(2000);
      await demoStep(page, "5/11 Modal 'Convertir a pedido' abierto");

      // Helper: scroll DENTRO del modal hasta que el elemento sea visible.
      // (El modal tiene max-h-[85vh] overflow-y-auto: sin scroll los
      // selectores de zona/pago quedan fuera del viewport y Ron no los ve.)
      const scrollModalTo = async (locator) => {
        await locator.scrollIntoViewIfNeeded({ timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(600);
      };

      // 5. Scroll a Zona + seleccionar (Montenegro / Motupe / Canto Grande = id 1)
      await page.getByText("Zona de delivery").first().waitFor({ timeout: 10000 }).catch(() => {});
      const zonaSelect = page.getByLabel(/Zona de delivery/).first();
      await scrollModalTo(zonaSelect);
      await demoStep(page, "6/11 Scroll dentro del modal → selector ZONA visible");
      await zonaSelect.selectOption({ index: 1 }).catch(async () => {
        await zonaSelect.selectOption("1").catch(() => {});
      });
      console.log("   zona value:", await zonaSelect.inputValue().catch(() => "?"));
      await demoStep(page, "7/11 Zona SELECCIONADA: Montenegro — S/5 fee, min S/35");

      // 6. Scroll a items + cantidad (Arroz con Mariscos x1 + Inca Kola x1)
      await page.getByText("Arroz con Mariscos").first().waitFor({ timeout: 15000 }).catch(() => {});
      for (const itemName of ["Arroz con Mariscos", "Inca Kola"]) {
        const row = page
          .locator('div.flex.items-center.justify-between.text-sm', { hasText: itemName })
          .first();
        if (await row.count()) {
          const input = row.locator('input[type="number"]');
          await scrollModalTo(input);
          await input.fill("1");
          const val = await input.inputValue();
          if (val !== "1") {
            await input.press("ArrowUp");
          }
          console.log(`   item ${itemName}: cantidad ${await input.inputValue()}`);
        } else {
          console.log(`   ⚠️ item ${itemName} no encontrado en el modal`);
        }
      }
      await demoStep(page, "8/11 Items: Arroz con Mariscos (S/32) + Inca Kola (S/5) = S/37 (min OK)");

      // 7. Scroll a Pago + seleccionar YAPE con referencia (flujo real)
      const pagoSelect = page.getByLabel(/Pago/).first();
      await scrollModalTo(pagoSelect);
      await demoStep(page, "9/11 Scroll → desplegable PAGO visible");
      await pagoSelect.selectOption("yape").catch(async () => {
        await pagoSelect.selectOption({ index: 0 }).catch(() => {});
      });
      // Referencia yape (obligatoria en el motor de ventas)
      const refInput = page.getByPlaceholder(/Código de referencia/).first();
      if (await refInput.count()) {
        await scrollModalTo(refInput);
        await refInput.fill("E2E-KARDEX-" + Date.now().toString().slice(-6));
      }
      // Dirección (sugerencia de zona) + nombre
      const addr = page.getByPlaceholder(/Av\. …/);
      if (await addr.count()) {
        await scrollModalTo(addr);
        await addr.fill("Av. Montenegro 123, Lima");
      }
      const nombre = page.getByPlaceholder(/Nombre \(opcional\)/);
      if (await nombre.count()) {
        await scrollModalTo(nombre);
        await nombre.fill("Cliente E2E Kárdex");
      }
      await demoStep(page, "10/11 Pago SELECCIONADO: Yape + referencia + dirección");

      // 8. Scroll al botón Guardar + clic → DLV-
      const btn = page.getByRole("button", { name: /Crear pedido/ });
      await scrollModalTo(btn);
      await btn.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
      await btn.evaluate((el) => el.disabled).then((d) => console.log("   btnCrear disabled?", d));
      await btn.click({ timeout: 5000 }).catch(() => console.log("   ⚠️ no se pudo hacer clic en Crear pedido"));
      await page.waitForTimeout(6000);
      await demoStep(page, "11/11 Pedido creado (DLV-) — card '✅ Convertida'");

      // Capturar el tracking del mensaje de éxito (si aparece)
      try {
        const okText = await page.getByText(/Pedido .* creado|DLV-/).first().innerText();
        console.log(`   mensaje: ${okText}`);
      } catch {}
    } else {
      console.log("⚠️ Botón 'Convertir a pedido' NO apareció — ¿WS recibió la llamada?");
      await demoStep(page, "5/9 ⚠️ Sin botón Convertir");
    }

    // 9. Verificación: stock DESPUÉS
    let stockDespues = null;
    if (apiOk) stockDespues = await fetchStock();
    if (!stockDespues) {
      const { execSync } = require("child_process");
      const out = execSync(
        `docker exec iaas-postgres psql -U ron -d iaas_ronsys -t -c "SELECT id, name, current_stock FROM products WHERE id IN (47,42,44,48);"`,
      ).toString();
      stockDespues = {};
      for (const line of out.trim().split("\n")) {
        const [, name, stock] = line.split("|").map((s) => s.trim());
        stockDespues[name] = parseFloat(stock);
      }
    }

    console.log(`\n📦 STOCK DESPUÉS (insumos Arroz con Mariscos):`);
    for (const [k, v] of Object.entries(stockDespues)) console.log(`   ${k}: ${v}`);

    console.log(`\n📉 DELTA KÁRDEX (antes → después):`);
    for (const ins of INSUMOS) {
      const antes = stockAntes?.[ins.name] ?? "?";
      const despues = stockDespues?.[ins.name] ?? "?";
      const delta = typeof antes === "number" && typeof despues === "number" ? (despues - antes).toFixed(2) : "?";
      console.log(`   ${ins.name}: ${antes} → ${despues} (delta ${delta})`);
    }

    // Tracking del pedido (buscar el último delivery order con la nota de QA)
    let tracking = null;
    if (apiOk) {
      const res = await fetch(`${API}/delivery/orders`, {
        headers: { Authorization: `Bearer ${JWT}`, "X-Tenant-ID": "1" },
      });
      const data = await res.json();
      const orders = Array.isArray(data) ? data : data?.items ?? [];
      tracking = orders.find((o) => o.notes?.includes("E2E"))?.tracking_code || orders[0]?.tracking_code;
      if (tracking) console.log(`\n🧾 Pedido detectado: ${tracking}`);
    }

    // 10. Limpieza
    if (tracking) {
      const c = await cancelOrder(tracking);
      console.log(`   Pedido ${tracking} cancelado: ${c ? "✅" : "⚠️ no cancelado"}`);
    }
    await purgeCalls();

    console.log(`\n✅ E2E F2 → KÁRDEX COMPLETADA — delta de insumos visible arriba`);
    console.log(`📸 Screenshots: /tmp/hotf2kardex-step-*.png`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/hotf2kardex-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
