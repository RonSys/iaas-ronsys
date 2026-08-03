"""
🛵 DeliveryService — Módulo Delivery / Dark Kitchen (Spec 03, Fase A).

Reglas de oro (Spec 03 §2.3):
  - El checkout crea un `Sale` DIRECTO (order_type='delivery') vía
    `SaleService.create_sale` → kárdex (explosión de recetas) + asiento
    contable automáticos. NO se copia el patrón TakeawayOrder.
  - `delivery_orders.sale_id` es la única FK al motor de ventas.
  - Cocina: `KitchenOrder.sale_id` (columna existente) + broadcast WS.
  - Endpoints públicos resuelven tenant por slug y SIEMPRE filtran por él.
"""

import time as _time
from datetime import datetime, time as dtime, UTC
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Company
from app.adapters.db.models.delivery import (
    Courier,
    DeliveryOrder,
    DeliveryZone,
    MarketingCampaign,
)
from app.adapters.db.models.restaurant import (
    KitchenOrder,
    MenuItem,
    MenuModifier,
    Promotion,
    RestaurantSection,
)
from app.adapters.db.models.sales import Sale
from app.core.ws_manager import manager
from app.models.user import User
from app.services.sales_service import SaleService
from zoneinfo import ZoneInfo


LIMA_TZ = "America/Lima"
# Default de ventana nocturna (D5 aprobada): 19:00–24:00 (hora de Lima)
DEFAULT_FROM = dtime(19, 0)
DEFAULT_TO = dtime(23, 59, 59)
_LIMA = ZoneInfo(LIMA_TZ)


def _now() -> datetime:
    return datetime.now(UTC)


def _money(v) -> float:
    return round(float(Decimal(str(v))), 2)


# ═══════════════════════════════════════════════════════════════
# Resolución de tenant (público)
# ═══════════════════════════════════════════════════════════════

