/**
 * E2E — Landing pública de delivery (Spec 03, Camino C).
 *
 * Corre contra PROD (https://www.ronsyserp.com), SIN autenticación.
 *
 * ⚠️ El test de checkout crea un pedido REAL (venta + kárdex + asiento).
 * Se usa nombre único `E2E-Landing-<ts>` y se CANCELA vía API en afterAll
 * (login admin + PATCH status=cancelled) — idempotente y sin basura en prod.
 *
 * Ejecución: npm run test:e2e:prod
 */
import { test, expect, type APIRequestContext } from "@playwright/test";

const LANDING = "/menu/el-segoviano";
const ADMIN = { email: "admin@elsegoviano.pe", password: "admin123" };

let createdTrackingCode: string | null = null;

async function cancelOrderByTracking(request: APIRequestContext, code: string) {
  const login = await request.post("https://www.ronsyserp.com/api/auth/login", {
    data: { email: ADMIN.email, password: ADMIN.password },
  });
  if (!login.ok()) return;
  const token = ((await login.json()) as { access_token: string }).access_token;
  const headers = { Authorization: `Bearer ${token}`, "X-Tenant-ID": "1" };
  const res = await request.get("https://www.ronsyserp.com/api/v1/delivery/orders", {
    headers,
  });
  if (!res.ok()) return;
  const orders = (await res.json()) as {
    id: number;
    tracking_code: string;
    status: string;
  }[];
  const order = orders.find((o) => o.tracking_code === code);
  if (order && !["delivered", "cancelled"].includes(order.status)) {
    await request.patch(
      `https://www.ronsyserp.com/api/v1/delivery/orders/${order.id}/status`,
      { headers, data: { status: "cancelled" } },
    );
  }
}

test.afterAll(async ({ request }) => {
  if (createdTrackingCode) {
    await cancelOrderByTracking(request, createdTrackingCode);
    console.log(`🧹 Pedido de prueba cancelado: ${createdTrackingCode}`);
  }
});

// ─── Tests ─────────────────────────────────────────────────────

test.describe("Landing delivery (pública)", () => {
  test("menú nocturno carga: horario, secciones y platos visibles", async ({ page }) => {
    await page.goto(LANDING);
    await expect(page.getByText(/19:00/).first()).toBeVisible({ timeout: 20_000 });
    // Al menos un plato agregable
    await expect(page.getByText("＋ Agregar al pedido").first()).toBeVisible();
    // Panel de carrito presente
    await expect(page.getByText("🧾 Tu pedido")).toBeVisible();
  });

  test("número Yape del negocio visible en el checkout", async ({ page }) => {
    await page.goto(LANDING);
    // El pago Yape es el default y muestra el número del tenant (D4)
    await expect(page.getByText(/Yapea al número/).first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("912057784")).toBeVisible();
  });

  test("agregar plato + elegir zona muestra fee y total estimado", async ({ page }) => {
    await page.goto(LANDING);
    await page.getByText("＋ Agregar al pedido").first().click();
    await expect(page.locator("text=/S\\/ \\d+\\.\\d{2}/").first()).toBeVisible();
    // Elegir Zona 1 (índice 1: el 0 es el placeholder "Selecciona tu zona")
    await page.locator("select").first().selectOption({ index: 1 });
    await expect(page.getByText("Delivery (Montenegro", { exact: false })).toBeVisible();
    await expect(page.getByText("Total estimado")).toBeVisible();
  });

  test("min_order de la zona se valida (aviso en el carrito)", async ({ page }) => {
    await page.goto(LANDING);
    // Agregar UN plato (subtotal < S/35 de la Zona 1 → aviso de mínimo)
    await page.getByText("＋ Agregar al pedido").first().click();
    await page.locator("select").first().selectOption({ index: 1 });
    await expect(page.getByText(/Pedido mínimo/)).toBeVisible();
  });
});

test.describe.serial("Checkout con UTM + tracking (crea y cancela pedido)", () => {
  test("checkout completo con UTM de campaña → código de seguimiento", async ({ page }) => {
    const ts = Date.now();
    await page.goto(
      `${LANDING}?utm_source=e2e&utm_medium=cpc&utm_campaign=e2e_landing_${ts}`,
    );
    // Ceviche Clásico (S/28) ×2 = S/56 → supera el mínimo de la Zona 1 (S/35).
    // El botón de la card (no el texto: el carrito también muestra el nombre).
    const cevicheCard = page.locator("button").filter({ hasText: "Ceviche Clásico" }).first();
    await cevicheCard.click();
    await cevicheCard.click();
    // Zona 1 (índice 1: el 0 es el placeholder)
    await page.locator("select").first().selectOption({ index: 1 });
    // Formulario
    await page.getByPlaceholder("Tu nombre").fill(`E2E-Landing-${ts}`);
    await page.getByPlaceholder("999 888 777").fill("999888777");
    await page.getByPlaceholder(/Calle, número/).fill("Av. E2E 123, SJL");
    await page.getByPlaceholder(/8 caracteres/).fill("E2E12345");
    // Confirmar
    await page.getByRole("button", { name: /Confirmar pedido/ }).click();
    await expect(page.getByText("¡Pedido confirmado!")).toBeVisible({ timeout: 30_000 });
    // Selector robusto: el código DLV- (evita CSS type-selector sin punto)
    const code = (await page.getByText(/^DLV-[0-9a-f]+$/).first().textContent())?.trim() ?? "";
    expect(code).toMatch(/^DLV-/);
    createdTrackingCode = code;
    // Totales mostrados
    await expect(page.getByText(/Tiempo estimado/)).toBeVisible();
  });

  test("tracking por código muestra la línea de tiempo", async ({ page }) => {
    expect(createdTrackingCode).not.toBeNull();
    await page.goto(LANDING);
    await page.getByRole("button", { name: /Seguir pedido/ }).click();
    await page.getByPlaceholder("Código DLV-XXXX").fill(createdTrackingCode!);
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.getByText("Pedido recibido")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("En cocina")).toBeVisible();
  });
});
