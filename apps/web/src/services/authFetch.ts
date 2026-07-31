/**
 * authFetch — Wrapper around fetch() that injects JWT + X-Tenant-ID.
 *
 * Usado por páginas de restaurante/ferretería que llaman APIs
 * directamente sin pasar por el interceptor de services/api.ts.
 *
 * UX (Spec 01 v0.2, ajuste UI): ante 401 intenta auto-refresh con el
 * refresh_token (single-flight, mismo patrón que api.ts) y reintenta la
 * request original UNA vez. Si el refresh falla → logout/redirección.
 *
 * @module services/authFetch
 */
import { authStore } from "./authStore";

// ─── Refresh queue (evita race condition entre requests) ────
let refreshPromise: Promise<string | null> | null = null;

function getRefreshPromise(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = authStore.refresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

/** Rutas de auth NO se reintentan (evita loops en login/refresh) */
function shouldSkipRetry(url: string): boolean {
  return url.includes("/auth/");
}

export async function authFetch(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const token = authStore.getAccessToken();
  const tenantId = authStore.getTenantId();
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (tenantId) headers["X-Tenant-ID"] = String(tenantId);

  let res = await fetch(url, { ...options, headers });

  // ─── 401 → auto-refresh → reintento único ─────────────────
  if (res.status === 401 && !shouldSkipRetry(url)) {
    const newToken = await getRefreshPromise();

    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      const newTenantId = authStore.getTenantId();
      if (newTenantId) headers["X-Tenant-ID"] = String(newTenantId);
      res = await fetch(url, { ...options, headers });
    } else {
      authStore.triggerLogout();
      throw new Error("Sesión expirada. Vuelve a iniciar sesión.");
    }
  }

  return res;
}
