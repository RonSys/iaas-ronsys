# Informe de Arquitectura — IaaS-RonSys

> **Fecha:** 2026-05-13
> **Proyecto:** IaaS-RonSys — ERP SaaS con Agentes IA para Franquicia "El Segoviano"
> **Alcance:** Análisis de arquitectura diseñada vs. implementada, brechas, y propuesta de estructura modular ERP para dos dominios de negocio (compra/venta ferretería + venta comida restaurante).
> **Restricción:** No se modifica código. Solo análisis y propuesta.

---

## 1. Resumen Ejecutivo

El sistema IaaS-RonSys fue diseñado como un **monolito modular con arquitectura hexagonal (Ports & Adapters)** para soportar dos dominios de negocio: **ferretería/retail** (compra/venta) y **restaurante** (venta de comida). El análisis revela que la arquitectura hexagonal está **parcialmente implementada**: el dominio contable (`core/accounting/`) respeta el patrón, pero los dominios de inventario y ventas son **carpetas vacías** cuya lógica se filtró hacia `services/` y `core/accounting/`, rompiendo la regla de dependencias. El frontend carece de agrupación modular y la infraestructura DevOps tiene directorios designados vacíos.

**Hallazgos críticos:**
- `core/inventory/` y `core/sales/` están **vacíos** — la lógica de dominio está dispersa
- `services/sales_service.py` importa directamente modelos ORM desde `adapters/` — **viola hexagonal**
- No existe Repository pattern para ventas — el servicio hace queries SQLAlchemy directas
- `app/models/user.py` fuera de `adapters/` — inconsistencia estructural
- Frontend con routing plano (sin agrupación por módulo de negocio)
- `infra/compose/` y `scripts/` están **vacíos**
- Setup/branding se persiste en memoria (no sobrevive reinicio)
- RabbitMQ desplegado pero sin producer/consumer implementado
- Módulo de Agentes IA es un stub (`BaseSkill` ABC solamente)

---

## 2. Arquitectura Diseñada (según README.md)

```
IaaS-RonSys/
├── apps/
│   ├── backend/          ← FastAPI Monolito Modular + Hexagonal
│   │   └── app/
│   │       ├── core/     ← Dominio puro (sin dependencias externas)
│   │       │   ├── accounting/   ← Motor contable + Kárdex
│   │       │   ├── agents/       ← Sistema de skills IA
│   │       │   ├── inventory/    ← Gestión de inventarios
│   │       │   └── sales/        ← Ventas / POS
│   │       ├── adapters/ ← Implementaciones concretas (DB, APIs)
│   │       │   ├── db/models/        ← SQLAlchemy ORM models
│   │       │   ├── db/repositories/  ← Implementaciones de puertos
│   │       │   └── alembic/          ← Migraciones de BD
│   │       ├── routers/   ← Endpoints FastAPI
│   │       ├── schemas/   ← Pydantic (request/response)
│   │       ├── services/  ← Orquestación de lógica
│   │       └── monitoring/← Prometheus, health checks
│   ├── web/              ← React (frontend de gestión)
│   └── mobile/           ← React Native (app móvil)
├── infra/
│   ├── docker/           ← Dockerfiles personalizados
│   ├── compose/          ← Docker Compose por entorno
│   └── ci/               ← CI/CD pipelines
├── docs/
├── scripts/
└── .env.example
```

**Principios declarados:**
1. **Hexagonal (Ports & Adapters):** Dominio puro sin dependencias externas; adapters implementan los puertos.
2. **Monolito Modular:** Cada dominio de negocio es un módulo con su core, adapters, routers, schemas.
3. **Multi-tenant:** Aislamiento por `company_id` en todas las tablas.
4. **Two Business Domains:** Restaurante + Ferretería/retail con especialización por `business_type`.

---

## 3. Arquitectura Implementada (estado actual)

### 3.1 Backend — Estructura real

