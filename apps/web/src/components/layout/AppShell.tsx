/**
 * AppShell — Layout principal con sidebar jerárquico.
 *
 * Provee sidebar lateral colapsable con navegación por dominio,
 * área de contenido principal y footer. Replacement del header-nav anterior.
 *
 * HU-F0-011: Sidebar jerárquico colapsable
 * HU-F1-003: Navegación condicional por feature flags (vía Sidebar)
 *
 * @param title - Título opcional que se muestra como breadcrumb
 * @param children - Contenido de la página
 */
import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { useState } from "react";

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

export function AppShell({ children, title }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-brand-background flex">
      {/* Sidebar */}
      <Sidebar
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header (mobile menu toggle + breadcrumb) */}
        <header className="sticky top-0 z-30 bg-brand-surface border-b border-gray-200 h-14 flex items-center px-4 gap-3 flex-shrink-0">
          {/* Mobile menu button */}
          <button
            className="md:hidden p-1.5 rounded-lg hover:bg-gray-100"
            aria-label="Abrir menú"
            onClick={() => setMobileOpen(true)}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          {title && (
            <span className="text-sm font-medium text-brand-text-primary">
              {title}
            </span>
          )}
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
    </div>
  );
}
