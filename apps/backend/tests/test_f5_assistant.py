"""
Tests Spec 08 — F5 "Pregúntale al Sistema" (backend, núcleo + seguridad).

Cubre (Fase 2–3, mock-based como F3 — sin LLM real ni BD en el pipeline):
  - Fallback determinista R5: selección por palabras clave (spike: 100%).
  - Anti-inyección R1/CA-F5.7: DROP/UNION/SELECT * / ';' → rechazo rejected.
  - Fechas relativas D7/R9: 'hoy', 'ayer', 'esta semana', 'el mes pasado'.
  - Validación de params R9/CA-F5.9: fecha inválida, from>to, enum, default 30d.
  - Tenant scope R2/CA-F5.5: :tenant_id siempre inyectado por el motor.
  - Auditoría R4/CA-F5.6: query_logs con pregunta, catalog_id, resumen, rejected.
  - Modo degradado CA-F5.8: sin LLM key → fallback, nunca 500.
  - Solo lectura R7: sql_template del seed es SELECT/WITH, sin cláusulas de escritura.

Regla dura (precedente F2 D4): ningún test usa números personales del agente.
"""

import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.db.models.assistant import QueryCatalog
from app.services.assistant_service import (
    _fallback_select,
    _is_injection,
    _resolve_relative_dates,
    AssistantService,
    DeliverySkill,
    LLMClient,
)

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

def _make_catalog(name: str = "top_products_delivery", **overrides) -> QueryCatalog:
    """QueryCatalog en memoria (sin tocar BD)."""
    params = [
        {"name": "date_from", "type": "date", "required": True,
         "description_es": "Fecha inicial"},
        {"name": "date_to", "type": "date", "required": True,
         "description_es": "Fecha final"},
        {"name": "limit", "type": "int", "required": False,
         "description_es": "Límite"},
    ]
    defaults = dict(
        id=1, skill="delivery", name=name,
        description_es="Producto(s) más vendido(s) por delivery en un rango de fechas",
        sql_template="""SELECT si.item_name AS name,
                               COALESCE(SUM(si.quantity),0) AS qty,
                               COALESCE(SUM(si.total),0) AS total
                        FROM sale_items si JOIN sales s ON s.id=si.sale_id
                        JOIN restaurant_sales rs ON rs.sale_id=s.id
                        WHERE s.tenant_id=:tenant_id AND s.is_voided=false
                          AND rs.order_type='delivery'
                          AND s.sale_date>=:date_from AND s.sale_date<=:date_to
                        GROUP BY si.item_name ORDER BY SUM(si.quantity) DESC LIMIT :limit""",
        params=params, allowed_roles=["admin", "manager", "viewer"],
        tenant_scope=True, active=True,
    )
    defaults.update(overrides)
    return QueryCatalog(**defaults)


def _make_service(role: str = "admin", llm_available: bool = False) -> AssistantService:
    db = AsyncMock()
    svc = AssistantService(db=db, tenant_id=1, user_id=7)
    svc.llm = MagicMock(spec=LLMClient)
    svc.llm.available = llm_available
    return svc


# ═══════════════════════════════════════════════════════════════
# Fallback determinista (R5 / CA-F5.8)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("question,expected", [
    ("¿cuál es el producto más vendido por delivery?", "top_products_delivery"),
    ("¿qué plato se vendió más a domicilio?", "top_products_delivery"),
    ("¿cuántos pedidos hubo en la Zona 1?", "sales_by_zone"),
    ("¿pedidos por distrito?", "sales_by_zone"),
    ("¿qué campaña tuvo mejor ROAS el mes pasado?", "campaign_roas"),
    ("¿cuánto invertimos en campañas?", "campaign_roas"),
    ("¿cuántos pedidos se cancelaron?", "orders_by_status"),
    ("¿cuántos pedidos se entregaron?", "orders_by_status"),
    ("¿cuál es el ticket promedio a domicilio?", "avg_ticket_delivery"),
    ("¿a qué hora se vende más delivery?", "sales_by_hour_delivery"),
    ("¿cuál es el margen del delivery?", "delivery_margins"),
    ("resumen de delivery de la semana", "delivery_overview"),
    ("¿cómo fue esta semana vs la anterior?", "comparison_week"),
    ("¿cuánto vendió el salón vs delivery?", "sales_by_channel"),
])
def test_fallback_select(question: str, expected: str):
    """R5: el fallback determinista elige la consulta correcta por palabras clave."""
    assert _fallback_select(question) == expected


