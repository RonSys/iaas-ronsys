/**
 * TakeawayPage — Pedidos para llevar.
 *
 * HU-F0-009: Formulario de creación + listado de pedidos
 * - Formulario: nombre cliente, teléfono, hora recojo, items del menú
 * - Listado de pedidos pendientes por estado
 * - Estados: Pendiente, Preparando, Listo, Recogido, Cancelado
 *
 * @module pages/restaurante/TakeawayPage
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";

interface TakeawayOrder {
  id: number;
  sale_id: number;
  customer_name: string;
  customer_phone: string;
  pickup_time: string;
  status: "pending" | "preparing" | "ready" | "picked_up" | "cancelled";
  notes: string | null;
  items?: { name: string; quantity: number; price: number }[];
  total?: number;
}

interface MenuItemSimple {
  id: number;
  name: string;
  price: number;
  category: string;
  active: boolean;
}

interface CartItem {
  menuItem: MenuItemSimple;
  quantity: number;
}

const STATUS_CONFIG: Record<TakeawayOrder["status"], { label: string; color: string }> = {
  pending: { label: "Pendiente", color: "bg-yellow-100 text-yellow-800" },
  preparing: { label: "Preparando", color: "bg-blue-100 text-blue-800" },
  ready: { label: "Listo", color: "bg-green-100 text-green-800" },
  picked_up: { label: "Recogido", color: "bg-gray-100 text-gray-600" },
  cancelled: { label: "Cancelado", color: "bg-red-100 text-red-600" },
};

export function TakeawayPage() {
  const [orders, setOrders] = useState<TakeawayOrder[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItemSimple[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"new" | "list">("new");

  // Form state
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [pickupTime, setPickupTime] = useState("");
  const [notes, setNotes] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/restaurant/takeaway-orders");
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders ?? data);
      }
    } catch {
      // non-critical
    }
  }, []);

  const fetchMenu = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/restaurant/menu");
      if (res.ok) {
        const data = await res.json();
        setMenuItems((data.items ?? data).filter((i: MenuItemSimple) => i.active));
      }
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchOrders(), fetchMenu()]).finally(() => setLoading(false));
  }, [fetchOrders, fetchMenu]);

  const filteredMenu = useMemo(() => {
    if (!search.trim()) return menuItems;
    const q = search.toLowerCase();
    return menuItems.filter((item) => item.name.toLowerCase().includes(q));
  }, [menuItems, search]);

  const cartTotal = useMemo(
    () =>
      cart.reduce((sum, c) => sum + c.menuItem.price * c.quantity, 0),
    [cart],
  );

  const addToCart = (item: MenuItemSimple) => {
    setCart((prev) => {
      const existing = prev.find((c) => c.menuItem.id === item.id);
      if (existing) {
        return prev.map((c) =>
          c.menuItem.id === item.id ? { ...c, quantity: c.quantity + 1 } : c,
        );
      }
      return [...prev, { menuItem: item, quantity: 1 }];
    });
  };

  const removeFromCart = (index: number) => {
    setCart((prev) => prev.filter((_, i) => i !== index));
  };

  const updateCartQty = (index: number, qty: number) => {
    if (qty <= 0) {
      removeFromCart(index);
      return;
    }
    setCart((prev) => prev.map((c, i) => (i === index ? { ...c, quantity: qty } : c)));
  };

  const handleSubmit = async () => {
    if (!customerName.trim() || cart.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim() || null,
        pickup_time: pickupTime || null,
        notes: notes.trim() || null,
        items: cart.map((c) => ({
          menu_item_id: c.menuItem.id,
          quantity: c.quantity,
          unit_price: c.menuItem.price,
        })),
        payments: [
          {
            payment_method: "cash",
            amount: cartTotal,
            reference: null,
          },
        ],
      };
      const res = await fetch("/api/v1/restaurant/takeaway-orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al crear pedido");
      }
      setCustomerName("");
      setCustomerPhone("");
      setPickupTime("");
      setNotes("");
      setCart([]);
      setSuccessMessage("✅ Pedido Take Away registrado");
      setTimeout(() => setSuccessMessage(null), 4000);
      await fetchOrders();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSubmitting(false);
    }
  };

  const groupedMenu = useMemo(() => {
    const acc: Record<string, MenuItemSimple[]> = {};
    for (const item of filteredMenu) {
      const cat = item.category || "General";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(item);
    }
    return acc;
  }, [filteredMenu]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-4">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-brand-text-primary">🥡 Take Away</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab("new")}
            className={`px-3 py-1.5 rounded-lg text-sm ${
              activeTab === "new"
                ? "bg-brand-primary text-white"
                : "border border-gray-300 hover:bg-gray-50"
            }`}
          >
            + Nuevo Pedido
          </button>
          <button
            onClick={() => setActiveTab("list")}
            className={`px-3 py-1.5 rounded-lg text-sm ${
              activeTab === "list"
                ? "bg-brand-primary text-white"
                : "border border-gray-300 hover:bg-gray-50"
            }`}
          >
            📋 Pedidos ({orders.length})
          </button>
        </div>
      </div>

      {successMessage && (
        <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}

      {activeTab === "new" ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Menu selector */}
          <div className="lg:col-span-2 space-y-4">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="🔍 Buscar ítem del menú..."
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
            {Object.entries(groupedMenu).map(([cat, items]) => (
              <div key={cat}>
                <h3 className="text-sm font-bold text-brand-text-primary uppercase mb-2">{cat}</h3>
                <div className="grid grid-cols-2 gap-2">
                  {items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => addToCart(item)}
                      className="text-left p-3 rounded-lg border hover:border-brand-primary hover:bg-brand-primary/5 transition-all"
                    >
                      <div className="text-sm font-medium">{item.name}</div>
                      <div className="text-sm font-bold text-brand-primary">
                        S/ {item.price.toFixed(2)}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {filteredMenu.length === 0 && (
              <p className="text-sm text-brand-text-secondary text-center py-8">
                No se encontraron ítems
              </p>
            )}
          </div>

          {/* Cart + customer form */}
          <div className="space-y-4">
            <div className="card">
              <h3 className="font-bold text-brand-text-primary mb-3">🧾 Pedido Actual</h3>
              {cart.length === 0 ? (
                <p className="text-sm text-brand-text-secondary">
                  Seleccioná ítems del menú para agregar al pedido.
                </p>
              ) : (
                <div className="space-y-2 mb-4">
                  {cart.map((c, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="flex-1 truncate">{c.menuItem.name}</span>
                      <input
                        type="number"
                        min={1}
                        value={c.quantity}
                        onChange={(e) => updateCartQty(i, Number(e.target.value))}
                        className="w-14 px-1.5 py-0.5 border rounded text-center text-xs"
                      />
                      <span className="w-16 text-right font-medium">
                        S/ {(c.menuItem.price * c.quantity).toFixed(2)}
                      </span>
                      <button
                        onClick={() => removeFromCart(i)}
                        className="text-red-500 text-xs"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="text-lg font-bold text-right border-t pt-2">
                Total: S/ {cartTotal.toFixed(2)}
              </div>
            </div>

            <div className="card space-y-3">
              <h3 className="font-bold text-brand-text-primary">👤 Datos del Cliente</h3>
              <div>
                <label className="block text-xs font-medium mb-1">Nombre *</label>
                <input
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Nombre del cliente"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Teléfono</label>
                <input
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="999 888 777"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Hora de Recojo</label>
                <input
                  type="datetime-local"
                  value={pickupTime}
                  onChange={(e) => setPickupTime(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Notas</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  rows={2}
                  placeholder="Ej: Sin cebolla, extra picante"
                />
              </div>
              <button
                onClick={handleSubmit}
                disabled={submitting || !customerName.trim() || cart.length === 0}
                className="w-full py-2.5 bg-brand-success text-white rounded-lg text-sm font-medium
                  hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? "Registrando..." : "🥡 Confirmar Pedido"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Orders list */
        <div className="space-y-3">
          {orders.length === 0 ? (
            <div className="p-10 text-center text-brand-text-secondary">
              <span className="text-4xl block mb-3">🥡</span>
              <p className="text-lg font-medium">No hay pedidos Take Away</p>
            </div>
          ) : (
            orders.map((order) => (
              <div key={order.id} className="card flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">#{order.id}</span>
                    <span className="text-sm">{order.customer_name}</span>
                    {order.customer_phone && (
                      <span className="text-xs text-brand-text-secondary">📱 {order.customer_phone}</span>
                    )}
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${STATUS_CONFIG[order.status].color}`}
                    >
                      {STATUS_CONFIG[order.status].label}
                    </span>
                  </div>
                  {order.items && (
                    <p className="text-xs text-brand-text-secondary mt-1">
                      {order.items.map((i) => `${i.quantity}x ${i.name}`).join(", ")}
                    </p>
                  )}
                  {order.pickup_time && (
                    <p className="text-xs text-brand-text-secondary mt-0.5">
                      🕐 Recojo: {new Date(order.pickup_time).toLocaleString("es-PE")}
                    </p>
                  )}
                </div>
                {order.total !== undefined && (
                  <span className="text-sm font-bold">S/ {order.total.toFixed(2)}</span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
