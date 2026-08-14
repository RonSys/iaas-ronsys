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

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.models.assistant import QueryCatalog, QueryLog
from app.core.dependencies import require_role
from app.core.rate_limit import get_rate_limiter
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.assistant import AskRequest, AskResponse, CatalogItem, QueryLogOut
from app.services.assistant_service import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    AssistantService,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant"])


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
