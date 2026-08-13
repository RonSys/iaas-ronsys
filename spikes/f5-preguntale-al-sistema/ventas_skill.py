"""
🧪 SPIKE F5 — "Pregúntale al Sistema" (Bloque A §9)
VentasSkill mínimo sobre el puerto hexagonal BaseSkill (deuda técnica #8).

SOLO LECTURA. Por defecto contra la BD QA (iaas_ronsys_qa, tenant 1).
Para demo read-only contra PROD: F5_DATABASE_URL=postgresql://ron:***@localhost:5432/iaas_ronsys
(todo es SELECT puro — nunca escritura).

Herramientas:
  1. ventas_del_dia        → total ventas + nº pedidos de un día (canal: delivery|restaurant)
  2. top_productos_dia     → top N productos vendidos hoy (por cantidad)
  3. ventas_por_zona_dia   → ventas + pedidos por zona de delivery hoy

Cada tool: SOLO SELECT, tenant scoped, parámetros validados.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg

# ═══════════════════════════════════════════════════════════════
# Config (QA por defecto; PROD solo para demo read-only)
# ═══════════════════════════════════════════════════════════════

DB_URL = os.environ.get(
    "F5_DATABASE_URL",
    "postgresql://ron:ron123@localhost:5432/iaas_ronsys_qa",
)


def _conn():
    return psycopg.connect(DB_URL)


# ═══════════════════════════════════════════════════════════════
# Tools (SOLO LECTURA — SELECT únicamente)
# ═══════════════════════════════════════════════════════════════


@dataclass
class Tool:
    name: str
    description: str
    params: list[dict]  # schema JSON para function calling
    run: callable


def _ventas_del_dia(tenant_id: int = 1, fecha: str | None = None, business_type: str = "delivery") -> dict:
    """Total vendido + nº de pedidos de un día y canal (por defecto hoy, delivery)."""
    fecha_clause = "AND s.sale_date = %s::date" if fecha else "AND s.sale_date = CURRENT_DATE"
    params = (tenant_id, business_type, fecha) if fecha else (tenant_id, business_type)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    COALESCE(SUM(s.total), 0)::numeric(12,2) AS total_ventas,
                    COUNT(*)::int AS num_ventas,
                    COALESCE(SUM(s.total) FILTER (WHERE d.status = 'delivered'), 0)::numeric(12,2) AS total_entregado
                FROM sales s
                LEFT JOIN delivery_orders d ON d.sale_id = s.id
                WHERE s.tenant_id = %s
                  AND s.business_type = %s
                  AND s.is_voided = false
                  {fecha_clause}
                """,
                params,
            )
            row = cur.fetchone()
    return {
        "fecha": fecha or "hoy",
        "canal": business_type,
        "total_ventas": float(row[0]),
        "num_ventas": row[1],
        "total_entregado": float(row[2]),
    }


def _top_productos_dia(tenant_id: int = 1, fecha: str | None = None, limite: int = 5, business_type: str = "delivery") -> dict:
    """Top productos más vendidos (por cantidad) en un día y canal."""
    limite = max(1, min(int(limite), 20))
    fecha_clause = "AND s.sale_date = %s::date" if fecha else "AND s.sale_date = CURRENT_DATE"
    params = (tenant_id, business_type, fecha, limite) if fecha else (tenant_id, business_type, limite)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT si.item_name,
                       SUM(si.quantity)::numeric(12,2) AS cantidad,
                       COUNT(DISTINCT s.id)::int AS n_ventas,
                       SUM(si.total)::numeric(12,2) AS total
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE s.tenant_id = %s
                  AND s.business_type = %s
                  AND s.is_voided = false
                  {fecha_clause}
                GROUP BY si.item_name
                ORDER BY cantidad DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()
    return {
        "fecha": fecha or "hoy",
        "canal": business_type,
        "top": [
            {"producto": r[0], "cantidad": float(r[1]), "ventas": r[2], "total_soles": float(r[3])}
            for r in rows
        ],
    }


