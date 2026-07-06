/**
 * Auth token store — bridge entre AuthContext y api.ts.
 *
 * Evita dependencias circulares: AuthContext y api.ts pueden
 * acceder a los tokens y la función de refresh sin importarse mutuamente.
 *
 * @module services/authStore
 */

import type { AuthTokens } from "@/types/auth";

let tokens: AuthTokens | null = null;
let onRefresh: (() => Promise<string | null>) | null = null;
let onLogout: (() => void) | null = null;

export const authStore = {
  /** Guardar tokens en memoria (access token) y sessionStorage (refresh token) */
  setTokens(t: AuthTokens | null) {
    tokens = t;
    if (t) {
      sessionStorage.setItem("refresh_token", t.refreshToken);
    } else {
      sessionStorage.removeItem("refresh_token");
    }
  },

  /** Obtener access token actual */
  getAccessToken(): string | null {
    return tokens?.accessToken ?? null;
  },

  /** Obtener refresh token (memoria o sessionStorage) */
  getRefreshToken(): string | null {
    return tokens?.refreshToken ?? sessionStorage.getItem("refresh_token") ?? null;
  },

  /** Obtener company_id desde el access token JWT decodificado */
  getTenantId(): number | null {
    const token = tokens?.accessToken;
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.company_id ?? payload.sub ?? null;
    } catch {
      return null;
    }
  },

  /** Registrar callback de refresh (llamado por AuthContext) */
  setRefreshCallback(fn: () => Promise<string | null>) {
    onRefresh = fn;
  },

  /** Registrar callback de logout */
  setLogoutCallback(fn: () => void) {
    onLogout = fn;
  },

  /** Disparar refresh desde api.ts */
  async refresh(): Promise<string | null> {
    if (!onRefresh) return null;
    return onRefresh();
  },

  /** Disparar logout desde api.ts */
  triggerLogout() {
    onLogout?.();
  },
};
