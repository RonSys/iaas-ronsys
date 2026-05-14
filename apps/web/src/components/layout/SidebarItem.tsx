/**
 * SidebarItem — Ítem individual del sidebar, con icono + etiqueta + estado activo.
 *
 * @module components/layout/SidebarItem
 */
import { useLocation, useNavigate } from "react-router-dom";

interface SidebarItemProps {
  icon: string;
  label: string;
  path: string;
  onClick?: () => void;
}

export function SidebarItem({ icon, label, path, onClick }: SidebarItemProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isActive = location.pathname === path;

  const handleClick = () => {
    navigate(path);
    onClick?.();
  };

  return (
    <button
      onClick={handleClick}
      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left
        ${isActive
          ? "bg-brand-primary/10 text-brand-primary font-medium"
          : "text-brand-text-secondary hover:bg-gray-100 hover:text-brand-text-primary"
        }`}
    >
      <span className="flex-shrink-0 text-base">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}
