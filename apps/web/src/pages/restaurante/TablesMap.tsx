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
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect, useCallback, useMemo } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import {
  ModifierBottomSheet,
  type ModifierSelection,
} from "@/components/restaurante/ModifierBottomSheet";

interface Table {
  id: number;
  number: string;
  capacity: number;
  status: "available" | "occupied" | "reserved" | "cleaning";
  section: string | null;
  section_id?: number | null;
  section_name?: string | null;
  guests?: number;
  waiter_name?: string;
  opened_at?: string;
  total_provisional?: number;
  order_id?: number | null;
}

interface Section {
  id: number;
  name: string;
  description?: string;
  table_count: number;
}

interface MenuModifier {
  id: number;
  name: string;
  price_adjustment: number;
  max_select: number;
  modifier_group_id?: number | null;
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
  notes?: string;
}

interface TableFormData {
  number: string;
  capacity: number;
  section: string;
  section_id: number | null;
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
  const { user } = useAuth();
  const [openWaiter, setOpenWaiter] = useState(user?.full_name ?? "");
  const [showManualWaiter, setShowManualWaiter] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Create/Edit modal
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingTable, setEditingTable] = useState<Table | null>(null);
  const [formData, setFormData] = useState<TableFormData>({ number: "", capacity: 4, section: "", section_id: null });
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Sections state
  const [sections, setSections] = useState<Section[]>([]);
  const [sectionsLoading, setSectionsLoading] = useState(true);
  const [sectionFilter, setSectionFilter] = useState<number | "all" | "none">("all");

  // Menu / Order state
  const [showMenuSelector, setShowMenuSelector] = useState(false);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [addingItemId, setAddingItemId] = useState<number | null>(null);
  const [sendingToKitchen, setSendingToKitchen] = useState(false);
  const [orderSent, setOrderSent] = useState(false);
  const [orderToast, setOrderToast] = useState<string | null>(null);

  // Payment modal state
  const [showPayModal, setShowPayModal] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "yape" | "split">("cash");
  const [yapeAmount, setYapeAmount] = useState(0);
  const [cashAmount, setCashAmount] = useState(0);
  const [paymentReference, setPaymentReference] = useState("");
  const [paySubmitting, setPaySubmitting] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  // Modifier Bottom Sheet state
  const [modifierSheetOpen, setModifierSheetOpen] = useState(false);
  const [modifierItem, setModifierItem] = useState<MenuItem | null>(null);
  const [modifierNotes, setModifierNotes] = useState("");

  // ─── WebSocket para notificaciones de cocina ───
  const [waiterNotif, setWaiterNotif] = useState<string | null>(null);

  useEffect(() => {
    const tenantId = 1; // demo tenant
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/restaurant/ws/waiter/${tenantId}`;
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === "order_ready") {
            const tableNum = msg.table_number || `Mesa ${msg.table_id}`;
            setWaiterNotif(`🍽️ ${tableNum}: pedido listo para servir`);
            setTimeout(() => setWaiterNotif(null), 6000);
            fetchTables(); // refrescar estados
          }
        } catch { /* ignore */ }
      };
      ws.onclose = () => {
        reconnectTimer = setTimeout(connect, 5000);
      };
    };

    connect();
    return () => {
      ws?.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

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

  // ─── Fetch sections ───
  const fetchSections = useCallback(async () => {
    try {
      const res = await authFetch("/api/v1/restaurant/sections");
      if (!res.ok) throw new Error("Error al cargar secciones");
      const data = await res.json();
      setSections(data.sections ?? data);
    } catch {
      setSections([]);
    } finally {
      setSectionsLoading(false);
    }
  }, []);

  useEffect(() => { fetchSections(); }, [fetchSections]);
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
      if (formData.section_id) body.section_id = formData.section_id;
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
      body.section_id = formData.section_id ?? null;
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

  const addToOrder = async (
    menuItem: MenuItem,
    modifierIds: number[] = [],
    notes = "",
    skipModifiers = false,
  ) => {
    if (!selectedTable) return;

    // If item has modifiers and no modifierIds passed, open ModifierBottomSheet (unless skipping)
    if (!skipModifiers && menuItem.modifiers && menuItem.modifiers.length > 0 && modifierIds.length === 0 && !modifierSheetOpen) {
      setModifierItem(menuItem);
      setModifierNotes("");
      setModifierSheetOpen(true);
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
            notes: notes || "",
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
      const noteSuffix = notes.trim() ? ` [${notes.trim()}]` : "";
      setOrderToast(`✅ ${menuItem.name}${modNames}${noteSuffix} agregado`);
      setTimeout(() => setOrderToast(null), 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al agregar");
    } finally {
      setAddingItemId(null);
      setModifierItem(null);
    }
  };

  const handleModifierConfirm = (selected: ModifierSelection[]) => {
    if (modifierItem) {
      addToOrder(
        modifierItem,
        selected.map((s) => s.id),
        modifierNotes,
      );
    }
    setModifierSheetOpen(false);
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
      setOrderSent(true);
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
    if (menuItem) addToOrder(menuItem, [], "", true);
  };

  const handleCloseOrder = async () => {
    if (!selectedTable) return;
    setSubmitting(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${selectedTable.id}/close-order`, { method: "POST" });
      if (!res.ok) throw new Error("Error al cerrar mesa");
      setOrderToast("📋 Cuenta cerrada — lista para pagar");
      setTimeout(() => setOrderToast(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al cerrar");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePayTable = () => {
    if (!selectedTable) return;
    const total = selectedTable.total_provisional ?? 0;
    setPaymentMethod("cash");
    setYapeAmount(0);
    setCashAmount(total);
    setPaymentReference("");
    setShowPayModal(true);
  };

  const handleConfirmPayment = async () => {
    if (!selectedTable) return;
    const total = selectedTable.total_provisional ?? 0;

    // Build payments array based on selected method
    let payments: { method: string; amount: number; reference?: string }[] = [];

    if (paymentMethod === "cash") {
      payments = [{ method: "cash", amount: total }];
    } else if (paymentMethod === "yape") {
      payments = [{ method: "yape", amount: total }];
      if (paymentReference.trim()) {
        payments[0].reference = paymentReference.trim();
      }
    } else if (paymentMethod === "split") {
      if (Math.abs(yapeAmount + cashAmount - total) > 0.01) {
        setError(`Los montos no cubren el total (S/ ${total.toFixed(2)})`);
        return;
      }
      const yapePayment: { method: string; amount: number; reference?: string } = {
        method: "yape",
        amount: Math.round(yapeAmount * 100) / 100,
      };
      if (paymentReference.trim()) {
        yapePayment.reference = paymentReference.trim();
      }
      payments = [
        yapePayment,
        { method: "cash", amount: Math.round(cashAmount * 100) / 100 },
      ];
    }

    setPaySubmitting(true);
    try {
      const res = await authFetch(`/api/v1/restaurant/tables/${selectedTable.id}/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payments }),
      });
      if (!res.ok) throw new Error("Error al procesar pago");
      setPaymentSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al pagar");
    } finally {
      // Pequeña pausa para ver el spinner
      await new Promise(r => setTimeout(r, 800));
      setPaySubmitting(false);
    }
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

  // Agrupar items por menu_item_id + modifiers + notes para el ticket
  const groupedItems = useMemo(() => {
    const map = new Map<string, OrderItem & { displayModifiers: string; displayNotes: string; unitPriceWithMods: number }>();
    orderItems.forEach((item) => {
      const modIds = (item.modifiers || [])
        .map((m) => m.id)
        .sort((a, b) => a - b)
        .join(",");
      const noteKey = item.notes ?? "";
      const key = `${item.menu_item_id}|${modIds}|${noteKey}`;
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
          displayNotes: item.notes ?? "",
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
    setOrderSent(false);
    setShowOpenModal(true);
    if (table.status === "available" || table.status === "reserved") {
      setOpenGuests(2);
      setOpenWaiter(user?.full_name ?? "");
      setShowManualWaiter(false);
    }
    if (table.status === "occupied") {
      fetchMenu();
      // No hay order_id en la lista de mesas — se obtiene al agregar items
    }
  };

  const openCreateModal = () => {
    setEditingTable(null);
    setFormData({ number: "", capacity: 4, section: "", section_id: null });
    setFormError(null);
    setShowFormModal(true);
  };

  const openEditModal = (table: Table) => {
    setEditingTable(table);
    setFormData({
      number: table.number,
      capacity: table.capacity,
      section: table.section ?? "",
      section_id: table.section_id ?? null,
    });
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
      {/* Notificación flotante de cocina */}
      {waiterNotif && (
        <div className="fixed top-4 right-4 z-[100] max-w-sm p-3 rounded-lg shadow-lg bg-orange-50 border border-orange-200 text-orange-700 text-sm animate-pulse">
          {waiterNotif}
        </div>
      )}
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

      {/* ─── Section filter ─── */}
      {sections.length > 0 && (
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-brand-text-secondary">Filtrar por sección:</label>
          <select
            value={sectionFilter}
            onChange={(e) => {
              const val = e.target.value;
              setSectionFilter(val === "all" ? "all" : val === "none" ? "none" : Number(val));
            }}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="all">Todas las secciones</option>
            <option value="none">Sin sección</option>
            {sections.map((sec) => (
              <option key={sec.id} value={sec.id}>{sec.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Grid de mesas */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {tables
          .filter((table) =>
            sectionFilter === "all" ? true :
            sectionFilter === "none" ? table.section_id === null :
            table.section_id === sectionFilter
          )
          .map((table) => (
          <button
            key={table.id}
            onClick={() => handleTableClick(table)}
            className={`relative p-4 rounded-xl border-2 text-left transition-all hover:shadow-md group ${STATUS_COLORS[table.status]}`}
          >
            <div className="text-lg font-bold">{table.number}</div>
            <div className="text-xs mt-1">{table.capacity} pers.</div>
            {(table.section_name || table.section) && (
              <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-brand-primary/10 text-brand-primary">
                {table.section_name ?? table.section}
              </span>
            )}
            <div className="text-xs font-medium mt-1">{STATUS_LABELS[table.status]}</div>
            {table.status === "occupied" && (
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg p-2 shadow text-xs text-left">
                <div>👥 {table.guests} comensales</div>
                <div>👤 {table.waiter_name}</div>
                {table.opened_at && (
                  <div>🕐 {new Date(table.opened_at).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</div>
                )}
                {table.total_provisional != null && (
                  <div className="font-bold mt-1">S/ {table.total_provisional.toFixed(2)}</div>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      {tables.length === 0 && !loading && !sectionsLoading && (
        <div className="p-10 text-center text-brand-text-secondary">
          <span className="text-4xl block mb-3">🪑</span>
          {/* ─── Onboarding: no tables AND no sections ─── */}
          {sections.length === 0 && !sectionsLoading ? (
            <>
              <p className="mb-2">Configura tus secciones primero.</p>
              <p className="text-xs text-gray-400 mb-4">Las secciones agrupan mesas (Terraza, Salón, etc.)</p>
              <a
                href="/restaurante/secciones"
                className="inline-block px-4 py-2 bg-brand-primary text-white rounded-lg text-sm hover:bg-brand-secondary"
              >
                ➕ Configurar Secciones
              </a>
            </>
          ) : (
            <>
              <p>No hay mesas configuradas.</p>
              <button onClick={openCreateModal} className="mt-3 px-4 py-2 bg-brand-primary text-white rounded-lg text-sm">
                ➕ Crear Primera Mesa
              </button>
            </>
          )}
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
                    <select
                      value={showManualWaiter ? "__other__" : (user?.full_name ?? "")}
                      onChange={(e) => {
                        if (e.target.value === "__other__") {
                          setOpenWaiter("");
                          setShowManualWaiter(true);
                        } else {
                          setOpenWaiter(e.target.value);
                          setShowManualWaiter(false);
                        }
                      }}
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                    >
                      <option value={user?.full_name ?? ""}>{user?.full_name ?? "Sin nombre"}</option>
                      <option value="__other__">Otro...</option>
                    </select>
                    {showManualWaiter && (
                      <input
                        value={openWaiter}
                        onChange={(e) => setOpenWaiter(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg text-sm mt-2"
                        placeholder="Escribir otro nombre"
                        autoFocus
                      />
                    )}
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
                  <p>Sección: {selectedTable.section_name ?? selectedTable.section ?? "General"}</p>
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
                  <p>Sección: {selectedTable.section_name ?? selectedTable.section ?? "General"}</p>
                  {selectedTable.guests && <p>Comensales: {selectedTable.guests}</p>}
                  {selectedTable.waiter_name && <p>Mesero: {selectedTable.waiter_name}</p>}
                  {selectedTable.total_provisional != null && (
                    <p className="font-bold text-brand-text-primary mt-1">
                      Total: S/ {selectedTable.total_provisional.toFixed(2)}
                    </p>
                  )}
                </div>

                {/* Current order items */}
                {orderItems.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-3 mb-2">
                    <h4 className="text-xs font-bold text-brand-text-primary mb-2">📋 Pedido Actual</h4>
                    <div className="max-h-64 overflow-y-auto space-y-0.5">
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
                            {item.displayNotes && (
                              <span className="text-[10px] text-orange-500 truncate ml-1">
                                📝 {item.displayNotes}
                              </span>
                            )}
                            {item.unitPriceWithMods > item.unit_price && (
                              <span className="text-[10px] text-orange-600 ml-1">
                                +S/ {(item.unitPriceWithMods - (item.unit_price || 0)).toFixed(2)} mods
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

                {/* Waiter notification from kitchen */}
                {waiterNotif && (
                  <div className="p-2 rounded-lg bg-orange-50 border border-orange-200 text-orange-700 text-xs text-center animate-pulse">
                    {waiterNotif}
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
                {orderSent ? (
                  <div className="w-full py-2.5 text-sm rounded-lg bg-green-100 border border-green-300 text-green-700 text-center font-medium">
                    ✅ Pedido enviado a cocina
                  </div>
                ) : orderItems.length > 0 && selectedTable.order_id ? (
                  <button onClick={sendToKitchen} disabled={sendingToKitchen}
                    className="w-full py-2.5 text-sm rounded-lg bg-orange-500 text-white font-medium
                      hover:bg-orange-600 disabled:opacity-50">
                    {sendingToKitchen ? "📨 Enviando..." : "📨 Enviar a Cocina"}
                  </button>
                ) : null}

                {/* Close order & Pay — liberar mesa */}
                {selectedTable.status === "occupied" && selectedTable.guests && (
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={handleCloseOrder}
                      className="py-2.5 text-sm rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600">
                      📋 Cerrar Mesa
                    </button>
                    {selectedTable.order_id ? (
                      <button onClick={handlePayTable}
                        className="py-2.5 text-sm rounded-lg bg-green-600 text-white font-medium hover:bg-green-700">
                        💰 Pagar
                      </button>
                    ) : (
                      <div className="py-2.5 text-sm rounded-lg bg-gray-300 text-gray-500 text-center flex items-center justify-center"
                        title="Esperar que cocina entregue">
                        ⏳ Pagar
                      </div>
                    )}
                  </div>
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
                  <p>Sección: {selectedTable.section_name ?? selectedTable.section ?? "General"}</p>
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

      {/* Modifier Bottom Sheet */}
      <ModifierBottomSheet
        open={modifierSheetOpen}
        onOpenChange={(open) => {
          setModifierSheetOpen(open);
          if (!open) setModifierItem(null);
        }}
        itemName={modifierItem?.name ?? ""}
        itemPrice={modifierItem?.price}
        modifiers={modifierItem?.modifiers ?? []}
        notes={modifierNotes}
        onNotesChange={setModifierNotes}
        onConfirm={handleModifierConfirm}
      />

      {/* Payment Modal */}
      {showPayModal && selectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 shadow-xl">
            {paymentSuccess ? (
              <>
                <h3 className="text-lg font-bold text-green-600 mb-4">
                  ✅ Pagado con éxito
                </h3>
                <p className="text-sm text-brand-text-secondary mb-2">
                  Mesa {selectedTable.number} — S/ {(selectedTable.total_provisional ?? 0).toFixed(2)}
                </p>
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={async () => {
                      await handleFree(selectedTable.id);
                      setShowPayModal(false);
                      setShowOpenModal(false);
                      setSelectedTable(null);
                      setPaymentSuccess(false);
                      await fetchTables();
                    }}
                    className="flex-1 py-2.5 text-sm rounded-lg bg-green-600 text-white font-medium hover:bg-green-700"
                  >
                    🚪 Liberar Mesa
                  </button>
                  <button
                    onClick={() => { setShowPayModal(false); setPaymentSuccess(false); }}
                    className="flex-1 py-2.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                  >
                    Cerrar
                  </button>
                </div>
              </>
            ) : (
              <>
            <h3 className="text-lg font-bold text-brand-text-primary mb-4">
              💰 Pagar Mesa {selectedTable.number}
            </h3>
            <p className="text-sm text-brand-text-secondary mb-4">
              Total:{" "}
              <span className="font-bold text-brand-text-primary">
                S/ {(selectedTable.total_provisional ?? 0).toFixed(2)}
              </span>
            </p>

            {/* Payment method selection */}
            <div className="space-y-2 mb-4">
              <button
                onClick={() => {
                  setPaymentMethod("cash");
                  const total = selectedTable.total_provisional ?? 0;
                  setCashAmount(total);
                  setYapeAmount(0);
                  setPaymentReference("");
                }}
                className={`w-full text-left px-4 py-3 rounded-lg border-2 text-sm transition-all ${
                  paymentMethod === "cash"
                    ? "border-green-500 bg-green-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <span className="font-medium">💵 Todo en Efectivo</span>
              </button>
              <button
                disabled
                className="w-full text-left px-4 py-3 rounded-lg border-2 text-sm border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
                title="Próximamente"
              >
                <span className="font-medium">📱 Todo con Yape 🔜</span>
              </button>
              <button
                disabled
                className="w-full text-left px-4 py-3 rounded-lg border-2 text-sm border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
                title="Próximamente"
              >
                <span className="font-medium">✂️ Dividir pago 🔜</span>
              </button>
            </div>

            {/* Yape reference (shown for yape and split) */}
            {paymentMethod === "yape" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">
                  Nombre/Referencia (opcional)
                </label>
                <input
                  type="text"
                  value={paymentReference}
                  onChange={(e) => setPaymentReference(e.target.value)}
                  placeholder="Nombre del cliente o N° operación"
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>
            )}

            {/* Split payment inputs */}
            {paymentMethod === "split" && (
              <div className="space-y-3 mb-4 p-3 bg-gray-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Monto Yape
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={yapeAmount}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      const total = selectedTable.total_provisional ?? 0;
                      setYapeAmount(val);
                      setCashAmount(
                        Math.round((total - val) * 100) / 100,
                      );
                    }}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Monto Efectivo
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={cashAmount}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      const total = selectedTable.total_provisional ?? 0;
                      setCashAmount(val);
                      setYapeAmount(
                        Math.round((total - val) * 100) / 100,
                      );
                    }}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-brand-text-secondary">
                    Suma:{" "}
                    <span
                      className={`font-semibold ${
                        Math.abs(
                          yapeAmount +
                            cashAmount -
                            (selectedTable.total_provisional ?? 0),
                        ) > 0.01
                          ? "text-red-500"
                          : "text-green-600"
                      }`}
                    >
                      S/ {(yapeAmount + cashAmount).toFixed(2)}
                    </span>
                  </span>
                  <span className="font-medium text-brand-text-primary">
                    Total: S/{" "}
                    {(selectedTable.total_provisional ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowPayModal(false)}
                className="flex-1 py-2.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={paySubmitting}
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmPayment}
                disabled={
                  paySubmitting ||
                  (paymentMethod === "split" &&
                    Math.abs(
                      yapeAmount +
                        cashAmount -
                        (selectedTable.total_provisional ?? 0),
                    ) > 0.01)
                }
                className="flex-1 py-2.5 text-sm rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {paySubmitting
                  ? "⏳ Procesando..."
                  : "✅ Confirmar pago"}
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
                <select
                  value={formData.section_id ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === "") {
                      setFormData({ ...formData, section_id: null, section: "" });
                    } else {
                      const secId = Number(val);
                      const sec = sections.find((s) => s.id === secId);
                      setFormData({
                        ...formData,
                        section_id: secId,
                        section: sec?.name ?? "",
                      });
                    }
                  }}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Sin sección</option>
                  {sections.map((sec) => (
                    <option key={sec.id} value={sec.id}>{sec.name}</option>
                  ))}
                </select>
              </div>
            </div>
            {!editingTable && sections.length === 0 && (
              <div className="mt-4 p-2 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-700 text-xs text-center">
                ⚠️ Aún no hay secciones. Puedes crearlas en <a href="/restaurante/secciones" className="underline">Mantenimiento de Secciones</a>.
              </div>
            )}
            <div className="flex gap-2 justify-end mt-4">
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
