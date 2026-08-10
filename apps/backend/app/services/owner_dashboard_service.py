"""
Panel del Dueño — servicio de métricas ejecutivas (Spec 04, V1).

Consolida por tenant: KPIs de ventas, series por hora/día, canales
(dine_in/takeout/delivery), top platos, pagos y delivery (zonas, embudo,
SLA, GMV, fee) + ROAS por campaña. Reutiliza delivery_service
(metrics_overview / metrics_campaigns) — no duplica lógica.

Solo lectura (D5). Fechas: date_from/date_to opcionales (ISO YYYY-MM-DD);
sin fechas → todo el histórico. Excluye ventas anuladas (is_voided=True).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.delivery import (
    DeliveryOrder,
    DeliveryZone,
)
from app.adapters.db.models.restaurant import KitchenOrder
from app.adapters.db.models.sales import (
    RestaurantSale,
    Sale,
    SaleItem,
    SalePayment,
)
from app.services.delivery_service import metrics_campaigns, metrics_overview

# ─── Helpers de fechas ────────────────────────────────────────


def _parse_date(value: str | None) -> date | None:
    """'YYYY-MM-DD' → date (None si vacío)."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Fecha inválida '{value}' (formato YYYY-MM-DD)")


def _today() -> date:
    return datetime.now().date()


def _money(v) -> float:
    return round(float(v or 0), 2)


def _resolve_dates(date_from: str | None, date_to: str | None) -> tuple[date, date]:
    """Resuelve el rango: default = últimos 30 días (incluye hoy)."""
    to = _parse_date(date_to) or _today()
    frm = _parse_date(date_from)
    if frm is None:
        frm = to - timedelta(days=29)
    if frm > to:
        raise ValueError("date_from no puede ser mayor que date_to")
    return frm, to


# ─── Queries del panel ────────────────────────────────────────

