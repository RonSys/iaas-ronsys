/**
 * SidebarSection — Sección colapsable del sidebar jerárquico.
 *
 * Recuerda el estado expandido/contraído en sessionStorage para persistencia
 * entre navegaciones.
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
  const stored = typeof window !== "undefined"
    ? sessionStorage.getItem(storageKey)
    : null;
  const initial = stored !== null ? stored === "true" : defaultExpanded;
  const [expanded, setExpanded] = useState(initial);

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    try {
      sessionStorage.setItem(storageKey, String(next));
    } catch {
      // sessionStorage may be unavailable in some environments
    }
  };

  return (
    <div className="mb-1">
      <button
        onClick={toggle}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg
          text-sm font-semibold text-brand-text-primary hover:bg-gray-100
          transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <span>{label}</span>
        </span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${
            expanded ? "rotate-90" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${
          expanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="ml-4 mt-1 space-y-1">
          {children}
        </div>
      </div>
    </div>
  );
}
