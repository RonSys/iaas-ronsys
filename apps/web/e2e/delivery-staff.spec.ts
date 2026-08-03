/**
 * E2E — Panel staff Delivery Nocturno (Spec 03, Camino C).
 *
 * Corre contra PROD con sesión real. La app guarda refresh_token en
 * sessionStorage (no lo captura storageState de Playwright), por eso la
 * fixture `staffPage` hace login REAL una sola vez vía API e inyecta el
 * token con addInitScript → AuthContext restaura la sesión en cada test
 * (sin UI login repetido → sin rate limit de 5/min).
 *
 * Datos de prueba idempotentes: nombres únicos `E2E-<ts>` y se eliminan
 * al final de cada test (zona y campaña), sin dejar basura en prod.
 */
import { test as base, expect, type Page } from "@playwright/test";

const ADMIN = { email: "admin@elsegoviano.pe", password: "admin123" };
const API = "https://www.ronsyserp.com/api";

let cachedRefreshToken: string | null = null;

const ts = Date.now();
const ZONE_NAME = `E2E Zona ${ts}`;
const CAMPAIGN_NAME = `E2E Campaña ${ts}`;

const staffTest = base.extend<{ staffPage: Page }>({
  staffPage: async ({ page, request }, use) => {
    // Si no tenemos token, login real vía API (1 sola vez por corrida).
    if (!cachedRefreshToken) {
      const res = await request.post(`${API}/auth/login`, {
        data: { email: ADMIN.email, password: ADMIN.password },
      });
      expect(res.ok()).toBeTruthy();
      const data = (await res.json()) as {
        refresh_token?: string;
        refreshToken?: string;
      };
      cachedRefreshToken = data.refresh_token ?? data.refreshToken ?? "";
      expect(cachedRefreshToken).toBeTruthy();
    }

    // Inyectar el token ANTES de que carguen los scripts de la app.
    await page.addInitScript(
      (t) => sessionStorage.setItem("refresh_token", t),
      cachedRefreshToken,
    );

    // Navegar al panel y esperar a que asiente (panel OK o login)
    await page.goto("/restaurante/delivery");
    const panelHeading = page.getByText("🛵 Delivery Nocturno");
    const loginField = page.getByPlaceholder("admin@segoviano.pe");
    await Promise.race([
      panelHeading.waitFor({ state: "visible", timeout: 25_000 }),
      loginField.waitFor({ state: "visible", timeout: 25_000 }),
    ]).catch(() => {});

    // Si cayó al login → UI login (fallback; ocurre solo si el restore falla)
    if (await loginField.isVisible().catch(() => false)) {
      await loginField.fill(ADMIN.email);
      await page.getByPlaceholder("••••••••").fill(ADMIN.password);
      await page.getByRole("button", { name: "Iniciar Sesión" }).click();
      await panelHeading.waitFor({ state: "visible", timeout: 25_000 });
    }

    // Guardar el refresh token ROTADO (single-use) para el siguiente test.
    const rotated = await page
      .evaluate(() => sessionStorage.getItem("refresh_token"))
      .catch(() => null);
    if (rotated) cachedRefreshToken = rotated;

    await use(page);
  },
});

