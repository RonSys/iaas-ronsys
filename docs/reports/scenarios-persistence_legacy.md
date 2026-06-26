# Ficha Técnica: Persistencia de Escenarios del Simulador

**Fecha:** 2026-05-12  
**Agente:** Architecture Agent 🏗️  
**Proyecto:** IaaS-RonSys  
**Alcance:** HU-F1.5 — Persistir escenarios del Simulador Financiero

---

## 1. Diagnóstico Actual

### 1.1 Lo que existe

```typescript
// apps/web/src/pages/Simulator.tsx — líneas 39-52
interface ScenarioSnapshot {
  id: string;          // Date.now().toString() — no persiste
  name: string;        // "Realista" | "Optimista" | "Escenario N"
  price: number;
  platesPerDay: number;
  costPct: number;
  rent: number;
  salaries: number;
  revenue: number;     // Del income_statement response
  grossProfit: number;
  netIncome: number;
  payback: number | null;
  van: number | null;
  tir: number | null;
  timestamp: Date;
}

const [scenarios, setScenarios] = useState<ScenarioSnapshot[]>([]);
```

**Problema:** `useState` local. Al recargar la página (`F5`), los escenarios se pierden. No hay llamadas API, no hay persistencia en backend.

### 1.2 Datos de simulación actuales

El simulador usa 5 sliders que mapean a campos de `InvestmentInput`:

| Slider | Campo InvestmentInput | Default |
|--------|----------------------|---------|
| Precio promedio por plato | `monthly_sales = price × plates × days` | 28 |
| Platos vendidos por día | `monthly_sales` (mismo array) | 40 |
| Costo de insumos (%) | `monthly_cost_pct` | 40% |
| Alquiler mensual | `monthly_rent` | S/ 2,500 |
| Sueldos totales | `monthly_salaries` | S/ 5,000 |

El resto de campos provienen de `BASE_INPUT` (capital, préstamo, equipamiento, etc.) que son fijos en el Simulador actual.

### 1.3 Flujo actual

```
Slider change → debounce 400ms → POST /api/accounting/setup
                                   (InvestmentInput completo)
                                        ↓
                                   FinancialStatementService.run_simulation()
                                        ↓
                                   FinancialReportResponse
                                        ↓
                                   Render KPIs + Payback/VAN/TIR
                                        ↓
                              [Guarda] → ScenarioSnapshot en useState local
```

---

## 2. Modelo de Datos

### 2.1 Tabla `scenarios`

```sql
CREATE TABLE scenarios (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    -- Identificación
    name            VARCHAR(100) NOT NULL,
    
    -- Snapshot completo de InvestmentInput
    input_data      JSONB NOT NULL,
    
    -- Resultados calculados (cache para no re-ejecutar setup)
    results         JSONB,
    
    -- Metadatos
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices
CREATE INDEX idx_scenarios_company ON scenarios(company_id);
CREATE INDEX idx_scenarios_company_user ON scenarios(company_id, user_id);
```

### 2.2 Forma del JSONB

#### `input_data` (InvestmentInput completo)

```json
{
  "capital": 50000,
  "loan_amount": 30000,
  "loan_rate_annual": 0.125,
  "loan_term_months": 24,
  "equipment_cost": 15000,
  "furniture_cost": 5000,
  "computer_cost": 3000,
  "software_cost": 1000,
  "guarantee_deposit": 3000,
  "initial_inventory": 5000,
  "monthly_sales": [29120, 29120, 29120, 29120, 29120, 29120, 29120, 29120, 29120, 29120, 29120, 29120],
  "monthly_cost_pct": 0.40,
  "monthly_rent": 2500,
  "monthly_utilities": 800,
  "monthly_salaries": 5000,
  "monthly_marketing": 500,
  "monthly_admin": 300,
  "monthly_maintenance": 200,
  "equipment_life_years": 8,
  "furniture_life_years": 10,
  "computer_life_years": 5,
  "software_life_years": 3,
  "months": 12,
  "start_date": "2026-01-01"
}
```

#### `results` (cache de FinancialReportResponse)

