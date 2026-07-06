/**
 * SuperAdminUsers — Gestión de usuarios multi-tenant.
 *
 * CRUD de usuarios en cualquier empresa del sistema.
 * Roles dinámicos según tipo de negocio de la empresa.
 * Solo accesible por rol superadmin.
 *
 * @module pages/superadmin/Users
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  getSuperadminUsers,
  createSuperadminUser,
  deleteSuperadminUser,
  activateSuperadminUser,
  getSuperadminCompanies,
} from "@/services/api";

interface SAUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  tenant_id: number | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

interface Company {
  id: number;
  name: string;
  business_type?: string;
}

const ROLE_LABELS: Record<string, string> = {
  superadmin: "🌐 Superadmin",
  admin: "👑 Admin",
  manager: "📋 Manager",
  operator: "🧑‍🍳 Operador",
  viewer: "👁️ Viewer",
};

const BUSINESS_ROLES: Record<string, { value: string; label: string }[]> = {
  restaurant: [
    { value: "admin", label: "👑 Admin (Gestión)" },
    { value: "operator", label: "🧑‍🍳 Cocinero" },
    { value: "operator", label: "🧑‍💼 Mesero" },
  ],
  hardware: [
    { value: "admin", label: "👑 Admin (Gestión)" },
    { value: "operator", label: "🛒 Vendedor" },
  ],
  services: [
    { value: "admin", label: "👑 Admin (Gestión)" },
    { value: "operator", label: "🧑‍🍳 Operador" },
  ],
  retail: [
    { value: "admin", label: "👑 Admin (Gestión)" },
    { value: "operator", label: "🧑‍🍳 Operador" },
  ],
};

function getRoleName(role: string, businessType?: string): string {
  if (role === "superadmin") return "🌐 Superadmin";
  const roles = BUSINESS_ROLES[businessType || ""];
  if (roles) {
    const found = roles.find(r => r.value === role);
    if (found) return found.label;
  }
  return ROLE_LABELS[role] || role;
}

function getRoleSuggestions(businessType?: string) {
  return BUSINESS_ROLES[businessType || ""] || BUSINESS_ROLES.restaurant;
}

export function SuperAdminUsers() {
  const [searchParams] = useSearchParams();
  const tenantFromParam = searchParams.get('tenant');

  const [users, setUsers] = useState<SAUser[]>([]);
  const [total, setTotal] = useState(0);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "operator",
    tenant_id: tenantFromParam ? Number(tenantFromParam) : 2,
  });
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [filterTenant, setFilterTenant] = useState<number | "">(tenantFromParam ? Number(tenantFromParam) : "");
  const [filterRole, setFilterRole] = useState("");
  const [filterType, setFilterType] = useState("");

  // Filter companies by business type for the dropdown
  const filteredCompanies = filterType
    ? companies.filter(c => c.business_type === filterType)
    : companies;

  // Filter users by business type client-side (evita bucle de renders)
  const displayedUsers = filterType
    ? users.filter(u => {
        if (u.tenant_id === null) return true; // superadmin global
        const comp = companies.find(c => c.id === u.tenant_id);
        return comp?.business_type === filterType;
      })
    : users;

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getSuperadminUsers({
        tenant_id: filterTenant ? Number(filterTenant) : undefined,
        role: filterRole || undefined,
      });
      setUsers(data.users || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filterTenant, filterRole]);

  const fetchCompanies = useCallback(async () => {
    try {
      const data = await getSuperadminCompanies();
      setCompanies(data.companies || []);
    } catch { /* ignore */ }
  }, []);

  // Cargar datos al montar o cambiar filtros
  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Cargar empresas UNA SOLA vez al montar
  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await createSuperadminUser(formData);
      setSuccessMsg(`✅ Usuario "${created.full_name}" creado en tenant ${created.tenant_id}`);
      setShowForm(false);
      setFormData({ email: "", full_name: "", password: "", role: "operator", tenant_id: formData.tenant_id });
      fetchUsers();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user: SAUser) => {
    if (user.role === "superadmin") {
      setError("No puedes desactivar al superadmin del sistema");
      setTimeout(() => setError(null), 3000);
      return;
    }
    const action = user.is_active ? "desactivar" : "reactivar";
    if (!confirm(`¿${action} a "${user.full_name}" (${user.email})?`)) return;

    try {
      if (user.is_active) {
        await deleteSuperadminUser(user.id);
      } else {
        await activateSuperadminUser(user.id);
      }
      setSuccessMsg(`✅ Usuario ${action}do correctamente`);
      fetchUsers();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const selectedCompany = companies.find(c => c.id === formData.tenant_id);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-brand-text-primary">
            👥 Usuarios
          </h1>
          <p className="text-sm text-brand-text-secondary mt-1">
            {total} usuario(s) en el sistema
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:opacity-90"
        >
          {showForm ? "✕ Cancelar" : "➕ Nuevo Usuario"}
        </button>
      </div>

      {successMsg && (
        <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm border border-green-200">
          {successMsg}
        </div>
      )}
      {error && (
        <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Cerrar</button>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="card p-4 space-y-4">
          <h3 className="font-semibold">Nuevo Usuario</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre completo *</label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: Mesero 3"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email *</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: mesero3@elsegoviano.pe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Contraseña *</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Min. 8 caracteres"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Rol *</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                {getRoleSuggestions(selectedCompany?.business_type).map((r, i) => (
                  <option key={`${r.value}-${i}`} value={r.value}>{r.label}</option>
                ))}
              </select>
              {selectedCompany && (
                <p className="text-xs text-brand-text-secondary mt-1">
                  {selectedCompany.business_type === 'restaurant'
                    ? '🍽️ Cevichería/Restaurante: Admin, Cocinero o Mesero'
                    : selectedCompany.business_type === 'hardware'
                      ? '🔧 Ferretería: Admin o Vendedor'
                      : `Roles según tipo: ${selectedCompany.business_type}`
                  }
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Empresa (Tenant) *</label>
              <select
                value={formData.tenant_id}
                onChange={(e) => {
                  const tid = Number(e.target.value);
                  setFormData({ ...formData, tenant_id: tid, role: 'operator' });
                }}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                {companies.length === 0 && <option value={0}>No hay empresas. Crea una primero.</option>}
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    🏢 {c.name} ({c.business_type === 'restaurant' ? '🍽️' : '🔧'})
                  </option>
                ))}
              </select>
              {companies.length === 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  ⚠️ Primero debes crear una empresa en la sección "Empresas"
                </p>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Creando..." : "Crear Usuario"}
            </button>
          </div>
        </form>
      )}

      <div className="flex gap-3 flex-wrap">
        <select
          value={filterTenant}
          onChange={(e) => setFilterTenant(e.target.value ? Number(e.target.value) : "")}
          className="px-3 py-1.5 border rounded-lg text-sm"
        >
          <option value="">🏢 Todas las empresas</option>
          {filteredCompanies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.business_type === 'restaurant' ? '🍽️' : '🔧'} {c.name}
            </option>
          ))}
        </select>
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className="px-3 py-1.5 border rounded-lg text-sm"
        >
          <option value="">👤 Todos los roles</option>
          {[
            { value: "superadmin", label: "🌐 Superadmin" },
            { value: "admin", label: "👑 Admin" },
            { value: "operator", label: "🧑‍🍳 Operador" },
            { value: "manager", label: "📋 Manager" },
            { value: "viewer", label: "👁️ Viewer" },
          ].map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-3 py-1.5 border rounded-lg text-sm"
        >
          <option value="">🏷️ Todos los tipos</option>
          <option value="restaurant">🍽️ Restaurante</option>
          <option value="hardware">🔧 Ferretería</option>
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="text-left p-3 font-medium">ID</th>
                  <th className="text-left p-3 font-medium">Nombre</th>
                  <th className="text-left p-3 font-medium">Email</th>
                  <th className="text-left p-3 font-medium">Rol</th>
                  <th className="text-center p-3 font-medium">Empresa</th>
                  <th className="text-center p-3 font-medium">Tipo</th>
                  <th className="text-center p-3 font-medium">Estado</th>
                  <th className="text-center p-3 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {displayedUsers.map((u) => {
                  const comp = companies.find(c => c.id === u.tenant_id);
                  return (
                    <tr key={u.id} className="border-b last:border-b-0 hover:bg-gray-50">
                      <td className="p-3 text-brand-text-secondary">{u.id}</td>
                      <td className="p-3 font-medium">{u.full_name}</td>
                      <td className="p-3 text-brand-text-secondary">{u.email}</td>
                      <td className="p-3">{getRoleName(u.role, comp?.business_type)}</td>
                      <td className="p-3 text-center">
                        {u.tenant_id ? (
                          <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                            {comp?.name || `ID: ${u.tenant_id}`}
                          </span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full">
                            🌐 Global
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        {comp ? (
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            comp.business_type === 'restaurant' ? 'bg-orange-50 text-orange-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {comp.business_type === 'restaurant' ? '🍽️ Restaurante' : '🔧 Ferretería'}
                          </span>
                        ) : (
                          <span className="text-xs text-brand-text-secondary">—</span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {u.is_active ? '✅ Activo' : '❌ Inactivo'}
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        {u.role !== "superadmin" && (
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={`text-xs hover:underline ${
                              u.is_active ? 'text-red-600' : 'text-green-600'
                            }`}
                          >
                            {u.is_active ? '🚫 Desactivar' : '✅ Reactivar'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
