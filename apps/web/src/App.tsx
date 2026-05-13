/**
 * App — Componente raíz de IaaS-RonSys.
 *
 * Responsabilidades:
 * - Cargar la paleta de colores vía usePalette() antes de renderizar
 * - Configurar el router con code-splitting (React.lazy + Suspense)
 * - Envolver cada ruta en AppShell (layout común)
 * - Proteger rutas con PrivateRoute (auth requerido)
 * - Exponer /login como ruta pública (sin AppShell ni auth)
 *
 * La paleta se aplica como CSS custom properties en :root y Tailwind
 * las consume vía theme.extend.colors.brand.*
 *
 * @module App
 */
import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { PrivateRoute } from "@/components/auth/PrivateRoute";
import { usePalette } from "@/hooks/usePalette";
import { AppShell } from "@/components/layout/AppShell";

// ─── Code-split: cada página es un chunk separado ───
const Dashboard = lazy(() =>
  import("@/pages/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const SetupWizard = lazy(() =>
  import("@/pages/SetupWizard").then((m) => ({ default: m.SetupWizard })),
);
const Simulator = lazy(() =>
  import("@/pages/Simulator").then((m) => ({ default: m.Simulator })),
);
const Reports = lazy(() =>
  import("@/pages/Reports").then((m) => ({ default: m.Reports })),
);
const KardexPage = lazy(() =>
  import("@/pages/Kardex").then((m) => ({ default: m.KardexPage })),
);
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const LoginPage = lazy(() =>
  import("@/pages/Login").then((m) => ({ default: m.LoginPage })),
);
// ─── Nuevas páginas Fase 1 + Fase 2 ───
const CashflowPage = lazy(() =>
  import("@/pages/Cashflow").then((m) => ({ default: m.CashflowPage })),
);
const PosPage = lazy(() =>
  import("@/pages/Pos").then((m) => ({ default: m.PosPage })),
);
const SalesNewPage = lazy(() =>
  import("@/pages/SalesNew").then((m) => ({ default: m.SalesNewPage })),
);
const SalesListPage = lazy(() =>
  import("@/pages/SalesListPage").then((m) => ({ default: m.SalesListPage })),
);

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-3 text-brand-text-secondary text-sm">Cargando página...</p>
      </div>
    </div>
  );
}

function SuspendedPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <AppShell title={title}>
      <Suspense fallback={<PageLoader />}>{children}</Suspense>
    </AppShell>
  );
}

function AppRoutes() {
  const { loading: paletteLoading } = usePalette();

  if (paletteLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background">
        <div className="text-center animate-fade-in">
          <span className="text-4xl">🐟</span>
          <p className="mt-3 text-brand-text-secondary text-sm">Cargando...</p>
          <div className="mt-4 w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* ─── Ruta pública (sin AppShell, sin auth) ─── */}
        <Route
          path="/login"
          element={
            <Suspense fallback={<PageLoader />}>
              <LoginPage />
            </Suspense>
          }
        />

        {/* ─── Rutas protegidas ─── */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <SuspendedPage title="Dashboard">
                <Dashboard />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/setup"
          element={
            <PrivateRoute>
              <SuspendedPage title="Configuración Inicial">
                <SetupWizard />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/simulador"
          element={
            <PrivateRoute>
              <SuspendedPage title="Simulador">
                <Simulator />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/reportes"
          element={
            <PrivateRoute>
              <SuspendedPage title="Reportes">
                <Reports />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/kardex"
          element={
            <PrivateRoute>
              <SuspendedPage title="Kárdex">
                <KardexPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <PrivateRoute allowedRoles={["admin", "manager"]}>
              <SuspendedPage title="Ajustes">
                <Settings />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ─── Fase 1: Cashflow ─── */}
        <Route
          path="/cashflow"
          element={
            <PrivateRoute>
              <SuspendedPage title="Flujo de Caja">
                <CashflowPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ─── Fase 2: POS ─── */}
        <Route
          path="/caja"
          element={
            <PrivateRoute allowedRoles={["admin", "manager", "operator"]}>
              <SuspendedPage title="Caja">
                <PosPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/ventas/nueva"
          element={
            <PrivateRoute allowedRoles={["admin", "manager", "operator"]}>
              <SuspendedPage title="Nueva Venta">
                <SalesNewPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/ventas"
          element={
            <PrivateRoute>
              <SuspendedPage title="Ventas">
                <SalesListPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
