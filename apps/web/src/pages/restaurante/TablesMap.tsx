/**
 * TablesMap — Mapa de mesas del restaurante con CRUD completo.
 *
 * HU-F0-006: Mapa visual de mesas + CRUD + apertura/cierre
 * - Grid responsivo de mesas coloreadas por estado
 * - Tooltip con info de mesa ocupada
 * - Modal para abrir mesa (comensales + mesero)
 * - Modal para crear/editar mesa (número, capacidad, sección)
 * - Eliminar mesa (solo libres, con confirmación)
 * - Polling cada 30s para refrescar estados
 *
 * @module pages/restaurante/TablesMap
 */
import { authFetch } from "@/services/authFetch";
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface Table {
  id: number;
  number: string;
  capacity: number;
  status: "available" | "occupied" | "reserved" | "cleaning";
  section: string | null;
  guests?: number;
  waiter_name?: string;
  opened_at?: string;
  total_provisional?: number;
}

interface TableFormData {
  number: string;
  capacity: number;
  section: string;
}

const STATUS_COLORS: Record<Table["status"], string> = {
  available: "bg-green-100 border-green-500 text-green-800",
  occupied: "bg-red-100 border-red-500 text-red-800",
  reserved: "bg-yellow-100 border-yellow-500 text-yellow-800",
  cleaning: "bg-gray-100 border-gray-400 text-gray-600",
};

const STATUS_LABELS: Record<Table["status"], string> = {
  available: "Libre",
  occupied: "Ocupada",
  reserved: "Reservada",
  cleaning: "Limpieza",
};

const CAPACITY_OPTIONS = [2, 4, 6, 8, 10, 12];

