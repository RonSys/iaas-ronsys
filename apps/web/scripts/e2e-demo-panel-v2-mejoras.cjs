/**
 * E2E Demo — Panel del Dueño Mejoras V2 (Spec 04 §3.2-V2: CA-M1..M4).
 *
 * Patrón de 2 modos (lección 2026-08-09, igual que e2e-demo-panel-v2.cjs):
 *   --demo (default): pausas visibles 2.5s entre pasos — para que Ron
 *                     vea el flujo en el monitor del servidor (DISPLAY :0).
 *   --fast | --headless: sin pausas — para cierre/CI.
 *
 * Mockea GET /api/v1/dashboard/owner (+ export) con el payload de
 * e2e/fixtures/mocks.ts (que incluye los 4 bloques nuevos CA-M1..M4) vía
 * page.route, para que las secciones nuevas rendericen con datos conocidos.
 *
 * Uso:
 *   node scripts/e2e-demo-panel-v2-mejoras.cjs [--demo|--fast] [--delay N]
 *
 * @file e2e-demo-panel-v2-mejoras.cjs
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

const SCREENSHOT_PATH = "/home/ron/projectos/segoviano/tmp-verify/panel-mejoras-v2.png";

// ─── Payload del mock (espejo de e2e/fixtures/mocks.ts → mockOwnerDashboard) ───
// Incluye los 4 bloques nuevos de la Iteración 3 (CA-M1..M4).
function ownerDashboardPayload() {
  return {
    period: { date_from: "2026-08-04", date_to: "2026-08-10" },
    kpis: {
      sales_total: 4850.5,
      orders_count: 42,
      avg_ticket: 115.5,
      orders_delivery: 15,
      orders_dine_in: 22,
      orders_takeout: 5,
      delivery_pct: 35.7,
      kitchen_open: 6,
      delivery_in_route: 3,
    },
    sales_by_hour: [
      { hour: 12, dine_in: 850.0, delivery: 420.0 },
      { hour: 13, dine_in: 1100.0, delivery: 380.0 },
      { hour: 19, dine_in: 900.0, delivery: 520.0 },
      { hour: 20, dine_in: 750.0, delivery: 610.0 },
    ],
    sales_by_weekday: [
      { weekday: 1, total: 3200.0 },
      { weekday: 2, total: 2800.0 },
      { weekday: 3, total: 3100.0 },
      { weekday: 4, total: 3400.0 },
      { weekday: 5, total: 4200.0 },
      { weekday: 6, total: 5100.0 },
      { weekday: 7, total: 4600.0 },
    ],
    channels: { dine_in: 2450.0, takeout: 620.0, delivery: 1780.5 },
    top_platos: [
      { name: "Ceviche Clásico", qty: 18, total: 720.0 },
      { name: "Lomo Saltado", qty: 14, total: 630.0 },
      { name: "Arroz con Mariscos", qty: 10, total: 550.0 },
    ],
    payments: { yape: 1800.0, plin: 950.0, cash: 1200.0, card: 700.5, transfer: 200.0 },
    delivery: {
      orders_by_zone: [
        { zone: "Norte", orders: 6 },
        { zone: "Centro", orders: 5 },
        { zone: "Sur", orders: 4 },
      ],
      funnel: {
        received: 15,
        preparing: 11,
        ready: 8,
        out_for_delivery: 3,
        delivered: 12,
        cancelled: 1,
      },
      avg_delivery_min: 32,
      gmv: 1780.5,
      fee_total: 89.0,
    },
    campaigns: [
      { campaign_id: 1, name: "Lanzamiento", channel: "meta", spend: 150.0, orders: 12, gmv: 900.0, aov: 75.0, roas: 6.0 },
      { campaign_id: 2, name: "Delivery Norte", channel: "google", spend: 80.0, orders: 5, gmv: 350.0, aov: 70.0, roas: 4.4 },
    ],
    heatmap: {
      dine_in: {
        rows: (() => {
          const rows = [];
          for (let h = 0; h < 24; h++) {
            for (let d = 1; d <= 7; d++) rows.push({ hour: h, weekday: d, total: 0 });
          }
          for (const [k, v] of Object.entries({
            "12-1": 320.5, "12-2": 410.0, "13-1": 512.0, "13-3": 460.0,
            "13-6": 480.0, "19-5": 505.0, "20-5": 390.0, "19-7": 450.0,
          })) {
            const [h, d] = k.split("-").map(Number);
            rows[h * 7 + (d - 1)].total = v;
          }
          return rows;
        })(),
      },
      delivery: {
        rows: (() => {
          const rows = [];
          for (let h = 0; h < 24; h++) {
            for (let d = 1; d <= 7; d++) rows.push({ hour: h, weekday: d, total: 0 });
          }
          for (const [k, v] of Object.entries({
            "12-1": 210.0, "12-5": 250.0, "13-2": 300.0, "19-6": 340.0,
            "20-5": 420.0, "20-6": 380.0, "21-7": 260.0,
          })) {
            const [h, d] = k.split("-").map(Number);
            rows[h * 7 + (d - 1)].total = v;
          }
          return rows;
        })(),
      },
    },
    margins: {
      by_channel: [
        { channel: "dine_in", revenue: 2450.0, cost: 980.0, margin_pct: 60.0 },
        { channel: "takeout", revenue: 620.0, cost: 310.0, margin_pct: 50.0 },
        { channel: "delivery", revenue: 1780.5, cost: 890.25, margin_pct: 50.0 },
      ],
      costable_note: "Margen calculado solo sobre ítems con receta (average_cost); ventas sin receta no aportan costo (decisión R2)",
    },
    comparison: {
      current: { sales_total: 4850.5, orders_count: 42, avg_ticket: 115.5, delivery_pct: 35.7 },
      previous: { sales_total: 4100.0, orders_count: 38, avg_ticket: 107.9, delivery_pct: 31.2 },
      deltas: { sales_total_pct: 18.3, orders_count_pct: 10.5, avg_ticket_pct: 7.0, delivery_pct_delta: 4.5 },
    },
    alerts: [
      { severity: "yellow", metric: "sales_total", message: "Hoy Ventas -12% vs promedio últimos 7 días" },
    ],
    // ─── Iteración 3 (CA-M1..M4) ───
    top_waiters: {
      rows: [
        { user_id: 1, name: "Juan Pérez", sales_count: 12, total: 1520.0, avg_ticket: 126.67 },
        { user_id: 2, name: "María Gómez", sales_count: 10, total: 1310.5, avg_ticket: 131.05 },
        { user_id: 3, name: "Carlos Ruiz", sales_count: 8, total: 940.0, avg_ticket: 117.5 },
        { user_id: 4, name: "Lucía Torres", sales_count: 6, total: 690.0, avg_ticket: 115.0 },
        { user_id: 5, name: "Pedro Díaz", sales_count: 4, total: 390.0, avg_ticket: 97.5 },
      ],
      total_sales: 40,
    },
    cancellation_rate: {
      voided_count: 2,
      total_count: 42,
      rate_pct: 4.8,
      top_reasons: [
        { reason: "Cliente no llegó", count: 1 },
        { reason: "Error de pedido", count: 1 },
      ],
    },
    avg_ticket_by: {
      channel: [
        { channel: "dine_in", ticket: 128.4 },
        { channel: "delivery", ticket: 97.2 },
      ],
      shift: [
        { shift: "morning", ticket: 88.5, orders: 8 },
        { shift: "afternoon", ticket: 132.1, orders: 22 },
        { shift: "evening", ticket: 115.8, orders: 12 },
      ],
    },
    delivery_campaign_effect: {
      by_campaign: [
        { campaign_id: 1, campaign_name: "Lanzamiento", orders: 12, gmv: 900.0, aov: 75.0 },
        { campaign_id: null, campaign_name: "Sin campaña", orders: 3, gmv: 180.5, aov: 60.17 },
      ],
      by_channel: [
        { source: "meta", orders: 12, gmv: 900.0, aov: 75.0 },
        { source: "directo", orders: 3, gmv: 180.5, aov: 60.17 },
      ],
    },
  };
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, desc) {
  console.log(`⏸ demo: ${desc}...`);
  if (DEMO) await sleep(DELAY_MS);
}

async function main() {
  console.log(`🚀 E2E Demo Panel Mejoras V2 (CA-M1..M4) (${DEMO ? "demo " + DELAY_MS + "ms" : "fast"}) → ${BASE_URL}`);
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

  // Mock del dashboard del dueño (+ export) ANTES de navegar: las secciones
  // CA-M1..M4 renderizan con datos conocidos sin depender del backend.
  await page.route("**/api/v1/dashboard/owner/export**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "text/csv",
      body: "# kpis\nmetric,value\nsales_total,4850.50\n",
    });
  });
  await page.route("**/api/v1/dashboard/owner**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(ownerDashboardPayload()),
    });
  });

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
    await demoStep(page, "Panel del Dueño cargado (mock con datos CA-M1..M4)");

    // 3. Regresión V1/V2: KPIs + heatmap + márgenes
    await page.waitForSelector("text=Ventas", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "KPIs visibles (regresión V1)");
    await page.waitForSelector("text=Heatmap de demanda — Salón", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA10: Heatmap Salón");
    await page.waitForSelector("text=Margen por canal (costeo por recetas)", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "V2 CA11: Márgenes por canal");

    // 4. Iteración 3 — secciones nuevas CA-M1..M4
    await page.waitForSelector("text=Top meseros", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Iteración 3 CA-M1: Top meseros (ranking + barras)");
    await page.waitForSelector("text=Rate de anulación", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Iteración 3 CA-M2: Rate de anulación (4.8% + motivos)");
    await page.waitForSelector("text=Ticket promedio por turno", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Iteración 3 CA-M3: Ticket promedio por turno y canal");
    await page.waitForSelector("text=Delivery: campaña vs sin campaña", { timeout: 15000 }).catch(() => {});
    await demoStep(page, "Iteración 3 CA-M4: Delivery campaña vs sin campaña + canal publicitario");

    // 5. Screenshot final full-page (espera explícita de las secciones nuevas)
    await page.waitForSelector("text=Top meseros", { timeout: 15000 });
    await page.waitForSelector("text=Rate de anulación", { timeout: 15000 });
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    console.log(`✅ DEMO MEJORAS V2 COMPLETADA — screenshot: ${SCREENSHOT_PATH}`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await page.screenshot({ path: "/tmp/panel-mejoras-v2-error.png", fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
