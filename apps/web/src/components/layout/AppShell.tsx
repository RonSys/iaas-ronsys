/**
 * AppShell — Layout principal de la aplicación.
 *
 * Provee el header con navegación (desktop + mobile), el área de contenido
 * principal y el footer. Todas las páginas se renderizan dentro de este shell.
 *
 * @param title - Título opcional que se muestra en el breadcrumb del header
 * @param children - Contenido de la página
 *
 * @example
 * <AppShell title="Dashboard">
 *   <Dashboard />
 * </AppShell>
 */
import type { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

export function AppShell({ children, title }: AppShellProps) {
  return (
    <div className="min-h-screen bg-brand-background flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-brand-primary text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">🐟</span>
            <h1 className="font-bold text-lg tracking-tight">
              El Segoviano
            </h1>
            {title && (
              <>
                <span className="text-white/30 mx-1">/</span>
                <span className="text-white/80 text-sm">{title}</span>
              </>
            )}
          </div>
          <nav className="hidden md:flex items-center gap-1 text-sm">
            <NavLink href="/">📊 Dashboard</NavLink>
            <NavLink href="/setup">🏗️ Setup</NavLink>
            <NavLink href="/simulador">🎮 Simulador</NavLink>
            <NavLink href="/reportes">📋 Reportes</NavLink>
            <NavLink href="/kardex">📦 Kárdex</NavLink>
            <NavLink href="/settings">⚙️ Ajustes</NavLink>
          </nav>
          {/* Mobile menu button */}
          <button
            className="md:hidden p-1.5 rounded-lg hover:bg-white/10"
            aria-label="Menú"
            onClick={() => {
              const sidebar = document.getElementById("mobile-sidebar");
              sidebar?.classList.toggle("hidden");
            }}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
        {/* Mobile nav */}
        <nav
          id="mobile-sidebar"
          className="hidden md:hidden bg-brand-primary/95 border-t border-white/10"
        >
          <div className="flex flex-col p-2 gap-1 text-sm">
            <MobileNavLink href="/">📊 Dashboard</MobileNavLink>
            <MobileNavLink href="/setup">🏗️ Setup</MobileNavLink>
            <MobileNavLink href="/simulador">🎮 Simulador</MobileNavLink>
            <MobileNavLink href="/reportes">📋 Reportes</MobileNavLink>
            <MobileNavLink href="/kardex">📦 Kárdex</MobileNavLink>
            <MobileNavLink href="/settings">⚙️ Ajustes</MobileNavLink>
          </div>
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-brand-surface py-4 text-center text-xs text-brand-text-secondary">
        IaaS-RonSys · El Segoviano · v0.1.0
      </footer>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  const isActive = typeof window !== "undefined" && window.location.pathname === href;
  return (
    <a
      href={href}
      className={`px-3 py-1.5 rounded-lg transition-colors ${
        isActive
          ? "bg-white/15 font-medium"
          : "hover:bg-white/10"
      }`}
    >
      {children}
    </a>
  );
}

function MobileNavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      className="px-3 py-2.5 rounded-lg hover:bg-white/10 transition-colors"
    >
      {children}
    </a>
  );
}
