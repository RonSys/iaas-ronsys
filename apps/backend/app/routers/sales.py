"""
🛒 Endpoints de Ventas — FastAPI Router.

HU-F2-003: Sesiones POS
HU-F2-004: Ventas CRUD
HU-F2-005: Integración Kárdex (automática en create/void)
HU-F2-006: Asiento contable (automático en create/void)
HU-F2-007: Ticket + payment methods

Endpoints:
  POST   /api/sales/sessions/open          → Abrir sesión POS
  GET    /api/sales/sessions/current        → Sesión activa + totales
  POST   /api/sales/sessions/{id}/close     → Cerrar sesión POS
  POST   /api/sales/sale                    → Crear venta completa
  GET    /api/sales/sales                   → Listar ventas (paginado)
  GET    /api/sales/sale/{id}               → Detalle de venta
  POST   /api/sales/sale/{id}/void          → Anular venta
  GET    /api/sales/sale/{id}/ticket         → Ticket formateado
  GET    /api/sales/payment-methods          → Métodos de pago habilitados
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.services.sales_service import PosSessionService, SaleService

router = APIRouter(prefix="/api/sales", tags=["Ventas"])


# ═══════════════════════════════════════════════════════════════
# HU-F2-003: Sesiones POS
# ═══════════════════════════════════════════════════════════════


@router.post("/sessions/open")
async def open_pos_session(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    opening_cash: float = Query(..., ge=0, description="Monto de caja inicial"),
    notes: str | None = None,
):
    """
    Abre una nueva sesión POS.

    Valida que no haya otra sesión abierta (409 si existe).
    """
    session = await PosSessionService.open_session(
        db=db,
        company_id=tenant_id,
        user_id=int(current_user.id),
        opening_cash=opening_cash,
        notes=notes,
    )
    return {
        "id": session.id,
        "company_id": session.company_id,
        "user_id": session.user_id,
        "opened_at": session.opened_at,
        "opening_cash": float(session.opening_cash),
        "status": session.status,
        "notes": session.notes,
    }


@router.get("/sessions/current")
async def get_current_pos_session(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Obtiene la sesión POS activa con ventas del turno + totales.

    Retorna 404 si no hay sesión abierta.
    """
    session = await PosSessionService.get_current_session(db, tenant_id)
    if not session:
        raise HTTPException(status_code=404, detail="No hay sesión POS abierta")

    return await PosSessionService.get_session_with_sales(db, session.id, tenant_id)


@router.post("/sessions/{session_id}/close")
async def close_pos_session(
    session_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    closing_cash: float = Query(..., ge=0, description="Efectivo contado al cierre"),
    notes: str | None = None,
):
    """
    Cierra sesión POS.

    Calcula expected_cash = opening + ventas_efectivo.
    Compara con closing_cash → retorna difference.
    status → closed. 409 si ya cerrada.
    """
    return await PosSessionService.close_session(
        db=db,
        session_id=session_id,
        company_id=tenant_id,
        closing_cash=closing_cash,
        notes=notes,
    )


# ═══════════════════════════════════════════════════════════════
# HU-F2-004: Ventas CRUD
# ═══════════════════════════════════════════════════════════════


@router.post("/sale")
async def create_sale(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """
    Crea una venta completa con items + payments.

    Valida:
      - Sesión abierta (409 si no)
      - Payments cubren total (400 si no)
      - Stock suficiente (409 si no)

    Efectos:
      - Crea Sale, SaleItems, SalePayments
      - Crea especialización (restaurant/hardware)
      - Registra salidas en kárdex (HU-F2-005)
      - Genera asiento contable automático (HU-F2-006)
    """
    return await SaleService.create_sale(
        db=db,
        company_id=tenant_id,
        user_id=int(current_user.id),
        data=body,
    )


@router.get("/sales")
async def list_sales(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    business_type: str | None = None,
    session_id: int | None = None,
    is_voided: bool | None = None,
):
    """
    Lista ventas paginado con filtros opcionales.

    Filtros: from, to, business_type, session_id, is_voided.
    """
    return await SaleService.list_sales(
        db=db,
        company_id=tenant_id,
        page=page,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
        business_type=business_type,
        session_id=session_id,
        is_voided=is_voided,
    )


@router.get("/sale/{sale_id}")
async def get_sale_detail(
    sale_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Obtiene detalle completo de una venta.

    Incluye: items, payments, especialización (restaurant/hardware),
    journal_entry_id.
    """
    return await SaleService.get_sale_detail(db, sale_id, tenant_id)


@router.post("/sale/{sale_id}/void")
async def void_sale(
    sale_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """
    Anula una venta.

    - is_voided = true
    - Registra razón de anulación
    - Reversa movimientos kárdex (HU-F2-005)
    - Crea contra-asiento contable (HU-F2-006)
    - 409 si ya está anulada
    """
    reason = body.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="Se requiere 'reason' para anular")
    return await SaleService.void_sale(db, sale_id, tenant_id, reason)


# ═══════════════════════════════════════════════════════════════
# HU-F2-007: Ticket + Payment Methods
# ═══════════════════════════════════════════════════════════════


@router.get("/sale/{sale_id}/ticket")
async def get_sale_ticket(
    sale_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("json", description="json | text"),
):
    """
    Obtiene ticket de venta formateado.

    Query params:
        format: 'json' (default) o 'text' (formato texto plano).
    """
    if format not in ("json", "text"):
        raise HTTPException(status_code=400, detail="Formato debe ser 'json' o 'text'")

    detail = await SaleService.get_sale_detail(db, sale_id, tenant_id)
    return SaleService.format_ticket(detail, format)


@router.get("/payment-methods")
async def get_payment_methods(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Lista métodos de pago habilitados según business_type/feature flags.
    """
    from app.adapters.db.models.accounting import Company
    from sqlalchemy import select

    result = await db.execute(select(Company).where(Company.id == tenant_id))
    company = result.scalar_one_or_none()
    bt = company.business_type if company else "retail"
    return SaleService.get_payment_methods(bt)