async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Company:
    """Resuelve el tenant por slug público. 404 si no existe (R9)."""
    company = (await db.execute(
        select(Company).where(Company.slug == slug)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    return company


async def _system_user_id(db: AsyncSession, tenant_id: int) -> int:
    """Usuario del sistema para pedidos públicos (sin sesión de staff).

    Resuelve el primer usuario activo del tenant (preferencia admin).
    """
    user = (await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        ).order_by(User.role == "admin").limit(1)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=500, detail="Tenant sin usuario activo para procesar pedidos"
        )
    return int(user.id)


# ═══════════════════════════════════════════════════════════════
# Catálogo público
# ═══════════════════════════════════════════════════════════════

def _item_available(item: MenuItem, now_time: dtime | None = None) -> bool:
    """R1: delivery_enabled + ventana horaria (available_from/to, default 19:00–24:00)."""
    if not item.delivery_enabled:
        return False
    if item.available_from is None and item.available_to is None:
        return True  # rige solo delivery_enabled
    t = now_time or datetime.now(_LIMA).time()
    frm = item.available_from or DEFAULT_FROM
    to = item.available_to or DEFAULT_TO
    if frm <= to:
        return frm <= t <= to
    return t >= frm or t <= to  # ventana que cruza medianoche


async def get_public_menu(db: AsyncSession, tenant_id: int) -> dict:
    """Catálogo público: secciones + items delivery + promos vigentes + ventana."""
    now = datetime.now(UTC)
    now_time = datetime.now(_LIMA).time()

    items = (await db.execute(
        select(MenuItem).where(
            MenuItem.tenant_id == tenant_id,
            MenuItem.active.is_(True),
        )
    )).scalars().all()

    sections = (await db.execute(
        select(RestaurantSection).where(
            RestaurantSection.tenant_id == tenant_id,
        ).order_by(RestaurantSection.sort_order, RestaurantSection.id)
    )).scalars().all()

    section_map: dict[int, list] = {}
    for it in items:
        if not _item_available(it, now_time):
            continue
        section_map.setdefault(it.category, []).append(it)

    # Agrupar por sección si existen secciones; fallback por categoría
    sections_out = []
    used_categories: set[str] = set()
    for s in sections:
        items_out = []
        for it in section_map.get(s.name, []):
            used_categories.add(s.name)
            items_out.append(_public_item(it))
        if items_out:
            sections_out.append({"id": s.id, "name": s.name, "items": items_out})
    # Categorías sin sección declarada
    for cat in sorted(section_map.keys()):
        if cat not in used_categories and section_map[cat]:
            sections_out.append({
                "id": 0, "name": cat,
                "items": [_public_item(it) for it in section_map[cat]],
            })

    # Promos vigentes
    promos = (await db.execute(
        select(Promotion).where(
            Promotion.tenant_id == tenant_id,
            Promotion.active.is_(True),
        )
    )).scalars().all()
    promotions_out = []
    for p in promos:
        if p.valid_to and now > p.valid_to:
            continue
        if now < p.valid_from:
            continue
        promotions_out.append({
            "id": p.id, "name": p.name, "promo_type": p.promo_type,
            "discount_value": float(p.discount_value),
            "description": p.description,
        })

    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    settings = (company.settings or {}) if company else {}
    if not isinstance(settings, dict):
        settings = {}
    branding = settings.get("branding", {}) if isinstance(settings.get("branding"), dict) else {}
    delivery_cfg = settings.get("delivery", {}) if isinstance(settings.get("delivery"), dict) else {}
    yape_phone = delivery_cfg.get("yape_phone") or branding.get("yape_phone")

    return {
        "tenant_name": company.name if company else "",
        "delivery_window": {"from": str(DEFAULT_FROM), "to": str(DEFAULT_TO)},
        "currency": "PEN",
        "yape_phone": yape_phone,
        # D-03: branding por tenant para la landing pública (paleta + logo)
        "branding": {
            "palette": branding.get("palette"),
            "logo_url": branding.get("logo_url"),
        },
        "sections": sections_out,
        "promotions": promotions_out,
    }


def _public_item(it: MenuItem) -> dict:
    mods = [
        {
            "id": m.id, "name": m.name,
            "price_adjustment": float(m.price_adjustment),
            "max_select": m.max_select,
        }
        for m in (it.modifiers or [])
    ]
    return {
        "id": it.id, "name": it.name, "description": it.description,
        "price": float(it.price),
        "delivery_surcharge": float(it.delivery_surcharge),
        "category": it.category, "item_type": it.item_type,
        "preparation_area": it.preparation_area,
        "modifiers": mods, "image_url": it.image_url,
        "available": True,
    }


async def get_public_zones(db: AsyncSession, tenant_id: int) -> list[dict]:
    zones = (await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.tenant_id == tenant_id,
            DeliveryZone.active.is_(True),
        )
    )).scalars().all()
    return [
        {
            "id": z.id, "name": z.name, "districts": z.districts,
            "fee": float(z.fee), "min_order": float(z.min_order),
            "eta_min": z.eta_min,
        }
        for z in zones
    ]


# ═══════════════════════════════════════════════════════════════
# Atribución de campaña (R4)
# ═══════════════════════════════════════════════════════════════

async def resolve_campaign(
    db: AsyncSession, tenant_id: int, utm: dict | None,
) -> int | None:
    """Match exacto utm_source+utm_medium+utm_campaign contra campañas activas."""
    if not utm:
        return None
    source = utm.get("source")
    medium = utm.get("medium")
    campaign = utm.get("campaign")
    if not (source and campaign):
        return None
    result = (await db.execute(
        select(MarketingCampaign).where(
            MarketingCampaign.tenant_id == tenant_id,
            MarketingCampaign.active.is_(True),
            MarketingCampaign.utm_source == source,
            MarketingCampaign.utm_campaign == campaign,
        )
    )).scalars().first()
    return result.id if result else None


# ═══════════════════════════════════════════════════════════════
# Checkout (el corazón de la Fase A)
# ═══════════════════════════════════════════════════════════════

