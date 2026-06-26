/**
 * SectionsManagement — CRUD de secciones del restaurante.
 *
 * Responsabilidades:
 * - Listar secciones en tabla con nombre, descripción, mesas asociadas
 * - Crear/editar sección vía modal
 * - Eliminar sección con confirmación
 * - Bloquear eliminación si tiene mesas asociadas
 * - Toast de feedback tras cada operación
 *
 * @module pages/restaurante/SectionsManagement
 */
import { useState, useEffect, useCallback } from "react";
import { authFetch } from "@/services/authFetch";
import { Skeleton } from "@/components/dashboard/KPICard";

interface Section {
  id: number;
  name: string;
  description?: string;
  sort_order: number;
  table_count: number;
}

interface SectionFormData {
  name: string;
  description: string;
}

type ToastType = "success" | "error";

export function SectionsManagement() {
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: ToastType; message: string } | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [formData, setFormData] = useState<SectionFormData>({ name: "", description: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // ─── Toast helper ───
  const showToast = useCallback((type: ToastType, message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ─── Fetch sections ───
  const fetchSections = useCallback(async () => {
    try {
      const res = await authFetch("/api/v1/restaurant/sections");
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al cargar secciones");
      }
      const data = await res.json();
      setSections(data.sections ?? data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSections(); }, [fetchSections]);

  // ─── Open create modal ───
  const openCreateModal = () => {
    setEditingSection(null);
    setFormData({ name: "", description: "" });
    setFormError(null);
    setShowModal(true);
  };

  // ─── Open edit modal ───
  const openEditModal = (section: Section) => {
    setEditingSection(section);
    setFormData({ name: section.name, description: section.description ?? "" });
    setFormError(null);
    setShowModal(true);
  };

  // ─── Handle create ───
  const handleCreate = async () => {
    if (!formData.name.trim()) {
      setFormError("El nombre de la sección es obligatorio");
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      const res = await authFetch("/api/v1/restaurant/sections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al crear sección");
      }
      setShowModal(false);
      await fetchSections();
      showToast("success", `✅ Sección "${formData.name}" creada`);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setFormSubmitting(false);
    }
  };

  // ─── Handle update ───
  const handleUpdate = async () => {
    if (!editingSection) return;
    if (!formData.name.trim()) {
      setFormError("El nombre de la sección es obligatorio");
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      const res = await authFetch(`/api/v1/restaurant/sections/${editingSection.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al actualizar sección");
      }
      setShowModal(false);
      setEditingSection(null);
      await fetchSections();
      showToast("success", `✅ Sección "${formData.name}" actualizada`);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Error al actualizar");
    } finally {
      setFormSubmitting(false);
    }
  };

  // ─── Handle delete ───
  const handleDelete = async (section: Section) => {
    if (section.table_count > 0) {
      showToast(
        "error",
        `❌ No se puede eliminar "${section.name}": ${section.table_count} mesa(s) asignada(s)`,
      );
      return;
    }
    if (!window.confirm(`¿Eliminar la sección "${section.name}"?`)) return;

    try {
      const res = await authFetch(`/api/v1/restaurant/sections/${section.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al eliminar sección");
      }
      await fetchSections();
      showToast("success", `🗑️ Sección "${section.name}" eliminada`);
    } catch (err: unknown) {
      showToast("error", `❌ ${err instanceof Error ? err.message : "Error al eliminar"}`);
    }
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ─── Toast ─── */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-[100] max-w-sm p-3 rounded-lg shadow-lg text-sm ${
            toast.type === "success"
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* ─── Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">📋 Secciones</h2>
          <p className="text-sm text-brand-text-secondary">
            {sections.length} sección(es) configurada(s)
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          ➕ Nueva Sección
        </button>
      </div>

      {/* ─── Error banner ─── */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="text-xs underline">Cerrar</button>
        </div>
      )}

      {/* ─── Empty state ─── */}
      {sections.length === 0 && !loading && !error && (
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">📋</span>
          <p>No hay secciones configuradas.</p>
          <button
            onClick={openCreateModal}
            className="mt-3 px-4 py-2 bg-brand-primary text-white rounded-lg text-sm"
          >
            ➕ Crear Primera Sección
          </button>
        </div>
      )}

      {/* ─── Table ─── */}
      {sections.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-brand-text-primary">Nombre</th>
                <th className="text-left px-4 py-3 font-semibold text-brand-text-primary">Descripción</th>
                <th className="text-center px-4 py-3 font-semibold text-brand-text-primary">Mesas</th>
                <th className="text-right px-4 py-3 font-semibold text-brand-text-primary">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sections.map((section) => (
                <tr key={section.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-brand-text-primary">
                    {section.name}
                  </td>
                  <td className="px-4 py-3 text-brand-text-secondary max-w-xs truncate">
                    {section.description || "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium ${
                        section.table_count > 0
                          ? "bg-brand-primary/10 text-brand-primary"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {section.table_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => openEditModal(section)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-brand-primary transition-colors"
                        title="Editar sección"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(section)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors"
                        title={section.table_count > 0 ? "Tiene mesas asignadas" : "Eliminar sección"}
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
      )}

      {/* ─── Modal: Crear / Editar Sección ─── */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              {editingSection ? `Editar Sección` : "Nueva Sección"}
            </h3>

            {formError && (
              <div className="mb-3 p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
                {formError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Nombre <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Ej: Terraza, Salón Principal"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Descripción</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm resize-none"
                  placeholder="Descripción opcional de la sección"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => { setShowModal(false); setEditingSection(null); }}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={formSubmitting}
              >
                Cancelar
              </button>
              <button
                onClick={editingSection ? handleUpdate : handleCreate}
                disabled={formSubmitting || !formData.name.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
              >
                {formSubmitting ? "Guardando..." : editingSection ? "Actualizar" : "Crear Sección"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
