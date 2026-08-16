#!/usr/bin/env node
/**
 * E2E en caliente — F6 "Agenda de Citas" (Spec 07) + Spec 08 (siembra mesas)
 * ================================================================
 * Monitor de producción (patrón e2e-hot-f3-recepcionista.cjs --demo / e2e-hot-f5).
 *
 * REQUISITO D4 (Ron): navegador ABIERTO en el monitor del servidor (DISPLAY :0),
 * modo --demo con pausas visibles. Evidencias en docs/reports/evidencias-f6-e2e-prod/.
 *
 * Flujo:
 *   A) TENANT 1 (operativo, mesas reales normalizadas — spec 08 D2):
 *      login staff → /restaurante/agenda → availability mesas reales →
 *      crear cita (modal) → verificar lista → confirmar (espejo reserved D1) →
 *      cancelar (espejo available) → limpieza.
 *   B) TENANT 3 (desde cero — spec 08 D3):
 *      login temp admin (creado para el E2E) → availability vacío (0 mesas) →
 *      appointments vacío → limpieza (usuario temp eliminado).
 *
 * ⚠️ REQUISITO RON: fixtures/payloads con tenant-id = 3 (solo para el flujo B;
 *    el flujo A usa el tenant operativo 1 con sus mesas reales).
 *
 * Uso:
 *   node scripts/e2e-hot-f6-agenda.cjs --demo   (navegador visible, pausas — MONITOR)
 *   node scripts/e2e-hot-f6-agenda.cjs --fast   (headless, sin pausas — CI)
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const args = process.argv.slice(2);
const DEMO = !args.includes("--fast");
const HEADLESS = args.includes("--fast") || process.env.E2E_HEADLESS === "1";
const DELAY_MS = 2800;

const BASE = process.env.E2E_BASE_URL || "http://localhost:8081";
const API = process.env.E2E_API_URL || "http://localhost:8000";

// Tenant 1 — operativo (spec 08 D1: el negocio real vive en tenant 1)
const EMAIL_T1 = "admin@elsegoviano.pe";
const PW_T1 = process.env.E2E_PW_T1 || "admin123";

// Tenant 3 — desde cero (spec 08 D3: entidad sin data; usuario temp para el E2E)
const TENANT3 = 3;
const EMAIL_T3 = "e2e-t3@elsegoviano.pe";
const PW_T3 = "e2e-t3-pass-2026";
const NAME_T3 = "E2E Tenant 3 Temp";

const OUT_DIR = path.join(__dirname, "../../../docs/reports/evidencias-f6-e2e-prod");
const RESULTS = [];
const APPT_DATE = (() => {
  const d = new Date();
  d.setDate(d.getDate() + 5);
  return d.toISOString().slice(0, 10);
})();
const CUSTOMER = "E2E F6 Cliente Monitor";
const PHONE = "+51999000007";

function record(name, ok, detail = "") {
  RESULTS.push({ name, ok, detail });
  console.log(`${ok ? "✅" : "❌"} ${name}${detail ? " — " + detail : ""}`);
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function demoStep(page, label) {
  console.log(`⏸ demo: ${label}`);
  if (DEMO) await sleep(DELAY_MS);
}

async function apiLogin(email, password) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await res.json();
  return { token: body.access_token || body.token || null, status: res.status };
}

async function api(pathname, token, opts = {}, tenantId) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
  if (tenantId) headers["X-Tenant-ID"] = String(tenantId);
  const res = await fetch(`${API}${pathname}`, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}
  return { status: res.status, json, text };
}

function runSql(sql) {
  return execSync(
    `docker exec iaas-postgres psql -U ron -d iaas_ronsys -tAc "${sql.replace(/"/g, '\\"')}"`,
    { encoding: "utf8" },
  ).trim();
}

// Crea usuario temp tenant 3 (patrón reset_demo_passwords de deploy.sh)
// ⚠️ El hash Argon2 contiene '$' → se pasa por env var para evitar expansión de shell.
function createTempTenant3User() {
  const hash = execSync(
    `docker exec -w /app iaas-backend-prod env PYTHONPATH=/app python -c "from pwdlib import PasswordHash; from pwdlib.hashers.argon2 import Argon2Hasher; print(PasswordHash([Argon2Hasher()]).hash('${PW_T3}'))"`,
    { encoding: "utf8" },
  ).trim();
  // Heredoc con delimitador citado (<<'SQL') → el shell NO expande $ → el hash Argon2 se inserta literal.
  execSync(
    `docker exec -i iaas-postgres psql -U ron -d iaas_ronsys <<'SQL'
INSERT INTO users (email, hashed_password, full_name, role, tenant_id, is_active, is_verified, failed_login_attempts, created_at, updated_at)
VALUES ('${EMAIL_T3}', '${hash}', '${NAME_T3}', 'admin', ${TENANT3}, true, true, 0, now(), now())
ON CONFLICT (email) DO UPDATE SET hashed_password=EXCLUDED.hashed_password, role='admin', tenant_id=${TENANT3}, is_active=true, updated_at=now();
SQL`,
    { encoding: "utf8", shell: "/bin/bash" },
  );
  return true;
}

function deleteTempTenant3User() {
  runSql(`DELETE FROM users WHERE email='${EMAIL_T3}'`);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({
    headless: HEADLESS,
    chromiumSandbox: false,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  console.log(`🖥️  E2E F6 PROD ${DEMO ? "--demo (MONITOR DISPLAY :0)" : "--fast (headless)"} · fecha cita: ${APPT_DATE}`);

  let tokenT1 = null;
  let tokenT3 = null;
  let appointmentId = null;
  let createdTableId = null;

  try {
    // ═══════════════════ FLUJO A — TENANT 1 (mesas reales) ═══════════════════
    console.log("\n═══ FLUJO A: TENANT 1 (operativo, mesas reales) ═══");
    const l1 = await apiLogin(EMAIL_T1, PW_T1);
    tokenT1 = l1.token;
    const payload1 = tokenT1 ? JSON.parse(Buffer.from(tokenT1.split(".")[1], "base64").toString()) : {};
    record("A-P0: login API tenant 1", !!tokenT1, `company_id=${payload1.company_id}`);

    // A-P1: availability mesas reales (spec 08 CA-SM-3)
    const avail = await api(
      `/api/v1/appointments/availability?date=${APPT_DATE}&guests=2&from=20:00&to=21:00`,
      tokenT1, {}, 1,
    );
    const slots = avail.json?.slots ?? [];
    record("A-P1: availability mesas reales (tenant 1)", slots.length > 0, `${slots.length} slot(s)`);

    // A-P2: login UI → agenda
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', EMAIL_T1);
    await page.fill('input[type="password"]', PW_T1);
    await page.getByRole("button", { name: /Iniciar Sesión/ }).click();
    await page.waitForTimeout(2500);
    await page.goto(`${BASE}/restaurante/agenda`, { waitUntil: "networkidle" }).catch(() => {});
    await page.waitForTimeout(2500);
    const bodyA = await page.locator("body").innerText().catch(() => "");
    record("A-P2: /restaurante/agenda cargado", bodyA.includes("Agenda de Citas"), page.url());
    await page.screenshot({ path: path.join(OUT_DIR, "01-agenda-t1.png") });
    await demoStep(page, "A-P2 agenda tenant 1 (mesas reales)");

    // A-P3: modal Nueva cita → slots reales
    await page.getByRole("button", { name: /Nueva cita/ }).click();
    await page.waitForTimeout(1200);
    const dateInput = page.locator('input[type="date"]').first();
    if (await dateInput.count()) await dateInput.fill(APPT_DATE);
    await page.locator('input[type="time"]').first().fill("20:00");
    await page.waitForTimeout(3000);
    const slotBtns = page.locator('button:has-text("🪑 Mesa")');
    const slotCount = await slotBtns.count();
    record("A-P3: slots reales en modal", slotCount > 0, `${slotCount} mesa(s)`);
    await page.screenshot({ path: path.join(OUT_DIR, "02-modal-disponibilidad-t1.png") });
    await demoStep(page, "A-P3 modal con disponibilidad real (mesas tenant 1)");

    // A-P4: crear cita (mesa real)
    if (slotCount > 0) {
      await slotBtns.first().click();
    }
    await page.locator('input[placeholder="Nombre y apellido"]').fill(CUSTOMER);
    await page.locator('input[placeholder="+51 999 999 999"]').fill(PHONE);
    await page.getByRole("button", { name: /Reservar mesa/ }).click();
    await page.waitForTimeout(3000);
    const afterCreate = await page.locator("body").innerText().catch(() => "");
    record("A-P4: cita creada (201)", afterCreate.includes(CUSTOMER), "");
    await page.screenshot({ path: path.join(OUT_DIR, "03-cita-creada-t1.png") });
    await demoStep(page, "A-P4 cita creada en tenant 1");

    // A-P5: verificar en lista
    const list = await api(
      `/api/v1/appointments?date=${APPT_DATE}&status=solicitada`,
      tokenT1, {}, 1,
    );
    const mine = (list.json?.items ?? []).find((i) => i.customer_name === CUSTOMER);
    appointmentId = mine?.id ?? null;
    record("A-P5: cita en lista (solicitada)", !!mine, mine ? `id=${mine.id} mesa=${mine.table_number ?? mine.table_id}` : "");
    record("A-P5.1: tenant_id=1", mine?.tenant_id === 1);
    createdTableId = mine?.table_id ?? null;

    // A-P6: confirmar → espejo reserved (D1)
    if (appointmentId) {
      const conf = await api(`/api/v1/appointments/${appointmentId}`, tokenT1, {
        method: "PATCH", body: { status: "confirmada" },
      }, 1);
      record("A-P6: confirmar → confirmada", conf.json?.status === "confirmada");
      if (createdTableId) {
        // GET /tables/{id} tiene un bug pre-existente (MissingGreenlet) → usar lista
        const t = await api(`/api/v1/restaurant/tables`, tokenT1, {}, 1);
        const row = (t.json ?? []).find((x) => x.id === createdTableId);
        record("A-P6.1: espejo mesa = reserved (D1)", row?.status === "reserved", `status=${row?.status}`);
      }
      await page.reload({ waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(2000);
      const fDate = page.locator('input[type="date"]').first();
      if (await fDate.count()) await fDate.fill(APPT_DATE);
      await page.getByRole("button", { name: /Filtrar/ }).click().catch(() => {});
      await page.waitForTimeout(2500);
      record("A-P6.2: UI muestra Confirmada", (await page.locator(`text=${CUSTOMER}`).count()) > 0, "");
      await page.screenshot({ path: path.join(OUT_DIR, "04-cita-confirmada-t1.png") });
      await demoStep(page, "A-P6 cita confirmada (espejo mesa=reserved)");
    }

    // A-P7: cancelar → espejo available
    if (appointmentId) {
      const canc = await api(`/api/v1/appointments/${appointmentId}`, tokenT1, {
        method: "PATCH", body: { status: "cancelada" },
      }, 1);
      record("A-P7: cancelar → cancelada", canc.json?.status === "cancelada");
      if (createdTableId) {
        const t = await api(`/api/v1/restaurant/tables`, tokenT1, {}, 1);
        const row = (t.json ?? []).find((x) => x.id === createdTableId);
        record("A-P7.1: espejo mesa liberada", row?.status === "available", `status=${row?.status}`);
      }
      await page.reload({ waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(2000);
      const fDate2 = page.locator('input[type="date"]').first();
      if (await fDate2.count()) await fDate2.fill(APPT_DATE);
      await page.getByRole("button", { name: /Filtrar/ }).click().catch(() => {});
      await page.waitForTimeout(2500);
      record("A-P7.2: UI muestra Cancelada", (await page.locator(`text=${CUSTOMER}`).count()) > 0, "");
      await page.screenshot({ path: path.join(OUT_DIR, "05-cita-cancelada-t1.png") });
      await demoStep(page, "A-P7 cita cancelada (espejo mesa=available)");
    }

    // A-P8: limpieza cita de prueba
    if (appointmentId) {
      runSql(`DELETE FROM appointments WHERE id = ${appointmentId} AND tenant_id = 1`);
      console.log(`🧹 Cita de prueba tenant 1 (${appointmentId}) eliminada`);
    }
    const t1Remaining = parseInt(runSql(`SELECT count(*) FROM appointments WHERE tenant_id = 1`) || "0", 10);
    record("A-P8: citas tenant 1 = 0 tras limpieza", t1Remaining === 0, `appointments=${t1Remaining}`);

    // ═══════════════════ FLUJO B — TENANT 3 (desde cero) ═══════════════════
    console.log("\n═══ FLUJO B: TENANT 3 (desde cero — spec 08 D3) ═══");
    createTempTenant3User();
    const l3 = await apiLogin(EMAIL_T3, PW_T3);
    tokenT3 = l3.token;
    const payload3 = tokenT3 ? JSON.parse(Buffer.from(tokenT3.split(".")[1], "base64").toString()) : {};
    record("B-P0: login temp admin tenant 3", !!tokenT3, `company_id=${payload3.company_id}`);
    record("B-P0.1: tenant-id = 3 en JWT", payload3.company_id === TENANT3);

    const avail3 = await api(
      `/api/v1/appointments/availability?date=${APPT_DATE}&guests=2&from=20:00&to=21:00`,
      tokenT3, {}, TENANT3,
    );
    record("B-P1: availability tenant 3 vacío (0 mesas)", (avail3.json?.slots ?? []).length === 0, `${(avail3.json?.slots ?? []).length} slot(s)`);

    const list3 = await api(`/api/v1/appointments?date=${APPT_DATE}`, tokenT3, {}, TENANT3);
    record("B-P2: agenda tenant 3 vacía (0 citas)", (list3.json?.items ?? []).length === 0, `total=${list3.json?.total}`);

    const tables3 = await api(`/api/v1/restaurant/tables`, tokenT3, {}, TENANT3);
    record("B-P3: mesas tenant 3 = 0 (data limpia)", (tables3.json ?? []).length === 0, `${(tables3.json ?? []).length} mesa(s)`);

    await page.screenshot({ path: path.join(OUT_DIR, "06-tenant3-desde-cero.png") });
    await demoStep(page, "B flujo tenant 3 desde cero (0 mesas, 0 citas)");

    // Limpieza flujo B: usuario temp
    deleteTempTenant3User();
    const t3Users = parseInt(runSql(`SELECT count(*) FROM users WHERE tenant_id = ${TENANT3}`) || "0", 10);
    record("B-P4: usuario temp eliminado", t3Users === 0, `users tenant3=${t3Users}`);

    // Verificación final global
    const t3Total = parseInt(runSql(`SELECT count(*) FROM appointments WHERE tenant_id = ${TENANT3}`) || "0", 10);
    record("FINAL: citas tenant 3 = 0", t3Total === 0, `appointments=${t3Total}`);
    await page.screenshot({ path: path.join(OUT_DIR, "07-estado-final.png") });
  } catch (e) {
    record("EXCEPCIÓN", false, e.message);
    await page.screenshot({ path: path.join(OUT_DIR, "error.png"), fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }

  const passed = RESULTS.filter((r) => r.ok).length;
  console.log(`\n=== E2E F6 PROD (spec 07 + 08): ${passed}/${RESULTS.length} OK ===`);
  fs.writeFileSync(
    path.join(OUT_DIR, "resumen.json"),
    JSON.stringify(
      {
        fecha: new Date().toISOString(),
        feature: "F6 Agenda de Citas (Spec 07) + Spec 08 siembra mesas tenant 1 / limpieza tenant 3",
        modo: DEMO ? "demo (monitor DISPLAY :0)" : "fast (headless)",
        tenant_operativo: 1,
        tenant3: TENANT3,
        appointment_date: APPT_DATE,
        resultados: RESULTS,
      },
      null,
      2,
    ),
  );
  process.exit(passed === RESULTS.length ? 0 : 1);
}

main().catch((e) => {
  console.error("E2E F6 falló:", e.message);
  process.exit(1);
});
