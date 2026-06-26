/**
 * SidebarSection — Sección colapsable del sidebar.
 *
 * HU-F0-011: Sidebar jerárquico colapsable
 * - Expande/colapsa con clic en el header
 * - Persiste estado en localStorage
 * - Auto-expande si contiene la ruta activa (solo si no fue colapsada manualmente)
 *
 * @module components/layout/SidebarSection
 */
import { useState, type ReactNode } from "react";

interface SidebarSectionProps {
  icon: string;
  label: string;
  storageKey: string;
  defaultExpanded?: boolean;
  children: ReactNode;
}

export function SidebarSection({
  icon,
  label,
  storageKey,
  defaultExpanded = false,
  children,
}: SidebarSectionProps) {
  const [expanded, setExpanded] = useState(() => {
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (stored !== null) return stored === "true";
    } catch {
      // sessionStorage blocked
    }
    return defaultExpanded;
  });

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    try {
      sessionStorage.setItem(storageKey, String(next));
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-0.5">
      <button
        onClick={toggle}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
          uppercase tracking-wider text-brand-text-secondary/70 hover:text-brand-text-secondary
          hover:bg-gray-100/50 transition-colors"
      >
        <span className="text-base">{icon}</span>
        <span className="flex-1 text-left">{label}</span>
        <svg
          className={`w-3 h-3 transition-transform duration-200 ${
            expanded ? "rotate-90" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      {expanded && <div className="pl-2 space-y-0.5">{children}</div>}
    </div>
  );
}
