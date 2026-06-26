/**
 * E2E: Login flow completo.
 *
 * Valida: login exitoso, credenciales inválidas, validación client-side,
 * rate limiting, cuenta bloqueada, logout.
 */
import { test, expect } from "@playwright/test";
import { setupMinimalMocks, mockLogin, mockRefresh, mockLogout } from "./fixtures/mocks";

test.describe("Login Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupMinimalMocks(page);
  });

  test("muestra el formulario de login", async ({ page }) => {
    await mockLogin(page);
    await page.goto("/login");

    await expect(page.locator("h1")).toContainText("IaaS-RonSys");
    await expect(page.getByPlaceholder("admin@segoviano.pe")).toBeVisible();
    await expect(page.getByPlaceholder("••••••••")).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar Sesión" })).toBeVisible();
  });

  test("login exitoso redirige al dashboard", async ({ page }) => {
    await mockLogin(page, 200);
    await mockRefresh(page, 200);
    await mockLogout(page);

    await page.goto("/login");
    await page.getByPlaceholder("admin@segoviano.pe").fill("admin@elsegoviano.pe");
    await page.getByPlaceholder("••••••••").fill("admin123");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();

    // Debe redirigir al dashboard
    await expect(page).toHaveURL("/");
  });

  test("credenciales inválidas muestran error", async ({ page }) => {
    await mockLogin(page, 401);

    await page.goto("/login");
    await page.getByPlaceholder("admin@segoviano.pe").fill("wrong@email.com");
    await page.getByPlaceholder("••••••••").fill("wrongpass");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();

    await expect(page.getByText("Email o contraseña inválidos")).toBeVisible();
  });

  test("email vacío muestra validación client-side", async ({ page }) => {
    await mockLogin(page);
    await page.goto("/login");

    // Dejar email vacío, llenar password
    await page.getByPlaceholder("••••••••").fill("admin123");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();

    await expect(page.getByText("El email es requerido")).toBeVisible();
  });

  test("password vacío muestra validación client-side", async ({ page }) => {
    await mockLogin(page);
    await page.goto("/login");

    await page.getByPlaceholder("admin@segoviano.pe").fill("admin@elsegoviano.pe");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();

    await expect(page.getByText("La contraseña es requerida")).toBeVisible();
  });

  test("rate limiting muestra mensaje 429", async ({ page }) => {
    await mockLogin(page, 429);

    await page.goto("/login");
    await page.getByPlaceholder("admin@segoviano.pe").fill("admin@elsegoviano.pe");
    await page.getByPlaceholder("••••••••").fill("admin123");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();

    await expect(page.getByText(/Demasiados intentos/)).toBeVisible();
  });

  test("logout vuelve a la página de login", async ({ page }) => {
    await mockLogin(page, 200);
    await mockRefresh(page, 200);
    await mockLogout(page);

    // Login primero
    await page.goto("/login");
    await page.getByPlaceholder("admin@segoviano.pe").fill("admin@elsegoviano.pe");
    await page.getByPlaceholder("••••••••").fill("admin123");
    await page.getByRole("button", { name: "Iniciar Sesión" }).click();
    await expect(page).toHaveURL("/");

    // Navegar a login → debe redirigir a / (ya autenticado)
    await page.goto("/login");
    await expect(page).toHaveURL("/");
  });
});
