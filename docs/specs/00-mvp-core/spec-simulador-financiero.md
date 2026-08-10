# SPEC — Simulador Financiero y Escenarios (MVP Core)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción, migración `0006`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: todos los tenants; planificador de inversión
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

El simulador financiero permite modelar una inversión (activos, financiamiento, ventas
proyectadas) y obtener la simulación contable a 12 meses: asientos, estados financieros,
ratios y flujo de caja. Los **escenarios** se guardan por tenant para comparar alternativas.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Modelo `Scenario` | `app/adapters/db/models/simulator.py` | ✅ Implementado |
| Migración `0006_scenarios` | `app/adapters/alembic/versions/0006_scenarios.py` | ✅ Aplicada en prod |
| Router CRUD escenarios | `app/routers/simulator.py` (108 ln) | ✅ Desplegado |
| Service | `app/services/simulator_service.py` (124 ln) | ✅ Implementado |
| Input de inversión (InvestmentInput) | `app/core/accounting/engine.py` `InvestmentVariables` (L257) | ✅ Implementado |
| Frontend Simulador | `apps/web/src/pages/Simulator.tsx` + ruta `/simulador` | ✅ Desplegado |
| E2E | `apps/web/e2e/simulador.spec.ts` | ✅ 1 spec |

### 2.2 Endpoints (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/simulator/scenarios` | Crear escenario (201) |
| GET | `/api/simulator/scenarios` | Listar escenarios del tenant |
| GET | `/api/simulator/scenarios/{id}` | Detalle |
| PUT | `/api/simulator/scenarios/{id}` | Actualizar |
| DELETE | `/api/simulator/scenarios/{id}` | Eliminar |

### 2.3 Flujo (verificado)

```
POST /api/simulator/scenarios
  → guarda Scenario (InvestmentInput serializado)
  → (el cálculo en vivo usa el motor contable — ver spec motor-contable §2.2)
```

El simulador reutiliza `InvestmentVariables` + `engine.generate_*` del motor contable
(simulación 12 meses con depreciación, intereses, IR 29.5%, partida doble).

### 2.4 Criterios de aceptación (verificados)

- CA1: CRUD de escenarios aislado por tenant. ✅
- CA2: escenario guarda InvestmentInput completo. ✅
- CA3: frontend `/simulador` muestra y ejecuta la simulación. ✅
- CA4: e2e `simulador.spec.ts` cubre el flujo principal. ✅

---

## 3. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Modelo + migración | `simulator.py` modelo + `0006` | §2.1 |
| Router | `app/routers/simulator.py` | §2.2 |
| Service | `app/services/simulator_service.py` | §2.1 |
| Motor de simulación | `app/core/accounting/engine.py` | §2.3 |
| Frontend | `apps/web/src/pages/Simulator.tsx` | §2.1 |
| E2E | `apps/web/e2e/simulador.spec.ts` | §2.1 |

> ⚠️ Si cambias el modelo de escenarios, el CRUD o el input de inversión, **actualiza esta spec** (Spec Anchor).
