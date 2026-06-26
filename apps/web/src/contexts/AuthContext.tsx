/**
 * AuthContext — Estado global de autenticación.
 *
 * Provee user, tenant, login/logout/refreshSession a toda la app
 * vía React Context API. Los tokens se almacenan en memoria (access)
 * y sessionStorage (refresh). Al montar, intenta restaurar sesión
 * automáticamente si hay refresh_token en sessionStorage.
 *
 * US-16: AuthContext — Estado Global de Autenticación
 *
 * @module contexts/AuthContext
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authStore } from "@/services/authStore";
import type { User, Tenant, AuthContextType, LoginResponse, RefreshResponse } from "@/types/auth";

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ─── helpers ───────────────────────────────────────────

  const deriveTenant = useCallback((u: User) => {
    const t: Tenant = { id: u.company_id ?? 0 };
    setTenant(t);
  }, []);

  // ─── refreshSession ────────────────────────────────────

  const refreshSession = useCallback(async (): Promise<string | null> => {
    const refreshToken = authStore.getRefreshToken();
    if (!refreshToken) return null;

    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) throw new Error("Refresh failed");

      const data: RefreshResponse = await res.json();
      authStore.setTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });

      // Decode user from access token
      const payload = JSON.parse(atob(data.access_token.split(".")[1]));
      const u: User = {
        id: payload.sub,
        email: payload.email ?? "",
        full_name: payload.name ?? "",
        role: payload.role ?? "viewer",
        company_id: payload.company_id ?? null,
      };
      setUser(u);
      deriveTenant(u);
      return data.access_token;
    } catch {
      authStore.setTokens(null);
      return null;
    }
  }, [deriveTenant]);

  // ─── login ─────────────────────────────────────────────

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const detail = errorData.detail ?? "Error al iniciar sesión";
        throw new Error(detail);
      }

      const data: LoginResponse = await res.json();
      authStore.setTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
      setUser(data.user);
      deriveTenant(data.user);
    },
    [deriveTenant],
  );

  // ─── logout ────────────────────────────────────────────

  const logout = useCallback(async () => {
    const refreshToken = authStore.getRefreshToken();
    if (refreshToken) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // Falla silenciosa — el token expirará eventualmente
      }
    }
    authStore.setTokens(null);
    setUser(null);
    setTenant(null);
  }, []);

  // ─── Efecto: restaurar sesión al montar ───── 0 ──────────

  useEffect(() => {
    (async () => {
      try {
        await refreshSession();
      } catch {
        // Sin sesión válida — welcome screen
      } finally {
        setIsLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── context value ─────────────────────────────────────

  const value: AuthContextType = {
    user,
    tenant,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider");
  }
  return ctx;
}
