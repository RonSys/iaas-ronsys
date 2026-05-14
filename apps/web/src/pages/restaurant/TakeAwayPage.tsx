/**
 * TakeAwayPage — Gestión de pedidos para llevar.
 *
 * HU-F0-014: Listado de pedidos takeaway + creación + alertas
 * - Ordenado por hora de recogida
 * - Estados: Pendiente → En preparación → Listo → Recogido
 * - Alertas visuales para pedidos atrasados (>30 min después de pickup_time)
 * - Modal de creación con búsqueda de items
 *
 * @module pages/restaurant/TakeAwayPage
 */
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

type TakeawayStatus = "pending" | "preparing" | "ready" | "picked_up" | "cancelled";

interface TakeawayOrder {
  id: number;
  customer_name: string | null;
  customer_phone: string | null;
  status: TakeawayStatus;
  items: Array<{ name: string; quantity: number }>;
  pickup_time: string | null;
  created_at: string;
}

const STATUS_LABELS: Record<TakeawayStatus, string> = {
  pending: "Pendiente",
  preparing: "En preparación",
  ready: "Listo",
  picked_up: "Recogido",
  cancelled: "Cancelado",
};

const STATUS_COLORS: Record<TakeawayStatus, string> = {
  pending: "bg-yellow-100 text-yellow-700 border-yellow-300",
  preparing: "bg-blue-100 text-blue-700 border-blue-300",
  ready: "bg-green-100 text-green-700 border-green-300",
  picked_up: "bg-gray-100 text-gray-500 border-gray-300",
  cancelled: "bg-red-100 text-red-500 border-red-300",
};