def test_fallback_select_no_match():
    """R5: sin match → None (rechazo amable con sugerencias)."""
    assert _fallback_select("¿cuál es el apellido del dueño?") is None


# ═══════════════════════════════════════════════════════════════
# Anti-inyección (R1 / CA-F5.7)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("question", [
    "dame SQL de todo; DROP TABLE sales--",
    "SELECT * FROM users",
    "SELECT * FROM users; DROP TABLE sales",
    "union select password from users",
    "cuéntame de information_schema.tables",
    "borra la venta 5",
    "update sales set total=0",
])
def test_is_injection(question: str):
    """CA-F5.7: intentos de inyección/SQL libre → detectados."""
    assert _is_injection(question)


@pytest.mark.parametrize("question", [
    "¿cuál es el producto más vendido hoy por delivery?",
    "¿cuánto vendió la Zona 1 esta semana?",
    "¿qué campaña tuvo mejor ROAS el mes pasado?",
])
def test_is_not_injection(question: str):
    """Preguntas legítimas NO son inyección."""
    assert not _is_injection(question)


# ═══════════════════════════════════════════════════════════════
# Fechas relativas (D7 / R9)
# ═══════════════════════════════════════════════════════════════

def test_resolve_relative_dates_hoy():
    frm, to = _resolve_relative_dates("¿cuánto vendió hoy?")
    assert frm == to == date.today()


def test_resolve_relative_dates_ayer():
    frm, to = _resolve_relative_dates("¿cuánto vendió ayer?")
    assert frm == to == date.today() - timedelta(days=1)


def test_resolve_relative_dates_semana():
    frm, to = _resolve_relative_dates("¿cuánto vendió la Zona 1 esta semana?")
    assert frm == date.today() - timedelta(days=date.today().weekday())
    assert to == date.today()


def test_resolve_relative_dates_mes_pasado():
    now = date.today()
    frm, to = _resolve_relative_dates("¿qué campaña tuvo mejor ROAS el mes pasado?")
    assert to == now.replace(day=1) - timedelta(days=1)
    assert frm == to.replace(day=1)


def test_resolve_relative_dates_none():
    assert _resolve_relative_dates("¿cuánto vendió el delivery?") is None


# ═══════════════════════════════════════════════════════════════
# Validación de params (R9 / CA-F5.9)
# ═══════════════════════════════════════════════════════════════

def test_validate_params_defaults_30d():
    """R9: sin fechas → últimos 30 días; limit default 5."""
    svc = _make_service()
    clean = svc._validate_params(_make_catalog(), {})
    assert clean["date_from"] == (date.today() - timedelta(days=29)).isoformat()
    assert clean["date_to"] == date.today().isoformat()
    assert clean["limit"] == 5


def test_validate_params_invalid_date():
    """CA-F5.9: fecha malformada → ValueError (422 en el router)."""
    svc = _make_service()
    with pytest.raises(ValueError, match="fecha inválida"):
        svc._validate_params(_make_catalog(), {"date_from": "13/13/2026"})


def test_validate_params_from_gt_to():
    """CA-F5.9: date_from > date_to → ValueError."""
    svc = _make_service()
    with pytest.raises(ValueError, match="date_from no puede ser posterior"):
        svc._validate_params(_make_catalog(), {
            "date_from": "2026-08-13", "date_to": "2026-08-01",
        })


def test_validate_params_empty_strings_to_default():
    """Bug del spike: strings vacíos del LLM → None → default."""
    svc = _make_service()
    clean = svc._validate_params(_make_catalog(), {
        "date_from": "", "date_to": "", "limit": "",
    })
    assert clean["date_from"] == (date.today() - timedelta(days=29)).isoformat()
    assert clean["limit"] == 5


def test_validate_params_enum():
    """R9: enum fuera de allowed_values → ValueError."""
    q = _make_catalog(name="campaign_roas", params=[
        {"name": "date_from", "type": "date", "required": True},
        {"name": "date_to", "type": "date", "required": True},
        {"name": "channel", "type": "enum", "required": False,
         "allowed_values": ["meta", "google", "tiktok", "other"]},
    ])
    svc = _make_service()
    with pytest.raises(ValueError, match="no permitido"):
        svc._validate_params(q, {"channel": "youtube"})
    clean = svc._validate_params(q, {"channel": "meta"})
    assert clean["channel"] == "meta"