async def create_order(db: AsyncSession, tenant_id: int, data: dict) -> dict:
    # ── 1. Zona ──────────────────────────────────────────────
    zone = (await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.id == data["zone_id"],
            DeliveryZone.tenant_id == tenant_id,
            DeliveryZone.active.is_(True),
        )
    )).scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona de delivery no encontrada")

    # ── 2. Validar ítems (disponibilidad + modificadores) ─────
    now_time = datetime.now(_LIMA).time()
    validated: list[dict] = []
    subtotal = 0.0
    for item_data in data["items"]:
        mid = item_data["menu_item_id"]
        menu_item = (await db.execute(
            select(MenuItem).where(
                MenuItem.id == mid, MenuItem.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not menu_item or not menu_item.active:
            raise HTTPException(
                status_code=422, detail=f"Ítem no disponible (id {mid})"
            )
        if not _item_available(menu_item, now_time):
            raise HTTPException(
                status_code=422,
                detail=f"'{menu_item.name}' no está disponible en el horario de delivery",
            )

        qty = int(item_data.get("quantity", 1))
        unit_price = float(menu_item.price)
        mods_total = 0.0

        mod_counts: dict[int, int] = {}
        for mod in item_data.get("modifiers", []):
            mid_mod = mod.get("id") if isinstance(mod, dict) else mod
            if mid_mod:
                mod_qty = mod.get("quantity", 1) if isinstance(mod, dict) else 1
                mod_counts[mid_mod] = mod_counts.get(mid_mod, 0) + max(1, int(mod_qty))
        for mmod_id, count in mod_counts.items():
            db_mod = (await db.execute(
                select(MenuModifier).where(
                    MenuModifier.id == mmod_id,
                    MenuModifier.menu_item_id == menu_item.id,
                )
            )).scalar_one_or_none()
            if db_mod:
                if count > db_mod.max_select:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Modificador '{db_mod.name}': máximo {db_mod.max_select}",
                    )
                mods_total += float(db_mod.price_adjustment) * count

        item_total = qty * (unit_price + mods_total)
        subtotal += item_total
        validated.append({
            "menu_item_id": menu_item.id, "item_name": menu_item.name,
            "quantity": qty, "unit_price": unit_price + mods_total,
            "modifiers_total": mods_total,
            "modifiers": item_data.get("modifiers", []),
            "total": item_total,
            "item_type": menu_item.item_type,
            "preparation_area": menu_item.preparation_area,
        })

    subtotal = _money(subtotal)

    # ── 3. Promoción vigente (mejor descuento simple) ─────────
    from app.services.restaurant_service import PromotionsService
    promos = (await db.execute(
        select(Promotion).where(
            Promotion.tenant_id == tenant_id,
            Promotion.active.is_(True),
        )
    )).scalars().all()
    best_promo, best_discount = None, 0.0
    for p in promos:
        if p.valid_to and datetime.now(UTC) > p.valid_to:
            continue
        if datetime.now(UTC) < p.valid_from:
            continue
        d = await PromotionsService.compute_discount(p, validated)
        if d > best_discount:
            best_promo, best_discount = p, d

    # ── 4. min_order de la zona (R2: contra subtotal) ─────────
    if subtotal < float(zone.min_order):
        raise HTTPException(
            status_code=422,
            detail=f"El pedido mínimo para {zone.name} es S/ {float(zone.min_order):.2f} "
                   f"(subtotal S/ {subtotal:.2f})",
        )

    # ── 5. Totales + fee ──────────────────────────────────────
    fee = float(zone.fee)
    discount_total = _money(best_discount)
    total = _money(subtotal - discount_total + fee)

    # ── 6. Pago (R5) ──────────────────────────────────────────
    payment = data["payment"]
    method = payment["method"]
    if method not in ("yape", "plin", "cash"):
        raise HTTPException(status_code=400, detail="Método de pago no soportado")
    if method in ("yape", "plin") and not payment.get("reference"):
        raise HTTPException(
            status_code=400, detail=f"El pago por {method} requiere el código de referencia"
        )
    payments = [{
        "payment_method": method,
        "amount": total,
        "reference": payment.get("reference"),
    }]

    # ── 7. Crear Sale (motor existente: kárdex + asiento) ────
    customer = data["customer"]
    # El fee entra como ítem de servicio (D1: cuenta 40, sin kárdex) para
    # que totales y pagos cuadren dentro del motor de ventas.
    sale_items = [
        {
            "menu_item_id": it["menu_item_id"],
            "item_name": it["item_name"],
            "quantity": it["quantity"],
            "unit_price": it["unit_price"],
            "total": it["total"],
            "tax_pct": 18,
            "igv_included": True,  # precios de menú finales (incluyen IGV)
        }
        for it in validated
    ]
    if fee > 0:
        sale_items.append({
            "item_name": "Delivery fee",
            "item_type": "service",
            "quantity": 1,
            "unit_price": fee,
            "total": fee,
            "tax_pct": 18,
            "igv_included": True,
        })
    sale_data = {
        "items": sale_items,
        "payments": payments,
        "business_type": "restaurant",
        "restaurant_data": {
            "order_type": "delivery",
            "guests": 1,
            "table_number": None,
            "delivery_address": customer["address"],
            "kitchen_notes": data.get("notes"),
        },
    }
    # Aplicar descuento de promoción en el primer ítem (el motor suma
    # discount_total por ítem; se descuenta el total de la promoción).
    if discount_total > 0:
        sale_data["items"][0]["discount_amount"] = discount_total
        sale_data["items"][0]["total"] = _money(
            float(sale_data["items"][0]["total"]) - discount_total
        )

    sale = await SaleService.create_sale(
        db=db, tenant_id=tenant_id, user_id=await _system_user_id(db, tenant_id),
        data=sale_data,
    )
    sale_detail = sale["sale"]
    sale_id = int(sale_detail["id"])
    sale_number = sale_detail.get("sale_number")

    # ── 8. DeliveryOrder ──────────────────────────────────────
    hex_part = f"{int(_time.time() * 1000):x}"[-10:]
    tracking_code = f"DLV-{hex_part}"
    utm_data = data.get("utm") or {}
    campaign_id = await resolve_campaign(db, tenant_id, utm_data)

    delivery_order = DeliveryOrder(
        tenant_id=tenant_id,
        sale_id=sale_id,
        zone_id=zone.id,
        campaign_id=campaign_id,
        tracking_code=tracking_code,
        customer_name=customer.get("name"),
        customer_phone=customer["phone"],
        customer_address=customer["address"],
        lat=customer.get("lat"),
        lng=customer.get("lng"),
        fee=fee,
        eta_min=zone.eta_min,
        status="received",
        utm=utm_data or None,
        notes=data.get("notes"),
        received_at=_now(),
    )
    db.add(delivery_order)
    await db.flush()

    # ── 9. Comanda a cocina (R8) ──────────────────────────────
    kitchen_items = [
        {
            "menu_item_id": it["menu_item_id"], "name": it["item_name"],
            "quantity": it["quantity"], "unit_price": it["unit_price"],
            "modifiers": it["modifiers"], "modifiers_total": it["modifiers_total"],
            "notes": "", "total": it["total"],
            "item_type": it["item_type"], "preparation_area": it["preparation_area"],
        }
        for it in validated
    ]
    kitchen = KitchenOrder(
        tenant_id=tenant_id, sale_id=sale_id,
        status="pending", items=kitchen_items,
        notes=f"DELIVERY {tracking_code} — {customer.get('name', '')} — {customer['phone']}",
    )
    db.add(kitchen)
    await db.flush()
    await db.refresh(kitchen)

    await manager.broadcast_to_kitchen(tenant_id, "new_delivery", {
        "id": delivery_order.id, "tracking_code": tracking_code,
        "kitchen_order_id": kitchen.id, "customer_name": customer.get("name"),
        "items": kitchen_items, "status": "received",
    })
    await db.commit()

    return {
        "tracking_code": tracking_code,
        "sale_id": sale_id,
        "sale_number": sale_number,
        "status": "received",
        "eta_min": zone.eta_min,
        "totals": {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "fee": fee,
            "total": total,
        },
        "payment": {"method": method, "status": "pending_confirm"},
        "promotion": (
            {"id": best_promo.id, "name": best_promo.name,
             "discount": discount_total}
            if best_promo else None
        ),
    }


# ═══════════════════════════════════════════════════════════════
# Seguimiento + máquina de estados (R10, §3.3)
# ═══════════════════════════════════════════════════════════════

TRANSITIONS: dict[str, list[str]] = {
    "received": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["out_for_delivery", "cancelled"],
    "out_for_delivery": ["delivered", "cancelled"],
    "delivered": [],
    "cancelled": [],
}

STATUS_FIELD = {
    "received": "received_at",
    "preparing": "preparing_at",
    "ready": "ready_at",
    "out_for_delivery": "out_for_delivery_at",
    "delivered": "delivered_at",
    "cancelled": "cancelled_at",
}


async def get_order(db: AsyncSession, order_id: int, tenant_id: int) -> DeliveryOrder:
    order = (await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido delivery no encontrado")
    return order


async def get_by_tracking(db: AsyncSession, tracking_code: str) -> DeliveryOrder | None:
    return (await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.tracking_code == tracking_code)
    )).scalar_one_or_none()


async def update_status(
    db: AsyncSession, order_id: int, tenant_id: int, new_status: str,
) -> dict:
    order = await get_order(db, order_id, tenant_id)
    allowed = TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Transición inválida: {order.status} → {new_status}. "
                   f"Permitidas: {allowed or 'ninguna'}",
        )
    order.status = new_status
    setattr(order, STATUS_FIELD[new_status], _now())
    await db.flush()

    # Si termina, liberar repartidor (CA14)
    if new_status in ("delivered", "cancelled") and order.courier_id:
        courier = (await db.execute(
            select(Courier).where(Courier.id == order.courier_id)
        )).scalar_one_or_none()
        if courier:
            courier.status = "available"
            await db.flush()

    detail = await order_detail(db, order.id, tenant_id)
    await manager.broadcast_to_kitchen(
        tenant_id, "delivery_updated", {"id": order.id, "status": new_status},
    )
    await db.commit()
    return detail


