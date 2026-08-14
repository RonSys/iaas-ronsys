"""
🗣️ Router — Asistente "Pregúntale al Sistema" (Spec 08 F5, §3.3.1).

Endpoints (staff autenticado, roles admin/manager/viewer — patrón Spec 04):
  - POST /api/v1/assistant/ask     — pregunta en lenguaje natural (D1)
  - GET  /api/v1/assistant/catalog — catálogo activo del rol (R8)
  - GET  /api/v1/assistant/logs    — auditoría (R4, SOLO admin)

Seguridad:
  - Tenant scoping: get_tenant_id (R2)
  - Roles: require_role("admin","manager","viewer") (R7/R8)
  - Rate limit Redis por tenant en /ask (R6): 10 req/min → 429 + Retry-After
  - Params inválidos → 422 con detalle (CA-F5.9)
  - 401 sin auth / 403 sin rol (CA-F5.14)
"""

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.models.assistant import QueryCatalog, QueryLog
from app.adapters.db.models.calls import CallRecord
from app.core.dependencies import require_role
from app.core.rate_limit import get_rate_limiter
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.assistant import (
    AskRequest,
    AskResponse,
    AssistantCostItem,
    AssistantCostsOut,
    CatalogItem,
    QueryLogOut,
)
from app.services.assistant_service import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    AssistantService,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant"])

# F5.3: tarifa estimada deepseek-v4-flash (promedio in+out) — USD por 1K tokens
COST_PER_1K_TOKENS_USD = 0.0005


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    request: Request,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager", "viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AskResponse:
    """CA-F5.1..CA-F5.4: pregunta en lenguaje natural → respuesta con dato real."""
    # R6 — rate limit por tenant (Redis sliding window + fallback in-memory)
    limiter = get_rate_limiter()
    rl = await limiter.check(
        key=f"assistant:ask:{tenant_id}",
        max_requests=RATE_LIMIT_MAX,
        window_seconds=RATE_LIMIT_WINDOW,
    )
    if not rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas consultas en poco tiempo. Espera un momento.",
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )

    svc = AssistantService(db=db, tenant_id=tenant_id, user_id=current_user.id)
    try:
        return await svc.ask(body.question, role=current_user.role)
    except ValueError as exc:
        # CA-F5.9 — params inválidos → 422 con detalle
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        # CA-F5.8 — nunca 500 silencioso; fallback amable
        from app.services.assistant_service import _FALLBACK_SUGGESTIONS
        await svc._log(body.question, None, None, None, None, rejected=True)
        raise HTTPException(
            status_code=500,
            detail=("No pude completar la consulta. "
                    f"Detalle: {str(exc)[:200]}"),
        )


@router.get("/catalog", response_model=list[CatalogItem])
async def catalog(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager", "viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CatalogItem]:
    """CA-F5.11: catálogo activo + permitido para el rol (R8)."""
    stmt = select(QueryCatalog).where(QueryCatalog.active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    allowed = [q for q in rows if current_user.role in (q.allowed_roles or [])]
    return [CatalogItem(
        id=q.id, skill=q.skill, name=q.name,
        description_es=q.description_es, params=q.params,
    ) for q in allowed]


@router.get("/logs", response_model=list[QueryLogOut])
async def logs(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
) -> list[QueryLogOut]:
    """CA-F5.6 / R4: auditoría de preguntas (SOLO admin)."""
    stmt = (
        select(QueryLog)
        .where(QueryLog.tenant_id == tenant_id)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [QueryLogOut(
        created_at=r.created_at,
        pregunta=r.pregunta,
        query_catalog_id=r.query_catalog_id,
        params=r.params,
        result_summary=r.result_summary,
        tokens_used=r.tokens_used,
        latency_ms=r.latency_ms,
        rejected=r.rejected,
    ) for r in rows]


@router.get("/costs", response_model=AssistantCostsOut)
async def costs(
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    tenant_id: Annotated[int, Depends(get_tenant_id)] = ...,
    current_user: Annotated[User, Depends(require_role("admin"))] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> AssistantCostsOut:
    """F5.3: costo IA por tenant en rango (query_logs + call_records).

    - Rango default: últimos 30 días (patrón R9). from > to → 422.
    - query_logs: costo estimado = tokens_used * COST_PER_1K_TOKENS_USD / 1000
      (tokens_used null → 0; se agrupa por día con func.date(created_at)).
    - call_records: costo real = cost_usd (F3, gobernanza existente); se agrupa
      por día con func.date(created_at).
    - Solo admin puede ver costos (es dato sensible) → require_role("admin").
    """
    today = date.today()
    from_date = from_date or (today - timedelta(days=29))
    to_date = to_date or today
    if from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="from no puede ser mayor que to",
        )

    from_dt = datetime.combine(from_date, time.min)
    to_exclusive = datetime.combine(to_date + timedelta(days=1), time.min)

    items: list[AssistantCostItem] = []

    # a) query_logs → fuente "assistant" (costo estimado por tokens)
    day_expr = func.date(QueryLog.created_at)
    stmt = (
        select(
            day_expr.label("day"),
            func.count().label("requests"),
            func.coalesce(func.sum(QueryLog.tokens_used), 0).label("tokens"),
        )
        .where(
            QueryLog.tenant_id == tenant_id,
            QueryLog.created_at >= from_dt,
            QueryLog.created_at < to_exclusive,
        )
        .group_by(day_expr)
    )
    rows = (await db.execute(stmt)).mappings().all()
    for r in rows:
        tokens = int(r["tokens"] or 0)
        items.append(AssistantCostItem(
            date=r["day"],
            source="assistant",
            requests=int(r["requests"]),
            tokens_used=tokens,
            cost_usd=round(tokens * COST_PER_1K_TOKENS_USD / 1000, 6),
        ))

    # b) call_records → fuente "voice_ai" (costo real F3)
    day_expr = func.date(CallRecord.created_at)
    stmt = (
        select(
            day_expr.label("day"),
            func.count().label("requests"),
            func.coalesce(func.sum(CallRecord.cost_usd), 0).label("cost"),
        )
        .where(
            CallRecord.tenant_id == tenant_id,
            CallRecord.created_at >= from_dt,
            CallRecord.created_at < to_exclusive,
        )
        .group_by(day_expr)
    )
    rows = (await db.execute(stmt)).mappings().all()
    for r in rows:
        items.append(AssistantCostItem(
            date=r["day"],
            source="voice_ai",
            requests=int(r["requests"]),
            cost_usd=float(r["cost"] or 0),
        ))

    # c) combinar: orden por (date, source); total + by_source
    items.sort(key=lambda it: (it.date, it.source))
    by_source: dict[str, float] = {}
    total = 0.0
    for it in items:
        by_source[it.source] = round(by_source.get(it.source, 0.0) + it.cost_usd, 6)
        total += it.cost_usd
    return AssistantCostsOut(
        tenant_id=tenant_id,
        date_from=from_date,
        date_to=to_date,
        total_cost_usd=round(total, 6),
        by_source=by_source,
        items=items,
    )
