/**
 * SuperAdminCompanies — CRUD de empresas multi-tenant.
 *
 * Solo accesible por rol superadmin.
 *
 * @module pages/superadmin/Companies
 */

import { useState, useEffect, useCallback } from "react";
import {
  getSuperadminCompanies,
  createSuperadminCompany,
  deleteSuperadminCompany,
} from "@/services/api";

interface Company {
  id: number;
  name: string;
  ruc: string;
  address: string | null;
  economic_activity: string | null;
  business_type: string;
  setup_complete: boolean;
  created_at: string | null;
}

interface CompanyListResponse {
  total: number;
  companies: Company[];
}

const BUSINESS_TYPES = [
  { value: "restaurant", label: "🍽️ Restaurante" },
  { value: "hardware", label: "🔧 Ferretería" },
  { value: "retail", label: "🏪 Retail" },
  { value: "services", label: "💼 Servicios" },
];

export function SuperAdminCompanies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    ruc: "",
    address: "",
    economic_activity: "",
    business_type: "restaurant",
  });
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchCompanies = useCallback(async () => {
    try {
      setLoading(true);
      const data: CompanyListResponse = await getSuperadminCompanies();
      setCompanies(data.companies);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await createSuperadminCompany(formData);
      setSuccessMsg(`✅ Empresa "${created.name}" creada exitosamente`);
      setShowForm(false);
      setFormData({ name: "", ruc: "", address: "", economic_activity: "", business_type: "restaurant" });
      fetchCompanies();
      setTimeout(() => setSuccessMsg(null), 8000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (company: Company) => {
    if (!confirm(`¿Eliminar "${company.name}"? Esta acción no se puede deshacer.`)) return;
    try {
      await deleteSuperadminCompany(company.id);
      setSuccessMsg(`✅ Empresa "${company.name}" eliminada`);
      fetchCompanies();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-text-primary">
            🏢 Empresas
          </h1>
          <p className="text-sm text-brand-text-secondary mt-1">
            {total} empresa(s) registrada(s) en el sistema
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:opacity-90"
        >
          {showForm ? "✕ Cancelar" : "➕ Nueva Empresa"}
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
          <h3 className="font-semibold">Nueva Empresa</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: Cevichería El Segoviano"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">RUC *</label>
              <input
                type="text"
                required
                value={formData.ruc}
                onChange={(e) => setFormData({ ...formData, ruc: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: 10777555551"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Dirección</label>
              <input
                type="text"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Av. Principal 123"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tipo de Negocio</label>
              <select
                value={formData.business_type}
                onChange={(e) => setFormData({ ...formData, business_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                {BUSINESS_TYPES.map((bt) => (
                  <option key={bt.value} value={bt.value}>{bt.label}</option>
                ))}
              </select>
              {formData.business_type === 'restaurant' && (
                <p className="text-xs text-brand-text-secondary mt-1">
                  🍽️ Roles sugeridos: Admin (gestión), Cocinero 🧑‍🍳, Mesero 🧑‍💼
                </p>
              )}
              {formData.business_type === 'hardware' && (
                <p className="text-xs text-brand-text-secondary mt-1">
                  🔧 Roles sugeridos: Admin (gestión), Vendedor 🛒
                </p>
              )}
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Actividad Económica</label>
              <input
                type="text"
                value={formData.economic_activity}
                onChange={(e) => setFormData({ ...formData, economic_activity: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                placeholder="Ej: Venta de comidas y bebidas"
              />
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
              {saving ? "Creando..." : "Crear Empresa"}
            </button>
          </div>
        </form>
      )}

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
                  <th className="text-left p-3 font-medium">RUC</th>
                  <th className="text-left p-3 font-medium">Tipo</th>
                  <th className="text-center p-3 font-medium">Estado</th>
                  <th className="text-center p-3 font-medium">Usuarios</th>
                  <th className="text-center p-3 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id} className="border-b last:border-b-0 hover:bg-gray-50">
                    <td className="p-3 text-brand-text-secondary">{c.id}</td>
                    <td className="p-3 font-medium">{c.name}</td>
                    <td className="p-3 text-brand-text-secondary">{c.ruc}</td>
                    <td className="p-3">{BUSINESS_TYPES.find(bt => bt.value === c.business_type)?.label || c.business_type}</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        c.setup_complete ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {c.setup_complete ? '✅ Activo' : '⏳ Pendiente'}
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <span className="text-xs text-brand-text-secondary">
                        {c.business_type === 'restaurant' ? '🧑‍🍳👨‍💼' : '🛒'}
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <a
                          href={`/superadmin/usuarios?tenant=${c.id}`}
                          className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100"
                        >
                          👥 Crear Usuarios
                        </a>
                        <button
                          onClick={() => handleDelete(c)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
