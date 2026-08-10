"""
Panel del Dueño — endpoints ejecutivos (Spec 04, V1).

GET /api/v1/dashboard/owner?date_from=&date_to=
  → OwnerDashboardResponse (KPIs, series, canales, platos, pagos, delivery, campañas)

Acceso: admin/manager/viewer (D6) — solo lectura (D5). Superadmin pasa siempre.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import require_role
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.services import owner_dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["Panel del Dueño"])


@router.get("/owner")
async def owner_dashboard(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager", "viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: str | None = Query(None, description="YYYY-MM-DD (default: últimos 30 días)"),
    date_to: str | None = Query(None, description="YYYY-MM-DD (default: hoy)"),
):
    """Resumen ejecutivo del dueño: KPIs + series + canales + platos + pagos + delivery + campañas."""
    try:
        return await owner_dashboard_service.get_owner_dashboard(
            db, tenant_id, date_from=date_from, date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
