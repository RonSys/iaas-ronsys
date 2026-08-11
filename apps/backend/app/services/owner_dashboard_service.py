"""
Panel del Dueño — servicio de métricas ejecutivas (Spec 04, V1 + V2).

V1: KPIs de ventas, series por hora/día, canales (dine_in/takeout/delivery),
top platos, pagos y delivery (zonas, embudo, SLA, GMV, fee) + ROAS por campaña.
Reutiliza delivery_service (metrics_overview / metrics_campaigns) — no duplica.

V2 (contrato §3.1-V2, bloques CA10-CA14):
  - heatmap: serie ventas (S/) por hora (0-23) × día de semana (1=Lun..7=Dom),
    separada por canal (dine_in/delivery; takeout suma a dine_in, misma
    convención que _sales_by_hour de V1). Rows completos (24×7) con 0.
  - margins: costo de venta por canal = Σ (cantidad vendida × average_cost del
    ingrediente) vía recetas — misma fórmula que recipe_explosion (R2: solo
    ítems con receta aportan costo; margen parcial declarado en costable_note).
  - comparison: período actual vs previo de igual longitud inmediatamente
    anterior, con deltas (*_pct null si previous=0; delivery_pct_delta en pts).
  - alerts: desviación del período (o último día si date_from==date_to) vs
    promedio de los 7 días calendario previos; red ≤ -20%, yellow ≤ -10%.
  - export PDF (CA13-b): render_owner_pdf — reportlab platypus, 9 secciones
    en español, misma data de get_owner_dashboard (una sola llamada).

Solo lectura (D5). Fechas: date_from/date_to opcionales (ISO YYYY-MM-DD);
sin fechas → últimos 30 días. Excluye ventas anuladas (is_voided=True).
"""
from __future__ import annotations

import csv
import io
import os
from datetime import date, datetime, time, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Product
from app.adapters.db.models.delivery import (
    DeliveryOrder,
    DeliveryZone,
    MarketingCampaign,
)
from app.adapters.db.models.restaurant import KitchenOrder, MenuItem, Recipe, RecipeIngredient
from app.adapters.db.models.sales import (
    RestaurantSale,
    Sale,
    SaleItem,
    SalePayment,
)
from app.models.user import User
from app.services.delivery_service import metrics_campaigns, metrics_overview

# ─── Constantes V2 (contrato §3.1-V2) ──────────────────────────

COSTABLE_NOTE = (
    "Margen calculado solo sobre ítems con receta (average_cost); "
    "ventas sin receta no aportan costo (decisión R2)"
)

# CA14: umbrales de alerta (aprobados por Ron) y etiquetas legibles
ALERT_THRESHOLD_RED = -20.0
ALERT_THRESHOLD_YELLOW = -10.0
ALERT_METRICS = ("sales_total", "orders_count", "avg_ticket", "delivery_pct")
ALERT_LABELS = {
    "sales_total": "Ventas",
    "orders_count": "Pedidos",
    "avg_ticket": "Ticket promedio",
    "delivery_pct": "% delivery",
}

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


def _pct(current: float, previous: float) -> float | None:
    """((current − previous) / previous) × 100, 1 decimal; null si previous=0."""
    if not previous:
        return None
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def _resolve_dates(date_from: str | None, date_to: str | None) -> tuple[date, date]:
    """Resuelve el rango: default = últimos 30 días (incluye hoy)."""
    to = _parse_date(date_to) or _today()
    frm = _parse_date(date_from)
    if frm is None:
        frm = to - timedelta(days=29)
    if frm > to:
        raise ValueError("date_from no puede ser mayor que date_to")
    return frm, to


