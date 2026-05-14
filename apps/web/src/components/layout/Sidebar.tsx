/**
 * Sidebar — Menú lateral jerárquico colapsable.
 *
 * HU-F0-011: Sidebar jerárquico con botón Salir siempre visible
 * - Estructura jerárquica por dominio de negocio
 * - Secciones colapsables con persistencia en sessionStorage
 * - Botón "Cerrar Sesión" siempre visible en la parte inferior
 * - Responsive: en mobile se oculta con overlay + backdrop
 * - Secciones condicionales según business_type
 *
 * @module components/layout/Sidebar
 */

import { useAuth } from "@/contexts/AuthContext";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import { SidebarSection } from "./SidebarSection";
import { SidebarItem } from "./SidebarItem";

interface SidebarProps {
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ isMobileOpen, onMobileClose }: SidebarProps) {
  const { logout } = useAuth();
  const { businessType } = useCompanySettings();

  const handleLogout = async () => {
    await logout();
    try {
      sessionStorage.clear();
    } catch {
      // ignore
    }
    window.location.href = "/login";
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo + Brand */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200">
        <span className="text-xl">🐟</span>
        <span className="font-bold text-brand-text-primary text-base">
          El Segoviano
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {/* ─── PROYECTO DE INVERSIÓN ─── */}
        <SidebarSection
          icon="🏗️"
          label="Proyecto de Inversión"
          storageKey="sidebar:investment"
          defaultExpanded={true}
        >
          <SidebarItem icon="📊" label="Dashboard" path="/" onClick={onMobileClose} />
          <SidebarItem icon="🏗️" label="Setup" path="/setup" onClick={onMobileClose} />
          <SidebarItem icon="🎮" label="Simulador" path="/simulador" onClick={onMobileClose} />
          <SidebarItem
            icon="📋"
            label="Reportes Financieros"
            path="/inversiones/reportes"
            onClick={onMobileClose}
          />
        </SidebarSection>

        {/* ─── VENTAS / POS ─── */}
        <SidebarSection
          icon="🧾"
          label="Ventas / POS"
          storageKey="sidebar:ventas"
          defaultExpanded={false}
        >
          <SidebarItem
            icon="💳"
            label="Caja / POS"
            path="/ventas/pos"
            onClick={onMobileClose}
          />
          <SidebarItem
            icon="🛒"
            label="Facturación"
            path="/ventas/nueva"
            onClick={onMobileClose}
          />
          <SidebarItem
            icon="📋"
            label="Historial"
            path="/ventas/historial"
            onClick={onMobileClose}
          />
        </SidebarSection>

        {/* ─── RESTAURANTE — visible según business_type ─── */}
        {businessType === "restaurant" && (
          <SidebarSection
            icon="🍽️"
            label="Restaurante"
            storageKey="sidebar:restaurante"
            defaultExpanded={false}
          >
            <SidebarItem
              icon="🪑"
              label="Mesas"
              path="/restaurante/mesas"
              onClick={onMobileClose}
            />
            <SidebarItem
              icon="📜"
              label="Menú"
              path="/restaurante/menu"
              onClick={onMobileClose}
            />
            <SidebarItem
              icon="👨‍🍳"
              label="Cocina"
              path="/restaurante/cocina"
              onClick={onMobileClose}
            />
            <SidebarItem
              icon="🥡"
              label="Take Away"
              path="/restaurante/takeaway"
              onClick={onMobileClose}
            />
            <SidebarItem
              icon="🏷️"
              label="Promociones"
              path="/restaurante/promociones"
              onClick={onMobileClose}
            />
          </SidebarSection>
        )}

        {/* ─── INVENTARIO ─── */}
        <SidebarSection
          icon="📦"
          label="Inventario"
          storageKey="sidebar:inventario"
          defaultExpanded={false}
        >
          <SidebarItem
            icon="📊"
            label="Kárdex"
            path="/inventario/kardex"
            onClick={onMobileClose}
          />
          <SidebarItem
            icon="🏷️"
            label="Categorías"
            path="/inventario/categorias"
            onClick={onMobileClose}
          />
        </SidebarSection>

        {/* ─── FINANZAS ─── */}
        <SidebarSection
          icon="💰"
          label="Finanzas"
          storageKey="sidebar:finanzas"
          defaultExpanded={false}
        >
          <SidebarItem
            icon="💵"
            label="Flujo de Caja"
            path="/finanzas/cashflow"
            onClick={onMobileClose}
          />
        </SidebarSection>

        {/* ─── CONFIGURACIÓN ─── */}
        <SidebarSection
          icon="⚙️"
          label="Configuración"
          storageKey="sidebar:config"
          defaultExpanded={false}
        >
          <SidebarItem
            icon="🎨"
            label="Marca / Branding"
            path="/config/marca"
            onClick={onMobileClose}
          />
        </SidebarSection>
      </nav>

      {/* ─── CERRAR SESIÓN — SIEMPRE VISIBLE ─── */}
      <div className="border-t border-gray-200 p-2 flex-shrink-0">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm
            text-red-600 hover:bg-red-50 transition-colors font-medium"
        >
          <span>🚪</span>
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:flex-col w-64 bg-brand-surface border-r border-gray-200 h-screen sticky top-0 flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={onMobileClose}
          />
          {/* Sidebar panel */}
          <div className="absolute left-0 top-0 bottom-0 w-72 bg-brand-surface shadow-xl z-10 animate-slide-in-left">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
