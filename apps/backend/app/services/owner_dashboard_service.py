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

Solo lectura (D5). Fechas: date_from/date_to opcionales (ISO YYYY-MM-DD);
sin fechas → últimos 30 días. Excluye ventas anuladas (is_voided=True).
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Product
from app.adapters.db.models.delivery import (
    DeliveryOrder,
    DeliveryZone,
)
from app.adapters.db.models.restaurant import KitchenOrder, MenuItem, Recipe, RecipeIngredient
from app.adapters.db.models.sales import (
    RestaurantSale,
    Sale,
    SaleItem,
    SalePayment,
)
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
