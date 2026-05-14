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
import { useState, useEffect, useCallback, useMemo } from "react";
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
  order_id?: number | null;
}

interface MenuModifier {
  id: number;
  name: string;
  price_adjustment: number;
  max_select?: number;
}

interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
  active: boolean;
  modifiers?: MenuModifier[] | null;
}

interface OrderItem {
  id?: number;
  menu_item_id: number;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers?: { id: number; name: string; price_adjustment: number }[];
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

  // Menu / Order state
  const [showMenuSelector, setShowMenuSelector] = useState(false);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [addingItemId, setAddingItemId] = useState<number | null>(null);
  const [sendingToKitchen, setSendingToKitchen] = useState(false);
  const [orderToast, setOrderToast] = useState<string | null>(null);

  // Modifier modal state
  const [showModifierModal, setShowModifierModal] = useState(false);
  const [selectedModifiers, setSelectedModifiers] = useState<number[]>([]);
  const [pendingMenuItem, setPendingMenuItem] = useState<MenuItem | null>(null);

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

  // ─── Menu / Order handlers ───
  const fetchMenu = useCallback(async () => {
    setMenuLoading(true);
    try {
      const res = await authFetch("/api/v1/restaurant/menu");
      if (!res.ok) throw new Error("Error al cargar menú");
      const data = await res.json();
      const items: MenuItem[] = (data.items ?? data).filter((i: MenuItem) => i.active);
      setMenuItems(items);
    } catch {
      setMenuItems([]);
    } finally {
      setMenuLoading(false);
    }
  }, []);

