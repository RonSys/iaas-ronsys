"""
🌐 Router Público — Delivery (Spec 03 §3.4.1).

Endpoints SIN JWT para la landing/catálogo. El tenant se resuelve por slug
(`/api/public/{slug}/...`) y TODA query filtra por ese tenant (R9).
Rate limiting Redis con fallback in-memory (patrón de auth).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.core.rate_limit import get_rate_limiter
from app.adapters.db.database import get_db
from app.schemas.delivery import (
    CheckoutRequest,
    CheckoutResponse,
    PublicMenuResponse,
    PublicZone,
    TrackingStatusOut,
)
from app.services import delivery_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/public", tags=["Delivery Público"])


async def public_rate_limit(request: Request, key: str, max_requests: int = 60, window: int = 60):
    """Dependency: rate-limit por slug/IP para el canal público."""
    limiter = get_rate_limiter(
        redis_url=settings.redis_url if settings.redis_url else None
    )
    client_ip = request.client.host if request.client else "unknown"
    result = await limiter.check(
        f"public:{key}:{client_ip}", max_requests=max_requests, window_seconds=window,
    )
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes. Reintenta en {result.retry_after_seconds}s",
        )


@router.get("/{slug}/menu", response_model=PublicMenuResponse)
async def public_menu(
    slug: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await public_rate_limit(request, f"menu:{slug}", max_requests=120, window=60)
    company = await delivery_service.get_tenant_by_slug(db, slug)
    return await delivery_service.get_public_menu(db, company.id)


@router.get("/{slug}/zones", response_model=list[PublicZone])
async def public_zones(
    slug: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await public_rate_limit(request, f"zones:{slug}", max_requests=120, window=60)
    company = await delivery_service.get_tenant_by_slug(db, slug)
    return await delivery_service.get_public_zones(db, company.id)


@router.post("/{slug}/orders", response_model=CheckoutResponse, status_code=201)
async def public_checkout(
    slug: str,
    body: CheckoutRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await public_rate_limit(request, f"checkout:{slug}", max_requests=10, window=60)
    company = await delivery_service.get_tenant_by_slug(db, slug)
    return await delivery_service.create_order(
        db, company.id, body.model_dump(mode="json"),
    )


@router.get("/orders/{tracking_code}/status", response_model=TrackingStatusOut)
async def public_tracking(
    tracking_code: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await public_rate_limit(request, "tracking", max_requests=120, window=60)
    order = await delivery_service.get_by_tracking(db, tracking_code)
    if not order:
        raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado")
    return {
        "tracking_code": order.tracking_code,
        "status": order.status,
        "eta_min": order.eta_min,
        "timestamps": delivery_service._timestamps(order),
    }