async def _period_summary(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """Resumen de período (CA12): sales_total, orders_count, avg_ticket, delivery_pct.

    Mismas fórmulas que _kpis (sin anuladas) pero sin los KPIs "en vivo" —
    usado por la comparativa y por alertas.
    """
    row = (await db.execute(
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
    )).one()
    sales_total = _money(row[0])
    orders_count = int(row[1] or 0)

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
    orders_delivery = sum(int(n or 0) for c, n in canales if c == "delivery")
    return {
        "sales_total": sales_total,
        "orders_count": orders_count,
        "avg_ticket": _money(sales_total / orders_count) if orders_count else 0.0,
        "delivery_pct": round(orders_delivery / orders_count * 100, 1) if orders_count else 0.0,
    }


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
            horas[h]["dine_in"] = _money(horas[h]["dine_in"] + float(total))
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


# ─── Bloques V2 (Spec 04 §3.1-V2: CA10-CA14) ──────────────────

async def _heatmap(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """CA10 — Ventas (S/) por hora × día de semana, separadas por canal.

    Canales: dine_in y delivery; takeout suma a dine_in (convención V1 de
    _sales_by_hour). Rows completos 24×7 por canal, celdas sin ventas en 0.
    Excluye ventas anuladas (is_voided=True).
    """
    rows = (await db.execute(
        select(
            func.extract("hour", Sale.sale_time).label("hora"),
            func.extract("isodow", Sale.sale_date).label("dia"),
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
        .group_by("hora", "dia", RestaurantSale.order_type)
    )).all()

    dine_in: dict[tuple[int, int], float] = {}
    delivery: dict[tuple[int, int], float] = {}
    for hora, dia, canal, total in rows:
        key = (int(hora or 0), int(dia or 0))
        if canal == "delivery":
            delivery[key] = _money(delivery.get(key, 0.0) + float(total))
        else:  # dine_in y takeout suman al salón
            dine_in[key] = _money(dine_in.get(key, 0.0) + float(total))

    def _rows(grid: dict[tuple[int, int], float]) -> list[dict]:
        # Orden: hora 0-23 (mayor), weekday 1-7 (menor) — filas completas con 0
        return [
            {"hour": h, "weekday": d, "total": _money(grid.get((h, d), 0.0))}
            for h in range(24)
            for d in range(1, 8)
        ]

    return {"dine_in": {"rows": _rows(dine_in)}, "delivery": {"rows": _rows(delivery)}}


async def _margins_by_channel(
    db: AsyncSession, tenant_id: int, frm: date, to: date, channels: dict,
) -> dict:
    """CA11 — Margen por canal con costeo vía recetas (reuso de recipe_explosion).

    Costo = Σ (cantidad vendida × Σ ingrediente.quantity × average_cost), la
    misma fórmula de explosión de recipe_explosion, en agregación SQL de solo
    lectura. Los sale_items sin receta (sin menu_item_id, plato sin receta o
    preparación != 'cocina') no matchean el join → no aportan costo (R2).
    """
    rows = (await db.execute(
        select(
            RestaurantSale.order_type,
            func.coalesce(
                func.sum(
                    SaleItem.quantity * RecipeIngredient.quantity * Product.average_cost
                ),
                0,
            ),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(RestaurantSale, RestaurantSale.sale_id == Sale.id)
        .join(MenuItem, MenuItem.id == SaleItem.menu_item_id)
        .join(Recipe, Recipe.menu_item_id == MenuItem.id)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .join(Product, Product.id == RecipeIngredient.product_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(RestaurantSale.order_type)
    )).all()
    cost_by_channel = {c: _money(v) for c, v in rows}

    by_channel = []
    for canal in ("dine_in", "takeout", "delivery"):
        revenue = _money(channels.get(canal, 0.0))
        cost = cost_by_channel.get(canal, 0.0)
        if revenue == 0:
            by_channel.append({"channel": canal, "revenue": 0.0, "cost": 0.0, "margin_pct": 0.0})
        else:
            by_channel.append({
                "channel": canal,
                "revenue": revenue,
                "cost": cost,
                "margin_pct": round((revenue - cost) / revenue * 100, 1),
            })
    return {"by_channel": by_channel, "costable_note": COSTABLE_NOTE}


async def _comparison(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """CA12 — Comparativa período actual vs previo de igual longitud."""
    current = await _period_summary(db, tenant_id, frm, to)
    length = (to - frm).days + 1
    prev_to = frm - timedelta(days=1)
    prev_frm = prev_to - timedelta(days=length - 1)
    previous = await _period_summary(db, tenant_id, prev_frm, prev_to)
    return {
        "current": current,
        "previous": previous,
        "deltas": {
            "sales_total_pct": _pct(current["sales_total"], previous["sales_total"]),
            "orders_count_pct": _pct(current["orders_count"], previous["orders_count"]),
            "avg_ticket_pct": _pct(current["avg_ticket"], previous["avg_ticket"]),
            "delivery_pct_delta": round(current["delivery_pct"] - previous["delivery_pct"], 1),
        },
    }


def _daily_metrics(daily: dict[date, dict], d: date) -> dict:
    """Métricas de un día calendario (0.0 si no hubo ventas)."""
    return daily.get(d) or {"sales_total": 0.0, "orders_count": 0, "avg_ticket": 0.0, "delivery_pct": 0.0}


def _avg_metrics(days: list[date], daily: dict[date, dict]) -> dict:
    """Promedio por día de las métricas (CA14).

    avg_ticket y delivery_pct solo promedian días con pedidos (no definidos
    en días sin ventas).
    """
    totals = [_daily_metrics(daily, d) for d in days]
    n = len(totals)
    tickets = [t["avg_ticket"] for t in totals if t["orders_count"] > 0 and t["avg_ticket"] is not None]
    pcts = [t["delivery_pct"] for t in totals if t["orders_count"] > 0 and t["delivery_pct"] is not None]
    return {
        "sales_total": _money(sum(t["sales_total"] for t in totals) / n),
        "orders_count": round(sum(t["orders_count"] for t in totals) / n, 1),
        "avg_ticket": round(sum(tickets) / len(tickets), 2) if tickets else 0.0,
        "delivery_pct": round(sum(pcts) / len(pcts), 1) if pcts else 0.0,
    }


async def _alerts(db: AsyncSession, tenant_id: int, frm: date, to: date) -> list[dict]:
    """CA14 — Alertas de desviación vs promedio de los 7 días previos.

    Compara el período actual — o el último día si date_from == date_to — contra
    el promedio de los 7 días calendario inmediatamente anteriores al inicio del
    período. Para períodos multi-día se compara el promedio diario del período
    (así la comparación es per-day vs per-day). Desviación ≤ -20% → red;
    ≤ -10% (y > -20%) → yellow. Sin desviación → [] (nunca null).
    """
    window_frm = frm - timedelta(days=7)
    # Totales diarios (suma, conteo) y conteos diarios de delivery en una sola
    # ventana [window_frm, to] para reusar la data de ambos lados.
    daily_rows = (await db.execute(
        select(
            Sale.sale_date,
            func.coalesce(func.sum(Sale.total), 0),
            func.count(Sale.id),
        )
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= window_frm,
            Sale.sale_date <= to,
        )
        .group_by(Sale.sale_date)
    )).all()
    deliv_rows = (await db.execute(
        select(Sale.sale_date, func.count(Sale.id))
        .join(RestaurantSale, RestaurantSale.sale_id == Sale.id)
        .where(
            RestaurantSale.order_type == "delivery",
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= window_frm,
            Sale.sale_date <= to,
        )
        .group_by(Sale.sale_date)
    )).all()

    daily: dict[date, dict] = {}
    for d, total, n in daily_rows:
        n = int(n or 0)
        daily[d] = {
            "sales_total": float(total or 0),
            "orders_count": n,
            "avg_ticket": _money(float(total or 0) / n) if n else 0.0,
            "delivery_pct": 0.0,
        }
    for d, n in deliv_rows:
        n = int(n or 0)
        if d in daily:
            daily[d]["delivery_pct"] = round(n / daily[d]["orders_count"] * 100, 1) if daily[d]["orders_count"] else 0.0

    period_days = [frm + timedelta(days=i) for i in range((to - frm).days + 1)]
    prev_days = [window_frm + timedelta(days=i) for i in range(7)]
    current = _avg_metrics(period_days, daily)
    baseline = _avg_metrics(prev_days, daily)

    alerts: list[dict] = []
    prefix = "Hoy" if frm == to else "Período"
    for metric in ALERT_METRICS:
        base = baseline[metric]
        if base == 0:
            continue  # sin base no hay desviación calculable
        dev = (float(current[metric]) - base) / base * 100
        if dev <= ALERT_THRESHOLD_RED:
            severity = "red"
        elif dev <= ALERT_THRESHOLD_YELLOW:
            severity = "yellow"
        else:
            continue
        alerts.append({
            "severity": severity,
            "metric": metric,
            "message": f"{prefix} {ALERT_LABELS.get(metric, metric)} {round(dev)}% vs promedio últimos 7 días",
        })
    return alerts


# ─── Iteración 3 (Spec 04 §3.2-V2: CA-M1..M4) ─────────────────

def _shift_of(t: time) -> str:
    """CA-M3: turno según hora (D-M1). morning 06-11:59, afternoon 12-17:59, evening 18-23:59."""
    if t is None:
        return "morning"
    if t.hour < 12:
        return "morning"
    if t.hour < 18:
        return "afternoon"
    return "evening"


async def _top_waiters(db: AsyncSession, tenant_id: int, frm: date, to: date, limit: int = 5) -> dict:
    """CA-M1 — Top N meseros por ventas (sin anuladas). sales.user_id → users.full_name."""
    rows = (await db.execute(
        select(Sale.user_id, User.full_name,
               func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
        .join(User, User.id == Sale.user_id)
        .where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
        .group_by(Sale.user_id, User.full_name)
        .order_by(func.sum(Sale.total).desc())
        .limit(limit)
    )).all()
    out = []
    for uid, name, cnt, total in rows:
        out.append({
            "user_id": uid, "name": name,
            "sales_count": cnt, "total": _money(total),
            "avg_ticket": round(float(total) / cnt, 2) if cnt else 0.0,
        })
    # total_sales = ventas sin anuladas del rango (contexto)
    total_sales = (await db.execute(
        select(func.count(Sale.id)).where(
            Sale.tenant_id == tenant_id,
            Sale.is_voided.is_(False),
            Sale.sale_date >= frm,
            Sale.sale_date <= to,
        )
    )).scalar() or 0
    return {"rows": out, "total_sales": total_sales}


async def _cancellation_rate(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """CA-M2 — % anuladas + top motivos."""
    voided = (await db.execute(
        select(func.count(Sale.id)).where(
            Sale.tenant_id == tenant_id, Sale.is_voided.is_(True),
            Sale.sale_date >= frm, Sale.sale_date <= to,
        )
    )).scalar() or 0
    total = (await db.execute(
        select(func.count(Sale.id)).where(
            Sale.tenant_id == tenant_id,
            Sale.sale_date >= frm, Sale.sale_date <= to,
        )
    )).scalar() or 0
    rate = round(voided / total * 100, 1) if total else 0.0
    reasons = (await db.execute(
        select(func.coalesce(Sale.void_reason, "(sin motivo)"), func.count(Sale.id))
        .where(
            Sale.tenant_id == tenant_id, Sale.is_voided.is_(True),
            Sale.sale_date >= frm, Sale.sale_date <= to,
        )
        .group_by(Sale.void_reason)
        .order_by(func.count(Sale.id).desc())
        .limit(5)
    )).all()
    return {
        "voided_count": voided, "total_count": total, "rate_pct": rate,
        "top_reasons": [{"reason": r, "count": c} for r, c in reasons],
    }


async def _avg_ticket_by(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """CA-M3 — Ticket promedio por canal (dine_in incluye takeout) y por turno."""
    ch_rows = (await db.execute(
        select(RestaurantSale.order_type,
               func.coalesce(func.avg(Sale.total), 0), func.count(Sale.id))
        .join(Sale, Sale.id == RestaurantSale.sale_id)
        .where(
            Sale.tenant_id == tenant_id, Sale.is_voided.is_(False),
            Sale.sale_date >= frm, Sale.sale_date <= to,
        )
        .group_by(RestaurantSale.order_type)
    )).all()
    ch_map = {ot: (round(float(avg), 2), cnt) for ot, avg, cnt in ch_rows}
    dine = ch_map.get("dine_in", (0.0, 0))
    takeout = ch_map.get("takeout", (0.0, 0))
    combined_cnt = dine[1] + takeout[1]
    combined_avg = (
        round((dine[0] * dine[1] + takeout[0] * takeout[1]) / combined_cnt, 2)
        if combined_cnt else 0.0
    )
    channel = [
        {"channel": "dine_in", "ticket": combined_avg},
        {"channel": "delivery", "ticket": ch_map.get("delivery", (0.0, 0))[0]},
    ]
    sh_rows = (await db.execute(
        select(Sale.sale_time, Sale.total)
        .where(
            Sale.tenant_id == tenant_id, Sale.is_voided.is_(False),
            Sale.sale_date >= frm, Sale.sale_date <= to,
        )
    )).all()
    agg = {"morning": [0, 0.0], "afternoon": [0, 0.0], "evening": [0, 0.0]}
    for t, total in sh_rows:
        s = _shift_of(t)
        agg[s][0] += 1
        agg[s][1] += float(total)
    shift = [
        {"shift": k, "ticket": round(v[1] / v[0], 2) if v[0] else 0.0, "orders": v[0]}
        for k, v in agg.items()
    ]
    return {"channel": channel, "shift": shift}


async def _delivery_campaign_effect(db: AsyncSession, tenant_id: int, frm: date, to: date) -> dict:
    """CA-M4 — Delivery: campaña vs sin campaña (by_campaign + by_channel utm.source). Solo no-cancelados."""
    dmin, dmax = datetime.combine(frm, time.min), datetime.combine(to, time.max)
    rows = (await db.execute(
        select(DeliveryOrder.campaign_id, DeliveryOrder.utm, Sale.total)
        .join(Sale, Sale.id == DeliveryOrder.sale_id)
        .where(
            DeliveryOrder.tenant_id == tenant_id,
            DeliveryOrder.status != "cancelled",
            DeliveryOrder.created_at >= dmin,
            DeliveryOrder.created_at <= dmax,
        )
    )).all()
    camp_names = {}
    camp_ids = {r[0] for r in rows if r[0] is not None}
    if camp_ids:
        crows = (await db.execute(
            select(MarketingCampaign.id, MarketingCampaign.name).where(MarketingCampaign.id.in_(camp_ids))
        )).all()
        camp_names = {cid: name for cid, name in crows}
    by_camp: dict = {}
    by_ch: dict = {}
    for cid, utm, total in rows:
        g = float(total or 0)
        key = cid if cid is not None else None
        if key not in by_camp:
            by_camp[key] = [0, 0.0]
        by_camp[key][0] += 1
        by_camp[key][1] += g
        src = (utm or {}).get("source") or "directo"
        if src not in by_ch:
            by_ch[src] = [0, 0.0]
        by_ch[src][0] += 1
        by_ch[src][1] += g
    by_campaign = [
        {
            "campaign_id": k,
            "campaign_name": camp_names.get(k, "Sin campaña") if k is not None else "Sin campaña",
            "orders": v[0], "gmv": _money(v[1]),
            "aov": round(v[1] / v[0], 2) if v[0] else 0.0,
        }
        for k, v in sorted(by_camp.items(), key=lambda kv: kv[1][1], reverse=True)
    ]
    by_channel = [
        {"source": k, "orders": v[0], "gmv": _money(v[1]),
         "aov": round(v[1] / v[0], 2) if v[0] else 0.0}
        for k, v in sorted(by_ch.items(), key=lambda kv: kv[1][1], reverse=True)
    ]
    return {"by_campaign": by_campaign, "by_channel": by_channel}


# ─── Export CSV (CA13) ─────────────────────────────────────────

CSV_SECTIONS = (
    "kpis",
    "sales_by_hour",
    "sales_by_weekday",
    "channels",
    "top_platos",
    "payments",
    "delivery_funnel",
    "delivery_zones",
    "campaigns",
    "comparison",
    "margins",
    "alerts",
)


def render_owner_csv(data: dict) -> str:
    """CA13 — CSV plano con secciones `# <bloque>` (UTF-8, stdlib csv)."""
    out = io.StringIO()
    w = csv.writer(out)

    def section(name: str) -> None:
        w.writerow([f"# {name}"])

    section("kpis")
    w.writerow(["metric", "value"])
    for k, v in data["kpis"].items():
        w.writerow([k, v])

    section("sales_by_hour")
    w.writerow(["hour", "dine_in", "delivery"])
    for r in data["sales_by_hour"]:
        w.writerow([r["hour"], r["dine_in"], r["delivery"]])

    section("sales_by_weekday")
    w.writerow(["weekday", "total"])
    for r in data["sales_by_weekday"]:
        w.writerow([r["weekday"], r["total"]])

    section("channels")
    w.writerow(["channel", "total"])
    for c, t in data["channels"].items():
        w.writerow([c, t])

    section("top_platos")
    w.writerow(["name", "qty", "total"])
    for r in data["top_platos"]:
        w.writerow([r["name"], r["qty"], r["total"]])

    section("payments")
    w.writerow(["method", "amount"])
    for m, a in data["payments"].items():
        w.writerow([m, a])

    section("delivery_funnel")
    w.writerow(["status", "orders"])
    for s, n in data["delivery"]["funnel"].items():
        w.writerow([s, n])

    section("delivery_zones")
    w.writerow(["zone", "orders"])
    for r in data["delivery"]["orders_by_zone"]:
        w.writerow([r["zone"], r["orders"]])

    section("campaigns")
    w.writerow(["campaign_id", "name", "channel", "spend", "orders", "gmv", "aov", "roas"])
    for c in data["campaigns"]:
        w.writerow([c.get(k, "") for k in ("campaign_id", "name", "channel", "spend", "orders", "gmv", "aov", "roas")])

    section("comparison")
    w.writerow(["metric", "current", "previous", "delta"])
    comp = data["comparison"]
    for metric in ("sales_total", "orders_count", "avg_ticket", "delivery_pct"):
        delta = comp["deltas"]["delivery_pct_delta"] if metric == "delivery_pct" else comp["deltas"][f"{metric}_pct"]
        w.writerow([metric, comp["current"][metric], comp["previous"][metric], delta])

    section("margins")
    w.writerow(["channel", "revenue", "cost", "margin_pct"])
    for r in data["margins"]["by_channel"]:
        w.writerow([r["channel"], r["revenue"], r["cost"], r["margin_pct"]])
    w.writerow([f"# costable_note: {data['margins']['costable_note']}"])

    section("alerts")
    w.writerow(["severity", "metric", "message"])
    for r in data["alerts"]:
        w.writerow([r["severity"], r["metric"], r["message"]])

    return out.getvalue()


# ─── Export PDF (CA13-b) ───────────────────────────────────────

# Fuente para los símbolos ▲▼⚠ (las 14 fuentes estándar de PDF no los
# incluyen). Se intenta registrar DejaVuSans (presente en la mayoría de
# distros); si no está disponible se usa un fallback ASCII legible
# (+, -, !) — la generación nunca falla por falta de fuente.
_DEJAVU_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/local/share/fonts/dejavu/DejaVuSans.ttf",
)


def _register_pdf_symbol_font() -> str | None:
    """Registra DejaVuSans (▲▼⚠) si existe en el sistema; None si no."""
    for path in _DEJAVU_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                return "DejaVuSans"
            except Exception:
                continue
    return None


_PDF_SYMBOL_FONT = _register_pdf_symbol_font()
if _PDF_SYMBOL_FONT:
    _SYM_UP = f'<font name="{_PDF_SYMBOL_FONT}">▲</font>'
    _SYM_DOWN = f'<font name="{_PDF_SYMBOL_FONT}">▼</font>'
    _SYM_WARN = f'<font name="{_PDF_SYMBOL_FONT}">⚠</font>'
else:
    # Fallback ASCII: el signo (+/-) ya comunica la dirección
    _SYM_UP = ""
    _SYM_DOWN = ""
    _SYM_WARN = "!"

_PDF_CHANNEL_LABELS = {
    "dine_in": "Salón", "takeout": "Para llevar", "delivery": "Delivery",
}
_PDF_CHANNEL_ORDER = ("dine_in", "takeout", "delivery")
_PDF_PAYMENT_LABELS = {
    "yape": "Yape", "plin": "Plin", "cash": "Efectivo",
    "card": "Tarjeta", "transfer": "Transferencia",
}
_PDF_FUNNEL_LABELS = {
    "received": "Recibidos", "preparing": "Preparando", "ready": "Listos",
    "out_for_delivery": "En ruta", "delivered": "Entregados", "cancelled": "Cancelados",
}
_PDF_FUNNEL_ORDER = (
    "received", "preparing", "ready", "out_for_delivery", "delivered", "cancelled",
)
_PDF_SEVERITY_LABELS = {"red": "Roja", "yellow": "Ámbar"}

_pdf_base = getSampleStyleSheet()
PDF_H1 = ParagraphStyle(
    "PDFH1", parent=_pdf_base["Title"], fontSize=15, leading=18,
    spaceAfter=3, textColor=colors.HexColor("#1f3864"),
)
PDF_SUB = ParagraphStyle(
    "PDFSub", parent=_pdf_base["Normal"], fontSize=9, leading=12,
    textColor=colors.HexColor("#4a4a4a"),
)
PDF_H2 = ParagraphStyle(
    "PDFH2", parent=_pdf_base["Heading2"], fontSize=12, leading=15,
    spaceBefore=12, spaceAfter=5, textColor=colors.HexColor("#1f3864"),
)
PDF_H3 = ParagraphStyle(
    "PDFH3", parent=_pdf_base["Normal"], fontSize=9, leading=11,
    fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2,
    textColor=colors.HexColor("#333333"),
)
PDF_TD = ParagraphStyle("PDFTd", parent=_pdf_base["Normal"], fontSize=8, leading=10)
PDF_NOTE = ParagraphStyle(
    "PDFNote", parent=_pdf_base["Normal"], fontSize=8, leading=10,
    textColor=colors.HexColor("#666666"),
)
PDF_SEV_RED = ParagraphStyle(
    "PDFSevRed", parent=PDF_TD, fontName="Helvetica-Bold",
    textColor=colors.HexColor("#b00020"),
)
PDF_SEV_YELLOW = ParagraphStyle(
    "PDFSevYellow", parent=PDF_TD, fontName="Helvetica-Bold",
    textColor=colors.HexColor("#b26a00"),
)

_PDF_HEADER_BG = colors.HexColor("#1f3864")
_PDF_GRID = colors.HexColor("#b8c2d0")
_PDF_ROW_ALT = colors.HexColor("#eef2f8")


def _money_str(v) -> str:
    """S/ 1,234.50 — monetario con miles y 2 decimales."""
    return f"S/ {float(v or 0):,.2f}"


def _qty_str(v) -> str:
    """Cantidad sin decimales innecesarios (15.0 → 15; 2.4 → 2.4)."""
    try:
        return f"{float(v):g}"
    except (TypeError, ValueError):
        return str(v)


def _pdf_delta(value, unit: str = "%") -> str:
    """Celda de cambio: ▲/▼ (o signo) + valor; '—' si el delta es None."""
    if value is None:
        return "—"
    v = float(value)
    if v > 0:
        return f"{_SYM_UP} {v:+.1f} {unit}"
    if v < 0:
        return f"{_SYM_DOWN} {v:+.1f} {unit}"
    return f"• {v:+.1f} {unit}"


def _pdf_table(rows: list, widths=None, right_cols=()) -> Table:
    """Tabla platypus: header con fondo, grid, filas alternadas, numeros a la derecha."""
    t = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, _PDF_GRID),
        ("BACKGROUND", (0, 0), (-1, 0), _PDF_HEADER_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(2, len(rows), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), _PDF_ROW_ALT))
    for col in right_cols:
        style.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _pdf_side_by_side(left: Table, right: Table, width: float = 88 * mm) -> Table:
    """Dos tablas lado a lado dentro de una tabla contenedora."""
    t = Table([[left, right]], colWidths=[width, width], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    return t


def render_owner_pdf(data: dict) -> bytes:
    """CA13-b — PDF del Panel del Dueño (reportlab platypus, 9 secciones).

    Recibe la misma data de get_owner_dashboard (una sola llamada, hecha por
    el router) y devuelve los bytes del PDF. pageCompression=0: streams de
    contenido sin comprimir → texto buscable en bytes y PDFs más simples.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        pageCompression=0,
        title="Panel del Dueño — El Segoviano",
        author="IaaS-RonSys",
        subject="Reporte ejecutivo del Panel del Dueño (Spec 04 CA13-b)",
    )
    story: list = []
    period = data.get("period", {})

    # 1. Encabezado
    story.append(Paragraph("Panel del Dueño — El Segoviano", PDF_H1))
    story.append(Paragraph(
        f"Período: {period.get('date_from', '—')} — {period.get('date_to', '—')}", PDF_SUB,
    ))
    story.append(Paragraph(
        f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", PDF_SUB,
    ))

    # 2. KPIs
    story.append(Paragraph("2. KPIs", PDF_H2))
    k = data.get("kpis", {})
    kpi_rows = [
        ["Métrica", "Valor"],
        ["Ventas totales", _money_str(k.get("sales_total"))],
        ["Pedidos", str(k.get("orders_count", 0))],
        ["Ticket promedio", _money_str(k.get("avg_ticket"))],
        ["% Delivery", f"{k.get('delivery_pct', 0)}%"],
        [
            "Pedidos por canal (salón / para llevar / delivery)",
            f"{k.get('orders_dine_in', 0)} / {k.get('orders_takeout', 0)} / {k.get('orders_delivery', 0)}",
        ],
        ["Cocina en vivo", str(k.get("kitchen_open", 0))],
        ["Delivery en ruta", str(k.get("delivery_in_route", 0))],
    ]
    story.append(_pdf_table(kpi_rows, widths=[100 * mm, 80 * mm], right_cols=(1,)))

    # 3. Comparativa semana vs semana
    story.append(Paragraph("3. Comparativa semana vs semana", PDF_H2))
    comp = data.get("comparison", {})
    cur_ = comp.get("current", {})
    prev_ = comp.get("previous", {})
    deltas = comp.get("deltas", {})
    comp_rows = [
        ["Métrica", "Período actual", "Período previo", "Cambio"],
        [
            "Ventas", _money_str(cur_.get("sales_total")), _money_str(prev_.get("sales_total")),
            Paragraph(_pdf_delta(deltas.get("sales_total_pct")), PDF_TD),
        ],
        [
            "Pedidos", str(cur_.get("orders_count", 0)), str(prev_.get("orders_count", 0)),
            Paragraph(_pdf_delta(deltas.get("orders_count_pct")), PDF_TD),
        ],
        [
            "Ticket promedio", _money_str(cur_.get("avg_ticket")), _money_str(prev_.get("avg_ticket")),
            Paragraph(_pdf_delta(deltas.get("avg_ticket_pct")), PDF_TD),
        ],
        [
            "% Delivery", f"{cur_.get('delivery_pct', 0)}%", f"{prev_.get('delivery_pct', 0)}%",
            Paragraph(_pdf_delta(deltas.get("delivery_pct_delta"), unit="pts"), PDF_TD),
        ],
    ]
    story.append(_pdf_table(
        comp_rows, widths=[45 * mm, 42 * mm, 42 * mm, 51 * mm], right_cols=(1, 2),
    ))

    # 4. Márgenes por canal
    story.append(Paragraph("4. Márgenes por canal", PDF_H2))
    margins = data.get("margins", {})
    m_rows = [["Canal", "Ingresos", "Costo", "Margen"]]
    for m in margins.get("by_channel", []):
        m_rows.append([
            _PDF_CHANNEL_LABELS.get(m.get("channel"), str(m.get("channel", ""))),
            _money_str(m.get("revenue")),
            _money_str(m.get("cost")),
            f"{m.get('margin_pct', 0)}%",
        ])
    if len(m_rows) == 1:
        m_rows.append(["—", "Sin datos en el período", "", ""])
    story.append(_pdf_table(m_rows, widths=[60 * mm, 40 * mm, 40 * mm, 40 * mm], right_cols=(1, 2, 3)))
    costable_note = margins.get("costable_note")
    if costable_note:
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"Nota: {costable_note}", PDF_NOTE))

    # 5. Top platos (top 10 por total)
    story.append(Paragraph("5. Top platos", PDF_H2))
    t_rows = [["#", "Plato", "Cantidad", "Total"]]
    for i, p in enumerate(data.get("top_platos", []), start=1):
        t_rows.append([
            str(i), p.get("name", ""), _qty_str(p.get("qty")), _money_str(p.get("total")),
        ])
    if len(t_rows) == 1:
        t_rows.append(["—", "Sin datos en el período", "", ""])
    story.append(_pdf_table(t_rows, widths=[10 * mm, 100 * mm, 30 * mm, 40 * mm], right_cols=(2, 3)))

    # 6. Canales + Pagos
    story.append(Paragraph("6. Canales y pagos", PDF_H2))
    channels = data.get("channels", {})
    chan_rows = [["Canal", "Ventas"]]
    for c in _PDF_CHANNEL_ORDER:
        if c in channels:
            chan_rows.append([_PDF_CHANNEL_LABELS[c], _money_str(channels[c])])
    if len(chan_rows) == 1:
        chan_rows.append(["—", "Sin datos en el período"])
    payments = data.get("payments", {})
    pay_rows = [["Método de pago", "Monto"]]
    for m, a in payments.items():
        pay_rows.append([_PDF_PAYMENT_LABELS.get(m, str(m)), _money_str(a)])
    if len(pay_rows) == 1:
        pay_rows.append(["—", "Sin datos en el período"])
    story.append(_pdf_side_by_side(
        _pdf_table(chan_rows, widths=[55 * mm, 33 * mm], right_cols=(1,)),
        _pdf_table(pay_rows, widths=[55 * mm, 33 * mm], right_cols=(1,)),
    ))

    # 7. Ventas por hora (0-23, salón vs delivery)
    story.append(Paragraph("7. Ventas por hora", PDF_H2))
    h_rows = [["Hora", "Salón (S/)", "Delivery (S/)"]]
    for r in data.get("sales_by_hour", []):
        h_rows.append([
            f"{r.get('hour', '')}:00", _money_str(r.get("dine_in")), _money_str(r.get("delivery")),
        ])
    if len(h_rows) == 1:
        h_rows.append(["—", "Sin datos en el período", ""])
    story.append(_pdf_table(h_rows, widths=[60 * mm, 60 * mm, 60 * mm], right_cols=(1, 2)))

    # 8. Delivery + Campañas
    story.append(Paragraph("8. Delivery y campañas", PDF_H2))
    delivery = data.get("delivery", {})
    gmv_txt = (
        f"GMV (entregados): {_money_str(delivery.get('gmv'))} · "
        f"Fees: {_money_str(delivery.get('fee_total'))}"
    )
    if delivery.get("avg_delivery_min") is not None:
        gmv_txt += f" · Tiempo promedio: {delivery.get('avg_delivery_min')} min"
    story.append(Paragraph(gmv_txt, PDF_TD))
    story.append(Spacer(1, 4))
    z_rows = [["Zona", "Pedidos"]]
    for z in delivery.get("orders_by_zone", []):
        z_rows.append([z.get("zone", ""), str(z.get("orders", 0))])
    if len(z_rows) == 1:
        z_rows.append(["—", "Sin datos en el período"])
    funnel = delivery.get("funnel", {})
    f_rows = [["Etapa", "Pedidos"]]
    for st in _PDF_FUNNEL_ORDER:
        f_rows.append([_PDF_FUNNEL_LABELS[st], str(funnel.get(st, 0))])
    story.append(Paragraph("Pedidos por zona", PDF_H3))
    story.append(_pdf_table(z_rows, widths=[60 * mm, 120 * mm], right_cols=(1,)))
    story.append(Paragraph("Embudo delivery", PDF_H3))
    story.append(_pdf_table(f_rows, widths=[60 * mm, 120 * mm], right_cols=(1,)))
    story.append(Paragraph("Campañas (ROAS)", PDF_H3))
    camp_rows = [["Campaña", "Canal", "Inversión", "Pedidos", "GMV", "ROAS"]]
    for c in data.get("campaigns", []):
        camp_rows.append([
            c.get("name") or f"#{c.get('campaign_id', '')}",
            c.get("channel", ""),
            _money_str(c.get("spend")),
            str(c.get("orders", 0)),
            _money_str(c.get("gmv")),
            _qty_str(c.get("roas")),
        ])
    if len(camp_rows) == 1:
        camp_rows.append(["—", "Sin campañas en el período", "", "", "", ""])
    story.append(_pdf_table(
        camp_rows, widths=[50 * mm, 22 * mm, 27 * mm, 22 * mm, 35 * mm, 24 * mm],
        right_cols=(2, 3, 4, 5),
    ))

    # 9. Alertas
    story.append(Paragraph("9. Alertas", PDF_H2))
    alerts = data.get("alerts", [])
    if not alerts:
        story.append(Paragraph("Sin alertas en el período", PDF_NOTE))
    else:
        a_rows = [["Severidad", "Métrica", "Mensaje"]]
        for a in alerts:
            sev = str(a.get("severity", ""))
            label = _PDF_SEVERITY_LABELS.get(sev, sev)
            cell_style = PDF_SEV_RED if sev == "red" else (PDF_SEV_YELLOW if sev == "yellow" else PDF_TD)
            a_rows.append([
                Paragraph(f"{_SYM_WARN} {label}", cell_style),
                a.get("metric", ""),
                a.get("message", ""),
            ])
        story.append(_pdf_table(a_rows, widths=[28 * mm, 32 * mm, 120 * mm]))

    doc.build(story)
    return buf.getvalue()


# ─── Orquestador ──────────────────────────────────────────────

async def get_owner_dashboard(
    db: AsyncSession, tenant_id: int,
    date_from: str | None = None, date_to: str | None = None,
) -> dict:
    """Resumen ejecutivo completo del dueño (Spec 04 §3.1 + §3.1-V2)."""
    frm, to = _resolve_dates(date_from, date_to)
    # Orden de ejecución de queries preservado de V1 (los mocks de tests
    # dependen del orden); los bloques V2 se anexan al final.
    kpis = await _kpis(db, tenant_id, frm, to)
    sales_by_hour = await _sales_by_hour(db, tenant_id, frm, to)
    sales_by_weekday = await _sales_by_weekday(db, tenant_id, frm, to)
    channels = await _channels(db, tenant_id, frm, to)
    top_platos = await _top_platos(db, tenant_id, frm, to)
    payments = await _payments(db, tenant_id, frm, to)
    delivery = await _delivery_block(db, tenant_id, frm, to)
    campaigns = await _campaigns(db, tenant_id, frm, to)
    # V2 (CA10-CA14)
    heatmap = await _heatmap(db, tenant_id, frm, to)
    margins = await _margins_by_channel(db, tenant_id, frm, to, channels)
    comparison = await _comparison(db, tenant_id, frm, to)
    alerts = await _alerts(db, tenant_id, frm, to)
    return {
        "period": {"date_from": frm.isoformat(), "date_to": to.isoformat()},
        "kpis": kpis,
        "sales_by_hour": sales_by_hour,
        "sales_by_weekday": sales_by_weekday,
        "channels": channels,
        "top_platos": top_platos,
        "payments": payments,
        "delivery": delivery,
        "campaigns": campaigns,
        "heatmap": heatmap,
        "margins": margins,
        "comparison": comparison,
        "alerts": alerts,
    }
