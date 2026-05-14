/**
 * AppShell — Layout principal de la aplicación.
 *
 * Provee el sidebar jerárquico (desktop + mobile overlay), el área de
 * contenido principal y el footer. Todas las páginas se renderizan
 * dentro de este shell.
 *
 * HU-F0-011: Sidebar jerárquico con botón Salir siempre visible
 * - Botón "Cerrar Sesión" solo en el sidebar (no en modales — cliente confirmó)
 * - Sidebar colapsable por sección (persistencia en sessionStorage)
 * - Responsive: mobile con overlay + hamburguesa
 *
 * @param children - Contenido de la página
 */
import { useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

// Mapa de títulos por ruta
const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/setup": "Configuración Inicial",
  "/simulador": "Simulador",
  "/inversiones/reportes": "Reportes Financieros",
  "/ventas/pos": "Caja / POS",
  "/ventas/nueva": "Nueva Venta",
  "/ventas/historial": "Historial de Ventas",
  "/restaurante/mesas": "Mapa de Mesas",
  "/restaurante/menu": "Menú",
  "/restaurante/comandas": "Comandas de Cocina",
  "/restaurante/takeaway": "Take Away",
  "/restaurante/promociones": "Promociones",
  "/inventario/kardex": "Kárdex",
  "/inventario/categorias": "Categorías",
  "/finanzas/cashflow": "Flujo de Caja",
  "/config/marca": "Marca / Branding",
};

function getRouteTitle(pathname: string): string | undefined {
  // Exact match first
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname];
  // Prefix match for dynamic routes
  for (const [route, title] of Object.entries(ROUTE_TITLES)) {
    if (pathname.startsWith(route) && route !== "/") return title;
  }
  return undefined;
}

export function AppShell({ children, title: explicitTitle }: AppShellProps) {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const routeTitle = getRouteTitle(location.pathname);
  const title = explicitTitle ?? routeTitle ?? "IaaS-RonSys";

  return (
    <div className="min-h-screen bg-brand-background flex flex-col md:flex-row">
      {/* Sidebar */}
      <Sidebar
        isMobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header (mobile: sticky with hamburger + breadcrumb) */}
        <header className="sticky top-0 z-30 bg-brand-primary text-white shadow-md md:relative">
          <div className="flex items-center justify-between px-4 h-14">
            {/* Mobile hamburger */}
            <button
              className="md:hidden p-1.5 rounded-lg hover:bg-white/10"
              aria-label="Menú"
              onClick={() => setMobileMenuOpen(true)}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Breadcrumb / title */}
            <div className="flex items-center gap-2">
              <span className="text-xl md:hidden">🐟</span>
              <h1 className="font-bold text-lg tracking-tight truncate max-w-[200px] md:max-w-none">
                {title}
              </h1>
            </div>

            {/* Spacer for mobile (balancing hamburger) */}
            <div className="w-9 md:hidden" />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 bg-brand-surface py-4 text-center text-xs text-brand-text-secondary">
          IaaS-RonSys · El Segoviano · v0.1.0
        </footer>
      </div>
    </div>
  );
}
