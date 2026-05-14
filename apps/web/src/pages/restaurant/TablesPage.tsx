/**
 * TablesPage — Mapa visual de mesas del restaurante.
 *
 * HU-F0-014: Mapa de mesas con estados visuales y acciones
 * - Grid de mesas con estado por color
 * - Click en mesa libre → modal "Abrir mesa"
 * - Click en mesa ocupada → modal "Ver pedido" / "Cerrar cuenta"
 * - Maneja 4 estados: loading (skeleton), empty, error, data
 *
 * @module pages/restaurant/TablesPage
 */
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

type TableStatus = "free" | "occupied" | "reserved" | "closed";

interface RestaurantTable {
  id: number;
  number: number;
  capacity: number;
  status: TableStatus;
  section: string | null;
  opened_at?: string;
  guest_count?: number;
}

const STATUS_CONFIG: Record<TableStatus, { color: string; bg: string; label: string }> = {
  free: { color: "text-green-600", bg: "bg-green-50 border-green-300", label: "Libre" },
  occupied: { color: "text-yellow-600", bg: "bg-yellow-50 border-yellow-300", label: "Ocupada" },
  reserved: { color: "text-red-600", bg: "bg-red-50 border-red-300", label: "Reservada" },
  closed: { color: "text-gray-500", bg: "bg-gray-100 border-gray-300", label: "Cerrada" },
};

export function TablesPage() {
  const [tables, setTables] = useState<RestaurantTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<RestaurantTable | null>(null);
  const [showModal, setShowModal] = useState(false);

  const fetchTables = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Wait for backend endpoint: GET /api/v1/restaurant/tables
      const res = await fetch("/api/v1/restaurant/tables");
      if (!res.ok) throw new Error("Error al cargar mesas");
      const data = await res.json();
      setTables(data.tables ?? data);
    } catch (err: unknown) {
      // Fallback: show empty with error
      setError(err instanceof Error ? err.message : "Error de conexión");
      setTables([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  const handleTableClick = (table: RestaurantTable) => {
    setSelectedTable(table);
    setShowModal(true);
  };

  const handleOpenTable = async (guestCount: number) => {
    if (!selectedTable) return;
    try {
      const res = await fetch(`/api/v1/restaurant/tables/${selectedTable.id}/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guest_count: guestCount }),
      });
      if (!res.ok) throw new Error("Error al abrir mesa");
      await fetchTables();
      setShowModal(false);
      setSelectedTable(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al abrir mesa");
    }
  };

  const handleClose = () => {
    setShowModal(false);
    setSelectedTable(null);
  };

  // ─── Loading state ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-1" />
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Error state ───
  if (error && tables.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🪑 Mapa de Mesas</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="text-lg mb-2">⚠️ Error al cargar las mesas</p>
          <p className="text-sm mb-4">{error}</p>
          <button
            onClick={fetchTables}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty state ───
  if (tables.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🪑 Mapa de Mesas</h2>
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🪑</span>
          <p className="text-lg font-medium">No hay mesas configuradas</p>
          <p className="text-sm mt-1">
            Configurá las mesas del salón desde la sección de Administración.
          </p>
        </div>
      </div>
    );
  }

  // ─── Data state ───
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🪑 Mapa de Mesas</h2>
          <p className="text-sm text-brand-text-secondary">
            {tables.filter((t) => t.status === "free").length} libre(s) ·{" "}
            {tables.filter((t) => t.status === "occupied").length} ocupada(s)
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchTables} className="underline text-xs">Reintentar</button>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {tables.map((table) => {
          const cfg = STATUS_CONFIG[table.status];
          return (
            <button
              key={table.id}
              onClick={() => handleTableClick(table)}
              className={`p-4 rounded-xl border-2 text-center transition-all hover:shadow-md ${cfg.bg}`}
            >
              <div className={`text-2xl font-bold ${cfg.color}`}>
                {table.number}
              </div>
              <div className={`text-xs font-semibold mt-1 ${cfg.color}`}>
                {cfg.label}
              </div>
              <div className="text-xs text-brand-text-secondary mt-1">
                {table.capacity} pax
              </div>
              {table.section && (
                <div className="text-xs text-brand-text-secondary">
                  {table.section}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Modal — Abrir mesa / Ver pedido */}
      {showModal && selectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            {selectedTable.status === "free" || selectedTable.status === "reserved" ? (
              <OpenTableForm
                table={selectedTable}
                onOpen={handleOpenTable}
                onClose={handleClose}
              />
            ) : (
              <OccupiedTableInfo
                table={selectedTable}
                onClose={handleClose}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Subcomponentes del modal ───

function OpenTableForm({
  table,
  onOpen,
  onClose,
}: {
  table: RestaurantTable;
  onOpen: (guests: number) => Promise<void>;
  onClose: () => void;
}) {
  const [guestCount, setGuestCount] = useState(table.capacity);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    await onOpen(guestCount);
    setSubmitting(false);
  };

  return (
    <div>
      <h3 className="text-lg font-bold text-brand-text-primary mb-2">
        Abrir Mesa #{table.number}
      </h3>
      <p className="text-sm text-brand-text-secondary mb-4">
        Capacidad: {table.capacity} personas
      </p>
      <div className="mb-4">
        <label className="block text-sm font-medium text-brand-text-primary mb-1">
          N° de comensales
        </label>
        <input
          type="number"
          min={1}
          max={table.capacity}
          value={guestCount}
          onChange={(e) => setGuestCount(Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
            focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"
        />
      </div>
      <div className="flex gap-2 justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          disabled={submitting}
        >
          Cancelar
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
            hover:bg-brand-secondary disabled:opacity-50"
        >
          {submitting ? "Abriendo..." : "Abrir Mesa"}
        </button>
      </div>
    </div>
  );
}

function OccupiedTableInfo({
  table,
  onClose,
}: {
  table: RestaurantTable;
  onClose: () => void;
}) {
  return (
    <div>
      <h3 className="text-lg font-bold text-brand-text-primary mb-2">
        Mesa #{table.number}
      </h3>
      <div className="text-sm space-y-2 mb-4">
        <p>
          <span className="font-medium">Estado:</span>{" "}
          <span className="text-yellow-600">{STATUS_CONFIG[table.status].label}</span>
        </p>
        {table.guest_count && (
          <p>
            <span className="font-medium">Comensales:</span> {table.guest_count}
          </p>
        )}
        {table.opened_at && (
          <p>
            <span className="font-medium">Abierta desde:</span>{" "}
            {new Date(table.opened_at).toLocaleTimeString("es-PE", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
      <div className="flex gap-2">
        <a
          href={`/ventas/nueva?table=${table.number}`}
          className="flex-1 px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
            hover:bg-brand-secondary text-center"
        >
          Ver / Tomar Pedido
        </a>
      </div>
      <div className="mt-3">
        <button
          onClick={onClose}
          className="w-full px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