export function TakeAwayPage() {
  const [orders, setOrders] = useState<TakeawayOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/restaurant/takeaway");
      if (!res.ok) throw new Error("Error al cargar pedidos");
      const data = await res.json();
      setOrders(data.orders ?? data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const updateStatus = async (id: number, status: TakeawayStatus) => {
    try {
      const res = await fetch(`/api/v1/restaurant/takeaway/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("Error al actualizar");
      await fetchOrders();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar");
    }
  };

  const markPickup = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/restaurant/takeaway/${id}/pickup`, {
        method: "PATCH",
      });
      if (!res.ok) throw new Error("Error al marcar recogido");
      await fetchOrders();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar");
    }
  };

  const isDelayed = (order: TakeawayOrder) => {
    if (!order.pickup_time || order.status === "picked_up" || order.status === "cancelled") return false;
    const pickup = new Date(order.pickup_time).getTime();
    return Date.now() - pickup > 30 * 60 * 1000;
  };

  // Sort by pickup_time ascending
  const sortedOrders = [...orders].sort((a, b) => {
    if (!a.pickup_time) return 1;
    if (!b.pickup_time) return -1;
    return new Date(a.pickup_time).getTime() - new Date(b.pickup_time).getTime();
  });

  const formatTime = (t: string | null) => {
    if (!t) return "—";
    return new Date(t).toLocaleTimeString("es-PE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  // ─── Error ───
  if (error && orders.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">🥡 Take Away</h2>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-center">
          <p className="text-lg mb-2">⚠️ {error}</p>
          <button onClick={fetchOrders} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // ─── Empty ───
  if (orders.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-brand-text-primary">🥡 Take Away</h2>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
          >
            + Nuevo Takeaway
          </button>
        </div>
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🥡</span>
          <p className="text-lg font-medium">No hay pedidos takeaway</p>
          <p className="text-sm mt-1">Creá el primer pedido para llevar.</p>
        </div>
      </div>
    );
  }

  // ─── Data ───
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">🥡 Take Away</h2>
          <p className="text-sm text-brand-text-secondary">
            {orders.filter((o) => o.status !== "picked_up" && o.status !== "cancelled").length} activo(s)
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
        >
          + Nuevo Takeaway
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-2">
        {sortedOrders.map((order) => {
          const delayed = isDelayed(order);
          return (
            <div
              key={order.id}
              className={`p-4 rounded-lg border bg-brand-surface flex flex-col sm:flex-row sm:items-center
                justify-between gap-3 ${delayed ? "border-red-400 bg-red-50" : ""}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-brand-text-primary">
                    {order.customer_name || "Cliente"}
                  </span>
                  {delayed && (
                    <span className="text-xs bg-red-200 text-red-700 px-2 py-0.5 rounded-full font-medium">
                      ⚠️ Atrasado
                    </span>
                  )}
                </div>
                {order.customer_phone && (
                  <p className="text-xs text-brand-text-secondary">
                    📞 {order.customer_phone}
                  </p>
                )}
                <div className="text-xs text-brand-text-secondary mt-1">
                  {order.items.slice(0, 3).map((item) => `${item.quantity}x ${item.name}`).join(", ")}
                  {order.items.length > 3 && ` +${order.items.length - 3} más`}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[order.status]}`}
                  >
                    {STATUS_LABELS[order.status]}
                  </span>
                  <p className="text-xs text-brand-text-secondary mt-0.5">
                    🕐 {formatTime(order.pickup_time)}
                  </p>
                </div>
                <div className="flex gap-1.5">
                  {order.status === "pending" && (
                    <button
                      onClick={() => updateStatus(order.id, "preparing")}
                      className="px-2 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600"
                    >
                      Preparar
                    </button>
                  )}
                  {order.status === "ready" && (
                    <button
                      onClick={() => markPickup(order.id)}
                      className="px-2 py-1 text-xs rounded bg-green-500 text-white hover:bg-green-600"
                    >
                      Recogido
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal: Nuevo takeaway */}
      {showModal && (
        <NewTakeawayModal
          onClose={() => setShowModal(false)}
          onCreated={fetchOrders}
        />
      )}
    </div>
  );
}

// ─── Modal ───

function NewTakeawayModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [pickupTime, setPickupTime] = useState("");
  const [search, setSearch] = useState("");
  const [menuItems, setMenuItems] = useState<Array<{ id: number; name: string; price: number }>>([]);
  const [selected, setSelected] = useState<Record<number, number>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch("/api/v1/restaurant/menu")
      .then((r) => r.json())
      .then((data) => setMenuItems(data.items ?? data))
      .catch(() => {});
  }, []);

  const filteredItems = menuItems.filter(
    (i) => i.name.toLowerCase().includes(search.toLowerCase()),
  );

  const toggleItem = (id: number) => {
    setSelected((prev) =>
      prev[id] ? { ...prev, [id]: prev[id] + 1 } : { ...prev, [id]: 1 },
    );
  };

  const handleSubmit = async () => {
    if (!customerName.trim()) return;
    setSubmitting(true);
    try {
      const items = Object.entries(selected).map(([id, qty]) => ({
        menu_item_id: Number(id),
        quantity: qty,
        modifiers: [],
      }));
      const res = await fetch("/api/v1/restaurant/takeaway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: customerName,
          customer_phone: customerPhone || undefined,
          items,
          pickup_time: pickupTime || undefined,
        }),
      });
      if (!res.ok) throw new Error("Error al crear pedido");
      await onCreated();
      onClose();
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const totalItems = Object.values(selected).reduce((a, b) => a + b, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-bold text-brand-text-primary mb-4">
          Nuevo Pedido Take Away
        </h3>

        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nombre del cliente *</label>
            <input
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Ej: Juan Pérez"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Teléfono</label>
            <input
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="Opcional"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Hora de recogida</label>
            <input
              type="datetime-local"
              value={pickupTime}
              onChange={(e) => setPickupTime(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
          </div>
        </div>

        {/* Product search */}
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">Buscar ítems del menú</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg text-sm"
            placeholder="Escribí para buscar..."
          />
        </div>

        {/* Menu items grid */}
        <div className="grid grid-cols-2 gap-2 mb-4 max-h-48 overflow-y-auto">
          {filteredItems.map((item) => (
            <button
              key={item.id}
              onClick={() => toggleItem(item.id)}
              className={`p-2 rounded-lg text-xs border text-left transition-colors
                ${selected[item.id]
                  ? "bg-brand-primary/10 border-brand-primary"
                  : "border-gray-200 hover:bg-gray-50"
                }`}
            >
              <div className="font-medium truncate">{item.name}</div>
              <div className="text-brand-text-secondary">
                S/ {item.price.toFixed(2)}
                {selected[item.id] && (
                  <span className="ml-1 font-bold text-brand-primary">
                    x{selected[item.id]}
                  </span>
                )}
              </div>
            </button>
          ))}
          {filteredItems.length === 0 && (
            <p className="col-span-2 text-center text-xs text-brand-text-secondary py-4">
              Sin resultados
            </p>
          )}
        </div>

        {totalItems > 0 && (
          <div className="text-sm text-brand-text-secondary mb-4">
            {totalItems} ítem(s) seleccionado(s)
          </div>
        )}

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
            disabled={submitting || !customerName.trim() || totalItems === 0}
            className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white
              hover:bg-brand-secondary disabled:opacity-50"
          >
            {submitting ? "Creando..." : "Crear Pedido"}
          </button>
        </div>
      </div>
    </div>
  );
}
