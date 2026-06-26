/**
 * authFetch — Wrapper around fetch() that injects JWT + X-Tenant-ID.
 *
 * Usado por páginas de restaurante/ferretería que llaman APIs
 * directamente sin pasar por el interceptor de services/api.ts.
 *
 * @module services/authFetch
 */
import { authStore } from "./authStore";

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
  return fetch(url, { ...options, headers });
}