async def assign_courier(
    db: AsyncSession, order_id: int, tenant_id: int, courier_id: int,
) -> dict:
    order = await get_order(db, order_id, tenant_id)
    if order.status not in ("ready", "received", "preparing"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede asignar repartidor en estado '{order.status}'",
        )
    courier = (await db.execute(
        select(Courier).where(
            Courier.id == courier_id,
            Courier.tenant_id == tenant_id,
            Courier.active.is_(True),
        )
    )).scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    if courier.status == "on_delivery":
        raise HTTPException(status_code=409, detail="El repartidor ya tiene una entrega")

    order.courier_id = courier.id
    courier.status = "on_delivery"
    await db.flush()
    await db.commit()
    return await order_detail(db, order.id, tenant_id)


def _timestamps(o: DeliveryOrder) -> dict:
    return {
        "received_at": o.received_at, "preparing_at": o.preparing_at,
        "ready_at": o.ready_at, "out_for_delivery_at": o.out_for_delivery_at,
        "delivered_at": o.delivered_at, "cancelled_at": o.cancelled_at,
    }


async def order_detail(db: AsyncSession, order_id: int, tenant_id: int) -> dict:
    order = await get_order(db, order_id, tenant_id)
    sale = None
    if order.sale_id:
        sale = (await db.execute(
            select(Sale).where(Sale.id == order.sale_id)
        )).scalar_one_or_none()
    return {
        "id": order.id,
        "tracking_code": order.tracking_code,
        "status": order.status,
        "customer": {
            "name": order.customer_name, "phone": order.customer_phone,
            "address": order.customer_address,
        },
        "zone_id": order.zone_id, "courier_id": order.courier_id,
        "campaign_id": order.campaign_id, "utm": order.utm,
        "fee": float(order.fee), "eta_min": order.eta_min,
        "sale_id": order.sale_id,
        "sale_number": sale.sale_number if sale else None,
        "total": float(sale.total) if sale else None,
        "notes": order.notes,
        "timestamps": _timestamps(order),
        "created_at": order.created_at,
    }


