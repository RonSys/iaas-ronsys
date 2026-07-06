/**
 * Auth types — User, Tenant, AuthContext interface.
 *
 * @module types/auth
 */

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "superadmin" | "admin" | "manager" | "operator" | "viewer";
  company_id: number | null;
}

export interface Tenant {
  id: number;
  name?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
}

export interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<string | null>;
}
