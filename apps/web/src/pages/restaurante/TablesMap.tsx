/**
 * TablesMap — Mapa de mesas del restaurante.
 *
 * HU-F0-006: Mapa visual de mesas con estados + apertura/cierre
 * - Grid responsivo de mesas coloreadas por estado
 * - Tooltip con info de mesa ocupada
 * - Modal para abrir mesa (comensales + mesero)
 * - Drawer lateral para mesa ocupada (pedidos activos)
 * - Polling cada 30s para refrescar estados
 * - Móvil: lista vertical en vez de grid
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

export function TablesMap() {
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [openGuests, setOpenGuests] = useState(2);
  const [openWaiter, setOpenWaiter] = useState("");
  const [submitting, setSubmitting] = useState(false);

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

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  // Polling cada 30s
  useEffect(() => {
    const interval = setInterval(fetchTables, 30000);
    return () => clearInterval(interval);
  }, [fetchTables]);

  const handleOpenTable = async () => {
    if (!selectedTable || !openWaiter.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `/api/v1/restaurant/tables/${selectedTable.id}/open`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ guests: openGuests, waiter_name: openWaiter }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al abrir mesa");
      }
      setShowOpenModal(false);
      await fetchTables();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleTableClick = (table: Table) => {
    setSelectedTable(table);
    if (table.status === "available") {
      setOpenGuests(2);
      setOpenWaiter("");
      setShowOpenModal(true);
    }
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
            {tables.length} mesas ·{" "}
            {tables.filter((t) => t.status === "available").length} libres
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs underline">Cerrar</button>
        </div>
      )}

      {/* Grid de mesas (desktop) → Lista (mobile) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {tables.map((table) => (
          <button
            key={table.id}
            onClick={() => handleTableClick(table)}
            className={`relative p-4 rounded-xl border-2 text-left transition-all hover:shadow-md group ${
              STATUS_COLORS[table.status]
            }`}
          >
            <div className="text-lg font-bold">{table.number}</div>
            <div className="text-xs mt-1">
              {table.capacity} pers. · {table.section ?? "General"}
            </div>
            <div className="text-xs font-medium mt-1">
              {STATUS_LABELS[table.status]}
            </div>
            {table.status === "occupied" && (
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg p-2 shadow text-xs text-left">
                <div>👥 {table.guests} comensales</div>
                <div>👤 {table.waiter_name}</div>
                {table.opened_at && (
                  <div>🕐 {new Date(table.opened_at).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</div>
                )}
                {table.total_provisional !== undefined && (
                  <div className="font-bold mt-1">
                    S/ {table.total_provisional.toFixed(2)}
                  </div>
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
        </div>
      )}

      {/* Modal: Abrir mesa */}
      {showOpenModal && selectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              Abrir Mesa {selectedTable.number}
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">
                  N° de Comensales
                </label>
                <input
                  type="number"
                  min={1}
                  max={selectedTable.capacity}
                  value={openGuests}
                  onChange={(e) => setOpenGuests(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Nombre del Mesero *
                </label>
                <input
                  value={openWaiter}
                  onChange={(e) => setOpenWaiter(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Ej: Carlos"
                  autoFocus
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => setShowOpenModal(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                onClick={handleOpenTable}
                disabled={submitting || !openWaiter.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
                  hover:bg-brand-secondary disabled:opacity-50"
              >
                {submitting ? "Abriendo..." : "Abrir Mesa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