async def list_orders(
    db: AsyncSession, tenant_id: int, status_filter: str | None = None,
) -> list[dict]:
    stmt = select(DeliveryOrder).where(DeliveryOrder.tenant_id == tenant_id)
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
        if statuses:
            stmt = stmt.where(DeliveryOrder.status.in_(statuses))
    else:
        stmt = stmt.where(
            DeliveryOrder.status != "delivered",
            DeliveryOrder.status != "cancelled",
        )
    stmt = stmt.order_by(DeliveryOrder.created_at.desc())
    orders = (await db.execute(stmt)).scalars().all()
    return [await order_detail(db, o.id, tenant_id) for o in orders]


# ═══════════════════════════════════════════════════════════════
# Métricas de campañas (ROAS / AOV — Spec 03 §3.4.2)
# ═══════════════════════════════════════════════════════════════

async def metrics_campaigns(
    db: AsyncSession, tenant_id: int,
    date_from=None, date_to=None, channel: str | None = None,
) -> list[dict]:
    campaigns = (await db.execute(
        select(MarketingCampaign).where(
            MarketingCampaign.tenant_id == tenant_id,
        ).order_by(MarketingCampaign.id)
    )).scalars().all()

    out = []
    for c in campaigns:
        if channel and c.channel != channel:
            continue
        stmt = select(func.count(DeliveryOrder.id), func.sum(Sale.total)).join(
            Sale, Sale.id == DeliveryOrder.sale_id,
        ).where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.campaign_id == c.id,
            DeliveryOrder.status == "delivered",
        )
        if date_from:
            stmt = stmt.where(DeliveryOrder.created_at >= date_from)
        if date_to:
            stmt = stmt.where(DeliveryOrder.created_at <= date_to)
        row = (await db.execute(stmt)).one()
        orders = row[0] or 0
        gmv = float(row[1] or 0)
        spend = float(c.spend)
        out.append({
            "campaign_id": c.id,
            "name": c.name,
            "channel": c.channel,
            "spend": spend,
            "orders": orders,
            "gmv": _money(gmv),
            "aov": _money(gmv / orders) if orders else 0.0,
            "roas": _money(gmv / spend) if spend > 0 else 0.0,
        })
    return out


