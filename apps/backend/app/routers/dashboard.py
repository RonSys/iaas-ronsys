"""
Panel del Dueño — endpoints ejecutivos (Spec 04, V1 + V2).

GET /api/v1/dashboard/owner?date_from=&date_to=
  → OwnerDashboardResponse (KPIs, series, canales, platos, pagos, delivery,
    campañas + bloques V2: heatmap, margins, comparison, alerts)

GET /api/v1/dashboard/owner/export?format=csv&date_from=&date_to=
  → CSV plano por secciones (CA13; R3: CSV primero, PDF en iteración 2)

Acceso: admin/manager/viewer (D6) — solo lectura (D5). Superadmin pasa siempre.
"""
from __future__ import annotations

import unicodedata
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import require_role
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.services import owner_dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["Panel del Dueño"])


def _ascii_filename(filename: str) -> str:
    """Translitera a ASCII (NFKD) para el `filename` plano del header."""
    return unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")


def _export_disposition(filename: str) -> str:
    """Content-Disposition: `filename` ASCII + `filename*` UTF-8 (RFC 5987/6266)."""
    return (
        f"attachment; filename=\"{_ascii_filename(filename)}\"; "
        f"filename*=UTF-8''{quote(filename)}"
    )


@router.get("/owner")
async def owner_dashboard(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager", "viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: str | None = Query(None, description="YYYY-MM-DD (default: últimos 30 días)"),
    date_to: str | None = Query(None, description="YYYY-MM-DD (default: hoy)"),
):
    """Resumen ejecutivo del dueño: KPIs + series + canales + platos + pagos + delivery + campañas + V2."""
    try:
        return await owner_dashboard_service.get_owner_dashboard(
            db, tenant_id, date_from=date_from, date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/owner/export")
async def owner_dashboard_export(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager", "viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("csv", description="Formato de exportación (solo 'csv' soportado, R3)"),
    date_from: str | None = Query(None, description="YYYY-MM-DD (default: últimos 30 días)"),
    date_to: str | None = Query(None, description="YYYY-MM-DD (default: hoy)"),
):
    """CA13 — Reporte descargable CSV del período (una sola llamada a get_owner_dashboard)."""
    if format != "csv":
        raise HTTPException(status_code=422, detail="Formato no soportado: solo 'csv' (R3; PDF en iteración 2)")
    try:
        data = await owner_dashboard_service.get_owner_dashboard(
            db, tenant_id, date_from=date_from, date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ymd = data["period"]["date_to"].replace("-", "")
    filename = f"panel_dueño_{ymd}.csv"
    return Response(
        content=owner_dashboard_service.render_owner_csv(data),
        media_type="text/csv",
        headers={"Content-Disposition": _export_disposition(filename)},
    )