  const addToOrder = async (menuItem: MenuItem, modifierIds: number[] = [], skipModifiers = false) => {
    if (!selectedTable) return;

    // If item has modifiers and no modifierIds passed, show modifier modal (unless skipping)
    if (!skipModifiers && menuItem.modifiers && menuItem.modifiers.length > 0 && modifierIds.length === 0 && !showModifierModal) {
      setPendingMenuItem(menuItem);
      setSelectedModifiers([]);
      setShowModifierModal(true);
      return;
    }

    setAddingItemId(menuItem.id);
    const modifiers = modifierIds.map((id) => {
      const mod = menuItem.modifiers?.find((m) => m.id === id);
      return mod ? { id: mod.id, name: mod.name, price_adjustment: mod.price_adjustment } : null;
    }).filter(Boolean);

    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${selectedTable.id}/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: [{
            menu_item_id: menuItem.id,
            quantity: 1,
            modifiers,
            notes: "",
          }],
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al agregar");
      }
      const data = await res.json();
      setOrderItems(data.items ?? [...orderItems, { menu_item_id: menuItem.id, name: menuItem.name, quantity: 1, unit_price: menuItem.price }]);
      const newOrderId = data.id || data.order_id;
      if (newOrderId && selectedTable.order_id !== newOrderId) {
        setSelectedTable({ ...selectedTable, order_id: newOrderId });
      }
      const modNames = modifiers.length > 0 ? ` (${modifiers.map((m: any) => m.name).join(", ")})` : "";
      setOrderToast(`✅ ${menuItem.name}${modNames} agregado`);
      setTimeout(() => setOrderToast(null), 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al agregar");
    } finally {
      setAddingItemId(null);
      setPendingMenuItem(null);
    }
  };

  const sendToKitchen = async () => {
    const orderId = selectedTable?.order_id;
    if (!orderId) return;
    setSendingToKitchen(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/orders/${orderId}/send-to-kitchen`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al enviar");
      }
      setOrderToast("📨 Pedido enviado a cocina");
      setTimeout(() => setOrderToast(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al enviar");
    } finally {
      setSendingToKitchen(false);
    }
  };

  const handleIncrement = async (item: OrderItem) => {
    const menuItem = menuItems.find((m) => m.id === item.menu_item_id);
    if (menuItem) addToOrder(menuItem, [], true);
  };

  const handleDecrement = async (item: OrderItem) => {
    if (!selectedTable?.order_id) return;
    setAddingItemId(item.menu_item_id);
    try {
      const res = await authFetch(
        `/api/v1/restaurant/orders/${selectedTable.order_id}/items/${item.menu_item_id}`,
        { method: "DELETE" },
      );
      if (!res.ok) throw new Error("Error al quitar item");
      const data = await res.json();
      setOrderItems(data.items ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setAddingItemId(null);
    }
  };

  // Agrupar items por menu_item_id + modifiers para el ticket
  const groupedItems = useMemo(() => {
    const map = new Map<string, OrderItem & { displayModifiers: string; unitPriceWithMods: number }>();
    orderItems.forEach((item) => {
      const modIds = (item.modifiers || [])
        .map((m) => m.id)
        .sort((a, b) => a - b)
        .join(",");
      const key = `${item.menu_item_id}|${modIds}`;
      const modsTotal = (item.modifiers || []).reduce(
        (sum, m) => sum + (m.price_adjustment || 0),
        0,
      );
      if (map.has(key)) {
        const existing = map.get(key)!;
        existing.quantity += item.quantity || 1;
      } else {
        map.set(key, {
          ...item,
          quantity: item.quantity || 1,
          unitPriceWithMods: (item.unit_price || 0) + modsTotal,
          displayModifiers: (item.modifiers || []).map((m) => m.name).join(", "),
        });
      }
    });
    return Array.from(map.values());
  }, [orderItems]);

  // ─── Click handlers ───
  const handleTableClick = (table: Table) => {
    setSelectedTable(table);
    setShowMenuSelector(false);
    setOrderItems([]);
    setShowOpenModal(true);
    if (table.status === "available" || table.status === "reserved") {
      setOpenGuests(2);
      setOpenWaiter("");
    }
    if (table.status === "occupied") {
      fetchMenu();
      // No hay order_id en la lista de mesas — se obtiene al agregar items
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
                <div className="space-y-2">
                  <button onClick={handleOpenTable} disabled={submitting || !openWaiter.trim()}
                    className="w-full py-2.5 text-sm rounded-lg bg-brand-primary text-white font-medium
                      hover:bg-brand-secondary disabled:opacity-50">
                    {submitting ? "Abriendo..." : "🔓 Abrir Mesa"}
                  </button>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => handleReserve(selectedTable.id)}
                      className="py-2 text-sm rounded-lg bg-yellow-500 text-white hover:bg-yellow-600"
                      disabled={submitting}>
                      📅 Reservar
                    </button>
                    <button onClick={() => openEditModal(selectedTable)}
                      className="py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                      ✏️ Editar
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => {
                      if (window.confirm(`¿Eliminar mesa ${selectedTable.number}?`)) {
                        setShowOpenModal(false);
                        handleDeleteTable(selectedTable.id);
                      }
                    }} className="py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                      🗑️ Eliminar
                    </button>
                    <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); }}
                      className="py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50" disabled={submitting}>
                      Cancelar
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
                <div className="space-y-2">
                  <button onClick={() => handleFree(selectedTable.id)}
                    className="w-full py-2.5 text-sm rounded-lg bg-gray-600 text-white font-medium
                      hover:bg-gray-700" disabled={submitting}>
                    🔓 Liberar Reserva
                  </button>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => openEditModal(selectedTable)}
                      className="py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                      ✏️ Editar
                    </button>
                    <button onClick={() => {
                      if (window.confirm(`¿Eliminar mesa ${selectedTable.number}?`)) {
                        setShowOpenModal(false);
                        handleDeleteTable(selectedTable.id);
                      }
                    }} className="py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                      🗑️ Eliminar
                    </button>
                  </div>
                  <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); }}
                    className="w-full py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                    disabled={submitting}>
                    Cancelar
                  </button>
                </div>
              </>
            )}

            {/* ─── OCCUPIED: tomar pedido + enviar cocina ─── */}
            {selectedTable.status === "occupied" && (
              <div className="space-y-3">
                <div className="text-sm text-brand-text-secondary">
                  <p>Capacidad: {selectedTable.capacity} pers.</p>
                  <p>Sección: {selectedTable.section ?? "General"}</p>
                  {selectedTable.guests && <p>Comensales: {selectedTable.guests}</p>}
                  {selectedTable.waiter_name && <p>Mesero: {selectedTable.waiter_name}</p>}
                  {selectedTable.total_provisional !== undefined && (
                    <p className="font-bold text-brand-text-primary mt-1">
                      Total prov: S/ {selectedTable.total_provisional.toFixed(2)}
                    </p>
                  )}
                </div>

                {/* Current order items */}
                {orderItems.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-3 mb-2">
                    <h4 className="text-xs font-bold text-brand-text-primary mb-2">📋 Pedido Actual</h4>
                    <div className="max-h-32 overflow-y-auto space-y-0.5">
                      {groupedItems.map((item, i) => (
                        <div key={i} className="flex justify-between text-xs py-1">
                          <div className="flex items-center gap-1 flex-1 min-w-0">
                            <button
                              onClick={() => handleDecrement(item)}
                              disabled={addingItemId === item.menu_item_id}
                              className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center
                                text-xs font-bold hover:bg-gray-300 disabled:opacity-40 flex-shrink-0"
                              style={{ minWidth: 20, minHeight: 20 }}
                              aria-label={`Quitar ${item.name}`}
                            >
                              −
                            </button>
                            <span className="w-4 text-center font-medium flex-shrink-0">{item.quantity}</span>
                            <button
                              onClick={() => handleIncrement(item)}
                              disabled={addingItemId === item.menu_item_id}
                              className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center
                                text-xs font-bold hover:bg-gray-300 disabled:opacity-40 flex-shrink-0"
                              style={{ minWidth: 20, minHeight: 20 }}
                              aria-label={`Agregar ${item.name}`}
                            >
                              +
                            </button>
                            <span className="ml-1 truncate">{item.name}</span>
                            {item.displayModifiers && (
                              <span className="text-[10px] text-gray-400 truncate">
                                ({item.displayModifiers})
                              </span>
                            )}
                          </div>
                          <span className="font-medium flex-shrink-0 ml-2">
                            S/ {(item.unitPriceWithMods * item.quantity).toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="flex justify-between text-xs font-bold pt-2 border-t border-gray-300 mt-2">
                      <span>TOTAL</span>
                      <span>S/ {groupedItems.reduce((sum, item) => sum + (item.unitPriceWithMods * item.quantity), 0).toFixed(2)}</span>
                    </div>
                  </div>
                )}

                {/* Toast confirmation */}
                {orderToast && (
                  <div className="p-2 rounded-lg bg-green-50 border border-green-200 text-green-700 text-xs text-center">
                    {orderToast}
                  </div>
                )}

                {/* Menu selector toggle */}
                {!showMenuSelector ? (
                  <button onClick={() => setShowMenuSelector(true)}
                    className="w-full py-2.5 text-sm rounded-lg bg-brand-primary text-white font-medium
                      hover:bg-brand-secondary">
                    🍽️ Tomar Pedido
                  </button>
                ) : (
                  <div className="border border-gray-200 rounded-lg p-3 max-h-64 overflow-y-auto">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold text-brand-text-primary">📜 Menú</h4>
                      <button onClick={() => setShowMenuSelector(false)}
                        className="text-xs text-brand-text-secondary hover:underline">
                        Ocultar
                      </button>
                    </div>
                    {menuLoading ? (
                      <p className="text-xs text-brand-text-secondary text-center py-4">Cargando menú...</p>
                    ) : menuItems.length === 0 ? (
                      <p className="text-xs text-brand-text-secondary text-center py-4">No hay ítems disponibles</p>
                    ) : (
                      <MenuGrouped items={menuItems} addingId={addingItemId} onAdd={addToOrder} />
                    )}
                  </div>
                )}

                {/* Send to kitchen */}
                {orderItems.length > 0 && selectedTable.order_id && (
                  <button onClick={sendToKitchen} disabled={sendingToKitchen}
                    className="w-full py-2.5 text-sm rounded-lg bg-orange-500 text-white font-medium
                      hover:bg-orange-600 disabled:opacity-50">
                    {sendingToKitchen ? "Enviando..." : "📨 Enviar a Cocina"}
                  </button>
                )}

                <button onClick={() => { setShowOpenModal(false); setSelectedTable(null); setShowMenuSelector(false); }}
                  className="w-full py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
                  Cerrar
                </button>
              </div>
            )}

            {/* ─── CLEANING: solo info ─── */}
            {selectedTable.status === "cleaning" && (
              <>
                <div className="mb-4 text-sm text-brand-text-secondary">
                  <p>Capacidad: {selectedTable.capacity} pers.</p>
                  <p>Sección: {selectedTable.section ?? "General"}</p>
                  <p>Estado: Limpieza</p>
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

      {/* Modal: Modificadores */}
      {showModifierModal && pendingMenuItem && pendingMenuItem.modifiers && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-brand-text-primary mb-1">
              {pendingMenuItem.name}
            </h3>
            <p className="text-xs text-brand-text-secondary mb-4">
              Personalizá tu pedido
            </p>
            <div className="space-y-2">
              {pendingMenuItem.modifiers.map((mod) => {
                const isSelected = selectedModifiers.includes(mod.id);
                return (
                  <label
                    key={mod.id}
                    className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                      isSelected
                        ? "border-brand-primary bg-brand-primary/5"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                    style={{ minHeight: 44 }}
                  >
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium">{mod.name}</span>
                      {mod.price_adjustment > 0 && (
                        <span className="text-xs text-orange-600 ml-1">
                          +S/ {mod.price_adjustment.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ml-2 ${
                        isSelected
                          ? "bg-brand-primary border-brand-primary"
                          : "border-gray-300"
                      }`}
                    >
                      {isSelected && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {
                        setSelectedModifiers((prev) =>
                          prev.includes(mod.id)
                            ? prev.filter((id) => id !== mod.id)
                            : [...prev, mod.id],
                        );
                      }}
                      className="sr-only"
                    />
                  </label>
                );
              })}
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => {
                  setShowModifierModal(false);
                  setPendingMenuItem(null);
                }}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (pendingMenuItem) {
                    addToOrder(pendingMenuItem, selectedModifiers);
                  }
                  setShowModifierModal(false);
                }}
                className="px-4 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary"
              >
                Agregar
              </button>
            </div>
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