```
apps/backend/app/
├── core/
│   ├── accounting/        ✅ IMPLEMENTADO (6 archivos)
│   │   ├── engine.py      ← Motor contable (45K+ chars, completo)
│   │   ├── kardex.py      ← Promedio ponderado
│   │   ├── cashflow.py    ← Proyección/real/comparativo
│   │   ├── ports.py       ← Interfaces abstractas (puertos)
│   │   ├── ratios.py      ← Ratios financieros
│   │   └── statements.py  ← Estados financieros
│   ├── agents/            ⚠️ STUB (solo BaseSkill ABC)
│   │   └── base.py
│   ├── inventory/         ❌ VACÍO (0 archivos)
│   ├── sales/             ❌ VACÍO (0 archivos)
│   ├── dependencies.py    ← DI para FastAPI
│   ├── rate_limit.py
│   ├── security.py
│   └── tenant.py
│
├── adapters/
│   ├── db/models/
│   │   ├── accounting.py  ← Company, Account, JournalEntry*, Product, KardexMovement, CashflowProjection
│   │   ├── sales.py       ← PosSession, Sale, SaleItem, SalePayment, RestaurantSale, HardwareSale
│   │   └── simulator.py   ← Modelos de simulación
│   ├── db/repositories/
│   │   ├── accounting.py  ✅ Repository para accounting
│   │   └── user.py        ✅ Repository para user
│   └── alembic/           ✅ Migraciones funcionales
│
├── models/                ❌ INCONSISTENCIA — fuera de adapters
│   └── user.py            ← Modelo User fuera de la estructura designada
│
├── routers/               ⚠️ PLANO — sin agrupación por dominio
│   ├── accounting.py
│   ├── admin.py
│   ├── auth.py
│   ├── health.py
│   ├── sales.py
│   ├── setup.py
│   └── simulator.py
│
├── schemas/
├── services/
│   ├── sales_service.py   ❌ ROMPE HEXAGONAL — importa ORM directamente
│   ├── kardex_service.py
│   ├── setup_service.py
│   └── simulator_service.py
│
├── monitoring/
└── main.py
```

### 3.2 Frontend — Estructura real

```
apps/web/src/
├── pages/                  ⚠️ PLANO — sin agrupación por módulo
│   ├── Dashboard.tsx
│   ├── SetupWizard.tsx
│   ├── Simulator.tsx
│   ├── Reports.tsx
│   ├── Kardex.tsx
│   ├── Settings.tsx
│   ├── Login.tsx
│   ├── Cashflow.tsx
│   ├── Pos.tsx
│   ├── SalesNew.tsx
│   └── SalesListPage.tsx
│
├── components/
│   ├── auth/
│   ├── dashboard/
│   ├── layout/
│   │   └── AppShell.tsx   ← Nav: Dashboard, Setup, Simulador, Reportes, Kárdex, Cashflow, Caja, Nueva Venta, Ventas, Ajustes, Salir
│   ├── pos/
│   ├── sales/
│   └── ui/
│
├── contexts/
├── hooks/                  ← 6 hooks (useAccounting, useCompanySettings, usePalette, usePosSession, useSales, useScenarios)
├── services/
│   └── api.ts             ← Cliente HTTP con interceptor auth
└── types/
```

### 3.3 Infraestructura — Estado real

| Componente | Diseñado | Implementado | Estado |
|---|---|---|---|
| PostgreSQL 16 + pgvector | ✅ | ✅ | Operativo |
| Redis 7 | ✅ | ✅ | Operativo |
| RabbitMQ 4 | ✅ | ✅ | Desplegado, sin código |
| Docker Compose base | ✅ | ✅ | `docker-compose.yml` |
| Compose dev/prod | `infra/compose/` | ❌ Vacío | No existe |
| CI/CD pipelines | `infra/ci/.github/` | ⚠️ Directorio existe | Sin workflows |
| Dockerfiles custom | `infra/docker/` | ✅ | backend/, web/, monitoring/ |
| Scripts auxiliares | `scripts/` | ❌ Vacío | No existe |
| App Móvil | `apps/mobile/` | ❌ Vacío | No existe |

