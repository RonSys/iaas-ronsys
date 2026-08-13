/**
 * PublicMenuPage — Landing pública de Delivery (Spec 03, Fase A).
 *
 * Ruta: /menu/:slug — SIN autenticación.
 * - Catálogo nocturno (filtrado por ventana horaria + delivery_enabled en backend)
 * - Carrito + checkout (zona, pago Yape/Plin/contraentrega, UTM automática)
 * - Seguimiento por código
 * - Branding del tenant (D-03): colores/logo desde companies.settings
 *
 * @module pages/public/PublicMenuPage
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  buildWhatsAppUrl,
  checkoutOrder,
  getCallHref,
  getPublicMenu,
  getPublicZones,
  getTrackingStatus,
  type CheckoutResponse,
  type ContactInfo,
  type PublicMenu,
  type PublicMenuItem,
  type PublicZone,
  type TrackingStatus,
} from "@/services/publicMenuApi";
import {
  ModifierBottomSheet,
  type MenuModifier,
  type ModifierSelection,
} from "@/components/restaurante/ModifierBottomSheet";

interface CartItem {
  item: PublicMenuItem;
  quantity: number;
  modifiers: ModifierSelection[];
}

function modifierKey(mods: ModifierSelection[]): string {
  return mods.length > 0 ? mods.map((m) => `${m.id}:${m.quantity}`).sort().join(",") : "";
}

/** Aplica la paleta del tenant a CSS custom properties (sin auth) */
function applyTenantPalette(palette?: Record<string, string> | null) {
  const root = document.documentElement.style;
  if (!palette) return;
  const map: Record<string, string> = {
    primary: "--color-primary",
    secondary: "--color-secondary",
    accent: "--color-accent",
    background: "--color-background",
    surface: "--color-surface",
    text_primary: "--color-text-primary",
    text_secondary: "--color-text-secondary",
    success: "--color-success",
    warning: "--color-warning",
    error: "--color-error",
  };
  for (const [key, cssVar] of Object.entries(map)) {
    const val = palette[key];
    if (val) root.setProperty(cssVar, val);
  }
}

type View = "menu" | "tracking";

const PAYMENT_METHODS = [
  { id: "yape", label: "📱 Yape" },
  { id: "plin", label: "💜 Plin" },
  { id: "cash", label: "💵 Contraentrega" },
];