staffTest.describe("Panel Delivery Nocturno (staff)", () => {
  staffTest("panel accesible con pestañas visibles", async ({ staffPage }) => {
    await expect(staffPage.getByText("🛵 Delivery Nocturno")).toBeVisible({ timeout: 25_000 });
    for (const tab of ["📦 Pedidos", "🗺️ Zonas", "🛵 Repartidores", "📢 Campañas", "📈 Métricas"]) {
      await expect(staffPage.getByRole("button", { name: tab })).toBeVisible();
    }
  });

  staffTest("kanban de pedidos muestra columnas de la máquina de estados", async ({ staffPage }) => {
    for (const col of ["Recibido", "En cocina", "Listo", "En ruta", "Entregado", "Cancelado"]) {
      await expect(staffPage.getByText(col).first()).toBeVisible({ timeout: 25_000 });
    }
  });

  staffTest("CRUD zona de prueba (crear → editar → eliminar)", async ({ staffPage }) => {
    await staffPage.getByRole("button", { name: "🗺️ Zonas" }).click();

    // Crear
    await staffPage.getByRole("button", { name: "+ Nueva Zona" }).click();
    await staffPage.getByPlaceholder("Nombre (ej: Zona 1 — Montenegro)").fill(ZONE_NAME);
    await staffPage.getByPlaceholder("Distritos (coma separada)").fill("E2E Distrito A, E2E Distrito B");
    await staffPage.getByPlaceholder("Fee S/").fill("7.50");
    await staffPage.getByPlaceholder("Pedido mínimo S/").fill("40");
    await staffPage.getByPlaceholder("ETA minutos").fill("50");
    await staffPage.getByRole("button", { name: "Guardar" }).click();
    await expect(staffPage.getByText(ZONE_NAME)).toBeVisible({ timeout: 20_000 });
    await expect(staffPage.getByText("S/ 7.50")).toBeVisible();

    // Operar SIEMPRE sobre la fila de la zona de prueba (hay zonas reales en prod)
    const row = staffPage.locator("tr").filter({ hasText: ZONE_NAME });

    // Editar (cambiar fee)
    await row.getByRole("button", { name: "Editar" }).click();
    await staffPage.getByPlaceholder("Fee S/").fill("8.00");
    await staffPage.getByRole("button", { name: "Guardar" }).click();
    await expect(row.getByText("S/ 8.00")).toBeVisible();

    // Eliminar
    await row.getByRole("button", { name: "Eliminar" }).click();
    await expect(staffPage.getByText(ZONE_NAME)).toHaveCount(0);
  });

  staffTest("CRUD campaña de prueba con UTM (crear → pausar → eliminar)", async ({ staffPage }) => {
    await staffPage.getByRole("button", { name: "📢 Campañas" }).click();

    await staffPage.getByPlaceholder("Nombre de campaña *").fill(CAMPAIGN_NAME);
    await staffPage.getByPlaceholder("utm_source (meta)").fill("e2e");
    await staffPage.getByPlaceholder("utm_campaign").fill(`e2e_${ts}`);
    await staffPage.getByPlaceholder("Presupuesto S/").fill("100");
    await staffPage.getByPlaceholder("Gasto S/").fill("20");
    await staffPage.getByRole("button", { name: "+ Crear" }).click();

    // Link UTM autogenerado visible
    await expect(staffPage.getByText("🔗 Link para anuncios")).toBeVisible({ timeout: 20_000 });
    await expect(staffPage.getByText(/utm_source=e2e/)).toBeVisible();
    await expect(staffPage.getByText(CAMPAIGN_NAME)).toBeVisible();

    // Operar SIEMPRE sobre la fila de la campaña de prueba (hay campañas reales en prod)
    const row = staffPage.locator("tr").filter({ hasText: CAMPAIGN_NAME });

    // Pausar → Activar
    await row.getByRole("button", { name: "Pausar" }).click();
    await expect(row.getByRole("button", { name: "Activar" })).toBeVisible({ timeout: 15_000 });
    await row.getByRole("button", { name: "Activar" }).click();

    // Eliminar
    await row.getByRole("button", { name: "Eliminar" }).click();
    await expect(staffPage.getByText(CAMPAIGN_NAME)).toHaveCount(0);
  });

  staffTest("métricas: tarjetas y tabla ROAS por campaña", async ({ staffPage }) => {
    await staffPage.getByRole("button", { name: "📈 Métricas" }).click();
    for (const label of ["Pedidos entregados", "GMV (ventas)", "Fee delivery", "Cancelados"]) {
      await expect(staffPage.getByText(label)).toBeVisible({ timeout: 25_000 });
    }
    await expect(staffPage.getByText("📢 Rendimiento por campaña")).toBeVisible();
  });
});
