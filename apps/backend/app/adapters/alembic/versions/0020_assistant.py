"""Spec 08 (F5 — "Pregúntale al Sistema", NL2SQL controlado, §3.2): catálogo + auditoría.

F5 = asistente conversacional de negocio en el Panel del Dueño (`/panel`).
El LLM NUNCA escribe SQL (D1): solo elige `query_catalog.id` y llena `params`
tipados; el motor ejecuta el `sql_template` con parámetros vinculados.

Esta migración:

1) Tabla `query_catalog` — catálogo SEGURO de consultas (único lugar donde
   existe SQL en todo el flujo):
     - skill           varchar(50)   — 'delivery' (MVP, D4); luego
       sales|inventory|finance|report (replicables sin cambiar contrato).
     - name            varchar(100)  — slug interno UNIQUE:
       'top_products_delivery', 'sales_by_zone', 'campaign_roas', ...
     - description_es  text          — para el LLM (tool description) y dueño.
     - sql_template    text          — SELECT parametrizado con :params
       (SOLO lectura, R7). Guarda obligatoria `sale_date = CURRENT_DATE`
       cuando el rango es opcional (hallazgo del spike 2026-08-13).
     - params          jsonb         — [{name, type: 'date'|'int'|'enum',
       required, description_es, allowed_values?}] (CHECK array).
     - allowed_roles   jsonb         — default ["admin","manager","viewer"] (R8).
     - tenant_scope    bool          — true: :tenant_id inyectado por el motor
       (R2), nunca por el LLM.
     - active          bool          — catálogo apagable sin tocar código.

2) Tabla `query_logs` — auditoría total (R4):
     - tenant_id       FK companies  ON DELETE CASCADE (R8 aislamiento).
     - user_id         FK users      ON DELETE SET NULL.
     - pregunta        text          — texto crudo del dueño (auditoría).
     - query_catalog_id FK query_catalog ON DELETE SET NULL (null = rechazado).
     - params          jsonb         — params finales ejecutados.
     - result_summary  jsonb         — {rows:int, total?:float} resumen,
       NUNCA data completa (evita duplicar datos sensibles en logs).
     - tokens_used / latency_ms      — consumo LLM y tiempo end-to-end.
     - rejected        bool          — true si no matcheó catálogo (R5).
     - created_at + índice (tenant_id, created_at DESC).

Reglas (Spec 08 §3.5): R1 solo catálogo · R2 tenant scope siempre ·
R3 sin cache · R4 auditoría · R5 fallback "no entendí" · R7 solo lectura ·
R8 roles por consulta · R9 fechas `_resolve_dates` (default 30 días).

Seed del catálogo MVP (D4 — solo delivery): 10 consultas (§3.4) que
delegan en `delivery_service.py`/`owner_dashboard_service.py` (misma
fórmula, cero divergencia) o en `sql_template` equivalente (las 2 sin
función delegable: top_products_delivery y comparison_week — replican
exactamente el filtrado de `_top_platos`/`_comparison`).

Revision ID: 0020_assistant
Revises: 0019_voice_ai
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0020_assistant"
down_revision: Union[str, Sequence[str], None] = "0019_voice_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════════
# Catálogo MVP (Spec 08 §3.4) — 10 consultas delivery
# ═══════════════════════════════════════════════════════════════════

CATALOG_SEED: list[dict] = [
    {
        "skill": "delivery",
        "name": "top_products_delivery",
        "description_es": (
            "Producto(s) más vendido(s) por delivery en un rango de fechas. "
            "Responde '¿cuál es el producto más vendido por delivery?', "
            "'¿qué plato se pidió más a domicilio?'"
        ),
        # Sin función delegable (architecture-agent): _top_platos no filtra
        # order_type → sql_template replica su fórmula + filtro canal delivery.
        "sql_template": """
            SELECT si.item_name AS name,
                   COALESCE(SUM(si.quantity), 0) AS qty,
                   COALESCE(SUM(si.total), 0) AS total
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN restaurant_sales rs ON rs.sale_id = s.id
            WHERE s.tenant_id = :tenant_id
              AND s.is_voided = false
              AND rs.order_type = 'delivery'
              AND s.sale_date >= :date_from
              AND s.sale_date <= :date_to
            GROUP BY si.item_name
            ORDER BY SUM(si.quantity) DESC, SUM(si.total) DESC
            LIMIT :limit
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD). Default: hace 30 días."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD). Default: hoy."},
            {"name": "limit", "type": "int", "required": False,
             "description_es": "Cantidad de productos a listar (default 5)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "sales_by_zone",
        "description_es": (
            "Ventas/pedidos por zona de delivery en un rango de fechas. "
            "Responde '¿cuánto vendió la Zona 1?', 'pedidos por distrito'."
        ),
        # Delegable: _delivery_block.orders_by_zone (solo conteo; SQL
        # equivalente con mismo join/WHERE).
        "sql_template": """
            SELECT dz.name AS zone, COUNT(dlv.id) AS orders
            FROM delivery_zones dz
            JOIN delivery_orders dlv ON dlv.zone_id = dz.id
            WHERE dlv.tenant_id = :tenant_id
              AND dlv.created_at >= CAST(:date_from AS timestamp)
              AND dlv.created_at <= CAST(:date_to AS timestamp) + interval '1 day'
            GROUP BY dz.name
            ORDER BY COUNT(dlv.id) DESC
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "campaign_roas",
        "description_es": (
            "ROAS, AOV, GMV e inversión por campaña de marketing en un rango "
            "de fechas (canal opcional: meta|google|tiktok|other). Responde "
            "'¿qué campaña tuvo mejor ROAS?', '¿cuánto generó cada campaña?'"
        ),
        # Delegable: metrics_campaigns (ROAS = gmv/spend, AOV = gmv/orders,
        # solo status='delivered'). SQL equivalente con LEFT JOIN.
        "sql_template": """
            SELECT c.id AS campaign_id, c.name, c.channel, c.spend,
                   COUNT(dlv.id) AS orders,
                   COALESCE(SUM(s.total), 0) AS gmv,
                   CASE WHEN COUNT(dlv.id) > 0
                        THEN COALESCE(SUM(s.total), 0) / COUNT(dlv.id) ELSE 0 END AS aov,
                   CASE WHEN c.spend > 0
                        THEN COALESCE(SUM(s.total), 0) / c.spend ELSE 0 END AS roas
            FROM marketing_campaigns c
            LEFT JOIN delivery_orders dlv
                   ON dlv.campaign_id = c.id
                  AND dlv.tenant_id = :tenant_id
                  AND dlv.status = 'delivered'
                  AND dlv.created_at >= CAST(:date_from AS timestamp)
                  AND dlv.created_at <= CAST(:date_to AS timestamp) + interval '1 day'
            LEFT JOIN sales s ON s.id = dlv.sale_id
            WHERE c.tenant_id = :tenant_id
              AND (CAST(:channel AS text) IS NULL OR c.channel = :channel)
            GROUP BY c.id, c.name, c.channel, c.spend
            ORDER BY roas DESC
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
            {"name": "channel", "type": "enum", "required": False,
             "description_es": "Canal de campaña (meta, google, tiktok, other).",
             "allowed_values": ["meta", "google", "tiktok", "other"]},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "delivery_overview",
        "description_es": (
            "Resumen delivery: pedidos entregados, GMV, fees y tiempo medio "
            "de entrega en un rango. Responde '¿cuántos pedidos de delivery "
            "hubo?', '¿cuánto vendió el delivery?'"
        ),
        # Delegable: metrics_overview (solo status='delivered' para GMV;
        # avg_delivery_min = epoch(delivered_at - received_at)).
        "sql_template": """
            SELECT COUNT(dlv.id) AS orders,
                   COALESCE(SUM(s.total), 0) AS gmv,
                   COALESCE(SUM(dlv.fee), 0) AS fee_total,
                   CASE WHEN COUNT(dlv.id) > 0
                        THEN AVG(EXTRACT(EPOCH FROM (dlv.delivered_at - dlv.received_at)) / 60)
                        ELSE NULL END AS avg_delivery_min,
                   (SELECT COUNT(*) FROM delivery_orders c
                     WHERE c.tenant_id = :tenant_id AND c.status = 'cancelled'
                       AND c.created_at >= CAST(:date_from AS timestamp)
                       AND c.created_at <= CAST(:date_to AS timestamp) + interval '1 day') AS cancelled
            FROM delivery_orders dlv
            JOIN sales s ON s.id = dlv.sale_id
            WHERE dlv.tenant_id = :tenant_id
              AND dlv.status = 'delivered'
              AND dlv.created_at >= CAST(:date_from AS timestamp)
              AND dlv.created_at <= CAST(:date_to AS timestamp) + interval '1 day'
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "orders_by_status",
        "description_es": (
            "Pedidos delivery por estado (embudo: recibido, preparando, "
            "listo, en reparto, entregado, cancelado) en un rango. Responde "
            "'¿cuántos pedidos se cancelaron?', '¿cuántos se entregaron?'"
        ),
        # Delegable: _delivery_block.funnel (conteo por status real).
        "sql_template": """
            SELECT dlv.status, COUNT(dlv.id) AS n
            FROM delivery_orders dlv
            WHERE dlv.tenant_id = :tenant_id
              AND dlv.created_at >= CAST(:date_from AS timestamp)
              AND dlv.created_at <= CAST(:date_to AS timestamp) + interval '1 day'
            GROUP BY dlv.status
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "avg_ticket_delivery",
        "description_es": (
            "Ticket promedio de delivery en un rango de fechas. Responde "
            "'¿cuál es el ticket promedio a domicilio?'"
        ),
        # Delegable: _avg_ticket_by → channel['delivery'].
        "sql_template": """
            SELECT COALESCE(AVG(s.total), 0) AS ticket, COUNT(s.id) AS orders
            FROM sales s
            JOIN restaurant_sales rs ON rs.sale_id = s.id
            WHERE s.tenant_id = :tenant_id
              AND s.is_voided = false
              AND rs.order_type = 'delivery'
              AND s.sale_date >= :date_from
              AND s.sale_date <= :date_to
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "sales_by_hour_delivery",
        "description_es": (
            "Ventas delivery por hora del día (0-23) en un rango. Responde "
            "'¿a qué hora se vende más delivery?'"
        ),
        # Delegable: _sales_by_hour → columna 'delivery' por hora.
        "sql_template": """
            SELECT EXTRACT(HOUR FROM s.sale_time)::int AS hour,
                   COALESCE(SUM(s.total), 0) AS total
            FROM sales s
            JOIN restaurant_sales rs ON rs.sale_id = s.id
            WHERE s.tenant_id = :tenant_id
              AND s.is_voided = false
              AND rs.order_type = 'delivery'
              AND s.sale_date >= :date_from
              AND s.sale_date <= :date_to
            GROUP BY EXTRACT(HOUR FROM s.sale_time)
            ORDER BY hour
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "comparison_week",
        "description_es": (
            "Comparativa delivery vs período anterior de igual longitud: "
            "ventas, pedidos, ticket promedio y % de delivery. Responde "
            "'¿cómo fue esta semana vs la anterior?', '¿subieron las ventas?'"
        ),
        # Sin función delegable 1:1: _comparison compara totales (no solo
        # delivery). El sql_template replica la fórmula con filtro delivery.
        "sql_template": """
            WITH current_p AS (
              SELECT COALESCE(SUM(s.total), 0) AS sales_total,
                     COUNT(s.id) AS orders
              FROM sales s
              JOIN restaurant_sales rs ON rs.sale_id = s.id
              WHERE s.tenant_id = :tenant_id
                AND s.is_voided = false
                AND rs.order_type = 'delivery'
                AND s.sale_date >= :date_from
                AND s.sale_date <= :date_to
            ), previous_p AS (
              SELECT COALESCE(SUM(s.total), 0) AS sales_total,
                     COUNT(s.id) AS orders
              FROM sales s
              JOIN restaurant_sales rs ON rs.sale_id = s.id
              WHERE s.tenant_id = :tenant_id
                AND s.is_voided = false
                AND rs.order_type = 'delivery'
                AND s.sale_date >= (CAST(:date_from AS date) - ((CAST(:date_to AS date) - CAST(:date_from AS date)) + 1))
                AND s.sale_date < :date_from
            )
            SELECT c.sales_total, c.orders,
                   CASE WHEN c.orders > 0 THEN c.sales_total / c.orders ELSE 0 END AS avg_ticket,
                   p.sales_total AS prev_sales_total, p.orders AS prev_orders,
                   CASE WHEN p.orders > 0 THEN p.sales_total / p.orders ELSE 0 END AS prev_avg_ticket,
                   CASE WHEN p.sales_total > 0
                        THEN (c.sales_total - p.sales_total) / p.sales_total * 100
                        ELSE NULL END AS sales_total_pct,
                   CASE WHEN p.orders > 0
                        THEN (c.orders - p.orders) / p.orders * 100
                        ELSE NULL END AS orders_count_pct
            FROM current_p c, previous_p p
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial del período actual (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final del período actual (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "delivery_margins",
        "description_es": (
            "Ingresos, costo y margen % del canal delivery en un rango. "
            "Responde '¿cuál es el margen del delivery?'"
        ),
        # Delegable componiendo _channels + _margins_by_channel (canal
        # delivery; costo vía recetas: si.quantity × ri.quantity × p.average_cost).
        "sql_template": """
            SELECT COALESCE(SUM(s.total), 0) AS revenue,
                   COALESCE(SUM(si.quantity * ri.quantity * p.average_cost), 0) AS cost
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN restaurant_sales rs ON rs.sale_id = s.id
            LEFT JOIN menu_items mi ON mi.id = si.menu_item_id
            LEFT JOIN recipes r ON r.menu_item_id = mi.id
            LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            LEFT JOIN products p ON p.id = ri.product_id
            WHERE s.tenant_id = :tenant_id
              AND s.is_voided = false
              AND rs.order_type = 'delivery'
              AND s.sale_date >= :date_from
              AND s.sale_date <= :date_to
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
    {
        "skill": "delivery",
        "name": "sales_by_channel",
        "description_es": (
            "Ventas por canal (salón / para llevar / delivery) en un rango. "
            "Responde '¿cuánto vendió el salón vs delivery?'"
        ),
        # Delegable: _channels (solo SELECT, sin anuladas).
        "sql_template": """
            SELECT rs.order_type AS channel, COALESCE(SUM(s.total), 0) AS total
            FROM sales s
            JOIN restaurant_sales rs ON rs.sale_id = s.id
            WHERE s.tenant_id = :tenant_id
              AND s.is_voided = false
              AND s.sale_date >= :date_from
              AND s.sale_date <= :date_to
            GROUP BY rs.order_type
        """,
        "params": [
            {"name": "date_from", "type": "date", "required": True,
             "description_es": "Fecha inicial (YYYY-MM-DD)."},
            {"name": "date_to", "type": "date", "required": True,
             "description_es": "Fecha final (YYYY-MM-DD)."},
        ],
        "allowed_roles": ["admin", "manager", "viewer"],
        "tenant_scope": True,
        "active": True,
    },
]


