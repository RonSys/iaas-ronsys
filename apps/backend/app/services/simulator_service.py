"""
📊 Scenario Service — Persistencia de escenarios del simulador (HU-SIM-001).

Límite: 4 escenarios por company_id.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.simulator import Scenario
from app.schemas.simulator import MAX_SCENARIOS


class ScenarioService:
    """CRUD de escenarios del simulador financiero."""

    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_id: int,
        user_id: int,
        name: str,
        input_data: dict,
        results: dict | None = None,
    ) -> Scenario:
        """Crea un escenario. Valida límite de 4 por company."""
        from fastapi import HTTPException

        # Check limit
        count_result = await db.execute(
            select(func.count(Scenario.id)).where(Scenario.tenant_id == tenant_id)
        )
        count = count_result.scalar() or 0
        if count >= MAX_SCENARIOS:
            raise HTTPException(
                status_code=409,
                detail=f"Máximo {MAX_SCENARIOS} escenarios por empresa. Elimina uno antes de guardar.",
            )

        scenario = Scenario(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            input_data=input_data,
            results=results,
        )
        db.add(scenario)
        await db.flush()
        await db.refresh(scenario)
        return scenario

    @staticmethod
    async def list_by_company(
        db: AsyncSession,
        tenant_id: int,
    ) -> dict:
        """Lista escenarios de una empresa, ordenados por created_at DESC."""
        result = await db.execute(
            select(Scenario)
            .where(Scenario.tenant_id == tenant_id)
            .order_by(Scenario.created_at.desc())
        )
        scenarios = result.scalars().all()
        return {
            "scenarios": scenarios,
            "total": len(scenarios),
            "max_allowed": MAX_SCENARIOS,
        }

    @staticmethod
    async def get(
        db: AsyncSession,
        tenant_id: int,
        scenario_id: int,
    ) -> Scenario:
        """Obtiene un escenario por id. 404 si no existe o no pertenece."""
        from fastapi import HTTPException

        result = await db.execute(
            select(Scenario).where(
                Scenario.id == scenario_id,
                Scenario.tenant_id == tenant_id,
            )
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise HTTPException(status_code=404, detail="Escenario no encontrado")
        return scenario

    @staticmethod
    async def update(
        db: AsyncSession,
        tenant_id: int,
        scenario_id: int,
        name: str | None = None,
        input_data: dict | None = None,
        results: dict | None = None,
    ) -> Scenario:
        """Actualiza un escenario. Campos no enviados se mantienen."""
        scenario = await ScenarioService.get(db, tenant_id, scenario_id)

        if name is not None:
            scenario.name = name
        if input_data is not None:
            scenario.input_data = input_data
        if results is not None:
            scenario.results = results

        await db.flush()
        await db.refresh(scenario)
        return scenario

    @staticmethod
    async def delete(
        db: AsyncSession,
        tenant_id: int,
        scenario_id: int,
    ) -> dict:
        """Elimina un escenario. 404 si no existe."""
        scenario = await ScenarioService.get(db, tenant_id, scenario_id)
        await db.delete(scenario)
        await db.flush()
        return {"status": "deleted", "id": scenario_id}