```json
{
  "income_statement": {
    "period": "2026-12",
    "revenue": 29120.0,
    "cost_of_sales": 11648.0,
    "gross_profit": 17472.0,
    "gross_margin_pct": 60.0,
    "operating_expenses": {
      "salaries": 60000.0,
      "operations": 30000.0,
      "marketing": 6000.0,
      "admin": 3600.0
    },
    "depreciation": 3600.0,
    "financial_expenses": 3600.0,
    "ebitda": 80400.0,
    "ebit": 76800.0,
    "operating_margin_pct": 25.6,
    "income_before_tax": 73200.0,
    "income_tax": 21594.0,
    "net_income": 51606.0,
    "net_margin_pct": 17.2
  },
  "ratios": [
    {"name": "Payback", "value": 18.5, "target": "≤ 24 meses", "traffic_light": "green", "formula": "Inversión / Flujo mensual"},
    {"name": "VAN", "value": 45000, "target": "> 0", "traffic_light": "green", "formula": "Σ flujos descontados"},
    {"name": "TIR", "value": 32.5, "target": "≥ 20%", "traffic_light": "green", "formula": "Tasa que hace VAN = 0"}
  ]
}
```

### 2.3 Validación de límite (4 escenarios por company)

```python
# Constante
MAX_SCENARIOS_PER_COMPANY = 4
```

Validación en el endpoint POST: contar escenarios activos de la company. Si >= 4 → 409 Conflict.

---

## 3. Schemas Pydantic

### 3.1 Request

```python
# app/schemas/simulator.py (nuevo archivo)

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class ScenarioCreate(BaseModel):
    """Crear un nuevo escenario guardado."""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del escenario")
    input_data: dict = Field(..., description="InvestmentInput completo (JSON)")
    results: dict | None = Field(None, description="Resultados cacheados (FinancialReportResponse)")


class ScenarioUpdate(BaseModel):
    """Actualizar nombre o results de un escenario existente."""
    name: str | None = Field(None, min_length=1, max_length=100)
    input_data: dict | None = None
    results: dict | None = None
```

### 3.2 Response

```python
class ScenarioResponse(BaseModel):
    """Escenario guardado."""
    id: int
    company_id: int
    user_id: int
    name: str
    input_data: dict
    results: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Lista de escenarios con metadatos."""
    scenarios: list[ScenarioResponse]
    total: int
    max_allowed: int = 4
```

---

## 4. Endpoints REST

| Método | Endpoint | Descripción | Auth | Tenant |
|--------|----------|-------------|------|--------|
| `POST` | `/api/simulator/scenarios` | Guardar nuevo escenario | JWT | X-Tenant-ID |
| `GET` | `/api/simulator/scenarios` | Listar escenarios de la company | JWT | X-Tenant-ID |
| `GET` | `/api/simulator/scenarios/{id}` | Obtener detalle de un escenario | JWT | X-Tenant-ID |
| `PUT` | `/api/simulator/scenarios/{id}` | Actualizar nombre/resultados | JWT | X-Tenant-ID |
| `DELETE` | `/api/simulator/scenarios/{id}` | Eliminar escenario | JWT | X-Tenant-ID |

### 4.1 POST `/api/simulator/scenarios`

**Request:**
```json
{
  "name": "Realista",
  "input_data": { /* InvestmentInput completo */ },
  "results": { /* FinancialReportResponse cache */ }
}
```

**Validaciones:**
- Cuenta escenarios de la company → si >= 4 → `409 Conflict: "Máximo 4 escenarios por empresa. Elimina uno antes de guardar."`
- `name` requerido, 1-100 chars
- `input_data` requerido, debe ser un objeto válido

**Response 201:**
```json
{
  "id": 1,
  "company_id": 1,
  "user_id": 2,
  "name": "Realista",
  "input_data": { ... },
  "results": { ... },
  "created_at": "2026-05-12T06:00:00Z",
  "updated_at": "2026-05-12T06:00:00Z"
}
```

### 4.2 GET `/api/simulator/scenarios`

**Response 200:**
```json
{
  "scenarios": [ /* ScenarioResponse[] */ ],
  "total": 2,
  "max_allowed": 4
}
```

### 4.3 GET `/api/simulator/scenarios/{id}`

**Response 200:** `ScenarioResponse`  
**Response 404:** `{ "detail": "Escenario no encontrado" }`

### 4.4 PUT `/api/simulator/scenarios/{id}`

