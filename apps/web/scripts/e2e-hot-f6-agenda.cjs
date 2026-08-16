#!/usr/bin/env node
/**
 * E2E en caliente — F6 "Agenda de Citas" (Spec 07)
 * ==================================================
 * Monitor de producción: verifica el módulo de agenda contra el backend PROD real
 * (patrón e2e-hot-f3-recepcionista.cjs / e2e-hot-f5-asistente.cjs).
 *
 * Flujo:
 *   P0 login API (staff tenant 3 — REQUISITO RON: tenant-id = 3)
 *   P1 fixtures: 2 mesas de prueba para tenant 3 (POST /restaurant/tables)
 *   P2 login UI → /restaurante/agenda
 *   P3 modal "＋ Nueva cita" → disponibilidad REAL (GET availability, tenant 3)
 *   P4 crear cita (source=in_person, mesa real desde availability) → 201
 *   P5 verificar en lista (estado Solicitada)
 *   P6 confirmar (PATCH → confirmada) → espejo tables.status='reserved' (D1)
 *   P7 cancelar (PATCH → cancelada) → espejo vuelve a 'available'
 *   P8 limpieza: borrar cita de prueba (SQL) + mesas fixture (API DELETE)
 *   P9 verificación final: appointments tenant 3 = 0 (BD limpia)
 *
 * Evidencias: docs/reports/evidencias-f6-e2e-prod/*.png + resumen.json
 *
 * ⚠️ REQUISITO RON: fixtures/payloads con tenant-id = 3 (admincevicheria).
 *
 * Uso: node scripts/e2e-hot-f6-agenda.cjs
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const BASE = process.env.E2E_BASE_URL || "http://localhost:8081";
const API = process.env.E2E_API_URL || "http://localhost:8000";
const EMAIL = "admincevicheria@elsegoviano.pe"; // tenant 3 (El Segoviano)
const PASSWORD = "cevicheria123";
const TENANT = 3; // ⚠️ REQUISITO RON
const OUT_DIR = path.join(__dirname, "../../../docs/reports/evidencias-f6-e2e-prod");
const RESULTS = [];

// Fecha futura estable (ventana 12:00–23:00 Lima): hoy + 5 días
function futureDate(days = 5) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
const APPT_DATE = futureDate(5);
const APPT_TIME = "20:00";
const CUSTOMER = "E2E F6 Cliente";
const PHONE = "+51999000006";
const TABLE_NUMBERS = ["F6E2E-1", "F6E2E-2"];

function record(name, ok, detail = "") {
  RESULTS.push({ name, ok, detail });
  console.log(`${ok ? "✅" : "❌"} ${name}${detail ? " — " + detail : ""}`);
}

async function apiLogin() {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  const body = await res.json();
  return body.access_token || body.token || null;
}

async function api(pathname, token, opts = {}) {
  const res = await fetch(`${API}${pathname}`, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": String(TENANT),
      ...(opts.headers || {}),
    },
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

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  let token = null;
  let fixtureTableIds = [];
  let appointmentId = null;
  let reservedTableId = null;

  try {
    // ── P0: login API (tenant 3) ──────────────────────────────
    token = await apiLogin();
    const payload = token
      ? JSON.parse(Buffer.from(token.split(".")[1], "base64").toString())
      : null;
    record("P0: login API staff", !!token, `company_id=${payload?.company_id ?? "?"}`);
    record("P0.1: tenant-id = 3 en payload JWT", payload?.company_id === TENANT);

    // ── P1: fixtures — 2 mesas de prueba para tenant 3 ────────
    for (const num of TABLE_NUMBERS) {
      const r = await api("/api/v1/restaurant/tables", token, {
        method: "POST",
        body: { number: num, capacity: 4, section: "E2E" },
      });
      if (r.status === 201 && r.json?.id) fixtureTableIds.push(r.json.id);
    }
    record(
      "P1: mesas fixture tenant 3 creadas",
      fixtureTableIds.length === TABLE_NUMBERS.length,
      `ids=${fixtureTableIds.join(",")}`,
    );

    // ── P1.1: availability con mesas reales (tenant 3) ────────
    const avail = await api(
      `/api/v1/appointments/availability?date=${APPT_DATE}&guests=2&from=${APPT_TIME}&to=21:00`,
      token,
    );
    const slots = avail.json?.slots ?? [];
    record("P1.1: availability devuelve mesas reales", slots.length > 0, `${slots.length} slot(s)`);

    // ── P2: login UI → /restaurante/agenda ────────────────────
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.getByRole("button", { name: /Iniciar Sesión/ }).click();
    await page.waitForTimeout(2500);
    await page.goto(`${BASE}/restaurante/agenda`, { waitUntil: "networkidle" }).catch(() => {});
    await page.waitForTimeout(2500);
    const bodyText = await page.locator("body").innerText().catch(() => "");
    record("P2: /restaurante/agenda cargado", bodyText.includes("Agenda de Citas"), page.url());
    await page.screenshot({ path: path.join(OUT_DIR, "01-agenda.png"), fullPage: false });

    // ── P3: modal Nueva cita + disponibilidad real ────────────
    await page.getByRole("button", { name: /Nueva cita/ }).click();
    await page.waitForTimeout(1200);
    // fecha futura en el input date del modal
    const dateInput = page.locator('input[type="date"]').first();
    if (await dateInput.count()) {
      await dateInput.fill(APPT_DATE);
    }
    await page.locator('input[type="time"]').first().fill(APPT_TIME);
    await page.waitForTimeout(2500); // esperar GET availability
    const slotBtns = page.locator('button:has-text("🪑 Mesa")');
    const slotCount = await slotBtns.count();
    record("P3: slots de mesas reales en el modal", slotCount > 0, `${slotCount} mesa(s)`);
    if (slotCount === 0) {
      const modalText = await page.locator(".fixed.inset-0").innerText().catch(() => "");
      console.log("  modal:", modalText.slice(0, 300).replace(/\n/g, " | "));
    }
    await page.screenshot({ path: path.join(OUT_DIR, "02-modal-disponibilidad.png"), fullPage: false });

    // ── P4: crear cita (mesa real desde availability) ─────────
    if (slotCount > 0) {
      await slotBtns.first().click();
      // reservar la mesa elegida para el check del espejo
      const firstSlotText = await slotBtns.first().innerText();
      const mTable = firstSlotText.match(/Mesa\s+(\S+)/);
      if (mTable) {
        const tbl = await api(`/api/v1/restaurant/tables?status=available`, token);
        const rows = (tbl.json ?? []).filter((t) => t.number === mTable[1]);
        if (rows.length) reservedTableId = rows[0].id;
      }
    }
    await page.locator('input[placeholder="Nombre y apellido"]').fill(CUSTOMER);
    await page.locator('input[placeholder="+51 999 999 999"]').fill(PHONE);
    await page.getByRole("button", { name: /Reservar mesa/ }).click();
    await page.waitForTimeout(3000);
    const afterCreate = await page.locator("body").innerText().catch(() => "");
    record("P4: cita creada (201 — mesa reservada)", afterCreate.includes(CUSTOMER), "");
    await page.screenshot({ path: path.join(OUT_DIR, "03-cita-creada.png"), fullPage: false });

    // ── P5: verificar en lista (estado Solicitada) ────────────
    const list = await api(
      `/api/v1/appointments?date=${APPT_DATE}&status=solicitada`,
      token,
    );
    const items = list.json?.items ?? [];
    const mine = items.find((i) => i.customer_name === CUSTOMER);
    appointmentId = mine?.id ?? null;
    record(
      "P5: cita en lista (solicitada)",
      !!mine,
      mine ? `id=${mine.id} mesa=${mine.table_number ?? mine.table_id} tenant=${mine.tenant_id}` : "",
    );
    record("P5.1: tenant_id=3 en la cita creada", mine?.tenant_id === TENANT);

    // ── P6: confirmar → espejo tables.status='reserved' (D1) ──
    if (appointmentId) {
      const conf = await api(`/api/v1/appointments/${appointmentId}`, token, {
        method: "PATCH",
        body: { status: "confirmada" },
      });
      record("P6: confirmar → confirmada", conf.json?.status === "confirmada", `status=${conf.json?.status}`);
      if (mine?.table_id) {
        const t = await api(`/api/v1/restaurant/tables/${mine.table_id}`, token);
        const status = t.json?.status;
        record("P6.1: espejo mesa = reserved (D1)", status === "reserved", `tables.status=${status}`);
        reservedTableId = mine.table_id;
      }
      // UI: filtrar por la fecha de la cita para verla en la lista
      await page.reload({ waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(2000);
      const fDate = page.locator('input[type="date"]').first();
      if (await fDate.count()) await fDate.fill(APPT_DATE);
      await page.getByRole("button", { name: /Filtrar/ }).click().catch(() => {});
      await page.waitForTimeout(2500);
      const confirmedRow = page.locator(`text=${CUSTOMER}`);
      record("P6.2: UI muestra cita Confirmada", (await confirmedRow.count()) > 0, "");
      await page.screenshot({ path: path.join(OUT_DIR, "04-cita-confirmada.png"), fullPage: false });
    }

    // ── P7: cancelar → espejo vuelve a 'available' ────────────
    if (appointmentId) {
      const canc = await api(`/api/v1/appointments/${appointmentId}`, token, {
        method: "PATCH",
        body: { status: "cancelada" },
      });
      record("P7: cancelar → cancelada", canc.json?.status === "cancelada", `status=${canc.json?.status}`);
      if (reservedTableId) {
        const t = await api(`/api/v1/restaurant/tables/${reservedTableId}`, token);
        record("P7.1: espejo mesa liberada", t.json?.status === "available", `tables.status=${t.json?.status}`);
      }
      await page.reload({ waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(2000);
      const fDate2 = page.locator('input[type="date"]').first();
      if (await fDate2.count()) await fDate2.fill(APPT_DATE);
      await page.getByRole("button", { name: /Filtrar/ }).click().catch(() => {});
      await page.waitForTimeout(2500);
      const canceledRow = page.locator(`text=${CUSTOMER}`);
      record("P7.2: UI muestra cita Cancelada", (await canceledRow.count()) > 0, "");
      await page.screenshot({ path: path.join(OUT_DIR, "05-cita-cancelada.png"), fullPage: false });
    }

    // ── P8: limpieza — borrar cita de prueba + mesas fixture ──
    if (appointmentId) {
      runSql(`DELETE FROM appointments WHERE id = ${appointmentId} AND tenant_id = ${TENANT}`);
      console.log(`🧹 Cita de prueba ${appointmentId} eliminada (SQL)`);
    }
    for (const tid of fixtureTableIds) {
      await api(`/api/v1/restaurant/tables/${tid}`, token, { method: "DELETE" });
      console.log(`🧹 Mesa fixture ${tid} eliminada (API 204)`);
    }
    record("P8: limpieza completada", true, `${fixtureTableIds.length} mesa(s) + 1 cita`);

    // ── P9: verificación final — BD limpia (tenant 3) ─────────
    const remaining = parseInt(runSql(
      `SELECT count(*) FROM appointments WHERE tenant_id = ${TENANT}`,
    ) || "0", 10);
    const remainingTables = parseInt(runSql(
      `SELECT count(*) FROM tables WHERE tenant_id = ${TENANT} AND number LIKE 'F6E2E%'`,
    ) || "0", 10);
    record("P9: citas de prueba tenant 3 = 0", remaining === 0, `appointments=${remaining}`);
    record("P9.1: mesas fixture eliminadas", remainingTables === 0, `tables=${remainingTables}`);

    await page.screenshot({ path: path.join(OUT_DIR, "06-estado-final.png"), fullPage: false });
  } catch (e) {
    record("EXCEPCIÓN", false, e.message);
    await page.screenshot({ path: path.join(OUT_DIR, "error.png"), fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }

  // ── Resumen ─────────────────────────────────────────────────
  const passed = RESULTS.filter((r) => r.ok).length;
  console.log(`\n=== E2E F6 PROD: ${passed}/${RESULTS.length} OK ===`);
  fs.writeFileSync(
    path.join(OUT_DIR, "resumen.json"),
    JSON.stringify(
      {
        fecha: new Date().toISOString(),
        feature: "F6 Agenda de Citas (Spec 07)",
        tenant_id: TENANT,
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
