/**
 * App — Componente raíz de IaaS-RonSys.
 *
 * Responsabilidades:
 * - Cargar la paleta de colores vía usePalette() antes de renderizar
 * - Configurar el router con code-splitting (React.lazy + Suspense)
 * - Envolver cada ruta en AppShell (layout común)
 * - Proteger rutas con PrivateRoute (auth requerido)
 * - Exponer /login como ruta pública (sin AppShell ni auth)
 * - Redireccionar rutas antiguas a nuevas (HU-F0-012)
 *
 * La paleta se aplica como CSS custom properties en :root y Tailwind
 * las consume vía theme.extend.colors.brand.*
 *
 * @module App
 */
import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { PrivateRoute } from "@/components/auth/PrivateRoute";
import { usePalette } from "@/hooks/usePalette";
import { AppShell } from "@/components/layout/AppShell";

// ─── Code-split: cada página es un chunk separado ───

// Auth
const LoginPage = lazy(() =>
  import("@/pages/Login").then((m) => ({ default: m.LoginPage })),
);

// Investment (proyecto de inversión)
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

// Ventas
const PosPage = lazy(() =>
  import("@/pages/ventas/PosPage").then((m) => ({ default: m.PosPage })),
);
const SalesNewPage = lazy(() =>
  import("@/pages/ventas/SalesNewPage").then((m) => ({ default: m.SalesNewPage })),
);
const SalesListPage = lazy(() =>
  import("@/pages/ventas/SalesListPage").then((m) => ({ default: m.SalesListPage })),
);

// Restaurante
const TablesPage = lazy(() =>
  import("@/pages/restaurant/TablesPage").then((m) => ({ default: m.TablesPage })),
);
const MenuPage = lazy(() =>
  import("@/pages/restaurant/MenuPage").then((m) => ({ default: m.MenuPage })),
);
const KitchenOrdersPage = lazy(() =>
  import("@/pages/restaurant/KitchenOrdersPage").then((m) => ({ default: m.KitchenOrdersPage })),
);
const TakeAwayPage = lazy(() =>
  import("@/pages/restaurant/TakeAwayPage").then((m) => ({ default: m.TakeAwayPage })),
);
const PromotionsPage = lazy(() =>
  import("@/pages/restaurant/PromotionsPage").then((m) => ({ default: m.PromotionsPage })),
);

// Inventario
const KardexPage = lazy(() =>
  import("@/pages/inventario/KardexPage").then((m) => ({ default: m.KardexPage })),
);
const CategoriesPage = lazy(() =>
  import("@/pages/inventario/CategoriesPage").then((m) => ({ default: m.CategoriesPage })),
);

// Finanzas
const CashflowPage = lazy(() =>
  import("@/pages/finanzas/CashflowPage").then((m) => ({ default: m.CashflowPage })),
);

// Configuración
const Settings = lazy(() =>
  import("@/pages/config/SettingsPage").then((m) => ({ default: m.Settings })),
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
  title?: string;
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
        {/* ═══════════════════════════════════════════════════════
           RUTA PÚBLICA (sin AppShell, sin auth)
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/login"
          element={
            <Suspense fallback={<PageLoader />}>
              <LoginPage />
            </Suspense>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           REDIRECTS 301 — Rutas antiguas → nuevas (HU-F0-012)
           ═══════════════════════════════════════════════════════ */}
        <Route path="/kardex" element={<Navigate to="/inventario/kardex" replace />} />
        <Route path="/reportes" element={<Navigate to="/inversiones/reportes" replace />} />
        <Route path="/cashflow" element={<Navigate to="/finanzas/cashflow" replace />} />
        <Route path="/caja" element={<Navigate to="/ventas/pos" replace />} />
        <Route path="/ventas" element={<Navigate to="/ventas/historial" replace />} />
        <Route path="/settings" element={<Navigate to="/config/marca" replace />} />

        {/* ═══════════════════════════════════════════════════════
           🏗️ PROYECTO DE INVERSIÓN
           ═══════════════════════════════════════════════════════ */}
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
          path="/inversiones/reportes"
          element={
            <PrivateRoute>
              <SuspendedPage title="Reportes Financieros">
                <Reports />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           🧾 VENTAS
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/ventas/pos"
          element={
            <PrivateRoute allowedRoles={["admin", "manager", "operator"]}>
              <SuspendedPage title="Caja / POS">
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
          path="/ventas/historial"
          element={
            <PrivateRoute>
              <SuspendedPage title="Historial de Ventas">
                <SalesListPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           🍽️ RESTAURANTE
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/restaurante/mesas"
          element={
            <PrivateRoute>
              <SuspendedPage title="Mapa de Mesas">
                <TablesPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/restaurante/menu"
          element={
            <PrivateRoute>
              <SuspendedPage title="Menú">
                <MenuPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/restaurante/comandas"
          element={
            <PrivateRoute>
              <SuspendedPage title="Comandas">
                <KitchenOrdersPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/restaurante/takeaway"
          element={
            <PrivateRoute>
              <SuspendedPage title="Take Away">
                <TakeAwayPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/restaurante/promociones"
          element={
            <PrivateRoute>
              <SuspendedPage title="Promociones">
                <PromotionsPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           📦 INVENTARIO
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/inventario/kardex"
          element={
            <PrivateRoute>
              <SuspendedPage title="Kárdex">
                <KardexPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />
        <Route
          path="/inventario/categorias"
          element={
            <PrivateRoute>
              <SuspendedPage title="Categorías">
                <CategoriesPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           💰 FINANZAS
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/finanzas/cashflow"
          element={
            <PrivateRoute>
              <SuspendedPage title="Flujo de Caja">
                <CashflowPage />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           ⚙️ CONFIGURACIÓN
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="/config/marca"
          element={
            <PrivateRoute allowedRoles={["admin", "manager"]}>
              <SuspendedPage title="Marca / Branding">
                <Settings />
              </SuspendedPage>
            </PrivateRoute>
          }
        />

        {/* ═══════════════════════════════════════════════════════
           404 — Catch-all
           ═══════════════════════════════════════════════════════ */}
        <Route
          path="*"
          element={
            <PrivateRoute>
              <SuspendedPage title="404">
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <span className="text-6xl mb-4">🔍</span>
                  <h2 className="text-xl font-bold text-brand-text-primary mb-2">
                    Página no encontrada
                  </h2>
                  <p className="text-sm text-brand-text-secondary mb-6">
                    La ruta que buscas no existe o fue movida.
                  </p>
                  <a
                    href="/"
                    className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
                  >
                    Volver al Dashboard
                  </a>
                </div>
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
