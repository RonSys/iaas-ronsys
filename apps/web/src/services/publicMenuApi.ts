/**
 * Public Delivery API — Landing pública (Spec 03 §3.4.1).
 *
 * Endpoints SIN autenticación (/api/public/*). Usa fetch directo.
 *
 * @module services/publicMenuApi
 */

// ─── Tipos ────────────────────────────────────────────────

export interface PublicModifier {
  id: number;
  name: string;
  price_adjustment: number;
  max_select: number;
}

export interface PublicMenuItem {
  id: number;
  name: string;
  description: string | null;
  price: number;
  delivery_surcharge: number;
  category: string;
  item_type: string;
  preparation_area: string;
  modifiers: PublicModifier[];
  image_url: string | null;
  available: boolean;
}

export interface PublicMenuSection {
  id: number;
  name: string;
  items: PublicMenuItem[];
}

export interface PublicPromotion {
  id: number;
  name: string;
  promo_type: string;
  discount_value: number;
  description: string | null;
}

export interface PublicMenu {
  tenant_name: string;
  delivery_window: { from: string; to: string };
  currency: string;
  yape_phone: string | null;
  branding: {
    palette?: Record<string, string> | null;
    logo_url?: string | null;
  };
  sections: PublicMenuSection[];
  promotions: PublicPromotion[];
}

export interface PublicZone {
  id: number;
  name: string;
  districts: string[] | null;
  fee: number;
  min_order: number;
  eta_min: number;
}

export interface CheckoutResponse {
  tracking_code: string;
  sale_id: number;
  sale_number: string;
  status: string;
  eta_min: number | null;
  totals: { subtotal: number; discount_total: number; fee: number; total: number };
  payment: { method: string; status: string };
  promotion: { id: number; name: string; discount: number } | null;
}

export interface TrackingStatus {
  tracking_code: string;
  status: string;
  eta_min: number | null;
  timestamps: Record<string, string | null>;
}

// ─── Fetch helpers ───────────────────────────────────────

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Error (${res.status})`);
  }
  return res.json();
}

// ─── Endpoints ───────────────────────────────────────────

export function getPublicMenu(slug: string): Promise<PublicMenu> {
  return publicFetch(`/api/public/${slug}/menu`);
}

export function getPublicZones(slug: string): Promise<PublicZone[]> {
  return publicFetch(`/api/public/${slug}/zones`);
}

export function checkoutOrder(
  slug: string,
  payload: Record<string, unknown>,
): Promise<CheckoutResponse> {
  return publicFetch(`/api/public/${slug}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getTrackingStatus(trackingCode: string): Promise<TrackingStatus> {
  return publicFetch(`/api/public/orders/${encodeURIComponent(trackingCode)}/status`);
}
