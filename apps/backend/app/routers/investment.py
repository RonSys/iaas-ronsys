"""
💰 Investment Router — Endpoints de Inversión / Puesta en Marcha (Caso 7).

Endpoints:
  GET    /api/v1/restaurant/investment           — Listar bienes
  POST   /api/v1/restaurant/investment           — Crear bien
  PUT    /api/v1/restaurant/investment/{id}      — Actualizar bien
  DELETE /api/v1/restaurant/investment/{id}      — Eliminar bien
  GET    /api/v1/restaurant/investment/summary   — Resumen de totes

🔒 Todos los endpoints requieren rol 'admin'.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.restaurant import InvestmentCreate, InvestmentUpdate
from app.services.investment_service import InvestmentService

router = APIRouter(prefix="/api/v1/restaurant/investment", tags=["Inversión"])


@router.get("")
async def list_investments(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None, description="Filtrar por categoría"),
    status: str | None = Query(None, description="Filtrar por estado (pending|acquired)"),
):
    """Lista todos los bienes de inversión del tenant."""
    return await InvestmentService.list_items(db, tenant_id, category, status)


@router.post("", status_code=201)
async def create_investment(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: InvestmentCreate,
):
    """Crea un nuevo bien de inversión.
    Usa el schema Pydantic InvestmentCreate para validación automática.
    """
    return await InvestmentService.create_item(db, tenant_id, body.model_dump(exclude_unset=True))


@router.get("/summary")
async def get_investment_summary(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retorna el resumen de totes de inversión."""
    return await InvestmentService.get_summary(db, tenant_id)


@router.get("/{item_id}")
async def get_investment_item(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene un bien de inversión por ID."""
    return await InvestmentService.get_item(db, item_id, tenant_id)


@router.put("/{item_id}")
async def update_investment(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: InvestmentUpdate,
):
    """Actualiza un bien de inversión existente.
    Usa el schema Pydantic InvestmentUpdate para validación automática.
    """
    return await InvestmentService.update_item(db, item_id, tenant_id, body.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=204)
async def delete_investment(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina un bien de inversión."""
    await InvestmentService.delete_item(db, item_id, tenant_id)