export function TablesMap() {
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);

  // Open modal
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [openGuests, setOpenGuests] = useState(2);
  const [openWaiter, setOpenWaiter] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Create/Edit modal
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingTable, setEditingTable] = useState<Table | null>(null);
  const [formData, setFormData] = useState<TableFormData>({ number: "", capacity: 4, section: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchTables = useCallback(async () => {
    try {
      const res = await authFetch("/api/v1/restaurant/tables");
      if (!res.ok) throw new Error("Error al cargar mesas");
      const data = await res.json();
      setTables(data.tables ?? data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTables(); }, [fetchTables]);

  useEffect(() => {
    const interval = setInterval(fetchTables, 30000);
    return () => clearInterval(interval);
  }, [fetchTables]);

  // ─── Open table ───
  const handleOpenTable = async () => {
    if (!selectedTable || !openWaiter.trim()) return;
    setSubmitting(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${selectedTable.id}/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guests: openGuests, waiter_name: openWaiter }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al abrir mesa");
      }
      setShowOpenModal(false);
      setSelectedTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSubmitting(false);
    }
  };

  // ─── Create table ───
  const handleCreateTable = async () => {
    const num = Number(formData.number);
    if (!formData.number.trim() || isNaN(num) || num <= 0 || !Number.isInteger(num)) {
      setFormError("El número de mesa debe ser un entero positivo");
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      const body: Record<string, unknown> = {
        number: String(num),
        capacity: formData.capacity,
      };
      if (formData.section.trim()) body.section = formData.section.trim();
      const res = await authFetch("/api/v1/restaurant/tables", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al crear mesa");
      }
      setShowFormModal(false);
      setEditingTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setFormSubmitting(false);
    }
  };

  // ─── Update table ───
  const handleUpdateTable = async () => {
    if (!editingTable) return;
    const num = Number(formData.number);
    if (!formData.number.trim() || isNaN(num) || num <= 0 || !Number.isInteger(num)) {
      setFormError("El número de mesa debe ser un entero positivo");
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      const body: Record<string, unknown> = {
        number: String(num),
        capacity: formData.capacity,
      };
      if (formData.section.trim()) body.section = formData.section.trim();
      const res = await authFetch(`/api/v1/restaurant/tables/${editingTable.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al actualizar mesa");
      }
      setShowFormModal(false);
      setEditingTable(null);
      setSelectedTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Error al actualizar");
    } finally {
      setFormSubmitting(false);
    }
  };

  // ─── Delete table ───
  const handleDeleteTable = async (id: number) => {
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al eliminar mesa");
      }
      setSelectedTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  // ─── Reserve / Free ───
  const handleReserve = async (id: number) => {
    setSubmitting(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${id}/reserve`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al reservar");
      }
      setShowOpenModal(false);
      setSelectedTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFree = async (id: number) => {
    setSubmitting(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${id}/free`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al liberar");
      }
      setShowOpenModal(false);
      setSelectedTable(null);
      await fetchTables();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSubmitting(false);
    }
  };

  // ─── Click handlers ───
  const handleTableClick = (table: Table) => {
    setSelectedTable(table);
    if (table.status === "available" || table.status === "reserved") {
      setOpenGuests(2);
      setOpenWaiter("");
      setShowOpenModal(true);
    }
  };

  const openCreateModal = () => {
    setEditingTable(null);
    setFormData({ number: "", capacity: 4, section: "" });
    setFormError(null);
    setShowFormModal(true);
  };

  const openEditModal = (table: Table) => {
    setEditingTable(table);
    setFormData({ number: table.number, capacity: table.capacity, section: table.section ?? "" });
    setFormError(null);
    setShowOpenModal(false);
    setShowFormModal(true);
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Error ───
  if (error && tables.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🪑 Mapa de Mesas</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="mb-2">⚠️ {error}</p>
          <button onClick={fetchTables} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🪑 Mapa de Mesas</h2>
          <p className="text-sm text-brand-text-secondary">
            {tables.length} mesas · {tables.filter((t) => t.status === "available").length} libres
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          ➕ Nueva Mesa
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs underline">Cerrar</button>
        </div>
      )}

      {/* Grid de mesas */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {tables.map((table) => (
          <button
            key={table.id}
            onClick={() => handleTableClick(table)}
            className={`relative p-4 rounded-xl border-2 text-left transition-all hover:shadow-md group ${STATUS_COLORS[table.status]}`}
          >
            <div className="text-lg font-bold">{table.number}</div>
            <div className="text-xs mt-1">{table.capacity} pers. · {table.section ?? "General"}</div>
            <div className="text-xs font-medium mt-1">{STATUS_LABELS[table.status]}</div>
            {table.status === "occupied" && (
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg p-2 shadow text-xs text-left">
                <div>👥 {table.guests} comensales</div>
                <div>👤 {table.waiter_name}</div>
                {table.opened_at && (
                  <div>🕐 {new Date(table.opened_at).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</div>
                )}
                {table.total_provisional !== undefined && (
                  <div className="font-bold mt-1">S/ {table.total_provisional.toFixed(2)}</div>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      {tables.length === 0 && !loading && (
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🪑</span>
          <p>No hay mesas configuradas.</p>
          <button onClick={openCreateModal} className="mt-3 px-4 py-2 bg-brand-primary text-white rounded-lg text-sm">
            ➕ Crear Primera Mesa
          </button>
        </div>
      )}

      {/* Modal: Acciones de mesa (varía según status) */}
      {showOpenModal && selectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <div className="flex items-center gap-2 mb-4">
              <span className={`w-3 h-3 rounded-full ${
                selectedTable.status === "available" ? "bg-green-500" :
                selectedTable.status === "reserved" ? "bg-yellow-500" :
                selectedTable.status === "occupied" ? "bg-red-500" : "bg-gray-400"
              }`} />
              <h3 className="text-lg font-bold text-brand-text-primary">
                Mesa {selectedTable.number}
              </h3>
              <span className="text-xs text-brand-text-secondary">
                ({STATUS_LABELS[selectedTable.status]})
              </span>
            </div>

            {/* ─── AVAILABLE: Abrir, Reservar, Editar, Eliminar ─── */}
            {selectedTable.status === "available" && (
              <>
                <div className="space-y-3 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">N° de Comensales</label>
                    <input
                      type="number" min={1} max={selectedTable.capacity}
                      value={openGuests} onChange={(e) => setOpenGuests(Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Nombre del Mesero *</label>
                    <input
                      value={openWaiter} onChange={(e) => setOpenWaiter(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Ej: Carlos" autoFocus
                    />
                  </div>
                </div>
                <div className="flex gap-2 justify-between">
                  <div className="flex gap-2">
                    <button onClick={() => handleReserve(selectedTable.id)}
                      className="px-3 py-2 text-sm rounded-lg bg-yellow-500 text-white hover:bg-yellow-600"
                      disabled={submitting}>
                      📅 Reservar
                    </button>
                    <button onClick={() => openEditModal(selectedTable)}
                      className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                      ✏️ Editar
                    </button>
                    <button onClick={() => {
                      if (window.confirm(`¿Eliminar mesa ${selectedTable.number}?`)) {
                        setShowOpenModal(false);
                        handleDeleteTable(selectedTable.id);
                      }
                    }} className="px-3 py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                      🗑️ Eliminar
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); }}
                      className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50" disabled={submitting}>
                      Cancelar
                    </button>
                    <button onClick={handleOpenTable} disabled={submitting || !openWaiter.trim()}
                      className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50">
                      {submitting ? "Abriendo..." : "Abrir Mesa"}
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* ─── RESERVED: Liberar, Editar, Eliminar ─── */}
            {selectedTable.status === "reserved" && (
              <>
                <div className="mb-4 text-sm text-brand-text-secondary">
                  <p>Capacidad: {selectedTable.capacity} pers.</p>
                  <p>Sección: {selectedTable.section ?? "General"}</p>
                </div>
                <div className="flex gap-2 justify-between">
                  <div className="flex gap-2">
                    <button onClick={() => handleFree(selectedTable.id)}
                      className="px-3 py-2 text-sm rounded-lg bg-gray-600 text-white hover:bg-gray-700"
                      disabled={submitting}>
                      🔓 Liberar Reserva
                    </button>
                    <button onClick={() => openEditModal(selectedTable)}
                      className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                      ✏️ Editar
                    </button>
                    <button onClick={() => {
                      if (window.confirm(`¿Eliminar mesa ${selectedTable.number}?`)) {
                        setShowOpenModal(false);
                        handleDeleteTable(selectedTable.id);
                      }
                    }} className="px-3 py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                      🗑️ Eliminar
                    </button>
                  </div>
                  <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); }}
                    className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50" disabled={submitting}>
                    Cancelar
                  </button>
                </div>
              </>
            )}

            {/* ─── OCCUPIED / CLEANING: solo info ─── */}
            {(selectedTable.status === "occupied" || selectedTable.status === "cleaning") && (
              <>
                <div className="mb-4 text-sm text-brand-text-secondary">
                  <p>Capacidad: {selectedTable.capacity} pers.</p>
                  <p>Sección: {selectedTable.section ?? "General"}</p>
                  <p>Estado: {STATUS_LABELS[selectedTable.status]}</p>
                  {selectedTable.guests && <p>Comensales: {selectedTable.guests}</p>}
                  {selectedTable.waiter_name && <p>Mesero: {selectedTable.waiter_name}</p>}
                </div>
                <div className="flex justify-end">
                  <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); }}
                    className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                    Cerrar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Modal: Crear / Editar mesa */}
      {showFormModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              {editingTable ? `Editar Mesa ${editingTable.number}` : "Nueva Mesa"}
            </h3>
            {formError && (
              <div className="mb-3 p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">{formError}</div>
            )}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Número de Mesa *</label>
                <input
                  type="number" min={1} step={1} value={formData.number}
                  onChange={(e) => setFormData({ ...formData, number: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Ej: 5" autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Capacidad</label>
                <select value={formData.capacity}
                  onChange={(e) => setFormData({ ...formData, capacity: Number(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg text-sm">
                  {CAPACITY_OPTIONS.map((n) => <option key={n} value={n}>{n} personas</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Sección</label>
                <input
                  value={formData.section}
                  onChange={(e) => setFormData({ ...formData, section: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Ej: Terraza, Salón Principal"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button onClick={() => { setShowFormModal(false); setEditingTable(null); }}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50" disabled={formSubmitting}>
                Cancelar
              </button>
              <button onClick={editingTable ? handleUpdateTable : handleCreateTable}
                disabled={formSubmitting || !formData.number.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50">
                {formSubmitting ? "Guardando..." : editingTable ? "Actualizar" : "Crear Mesa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
