/**
 * LoginPage — Pantalla pública de inicio de sesión.
 *
 * Formulario centrado con email + password + validación
 * y manejo completo de estados (loading, error, 423, 429).
 * Sin AppShell — pantalla completa con diseño independiente.
 *
 * US-17: Página de Login
 *
 * @module pages/Login
 */

import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

interface FormErrors {
  email?: string;
  password?: string;
}

const MAP_ERROR: Record<number, string> = {
  401: "Email o contraseña inválidos",
  423: "Cuenta bloqueada temporalmente. Intente de nuevo más tarde.",
  429: "Demasiados intentos. Espere unos segundos.",
};

export function LoginPage() {
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryAfter, setRetryAfter] = useState(0);

  // Si ya autenticado, redirigir al dashboard
  if (isAuthenticated && !authLoading) {
    return <Navigate to="/" replace />;
  }

  // Si está cargando sesión restaurada
  if (authLoading) {
    return (
      <LoginShell>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          <p className="text-white/60 text-sm">Restaurando sesión...</p>
        </div>
      </LoginShell>
    );
  }

  const validate = (): boolean => {
    const e: FormErrors = {};
    if (!email.trim()) e.email = "El email es requerido";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "Ingrese un email válido";
    if (!password) e.password = "La contraseña es requerida";
    else if (password.length < 6) e.password = "Mínimo 6 caracteres";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await login(email, password);
      // Redirigir a la ruta original o dashboard
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al iniciar sesión";
      // Intentar extraer status code del mensaje
      const statusMatch = msg.match(/^(\d{3})/);
      if (statusMatch) {
        const code = parseInt(statusMatch[1]);
        setServerError(MAP_ERROR[code] ?? msg);
        if (code === 429) {
          setRetryAfter(30);
          const timer = setInterval(() => {
            setRetryAfter((prev) => {
              if (prev <= 1) { clearInterval(timer); return 0; }
              return prev - 1;
            });
          }, 1000);
        }
      } else {
        setServerError(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <LoginShell>
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <span className="text-5xl">🐟</span>
          <h1 className="mt-3 text-2xl font-bold text-white">IaaS-RonSys</h1>
          <p className="mt-1 text-white/50 text-sm">Iniciar Sesión</p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/10 p-6 shadow-2xl">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setErrors((p) => ({ ...p, email: undefined })); }}
                onBlur={() => {
                  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                    setErrors((p) => ({ ...p, email: "Ingrese un email válido" }));
                  }
                }}
                placeholder="admin@segoviano.pe"
                className={`w-full px-3 py-2.5 rounded-lg bg-white/5 border text-white text-sm
                  placeholder:text-white/30 outline-none transition-colors
                  ${errors.email ? "border-red-400 focus:ring-red-400/30" : "border-white/10 focus:ring-white/20"}
                  focus:ring-2`}
                disabled={isSubmitting}
                autoComplete="email"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-300">{errors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: undefined })); }}
                  placeholder="••••••••"
                  className={`w-full px-3 py-2.5 pr-10 rounded-lg bg-white/5 border text-white text-sm
                    placeholder:text-white/30 outline-none transition-colors
                    ${errors.password ? "border-red-400 focus:ring-red-400/30" : "border-white/10 focus:ring-white/20"}
                    focus:ring-2`}
                  disabled={isSubmitting}
                  autoComplete="current-password"
                  onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(e); }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? "🙈" : "👁"}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-300">{errors.password}</p>
              )}
            </div>

            {/* Server error */}
            {serverError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                {serverError}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting || retryAfter > 0}
              className="w-full py-2.5 rounded-lg font-medium text-sm transition-all
                bg-white text-slate-800 hover:bg-white/90
                disabled:opacity-50 disabled:cursor-not-allowed
                focus:outline-none focus:ring-2 focus:ring-white/30"
            >
              {isSubmitting ? (
                <span className="inline-flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                  Ingresando...
                </span>
              ) : retryAfter > 0 ? (
                `Esperar ${retryAfter}s`
              ) : (
                "Iniciar Sesión"
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-white/30 text-xs">
          IaaS-RonSys v0.1 · El Segoviano
        </p>
      </div>
    </LoginShell>
  );
}

/** Shell centrado para la pantalla de login (sin AppShell) */
function LoginShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      {children}
    </div>
  );
}
