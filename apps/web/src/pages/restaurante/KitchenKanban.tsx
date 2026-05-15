/**
 * KitchenKanban — Pantalla de cocina tipo Kanban.
 *
 * HU-F0-008: Kanban de comandas con columnas por estado
 * - Columnas: Pendientes, Preparando, Listos, Entregados
 * - Polling cada 10s para nuevas comandas
 * - Timer: warning >15min (naranja), crítico >30min (rojo)
 * - Botón "✅ Listo" para mover a Listos
 * - Botón "🗑️ Cancelar" con modal de motivo
 *
 * @module pages/restaurante/KitchenKanban
 */
import { authFetch } from "@/services/authFetch";
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface KitchenOrder {
  id: number;
  sale_id: number;
  table_id: number;
  table_number?: string;
  status: "pending" | "preparing" | "ready" | "delivered" | "cancelled";
  items: KitchenOrderItem[];
  notes: string | null;
  ordered_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface KitchenOrderItem {
  menu_item_id: number;
  name: string;
  quantity: number;
  modifiers_applied?: string[];
  modifiers?: Array<{ id?: number; name?: string; price_adjustment?: number }>;
  notes?: string;
}

interface TakeawayKitchenOrder {
  id: number;
  customer_name: string;
  pickup_time: string | null;
  status: "pending" | "preparing" | "ready" | "picked_up" | "cancelled";
  items: TakeawayKitchenItem[];
  notes: string | null;
  ordered_at?: string;
  created_at?: string;
}

interface TakeawayKitchenItem {
  name: string;
  quantity: number;
  modifiers?: Array<{ id?: number; name?: string; price_adjustment?: number }>;
}

const COLUMNS: { key: KitchenOrder["status"]; label: string; icon: string }[] = [
  { key: "pending", label: "Pendientes", icon: "⏳" },
  { key: "preparing", label: "Preparando", icon: "🔥" },
  { key: "ready", label: "Listos", icon: "✅" },
  { key: "delivered", label: "Entregados", icon: "📤" },
];

const TAKEAWAY_COLUMNS: {
  key: TakeawayKitchenOrder["status"];
  label: string;
  icon: string;
}[] = [
  { key: "pending", label: "Pendientes", icon: "⏳" },
  { key: "preparing", label: "Preparando", icon: "🔥" },
  { key: "ready", label: "Listos", icon: "✅" },
];

export function KitchenKanban() {
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelOrder, setCancelOrder] = useState<KitchenOrder | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  // Takeaway orders
  const [takeawayOrders, setTakeawayOrders] = useState<TakeawayKitchenOrder[]>([]);
  const [takeawayLoading, setTakeawayLoading] = useState(true);

  const fetchOrders = useCallback(async () => {
    try {
      const res = await authFetch("/api/v1/restaurant/orders/active");
      if (!res.ok) throw new Error("Error al cargar comandas");
      const data = await res.json();
      setOrders(data.orders ?? data);
      setError(null);
    } catch (err: unknown) {
      if (!orders.length) {
        setError(err instanceof Error ? err.message : "Error de conexión");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTakeawayOrders = useCallback(async () => {
    try {
      const res = await authFetch(
        "/api/v1/restaurant/takeaway?status=pending,preparing,ready",
      );
      if (!res.ok) throw new Error("Error al cargar takeaway");
      const data = await res.json();
      setTakeawayOrders(data.orders ?? data);
    } catch {
      // non-critical — keep last known orders
    } finally {
      setTakeawayLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    fetchTakeawayOrders();
  }, [fetchOrders, fetchTakeawayOrders]);

  // Polling cada 30s (dining + takeaway)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchOrders();
      fetchTakeawayOrders();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchOrders, fetchTakeawayOrders]);

  const updateStatus = async (orderId: number, status: string) => {
    try {
      await authFetch(`/api/v1/restaurant/orders/${orderId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, status: status as KitchenOrder["status"] } : o)),
      );
    } catch {
      // ignore
    }
  };

  const updateTakeawayStatus = async (id: number, status: string) => {
    try {
      await authFetch(`/api/v1/restaurant/takeaway/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setTakeawayOrders((prev) =>
        prev.map((o) =>
          o.id === id
            ? { ...o, status: status as TakeawayKitchenOrder["status"] }
            : o,
        ),
      );
    } catch {
      // ignore
    }
  };

  const handleCancel = async () => {
    if (!cancelOrder) return;
    try {
      await authFetch(`/api/v1/restaurant/orders/${cancelOrder.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "cancelled", notes: cancelReason }),
      });
      setOrders((prev) =>
        prev.map((o) => (o.id === cancelOrder.id ? { ...o, status: "cancelled" as const } : o)),
      );
      setCancelOrder(null);
      setCancelReason("");
    } catch {
      // ignore
    }
  };

  const getMinutesElapsed = (orderedAt: string): number => {
    return Math.floor((Date.now() - new Date(orderedAt).getTime()) / 60000);
  };

  const getTimerClass = (minutes: number): string => {
    if (minutes > 30) return "bg-red-100 border-red-400 text-red-800";
    if (minutes > 15) return "bg-orange-100 border-orange-400 text-orange-800";
    return "";
  };

  if (loading || takeawayLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">👨‍🍳 Cocina</h2>
          <p className="text-sm text-brand-text-secondary">
            {orders.filter((o) => o.status !== "delivered" && o.status !== "cancelled").length}{" "}
            comandas activas
            {takeawayOrders.filter((o) => o.status !== "picked_up" && o.status !== "cancelled").length > 0 && (
              <span className="ml-2">
                + {takeawayOrders.filter((o) => o.status !== "picked_up" && o.status !== "cancelled").length} 🥡
              </span>
            )}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={fetchOrders} className="ml-2 underline text-xs">Reintentar</button>
        </div>
      )}

      {/* Kanban columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const colOrders = orders.filter((o) => o.status === col.key);
          return (
            <div key={col.key} className="bg-gray-50 rounded-xl p-3 min-h-[200px]">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-brand-text-primary">
                  {col.icon} {col.label}
                </h3>
                <span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full">
                  {colOrders.length}
                </span>
              </div>
              <div className="space-y-2">
                {colOrders.map((order) => {
                  const minutes = getMinutesElapsed(order.ordered_at);
                  const timerClass = getTimerClass(minutes);
                  return (
                    <div
                      key={order.id}
                      className={`bg-white rounded-lg border p-3 shadow-sm ${
                        order.status === "cancelled" ? "opacity-50 line-through" : ""
                      } ${timerClass}`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold">
                          {order.table_number ?? `Mesa ${order.table_id}`}
                        </span>
                        <span className="text-xs text-brand-text-secondary">
                          {minutes} min
                        </span>
                      </div>
                      {order.items.map((item, i) => (
                        <div key={i} className="text-sm">
                          <span className="font-medium">{item.quantity}x</span>{" "}
                          {item.name}
                          {(item.modifiers_applied || item.modifiers || []).length > 0 && (
                            <span className="text-xs text-brand-text-secondary block">
                              {(item.modifiers_applied || (item.modifiers || []).map((m: any) => m.name || m)).join(", ")}
                            </span>
                          )}
                          {item.notes && (
                            <span className="text-xs text-brand-warning block">
                              📝 {item.notes}
                            </span>
                          )}
                        </div>
                      ))}
                      {order.notes && (
                        <p className="text-xs text-brand-text-secondary mt-1 italic">
                          {order.notes}
                        </p>
                      )}

                      {/* Action buttons */}
                      <div className="flex gap-2 mt-2 pt-2 border-t border-gray-100">
                        {col.key === "pending" && (
                          <button
                            onClick={() => updateStatus(order.id, "preparing")}
                            className="flex-1 text-xs py-1 px-2 bg-blue-500 text-white rounded"
                          >
                            🔥 Iniciar
                          </button>
                        )}
                        {col.key === "preparing" && (
                          <button
                            onClick={() => updateStatus(order.id, "ready")}
                            className="flex-1 text-xs py-1 px-2 bg-green-500 text-white rounded"
                          >
                            ✅ Listo
                          </button>
                        )}
                        {col.key === "ready" && (
                          <button
                            onClick={() => updateStatus(order.id, "delivered")}
                            className="flex-1 text-xs py-1 px-2 bg-gray-500 text-white rounded"
                          >
                            📤 Entregado
                          </button>
                        )}
                        {(col.key === "pending" || col.key === "preparing") && (
                          <button
                            onClick={() => setCancelOrder(order)}
                            className="text-xs py-1 px-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
                          >
                            🗑️
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* 🥡 Takeaway section */}
      {takeawayOrders.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 pt-2 border-t-2 border-dashed border-gray-200">
            <h3 className="text-lg font-bold text-brand-text-primary">🥡 Para llevar</h3>
            <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              {takeawayOrders.filter((o) => o.status !== "picked_up" && o.status !== "cancelled").length} activos
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TAKEAWAY_COLUMNS.map((col) => {
              const colOrders = takeawayOrders.filter((o) => o.status === col.key);
              return (
                <div key={col.key} className="bg-amber-50/60 rounded-xl p-3 min-h-[120px]">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-bold text-brand-text-primary">
                      {col.icon} {col.label}
                    </h3>
                    <span className="text-xs bg-amber-100 px-2 py-0.5 rounded-full">
                      {colOrders.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {colOrders.map((order) => {
                      const orderTime = order.ordered_at ?? order.created_at;
                      const minutes = orderTime ? getMinutesElapsed(orderTime) : null;
                      const timerClass = minutes !== null ? getTimerClass(minutes) : "";
                      return (
                        <div
                          key={order.id}
                          className={`bg-white rounded-lg border p-3 shadow-sm ${
                            order.status === "cancelled" ? "opacity-50 line-through" : ""
                          } ${timerClass}`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold">
                              🧑 {order.customer_name}
                            </span>
                            {minutes !== null && (
                              <span className="text-xs text-brand-text-secondary">
                                {minutes} min
                              </span>
                            )}
                          </div>
                          {order.items.map((item, i) => (
                            <div key={i} className="text-sm">
                              <span className="font-medium">{item.quantity}x</span>{" "}
                              {item.name}
                              {item.modifiers && item.modifiers.length > 0 && (
                                <span className="text-xs text-brand-text-secondary block">
                                  ({item.modifiers.map((m) => m.name).filter(Boolean).join(", ")})
                                </span>
                              )}
                            </div>
                          ))}
                          {order.pickup_time && (
                            <p className="text-xs text-amber-700 mt-1">
                              🕐 Recojo: {new Date(order.pickup_time).toLocaleTimeString("es-PE", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </p>
                          )}
                          {order.notes && (
                            <p className="text-xs text-brand-text-secondary mt-1 italic">
                              📝 {order.notes}
                            </p>
                          )}

                          {/* Action buttons */}
                          <div className="flex gap-2 mt-2 pt-2 border-t border-gray-100">
                            {col.key === "pending" && (
                              <button
                                onClick={() => updateTakeawayStatus(order.id, "preparing")}
                                className="flex-1 text-xs py-1 px-2 bg-blue-500 text-white rounded"
                              >
                                🔥 Preparando
                              </button>
                            )}
                            {col.key === "preparing" && (
                              <button
                                onClick={() => updateTakeawayStatus(order.id, "ready")}
                                className="flex-1 text-xs py-1 px-2 bg-green-500 text-white rounded"
                              >
                                ✅ Listo
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    {colOrders.length === 0 && (
                      <p className="text-xs text-brand-text-secondary text-center py-4">
                        Sin pedidos
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Cancel modal */}
      {cancelOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              Cancelar Comanda
            </h3>
            <p className="text-sm text-brand-text-secondary mb-3">
              ¿Por qué se cancela la comanda de la{" "}
              {cancelOrder.table_number ?? `Mesa ${cancelOrder.table_id}`}?
            </p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={2}
              placeholder="Motivo de cancelación"
            />
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setCancelOrder(null)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              >
                Volver
              </button>
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
              >
                Confirmar Cancelación
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
