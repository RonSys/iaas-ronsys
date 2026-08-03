/**
 * DeliveryPage — Panel staff del módulo Delivery (Spec 03, Fase A).
 *
 * Pestañas:
 *  1. 📦 Pedidos   — kanban con máquina de estados + asignación de repartidor
 *  2. 🗺️ Zonas     — CRUD zonas de reparto (fee, mínimo, ETA)
 *  3. 🛵 Repartidores — CRUD repartidores internos
 *  4. 📢 Campañas  — CRUD campañas de marketing digital (UTM + gasto)
 *  5. 📈 Métricas  — ROAS / AOV / GMV por campaña
 *
 * @module pages/restaurante/DeliveryPage
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Skeleton } from "@/components/dashboard/KPICard";
import {
  getCampaignMetrics,
  getCampaigns,
  getCouriers,
  getDeliveryOrders,
  getDeliveryOverview,
  getZones,
  updateOrderStatus,
  assignCourierToOrder,
  createZone,
  updateZone,
  deleteZone,
  createCourier,
  updateCourier,
  deleteCourier,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  ORDER_STATUS_LABEL,
  ORDER_TRANSITIONS,
  type Campaign,
  type CampaignMetrics,
  type Courier,
  type DeliveryOrder,
  type DeliveryOverview,
  type DeliveryZone,
} from "@/services/deliveryApi";

type Tab = "orders" | "zones" | "couriers" | "campaigns" | "metrics";

const STATUS_COLORS: Record<DeliveryOrder["status"], string> = {
  received: "bg-yellow-100 text-yellow-800",
  preparing: "bg-blue-100 text-blue-800",
  ready: "bg-green-100 text-green-700",
  out_for_delivery: "bg-purple-100 text-purple-700",
  delivered: "bg-gray-100 text-gray-600",
  cancelled: "bg-red-100 text-red-600",
};

const TABS: { id: Tab; label: string }[] = [
  { id: "orders", label: "📦 Pedidos" },
  { id: "zones", label: "🗺️ Zonas" },
  { id: "couriers", label: "🛵 Repartidores" },
  { id: "campaigns", label: "📢 Campañas" },
  { id: "metrics", label: "📈 Métricas" },
];

export function DeliveryPage() {
  const [tab, setTab] = useState<Tab>("orders");
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-brand-text-primary">🛵 Delivery Nocturno</h2>
        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === t.id
                  ? "bg-brand-primary text-white"
                  : "border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {tab === "orders" && <OrdersTab />}
      {tab === "zones" && <ZonesTab />}
      {tab === "couriers" && <CouriersTab />}
      {tab === "campaigns" && <CampaignsTab />}
      {tab === "metrics" && <MetricsTab />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// 📦 Pedidos (kanban)
// ═══════════════════════════════════════════════════════════

function OrdersTab() {
  const [orders, setOrders] = useState<DeliveryOrder[]>([]);
  const [couriers, setCouriers] = useState<Courier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState<number | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [o, c] = await Promise.all([getDeliveryOrders(), getCouriers()]);
      setOrders(o);
      setCouriers(c);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleTransition = async (order: DeliveryOrder, next: string) => {
    setError(null);
    try {
      await updateOrderStatus(order.id, next);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  };

  const handleAssign = async (orderId: number, courierId: number) => {
    setError(null);
    setAssigning(orderId);
    try {
      await assignCourierToOrder(orderId, courierId);
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setAssigning(null);
    }
  };

  const columns: DeliveryOrder["status"][] = [
    "received", "preparing", "ready", "out_for_delivery", "delivered", "cancelled",
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}
      <div className="flex items-center justify-between">
        <p className="text-sm text-brand-text-secondary">
          Pedidos activos:{" "}
          <span className="font-semibold">
            {orders.filter((o) => !["delivered", "cancelled"].includes(o.status)).length}
          </span>
        </p>
        <button
          onClick={fetchAll}
          className="px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"
        >
          🔄 Refrescar
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {columns.map((col) => {
          const colOrders = orders.filter((o) => o.status === col);
          return (
            <div key={col} className="card p-3">
              <div className="flex items-center justify-between mb-3">
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[col]}`}>
                  {ORDER_STATUS_LABEL[col]}
                </span>
                <span className="text-xs text-brand-text-secondary">{colOrders.length}</span>
              </div>
              <div className="space-y-2">
                {colOrders.length === 0 && (
                  <p className="text-xs text-brand-text-secondary text-center py-4">Sin pedidos</p>
                )}
                {colOrders.map((o) => {
                  const next = ORDER_TRANSITIONS[o.status] ?? [];
                  const availableCouriers = couriers.filter(
                    (c) => c.active && c.status !== "on_delivery",
                  );
                  const canAssign =
                    ["received", "preparing", "ready"].includes(o.status) &&
                    availableCouriers.length > 0;
                  return (
                    <div key={o.id} className="border rounded-lg p-3 bg-white">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold truncate">
                            {o.customer.name || "Cliente"} ·{" "}
                            <span className="text-brand-primary font-mono text-xs">
                              {o.tracking_code}
                            </span>
                          </p>
                          <p className="text-xs text-brand-text-secondary truncate">
                            📍 {o.customer.address}
                          </p>
                          <p className="text-xs text-brand-text-secondary">
                            📱 {o.customer.phone} · 🕐 {o.eta_min} min · S/{" "}
                            {o.total?.toFixed(2) ?? "-"}
                          </p>
                          {o.notes && (
                            <p className="text-xs text-amber-600 mt-0.5">📝 {o.notes}</p>
                          )}
                        </div>
                        <span className="text-sm font-bold">S/ {o.total?.toFixed(2) ?? "-"}</span>
                      </div>
                      {next.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {next.map((n) => (
                            <button
                              key={n}
                              onClick={() => handleTransition(o, n)}
                              className={`text-xs px-2 py-1 rounded-md font-medium ${
                                n === "cancelled"
                                  ? "border border-red-200 text-red-600 hover:bg-red-50"
                                  : "bg-brand-primary/10 text-brand-primary hover:bg-brand-primary hover:text-white"
                              }`}
                            >
                              {n === "cancelled" ? "✕ Cancelar" : `→ ${ORDER_STATUS_LABEL[n]}`}
                            </button>
                          ))}
                          {canAssign && (
                            <select
                              value=""
                              disabled={assigning === o.id}
                              onChange={(e) => {
                                if (e.target.value) {
                                  handleAssign(o.id, Number(e.target.value));
                                }
                              }}
                              className="text-xs px-2 py-1 border rounded-md bg-white"
                            >
                              <option value="">
                                {assigning === o.id ? "Asignando..." : "🛵 Asignar repartidor"}
                              </option>
                              {availableCouriers.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.name} ({c.vehicle || "sin vehículo"})
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// 🗺️ Zonas
// ═══════════════════════════════════════════════════════════

function ZonesTab() {
  const [zones, setZones] = useState<DeliveryZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<DeliveryZone | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchZones = useCallback(async () => {
    try {
      setZones(await getZones());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  const handleSave = async (data: Partial<DeliveryZone>, id?: number) => {
    try {
      if (id) await updateZone(id, data);
      else await createZone(data);
      setEditing(null);
      setCreating(false);
      await fetchZones();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  };

  if (loading) return <Skeleton className="h-64 w-full" />;
  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}
      <button
        onClick={() => setCreating(true)}
        className="px-3 py-1.5 bg-brand-primary text-white rounded-lg text-sm"
      >
        + Nueva Zona
      </button>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-brand-text-secondary border-b">
              <th className="py-2">Zona</th>
              <th>Distritos</th>
              <th>Fee</th>
              <th>Mínimo</th>
              <th>ETA</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {zones.map((z) => (
              <tr key={z.id} className="border-b">
                <td className="py-2 font-medium">{z.name}</td>
                <td className="text-xs">{z.districts?.join(", ") || "-"}</td>
                <td>S/ {z.fee.toFixed(2)}</td>
                <td>S/ {z.min_order.toFixed(2)}</td>
                <td>{z.eta_min} min</td>
                <td>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      z.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {z.active ? "Activa" : "Inactiva"}
                  </span>
                </td>
                <td className="text-right">
                  <button onClick={() => setEditing(z)} className="text-xs underline mr-2">
                    Editar
                  </button>
                  <button
                    onClick={async () => {
                      await deleteZone(z.id);
                      await fetchZones();
                    }}
                    className="text-xs text-red-500 underline"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {zones.length === 0 && (
              <tr>
                <td colSpan={7} className="py-6 text-center text-brand-text-secondary text-sm">
                  Sin zonas configuradas
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {(creating || editing) && (
        <ZoneForm
          initial={editing}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

function ZoneForm({
  initial,
  onCancel,
  onSave,
}: {
  initial: DeliveryZone | null;
  onCancel: () => void;
  onSave: (data: Partial<DeliveryZone>, id?: number) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [districts, setDistricts] = useState(initial?.districts?.join(", ") ?? "");
  const [fee, setFee] = useState(initial?.fee?.toString() ?? "5.00");
  const [minOrder, setMinOrder] = useState(initial?.min_order?.toString() ?? "35.00");
  const [eta, setEta] = useState(initial?.eta_min?.toString() ?? "35");
  const [active, setActive] = useState(initial?.active ?? true);
  const [saving, setSaving] = useState(false);

  return (
    <div className="card space-y-3 p-4">
      <h3 className="font-bold">{initial ? "✏️ Editar Zona" : "➕ Nueva Zona"}</h3>
      <div className="grid grid-cols-2 gap-3">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre (ej: Zona 1 — Montenegro)" className="col-span-2 px-3 py-2 border rounded-lg text-sm" />
        <input value={districts} onChange={(e) => setDistricts(e.target.value)} placeholder="Distritos (coma separada)" className="col-span-2 px-3 py-2 border rounded-lg text-sm" />
        <input value={fee} onChange={(e) => setFee(e.target.value)} placeholder="Fee S/" className="px-3 py-2 border rounded-lg text-sm" />
        <input value={minOrder} onChange={(e) => setMinOrder(e.target.value)} placeholder="Pedido mínimo S/" className="px-3 py-2 border rounded-lg text-sm" />
        <input value={eta} onChange={(e) => setEta(e.target.value)} placeholder="ETA minutos" className="px-3 py-2 border rounded-lg text-sm" />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          Activa
        </label>
      </div>
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="px-3 py-1.5 border rounded-lg text-sm">Cancelar</button>
        <button
          disabled={saving || !name.trim()}
          onClick={async () => {
            setSaving(true);
            await onSave(
              {
                name: name.trim(),
                districts: districts.split(",").map((d) => d.trim()).filter(Boolean),
                fee: Number(fee),
                min_order: Number(minOrder),
                eta_min: Number(eta),
                active,
              },
              initial?.id,
            );
            setSaving(false);
          }}
          className="px-3 py-1.5 bg-brand-success text-white rounded-lg text-sm disabled:opacity-50"
        >
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// 🛵 Repartidores
// ═══════════════════════════════════════════════════════════

function CouriersTab() {
  const [couriers, setCouriers] = useState<Courier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCouriers = useCallback(async () => {
    try {
      setCouriers(await getCouriers());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCouriers();
  }, [fetchCouriers]);

  const handleToggleStatus = async (c: Courier) => {
    const next = c.status === "available" ? "offline" : c.status === "offline" ? "available" : c.status;
    await updateCourier(c.id, { status: next });
    await fetchCouriers();
  };

  if (loading) return <Skeleton className="h-64 w-full" />;
  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}
      <AddCourierForm onCreated={fetchCouriers} />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {couriers.map((c) => (
          <div key={c.id} className="card p-3 flex items-center justify-between">
            <div>
              <p className="font-medium">🛵 {c.name}</p>
              <p className="text-xs text-brand-text-secondary">
                {c.phone || "sin teléfono"} · {c.vehicle || "sin vehículo"}
              </p>
              <span
                className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${
                  c.status === "on_delivery"
                    ? "bg-purple-100 text-purple-700"
                    : c.status === "available"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                }`}
              >
                {c.status === "on_delivery"
                  ? "En entrega"
                  : c.status === "available"
                    ? "Disponible"
                    : "Desconectado"}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {c.status !== "on_delivery" && (
                <button
                  onClick={() => handleToggleStatus(c)}
                  className="text-xs border px-2 py-1 rounded-md hover:bg-gray-50"
                >
                  {c.status === "available" ? "Poner offline" : "Poner disponible"}
                </button>
              )}
              <button
                onClick={async () => {
                  await deleteCourier(c.id);
                  await fetchCouriers();
                }}
                className="text-xs text-red-500 underline"
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
        {couriers.length === 0 && (
          <p className="text-sm text-brand-text-secondary text-center py-8 col-span-full">
            Sin repartidores registrados
          </p>
        )}
      </div>
    </div>
  );
}

function AddCourierForm({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <div className="card p-3 flex flex-wrap gap-2 items-end">
      <div className="flex-1 min-w-40">
        <label className="block text-xs font-medium mb-1">Nombre *</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej: Nilton" className="w-full px-3 py-2 border rounded-lg text-sm" />
      </div>
      <div className="w-36">
        <label className="block text-xs font-medium mb-1">Teléfono</label>
        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="999 888 777" className="w-full px-3 py-2 border rounded-lg text-sm" />
      </div>
      <div className="w-32">
        <label className="block text-xs font-medium mb-1">Vehículo</label>
        <select value={vehicle} onChange={(e) => setVehicle(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
          <option value="">—</option>
          <option value="moto">Moto</option>
          <option value="bicicleta">Bicicleta</option>
          <option value="auto">Auto</option>
        </select>
      </div>
      <button
        disabled={saving || !name.trim()}
        onClick={async () => {
          setSaving(true);
          await createCourier({ name: name.trim(), phone: phone.trim() || null, vehicle: vehicle || null });
          setName("");
          setPhone("");
          setVehicle("");
          setSaving(false);
          await onCreated();
        }}
        className="px-3 py-2 bg-brand-primary text-white rounded-lg text-sm disabled:opacity-50"
      >
        {saving ? "..." : "+ Agregar"}
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// 📢 Campañas
// ═══════════════════════════════════════════════════════════

function CampaignsTab() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCampaigns = useCallback(async () => {
    try {
      setCampaigns(await getCampaigns());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  if (loading) return <Skeleton className="h-64 w-full" />;
  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}
      <AddCampaignForm onCreated={fetchCampaigns} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-brand-text-secondary border-b">
              <th className="py-2">Campaña</th>
              <th>Canal</th>
              <th>UTM</th>
              <th>Presupuesto</th>
              <th>Gasto</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-b">
                <td className="py-2 font-medium">{c.name}</td>
                <td className="uppercase text-xs">{c.channel}</td>
                <td className="text-xs font-mono">
                  {c.utm_source}/{c.utm_medium}/{c.utm_campaign}
                </td>
                <td>S/ {c.budget.toFixed(2)}</td>
                <td>S/ {c.spend.toFixed(2)}</td>
                <td>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      c.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {c.active ? "Activa" : "Pausada"}
                  </span>
                </td>
                <td className="text-right">
                  <button
                    onClick={async () => {
                      await updateCampaign(c.id, { active: !c.active });
                      await fetchCampaigns();
                    }}
                    className="text-xs underline mr-2"
                  >
                    {c.active ? "Pausar" : "Activar"}
                  </button>
                  <button
                    onClick={async () => {
                      await deleteCampaign(c.id);
                      await fetchCampaigns();
                    }}
                    className="text-xs text-red-500 underline"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {campaigns.length === 0 && (
              <tr>
                <td colSpan={7} className="py-6 text-center text-brand-text-secondary text-sm">
                  Sin campañas registradas
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AddCampaignForm({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [channel, setChannel] = useState("meta");
  const [utmSource, setUtmSource] = useState("");
  const [utmCampaign, setUtmCampaign] = useState("");
  const [budget, setBudget] = useState("");
  const [spend, setSpend] = useState("");
  const [saving, setSaving] = useState(false);

  const utmHint = useMemo(() => {
    const src = utmSource || "fuente";
    const camp = utmCampaign || "campaña";
    return `/menu/el-segoviano?utm_source=${src}&utm_medium=${channel === "meta" ? "cpc" : "cpc"}&utm_campaign=${camp}`;
  }, [utmSource, utmCampaign, channel]);

  return (
    <div className="card p-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre de campaña *" className="flex-1 min-w-40 px-3 py-2 border rounded-lg text-sm" />
        <select value={channel} onChange={(e) => setChannel(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
          <option value="meta">Meta / Instagram</option>
          <option value="google">Google</option>
          <option value="tiktok">TikTok</option>
          <option value="other">Otro</option>
        </select>
        <input value={utmSource} onChange={(e) => setUtmSource(e.target.value)} placeholder="utm_source (meta)" className="w-32 px-3 py-2 border rounded-lg text-sm" />
        <input value={utmCampaign} onChange={(e) => setUtmCampaign(e.target.value)} placeholder="utm_campaign" className="w-40 px-3 py-2 border rounded-lg text-sm" />
        <input value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="Presupuesto S/" className="w-32 px-3 py-2 border rounded-lg text-sm" />
        <input value={spend} onChange={(e) => setSpend(e.target.value)} placeholder="Gasto S/" className="w-28 px-3 py-2 border rounded-lg text-sm" />
        <button
          disabled={saving || !name.trim()}
          onClick={async () => {
            setSaving(true);
            await createCampaign({
              name: name.trim(),
              channel,
              utm_source: utmSource.trim() || null,
              utm_medium: "cpc",
              utm_campaign: utmCampaign.trim() || null,
              budget: Number(budget) || 0,
              spend: Number(spend) || 0,
            });
            setName(""); setUtmSource(""); setUtmCampaign(""); setBudget(""); setSpend("");
            setSaving(false);
            await onCreated();
          }}
          className="px-3 py-2 bg-brand-primary text-white rounded-lg text-sm disabled:opacity-50"
        >
          {saving ? "..." : "+ Crear"}
        </button>
      </div>
      {utmSource && utmCampaign && (
        <p className="text-xs text-brand-text-secondary">
          🔗 Link para anuncios: <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{utmHint}</span>
        </p>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// 📈 Métricas
// ═══════════════════════════════════════════════════════════

function MetricsTab() {
  const [overview, setOverview] = useState<DeliveryOverview | null>(null);
  const [metrics, setMetrics] = useState<CampaignMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const [ov, m] = await Promise.all([getDeliveryOverview(), getCampaignMetrics()]);
      setOverview(ov);
      setMetrics(m);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  if (loading) return <Skeleton className="h-64 w-full" />;
  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">Cerrar</button>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Pedidos entregados" value={overview?.orders?.toString() ?? "0"} />
        <MetricCard label="GMV (ventas)" value={`S/ ${overview?.gmv?.toFixed(2) ?? "0.00"}`} />
        <MetricCard label="Fee delivery" value={`S/ ${overview?.fee_total?.toFixed(2) ?? "0.00"}`} />
        <MetricCard
          label="Tiempo promedio"
          value={overview?.avg_delivery_min != null ? `${overview.avg_delivery_min} min` : "—"}
        />
        <MetricCard label="Cancelados" value={overview?.cancelled?.toString() ?? "0"} />
      </div>

      <div className="card p-4">
        <h3 className="font-bold mb-3">📢 Rendimiento por campaña</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-brand-text-secondary border-b">
                <th className="py-2">Campaña</th>
                <th>Canal</th>
                <th>Gasto</th>
                <th>Pedidos</th>
                <th>GMV</th>
                <th>Ticket prom.</th>
                <th>ROAS</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.campaign_id} className="border-b">
                  <td className="py-2 font-medium">{m.name}</td>
                  <td className="uppercase text-xs">{m.channel}</td>
                  <td>S/ {m.spend.toFixed(2)}</td>
                  <td>{m.orders}</td>
                  <td>S/ {m.gmv.toFixed(2)}</td>
                  <td>S/ {m.aov.toFixed(2)}</td>
                  <td>
                    <span
                      className={`font-bold ${
                        m.roas >= 2 ? "text-green-600" : m.roas >= 1 ? "text-amber-600" : "text-red-500"
                      }`}
                    >
                      {m.roas.toFixed(2)}x
                    </span>
                  </td>
                </tr>
              ))}
              {metrics.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-brand-text-secondary text-sm">
                    Sin datos de campañas aún
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-brand-text-secondary mt-2">
          💡 ROAS = GMV ÷ gasto en anuncios. Mayor a 1.0 significa que cada sol invertido genera más
          de un sol en ventas.
        </p>
      </div>
      <button onClick={fetchMetrics} className="px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50">
        🔄 Refrescar
      </button>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-3">
      <p className="text-xs text-brand-text-secondary">{label}</p>
      <p className="text-lg font-bold text-brand-text-primary">{value}</p>
    </div>
  );
}
