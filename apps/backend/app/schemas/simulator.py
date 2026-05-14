"""
Schemas Pydantic — Simulador de Escenarios (HU-SIM-001).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import InvestmentInput


class ScenarioCreate(BaseModel):
    """Crear un escenario."""
    name: str = Field(..., min_length=1, max_length=100)
    input_data: dict  # InvestmentInput dict
    results: dict | None = None  # Cache de FinancialReport


class ScenarioUpdate(BaseModel):
    """Actualizar un escenario (todo opcional)."""
    name: str | None = Field(None, min_length=1, max_length=100)
    input_data: dict | None = None
    results: dict | None = None


class ScenarioResponse(BaseModel):
    """Respuesta de escenario."""
    id: int
    company_id: int
    user_id: int | None = None
    name: str
    input_data: dict
    results: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScenarioListResponse(BaseModel):
    """Lista de escenarios."""
    scenarios: list[ScenarioResponse]
    total: int
    max_allowed: int


MAX_SCENARIOS = 4