Permite actualizar `name` y/o `results` (re-calcular después de editar sliders).

### 4.5 DELETE `/api/simulator/scenarios/{id}`

**Response 200:** `{ "status": "deleted", "id": 1 }`  
**Response 404:** `{ "detail": "Escenario no encontrado" }`

---

## 5. ORM Model (SQLAlchemy)

```python
# app/adapters/db/models/simulator.py (nuevo archivo)

from datetime import datetime
from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.models.accounting import Base


class Scenario(Base):
    """Escenario guardado del Simulador Financiero."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_scenarios_company", "company_id"),
    )
```

---

## 6. Migración Alembic

```bash
# Crear migración
cd apps/backend
alembic revision -m "0006_scenarios_table"
```

```python
# apps/backend/app/adapters/alembic/versions/0006_scenarios_table.py

"""scenarios: persistencia de escenarios del simulador

Revision ID: 0006
Revises: 0005_sales_tables
Create Date: 2026-05-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005_sales_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scenarios_company", "scenarios", ["company_id"])


def downgrade() -> None:
    op.drop_index("idx_scenarios_company", table_name="scenarios")
    op.drop_table("scenarios")
```

---

## 7. Servicio (Backend)

```python
# app/services/simulator_service.py (nuevo archivo)

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.adapters.db.models.simulator import Scenario

MAX_SCENARIOS = 4


class ScenarioService:

    @staticmethod
    async def create(
        db: AsyncSession,
        company_id: int,
        user_id: int,
        name: str,
        input_data: dict,
        results: dict | None = None,
    ) -> Scenario:
        # Validar límite
        count = await db.scalar(
            select(func.count(Scenario.id)).where(Scenario.company_id == company_id)
        )
        if count >= MAX_SCENARIOS:
            raise HTTPException(
                status_code=409,
                detail=f"Máximo {MAX_SCENARIOS} escenarios por empresa. Elimina uno antes de guardar."
            )

        scenario = Scenario(
            company_id=company_id,
            user_id=user_id,
            name=name,
            input_data=input_data,
            results=results,
        )
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        return scenario

    @staticmethod
    async def list_by_company(
        db: AsyncSession,
        company_id: int,
    ) -> list[Scenario]:
        result = await db.execute(
            select(Scenario)
            .where(Scenario.company_id == company_id)
            .order_by(Scenario.created_at.desc())
        )
        scenarios = result.scalars().all()
        return list(scenarios)

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        scenario_id: int,
        company_id: int,
    ) -> Scenario:
        result = await db.execute(
            select(Scenario).where(
                Scenario.id == scenario_id,
                Scenario.company_id == company_id,
            )
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise HTTPException(status_code=404, detail="Escenario no encontrado")
        return scenario

    @staticmethod
    async def update(
        db: AsyncSession,
        scenario_id: int,
        company_id: int,
        name: str | None = None,
        input_data: dict | None = None,
        results: dict | None = None,
    ) -> Scenario:
        scenario = await ScenarioService.get_by_id(db, scenario_id, company_id)
        if name is not None:
            scenario.name = name
        if input_data is not None:
            scenario.input_data = input_data
        if results is not None:
            scenario.results = results
        await db.commit()
        await db.refresh(scenario)
        return scenario

    @staticmethod
    async def delete(
        db: AsyncSession,
        scenario_id: int,
        company_id: int,
    ) -> None:
        scenario = await ScenarioService.get_by_id(db, scenario_id, company_id)
        await db.delete(scenario)
        await db.commit()
```

---

## 8. Router (Backend)

