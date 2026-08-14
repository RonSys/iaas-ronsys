"""
🤖 Schemas — Asistente "Pregúntale al Sistema" (Spec 08 F5, §3.3).

Contratos de los endpoints F5 (staff autenticado, roles admin/manager/viewer):
  - POST /api/v1/assistant/ask    { question } → AskResponse
  - GET  /api/v1/assistant/catalog → CatalogItem[]
  - GET  /api/v1/assistant/logs    → QueryLogOut[] (solo admin, R4)

Diseño (Spec 08 §3.3):
  - `catalog_query_used: null` ⇒ fallback R5 (rechazo amable + sugerencias).
  - `data` = data real de la consulta ejecutada (R3, sin cache).
  - `params` = params finales ejecutados (auditoría, R4).
  - `result_summary` en logs = SOLO resumen (rows/total), nunca data completa.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# POST /ask
# ═══════════════════════════════════════════════════════════════

class AskRequest(BaseModel):
    """Pregunta en lenguaje natural del dueño (D1: nunca SQL)."""

    question: str = Field(
        ..., min_length=3, max_length=500,
        description="Pregunta en español (ej: '¿cuál es el producto más vendido hoy por delivery?')",
    )


class CatalogQueryUsed(BaseModel):
    """Consulta del catálogo que el LLM eligió (D1)."""

    id: int
    name: str
    skill: str


class AskResponse(BaseModel):
    """Respuesta del asistente (CA-F5.1/CA-F5.4)."""

    answer: str = Field(..., description="Respuesta en español, concisa, con números exactos")
    data: Optional[Any] = Field(None, description="Data real de la consulta (R3)")
    catalog_query_used: Optional[CatalogQueryUsed] = Field(
        None, description="null ⇒ fallback R5 (rechazo amable)"
    )
    params: Optional[dict[str, Any]] = Field(
        None, description="Params finales ejecutados (R4)"
    )
    suggestions: Optional[list[str]] = Field(
        None, description="Sugerencias del catálogo (solo en fallback R5)"
    )


# ═══════════════════════════════════════════════════════════════
# GET /catalog
# ═══════════════════════════════════════════════════════════════

class CatalogItem(BaseModel):
    """Consulta visible del catálogo (solo active + rol permitido, R8)."""

    id: int
    skill: str
    name: str
    description_es: str
    params_schema: list[dict[str, Any]] = Field(alias="params")


# ═══════════════════════════════════════════════════════════════
# GET /logs (solo admin, R4)
# ═══════════════════════════════════════════════════════════════

class QueryLogOut(BaseModel):
    """Fila de auditoría (R4): resumen, NUNCA data completa."""

    created_at: datetime
    pregunta: str
    query_catalog_id: Optional[int]
    params: Optional[dict[str, Any]]
    result_summary: Optional[dict[str, Any]]
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    rejected: bool


# ═══════════════════════════════════════════════════════════════
# GET /costs (F5.3 — solo admin; unifica query_logs + call_records)
# ═══════════════════════════════════════════════════════════════

class AssistantCostItem(BaseModel):
    """Costo de IA por fuente (F5.3 — unifica query_logs + call_records)."""

    date: date
    source: str  # "assistant" | "voice_ai"
    requests: int
    tokens_used: Optional[int] = None
    cost_usd: float


class AssistantCostsOut(BaseModel):
    """Resumen de costos IA por tenant y rango (F5.3)."""

    tenant_id: int
    date_from: date
    date_to: date
    total_cost_usd: float
    by_source: dict[str, float]
    items: list[AssistantCostItem]
