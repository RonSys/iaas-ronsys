/**
 * SidebarItem — Ítem de navegación del sidebar.
 *
 * HU-F0-011: Sidebar jerárquico colapsable
 * - Resalta si la ruta actual coincide
 * - Llama a onClick para cerrar sidebar en mobile
 *
 * @module components/layout/SidebarItem
 */

interface SidebarItemProps {
  icon: string;
  label: string;
  path: string;
  onClick?: () => void;
}

export function SidebarItem({ icon, label, path, onClick }: SidebarItemProps) {
  const isActive = window.location.pathname === path;

  return (
    <a
      href={path}
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
        isActive
          ? "bg-brand-primary/10 text-brand-primary font-medium"
          : "text-brand-text-secondary hover:bg-gray-100/50 hover:text-brand-text-primary"
      }`}
    >
      <span className="text-base">{icon}</span>
      <span>{label}</span>
    </a>
  );
}