async def metrics_overview(
    db: AsyncSession, tenant_id: int, date_from=None, date_to=None,
) -> dict:
    stmt = select(
        func.count(DeliveryOrder.id),
        func.sum(Sale.total),
        func.sum(DeliveryOrder.fee),
        func.sum(
            func.extract("epoch", DeliveryOrder.delivered_at)
            - func.extract("epoch", DeliveryOrder.received_at)
        ),
    ).join(Sale, Sale.id == DeliveryOrder.sale_id).where(
        DeliveryOrder.tenant_id == tenant_id,
        DeliveryOrder.status == "delivered",
    )
    if date_from:
        stmt = stmt.where(DeliveryOrder.created_at >= date_from)
    if date_to:
        stmt = stmt.where(DeliveryOrder.created_at <= date_to)
    row = (await db.execute(stmt)).one()
    orders = row[0] or 0
    cancelled = (await db.execute(
        select(func.count(DeliveryOrder.id)).where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.status == "cancelled",
        )
    )).scalar() or 0
    total_secs = float(row[3] or 0)
    return {
        "orders": orders,
        "gmv": _money(float(row[1] or 0)),
        "fee_total": _money(float(row[2] or 0)),
        "avg_delivery_min": round(total_secs / 60 / orders, 1) if orders else None,
        "cancelled": cancelled,
    }


# ═══════════════════════════════════════════════════════════════
# CRUD staff (zonas / repartidores / campañas)
# ═══════════════════════════════════════════════════════════════

async def create_zone(db: AsyncSession, tenant_id: int, data: dict) -> dict:
    zone = DeliveryZone(tenant_id=tenant_id, **data)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return _zone_out(zone)


