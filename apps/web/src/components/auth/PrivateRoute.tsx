/**
 * PrivateRoute — Protección de rutas autenticadas.
 *
 * Envuelve rutas que requieren sesión. Si el usuario no está
 * autenticado, redirige a /login guardando la ruta original.
 * Opcionalmente restringe por rol.
 *
 * US-18: PrivateRoute — Protección de Rutas
 *
 * @module components/auth/PrivateRoute
 */

import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/auth";

type UserRole = User["role"];

interface PrivateRouteProps {
  children: ReactNode;
  allowedRoles?: UserRole[];
}

export function PrivateRoute({ children, allowedRoles }: PrivateRouteProps) {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  // Loading — mostramos spinner mientras se valida sesión
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background">
        <div className="text-center animate-fade-in">
          <span className="text-4xl">🐟</span>
          <div className="mt-4 w-10 h-10 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-3 text-brand-text-secondary text-sm">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  // No autenticado → login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Restricción por rol
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background">
        <div className="text-center p-8 card max-w-md">
          <span className="text-5xl">🚫</span>
          <h2 className="mt-4 text-xl font-bold text-brand-text-primary">
            Acceso Denegado
          </h2>
          <p className="mt-2 text-sm text-brand-text-secondary">
            No tenés permisos para acceder a esta sección.
          </p>
          <a href="/" className="btn-primary mt-4 inline-block text-sm">
            Volver al Dashboard
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