```python
# app/routers/simulator.py (nuevo archivo)

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas.simulator import (
    ScenarioCreate, ScenarioUpdate,
    ScenarioResponse, ScenarioListResponse,
)
from app.services.simulator_service import ScenarioService, MAX_SCENARIOS

router = APIRouter(prefix="/api/simulator", tags=["Simulador"])


@router.post("/scenarios", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ScenarioCreate,
):
    """Guarda un nuevo escenario del simulador (máx 4 por empresa)."""
    return await ScenarioService.create(
        db=db,
        company_id=tenant_id,
        user_id=int(current_user.id),
        name=data.name,
        input_data=data.input_data,
        results=data.results,
    )


@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista todos los escenarios guardados de la empresa."""
    scenarios = await ScenarioService.list_by_company(db, tenant_id)
    return ScenarioListResponse(
        scenarios=scenarios,
        total=len(scenarios),
        max_allowed=MAX_SCENARIOS,
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene el detalle de un escenario guardado."""
    return await ScenarioService.get_by_id(db, scenario_id, tenant_id)


@router.put("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ScenarioUpdate,
):
    """Actualiza nombre y/o resultados de un escenario."""
    return await ScenarioService.update(
        db=db,
        scenario_id=scenario_id,
        company_id=tenant_id,
        name=data.name,
        input_data=data.input_data,
        results=data.results,
    )


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(
    scenario_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina un escenario guardado."""
    await ScenarioService.delete(db, scenario_id, tenant_id)
    return {"status": "deleted", "id": scenario_id}
```

### Registro en `main.py`

```python
# Añadir en apps/backend/app/main.py
from app.routers.simulator import router as simulator_router
app.include_router(simulator_router)
```

---

## 9. Cambios en Frontend (Simulator.tsx)

### 9.1 Nuevos types y hook

```typescript
// apps/web/src/types/simulator.ts (nuevo archivo)

export interface ScenarioData {
  id: number;
  company_id: number;
  user_id: number;
  name: string;
  input_data: InvestmentInput;
  results: FinancialReportResponse | null;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  input_data: InvestmentInput;
  results?: FinancialReportResponse | null;
}

export interface ScenarioUpdate {
  name?: string;
  results?: FinancialReportResponse | null;
}

// apps/web/src/hooks/useScenarios.ts (nuevo archivo)
import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api/client";
import type { ScenarioData, ScenarioCreate, ScenarioUpdate } from "@/types/simulator";

export function useScenarios() {
  const { isAuthenticated } = useAuth();
  const [scenarios, setScenarios] = useState<ScenarioData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet("/api/simulator/scenarios");
      setScenarios(res.scenarios);
    } catch (err: any) {
      setError(err.message || "Error al cargar escenarios");
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const saveScenario = useCallback(async (data: ScenarioCreate) => {
    setError(null);
    try {
      const created = await apiPost("/api/simulator/scenarios", data);
      setScenarios(prev => [...prev, created]);
      return created;
    } catch (err: any) {
      setError(err.message || "Error al guardar escenario");
      throw err;
    }
  }, []);

  const updateScenario = useCallback(async (id: number, data: ScenarioUpdate) => {
    setError(null);
    try {
      const updated = await apiPut(`/api/simulator/scenarios/${id}`, data);
      setScenarios(prev => prev.map(s => s.id === id ? updated : s));
      return updated;
    } catch (err: any) {
      setError(err.message || "Error al actualizar escenario");
      throw err;
    }
  }, []);

  const deleteScenario = useCallback(async (id: number) => {
    setError(null);
    try {
      await apiDelete(`/api/simulator/scenarios/${id}`);
      setScenarios(prev => prev.filter(s => s.id !== id));
    } catch (err: any) {
      setError(err.message || "Error al eliminar escenario");
      throw err;
    }
  }, []);

  // Cargar al montar
  useEffect(() => {
    if (isAuthenticated) fetchScenarios();
  }, [isAuthenticated, fetchScenarios]);

  return {
    scenarios,
    loading,
    error,
    fetchScenarios,
    saveScenario,
    updateScenario,
    deleteScenario,
  };
}
```

### 9.2 Refactor de Simulator.tsx

Cambios mínimos requeridos:

1. **Reemplazar `useState<ScenarioSnapshot[]>` por `useScenarios()`**
2. **`saveScenario()` ahora hace POST al backend** en vez de `setScenarios(prev => [...prev, snapshot])`
3. **`deleteScenario()` ahora hace DELETE al backend**
4. **`clearScenarios()` se mantiene** (llamada múltiple a delete)
5. **Cargar escenarios al montar** (ya manejado por el hook)
6. **Manejar estado `loading` y `error`** del hook
7. **Mostrar indicador "máx 4 alcanzado"** vía `scenarios.length >= 4`