# ═══════════════════════════════════════════════════════════════
# Pipeline ask (R2/R4/R5/CA-F5.8)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ask_fallback_success():
    """CA-F5.1: pregunta → fallback (sin LLM) → respuesta con data + auditoría."""
    svc = _make_service(llm_available=False)
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock(return_value=[
        {"name": "Lomo Saltado", "qty": 12, "total": 486.0},
    ])
    svc._log = AsyncMock()

    resp = await svc.ask("¿cuál es el producto más vendido por delivery?", role="admin")

    assert resp.catalog_query_used is not None
    assert resp.catalog_query_used.name == "top_products_delivery"
    assert "Lomo Saltado" in resp.answer
    assert resp.data == [{"name": "Lomo Saltado", "qty": 12, "total": 486.0}]
    assert resp.params["limit"] == 5
    # R2: tenant_id inyectado en la ejecución
    _, kwargs = svc.skill.execute.call_args
    assert kwargs["tenant_id"] == 1
    # R4: auditoría con catalog_id
    assert svc._log.await_count == 1


@pytest.mark.asyncio
async def test_ask_injection_rejected():
    """CA-F5.7: inyección → rechazo R5, nunca se ejecuta, rejected=true."""
    svc = _make_service(llm_available=False)
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock()
    svc._log = AsyncMock()

    resp = await svc.ask("SELECT * FROM users; DROP TABLE sales--", role="admin")

    assert resp.catalog_query_used is None
    assert "No ejecuto instrucciones SQL" in resp.answer
    svc.skill.execute.assert_not_awaited()
    _, kwargs = svc._log.call_args
    assert kwargs["rejected"] is True


@pytest.mark.asyncio
async def test_ask_no_match_suggestions():
    """CA-F5.4: fuera de catálogo → fallback amable con sugerencias, rejected."""
    svc = _make_service(llm_available=False)
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock()
    svc._log = AsyncMock()

    resp = await svc.ask("¿cuál es el apellido del dueño?", role="admin")

    assert resp.catalog_query_used is None
    assert resp.suggestions and len(resp.suggestions) >= 3
    svc.skill.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_ask_llm_selection_used():
    """D1: con LLM disponible, usa la selección del tool calling."""
    svc = _make_service(llm_available=True)
    svc.llm.select_query = AsyncMock(return_value={
        "name": "top_products_delivery",
        "params": {"date_from": "2026-08-13", "date_to": "2026-08-13", "limit": 3},
    })
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock(return_value=[
        {"name": "Ceviche", "qty": 5, "total": 240.0},
    ])
    svc._log = AsyncMock()

    resp = await svc.ask("¿cuál es el producto más vendido hoy?", role="viewer")

    assert resp.catalog_query_used.name == "top_products_delivery"
    assert resp.params["date_from"] == "2026-08-13"
    assert resp.params["limit"] == 3
    svc.llm.select_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_ask_llm_error_falls_back():
    """CA-F5.8: error LLM → fallback determinista, nunca 500."""
    svc = _make_service(llm_available=True)
    svc.llm.select_query = AsyncMock(return_value=None)  # LLM falló
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock(return_value=[
        {"name": "Lomo Saltado", "qty": 12, "total": 486.0},
    ])
    svc._log = AsyncMock()

    resp = await svc.ask("¿cuál es el producto más vendido por delivery?", role="admin")

    assert resp.catalog_query_used.name == "top_products_delivery"
    assert "Lomo Saltado" in resp.answer


@pytest.mark.asyncio
async def test_ask_tenant_scope_always_injected():
    """R2/CA-F5.5: :tenant_id SIEMPRE inyectado por el motor (nunca por el LLM)."""
    svc = _make_service(llm_available=True)
    # el LLM intenta colar otro tenant_id
    svc.llm.select_query = AsyncMock(return_value={
        "name": "top_products_delivery",
        "params": {"date_from": "2026-08-01", "date_to": "2026-08-13",
                   "tenant_id": 999},
    })
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock(return_value=[])
    svc._log = AsyncMock()

    await svc.ask("¿top productos?", role="admin")

    _, kwargs = svc.skill.execute.call_args
    # el motor usa tenant_id del contexto (1), no el 999 del LLM
    assert kwargs["tenant_id"] == 1
    # params finales NO contienen tenant_id (no está en el schema → se ignora)
    assert "tenant_id" not in kwargs["params"] or kwargs["params"].get("tenant_id") is None


