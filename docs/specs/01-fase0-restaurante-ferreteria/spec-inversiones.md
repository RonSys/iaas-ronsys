# SPEC — Módulo de Inversiones (Items de Inversión y Reportes)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción, migración `0013`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: tenants restaurante (El Segoviano); reportes de inversión
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

El módulo de inversiones registra **items de inversión** (activos/mejoras del local, ej:
upgrade dark kitchen) y genera el **reporte de inversión** con resumen y métricas
(`/reportes` en el frontend). Se integra con la simulación financiera (spec 00-simulador).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Modelo `InvestmentItem` | `app/adapters/db/models/restaurant.py` (L342) | ✅ Implementado |
| Migración `0013_investment_items` | `app/adapters/alembic/versions/0013_investment_items.py` | ✅ Aplicada en prod |
| Router inversión | `app/routers/investment.py` (97 ln) | ✅ Desplegado |
| Service | `app/services/investment_service.py` (275 ln) | ✅ Implementado |
| Frontend | `pages/restaurante/InvestmentPage.tsx`, `pages/Reports.tsx` (ruta `/inversiones/reportes`) | ✅ Desplegado |
| Tests | `test_caso7_investment.py` | ✅ 1 archivo |

### 2.2 Endpoints (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/restaurant/investment` | Listar items |
| POST | `/api/v1/restaurant/investment` | Crear item (201) |
| GET | `/api/v1/restaurant/investment/summary` | Resumen de inversión |
| GET | `/api/v1/restaurant/investment/{id}` | Detalle item |
| PUT | `/api/v1/restaurant/investment/{id}` | Actualizar item |
| DELETE | `/api/v1/restaurant/investment/{id}` | Eliminar item (204) |

### 2.3 Modelo de datos (verificado)

```sql
investment_items (
  id, tenant_id,
  name, description,
  amount numeric,           -- monto de la inversión
  category varchar,         -- ej: equipamiento, remodelación, marketing
  status varchar,           -- ej: planeado, en_progreso, completado
  date, created_at, updated_at
)
```

### 2.4 Criterios de aceptación (verificados)

- CA1: CRUD de items aislado por tenant. ✅
- CA2: `/summary` agrega montos por categoría/estado. ✅
- CA3: reporte en frontend `/inversiones/reportes` con métricas. ✅
- CA4: `test_caso7_investment.py` PASS. ✅

---

## 3. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Router | `app/routers/investment.py` | §2.2 |
| Service | `app/services/investment_service.py` | §2.1 |
| Modelo + migración | `models/restaurant.py`, `0013_investment_items` | §2.3 |
| Frontend | `InvestmentPage.tsx`, `Reports.tsx` | §2.1 |
| Tests | `test_caso7_investment.py` | §2.4 |

> ⚠️ Si cambias items de inversión, summary o reportes, **actualiza esta spec** (Spec Anchor).
