/**
 * KitchenOrdersPage — Pantalla de comandas para cocina (Kanban).
 *
 * HU-F0-014: Tablero Kanban con 3 columnas + WebSocket en tiempo real
 * - Pendiente → Preparando → Listo
 * - WebSocket con fallback a polling cada 10s
 * - Alerta sonora/visual para nuevas órdenes
 *
 * @module pages/restaurant/KitchenOrdersPage
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

type KitchenStatus = "pending" | "preparing" | "ready" | "served" | "cancelled";

interface KitchenOrder {
  id: number;
  table_number: number | null;
  order_type: "dine_in" | "takeaway" | "delivery";
  status: KitchenStatus;
  items: Array<{
    menu_item_id: number;
    name: string;
    quantity: number;
    modifiers?: string[];
    notes?: string;
  }>;
  priority: number;
  notes: string | null;
  sent_at: string;
  completed_at: string | null;
}

const COLUMNS: { status: KitchenStatus; label: string; color: string }[] = [
  { status: "pending", label: "Pendiente", color: "bg-yellow-100 border-yellow-400" },
  { status: "preparing", label: "Preparando", color: "bg-blue-100 border-blue-400" },
  { status: "ready", label: "Listo", color: "bg-green-100 border-green-400" },
];

const STATUS_ORDER: KitchenStatus[] = ["pending", "preparing", "ready"];

export function KitchenOrdersPage() {
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/restaurant/orders?status=active");
      if (!res.ok) throw new Error("Error al cargar órdenes");
      const data = await res.json();
      setOrders(data.orders ?? data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }, []);

  // ─── WebSocket connection ───
  useEffect(() => {
    const tenantId = "current"; // Will be replaced with actual tenant ID
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/kitchen/${tenantId}`;

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "new_order" || msg.type === "order_ready") {
              fetchOrders();
              // Play notification sound for new orders
              if (msg.type === "new_order") {
                playNotificationSound();
              }
            } else if (msg.type === "full_state_sync") {
              setOrders(msg.orders ?? []);
            }
          } catch {
            // ignore parse errors
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          startPolling();
          // Reconnect after 3s
          reconnectTimer = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        startPolling();
      }
    }

    function startPolling() {
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchOrders, 10000);
      }
    }

    function playNotificationSound() {
      try {
        if (audioRef.current) {
          audioRef.current.play().catch(() => {});
        }
      } catch {
        // audio not available
      }
    }

    connect();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchOrders]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const updateStatus = async (orderId: number, newStatus: KitchenStatus) => {
    try {
      const res = await fetch(`/api/v1/restaurant/orders/${orderId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error("Error al actualizar estado");
      // Optimistic update
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, status: newStatus } : o)),
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar");
    }
  };

  const getElapsed = (sentAt: string) => {
    const diff = Date.now() - new Date(sentAt).getTime();
    const mins = Math.floor(diff / 60000);
    return mins < 1 ? "< 1 min" : `${mins} min`;
  };

  // ─── Loading ───
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ─── Error ───
  if (error && orders.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">📝 Comandas de Cocina</h2>
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
  const activeOrders = orders.filter((o) => STATUS_ORDER.includes(o.status));
  if (activeOrders.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-brand-text-primary">📝 Comandas de Cocina</h2>
        <div className="text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🍳</span>
          <p className="text-lg font-medium">No hay comandas activas</p>
          <p className="text-sm mt-1">
            Las nuevas órdenes aparecerán aquí automáticamente.
          </p>
        </div>
      </div>
    );
  }

  // ─── Data ───
  return (
    <div className="space-y-4">
      {/* Audio element for notification */}
      <audio ref={audioRef} src="/notification.mp3" preload="none" />

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">📝 Comandas de Cocina</h2>
          <p className="text-xs text-brand-text-secondary">
            {wsConnected ? "🟢 Tiempo real" : "🟡 Polling (10s)"}
            {" · "}
            {activeOrders.length} activa(s)
          </p>
        </div>
        <button
          onClick={fetchOrders}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          ↻ Refrescar
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {COLUMNS.map((col) => {
          const colOrders = orders.filter((o) => o.status === col.status);
          return (
            <div
              key={col.status}
              className={`rounded-xl border-2 p-3 min-h-[200px] ${col.color}`}
            >
              <h3 className="text-sm font-bold mb-3 flex items-center justify-between">
                <span>{col.label}</span>
                <span className="text-xs bg-white/60 px-2 py-0.5 rounded-full">
                  {colOrders.length}
                </span>
              </h3>

              {colOrders.length === 0 && (
                <p className="text-xs text-center text-brand-text-secondary py-4">
                  Sin órdenes
                </p>
              )}

              <div className="space-y-2">
                {colOrders.map((order) => (
                  <div
                    key={order.id}
                    className="p-3 rounded-lg bg-white shadow-sm border border-gray-100"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-bold">
                        {order.table_number
                          ? `Mesa ${order.table_number}`
                          : order.order_type === "takeaway"
                            ? "🥡 Take Away"
                            : "🛵 Delivery"}
                      </span>
                      <span className="text-xs text-brand-text-secondary">
                        {getElapsed(order.sent_at)}
                      </span>
                    </div>

                    <div className="space-y-1 mb-2">
                      {order.items.slice(0, 4).map((item, idx) => (
                        <div key={idx} className="text-xs">
                          <span className="font-medium">
                            {item.quantity}x {item.name}
                          </span>
                          {item.modifiers && item.modifiers.length > 0 && (
                            <span className="text-brand-text-secondary">
                              {" "}
                              ({item.modifiers.join(", ")})
                            </span>
                          )}
                        </div>
                      ))}
                      {order.items.length > 4 && (
                        <p className="text-xs text-brand-text-secondary">
                          +{order.items.length - 4} más
                        </p>
                      )}
                    </div>

                    {order.notes && (
                      <p className="text-xs text-yellow-700 bg-yellow-50 rounded px-1.5 py-0.5 mb-1.5">
                        📝 {order.notes}
                      </p>
                    )}

                    {/* Action buttons */}
                    <div className="flex gap-1.5 mt-2">
                      {col.status === "pending" && (
                        <button
                          onClick={() => updateStatus(order.id, "preparing")}
                          className="flex-1 px-2 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600"
                        >
                          Iniciar
                        </button>
                      )}
                      {col.status === "preparing" && (
                        <button
                          onClick={() => updateStatus(order.id, "ready")}
                          className="flex-1 px-2 py-1 text-xs rounded bg-green-500 text-white hover:bg-green-600"
                        >
                          Listo
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