/** Menu items grouped by category with Add buttons */
function MenuGrouped({
  items,
  addingId,
  onAdd,
}: {
  items: MenuItem[];
  addingId: number | null;
  onAdd: (item: MenuItem) => void;
}) {
  const grouped = items.reduce<Record<string, MenuItem[]>>((acc, item) => {
    const cat = item.category || "General";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  return (
    <div className="space-y-2">
      {Object.entries(grouped).map(([cat, catItems]) => (
        <div key={cat}>
          <div className="text-[10px] font-semibold uppercase text-brand-text-secondary mb-1">
            {cat}
          </div>
          <div className="space-y-0.5">
            {catItems.map((item) => (
              <div key={item.id} className="flex items-center justify-between py-1 px-2 rounded hover:bg-gray-50">
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-medium">{item.name}</span>
                  <span className="text-xs text-brand-text-secondary ml-1">
                    S/ {item.price.toFixed(2)}
                  </span>
                </div>
                <button
                  onClick={() => onAdd(item)}
                  disabled={addingId === item.id}
                  className="ml-2 px-2 py-1 text-xs rounded bg-brand-primary/10 text-brand-primary
                    hover:bg-brand-primary/20 disabled:opacity-50 flex-shrink-0"
                  style={{ minWidth: 44, minHeight: 28 }}
                >
                  {addingId === item.id ? "..." : "➕"}
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