```typescript
// Cambio principal en Simulator.tsx
// ANTES:
const [scenarios, setScenarios] = useState<ScenarioSnapshot[]>([]);
const saveScenario = () => {
  const snapshot: ScenarioSnapshot = { ... };
  setScenarios((prev) => [...prev, snapshot]);
};

// DESPUÉS:
const { scenarios, loading: scenarioLoading, error: scenarioError,
        saveScenario: saveToBackend, deleteScenario: deleteFromBackend,
        fetchScenarios } = useScenarios();

const saveScenario = async () => {
  if (!incomeStmt || !result) return;
  await saveToBackend({
    name: nameForScenario(),
    input_data: buildCurrentInput(),
    results: result,
  });
};
```

---

## 10. Priorización y Esfuerzo Estimado

| Tarea | Esfuerzo | Prioridad | Dependencias |
|-------|----------|-----------|--------------|
| Crear modelo ORM `Scenario` | 15 min | P1 | Models existentes |
| Crear migración 0006 | 10 min | P1 | 0005_sales_tables |
| Crear schemas `simulator.py` | 15 min | P1 | Schemas existentes |
| Crear `ScenarioService` | 25 min | P1 | get_db |
| Crear `simulator.py` router | 20 min | P1 | ScenarioService |
| Registrar router en `main.py` | 2 min | P1 | — |
| Crear types frontend `simulator.ts` | 10 min | P2 | — |
| Crear hook `useScenarios.ts` | 20 min | P2 | AuthContext, api client |
| Refactor `Simulator.tsx` | 30 min | P2 | hook + types |
| Probar flujo completo | 15 min | P2 | Backend + Frontend |
| **TOTAL** | **~2.5 horas** | — | — |

**Clasificación:** 🟡 Media — bloquea la experiencia de usuario pero no la funcionalidad core.

---

## 11. Dependencias

| Dependencia | Estado | Nota |
|-------------|--------|------|
| Auth (JWT + X-Tenant-ID) | ✅ Implementado | Ya usado en los endpoints contables |
| `get_db` (AsyncSession) | ✅ Implementado | SQLAlchemy async |
| Alembic migrations | ✅ Implementado | Última: 0005_sales_tables |
| API client frontend | ✅ Implementado | `apiGet`, `apiPost`, etc. |
| `useAuth()` | ✅ Implementado | AuthContext |

**Sin dependencias bloqueantes.** Todo lo necesario ya existe.

---

## 12. Recomendación de Implementación

### Orden sugerido

1. **Backend primero** (modelo → migración → schemas → service → router)
2. **Probar con curl** los 5 endpoints
3. **Frontend** (types → hook → refactor Simulator.tsx)
4. **Test de integración** (guardar, recargar página, verificar persistencia)

### Decisiones de diseño

| Decisión | Opción elegida | Justificación |
|----------|---------------|---------------|
| Almacenar `results` cacheados | ✅ Sí | Evita re-ejecutar simulación al cargar escenarios (POST /setup es costoso: 152 asientos) |
| `user_id` nullable | ✅ Sí | Si un usuario se elimina, el escenario sobrevive (`ON DELETE SET NULL`) |
| `input_data` completo vs solo sliders | Completo | Guarda todo `InvestmentInput` — si en el futuro se añaden sliders, los escenarios viejos no se rompen |
| JSONB vs columnas | JSONB | Los datos son un snapshot opaco. No se consulta ni filtra por campos individuales del input |
| Límite 4 por company (no por user) | Por company | Los escenarios son compartidos entre usuarios del mismo tenant (todos ven la misma comparativa) |
| Endpoint `/api/simulator/scenarios` (no `/api/accounting/`) | Separado | El simulador es un módulo distinto con su propio prefijo; más limpio que mezclarlo en accounting |

### Edge cases cubiertos

- **409 al exceder 4 escenarios** — mensaje claro con instrucción
- **404 al acceder escenario de otra company** — filtrado por `company_id`
- **Auth requerido** — todos los endpoints usan `get_current_active_user`
- **Tenant isolation** — todos los endpoints usan `get_tenant_id`
- **Resultados nulos** — `results` es nullable; se puede crear sin haber simulado aún

---

**Fin de la Ficha Técnica**  
Documento guardado en: `/home/ron/projectos/IaaS-RonSys/docs/reports/scenarios-persistence.md`
