"""
🤖 AssistantService — "Pregúntale al Sistema" (Spec 08 F5, §3.3.2).

Pipeline (D1 — el LLM NUNCA escribe SQL):
    question ─► 1. sanitize (límite chars)
             ─► 2. LLM tool calling: tools = catálogo activo del tenant/rol
                    → elige query_catalog_id + params (fechas ISO)
                    → sin match ⇒ R5 (rechazo amable + sugerencias)
             ─► 3. validar params contra schema (tipos, required, allowed_values,
                    rango de fechas — R9)
             ─► 4. inyectar :tenant_id (get_tenant_id) — R2
             ─► 5. ejecutar consulta (SQL parametrizado vinculado — R1/R7)
             ─► 6. formatear answer en español (template por consulta + data)
             ─► 7. escribir query_logs (R4)
             ─► 8. responder {answer, data, catalog_query_used, params}

Seguridad:
  - Catálogo cerrado: solo `query_catalog.sql_template` (R1). Params se
    vinculan con SQLAlchemy `text()` + bindparams — NUNCA interpolación.
  - Tenant scope: `:tenant_id` inyectado por el motor (R2).
  - Solo lectura: templates son SELECT (R7, CHECK en migración).
  - Sin LLM key / error LLM → fallback determinista por palabras clave
    (R5/CA-F5.8, validado en spike: 100% a 35–44ms) — nunca 500.
  - Rate limit por tenant en el router (R6).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.assistant import QueryCatalog, QueryLog
from app.config import settings
from app.schemas.assistant import AskResponse, CatalogQueryUsed

logger = logging.getLogger(__name__)

# Límite de caracteres de la pregunta (sanitize, R5/CA-F5.7)
MAX_QUESTION_CHARS = 500
# Default de rango de fechas (R9 — patrón _resolve_dates de Spec 04)
DEFAULT_RANGE_DAYS = 30
# Rate limit por tenant en /ask (R6, ajustable)
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60

# Marcadores de inyección SQL (R1/CA-F5.7): si aparecen, rechazo R5
_INJECTION_PATTERNS = (
    r"\b(drop|truncate|delete|update|insert|alter|create|grant|revoke)\b",
    r"(--|;|/\*)",
    r"\b(borra|borrar|elimina|eliminar|anula)\b",
    r"\bunion\s+select\b|\bselect\s+\*|\binformation_schema\b|\bpg_catalog\b",
)

# Fallback determinista (spike validado 100%) — palabras clave → consulta
# Orden IMPORTANTE: reglas más específicas primero ("vs" de comparativa es
# greedy → sales_by_channel va antes).
_FALLBACK_RULES: list[tuple[str, list[str]]] = [
    ("top_products_delivery", [
        "producto", "plato", "más vendido", "vendido más", "top", "qué plato",
        "más pedido", "mejor vendido", "se pidió más", "más solicitado",
    ]),
    ("campaign_roas", [
        "roas", "campaña", "campañas", "inversión", "retorno", "aov", "gmv",
    ]),
    ("sales_by_zone", [
        "zona", "distrito", "por zona", "domicilio por zona",
    ]),
    ("orders_by_status", [
        "estado", "embudo", "cancelados", "canceladas", "cancelaron",
        "entregados", "entregadas", "entregaron", "preparando", "reparto",
    ]),
    ("avg_ticket_delivery", [
        "ticket promedio", "ticket medio", "promedio de pedido",
    ]),
    ("sales_by_hour_delivery", [
        "hora", "horas", "por hora", "a qué hora",
    ]),
    ("delivery_margins", [
        "margen", "márgenes", "costo", "rentabilidad",
    ]),
    ("delivery_overview", [
        "resumen de delivery", "resumen del delivery", "cuánto vendió el delivery",
        "pedidos de delivery", "pedidos entregados", "tiempo de entrega", "fees",
        "gmv del delivery", "gmv total", "métricas generales",
    ]),
    ("sales_by_channel", [
        "canal", "canales", "salón vs delivery", "para llevar",
    ]),
    ("comparison_week", [
        "comparar", "comparativa", "semana pasada", "anterior",
        "subieron", "bajaron", "mejor que", "vs la", "vs el", "vs semana",
    ]),
]

# Resolvedores de fecha relativa (D7/R9 — normalizados a ISO por el pipeline)
# Todos reciben (now, match) — los que no usan match lo ignoran.
_RELATIVE_DATE_PATTERNS: list[tuple[re.Pattern, callable]] = [
    (re.compile(r"\b(hoy|el día de hoy)\b"), lambda now, m: (now, now)),
    (re.compile(r"\b(ayer|de ayer|día de ayer)\b"),
     lambda now, m: (now - timedelta(days=1), now - timedelta(days=1))),
    (re.compile(r"\b(esta semana|en la semana)\b"),
     lambda now, m: (now - timedelta(days=now.weekday()), now)),
    (re.compile(r"\b(la semana pasada|semana anterior|última semana)\b"),
     lambda now, m: (now - timedelta(days=now.weekday() + 7), now - timedelta(days=now.weekday() + 1))),
    (re.compile(r"\b(este mes|en el mes)\b"), lambda now, m: (now.replace(day=1), now)),
    (re.compile(r"\b(el mes pasado|mes anterior|último mes)\b"),
     lambda now, m: ((now.replace(day=1) - timedelta(days=1)).replace(day=1), now.replace(day=1) - timedelta(days=1))),
    (re.compile(r"\b(últimos?|últimas?)\s+(\d+)\s+(días?|dias?)\b"),
     lambda now, m: (now - timedelta(days=int(m.group(2)) - 1), now)),
]

# Plantillas de respuesta en español (paso 6 del pipeline, §3.3.2)
_ANSWER_TEMPLATES: dict[str, str] = {
    "top_products_delivery": (
        "🏆 Top {limit} productos más vendidos por delivery ({date_from} a {date_to}):\n"
        "{items}"
    ),
    "sales_by_zone": (
        "🗺️ Pedidos por zona de delivery ({date_from} a {date_to}):\n{items}"
    ),
    "campaign_roas": (
        "📈 ROAS por campaña ({date_from} a {date_to}):\n{items}"
    ),
    "delivery_overview": (
        "📊 Resumen delivery ({date_from} a {date_to}): {orders} pedidos entregados, "
        "GMV S/ {gmv:,.2f}, fees S/ {fee_total:,.2f}, tiempo medio {avg_delivery_min} min, "
        "{cancelled} cancelados."
    ),
    "orders_by_status": (
        "🚚 Pedidos delivery por estado ({date_from} a {date_to}):\n{items}"
    ),
    "avg_ticket_delivery": (
        "🎫 Ticket promedio de delivery ({date_from} a {date_to}): S/ {ticket:,.2f} "
        "en {orders} pedidos."
    ),
    "sales_by_hour_delivery": (
        "🕐 Ventas delivery por hora ({date_from} a {date_to}):\n{items}"
    ),
    "comparison_week": (
        "📉 Comparativa ({date_from} a {date_to}) vs período anterior: "
        "ventas {sales_total_pct:+.1f}% (S/ {sales_total:,.2f} vs S/ {prev_sales_total:,.2f}), "
        "pedidos {orders_count_pct:+.1f}% ({orders} vs {prev_orders})."
    ),
    "delivery_margins": (
        "💰 Margen delivery ({date_from} a {date_to}): ingresos S/ {revenue:,.2f}, "
        "costo S/ {cost:,.2f}, margen {margin_pct:.1f}%."
    ),
    "sales_by_channel": (
        "🏪 Ventas por canal ({date_from} a {date_to}):\n{items}"
    ),
}

_FALLBACK_SUGGESTIONS = [
    "🏆 ¿Cuál es el producto más vendido por delivery?",
    "🗺️ ¿Cuántos pedidos hubo por zona?",
    "📈 ¿Qué campaña tuvo mejor ROAS?",
    "📊 Resumen de delivery",
    "🚚 ¿Cuántos pedidos se cancelaron?",
]


# ═══════════════════════════════════════════════════════════════
# Cliente LLM (D2 — OpenAI-compatible; DeepSeek con solo config)
# ═══════════════════════════════════════════════════════════════

class LLMClient:
    """Chat completion con tools (function calling) — OpenAI/DeepSeek compatible.

    Sin key configurada → `available=False` → el pipeline usa el fallback
    determinista (R5/CA-F5.8, nunca 500).
    """

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 provider: str | None = None, timeout_s: float = 30.0):
        self.api_key = api_key or settings.llm_api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or settings.llm_model or "gpt-4o"
        self.provider = provider or settings.llm_provider or "openai"
        self.timeout_s = timeout_s
        # DeepSeek usa la misma API de OpenAI con base_url distinto
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "https://api.deepseek.com/chat/completions"
            if self.provider == "deepseek"
            else "https://api.openai.com/v1/chat/completions",
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _tools_schema(self, catalog: list[QueryCatalog]) -> list[dict]:
        """Catálogo → schema de tools para function calling (formato OpenAI)."""
        out = []
        for q in catalog:
            props: dict[str, Any] = {}
            required: list[str] = []
            for p in q.params or []:
                ptype = "string" if p.get("type") in ("date", "enum") else "integer"
                props[p["name"]] = {
                    "type": ptype,
                    "description": p.get("description_es", ""),
                }
                if p.get("type") == "enum" and p.get("allowed_values"):
                    props[p["name"]]["enum"] = p["allowed_values"]
                if p.get("required"):
                    required.append(p["name"])
            out.append({
                "type": "function",
                "function": {
                    "name": q.name,
                    "description": q.description_es,
                    "parameters": {"type": "object", "properties": props, "required": required},
                },
            })
        return out

    async def select_query(self, question: str, catalog: list[QueryCatalog]) -> dict | None:
        """
        LLM elige query_catalog.name + params vía tool calling (D1).

        Devuelve {"name": str, "params": dict} o None (sin match / error /
        sin key → el pipeline cae al fallback determinista R5).
        """
        if not self.available:
            return None

        system = (
            "Eres el asistente de datos de El Segoviano (restaurante con delivery). "
            "El usuario pregunta en lenguaje natural sobre ventas/delivery. "
            "Usa SIEMPRE las herramientas disponibles (catálogo cerrado — nunca "
            "inventes SQL ni datos). Resuelve fechas relativas ('hoy', 'esta semana', "
            "'el mes pasado') a YYYY-MM-DD en los argumentos. Si no hay pista de "
            "fecha, omite date_from/date_to (el sistema usa los últimos 30 días). "
            "Responde eligiendo UNA herramienta con sus argumentos tipados."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question[:MAX_QUESTION_CHARS]},
            ],
            "tools": self._tools_schema(catalog),
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": 400,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.warning("LLM %s → HTTP %s: %s", self.provider, resp.status_code, resp.text[:200])
                    return None
                msg = resp.json()["choices"][0]["message"]
        except Exception as exc:  # noqa: BLE001 — degradación elegante R5
            logger.warning("LLM tool calling falló (%s) → fallback determinista", exc)
            return None

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return None
        tc = tool_calls[0]["function"]
        try:
            raw_args = json.loads(tc.get("arguments") or "{}")
        except json.JSONDecodeError:
            raw_args = {}
        # Sanear: strings vacíos → None (bug del spike) + solo keys del schema
        return {"name": tc.get("name", ""), "params": raw_args or {}}


# ═══════════════════════════════════════════════════════════════
# Fallback determinista (R5 — sin LLM key / error / sin match)
# ═══════════════════════════════════════════════════════════════

def _is_injection(question: str) -> bool:
    """R1/CA-F5.7: intento de SQL libre → rechazo R5."""
    q = question.lower()
    return any(re.search(pat, q) for pat in _INJECTION_PATTERNS)


def _fallback_select(question: str) -> str | None:
    """Elige consulta del catálogo por palabras clave (spike: 100% a 35-44ms).

    Score: gana la regla con MÁS keywords matcheadas (desempate por orden).
    Así "resumen de delivery... GMV" → delivery_overview (2 hits) y no
    campaign_roas (1 hit por 'gmv') — lección F3 del greedy 'vs'.
    """
    q = question.lower()
    best_name: str | None = None
    best_score = 0
    for name, keywords in _FALLBACK_RULES:
        score = sum(1 for k in keywords if k in q)
        if score > best_score:
            best_name, best_score = name, score
    return best_name


def _resolve_relative_dates(question: str) -> tuple[date, date] | None:
    """D7/R9: normaliza fechas relativas del lenguaje natural a ISO."""
    now = datetime.now(timezone.utc).date()
    for pattern, resolver in _RELATIVE_DATE_PATTERNS:
        m = pattern.search(question.lower())
        if m:
            try:
                return resolver(now, m)
            except Exception:  # noqa: BLE001
                continue
    return None


# ═══════════════════════════════════════════════════════════════
# DeliverySkill (D3 — implementa el puerto hexagonal BaseSkill)
# ═══════════════════════════════════════════════════════════════

class DeliverySkill:
    """Skill concreta del MVP (D4 — solo delivery).

    Ejecuta las consultas del catálogo con SQL parametrizado vinculado (R1).
    Replica las fórmulas de owner_dashboard_service/delivery_service
    (misma fórmula, cero divergencia — decisión Spec Anchor).

    Implementa el contrato BaseSkill de `app/core/agents/base.py` (deuda #8):
    name/description/execute(context, params) → SkillResult.
    """

    name = "delivery"
    description = "Consultas de delivery: top productos, zonas, ROAS, resumen, embudo, ticket, horas, comparativa, márgenes, canales."

    async def execute(self, db: AsyncSession, tenant_id: int,
                      catalog: QueryCatalog, params: dict[str, Any]) -> dict:
        """Ejecuta sql_template con params vinculados + :tenant_id (R2).

        - SQLAlchemy detecta `:name` del template automáticamente (R1).
        - Fechas ISO → date objects (asyncpg rechaza str para columnas DATE).
        """
        bind: dict[str, Any] = {"tenant_id": tenant_id}
        for k, v in (params or {}).items():
            # normalize ISO dates → date() (asyncpg exige el objeto para DATE)
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                try:
                    bind[k] = date.fromisoformat(v)
                except ValueError:
                    bind[k] = v
            else:
                bind[k] = v
        stmt = text(catalog.sql_template)
        rows = (await db.execute(stmt, params=bind)).mappings().all()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# AssistantService — pipeline completo (§3.3.2)
# ═══════════════════════════════════════════════════════════════

class AssistantService:
    def __init__(self, db: AsyncSession, tenant_id: int, user_id: int | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.llm = LLMClient()
        self.skill = DeliverySkill()

    async def _load_catalog(self, role: str) -> list[QueryCatalog]:
        """Catálogo activo del tenant/rol (R8). El catálogo es global (seed),
        pero filtrado por `allowed_roles` y `active`."""
        from sqlalchemy import select
        stmt = select(QueryCatalog).where(QueryCatalog.active.is_(True))
        rows = (await self.db.execute(stmt)).scalars().all()
        return [q for q in rows if role in (q.allowed_roles or [])]

    def _validate_params(self, catalog: QueryCatalog, params: dict[str, Any]) -> dict[str, Any]:
        """Paso 3 — validar params contra el schema (R9/CA-F5.9).

        - solo keys del schema (ignora extras del LLM)
        - tipos: date → ISO válida; int → entero; enum → allowed_values
        - date_from <= date_to
        - strings vacíos → None (bug del spike)
        - default: rango = últimos 30 días (R9, patrón _resolve_dates)
        """
        schema = {p["name"]: p for p in (catalog.params or [])}
        clean: dict[str, Any] = {}
        for name, p in schema.items():
            raw = params.get(name)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                if p.get("required") and p["type"] == "date":
                    continue  # fecha requerida sin valor → se resuelve por default
                # opcional sin valor → None explícito (el template lo bindea
                # como NULL, ej. `:channel IS NULL OR c.channel = :channel`)
                clean[name] = None
                continue
            if p["type"] == "date":
                try:
                    clean[name] = date.fromisoformat(str(raw)).isoformat()
                except ValueError:
                    raise ValueError(f"fecha inválida '{raw}' en parámetro '{name}' (YYYY-MM-DD)")
            elif p["type"] == "int":
                try:
                    clean[name] = int(raw)
                except (TypeError, ValueError):
                    raise ValueError(f"entero inválido '{raw}' en parámetro '{name}'")
            elif p["type"] == "enum":
                allowed = p.get("allowed_values") or []
                if raw not in allowed:
                    raise ValueError(
                        f"valor '{raw}' no permitido en '{name}' (opciones: {', '.join(allowed)})"
                    )
                clean[name] = raw
            else:
                clean[name] = str(raw)

        # Fechas: default últimos 30 días (R9) + from <= to
        if "date_from" in schema and ("date_from" not in clean or clean["date_from"] is None):
            clean["date_from"] = (date.today() - timedelta(days=DEFAULT_RANGE_DAYS - 1)).isoformat()
        if "date_to" in schema and ("date_to" not in clean or clean["date_to"] is None):
            clean["date_to"] = date.today().isoformat()
        if "date_from" in clean and "date_to" in clean:
            if clean["date_from"] > clean["date_to"]:
                raise ValueError("date_from no puede ser posterior a date_to (R9)")
        # limit default (top_products_delivery)
        if "limit" in schema and ("limit" not in clean or clean["limit"] is None):
            clean["limit"] = 5
        return clean

    def _format_answer(self, catalog: QueryCatalog, rows: list[dict],
                       params: dict[str, Any]) -> str:
        """Paso 6 — respuesta en español con plantilla por consulta (§3.3.2)."""
        tpl = _ANSWER_TEMPLATES.get(catalog.name)
        if tpl is None:
            return f"📊 {catalog.description_es.split('.')[0]}: {json.dumps(rows, ensure_ascii=False, default=str)}"
        ctx: dict[str, Any] = {
            "date_from": params.get("date_from", ""),
            "date_to": params.get("date_to", ""),
            "limit": params.get("limit", 5),
        }

        def _money(v) -> float:
            try:
                return round(float(v or 0), 2)
            except (TypeError, ValueError):
                return 0.0

        if catalog.name == "top_products_delivery":
            items = "\n".join(
                f"  {i}. {r['name']} — {_money(r['qty']):.0f} und en S/ {_money(r['total']):,.2f}"
                for i, r in enumerate(rows[:ctx["limit"]], 1)
            ) or "  (sin ventas en el período)"
            ctx["items"] = items
        elif catalog.name == "sales_by_zone":
            ctx["items"] = "\n".join(
                f"  • {r['zone']}: {int(r['orders'])} pedidos" for r in rows
            ) or "  (sin pedidos)"
        elif catalog.name == "campaign_roas":
            ctx["items"] = "\n".join(
                f"  • {r['name']} ({r['channel']}): ROAS {_money(r['roas']):.2f}, "
                f"AOV S/ {_money(r['aov']):,.2f}, GMV S/ {_money(r['gmv']):,.2f} "
                f"(inversión S/ {_money(r['spend']):,.2f})"
                for r in rows
            ) or "  (sin campañas en el período)"
        elif catalog.name == "delivery_overview":
            ctx["orders"] = int(rows[0]["orders"] or 0) if rows else 0
            ctx["gmv"] = _money(rows[0]["gmv"] if rows else 0)
            ctx["fee_total"] = _money(rows[0]["fee_total"] if rows else 0)
            ctx["avg_delivery_min"] = rows[0].get("avg_delivery_min") if rows else None
            ctx["cancelled"] = int(rows[0]["cancelled"] or 0) if rows else 0
        elif catalog.name == "orders_by_status":
            ctx["items"] = "\n".join(
                f"  • {r['status']}: {int(r['n'])}" for r in rows
            ) or "  (sin pedidos)"
        elif catalog.name == "avg_ticket_delivery":
            ctx["ticket"] = _money(rows[0]["ticket"] if rows else 0)
            ctx["orders"] = int(rows[0]["orders"] or 0) if rows else 0
        elif catalog.name == "sales_by_hour_delivery":
            ctx["items"] = "\n".join(
                f"  • {int(r['hour']):02d}:00 — S/ {_money(r['total']):,.2f}" for r in rows
            ) or "  (sin ventas)"
        elif catalog.name == "comparison_week":
            r = rows[0] if rows else {}
            ctx["sales_total"] = _money(r.get("sales_total"))
            ctx["prev_sales_total"] = _money(r.get("prev_sales_total"))
            ctx["orders"] = int(r.get("orders") or 0)
            ctx["prev_orders"] = int(r.get("prev_orders") or 0)
            # pct puede ser NULL (período anterior sin ventas) → 0.0
            ctx["sales_total_pct"] = r.get("sales_total_pct")
            if ctx["sales_total_pct"] is None:
                ctx["sales_total_pct"] = 0.0
            ctx["orders_count_pct"] = r.get("orders_count_pct")
            if ctx["orders_count_pct"] is None:
                ctx["orders_count_pct"] = 0.0
        elif catalog.name == "delivery_margins":
            r = rows[0] if rows else {}
            revenue = _money(r.get("revenue"))
            cost = _money(r.get("cost"))
            ctx["revenue"] = revenue
            ctx["cost"] = cost
            ctx["margin_pct"] = round((revenue - cost) / revenue * 100, 1) if revenue else 0.0
        elif catalog.name == "sales_by_channel":
            ctx["items"] = "\n".join(
                f"  • {r['channel']}: S/ {_money(r['total']):,.2f}" for r in rows
            ) or "  (sin ventas)"
        return tpl.format(**ctx)

    async def ask(self, question: str, role: str) -> AskResponse:
        """Pipeline completo (§3.3.2). CA-F5.1..CA-F5.9."""
        started = time.time()
        question = question.strip()[:MAX_QUESTION_CHARS]

        # Sanitize + anti-inyección (R1/CA-F5.7)
        if not question or _is_injection(question):
            await self._log(pregunta=question, catalog_id=None, params=None,
                            summary=None, tokens_used=None, rejected=True)
            return AskResponse(
                answer=("Solo puedo responder consultas de delivery con datos del sistema. "
                        "No ejecuto instrucciones SQL ni comandos."),
                catalog_query_used=None, data=None,
                suggestions=list(_FALLBACK_SUGGESTIONS),
            )

        catalog = await self._load_catalog(role)

        # Paso 2 — LLM tool calling (D1); sin key/error → fallback (R5)
        selection: dict | None = None
        llm_failed = False
        if self.llm.available:
            selection = await self.llm.select_query(question, catalog)
            if selection is None:
                llm_failed = True
        if selection is None:
            name = _fallback_select(question)
            if name is None:
                # R5 — sin match de catálogo: rechazo amable + sugerencias
                await self._log(pregunta=question, catalog_id=None, params=None,
                                summary=None, tokens_used=None, rejected=True)
                return AskResponse(
                    answer=("Aún no sé responder eso. Puedo ayudarte con consultas de "
                            "delivery como:"),
                    catalog_query_used=None, data=None,
                    suggestions=list(_FALLBACK_SUGGESTIONS),
                )
            selection = {"name": name, "params": {}}
            # fechas relativas en modo fallback (D7)
            rel = _resolve_relative_dates(question)
            if rel:
                selection["params"]["date_from"] = rel[0].isoformat()
                selection["params"]["date_to"] = rel[1].isoformat()

        q = next((c for c in catalog if c.name == selection["name"]), None)
        if q is None:
            await self._log(pregunta=question, catalog_id=None, params=None,
                            summary=None, tokens_used=None, rejected=True)
            return AskResponse(
                answer="No encontré esa consulta en el catálogo disponible.",
                catalog_query_used=None, data=None,
                suggestions=list(_FALLBACK_SUGGESTIONS),
            )

        # Paso 3 — validar params (R9/CA-F5.9) → 422 por el router
        try:
            clean_params = self._validate_params(q, selection.get("params") or {})
        except ValueError as exc:
            raise ValueError(str(exc))

        # Paso 4+5 — inyectar tenant (R2) y ejecutar (R1/R7)
        try:
            rows = await self.skill.execute(
                db=self.db, tenant_id=self.tenant_id,
                catalog=q, params=clean_params,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("F5 consulta %s falló: %s", q.name, exc)
            raise

        # Paso 6 — formatear en español
        answer = self._format_answer(q, rows, clean_params)

        # Paso 7 — auditoría (R4)
        summary = {"rows": len(rows)}
        if rows and any(k in rows[0] for k in ("total", "gmv", "revenue", "sales_total", "ticket")):
            first = rows[0]
            for k in ("total", "gmv", "revenue", "sales_total", "ticket", "roas"):
                if k in first:
                    summary["total"] = round(float(first[k] or 0), 2)
                    break
        await self._log(pregunta=question, catalog_id=q.id, params=clean_params,
                        summary=summary, tokens_used=None, rejected=False,
                        latency_ms=int((time.time() - started) * 1000))

        return AskResponse(
            answer=answer,
            data=rows,
            catalog_query_used=CatalogQueryUsed(id=q.id, name=q.name, skill=q.skill),
            params=clean_params,
        )

    async def _log(self, pregunta: str, catalog_id: int | None, params: dict | None,
                   summary: dict | None, tokens_used: int | None,
                   rejected: bool, latency_ms: int | None = None) -> None:
        """R4 — escribir query_logs (nunca falla el ask por el log)."""
        try:
            self.db.add(QueryLog(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                pregunta=pregunta,
                query_catalog_id=catalog_id,
                params=params,
                result_summary=summary,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                rejected=rejected,
            ))
            await self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("F5 query_logs falló (no bloquea el ask): %s", exc)
            await self.db.rollback()
