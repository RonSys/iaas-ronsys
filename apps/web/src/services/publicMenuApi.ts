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

/**
 * Contacto del negocio para botones wa.me / tel: (Spec 04 §3.5).
 *
 * Contrato backend `GET /api/public/{slug}/menu`:
 * - `whatsapp_link` = `https://wa.me/<business_phone>?text=<mensaje prefabricado>` (URL-encoded)
 * - `phone` = `tel:<business_phone>`
 * - `whatsapp_message` = mensaje prefabricado en texto plano
 *
 * `contact` es `null` cuando la config WhatsApp está inactiva (enabled=false o sin
 * business_phone) → los botones NO se renderizan (CA-F1.14).
 */
export interface ContactInfo {
  whatsapp_link?: string | null;
  phone?: string | null;
  whatsapp_message?: string | null;
}

export interface PublicMenu {
  tenant_name: string;
  delivery_window: { from: string; to: string };
  currency: string;
  yape_phone: string | null;
  contact?: ContactInfo | null;
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

// ─── Helpers botones wa.me / tel: (Spec 04 §3.6, D5) ──────

/**
 * Número base del negocio extraído SOLO desde el contrato público (`contact`),
 * nunca hardcodeado (R-F1.3 / CA-F1.11).
 *
 * Fuentes: `whatsapp_link` (`wa.me/<num>?text=...`) y fallback `phone` (`tel:<num>`).
 */
function waBusinessNumber(contact: ContactInfo | null | undefined): string | null {
  if (!contact) return null;
  const waMatch = contact.whatsapp_link?.match(/wa\.me\/([^?/#]+)/);
  if (waMatch?.[1]) return waMatch[1];
  const tel = contact.phone?.replace(/^tel:/, "");
  return tel || null;
}

/**
 * Construye `https://wa.me/<business_phone>?text=<mensaje>` (URL-encoded).
 * Devuelve `null` si no hay `contact` válido (CA-F1.14: sin config → sin botones).
 */
export function buildWhatsAppUrl(
  contact: ContactInfo | null | undefined,
  message: string,
): string | null {
  const number = waBusinessNumber(contact);
  if (!number || !message.trim()) return null;
  return `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
}

/**
 * Devuelve el href `tel:<business_phone>` del contrato, o `null` si no existe.
 */
export function getCallHref(contact: ContactInfo | null | undefined): string | null {
  const tel = contact?.phone;
  if (!tel) return null;
  return tel.startsWith("tel:") ? tel : `tel:${tel}`;
}