---

## 4. Matriz de Desviaciones: Diseñado vs. Implementado

| # | Desviación | Severidad | Descripción |
|---|---|---|---|
| D-01 | `core/inventory/` vacío | **Alta** | La lógica de inventario (gestión de stock, alertas, reorden) no tiene dominio propio. La lógica de kárdex vive en `core/accounting/kardex.py` y `adapters/db/models/accounting.py` (Product, KardexMovement). |
| D-02 | `core/sales/` vacío | **Alta** | La lógica de ventas (POS, reglas de negocio, cálculos) está en `services/sales_service.py` en vez del dominio. |
| D-03 | `services/sales_service.py` importa ORM | **Alta** | Importa directamente desde `adapters/db/models/sales.py` y `adapters/db/models/accounting.py`, violando la regla hexagonal de que el dominio no depende de adapters. |
| D-04 | Sin Repository para ventas | **Media** | No existe `adapters/db/repositories/sales.py`. El servicio hace `select()`, `db.execute()`, `db.add()` directamente con ORM. |
| D-05 | `models/user.py` fuera de adapters | **Baja** | Modelo User en `app/models/user.py` en vez de `app/adapters/db/models/`. Inconsistencia estructural. |
| D-06 | Routers planos | **Media** | Todos los routers están en un solo nivel sin agrupación por dominio (commercial/, restaurant/, shared/). |
| D-07 | Frontend routing plano | **Media** | 11 páginas en `src/pages/` sin subdirectorios por módulo de negocio. |
| D-08 | Setup en memoria | **Media** | `setup_service.py` y `setup.py` router persisten configuración en memoria — se pierde al reiniciar. |
| D-09 | `infra/compose/` vacío | **Media** | No hay `docker-compose.dev.yml` ni `docker-compose.prod.yml`. |
| D-10 | `scripts/` vacío | **Baja** | No hay scripts de seeding, migración, o utilidades. |
| D-11 | RabbitMQ sin código | **Baja** | Infraestructura desplegada pero sin producer/consumer ni colas definidas. |
| D-12 | Agentes IA es stub | **Baja** | Solo `BaseSkill` ABC sin skills concretas (deuda técnica #8). |
| D-13 | Mobile vacío | **Info** | `apps/mobile/` existe pero no tiene código — planificado para futuro. |

---

## 5. Análisis Detallado de Violaciones Hexagonales

### 5.1 La violación principal: `services/sales_service.py`

```
services/sales_service.py
  ├── from app.adapters.db.models.sales import PosSession, Sale, SaleItem, ...
  ├── from app.adapters.db.models.accounting import Company, JournalEntry, Product, ...
  └── Queries directas: select(Sale).where(...), db.add(sale), db.flush()
```

**Problema:** En arquitectura hexagonal, la capa de servicios (application layer) debe depender de **puertos abstractos** (interfaces), no de modelos ORM concretos. El flujo correcto sería:

```
core/sales/ports.py          ← AbstractSaleRepository (interface)
adapters/db/repositories/sales.py  ← SqlAlchemySaleRepository (implementación)
services/sales_service.py    ← Depende de AbstractSaleRepository, no de ORM
```

**Impacto:** No se puede cambiar de SQLAlchemy a otro ORM o base de datos sin reescribir el servicio. No se pueden hacer tests unitarios del servicio sin levantar una DB real.

### 5.2 Product y KardexMovement en accounting

Los modelos `Product` y `KardexMovement` están en `adapters/db/models/accounting.py` pero conceptualmente pertenecen al dominio de **inventario**. Esto crea un acoplamiento artificial entre contabilidad e inventario que dificultará la separación modular.

### 5.3 Feature flags sin persistencia

`useCompanySettings` en el frontend consulta feature flags (`tables_enabled`, `invoice_required`) pero el endpoint de setup (`/api/settings`) retorna datos en memoria. Al reiniciar el backend, las flags se pierden.

---

## 6. Navegación Actual del Frontend

Links en `AppShell.tsx` (header):

| Posición | Label | Ruta | Módulo conceptual |
|---|---|---|---|
| 1 | 📊 Dashboard | `/` | Pre-op / Operación |
| 2 | 🏗️ Setup | `/setup` | Pre-op |
| 3 | 🎮 Simulador | `/simulador` | Pre-op |
| 4 | 📋 Reportes | `/reportes` | Transversal |
| 5 | 📦 Kárdex | `/kardex` | Inventario |
| 6 | 💰 Cashflow | `/cashflow` | Finanzas |
| 7 | 🧾 Caja | (POS) | Ventas |
| 8 | ➕ Nueva Venta | `/ventas/nueva` | Ventas |
| 9 | 📋 Ventas | `/ventas` | Ventas |
| 10 | 🪑 Mesas | `/mesas` | Restaurante (feature flag) |
| 11 | ⚙️ Ajustes | `/settings` | Configuración |
| 12 | 🚪 Salir | (logout) | Transversal |

**Problemas observados:**
- Mezcla links de Pre-operación (Setup, Simulador) con Operación (Ventas, Caja, Kárdex)
- No hay separación visual entre dominios (comercial vs. restaurante)
- "Reportes" y "Ajustes" deberían ser módulos separados conectados a datos ERP
- "Salir" aparece solo en header, no es accesible desde sub-módulos

---

## 7. Propuesta: Estructura ERP Modular

### 7.1 Dos Fases Operativas

| Fase | Módulos | Descripción |
|---|---|---|
| **Pre-Operación** | Dashboard, Setup, Simulador, Reportes | Proyecto de inversión, simulación financiera, configuración inicial |
| **Operación (ERP)** | Ventas, Restaurante, Cocina/Producción, Compras, Inventario, Finanzas, Reportes, Configuración | Día a día del negocio |

### 7.2 Propuesta de Backend — Routers por Dominio

```
app/routers/
├── commercial/                 ← Dominio: Compra/Venta (ferretería, retail)
│   ├── __init__.py
│   ├── sales.py                ← Ventas POS ferretería
│   ├── purchases.py            ← Compras (NUEVO — no implementado)
│   ├── invoices.py             ← Boleta/Factura (NUEVO)
│   └── hardware_specialization.py  ← Especialización ferretería
│
├── restaurant/                 ← Dominio: Venta de Comida
│   ├── __init__.py
│   ├── sales.py                ← Ventas POS restaurante
│   ├── tables.py               ← Gestión de mesas
│   ├── kitchen.py              ← Cocina/Producción (NUEVO)
│   └── delivery.py             ← Delivery (NUEVO)
│
├── shared/                     ← Transversal
│   ├── __init__.py
│   ├── pos_sessions.py         ← Sesiones de caja (compartido)
│   ├── payments.py             ← Métodos de pago (compartido)
│   ├── kardex.py               ← Kárdex / Inventario
│   ├── accounting.py           ← Motor contable
│   ├── cashflow.py             ← Flujo de caja
│   └── reports.py              ← Reportes financieros + operativos
│
├── preop/                      ← Pre-Operación
│   ├── __init__.py
│   ├── setup.py                ← Setup wizard
│   └── simulator.py            ← Simulador financiero
│
├── admin.py                    ← Admin (auth, users, tenants)
├── auth.py                     ← Autenticación
└── health.py                   ← Health check
```

### 7.3 Propuesta de Backend — Core (Dominio)

```
app/core/
├── accounting/                 ✅ Ya implementado (mantener)
│   ├── engine.py
│   ├── kardex.py
│   ├── cashflow.py
│   ├── ports.py
│   ├── ratios.py
│   └── statements.py
│
├── inventory/                  ← RECONSTRUIR
│   ├── __init__.py
│   ├── ports.py                ← AbstractProductRepository, AbstractKardexRepository
│   ├── product_domain.py       ← Entidades de dominio: Product, StockAlert, ReorderRule
│   ├── kardex_domain.py        ← Entidades de dominio: KardexMovement, KardexEntry, KardexExit
│   └── stock_rules.py          ← Reglas de negocio: validación stock, alertas, reorden
│
├── sales/                      ← RECONSTRUIR
│   ├── __init__.py
│   ├── ports.py                ← AbstractSaleRepository, AbstractPosSessionRepository
│   ├── sale_domain.py          ← Entidades: Sale, SaleItem, SalePayment
│   ├── pos_domain.py           ← Entidades: PosSession, PosCloseResult
│   ├── pricing.py              ← Reglas de pricing, IGV, descuentos, igv_included
│   └── ticket.py               ← Formato de ticket (lógica de dominio)
│
├── agents/                     ← STUB (mantener para futuro)
│   └── base.py
│
├── dependencies.py
├── rate_limit.py
├── security.py
└── tenant.py
```

### 7.4 Propuesta de Backend — Adapters

```
app/adapters/
├── db/
│   ├── models/
│   │   ├── accounting.py       ✅ Mantener (JournalEntry, Account, CashflowProjection)
│   │   ├── inventory.py        ← NUEVO — mover Product, KardexMovement desde accounting.py
│   │   ├── sales.py            ✅ Mantener (Sale, SaleItem, SalePayment, PosSession, RestaurantSale, HardwareSale)
│   │   ├── user.py             ← MOVER desde app/models/user.py
│   │   └── simulator.py        ✅ Mantener
│   │
│   └── repositories/
│       ├── accounting.py       ✅ Mantener
│       ├── inventory.py        ← NUEVO — SqlAlchemyProductRepository, SqlAlchemyKardexRepository
│       ├── sales.py            ← NUEVO — SqlAlchemySaleRepository, SqlAlchemyPosSessionRepository
│       └── user.py             ✅ Mantener
│
└── alembic/                    ✅ Mantener
```

### 7.5 Propuesta de Frontend — Rutas y Páginas por Módulo

```
apps/web/src/
├── pages/
│   ├── preop/                          ← Pre-Operación
│   │   ├── Dashboard.tsx               ← / (dashboard de inversión)
│   │   ├── SetupWizard.tsx             ← /setup
│   │   └── Simulator.tsx              ← /simulador
│   │
│   ├── commercial/                     ← Dominio: Ferretería/Retail
│   │   ├── Pos.tsx                     ← /comercial/ventas/nueva
│   │   ├── SalesListPage.tsx           ← /comercial/ventas
│   │   ├── PurchasesPage.tsx           ← /comercial/compras (NUEVO)
│   │   └── InvoicesPage.tsx            ← /comercial/facturacion (NUEVO)
│   │
│   ├── restaurant/                     ← Dominio: Restaurante
│   │   ├── RestaurantPos.tsx           ← /restaurante/ventas/nueva (NUEVO)
│   │   ├── TablesPage.tsx              ← /restaurante/mesas
│   │   ├── KitchenPage.tsx             ← /restaurante/cocina (NUEVO)
│   │   └── DeliveryPage.tsx            ← /restaurante/delivery (NUEVO)
│   │
│   ├── inventory/                      ← Inventario (compartido)
│   │   ├── Kardex.tsx                  ← /inventario/kardex
│   │   ├── ProductsPage.tsx            ← /inventario/productos (NUEVO)
│   │   └── StockAlertsPage.tsx         ← /inventario/alertas (NUEVO)
│   │
│   ├── finance/                        ← Finanzas (compartido)
│   │   ├── Cashflow.tsx                ← /finanzas/cashflow
│   │   ├── AccountingPage.tsx          ← /finanzas/contabilidad (NUEVO)
│   │   └── CajaPage.tsx                ← /finanzas/caja
│   │
│   ├── reports/                        ← Reportes (módulo separado, conectado a ERP data)
│   │   ├── Reports.tsx                 ← /reportes
│   │   ├── FinancialReports.tsx        ← /reportes/financieros (NUEVO)
│   │   └── SalesReports.tsx            ← /reportes/ventas (NUEVO)
│   │
│   ├── settings/                       ← Configuración (módulo separado)
│   │   ├── Settings.tsx                ← /configuracion
│   │   ├── BrandingPage.tsx            ← /configuracion/marca (NUEVO)
│   │   └── UsersPage.tsx               ← /configuracion/usuarios (NUEVO)
│   │
│   └── auth/
│       └── Login.tsx                   ← /login
│
├── components/
│   ├── layout/
│   │   └── AppShell.tsx               ← Rediseñar nav con agrupación por fase/módulo
│   ├── commercial/                     ← Componentes ferretería
│   ├── restaurant/                     ← Componentes restaurante
│   ├── inventory/                      ← Componentes inventario
│   ├── finance/                        ← Componentes finanzas
│   ├── ui/                             ← Componentes compartidos
│   └── auth/
│
└── hooks/                              ← Mantener + agregar hooks por módulo
    ├── useAccounting.ts
    ├── useCompanySettings.ts
    ├── usePalette.ts
    ├── usePosSession.ts
    ├── useSales.ts
    └── useScenarios.ts
```

### 7.6 Propuesta de Navegación — AppShell Rediseñado

```
┌─────────────────────────────────────────────────────────────────┐
│ 🐟 El Segoviano                    [Salir] ← SIEMPRE visible   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ▸ Pre-Operación                                                 │
│   📊 Dashboard  │  🏗️ Setup  │  🎮 Simulador                  │
│                                                                 │
│ ▸ Operación                                                     │
│   🏪 Comercial    │  🍽️ Restaurante                            │
│     🧾 Nueva Venta  │  ➕ Nueva Venta                           │
│     📋 Ventas       │  📋 Ventas                                │
│     🛒 Compras      │  🪑 Mesas                                 │
│     🧾 Facturación  │  🍳 Cocina                                │
│                     │  🛵 Delivery                               │
│                                                                 │
│ ▸ Compartido                                                    │
│   📦 Inventario  │  💰 Finanzas  │  📋 Reportes  │  ⚙️ Config  │
│     📦 Kárdex      │  💰 Cashflow  │              │  ⚙️ Marca   │
│     📋 Productos   │  🧾 Caja     │              │  👥 Usuarios │
│     ⚠️ Alertas     │  📒 Contab.  │              │              │
│                                                                 │
│                                          [🚪 Salir]             │
└─────────────────────────────────────────────────────────────────┘
```

**Regla:** El botón **"Salir"** debe aparecer en TODAS las tabs/módulos/submódulos, tanto en desktop como mobile.

---

## 8. Plan de Migración Sugerido (por fases)

### Fase 1: Corregir violaciones hexagonales (prioridad alta)

1. **Crear `core/sales/ports.py`** con interfaces abstractas:
   - `AbstractSaleRepository` (crear, listar, detalle, anular)
   - `AbstractPosSessionRepository` (abrir, cerrar, obtener activa)
   - `AbstractPaymentRepository` (registrar pagos)

2. **Crear `core/inventory/ports.py`** con interfaces abstractas:
   - `AbstractProductRepository` (get, update_stock)
   - `AbstractKardexRepository` (registrar_movimiento, obtener_movimientos)

3. **Crear `adapters/db/repositories/sales.py`** y `adapters/db/repositories/inventory.py`** implementando los puertos.

4. **Refactorizar `services/sales_service.py`** para depender de los puertos abstractos, no de ORM directamente.

5. **Mover `Product` y `KardexMovement`** de `adapters/db/models/accounting.py` a `adapters/db/models/inventory.py`.

6. **Mover `app/models/user.py`** a `adapters/db/models/user.py`.

### Fase 2: Reorganizar routers por dominio (prioridad media)

7. Crear estructura `routers/commercial/`, `routers/restaurant/`, `routers/shared/`, `routers/preop/`.
8. Mover routers existentes a sus respectivos subdirectorios.
9. Actualizar `main.py` para incluir routers desde la nueva estructura.

### Fase 3: Reorganizar frontend por módulo (prioridad media)

10. Crear subdirectorios en `pages/` por módulo de negocio.
11. Rediseñar `AppShell.tsx` con navegación agrupada por fase (Pre-op / Operación).
12. Garantizar que "Salir" aparezca en todos los niveles.

### Fase 4: Persistir configuración (prioridad media)

13. Crear tabla `company_settings` en DB para feature flags y branding.
14. Refactorizar `setup_service.py` para leer/escribir desde DB.
15. Actualizar `useCompanySettings` para consumir endpoint persistido.

### Fase 5: Completar infraestructura (prioridad baja)

16. Crear `infra/compose/docker-compose.dev.yml` y `docker-compose.prod.yml`.
17. Implementar producer/consumer para RabbitMQ (eventos de dominio).
18. Crear scripts de seeding en `scripts/`.

### Fase 6: Agentes IA (excluido del alcance actual)

- No se trabaja en la creación de Agentes IA en esta iteración.
- El stub `core/agents/base.py` se mantiene como deuda técnica #8.

---

## 9. Modelo de Datos — Tablas Existentes vs. Propuestas

### 9.1 Tablas existentes (en DB)

| Tabla | Ubicación ORM | Dominio conceptual |
|---|---|---|
| `companies` | `adapters/db/models/accounting.py` | Multi-tenant |
| `accounts` | `adapters/db/models/accounting.py` | Contabilidad |
| `journal_entries` | `adapters/db/models/accounting.py` | Contabilidad |
| `journal_entry_lines` | `adapters/db/models/accounting.py` | Contabilidad |
| `products` | `adapters/db/models/accounting.py` | **Inventario** (mal ubicado) |
| `kardex_movements` | `adapters/db/models/accounting.py` | **Inventario** (mal ubicado) |
| `cashflow_projections` | `adapters/db/models/accounting.py` | Finanzas |
| `pos_sessions` | `adapters/db/models/sales.py` | Ventas (compartido) |
| `sales` | `adapters/db/models/sales.py` | Ventas |
| `sale_items` | `adapters/db/models/sales.py` | Ventas |
| `sale_payments` | `adapters/db/models/sales.py` | Ventas |
| `restaurant_sales` | `adapters/db/models/sales.py` | Restaurante |
| `hardware_sales` | `adapters/db/models/sales.py` | Ferretería |
| `users` | `app/models/user.py` | Auth (**mal ubicado**) |

### 9.2 Tablas propuestas (nuevas)

| Tabla | Dominio | Propósito |
|---|---|---|
| `company_settings` | Multi-tenant | Persistir feature flags, branding, configuración |
| `purchases` | Compras | Órdenes de compra (ferretería) |
| `purchase_items` | Compras | Ítems de compra |
| `suppliers` | Compras | Proveedores |
| `kitchen_orders` | Restaurante | Pedidos de cocina con estados |
| `tables` | Restaurante | Mesas con estado (libre/ocupada/reservada) |
| `delivery_orders` | Restaurante | Pedidos delivery con tracking |
| `stock_alerts` | Inventario | Alertas de stock mínimo/reorden |
| `inventory_counts` | Inventario | Toma de inventario físico |

---

## 10. Dependencias entre Módulos

```
                    ┌─────────────┐
                    │   Auth/     │
                    │   Users     │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐
    │  Commercial│   │  Restaurant │   │  Pre-Op   │
    │  (ventas,  │   │  (mesas,    │   │ (setup,   │
    │  compras,  │   │  cocina,    │   │ simulador)│
    │  facturac.)│   │  delivery)  │   └───────────┘
    └─────┬──────┘   └──────┬──────┘
          │                 │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │    Shared /     │
          │  Transversal    │
          │  ┌───────────┐  │
          │  │ Inventario│  │
          │  │ (kárdex,  │  │
          │  │  stock)   │  │
          │  └─────┬─────┘  │
          │  ┌─────▼─────┐  │
          │  │Contabilidad│  │
          │  │ (asientos, │  │
          │  │  estados)  │  │
          │  └─────┬─────┘  │
          │  ┌─────▼─────┐  │
          │  │  Finanzas │  │
          │  │ (cashflow,│  │
          │  │   caja)   │  │
          │  └───────────┘  │
          │                 │
          │  ┌───────────┐  │
          │  │ Reportes  │  │
          │  │ (conecta  │  │
          │  │  a todo)  │  │
          │  └───────────┘  │
          │                 │
          │  ┌───────────┐  │
          │  │ Config/   │  │
          │  │ Branding  │  │
          │  └───────────┘  │
          └─────────────────┘
```

**Principio:** Commercial y Restaurant dependen de Shared (inventario → contabilidad → finanzas). Reportes y Configuración son consumidores de datos de todos los módulos. Pre-Op es independiente del ERP operativo.

---

## 11. Métricas de Cobertura por Dominio

| Dominio | Core | Adapter/Repo | Router | Service | Frontend | Cobertura |
|---|---|---|---|---|---|---|
| **Contabilidad** | ✅ 6 archivos | ✅ 1 repo | ✅ 1 router | ✅ | ✅ | **90%** |
| **Ventas/POS** | ❌ Vacío | ❌ Sin repo | ✅ 1 router | ⚠️ Rompe hexagonal | ✅ 3 páginas | **40%** |
| **Inventario** | ❌ Vacío | ❌ Sin repo | ❌ Sin router | ✅ kardex_service | ⚠️ 1 página | **25%** |
| **Finanzas** | ✅ (en accounting) | ✅ (en accounting) | ❌ Sin router propio | ✅ | ⚠️ 1 página | **50%** |
| **Restaurante** | ❌ Vacío | ❌ Sin repo | ❌ Sin router | ❌ | ❌ Sin páginas específicas | **10%** |
| **Compras** | ❌ No existe | ❌ No existe | ❌ No existe | ❌ | ❌ | **0%** |
| **Agentes IA** | ⚠️ Stub | ❌ | ❌ | ❌ | ❌ | **5%** |
| **Auth** | ✅ security.py | ✅ user repo | ✅ auth router | ✅ | ✅ Login | **80%** |

---

## 12. Recomendaciones para el Arquitecto

1. **Priorizar la corrección hexagonal** (Fase 1) antes de agregar nuevos features — cada nuevo módulo escrito sobre ORM directo amplifica la deuda técnica.
2. **Separar `Product` y `KardexMovement`** del módulo accounting — son conceptos de inventario, no contabilidad.
3. **Definir contratos (ports) antes de implementar** — cada nuevo módulo (Compras, Cocina, Delivery) debe empezar con `core/{domain}/ports.py`.
4. **Event-driven para integración** — usar RabbitMQ (ya desplegado) para eventos entre módulos: `SaleCreated`, `KardexMovementRegistered`, `KitchenOrderReady`.
5. **API versioning** — al reorganizar routers por dominio, introducir `/api/v1/comercial/`, `/api/v1/restaurante/`, etc.

## 13. Recomendaciones para el Product Owner

1. **Definir MVP del dominio Restaurante** — actualmente solo existe la tabla `restaurant_sales` como especialización de Sale. Falta: gestión de mesas, pedidos de cocina, delivery.
2. **Definir MVP del dominio Compras** — no existe nada. Para ferretería, las compras son tan críticas como las ventas.
3. **Priorizar persistencia de configuración** — sin ella, cada reinicio pierde feature flags y branding.
4. **Decidir alcance del botón "Salir"** — la spec dice "debe aparecer en TODAS las tabs/módulos/submódulos". Validar si aplica también a sub-vistas modales.
5. **Planificar transición Pre-Op → Operación** — definir qué datos del Simulador se migran al ERP operativo (plan de cuentas, proyecciones iniciales, etc.).

---

*Fin del informe.*