async def _kpis(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """KPIs de ventas (sin anuladas) + conteo por canal + en vivo."""
    base = (
        select(
            func.coalesce(func.sum(Sale.total), 0),
            func.count(Sale.id),
        )
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
    )
    row = (await db.execute(base)).one()
    sales_total = _money(row[0])
    orders_count = int(row[1] or 0)

    # Conteo por canal desde restaurant_sales (join 1:1)
    canales = (await db.execute(
        select(RestaurantSale.order_type, func.count(Sale.id))
        .join(Sale, Sale.id == RestaurantSale.sale_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(RestaurantSale.order_type)
    )).all()
    por_canal = {c: int(n or 0) for c, n in canales}
    orders_delivery = por_canal.get("delivery", 0)
    orders_dine_in = por_canal.get("dine_in", 0)
    orders_takeout = por_canal.get("takeout", 0)

    # En vivo (sin filtro de fecha — estado actual)
    kitchen_open = (await db.execute(
        select(func.count(KitchenOrder.id)).where(
            KitchenOrder.tenant_id == tenant_id,
            KitchenOrder.status.in_(("pending", "preparing")),
        )
    )).scalar() or 0
    delivery_in_route = (await db.execute(
        select(func.count(DeliveryOrder.id)).where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.status == "out_for_delivery",
        )
    )).scalar() or 0

    return {
        "sales_total": sales_total,
        "orders_count": orders_count,
        "avg_ticket": _money(sales_total / orders_count) if orders_count else 0.0,
        "orders_delivery": orders_delivery,
        "orders_dine_in": orders_dine_in,
        "orders_takeout": orders_takeout,
        "delivery_pct": round(orders_delivery / orders_count * 100, 1) if orders_count else 0.0,
        "kitchen_open": int(kitchen_open),
        "delivery_in_route": int(delivery_in_route),
    }


async def _sales_by_hour(db: AsyncSession, tenant_id: int, frm: date, to: date) -> list[dict]:
    """Serie 0-23: ventas por hora separando salón (dine_in) vs delivery."""
    rows = (await db.execute(
        select(
            func.extract("hour", Sale.sale_time).label("hora"),
            RestaurantSale.order_type,
            func.coalesce(func.sum(Sale.total), 0),
        )
        .join(RestaurantSale, RestaurantSale.sale_id == Sale.id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by("hora", RestaurantSale.order_type)
        .order_by("hora")
    )).all()
    horas: dict[int, dict] = {h: {"hour": h, "dine_in": 0.0, "delivery": 0.0}
                              for h in range(24)}
    for hora, canal, total in rows:
        h = int(hora or 0)
        if canal == "delivery":
            horas[h]["delivery"] = _money(total)
        else:  # dine_in y takeout suman al salón
            horas[h]["dine_in"] = _money(horas[h]["dine_in"] + total)
    return [horas[h] for h in range(24)]


async def _sales_by_weekday(db: AsyncSession, tenant_id: int, frm: date, to: date) -> list[dict]:
    """Serie 1-7 (ISO: 1=Lun..7=Dom): total por día de semana."""
    rows = (await db.execute(
        select(
            func.extract("isodow", Sale.sale_date).label("dia"),
            func.coalesce(func.sum(Sale.total), 0),
        )
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by("dia")
    )).all()
    dias = {d: 0.0 for d in range(1, 8)}
    for dia, total in rows:
        dias[int(dia)] = _money(total)
    return [{"weekday": d, "total": dias[d]} for d in range(1, 8)]


async def _channels(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """S/ por canal (dine_in/takeout/delivery) — sin anuladas."""
    rows = (await db.execute(
        select(RestaurantSale.order_type, func.coalesce(func.sum(Sale.total), 0))
        .join(Sale, Sale.id == RestaurantSale.sale_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(RestaurantSale.order_type)
    )).all()
    return {c: _money(t) for c, t in rows}


async def _top_platos(db: AsyncSession, tenant_id: int, frm: date, to: date, limit: int = 10) -> list[dict]:
    """Top N platos por cantidad vendida (con total en soles). Sin anuladas."""
    rows = (await db.execute(
        select(
            SaleItem.item_name,
            func.coalesce(func.sum(SaleItem.quantity), 0),
            func.coalesce(func.sum(SaleItem.total), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(SaleItem.item_name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
    )).all()
    return [{"name": n, "qty": float(q or 0), "total": _money(t)} for n, q, t in rows]


async def _payments(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """S/ por método de pago (payment_method)."""
    rows = (await db.execute(
        select(SalePayment.payment_method, func.coalesce(func.sum(SalePayment.amount), 0))
        .join(Sale, Sale.id == SalePayment.sale_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(SalePayment.payment_method)
    )).all()
    return {m: _money(a) for m, a in rows}


async def _delivery_block(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """Zonas + embudo + SLA + GMV + fee (reusa metrics_overview)."""
    # Pedidos por zona (todos los estados del período)
    zonas = (await db.execute(
        select(DeliveryZone.name, func.count(DeliveryOrder.id))
        .join(DeliveryOrder, DeliveryOrder.zone_id == DeliveryZone.id)
        .where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.created_at >= datetime.combine(frm, time.min),
            DeliveryOrder.created_at <= datetime.combine(to, time.max),
        )
        .group_by(DeliveryZone.name)
        .order_by(func.count(DeliveryOrder.id).desc())
    )).all()

    # Embudo: conteo por estado real del CHECK (6 estados)
    embudo_rows = (await db.execute(
        select(DeliveryOrder.status, func.count(DeliveryOrder.id))
        .where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.created_at >= datetime.combine(frm, time.min),
            DeliveryOrder.created_at <= datetime.combine(to, time.max),
        )
        .group_by(DeliveryOrder.status)
    )).all()
    funnel = {"received": 0, "preparing": 0, "ready": 0,
              "out_for_delivery": 0, "delivered": 0, "cancelled": 0}
    for st, n in embudo_rows:
        if st in funnel:
            funnel[st] = int(n or 0)

    # Reuso: métricas entregados (D7 — GMV = entregados, consistente)
    ov = await metrics_overview(
        db, tenant_id,
        date_from=datetime.combine(frm, time.min),
        date_to=datetime.combine(to, time.max),
    )
    return {
        "orders_by_zone": [{"zone": z, "orders": int(n or 0)} for z, n in zonas],
        "funnel": funnel,
        "avg_delivery_min": ov.get("avg_delivery_min"),
        "gmv": ov.get("gmv", 0.0),
        "fee_total": ov.get("fee_total", 0.0),
    }


async def _campaigns(db: AsyncSession, tenant_id: int, frm: date, to: date) -> list[dict]:
    """ROAS por campaña (reusa metrics_campaigns)."""
    return await metrics_campaigns(
        db, tenant_id,
        date_from=datetime.combine(frm, time.min),
        date_to=datetime.combine(to, time.max),
    )


# ─── Orquestador ──────────────────────────────────────────────

async def get_owner_dashboard(
    db: AsyncSession, tenant_id: int,
    date_from: str | None = None, date_to: str | None = None,
) -> dict:
    """Resumen ejecutivo completo del dueño (Spec 04 §3.1)."""
    frm, to = _resolve_dates(date_from, date_to)
    return {
        "period": {"date_from": frm.isoformat(), "date_to": to.isoformat()},
        "kpis": await _kpis(db, tenant_id, frm, to),
        "sales_by_hour": await _sales_by_hour(db, tenant_id, frm, to),
        "sales_by_weekday": await _sales_by_weekday(db, tenant_id, frm, to),
        "channels": await _channels(db, tenant_id, frm, to),
        "top_platos": await _top_platos(db, tenant_id, frm, to),
        "payments": await _payments(db, tenant_id, frm, to),
        "delivery": await _delivery_block(db, tenant_id, frm, to),
        "campaigns": await _campaigns(db, tenant_id, frm, to),
    }
