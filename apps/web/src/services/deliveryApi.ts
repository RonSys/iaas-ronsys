/**
 * Delivery API — Panel staff del módulo Delivery (Spec 03, Fase A).
 *
 * Endpoints autenticados (/api/v1/delivery/*) usando authFetch.
 *
 * @module services/deliveryApi
 */
import { authFetch } from "./authFetch";

// ─── Tipos ────────────────────────────────────────────────

export interface DeliveryOrder {
  id: number;
  tracking_code: string;
  status: "received" | "preparing" | "ready" | "out_for_delivery" | "delivered" | "cancelled";
  customer: { name: string | null; phone: string; address: string };
  zone_id: number | null;
  courier_id: number | null;
  campaign_id: number | null;
  utm: Record<string, unknown> | null;
  fee: number;
  eta_min: number | null;
  sale_id: number | null;
  sale_number: string | null;
  total: number | null;
  notes: string | null;
  timestamps: Record<string, string | null>;
  created_at: string;
}

export interface DeliveryZone {
  id: number;
  name: string;
  description: string | null;
  districts: string[] | null;
  fee: number;
  min_order: number;
  eta_min: number;
  active: boolean;
}

export interface Courier {
  id: number;
  name: string;
  phone: string | null;
  vehicle: string | null;
  user_id: number | null;
  status: "available" | "on_delivery" | "offline";
  active: boolean;
}

export interface Campaign {
  id: number;
  name: string;
  channel: string;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  budget: number;
  spend: number;
  starts_on: string | null;
  ends_on: string | null;
  active: boolean;
  notes: string | null;
}

export interface CampaignMetrics {
  campaign_id: number;
  name: string;
  channel: string;
  spend: number;
  orders: number;
  gmv: number;
  aov: number;
  roas: number;
}

export interface DeliveryOverview {
  orders: number;
  gmv: number;
  fee_total: number;
  avg_delivery_min: number | null;
  cancelled: number;
}

// Transiciones válidas (espejo del backend §3.3)
export const ORDER_TRANSITIONS: Record<DeliveryOrder["status"], DeliveryOrder["status"][]> = {
  received: ["preparing", "cancelled"],
  preparing: ["ready", "cancelled"],
  ready: ["out_for_delivery", "cancelled"],
  out_for_delivery: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

export const ORDER_STATUS_LABEL: Record<DeliveryOrder["status"], string> = {
  received: "Recibido",
  preparing: "En cocina",
  ready: "Listo",
  out_for_delivery: "En ruta",
  delivered: "Entregado",
  cancelled: "Cancelado",
};

// ─── Pedidos ─────────────────────────────────────────────

export async function getDeliveryOrders(status?: string): Promise<DeliveryOrder[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await authFetch(`/api/v1/delivery/orders${qs}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cargar pedidos delivery");
  }
  return res.json();
}

export async function updateOrderStatus(orderId: number, status: string): Promise<DeliveryOrder> {
  const res = await authFetch(`/api/v1/delivery/orders/${orderId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al actualizar estado");
  }
  return res.json();
}

export async function assignCourierToOrder(orderId: number, courierId: number): Promise<DeliveryOrder> {
  const res = await authFetch(`/api/v1/delivery/orders/${orderId}/assign-courier`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ courier_id: courierId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al asignar repartidor");
  }
  return res.json();
}

// ─── Zonas ───────────────────────────────────────────────

export async function getZones(): Promise<DeliveryZone[]> {
  const res = await authFetch("/api/v1/delivery/zones");
  if (!res.ok) throw new Error("Error al cargar zonas");
  return res.json();
}

export async function createZone(data: Partial<DeliveryZone>): Promise<DeliveryZone> {
  const res = await authFetch("/api/v1/delivery/zones", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al crear zona");
  }
  return res.json();
}

export async function updateZone(id: number, data: Partial<DeliveryZone>): Promise<DeliveryZone> {
  const res = await authFetch(`/api/v1/delivery/zones/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al actualizar zona");
  }
  return res.json();
}

export async function deleteZone(id: number): Promise<void> {
  const res = await authFetch(`/api/v1/delivery/zones/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar zona");
}

// ─── Repartidores ────────────────────────────────────────

export async function getCouriers(): Promise<Courier[]> {
  const res = await authFetch("/api/v1/delivery/couriers");
  if (!res.ok) throw new Error("Error al cargar repartidores");
  return res.json();
}

export async function createCourier(data: Partial<Courier>): Promise<Courier> {
  const res = await authFetch("/api/v1/delivery/couriers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al crear repartidor");
  }
  return res.json();
}

export async function updateCourier(id: number, data: Partial<Courier>): Promise<Courier> {
  const res = await authFetch(`/api/v1/delivery/couriers/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al actualizar repartidor");
  }
  return res.json();
}

export async function deleteCourier(id: number): Promise<void> {
  const res = await authFetch(`/api/v1/delivery/couriers/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar repartidor");
}

// ─── Campañas ────────────────────────────────────────────

export async function getCampaigns(): Promise<Campaign[]> {
  const res = await authFetch("/api/v1/delivery/campaigns");
  if (!res.ok) throw new Error("Error al cargar campañas");
  return res.json();
}

export async function createCampaign(data: Partial<Campaign>): Promise<Campaign> {
  const res = await authFetch("/api/v1/delivery/campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al crear campaña");
  }
  return res.json();
}

export async function updateCampaign(id: number, data: Partial<Campaign>): Promise<Campaign> {
  const res = await authFetch(`/api/v1/delivery/campaigns/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al actualizar campaña");
  }
  return res.json();
}

export async function deleteCampaign(id: number): Promise<void> {
  const res = await authFetch(`/api/v1/delivery/campaigns/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar campaña");
}

// ─── Métricas ────────────────────────────────────────────

export async function getCampaignMetrics(): Promise<CampaignMetrics[]> {
  const res = await authFetch("/api/v1/delivery/metrics/campaigns");
  if (!res.ok) throw new Error("Error al cargar métricas de campañas");
  return res.json();
}

export async function getDeliveryOverview(): Promise<DeliveryOverview> {
  const res = await authFetch("/api/v1/delivery/metrics/overview");
  if (!res.ok) throw new Error("Error al cargar métricas generales");
  return res.json();
}