def _zone_out(z: DeliveryZone) -> dict:
    return {
        "id": z.id, "name": z.name, "description": z.description,
        "districts": z.districts, "fee": float(z.fee),
        "min_order": float(z.min_order), "eta_min": z.eta_min,
        "active": z.active, "created_at": z.created_at,
    }


async def list_zones(db: AsyncSession, tenant_id: int) -> list[dict]:
    zones = (await db.execute(
        select(DeliveryZone).where(DeliveryZone.tenant_id == tenant_id)
        .order_by(DeliveryZone.id)
    )).scalars().all()
    return [_zone_out(z) for z in zones]


async def update_zone(
    db: AsyncSession, zone_id: int, tenant_id: int, data: dict,
) -> dict:
    zone = (await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.id == zone_id, DeliveryZone.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    for k, v in data.items():
        if v is not None:
            setattr(zone, k, v)
    await db.commit()
    await db.refresh(zone)
    return _zone_out(zone)


async def delete_zone(db: AsyncSession, zone_id: int, tenant_id: int) -> None:
    zone = (await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.id == zone_id, DeliveryZone.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    await db.delete(zone)
    await db.commit()


async def create_courier(db: AsyncSession, tenant_id: int, data: dict) -> dict:
    courier = Courier(tenant_id=tenant_id, **data)
    db.add(courier)
    await db.commit()
    await db.refresh(courier)
    return _courier_out(courier)


def _courier_out(c: Courier) -> dict:
    return {
        "id": c.id, "name": c.name, "phone": c.phone, "vehicle": c.vehicle,
        "user_id": c.user_id, "status": c.status, "active": c.active,
        "created_at": c.created_at,
    }


async def list_couriers(db: AsyncSession, tenant_id: int) -> list[dict]:
    couriers = (await db.execute(
        select(Courier).where(Courier.tenant_id == tenant_id).order_by(Courier.id)
    )).scalars().all()
    return [_courier_out(c) for c in couriers]


async def update_courier(
    db: AsyncSession, courier_id: int, tenant_id: int, data: dict,
) -> dict:
    courier = (await db.execute(
        select(Courier).where(
            Courier.id == courier_id, Courier.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    for k, v in data.items():
        if v is not None:
            setattr(courier, k, v)
    await db.commit()
    await db.refresh(courier)
    return _courier_out(courier)


async def delete_courier(db: AsyncSession, courier_id: int, tenant_id: int) -> None:
    courier = (await db.execute(
        select(Courier).where(
            Courier.id == courier_id, Courier.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    await db.delete(courier)
    await db.commit()


async def create_campaign(db: AsyncSession, tenant_id: int, data: dict) -> dict:
    campaign = MarketingCampaign(tenant_id=tenant_id, **data)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_out(campaign)


def _campaign_out(c: MarketingCampaign) -> dict:
    return {
        "id": c.id, "name": c.name, "channel": c.channel,
        "utm_source": c.utm_source, "utm_medium": c.utm_medium,
        "utm_campaign": c.utm_campaign, "budget": float(c.budget),
        "spend": float(c.spend), "starts_on": c.starts_on, "ends_on": c.ends_on,
        "active": c.active, "notes": c.notes, "created_at": c.created_at,
    }


async def list_campaigns(db: AsyncSession, tenant_id: int) -> list[dict]:
    campaigns = (await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.tenant_id == tenant_id)
        .order_by(MarketingCampaign.id)
    )).scalars().all()
    return [_campaign_out(c) for c in campaigns]


async def update_campaign(
    db: AsyncSession, campaign_id: int, tenant_id: int, data: dict,
) -> dict:
    campaign = (await db.execute(
        select(MarketingCampaign).where(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    for k, v in data.items():
        if v is not None:
            setattr(campaign, k, v)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_out(campaign)


async def delete_campaign(db: AsyncSession, campaign_id: int, tenant_id: int) -> None:
    campaign = (await db.execute(
        select(MarketingCampaign).where(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    await db.delete(campaign)
    await db.commit()