@pytest.mark.asyncio
async def test_ask_invalid_params_raises():
    """CA-F5.9: params inválidos → ValueError (el router responde 422)."""
    svc = _make_service(llm_available=True)
    svc.llm.select_query = AsyncMock(return_value={
        "name": "top_products_delivery",
        "params": {"date_from": "13/13/2026", "date_to": "2026-08-13"},
    })
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])

    with pytest.raises(ValueError, match="fecha inválida"):
        await svc.ask("¿top productos?", role="admin")


@pytest.mark.asyncio
async def test_ask_audit_log_fields():
    """R4/CA-F5.6: el log lleva pregunta cruda, catalog_id, params, resumen."""
    svc = _make_service(llm_available=False)
    svc._load_catalog = AsyncMock(return_value=[_make_catalog()])
    svc.skill.execute = AsyncMock(return_value=[
        {"name": "Lomo Saltado", "qty": 12, "total": 486.0},
    ])
    svc._log = AsyncMock()

    await svc.ask("¿cuál es el producto más vendido por delivery?", role="admin")

    _, kwargs = svc._log.call_args
    assert kwargs["pregunta"] == "¿cuál es el producto más vendido por delivery?"
    assert kwargs["catalog_id"] == 1
    assert kwargs["rejected"] is False
    assert kwargs["summary"] == {"rows": 1, "total": 486.0}
    assert kwargs["latency_ms"] is not None


@pytest.mark.asyncio
async def test_ask_comparison_week_null_pcts():
    """Regresión QA 2026-08-14: prev_sales_total=0 → pct NULL → no 500.

    El SQL devuelve sales_total_pct/orders_count_pct NULL cuando el período
    anterior no tuvo ventas; el formateo debía fallar con
    "unsupported format string passed to NoneType.__format__".
    """
    svc = _make_service(llm_available=False)
    q = _make_catalog(name="comparison_week", params=[
        {"name": "date_from", "type": "date", "required": True},
        {"name": "date_to", "type": "date", "required": True},
    ])
    svc._load_catalog = AsyncMock(return_value=[q])
    svc.skill.execute = AsyncMock(return_value=[{
        "sales_total": 58.0, "orders": 2, "avg_ticket": 29.0,
        "prev_sales_total": 0, "prev_orders": 0, "prev_avg_ticket": 0,
        "sales_total_pct": None, "orders_count_pct": None,
    }])
    svc._log = AsyncMock()

    resp = await svc.ask("¿cómo fue esta semana vs la anterior?", role="admin")

    assert resp.catalog_query_used.name == "comparison_week"
    assert "S/ 58.00" in resp.answer
    assert "+0.0%" in resp.answer  # pct NULL → 0.0


# ═══════════════════════════════════════════════════════════════
# DeliverySkill (R1/R7 — ejecución con SQL parametrizado)
# ═══════════════════════════════════════════════════════════════

def test_skill_execute_binds_params():
    """R1: ejecución con params vinculados + tenant inyectado (nunca string SQL).

    Además: fechas ISO → date objects (asyncpg exige date() para columnas DATE).
    """
    class _FakeResult:
        def mappings(self):
            return self

        def all(self):
            return [{"name": "Lomo", "qty": 12, "total": 486.0}]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_FakeResult())
    skill = DeliverySkill()
    q = _make_catalog()
    rows = asyncio.run(skill.execute(db, tenant_id=1, catalog=q,
                                     params={"date_from": "2026-08-01", "date_to": "2026-08-13", "limit": 5}))
    assert rows == [{"name": "Lomo", "qty": 12, "total": 486.0}]
    # tenant_id siempre en el bind + fechas normalizadas a date()
    _, kwargs = db.execute.call_args
    assert kwargs["params"]["tenant_id"] == 1
    assert kwargs["params"]["date_from"] == date(2026, 8, 1)
    assert kwargs["params"]["date_to"] == date(2026, 8, 13)
    assert kwargs["params"]["limit"] == 5
