/**
 * SuperAdminDashboard — Panel de control global multi-tenant.
 *
 * Muestra estadísticas de todas las empresas y usuarios.
 * Solo accesible por rol 'superadmin'.
 *
 * @module pages/superadmin/Dashboard
 */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getSuperadminDashboard } from "@/services/api";

interface DashboardStats {
  total_companies: number;
  total_users: number;
  companies_by_type: Record<string, number>;
  users_by_role: Record<string, number>;
  active_companies: number;
  inactive_companies: number;
  active_users: number;
  inactive_users: number;
  recent_companies: Array<{
    id: number;
    name: string;
    business_type: string;
    setup_complete: boolean;
  }>;
  recent_users: Array<{
    id: number;
    email: string;
    full_name: string;
    role: string;
    tenant_id: number | null;
  }>;
}

const ROLE_LABELS: Record<string, string> = {
  superadmin: "Superadmin 🌐",
  admin: "Admin 👑",
  manager: "Manager 📋",
  operator: "Operador 🧑‍🍳",
  viewer: "Espectador 👁️",
};

const TYPE_LABELS: Record<string, string> = {
  restaurant: "🍽️ Restaurante",
  hardware: "🔧 Ferretería",
};

export function SuperAdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getSuperadminDashboard();
      setStats(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-10 h-10 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <span className="text-4xl">⚠️</span>
        <p className="mt-3 text-red-600">{error}</p>
        <button onClick={fetchDashboard} className="btn-primary mt-4 text-sm">
          Reintentar
        </button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-text-primary">
            🌐 Panel Superadmin
          </h1>
          <p className="text-sm text-brand-text-secondary mt-1">
            Bienvenido, {user?.full_name || user?.email} — Gestión global multi-tenant
          </p>
        </div>
        <button
          onClick={fetchDashboard}
          className="text-sm px-3 py-1.5 bg-brand-primary text-white rounded-lg hover:opacity-90"
        >
          🔄 Actualizar
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <div className="text-3xl font-bold text-brand-primary">{stats.total_companies}</div>
          <p className="text-xs text-brand-text-secondary mt-1">Empresas</p>
        </div>
        <div className="card p-4 text-center">
          <div className="text-3xl font-bold text-green-600">{stats.active_companies}</div>
          <p className="text-xs text-brand-text-secondary mt-1">Activas</p>
        </div>
        <div className="card p-4 text-center">
          <div className="text-3xl font-bold text-brand-primary">{stats.total_users}</div>
          <p className="text-xs text-brand-text-secondary mt-1">Usuarios</p>
        </div>
        <div className="card p-4 text-center">
          <div className="text-3xl font-bold text-green-600">{stats.active_users}</div>
          <p className="text-xs text-brand-text-secondary mt-1">Usuarios Activos</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card p-4">
          <h3 className="font-semibold text-brand-text-primary mb-3">📊 Empresas por Tipo</h3>
          <div className="space-y-2">
            {Object.entries(stats.companies_by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-sm">{TYPE_LABELS[type] || type}</span>
                <span className="text-sm font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <h3 className="font-semibold text-brand-text-primary mb-3">👥 Usuarios por Rol</h3>
          <div className="space-y-2">
            {Object.entries(stats.users_by_role).map(([role, count]) => (
              <div key={role} className="flex items-center justify-between">
                <span className="text-sm">{ROLE_LABELS[role] || role}</span>
                <span className="text-sm font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card p-4">
          <h3 className="font-semibold text-brand-text-primary mb-3">🏢 Últimas Empresas</h3>
          <div className="space-y-2">
            {stats.recent_companies.map((c) => (
              <div key={c.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div>
                  <span className="text-sm font-medium">{c.name}</span>
                  <span className="text-xs text-brand-text-secondary ml-2">
                    {TYPE_LABELS[c.business_type] || c.business_type}
                  </span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  c.setup_complete ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {c.setup_complete ? '✅ Activo' : '⏳ Pendiente'}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <h3 className="font-semibold text-brand-text-primary mb-3">👤 Últimos Usuarios</h3>
          <div className="space-y-2">
            {stats.recent_users.map((u) => (
              <div key={u.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div className="min-w-0">
                  <span className="text-sm font-medium truncate block">{u.full_name}</span>
                  <span className="text-xs text-brand-text-secondary">{u.email}</span>
                </div>
                <span className="text-xs text-brand-text-secondary ml-2">
                  {ROLE_LABELS[u.role] || u.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