export function PublicMenuPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [menu, setMenu] = useState<PublicMenu | null>(null);
  const [zones, setZones] = useState<PublicZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("menu");

  const [cart, setCart] = useState<CartItem[]>([]);
  const [modifierItem, setModifierItem] = useState<PublicMenuItem | null>(null);
  const [modifierSheetOpen, setModifierSheetOpen] = useState(false);

  // Checkout form
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [payMethod, setPayMethod] = useState("yape");
  const [payReference, setPayReference] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CheckoutResponse | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Tracking
  const [trackingCode, setTrackingCode] = useState("");
  const [tracking, setTracking] = useState<TrackingStatus | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      const [m, z] = await Promise.all([getPublicMenu(slug), getPublicZones(slug)]);
      setMenu(m);
      setZones(z);
      applyTenantPalette(m.branding?.palette);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el menú");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const selectedZone = useMemo(
    () => zones.find((z) => z.id === Number(zoneId)),
    [zones, zoneId],
  );

  const subtotal = useMemo(
    () =>
      cart.reduce((sum, c) => {
        const modSum = c.modifiers.reduce((s, m) => s + m.price_adjustment * m.quantity, 0);
        return sum + (c.item.price + modSum) * c.quantity;
      }, 0),
    [cart],
  );

  // ── Botones de contacto (Spec 04 §3.6 — D5): wa.me / tel: ──
  // Los enlaces se construyen SIEMPRE desde `contact` del menú público (§3.5),
  // nunca con números hardcodeados (R-F1.3 / CA-F1.11). Si `contact` es null
  // (config inactiva) los hrefs son null → botones ocultos (CA-F1.14).
  const contact = menu?.contact ?? null;
  const waOrderMessage = useMemo(() => {
    const tenant = menu?.tenant_name ?? "";
    if (cart.length === 0) return `¡Hola ${tenant}! Quiero hacer un pedido.`;
    const items = cart.map((c) => `${c.quantity}x ${c.item.name}`).join(", ");
    const total = subtotal + (selectedZone?.fee ?? 0);
    return `¡Hola ${tenant}! Quiero hacer un pedido: ${items} — Total aprox: S/ ${total.toFixed(2)}`;
  }, [cart, menu?.tenant_name, subtotal, selectedZone?.fee]);
  const waOrderHref = useMemo(
    () => buildWhatsAppUrl(contact, waOrderMessage),
    [contact, waOrderMessage],
  );
  const callHref = useMemo(() => getCallHref(contact), [contact]);

  const addToCart = (item: PublicMenuItem, preselected: ModifierSelection[] = []) => {
    if (item.modifiers.length > 0 && preselected.length === 0) {
      setModifierItem(item);
      setModifierSheetOpen(true);
      return;
    }
    const mods = preselected;
    setCart((prev) => {
      const existing = prev.find(
        (c) => c.item.id === item.id && modifierKey(c.modifiers) === modifierKey(mods),
      );
      if (existing) {
        return prev.map((c) =>
          c.item.id === item.id && modifierKey(c.modifiers) === modifierKey(mods)
            ? { ...c, quantity: c.quantity + 1 }
            : c,
        );
      }
      return [...prev, { item, quantity: 1, modifiers: mods }];
    });
    setModifierItem(null);
  };

  const updateQty = (index: number, qty: number) => {
    if (qty <= 0) {
      setCart((prev) => prev.filter((_, i) => i !== index));
      return;
    }
    setCart((prev) => prev.map((c, i) => (i === index ? { ...c, quantity: qty } : c)));
  };

  const handleCheckout = async () => {
    setFormError(null);
    if (cart.length === 0) return setFormError("Agrega al menos un plato a tu pedido.");
    if (!phone.trim()) return setFormError("Ingresa tu teléfono.");
    if (address.trim().length < 5) return setFormError("Ingresa tu dirección completa.");
    if (!zoneId) return setFormError("Selecciona tu zona de entrega.");
    if ((payMethod === "yape" || payMethod === "plin") && !payReference.trim()) {
      return setFormError("Ingresa el código de referencia de tu pago.");
    }
    setSubmitting(true);
    try {
      const payload = {
        items: cart.map((c) => ({
          menu_item_id: c.item.id,
          quantity: c.quantity,
          modifiers: c.modifiers.map((m) => ({ id: m.id, quantity: m.quantity })),
        })),
        customer: { name: name.trim() || null, phone: phone.trim(), address: address.trim() },
        zone_id: Number(zoneId),
        payment: {
          method: payMethod,
          reference: payMethod === "cash" ? null : payReference.trim(),
        },
        notes: notes.trim() || null,
        utm: parseUtm(),
      };
      const res = await checkoutOrder(slug, payload);
      setResult(res);
      setCart([]);
      setName(""); setPhone(""); setAddress(""); setZoneId(""); setPayReference(""); setNotes("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al procesar el pedido");
    } finally {
      setSubmitting(false);
    }
  };

  const handleTracking = async () => {
    if (!trackingCode.trim()) return;
    setTrackingLoading(true);
    setError(null);
    try {
      setTracking(await getTrackingStatus(trackingCode.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código no encontrado");
      setTracking(null);
    } finally {
      setTrackingLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-brand-background flex items-center justify-center">
        <div className="text-center">
          <span className="text-4xl">🐟</span>
          <p className="mt-3 text-brand-text-secondary text-sm">Cargando menú...</p>
        </div>
      </div>
    );
  }

  if (error && !menu) {
    return (
      <div className="min-h-screen bg-brand-background flex items-center justify-center p-6">
        <div className="card p-8 max-w-md text-center">
          <span className="text-5xl block mb-4">🛵</span>
          <h1 className="text-xl font-bold text-brand-text-primary mb-2">No encontramos el local</h1>
          <p className="text-sm text-brand-text-secondary">{error}</p>
          <a href="/" className="inline-block mt-4 text-sm text-brand-primary underline">
            Volver al inicio
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-background">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-brand-surface shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {menu?.branding?.logo_url ? (
              <img src={menu.branding.logo_url} alt={menu.tenant_name} className="h-9 w-9 rounded-full object-cover" />
            ) : (
              <span className="text-2xl">🐟</span>
            )}
            <div className="min-w-0">
              <p className="font-bold text-brand-text-primary truncate">{menu?.tenant_name}</p>
              <p className="text-xs text-brand-text-secondary">
                🕐 Delivery {menu?.delivery_window?.from?.slice(0, 5)} – {menu?.delivery_window?.to?.slice(0, 5)}
              </p>
            </div>
          </div>
          <nav className="flex gap-1">
            <button
              onClick={() => setView("menu")}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                view === "menu" ? "bg-brand-primary text-white" : "border border-gray-300"
              }`}
            >
              🍽️ Menú
            </button>
            <button
              onClick={() => setView("tracking")}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                view === "tracking" ? "bg-brand-primary text-white" : "border border-gray-300"
              }`}
            >
              📍 Seguir pedido
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {view === "menu" ? (
          <>
            {(waOrderHref || callHref) && (
              <div className="bg-brand-primary text-white rounded-2xl p-6 mb-6 shadow-sm">
                <h1 className="text-2xl font-bold">🍽️ {menu?.tenant_name}</h1>
                <p className="text-white/80 text-sm mt-1">
                  Delivery nocturno — arma tu pedido y contáctanos directo por WhatsApp o llámanos.
                </p>
                <div className="flex flex-wrap gap-2 mt-4">
                  {waOrderHref && (
                    <a
                      href={waOrderHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-white text-brand-primary rounded-xl text-sm font-bold hover:opacity-90"
                    >
                      💬 Pedir por WhatsApp
                    </a>
                  )}
                  {callHref && (
                    <a
                      href={callHref}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-white/60 text-white rounded-xl text-sm font-semibold hover:bg-white/10"
                    >
                      📞 Llamar
                    </a>
                  )}
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Catálogo */}
            <div className="lg:col-span-2 space-y-6">
              {menu?.promotions && menu.promotions.length > 0 && (
                <div className="bg-brand-primary/10 border border-brand-primary/30 rounded-xl p-3">
                  <p className="text-sm font-semibold text-brand-primary">🎉 Promociones vigentes</p>
                  {menu.promotions.map((p) => (
                    <p key={p.id} className="text-xs text-brand-text-secondary mt-1">
                      • {p.name}
                    </p>
                  ))}
                </div>
              )}
              {menu?.sections.map((section) => (
                <section key={section.id || section.name}>
                  <h2 className="text-sm font-bold uppercase tracking-wide text-brand-text-secondary mb-3">
                    {section.name}
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {section.items.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => addToCart(item)}
                        disabled={!item.available}
                        className="text-left card p-4 hover:border-brand-primary transition-all disabled:opacity-50"
                      >
                        <div className="flex justify-between gap-2">
                          <p className="font-semibold text-brand-text-primary">{item.name}</p>
                          <p className="font-bold text-brand-primary whitespace-nowrap">
                            S/ {item.price.toFixed(2)}
                          </p>
                        </div>
                        {item.description && (
                          <p className="text-xs text-brand-text-secondary mt-1 line-clamp-2">
                            {item.description}
                          </p>
                        )}
                        <p className="text-xs text-brand-text-secondary mt-2">
                          {item.modifiers.length > 0
                            ? `Personalizable (${item.modifiers.length} opciones)`
                            : "＋ Agregar al pedido"}
                        </p>
                      </button>
                    ))}
                  </div>
                </section>
              ))}
              {menu?.sections.length === 0 && (
                <div className="card p-10 text-center">
                  <span className="text-4xl block mb-3">🌙</span>
                  <p className="font-medium text-brand-text-primary">El delivery aún está cerrado</p>
                  <p className="text-sm text-brand-text-secondary mt-1">
                    Nuestro horario de delivery es de {menu?.delivery_window?.from?.slice(0, 5)} a{" "}
                    {menu?.delivery_window?.to?.slice(0, 5)}. ¡Vuelve pronto!
                  </p>
                </div>
              )}
            </div>

            {/* Carrito + checkout */}
            <div className="space-y-4">
              {result ? (
                <SuccessCard
                  result={result}
                  contact={contact}
                  onTrack={() => {
                    setView("tracking");
                    setTrackingCode(result.tracking_code);
                  }}
                  onNew={() => setResult(null)}
                />
              ) : (
                <>
                  <div className="card p-4">
                    <h3 className="font-bold text-brand-text-primary mb-3">🧾 Tu pedido</h3>
                    {cart.length === 0 ? (
                      <p className="text-sm text-brand-text-secondary">
                        Selecciona platos del menú para armar tu pedido.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {cart.map((c, i) => {
                          const modSum = c.modifiers.reduce((s, m) => s + m.price_adjustment * m.quantity, 0);
                          const modLabel =
                            c.modifiers.length > 0
                              ? ` (${c.modifiers.map((m) => (m.quantity > 1 ? `${m.quantity}x ${m.name}` : m.name)).join(", ")})`
                              : "";
                          return (
                            <div key={i} className="flex items-center gap-2 text-sm">
                              <span className="flex-1 truncate">
                                {c.item.name}
                                {modLabel && (
                                  <span className="text-xs text-brand-text-secondary">{modLabel}</span>
                                )}
                              </span>
                              <input
                                type="number"
                                min={1}
                                value={c.quantity}
                                onChange={(e) => updateQty(i, Number(e.target.value))}
                                className="w-12 px-1 py-0.5 border rounded text-center text-xs"
                              />
                              <span className="w-16 text-right font-medium">
                                S/ {((c.item.price + modSum) * c.quantity).toFixed(2)}
                              </span>
                              <button onClick={() => updateQty(i, 0)} className="text-red-500 text-xs">✕</button>
                            </div>
                          );
                        })}
                        <div className="border-t pt-2 space-y-1 text-sm">
                          <div className="flex justify-between text-brand-text-secondary">
                            <span>Subtotal</span>
                            <span>S/ {subtotal.toFixed(2)}</span>
                          </div>
                          {selectedZone && (
                            <div className="flex justify-between">
                              <span>Delivery ({selectedZone.name})</span>
                              <span>S/ {selectedZone.fee.toFixed(2)}</span>
                            </div>
                          )}
                          <div className="flex justify-between font-bold text-base">
                            <span>Total estimado</span>
                            <span>
                              S/ {(subtotal + (selectedZone?.fee ?? 0)).toFixed(2)}
                            </span>
                          </div>
                          {selectedZone && subtotal < selectedZone.min_order && (
                            <p className="text-xs text-amber-600">
                              ⚠️ Pedido mínimo: S/ {selectedZone.min_order.toFixed(2)}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="card p-4 space-y-3">
                    <h3 className="font-bold text-brand-text-primary">🚚 Entrega</h3>
                    <div>
                      <label className="block text-xs font-medium mb-1">Zona de entrega *</label>
                      <select
                        value={zoneId}
                        onChange={(e) => setZoneId(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                      >
                        <option value="">Selecciona tu zona</option>
                        {zones.map((z) => (
                          <option key={z.id} value={z.id}>
                            {z.name} — S/ {z.fee.toFixed(2)} · {z.eta_min} min
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Nombre</label>
                      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Tu nombre" className="w-full px-3 py-2 border rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Teléfono *</label>
                      <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="999 888 777" className="w-full px-3 py-2 border rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Dirección *</label>
                      <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Calle, número, referencia" className="w-full px-3 py-2 border rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Pago *</label>
                      <div className="grid grid-cols-3 gap-1.5">
                        {PAYMENT_METHODS.map((m) => (
                          <button
                            key={m.id}
                            onClick={() => setPayMethod(m.id)}
                            className={`px-2 py-1.5 rounded-lg text-xs border ${
                              payMethod === m.id
                                ? "bg-brand-primary text-white border-brand-primary"
                                : "border-gray-300 hover:bg-gray-50"
                            }`}
                          >
                            {m.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    {payMethod !== "cash" && (
                      <div>
                        <label className="block text-xs font-medium mb-1">
                          Código de referencia del pago *
                        </label>
                        <input
                          value={payReference}
                          onChange={(e) => setPayReference(e.target.value)}
                          placeholder="Ej: 8 caracteres de tu Yape/Plin"
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                        {payMethod === "yape" && menu?.yape_phone && (
                          <p className="text-xs text-brand-text-secondary mt-1">
                            📱 Yapea al número: <b>{menu.yape_phone}</b> y copia el código.
                          </p>
                        )}
                      </div>
                    )}
                    <div>
                      <label className="block text-xs font-medium mb-1">Notas</label>
                      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Ej: sin cebolla, extra picante" className="w-full px-3 py-2 border rounded-lg text-sm" />
                    </div>
                    {formError && (
                      <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                        {formError}
                      </p>
                    )}
                    <button
                      onClick={handleCheckout}
                      disabled={submitting || cart.length === 0}
                      className="w-full py-3 bg-brand-success text-white rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-50"
                    >
                      {submitting ? "Procesando pedido..." : `🛵 Confirmar pedido · S/ ${(subtotal + (selectedZone?.fee ?? 0)).toFixed(2)}`}
                    </button>
                    <p className="text-[11px] text-brand-text-secondary text-center">
                      Al confirmar aceptas el pedido mínimo de la zona y los tiempos estimados de entrega.
                    </p>
                  </div>
                </>
              )}
            </div>
            </div>
          </>
        ) : (
          /* Tracking */
          <div className="max-w-md mx-auto space-y-4">
            <div className="card p-6">
              <h2 className="font-bold text-brand-text-primary mb-3">📍 Seguir mi pedido</h2>
              <div className="flex gap-2">
                <input
                  value={trackingCode}
                  onChange={(e) => setTrackingCode(e.target.value)}
                  placeholder="Código DLV-XXXX"
                  className="flex-1 px-3 py-2 border rounded-lg text-sm font-mono"
                />
                <button
                  onClick={handleTracking}
                  disabled={trackingLoading}
                  className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm disabled:opacity-50"
                >
                  {trackingLoading ? "..." : "Buscar"}
                </button>
              </div>
            </div>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
            )}
            {tracking && <TrackingTimeline tracking={tracking} />}
          </div>
        )}
      </main>

      <footer className="text-center py-6 text-xs text-brand-text-secondary">
        Pedidos nocturnos · El Segoviano 🐟 — calidad de cevichería, ahora en tu puerta
      </footer>

      <ModifierBottomSheet
        open={modifierSheetOpen}
        onOpenChange={(open) => {
          setModifierSheetOpen(open);
          if (!open) setModifierItem(null);
        }}
        itemName={modifierItem?.name ?? ""}
        itemPrice={modifierItem?.price}
        modifiers={(modifierItem?.modifiers as MenuModifier[]) ?? []}
        onConfirm={(selected) => {
          if (modifierItem) addToCart(modifierItem, selected);
        }}
      />
    </div>
  );
}

/** Extrae UTMs de la URL (primer clic de campaña) */
function parseUtm(): Record<string, string> | null {
  try {
    const params = new URLSearchParams(window.location.search);
    const source = params.get("utm_source");
    const campaign = params.get("utm_campaign");
    if (!source || !campaign) return null;
    const utm: Record<string, string> = {
      source,
      medium: params.get("utm_medium") || "cpc",
      campaign,
    };
    const term = params.get("utm_term");
    const content = params.get("utm_content");
    if (term) utm.term = term;
    if (content) utm.content = content;
    return utm;
  } catch {
    return null;
  }
}

function SuccessCard({
  result,
  contact,
  onTrack,
  onNew,
}: {
  result: CheckoutResponse;
  contact: ContactInfo | null;
  onTrack: () => void;
  onNew: () => void;
}) {
  // Spec 04 §3.6 — botón "Ver mi pedido por WhatsApp" (mensaje de servicio con tracking).
  // Solo se renderiza si `contact` es válido (CA-F1.14).
  const waTrackingHref = buildWhatsAppUrl(
    contact,
    `Hola, mi pedido es ${result.tracking_code}. ¿En qué estado está?`,
  );
  return (
    <div className="card p-6 text-center">
      <span className="text-5xl block mb-3">✅</span>
      <h3 className="text-lg font-bold text-brand-text-primary mb-1">¡Pedido confirmado!</h3>
      <p className="text-sm text-brand-text-secondary">
        Tu código de seguimiento es:
      </p>
      <p className="font-mono font-bold text-brand-primary text-lg my-2">{result.tracking_code}</p>
      <p className="text-xs text-brand-text-secondary">
        Tiempo estimado: <b>{result.eta_min} min</b> · Total:{" "}
        <b>S/ {result.totals.total.toFixed(2)}</b>
      </p>
      {result.promotion && (
        <p className="text-xs text-green-600 mt-1">
          🎉 Promoción aplicada: {result.promotion.name} (−S/ {result.promotion.discount.toFixed(2)})
        </p>
      )}
      <div className="flex flex-wrap gap-2 justify-center mt-4">
        {waTrackingHref && (
          <a
            href={waTrackingHref}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:opacity-90"
          >
            💬 Ver mi pedido por WhatsApp
          </a>
        )}
        <button onClick={onTrack} className="px-4 py-2 bg-brand-primary text-white rounded-lg text-sm">
          📍 Seguir mi pedido
        </button>
        <button onClick={onNew} className="px-4 py-2 border rounded-lg text-sm">
          Nuevo pedido
        </button>
      </div>
    </div>
  );
}

const TRACK_STEPS: { key: string; label: string; icon: string }[] = [
  { key: "received_at", label: "Pedido recibido", icon: "📥" },
  { key: "preparing_at", label: "En cocina", icon: "👨‍🍳" },
  { key: "ready_at", label: "Listo", icon: "🍽️" },
  { key: "out_for_delivery_at", label: "En camino", icon: "🛵" },
  { key: "delivered_at", label: "Entregado", icon: "🏠" },
];

function TrackingTimeline({ tracking }: { tracking: TrackingStatus }) {
  const isCancelled = tracking.status === "cancelled";
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="font-mono font-bold">{tracking.tracking_code}</p>
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            isCancelled
              ? "bg-red-100 text-red-600"
              : tracking.status === "delivered"
                ? "bg-green-100 text-green-700"
                : "bg-blue-100 text-blue-700"
          }`}
        >
          {isCancelled ? "Cancelado" : tracking.status === "delivered" ? "Entregado" : "En proceso"}
        </span>
      </div>
      {isCancelled ? (
        <p className="text-sm text-red-600">Este pedido fue cancelado.</p>
      ) : (
        <ol className="space-y-3">
          {TRACK_STEPS.map((step, i) => {
            const ts = tracking.timestamps[step.key];
            const done = Boolean(ts);
            return (
              <li key={step.key} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                      done ? "bg-brand-success text-white" : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {done ? "✓" : step.icon}
                  </span>
                  {i < TRACK_STEPS.length - 1 && (
                    <span className={`w-0.5 flex-1 ${done ? "bg-brand-success" : "bg-gray-200"}`} />
                  )}
                </div>
                <div className="pb-4">
                  <p className={`text-sm font-medium ${done ? "text-brand-text-primary" : "text-gray-400"}`}>
                    {step.label}
                  </p>
                  {done && (
                    <p className="text-xs text-brand-text-secondary">
                      {new Date(ts as string).toLocaleString("es-PE", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
