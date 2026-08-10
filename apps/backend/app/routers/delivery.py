"""
🛵 Router Staff — Delivery (Spec 03 §3.4.2).

Panel de operaciones: zonas, repartidores, campañas, pedidos (máquina de
estados), asignación de repartidor y métricas (ROAS/AOV).
Todos los endpoints exigen auth + tenant (X-Tenant-ID o JWT).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.delivery import (
    CampaignIn,
    CampaignMetricsOut,
    CampaignOut,
    CampaignUpdate,
    CourierIn,
    CourierOut,
    CourierUpdate,
    DeliveryOverviewOut,
    ZoneIn,
    ZoneOut,
    ZoneUpdate,
)
from app.services import delivery_service

router = APIRouter(prefix="/api/v1/delivery", tags=["Delivery Staff"])


# ═══════════════════════════════════════════════════════════════
# Zonas
# ═══════════════════════════════════════════════════════════════

@router.get("/zones", response_model=list[ZoneOut])
async def list_zones(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.list_zones(db, tenant_id)


@router.post("/zones", response_model=ZoneOut, status_code=201)
async def create_zone(
    body: ZoneIn,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.create_zone(
        db, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.patch("/zones/{zone_id}", response_model=ZoneOut)
async def update_zone(
    zone_id: int,
    body: ZoneUpdate,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.update_zone(
        db, zone_id, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.delete("/zones/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delivery_service.delete_zone(db, zone_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# Repartidores
# ═══════════════════════════════════════════════════════════════

@router.get("/couriers", response_model=list[CourierOut])
async def list_couriers(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.list_couriers(db, tenant_id)


@router.post("/couriers", response_model=CourierOut, status_code=201)
async def create_courier(
    body: CourierIn,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.create_courier(
        db, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.patch("/couriers/{courier_id}", response_model=CourierOut)
async def update_courier(
    courier_id: int,
    body: CourierUpdate,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.update_courier(
        db, courier_id, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.delete("/couriers/{courier_id}", status_code=204)
async def delete_courier(
    courier_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delivery_service.delete_courier(db, courier_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# Campañas
# ═══════════════════════════════════════════════════════════════

@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.list_campaigns(db, tenant_id)


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
async def create_campaign(
    body: CampaignIn,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.create_campaign(
        db, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.update_campaign(
        db, campaign_id, tenant_id, body.model_dump(exclude_unset=True),
    )


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delivery_service.delete_campaign(db, campaign_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# Pedidos + máquina de estados
# ═══════════════════════════════════════════════════════════════

@router.get("/orders")
async def list_orders(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtro multi-status (coma)"),
):
    return await delivery_service.list_orders(db, tenant_id, status)


@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await delivery_service.order_detail(db, order_id, tenant_id)


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    body: dict,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    new_status = (body or {}).get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="Se requiere 'status'")
    return await delivery_service.update_status(db, order_id, tenant_id, new_status)


@router.post("/orders/{order_id}/assign-courier")
async def assign_courier(
    order_id: int,
    body: dict,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    courier_id = (body or {}).get("courier_id")
    if not courier_id:
        raise HTTPException(status_code=400, detail="Se requiere 'courier_id'")
    return await delivery_service.assign_courier(db, order_id, tenant_id, int(courier_id))


# ═══════════════════════════════════════════════════════════════
# Métricas
# ═══════════════════════════════════════════════════════════════

@router.get("/metrics/campaigns", response_model=list[CampaignMetricsOut])
async def metrics_campaigns(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    channel: str | None = Query(None),
):
    return await delivery_service.metrics_campaigns(db, tenant_id, from_date, to_date, channel)


@router.get("/metrics/overview", response_model=DeliveryOverviewOut)
async def metrics_overview(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
):
    return await delivery_service.metrics_overview(db, tenant_id, from_date, to_date)