def upgrade() -> None:
    # ── 1) query_catalog (catálogo seguro, R1/R7/R8) ───────────────
    op.create_table(
        "query_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description_es", sa.Text(), nullable=False),
        sa.Column("sql_template", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("allowed_roles", postgresql.JSONB(), nullable=False,
                  server_default=sa.text(
                      "'[\"admin\",\"manager\",\"viewer\"]'::jsonb")),
        sa.Column("tenant_scope", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_query_catalog_name", "query_catalog", ["name"])
    op.create_check_constraint(
        "ck_query_catalog_params_array", "query_catalog",
        "jsonb_typeof(params) = 'array'",
    )

    # ── 2) query_logs (auditoría R4) ───────────────────────────────
    op.create_table(
        "query_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("pregunta", sa.Text(), nullable=False),
        sa.Column(
            "query_catalog_id", sa.Integer(),
            sa.ForeignKey("query_catalog.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("rejected", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_query_logs_tenant_created", "query_logs",
        ["tenant_id", sa.text("created_at DESC")],
    )

    # ── 3) Seed catálogo delivery (CA-F5.12: ≥8 consultas) ─────────
    meta = sa.MetaData()
    qc = sa.table(
        "query_catalog",
        sa.column("skill", sa.String),
        sa.column("name", sa.String),
        sa.column("description_es", sa.Text),
        sa.column("sql_template", sa.Text),
        sa.column("params", postgresql.JSONB),
        sa.column("allowed_roles", postgresql.JSONB),
        sa.column("tenant_scope", sa.Boolean),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(qc, CATALOG_SEED)


def downgrade() -> None:
    op.drop_index("ix_query_logs_tenant_created", table_name="query_logs")
    op.drop_table("query_logs")
    op.drop_table("query_catalog")
