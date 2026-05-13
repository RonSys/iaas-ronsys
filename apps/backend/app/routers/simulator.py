"""
🧪 Endpoints de Simulador — FastAPI Router (HU-SIM-001).

Endpoints:
  POST   /api/simulator/scenarios        → Guardar escenario
  GET    /api/simulator/scenarios        → Listar escenarios
  GET    /api/simulator/scenarios/{id}   → Detalle
  PUT    /api/simulator/scenarios/{id}   → Actualizar
  DELETE /api/simulator/scenarios/{id}   → Eliminar

Límite: 4 escenarios por empresa.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.services.simulator_service import ScenarioService
from app.schemas.simulator import (
    ScenarioCreate,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
)

router = APIRouter(prefix="/api/simulator", tags=["Simulador"])


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    body: ScenarioCreate,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Guarda un escenario de simulación (máx 4 por empresa)."""
    scenario = await ScenarioService.create(
        db=db,
        company_id=tenant_id,
        user_id=int(current_user.id),
        name=body.name,
        input_data=body.input_data,
        results=body.results,
    )
    return ScenarioResponse.model_validate(scenario)


@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista escenarios de la empresa (ordenados por fecha DESC)."""
    result = await ScenarioService.list_by_company(db, tenant_id)
    return ScenarioListResponse(
        scenarios=[ScenarioResponse.model_validate(s) for s in result["scenarios"]],
        total=result["total"],
        max_allowed=result["max_allowed"],
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene detalle de un escenario."""
    scenario = await ScenarioService.get(db, tenant_id, scenario_id)
    return ScenarioResponse.model_validate(scenario)


@router.put("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: int,
    body: ScenarioUpdate,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza un escenario (campos opcionales)."""
    scenario = await ScenarioService.update(
        db=db,
        company_id=tenant_id,
        scenario_id=scenario_id,
        name=body.name,
        input_data=body.input_data,
        results=body.results,
    )
    return ScenarioResponse.model_validate(scenario)


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(
    scenario_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina un escenario."""
    return await ScenarioService.delete(db, tenant_id, scenario_id)