def _ventas_por_zona_dia(tenant_id: int = 1, fecha: str | None = None, business_type: str = "delivery") -> dict:
    """Ventas y pedidos por zona de delivery de un día."""
    fecha_clause = "AND s.sale_date = %s::date" if fecha else "AND s.sale_date = CURRENT_DATE"
    params = (tenant_id, business_type, fecha) if fecha else (tenant_id, business_type)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT z.name,
                       COUNT(d.id)::int AS pedidos,
                       COALESCE(SUM(s.total), 0)::numeric(12,2) AS total
                FROM delivery_orders d
                JOIN sales s ON s.id = d.sale_id
                LEFT JOIN delivery_zones z ON z.id = d.zone_id
                WHERE d.tenant_id = %s
                  AND s.business_type = %s
                  AND s.is_voided = false
                  {fecha_clause}
                GROUP BY z.name
                ORDER BY total DESC
                """,
                params,
            )
            rows = cur.fetchall()
    return {
        "fecha": fecha or "hoy",
        "canal": business_type,
        "zonas": [
            {"zona": r[0] or "(sin zona)", "pedidos": r[1], "total_soles": float(r[2])}
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Registro de tools (catálogo cerrado — la IA solo elige de aquí)
# ═══════════════════════════════════════════════════════════════

TOOLS: list[Tool] = [
    Tool(
        name="ventas_del_dia",
        description=(
            "Ventas totales (en soles) y número de pedidos de un día. "
            "Úsala cuando pregunten cuánto se vendió hoy, cuántos pedidos hubo, "
            "o el total de un día específico. Canal: delivery (pedidos) o restaurant (salón)."
        ),
        params=[
            {"name": "fecha", "type": "string", "description": "Fecha ISO (YYYY-MM-DD). Vacío = hoy", "required": False},
            {"name": "business_type", "type": "string", "description": "Canal: delivery (default) o restaurant", "required": False},
            {"name": "tenant_id", "type": "integer", "description": "Tenant (default 1)", "required": False},
        ],
        run=_ventas_del_dia,
    ),
    Tool(
        name="top_productos_dia",
        description=(
            "Top productos más vendidos (por cantidad) de un día — con total en soles. "
            "Úsala cuando pregunten qué se vendió más, cuál es el plato/producto "
            "más vendido, o top productos."
        ),
        params=[
            {"name": "fecha", "type": "string", "description": "Fecha ISO (YYYY-MM-DD). Vacío = hoy", "required": False},
            {"name": "limite", "type": "integer", "description": "Nº de resultados (default 5, máx 20)", "required": False},
            {"name": "business_type", "type": "string", "description": "Canal: delivery (default) o restaurant", "required": False},
            {"name": "tenant_id", "type": "integer", "description": "Tenant (default 1)", "required": False},
        ],
        run=_top_productos_dia,
    ),
    Tool(
        name="ventas_por_zona_dia",
        description=(
            "Ventas (soles) y pedidos por zona de delivery de un día. "
            "Úsala cuando pregunten por zona, distrito, o qué zona vendió más."
        ),
        params=[
            {"name": "fecha", "type": "string", "description": "Fecha ISO (YYYY-MM-DD). Vacío = hoy", "required": False},
            {"name": "business_type", "type": "string", "description": "Canal: delivery (default) o restaurant", "required": False},
            {"name": "tenant_id", "type": "integer", "description": "Tenant (default 1)", "required": False},
        ],
        run=_ventas_por_zona_dia,
    ),
]

TOOL_BY_NAME = {t.name: t for t in TOOLS}


def run_tool(name: str, arguments: dict) -> dict:
    """Ejecuta una tool del catálogo con validación de argumentos."""
    tool = TOOL_BY_NAME.get(name)
    if not tool:
        raise ValueError(f"Tool desconocida: {name}")
    # Solo permitir keys conocidas de la tool + saneo de vacíos
    allowed = {p["name"] for p in tool.params}
    args = {k: v for k, v in (arguments or {}).items() if k in allowed}
    # Strings vacíos → None (la tool usa CURRENT_DATE en SQL)
    args = {k: (None if v == "" else v) for k, v in args.items()}
    return {"tool": name, "result": tool.run(**args)}
