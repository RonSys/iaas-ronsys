Plan Integral de Integración de Módulos ERP — IaaS-RonSys

Versión: 3.0 (Final - con asignación de deudas técnicas por fase)
Fecha: 2026-05-13
Audiencia: Arquitecto de Sistemas, Product Owner, Equipo de Desarrollo
Propósito: Consolidar el análisis arquitectónico, identificar brechas, proponer la estructura modular definitiva para los dominios de negocio (ferretería/compra-venta y restaurante/venta de comida) y establecer un plan de migración por fases que asegure la entrega de las funcionalidades acordadas con el cliente, resolviendo las deudas técnicas en el orden correcto para no afectar el flujo de desarrollo.
Restricción: No se modifica código existente. Solo análisis y propuesta.

📑 Tabla de Contenidos

Resumen Ejecutivo

Arquitectura Diseñada vs. Realidad

Arquitectura Actual — Backend Detallado

Arquitectura Actual — Frontend Detallado

Stack Tecnológico Real

Hallazgos Críticos y Violaciones Hexagonales

Deudas Técnicas Agrupadas por Severidad con Fase de Resolución

Propuesta de Estructura ERP Modular — Backend

Propuesta de Estructura ERP Modular — Frontend

Propuesta de Navegación Definitiva (Sidebar Jerárquico)

Modelo de Datos — Tablas Existentes vs. Propuestas

Matriz de Cobertura por Dominio

Plan de Migración por Fases (Con todas las deudas asignadas)

Métricas de Éxito para el Próximo Hito

Recomendaciones para el Arquitecto y el Product Owner

Anexo: Resumen de Decisiones del Cliente

1. Resumen Ejecutivo

El sistema IaaS-RonSys fue diseñado como un monolito modular con arquitectura hexagonal (Ports & Adapters) para soportar dos dominios de negocio: ferretería/retail (compra/venta) y restaurante (venta de comida). El análisis de la implementación actual revela que:

    ✅ El 72% de la arquitectura diseñada se ha respetado. El módulo contable (core/accounting/) está completo y correctamente aislado, con puertos definidos, repositorios ORM y servicios orquestadores.

    ⚠️ Los dominios de ventas e inventario están incompletos o violan la arquitectura hexagonal. Las carpetas core/sales/ y core/inventory/ existen vacías; la lógica de negocio correspondiente se ha filtrado hacia services/sales_service.py y core/accounting/kardex.py, generando dependencias directas con el ORM.

    ⚠️ El frontend carece de organización modular. Las 11 páginas están en un directorio plano, sin agrupación por dominio de negocio, y la navegación es lineal, lo que colapsará cuando se agreguen los 20+ módulos ERP planificados.

    ⚠️ La infraestructura DevOps está incompleta. Directorios como infra/compose/, infra/ci/ y scripts/ existen vacíos.

    ⚠️ La configuración de branding y feature flags se persiste en memoria (se pierde al reiniciar el backend).

    ⚠️ No existe CI/CD, ni sistema de eventos (RabbitMQ) utilizado, ni dashboards de Grafana configurados.

Propuesta central: Se ha definido un plan de migración por fases que prioriza la entrega del MVP de Restaurante y Ferretería básica en la Fase 0, aceptando deudas técnicas temporales (cierre de comanda, delivery avanzado, facturación electrónica). Luego se corregirá la arquitectura hexagonal (Fase 1) y se completarán los módulos restantes (Fases 2-4). Este enfoque asegura que el cliente no pierda las funcionalidades críticas de restaurante y cocina, mientras se mantiene la calidad arquitectónica a largo plazo.

Las deudas técnicas se han asignado a fases específicas para no afectar el flujo de desarrollo:

    Las deudas críticas de arquitectura (D-01 a D-04, D-07 a D-09) se resuelven en Fase 1 (antes de agregar nuevos módulos).

    Las deudas funcionales acordadas con el cliente (D-05, D-06, D-20, D-21) se resuelven en Fase 2 o posteriores.

    Las deudas de infraestructura y mantenibilidad (D-10 a D-19) se resuelven en Fase 4.

Decisiones clave del cliente incorporadas:

    ✅ Multitenant: Cada empresa es un tenant separado (base de datos compartida con tenant_id).

    ✅ MVP Restaurante: Salones, menú, comandas (envío a cocina), takeaway, promociones básicas. Delivery avanzado en Fase 2.

    ✅ Seriales en inventario: Productos con trazabilidad individual (obligatorio desde Fase 0).

    ✅ Código de barras: Opcional, no requerido inicialmente. Solo campo barcode en la tabla products.

    ✅ Facturación electrónica: Genérica, pospuesta a V2 (Fase 3 o 4).

    ✅ Botón "Salir": Solo en el sidebar (no en modales), siempre visible.

2. Arquitectura Diseñada vs. Realidad
2.1 Estructura del Monorepo
| Ruta en README | Estado real | Brecha |
| --- | --- | --- |
| apps/backend/app/core/accounting/ | ✅ Implementado completo (engine.py, kardex.py, cashflow.py, ports.py, ratios.py, statements.py) | Ninguna |
| apps/backend/app/core/agents/ | 🟡 Solo base.py (puerto abstracto BaseSkill) | Sin skills concretas |
| apps/backend/app/core/inventory/ | ⚠️ Directorio VACÍO | Dominio de inventario no extraído |
| apps/backend/app/core/sales/ | ⚠️ Directorio VACÍO | Dominio de ventas no extraído |
| apps/backend/app/adapters/db/models/ | ✅ Implementado (accounting.py, sales.py, simulator.py) | Modelo User fuera de aquí (en app/models/user.py) |
| apps/backend/app/adapters/db/repositories/ | ✅ Implementado (accounting.py, user.py) | Falta repositorio para ventas e inventario |
| apps/backend/app/adapters/alembic/ | ✅ 6 migraciones funcionales | Ninguna |
| apps/backend/app/routers/ | ✅ 8 routers, pero planos (sin agrupación por dominio) | No existe commercial/, restaurant/, shared/ |
| apps/backend/app/schemas/ | ✅ Pydantic para auth, sales, simulator, init | Ninguna |
| apps/backend/app/services/ | ⚠️ sales_service.py viola hexagonal (importa ORM) | Dependencia incorrecta |
| apps/backend/app/monitoring/ | ✅ Prometheus middleware | Ninguna |
| apps/backend/tests/ | ✅ 9 test files, 66 tests | Faltan tests de integración HTTP |
| apps/web/ | ✅ React + Vite + TS implementado | Organización plana de páginas |
| apps/mobile/ | ❌ No implementado | Coherente con README ("futuro") |
| infra/docker/monitoring/ | ✅ Solo Prometheus config | Falta Grafana, Loki, AlertManager |
| infra/compose/ | ⚠️ Directorio VACÍO | No hay docker-compose.dev.yml ni prod.yml |
| infra/ci/.github/workflows/ | ⚠️ Directorio VACÍO | Sin CI/CD |
| scripts/ | ⚠️ Directorio VACÍO | Sin scripts auxiliares |
| docs/ | ✅ 19 archivos de documentación | Bien documentado |
2.2 Stack Tecnológico
| Componente | README | Realidad | Estado |
| --- | --- | --- | --- |
| Backend | FastAPI + Python 3.12 | ✅ FastAPI 0.115.x + Python 3.12.9 | ✅ |
| Frontend Web | React + Vite + Tailwind + TS | ✅ React 19 + Vite 6 + Tailwind 3.4 + TS 5.7 | ✅ |
| App Móvil | React Native + Expo | ❌ No implementado | ⏳ Pendiente |
| PostgreSQL | 16 + pgvector | ✅ PostgreSQL 16 (sin pgvector) | ✅ |
| ORM | SQLAlchemy + Alembic 2.0 | ✅ SQLAlchemy 2.0 + Alembic | ✅ |
| Redis | 7+ | ⚠️ Instalado en Docker, pero rate limiting usa fallback en memoria | ⚠️ Parcial |
| RabbitMQ | 4+ | ⚠️ Instalado en Docker, pero sin implementación de colas/eventos | ❌ No implementado |
| Prometheus | ✅ | ✅ Configurado | ✅ |
| Grafana | ✅ | ⚠️ En docker-compose, pero sin dashboards pre-configurados | ⚠️ Vacío |
| Loki | — | ❌ No configurado | ❌ |
| APM OpenTelemetry | — | ❌ No implementado | ❌ |
| AlertManager | — | ❌ No configurado | ❌ |
| LLM/IA | OpenAI/Claude API + LangChain | ❌ No implementado (solo puerto abstracto) | ❌ |
3. Arquitectura Actual — Backend Detallado
3.1 Diagrama de Capas (Realidad)
```text

┌──────────────────────────────────────────────────────────────────────────┐
│                          ROUTERS (FastAPI)                              │
│  /api/health  /api/auth/*  /api/admin/*  /api/accounting/*             │
│  /api/sales/*  /api/settings  /api/simulator/*                        │
│  (8 routers planos, sin agrupación por dominio)                        │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────────────┐
│                       SERVICES (orquestación)                            │
│  kardex_service.py  │  sales_service.py  │  setup_service.py           │
│  simulator_service.py                                                   │
│  ⚠️ sales_service.py importa ORM directo (violación hexagonal)         │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────────────┐
│                       CORE (dominio puro)                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Accounting       │  │ Agents           │  │ Inventory        │      │
│  │  engine.py       │  │  base.py         │  │  (VACÍO ⚠️)     │      │
│  │  kardex.py       │  └──────────────────┘  └──────────────────┘      │
│  │  statements.py   │  ┌──────────────────┐  ┌──────────────────┐      │
│  │  ratios.py       │  │ Sales            │  │ Security, Tenant│      │
│  │  cashflow.py     │  │  (VACÍO ⚠️)     │  │  rate_limit.py  │      │
│  │  ports.py        │  └──────────────────┘  └──────────────────┘      │
│  └──────────────────┘                                                 │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │
               ┌─────────────────────┼─────────────────────┐
               │                     │                     │
┌──────────────▼────────────┐ ┌─────▼──────┐ ┌────────────▼────────────┐
│       ADAPTERS (DB)       │ │ ADAPTERS   │ │     ADAPTERS (Cache)    │
│  db/models/               │ │ (Auth)     │ │    Redis (fallback)     │
│    accounting.py          │ │ Refresh    │ │    ⚠️ en memoria        │
│    sales.py               │ │ Token      │ └─────────────────────────┘
│    simulator.py           │ │ Model      │
│    user.py (❌ fuera)     │ └────────────┘
│  db/repositories/         │
│    accounting.py          │
│    user.py                │
│  alembic/ (6 migraciones) │
└────────────────────────────┘
```

3.2 Endpoints Implementados (Backend Real)
| Método | Ruta | Módulo |
| --- | --- | --- |
| GET | /api/health | Health |
| GET | /api/ready | Health |
| POST | /api/auth/login | Auth (JWT) |
| POST | /api/auth/refresh | Auth (refresh rotativo) |
| POST | /api/auth/logout | Auth (revocación) |
| GET | /api/auth/me | Auth (perfil) |
| POST | /api/admin/users | Admin (crear usuario) |
| GET | /api/admin/users | Admin (listar) |
| POST | /api/accounting/setup | Contabilidad (simulación) |
| GET | /api/accounting/bcss | Contabilidad (BCSS) |
| GET | /api/accounting/pyg | Contabilidad (PYG) |
| GET | /api/accounting/balance | Contabilidad (Balance) |
| GET | /api/accounting/ratios | Contabilidad (Ratios) |
| POST | /api/accounting/transaction | Contabilidad (transacción manual) |
| POST | /api/accounting/validate | Contabilidad (validación) |
| POST | /api/accounting/kardex/products | Kárdex (productos) |
| POST | /api/accounting/kardex/entry | Kárdex (entradas) |
| POST | /api/accounting/kardex/exit | Kárdex (salidas) |
| GET | /api/accounting/kardex/{code} | Kárdex (historial) |
| GET | /api/accounting/kardex/inventory/summary | Kárdex (resumen) |
| POST | /api/accounting/kardex/warehouse-close | Kárdex (cierre almacén) |
| POST | /api/sales/sessions/open | POS / Ventas |
| GET | /api/sales/sessions/current | POS / Ventas |
| POST | /api/sales/sessions/{id}/close | POS / Ventas |
| POST | /api/sales/sale | Ventas (crear venta) |
| GET | /api/sales/sales | Ventas (listar) |
| GET | /api/sales/sale/{id} | Ventas (detalle) |
| POST | /api/sales/sale/{id}/void | Ventas (anular) |
| GET | /api/sales/sale/{id}/ticket | Ventas (ticket) |
| GET | /api/sales/payment-methods | Ventas (métodos pago) |
| GET | /api/settings | Configuración / Branding |
| PATCH | /api/settings | Configuración / Branding |
| GET | /api/settings/palette | Configuración (paleta) |
| PATCH | /api/settings/palette | Configuración (paleta) |
| POST | /api/simulator/scenarios | Simulador (crear) |
| GET | /api/simulator/scenarios | Simulador (listar) |
3.3 Modelos de Base de Datos (Migraciones Alembic)
| Migración | Tablas creadas | Propósito |
| --- | --- | --- |
| 0001_initial_setup | companies, accounts, journal_entries, journal_lines, products | Setup inicial contable |
| 0002_users_auth | users, refresh_tokens | Auth + RBAC |
| 0003_business_type | companies.business_type (columna) | Tipo de negocio (retail/restaurant) |
| 0004_cashflow_projections | cashflow_projections | Proyecciones de flujo |
| 0005_sales_tables | sales, sale_items, sale_payments, pos_sessions, restaurant_sales, hardware_sales | Sales/POS |
| 0006_scenarios | simulation_scenarios | Escenarios del simulador |
4. Arquitectura Actual — Frontend Detallado
4.1 Estructura de Páginas (Realidad)
```text

apps/web/src/
├── pages/                          ← 11 páginas planas
│   ├── Login.tsx                   ← Ruta pública
│   ├── Dashboard.tsx               ← KPIs + gráficos
│   ├── SetupWizard.tsx             ← Formulario de inversión
│   ├── Simulator.tsx               ← Sliders + escenarios
│   ├── Reports.tsx                 ← PYG, Balance, BCSS, Ratios (datos del simulador)
│   ├── Kardex.tsx                  ← Inventario + movimientos
│   ├── Cashflow.tsx                ← Flujo de caja
│   ├── Pos.tsx                     ← Caja (sesión POS)
│   ├── SalesNew.tsx                ← Nueva venta
│   ├── SalesListPage.tsx           ← Listado de ventas
│   └── Settings.tsx                ← Branding / paleta
├── components/
│   ├── layout/
│   │   └── AppShell.tsx            ← Shell principal + navegación lineal
│   ├── auth/
│   ├── dashboard/
│   ├── pos/
│   ├── sales/
│   └── ui/
├── hooks/                          ← useAccounting, usePalette, useSales, etc.
├── services/
│   └── api.ts                      ← Cliente HTTP con interceptor auth
├── contexts/
│   └── AuthContext.tsx
└── types/
```

4.2 Navegación Actual (AppShell)
| Orden | Ruta | Etiqueta | Observación |
| --- | --- | --- | --- |
| 1 | / | 📊 Dashboard | Principal |
| 2 | /setup | 🏗️ Setup | Proyecto de inversión |
| 3 | /simulador | 🎮 Simulador | Proyecto de inversión |
| 4 | /reportes | 📋 Reportes | Reportes financieros (simulador, no datos reales) |
| 5 | /kardex | 📦 Kárdex | Módulo ERP |
| 6 | /cashflow | 💰 Cashflow | Módulo ERP |
| 7 | /caja | 🧾 Caja | POS / Ventas |
| 8 | /ventas/nueva | ➕ Nueva Venta | Ventas |
| 9 | /ventas | 📋 Ventas | Ventas |
| — | /settings | ⚙️ Ajustes | Configuración (branding) |
| — | logout | 🚪 Salir | Cerrar sesión (solo en header desktop) |
4.3 Problemas Identificados en Frontend

    Reportes financieros mezclados con simulador
    Reports.tsx obtiene datos del simulador (/api/accounting/pyg, etc.), no de transacciones reales del ERP. Cuando los módulos ERP generen ventas, compras e inventario real, los reportes financieros deben reflejar datos reales, no simulados.

    Rutas planas sin agrupación por dominio de negocio
    Las rutas actuales son /kardex, /cashflow, /caja, /ventas/nueva, /ventas. Deberían agruparse: /erp/inventario/*, /erp/ventas/*, /erp/finanzas/*.

    Menú lineal sin estructura jerárquica
    Cuando se agreguen módulos como Restaurante (Salones, Menú, Comandas, Delivery, TakeAway, Promociones), Cocina/Producción (Recetas, Órdenes, Mermas), Compras (Órdenes, Ingresos, Rechazos, Proveedores), la navegación lineal colapsará.

    Botón "Salir" no siempre visible
    En desktop aparece solo en el header; en mobile está dentro del menú hamburguesa. La especificación del cliente requiere que aparezca siempre en el sidebar (no en modales).

5. Stack Tecnológico Real
```yaml

backend:
  language: Python 3.12.9
  framework: FastAPI 0.115.x
  orm: SQLAlchemy 2.0.x + asyncpg
  auth: PyJWT[crypto] + pwdlib[argon2] (Argon2id)
  validation: Pydantic v2
  testing: pytest + pytest-asyncio + pytest-cov
  monitoring: prometheus-client

frontend:
  framework: React 19
  bundler: Vite 6
  styling: TailwindCSS 3.4
  language: TypeScript 5.7
  charts: Recharts
  routing: react-router-dom v7
  state: Zustand (authStore) + Context (AuthContext)
  testing: Jest + React Testing Library + Playwright E2E
  proxy: Vite server proxy → backend :8000

infrastructure:
  containers: Docker + Docker Compose
  database: PostgreSQL 16
  cache: Redis 7 (declared, no activo en rate limiting)
  queue: RabbitMQ 4 (declared, no implementado)
  monitoring: Prometheus (:9090), Grafana (:3000) sin dashboards
  environments: QA (:5173/:8001) + Production (Nginx :80/:8000)
  deploy: deploy.sh (idempotent, env-aware)
```

6. Hallazgos Críticos y Violaciones Hexagonales
6.1 La violación principal: services/sales_service.py
```python

# Código actual (simplificado)
from app.adapters.db.models.sales import PosSession, Sale, SaleItem, ...
from app.adapters.db.models.accounting import Company, JournalEntry, Product, ...

def create_sale(...):
    # Queries directas con ORM
    session = db.execute(select(PosSession).where(...))
    sale = Sale(...)
    db.add(sale)
    db.flush()
    # ...
```

Problema: En arquitectura hexagonal, la capa de servicios (application layer) debe depender de puertos abstractos (interfaces), no de modelos ORM concretos. El flujo correcto sería:
```text

core/sales/ports.py          ← AbstractSaleRepository (interface)
adapters/db/repositories/sales.py  ← SqlAlchemySaleRepository (implementación)
services/sales_service.py    ← Depende de AbstractSaleRepository, no de ORM
```

Impacto:

    No se puede cambiar de SQLAlchemy a otro ORM o base de datos sin reescribir el servicio.

    No se pueden hacer tests unitarios del servicio sin levantar una base de datos real.

    El dominio de ventas no está extraído, por lo que cualquier lógica de negocio compleja (descuentos por volumen, impuestos específicos, etc.) quedará atrapada en el servicio.

6.2 Product y KardexMovement en el módulo contable

Los modelos Product y KardexMovement están en adapters/db/models/accounting.py, pero conceptualmente pertenecen al dominio de inventario. Esto crea un acoplamiento artificial entre contabilidad e inventario que dificultará la separación modular.
6.3 Setup/Branding en memoria global
```python

# app/services/setup_service.py
_current_settings = { ... }  # Diccionario global
```

Cada reinicio del backend pierde la configuración de branding y feature flags. No es escalable para multi-tenant.
6.4 Modelo User fuera de adapters/db/models/
```python

# app/models/user.py (¡¡¡fuera de adapters!!!)
```

Inconsistencia estructural: debería estar en app/adapters/db/models/user.py.
6.5 Falta de repositorios específicos para ventas e inventario

No existen adapters/db/repositories/sales.py ni inventory.py, por lo que los servicios hacen queries SQLAlchemy directamente.
7. Deudas Técnicas Agrupadas por Severidad con Fase de Resolución
🔴 Críticas (deben resolverse antes de cualquier nuevo módulo, excepto lo acordado con el cliente)
| ID | Deuda | Impacto | Esfuerzo estimado | Fase de resolución |
| --- | --- | --- | --- | --- |
| D-01 | core/sales/ y core/inventory/ vacíos — dominio de ventas e inventario no extraído | Al agregar nuevos tipos de venta o almacenes, la lógica se dispersará | 2-3 días | Fase 1 |
| D-02 | services/sales_service.py importa ORM directamente — viola hexagonal | Dificulta el testeo unitario del dominio de ventas; acoplamiento a SQLAlchemy | 2 días | Fase 1 |
| D-03 | Setup/Branding en memoria global (_current_settings) — no persiste, no es multi-tenant | Cada reinicio pierde configuración; no escalable | 0.5 día | Fase 1 |
| D-04 | Reportes financieros integrados al simulador, no a datos reales del ERP | Cuando los módulos ERP generen datos reales, habrá que migrar los reportes | 1 día | Fase 1 |
| D-05 | Cierre de comanda solo al pagar (debe ser al cancelar pedido) — DT-REST-01 | Lógica de negocio incompleta | 0.5 día | Fase 2 |
| D-06 | Delivery sin repartidores, zonas, tracking — DT-REST-02 | Funcionalidad limitada | 2 días | Fase 2 |
🟡 Medias (prioridad alta después de las críticas)
| ID | Deuda | Impacto | Esfuerzo estimado | Fase de resolución |
| --- | --- | --- | --- | --- |
| D-07 | Frontend sin organización de rutas por dominio de negocio | Dificulta la navegación y escalabilidad al agregar módulos ERP | 2-3 días | Fase 1 |
| D-08 | Sin sidebar jerárquica — navegación lineal | Cuando haya 20+ módulos, colapsa | 2-3 días | Fase 1 |
| D-09 | Botón "Salir" solo en header desktop + menú mobile, no en todas las páginas | Requerimiento de negocio no cumplido | 0.25 día | Fase 1 |
| D-10 | Rate limiting con fallback en memoria (no Redis) | No escala con múltiples workers | 0.5 día | Fase 4 |
| D-11 | Auth requiere deploy con PostgreSQL real + Redis | Riesgo en producción (actualmente funcional pero en entorno controlado) | 1-2 días | Fase 4 |
| D-12 | Sin CI/CD (infra/ci/ vacío) | Despliegue manual con riesgo de error humano | 1-2 días | Fase 4 |
| D-13 | Grafana instalado sin dashboards pre-configurados | Monitoreo parcial | 1 día | Fase 4 |
| D-14 | Tests de integración HTTP (FastAPI TestClient) no existen | No se validan routers | 1-2 días | Fase 4 |
🟢 Bajas (pueden posponerse)
| ID | Deuda | Impacto | Esfuerzo estimado | Fase de resolución |
| --- | --- | --- | --- | --- |
| D-15 | Cashflow lógica embebida en statements.py en vez de módulo propio cashflow.py | Dificulta mantenimiento | 1-2 días | Fase 4 |
| D-16 | Sin Storybook, sin ESLint/Prettier configurados | Inconsistencias de estilo | 0.5 día | Fase 4 |
| D-17 | Sin Loki para logs centralizados | Dificulta debugging en producción | 1 día | Fase 4 |
| D-18 | Sin OpenTelemetry para trazas distribuidas | No hay visibilidad de latencia | 2 días | Fase 4 |
| D-19 | Mobile vacío (consistente con README, pero planificado para futuro) | — | — | Futuro |
| D-20 | Facturación electrónica (genérica) — DT-FERR-01 | Pospuesto a V2 | 1 día | Fase 3 o 4 (V2) |
| D-21 | Código de barras (escáner) — no requerido inicialmente | Solo campo barcode en tabla | 0.5 día | Fase 2 (opcional) |
📌 Resumen del orden de resolución de deudas
| Fase | Deudas que se resuelven | Tipo |
| --- | --- | --- |
| Fase 1 | D-01, D-02, D-03, D-04, D-07, D-08, D-09 | Arquitectura crítica + Frontend |
| Fase 2 | D-05, D-06, (D-21 opcional) | Funcionales acordadas con cliente |
| Fase 3 | D-20 (facturación electrónica) | V2 |
| Fase 4 | D-10 a D-18 | Infraestructura + Mantenibilidad |
| Futuro | D-19 | Mobile |
8. Propuesta de Estructura ERP Modular — Backend
8.1 Nuevos routers agrupados por dominio
```text

apps/backend/app/routers/
├── __init__.py
├── api.py                      ← Router principal que incluye a los demás
├── investment/                 ← 🏗️ Proyecto de inversión (pre-operación)
│   ├── __init__.py
│   ├── dashboard.py
│   ├── setup.py
│   ├── simulator.py
│   ├── accounting.py           ← Estados financieros (PYG, Balance, BCSS, Ratios)
│   └── reports.py              ← Reportes de inversión
│
├── commercial/                 ← 🏪 Dominio ferretería/retail
│   ├── __init__.py
│   ├── pos.py                  ← Caja rápida (takeaway, cuentas al instante)
│   ├── invoices.py             ← Facturación (salón, delivery)
│   ├── sales.py                ← Historial de ventas
│   ├── purchases.py            ← Órdenes de compra (NUEVO)
│   └── suppliers.py            ← Proveedores (NUEVO)
│
├── restaurant/                 ← 🍽️ Dominio venta de comida
│   ├── __init__.py
│   ├── tables.py               ← Mapa de mesas, estados, reservas
│   ├── menu.py                 ← Carta, modificadores
│   ├── orders.py               ← Comandas, pantalla de cocina
│   ├── delivery.py             ← Delivery, repartidores, zonas
│   ├── takeaway.py             ← Pedidos para llevar
│   └── promotions.py           ← Combos, menú del día, ofertas
│
├── production/                 ← 🧑‍🍳 Cocina / Producción
│   ├── __init__.py
│   ├── recipes.py              ← Fichas técnicas, explosión de insumos
│   ├── orders.py               ← Órdenes de producción
│   └── waste.py                ← Mermas, pérdidas
│
├── purchasing/                 ← 🛒 Compras (compartido entre dominios)
│   ├── __init__.py
│   ├── orders.py               ← Pedidos a proveedores
│   ├── receipts.py             ← Recepción de insumos
│   ├── returns.py              ← Devoluciones
│   └── suppliers.py            ← Proveedores
│
├── inventory/                  ← 📦 Inventario (compartido)
│   ├── __init__.py
│   ├── supplies.py             ← Insumos (materia prima, ingredientes)
│   ├── warehouses.py           ← Almacenes (bar, cocina fría, bodega)
│   ├── transfers.py            ← Traslados internos
│   ├── adjustments.py          ← Ajustes, mermas
│   └── counts.py               ← Conteos físicos cíclicos
│
├── finance/                    ← 💰 Finanzas operativas
│   ├── __init__.py
│   ├── payables.py             ← Cuentas por pagar
│   ├── treasury.py             ← Tesorería, arqueo, bancos
│   └── reconciliations.py      ← Conciliaciones
│
├── reports/                    ← 📊 Reportes del ERP (datos reales)
│   ├── __init__.py
│   ├── sales.py                ← Ventas (por plato, categoría, salón vs delivery)
│   ├── costs.py                ← Costos (por plato, márgenes)
│   ├── purchases.py            ← Compras
│   ├── inventory.py            ← Rotación, valorizado
│   └── finance.py              ← Financieros
│
├── shared/                     ← 🔧 Compartido (endpoints comunes)
│   ├── __init__.py
│   ├── inventory.py            ← Productos/insumos compartidos
│   ├── purchases.py            ← Compras compartidas
│   └── finance.py              ← Finanzas compartidas
│
├── config/                     ← ⚙️ Configuración general
│   ├── __init__.py
│   ├── company.py              ← Empresa
│   ├── branches.py             ← Sucursales
│   ├── users.py                ← Usuarios
│   ├── roles.py                ← Roles
│   ├── parameters.py           ← Parámetros (propinas, delivery fee, etc.)
│   └── branding.py             ← Branding (paleta, logo, favicon)
│
├── admin.py                    ← Admin (auth, tenants)
├── auth.py                     ← Autenticación
└── health.py                   ← Health check
```

8.2 Nuevos core por dominio
```text

apps/backend/app/core/
├── accounting/                 ✅ Mantener (no cambiar)
│   ├── engine.py
│   ├── kardex.py               ⚠️ Mover lógica de inventario a inventario/
│   ├── cashflow.py
│   ├── ports.py
│   ├── ratios.py
│   └── statements.py
│
├── agents/                     🟡 Mantener para futuro
│   └── base.py
│
├── inventory/                  🆕 Crear (extraer desde accounting/kardex.py)
│   ├── __init__.py
│   ├── ports.py                ← AbstractProductRepository, AbstractKardexRepository
│   ├── product_domain.py       ← Entidades: Product, StockAlert, ReorderRule
│   ├── kardex_domain.py        ← Entidades: KardexMovement, KardexEntry, KardexExit
│   └── stock_rules.py          ← Reglas: validación stock, alertas, reorden
│
├── sales/                      🆕 Crear (extraer desde services/sales_service.py)
│   ├── __init__.py
│   ├── ports.py                ← AbstractSaleRepository, AbstractPosSessionRepository
│   ├── sale_domain.py          ← Entidades: Sale, SaleItem, SalePayment
│   ├── pos_domain.py           ← Entidades: PosSession, PosCloseResult
│   ├── pricing.py              ← Reglas: descuentos, IGV, igv_included
│   └── ticket.py               ← Lógica de formato de ticket
│
├── purchasing/                 🆕 Crear (futuro)
├── production/                 🆕 Crear (futuro)
├── restaurant/                 🆕 Crear (futuro)
├── finance/                    🆕 Crear (futuro)
│
├── dependencies.py
├── rate_limit.py
├── security.py
└── tenant.py
```

8.3 Nuevos adapters
```text

apps/backend/app/adapters/
├── db/
│   ├── models/
│   │   ├── accounting.py       ✅ Mantener (JournalEntry, Account, CashflowProjection)
│   │   ├── inventory.py        🆕 Mover Product, KardexMovement aquí
│   │   ├── sales.py            ✅ Mantener (Sale, SaleItem, SalePayment, PosSession, RestaurantSale, HardwareSale)
│   │   ├── user.py             🆕 Mover User desde app/models/user.py
│   │   ├── purchasing.py       🆕 Crear (Order, Receipt, Return, Supplier)
│   │   ├── production.py       🆕 Crear (Recipe, ProductionOrder, Waste)
│   │   ├── restaurant.py       🆕 Crear (Table, MenuItem, KitchenOrder, DeliveryOrder, Promotion)
│   │   ├── finance.py          🆕 Crear (Payable, Treasury, Reconciliation)
│   │   ├── config.py           🆕 Crear (CompanySettings, Branch, Role, Parameter)
│   │   └── simulator.py        ✅ Mantener
│   │
│   └── repositories/
│       ├── accounting.py       ✅ Mantener
│       ├── inventory.py        🆕 Crear (SqlAlchemyProductRepository, SqlAlchemyKardexRepository)
│       ├── sales.py            🆕 Crear (SqlAlchemySaleRepository, SqlAlchemyPosSessionRepository)
│       ├── user.py             ✅ Mantener
│       ├── purchasing.py       🆕 Crear
│       ├── production.py       🆕 Crear
│       ├── restaurant.py       🆕 Crear
│       ├── finance.py          🆕 Crear
│       └── config.py           🆕 Crear
│
└── alembic/                    ✅ Mantener + migraciones para nuevas tablas
```

9. Propuesta de Estructura ERP Modular — Frontend
9.1 Páginas agrupadas por módulo
```text

apps/web/src/pages/
├── investment/                 ← 🏗️ Pre-operación (proyecto de inversión)
│   ├── Dashboard.tsx           ← / (dashboard de inversión)
│   ├── SetupWizard.tsx         ← /setup
│   ├── Simulator.tsx           ← /simulador
│   ├── AccountingReports.tsx   ← /reportes/inversion
│   └── InvestmentReports.tsx   ← /reportes/inversion (PYG, Balance, BCSS, Ratios)
│
├── commercial/                 ← 🏪 Ferretería/Retail
│   ├── Pos.tsx                 ← /comercial/ventas/nueva
│   ├── SalesListPage.tsx       ← /comercial/ventas
│   ├── PurchasesPage.tsx       ← /comercial/compras (NUEVO)
│   ├── InvoicesPage.tsx        ← /comercial/facturacion (NUEVO)
│   └── SuppliersPage.tsx       ← /comercial/proveedores (NUEVO)
│
├── restaurant/                 ← 🍽️ Restaurante
│   ├── RestaurantPos.tsx       ← /restaurante/ventas/nueva (NUEVO)
│   ├── TablesPage.tsx          ← /restaurante/mesas
│   ├── MenuPage.tsx            ← /restaurante/menu (NUEVO)
│   ├── KitchenOrdersPage.tsx   ← /restaurante/comandas (NUEVO)
│   ├── DeliveryPage.tsx        ← /restaurante/delivery (NUEVO)
│   ├── TakeAwayPage.tsx        ← /restaurante/takeaway (NUEVO)
│   └── PromotionsPage.tsx      ← /restaurante/promociones (NUEVO)
│
├── production/                 ← 🧑‍🍳 Cocina / Producción
│   ├── RecipesPage.tsx         ← /produccion/recetas (NUEVO)
│   ├── ProductionOrdersPage.tsx ← /produccion/ordenes (NUEVO)
│   └── WastePage.tsx           ← /produccion/mermas (NUEVO)
│
├── purchasing/                 ← 🛒 Compras (compartido)
│   ├── PurchaseOrdersPage.tsx  ← /compras/ordenes (NUEVO)
│   ├── ReceiptsPage.tsx        ← /compras/ingresos (NUEVO)
│   ├── ReturnsPage.tsx         ← /compras/rechazos (NUEVO)
│   └── SuppliersPage.tsx       ← /compras/proveedores (NUEVO)
│
├── inventory/                  ← 📦 Inventario
│   ├── Kardex.tsx              ← /inventario/kardex
│   ├── SuppliesPage.tsx        ← /inventario/insumos (NUEVO)
│   ├── WarehousesPage.tsx      ← /inventario/almacenes (NUEVO)
│   ├── TransfersPage.tsx       ← /inventario/traslados (NUEVO)
│   ├── AdjustmentsPage.tsx     ← /inventario/ajustes (NUEVO)
│   └── CountsPage.tsx          ← /inventario/conteos (NUEVO)
│
├── finance/                    ← 💰 Finanzas operativas
│   ├── Cashflow.tsx            ← /finanzas/cashflow
│   ├── PayablesPage.tsx        ← /finanzas/cuentas-por-pagar (NUEVO)
│   ├── TreasuryPage.tsx        ← /finanzas/tesoreria (NUEVO)
│   └── ReconciliationsPage.tsx ← /finanzas/conciliaciones (NUEVO)
│
├── reports/                    ← 📊 Reportes ERP (datos reales)
│   ├── SalesReports.tsx        ← /reportes/ventas (NUEVO)
│   ├── CostsReports.tsx        ← /reportes/costos (NUEVO)
│   ├── PurchasesReports.tsx    ← /reportes/compras (NUEVO)
│   ├── InventoryReports.tsx    ← /reportes/inventario (NUEVO)
│   └── FinanceReports.tsx      ← /reportes/finanzas (NUEVO)
│
├── config/                     ← ⚙️ Configuración general
│   ├── CompanyPage.tsx         ← /config/empresa (NUEVO)
│   ├── BranchesPage.tsx        ← /config/sucursales (NUEVO)
│   ├── UsersPage.tsx           ← /config/usuarios (NUEVO)
│   ├── RolesPage.tsx           ← /config/roles (NUEVO)
│   ├── ParametersPage.tsx      ← /config/parametros (NUEVO)
│   └── BrandingPage.tsx        ← /config/marca (mover desde Settings.tsx)
│
└── auth/
    └── Login.tsx               ← /login
```

9.2 Componentes organizados por dominio
```text

apps/web/src/components/
├── investment/                 ← Componentes específicos de pre-operación
├── commercial/                 ← Componentes de ferretería/retail
├── restaurant/                 ← Componentes de restaurante
├── production/                 ← Componentes de cocina/producción
├── purchasing/                 ← Componentes de compras
├── inventory/                  ← Componentes de inventario
├── finance/                    ← Componentes de finanzas
├── reports/                    ← Componentes de reportes
├── config/                     ← Componentes de configuración
├── layout/                     ← AppShell, Header, Sidebar (jerárquico)
├── auth/                       ← PrivateRoute, LoginForm
└── ui/                         ← Componentes compartidos (Button, Card, Modal, etc.)
```

9.3 Hooks por módulo
```text

apps/web/src/hooks/
├── investment/
│   ├── useAccounting.ts
│   ├── useScenarios.ts
│   └── useSetup.ts
├── commercial/
│   ├── useSales.ts
│   ├── usePosSession.ts
│   ├── usePurchases.ts
│   └── useInvoices.ts
├── restaurant/
│   ├── useTables.ts
│   ├── useMenu.ts
│   ├── useKitchenOrders.ts
│   └── useDelivery.ts
├── inventory/
│   ├── useKardex.ts
│   ├── useSupplies.ts
│   ├── useWarehouses.ts
│   └── useTransfers.ts
├── finance/
│   ├── useCashflow.ts
│   ├── usePayables.ts
│   └── useTreasury.ts
├── reports/
│   ├── useSalesReports.ts
│   └── useCostsReports.ts
├── config/
│   ├── useCompanySettings.ts
│   ├── usePalette.ts
│   └── useUsers.ts
└── shared/
    └── useAuth.ts
```

10. Propuesta de Navegación Definitiva (Sidebar Jerárquico)
10.1 Estructura visual del sidebar
```text

┌───────────────────────────────────────────────────────────────────────────┐
│ 🐟 El Segoviano                                                          │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                           │
│ ▸ 🏗️ PROYECTO DE INVERSIÓN                                               │
│   📊 Dashboard   🏗️ Setup   🎮 Simulador   📋 Reportes Financieros      │
│                                                                           │
│ ▸ 🏪 ERP                                                                  │
│   ├─ 🧾 Ventas                                                           │
│   │   💳 Caja / POS   🧾 Facturación   📋 Historial                      │
│   ├─ 🍽️ Restaurante                                                     │
│   │   🪑 Salones   📜 Menú   📝 Comandas   🛵 Delivery   🥡 Take Away   │
│   │   🏷️ Promociones                                                    │
│   ├─ 🧑‍🍳 Cocina / Producción                                            │
│   │   📖 Recetas   📋 Órdenes de Producción   🗑️ Mermas                 │
│   ├─ 🛒 Compras                                                          │
│   │   📦 Órdenes de Compra   📥 Recepción   ↩️ Devoluciones   🏢 Proved. │
│   ├─ 📦 Inventario                                                       │
│   │   🥩 Insumos   🏭 Almacenes   🔄 Traslados   🔧 Ajustes   📊 Conteos │
│   └─ 💰 Finanzas                                                         │
│       💳 Cuentas por Pagar   🏦 Tesorería   🔄 Conciliaciones            │
│                                                                           │
│ ▸ 📊 REPORTES ERP                                                         │
│   📈 Ventas   💲 Costos   🛒 Compras   📦 Inventario   💵 Finanzas       │
│                                                                           │
│ ▸ ⚙️ CONFIGURACIÓN                                                       │
│   🏢 Empresa   🏬 Sucursales   👥 Usuarios   🔐 Roles   ⚙️ Parámetros   │
│   🎨 Branding                                                            │
│                                                                           │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 🚪 Cerrar Sesión                ← SIEMPRE VISIBLE EN TODAS LAS PÁGINAS   │
└───────────────────────────────────────────────────────────────────────────┘
```

10.2 Reglas de navegación (según respuestas del cliente)

    El botón "Salir" (Cerrar Sesión) debe aparecer siempre visible en el sidebar, tanto en desktop como mobile, sin importar el módulo o submódulo actual. No debe aparecer dentro de modales ni sub-vistas (cliente confirmó).

    Los módulos de pre-operación (Dashboard, Setup, Simulador, Reportes de Inversión) están disponibles solo durante la fase de configuración del proyecto. Una vez que el ERP está operativo, estos pueden ocultarse o mantenerse para análisis.

    La navegación es jerárquica y colapsable, permitiendo expandir/contraer módulos para no abrumar al usuario con 20+ opciones.

    Todos los módulos tienen su propio icono y etiqueta clara, con colores diferenciados por dominio (inversión: azul, ventas: verde, restaurante: naranja, etc.).

11. Modelo de Datos — Tablas Existentes vs. Propuestas
11.1 Tablas existentes (en DB actual)
| Tabla | Ubicación ORM actual | Dominio conceptual | Estado |
| --- | --- | --- | --- |
| companies | adapters/db/models/accounting.py | Multi-tenant | ✅ |
| accounts | adapters/db/models/accounting.py | Contabilidad | ✅ |
| journal_entries | adapters/db/models/accounting.py | Contabilidad | ✅ |
| journal_entry_lines | adapters/db/models/accounting.py | Contabilidad | ✅ |
| products | adapters/db/models/accounting.py | Inventario (mal ubicado) | ⚠️ |
| kardex_movements | adapters/db/models/accounting.py | Inventario (mal ubicado) | ⚠️ |
| cashflow_projections | adapters/db/models/accounting.py | Finanzas | ✅ |
| pos_sessions | adapters/db/models/sales.py | Ventas (compartido) | ✅ |
| sales | adapters/db/models/sales.py | Ventas | ✅ |
| sale_items | adapters/db/models/sales.py | Ventas | ✅ |
| sale_payments | adapters/db/models/sales.py | Ventas | ✅ |
| restaurant_sales | adapters/db/models/sales.py | Restaurante | ✅ |
| hardware_sales | adapters/db/models/sales.py | Ferretería | ✅ |
| users | app/models/user.py | Auth (mal ubicado) | ⚠️ |
| simulation_scenarios | adapters/db/models/simulator.py | Simulador | ✅ |
11.2 Tablas propuestas (nuevas)
| Tabla | Dominio | Propósito |
| --- | --- | --- |
| company_settings | Configuración | Persistir feature flags, branding, parámetros |
| product_units | Inventario | Almacenar seriales individuales de productos (trazabilidad) |
| purchases | Compras | Órdenes de compra |
| purchase_items | Compras | Ítems de compra |
| suppliers | Compras | Proveedores |
| receipts | Compras | Recepción de insumos |
| returns | Compras | Devoluciones a proveedores |
| recipes | Cocina | Fichas técnicas, explosión de insumos |
| production_orders | Cocina | Órdenes de producción |
| waste_logs | Cocina | Mermas y pérdidas |
| tables | Restaurante | Mesas con estado (libre/ocupada/reservada) |
| menu_items | Restaurante | Carta, modificadores |
| kitchen_orders | Restaurante | Pedidos a cocina con estados |
| delivery_orders | Restaurante | Pedidos delivery con tracking |
| promotions | Restaurante | Combos, menú del día, ofertas |
| stock_alerts | Inventario | Alertas de stock mínimo/reorden |
| inventory_counts | Inventario | Toma de inventario físico |
| transfers | Inventario | Traslados entre almacenes |
| adjustments | Inventario | Correcciones de stock |
| payables | Finanzas | Cuentas por pagar |
| treasury_movements | Finanzas | Movimientos de tesorería |
| reconciliations | Finanzas | Conciliaciones bancarias |
| branches | Configuración | Sucursales del negocio |
| roles | Configuración | Roles y permisos |
| parameters | Configuración | Parámetros del sistema (propinas, delivery fee, etc.) |
12. Matriz de Cobertura por Dominio
| Dominio | Core (puertos) | Adapters (repos) | Router | Service | Frontend | Cobertura actual | Meta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Contabilidad | ✅ 6 archivos | ✅ 1 repo | ✅ 1 router | ✅ | ✅ | 90% | 100% |
| Ventas/POS | ❌ Vacío | ❌ Sin repo | ✅ 1 router | ⚠️ Rompe hexagonal | ✅ 3 páginas | 40% | 100% |
| Inventario | ❌ Vacío | ❌ Sin repo | ❌ Sin router propio | ✅ kardex_service | ⚠️ 1 página | 25% | 100% |
| Finanzas | ✅ (en accounting) | ✅ (en accounting) | ❌ Sin router propio | ✅ | ⚠️ 1 página | 50% | 100% |
| Restaurante | ❌ Vacío | ❌ Sin repo | ❌ Sin router | ❌ | ❌ Sin páginas específicas | 10% | 100% |
| Compras | ❌ No existe | ❌ No existe | ❌ No existe | ❌ | ❌ | 0% | 100% |
| Cocina/Producción | ❌ No existe | ❌ No existe | ❌ No existe | ❌ | ❌ | 0% | 100% |
| Configuración | ⚠️ Stub (en memoria) | ❌ Sin repo | ✅ 1 router | ✅ setup_service | ✅ Settings.tsx | 30% | 100% |
| Agentes IA | ⚠️ Stub (BaseSkill) | ❌ | ❌ | ❌ | ❌ | 5% | (excluido) |
| Auth | ✅ security.py | ✅ user repo | ✅ auth router | ✅ | ✅ Login | 80% | 100% |
| Pre-operación | ✅ | ✅ | ✅ | ✅ | ✅ | 95% | 100% |
| Reportes ERP | ❌ | ❌ | ❌ | ❌ | ❌ | 0% | 100% |

Promedio de cobertura actual: ~43% (excluyendo agentes IA y lo no implementado).
Meta después de Fase 1-2: >80% con la arquitectura hexagonal correcta.
13. Plan de Migración por Fases (Con todas las deudas asignadas)
Fase 0 – MVP Restaurante + Ferretería Básico (3 sprints / 3-4 semanas)

Entregable: Sistema funcional con ventas, inventario básico (con seriales opcionales), y módulo Restaurante (salones, menú, comandas, takeaway, promociones básicas).
*Deudas técnicas pospuestas: D-05, D-06, D-20, D-21 (se resolverán en fases posteriores).*
| Tarea | Responsable | Esfuerzo | ¿Entrega funcionalidad? |
| --- | --- | --- | --- |
| 0.1 Configurar multitenant (tenant_id en tablas existentes + middleware) | Backend | 1 día | ✅ |
| 0.2 Implementar selección de tipo de negocio (ferretería/restaurante) en setup de tenant | Backend | 0.5 día | ✅ |
| 0.3 Crear modelos y migraciones para Restaurante: tables, menu_items, kitchen_orders, takeaway_orders, promotions | Backend | 2 días | ✅ |
| 0.4 Implementar endpoints de Restaurante (abrir mesa, tomar pedido, enviar a cocina, cerrar comanda) | Backend | 3 días | ✅ |
| 0.5 Implementar lógica de promociones básicas (combos, descuentos fijos) | Backend | 1 día | ✅ |
| 0.6 Crear páginas frontend para Restaurante (mapa de mesas, menú, comandas, takeaway, promociones) | Frontend | 3 días | ✅ |
| 0.7 Asegurar que POS soporte ventas al por mayor/detal (diferentes precios, cantidades) | Backend | 1 día | ✅ |
| 0.8 Implementar seriales en inventario (tabla product_units, campo has_serial, lógica de venta con selección de serial) | Backend | 4 días | ✅ |
| 0.9 Agregar campo barcode en products (opcional, sin lógica de escáner) | Backend | 0.5 día | ✅ |
| 0.10 Implementar grupos de productos (1 nivel de categoría: ej. "Fierros") | Backend | 0.5 día | ✅ |
| 0.11 Configurar sidebar jerárquico con botón "Salir" siempre visible (solo en sidebar, no en modales) | Frontend | 1 día | ✅ |
| 0.12 Documentar deudas técnicas (D-05, D-06, D-20, D-21) | Equipo | 0.5 día | ⏳ |

Métrica de éxito: Cliente puede abrir una mesa, tomar pedido, enviar a cocina, cerrar cuenta (con promociones); realizar ventas al por mayor/detal en ferretería; registrar productos con seriales (trazabilidad individual) y productos sin serial (solo cantidad); el campo barcode existe en la base de datos pero no se utiliza en la interfaz.
Fase 1 – Corrección Hexagonal + Persistencia de Configuración + Reorganización Frontend (2 sprints / 2 semanas)

Entregable: Arquitectura limpia para ventas e inventario, configuración persistente en DB, frontend organizado por dominio.
*Deudas resueltas en esta fase: D-01, D-02, D-03, D-04, D-07, D-08, D-09.*
| Tarea | Responsable | Esfuerzo | Deuda resuelta |
| --- | --- | --- | --- |
| 1.1 Crear core/sales/ports.py y core/inventory/ports.py | Backend | 0.5 día | D-01 |
| 1.2 Implementar repositorios en adapters/db/repositories/ (sales.py, inventory.py) | Backend | 1 día | D-01 |
| 1.3 Refactorizar services/sales_service.py para usar puertos (no ORM directo) | Backend | 1 día | D-02 |
| 1.4 Mover Product y KardexMovement de accounting.py a inventory.py | Backend | 0.5 día | D-01 |
| 1.5 Mover models/user.py de app/models/ a app/adapters/db/models/user.py | Backend | 0.25 día | — |
| 1.6 Crear tabla company_settings y refactorizar setup_service.py para persistir branding | Backend | 0.5 día | D-03 |
| 1.7 Actualizar frontend useCompanySettings para consumir datos de DB | Frontend | 0.5 día | D-03 |
| 1.8 Actualizar migraciones Alembic | Backend | 0.5 día | — |
| 1.9 Refactorizar routers para agrupar por dominio (investment/, commercial/, restaurant/, etc.) | Backend | 1 día | — |
| 1.10 Reorganizar páginas frontend en pages/ por dominio | Frontend | 1 día | D-07 |
| 1.11 Rediseñar AppShell.tsx con sidebar jerárquico colapsable | Frontend | 1 día | D-08 |
| 1.12 Asegurar botón "Salir" siempre visible en sidebar (no en modales) | Frontend | 0.25 día | D-09 |
| 1.13 Separar reportes financieros del simulador (preparar estructura para datos reales) | Backend | 0.5 día | D-04 |

Métrica de éxito: core/sales/ y core/inventory/ tienen puertos definidos; sales_service.py ya no importa ORM; configuración persiste entre reinicios; routers organizados por dominio; frontend con páginas agrupadas y navegación jerárquica; "Salir" siempre visible en sidebar.
Fase 2 – Cocina/Producción + Delivery Avanzado + Compras (2 sprints / 2 semanas)

Entregable: Módulos de cocina (recetas, órdenes, mermas), delivery (repartidores, zonas, tracking), y compras básicas.
*Deudas resueltas en esta fase: D-05, D-06, (D-21 opcional).*
| Tarea | Responsable | Esfuerzo | Deuda resuelta |
| --- | --- | --- | --- |
| 2.1 Implementar core/production/ports.py (recetas, órdenes, mermas) | Backend | 1 día | — |
| 2.2 Crear modelos y endpoints para recetas, producción, mermas | Backend | 2 días | — |
| 2.3 Implementar lógica de explosión de insumos (receta → productos) | Backend | 1 día | — |
| 2.4 Crear páginas frontend para Cocina | Frontend | 2 días | — |
| 2.5 Implementar delivery avanzado (repartidores, zonas, tracking) – DT-REST-02 | Backend | 2 días | D-06 |
| 2.6 Crear páginas frontend para Delivery | Frontend | 1 día | — |
| 2.7 Implementar core/purchasing/ports.py (órdenes, recepción, devoluciones, proveedores) | Backend | 1 día | — |
| 2.8 Crear modelos y endpoints para Compras | Backend | 2 días | — |
| 2.9 Crear páginas frontend para Compras | Frontend | 1 día | — |
| 2.10 Refinar lógica de cierre de comanda (DT-REST-01) | Backend | 0.5 día | D-05 |
| 2.11 (Opcional) Implementar campo barcode y lógica básica de búsqueda por código de barras | Backend | 0.5 día | D-21 |

Métrica de éxito: Cliente puede crear recetas, generar órdenes de producción, registrar mermas; delivery con repartidores y tracking; compras completas; cierre de comanda corregido.
Fase 3 – Inventario Completo + Finanzas Operativas (2 sprints / 2 semanas)

Entregable: Almacenes, traslados, ajustes, conteos; cuentas por pagar, tesorería, conciliaciones.
*Deudas resueltas en esta fase: D-20 (facturación electrónica – V2).*
| Tarea | Responsable | Esfuerzo | Deuda resuelta |
| --- | --- | --- | --- |
| 3.1 Implementar core/inventory/warehouses.py, transfers.py, adjustments.py, counts.py | Backend | 2 días | — |
| 3.2 Crear modelos y endpoints correspondientes | Backend | 2 días | — |
| 3.3 Crear páginas frontend para inventario completo | Frontend | 2 días | — |
| 3.4 Implementar core/finance/ports.py (CxP, tesorería, conciliaciones) | Backend | 1 día | — |
| 3.5 Crear modelos y endpoints para finanzas operativas | Backend | 2 días | — |
| 3.6 Crear páginas frontend para finanzas | Frontend | 1 día | — |
| 3.7 Implementar facturación electrónica genérica (DT-FERR-01) – V2 | Backend | 1 día | D-20 |

Métrica de éxito: Cliente puede gestionar múltiples almacenes, trasladar productos, hacer conteos físicos; manejar cuentas por pagar y conciliaciones.
Fase 4 – Reportes ERP + Configuración Completa + Infraestructura (1 sprint / 1 semana)

Entregable: Reportes basados en datos reales; configuración avanzada (sucursales, roles, parámetros, branding); CI/CD; monitoreo completo.
*Deudas resueltas en esta fase: D-10 a D-18.*
| Tarea | Responsable | Esfuerzo | Deuda resuelta |
| --- | --- | --- | --- |
| 4.1 Implementar reportes de ventas (por plato, categoría, salón vs delivery) | Backend | 1 día | — |
| 4.2 Implementar reportes de costos (márgenes por plato) | Backend | 1 día | — |
| 4.3 Implementar reportes de inventario (rotación, valorizado) | Backend | 1 día | — |
| 4.4 Implementar reportes financieros | Backend | 1 día | — |
| 4.5 Crear páginas frontend para reportes | Frontend | 1 día | — |
| 4.6 Implementar configuración completa (sucursales, roles, parámetros) | Backend | 1 día | — |
| 4.7 Crear páginas frontend para configuración | Frontend | 0.5 día | — |
| 4.8 Configurar CI/CD básico (infra/ci/) | DevOps | 1 día | D-12 |
| 4.9 Configurar dashboards Grafana pre-hechos | DevOps | 1 día | D-13 |
| 4.10 Implementar rate limiting con Redis (D-10) | Backend | 0.5 día | D-10 |
| 4.11 Refactorizar Auth para usar PostgreSQL real + Redis (D-11) | Backend | 1 día | D-11 |
| 4.12 Implementar tests de integración HTTP (D-14) | Backend | 1 día | D-14 |
| 4.13 Mejorar cashflow como módulo separado (D-15) | Backend | 1 día | D-15 |
| 4.14 Configurar ESLint/Prettier (D-16) | Frontend | 0.5 día | D-16 |
| 4.15 Configurar Loki (D-17) | DevOps | 1 día | D-17 |
| 4.16 Configurar OpenTelemetry (D-18) | DevOps | 2 días | D-18 |

Métrica de éxito: Todos los reportes muestran datos reales (no simulados); la configuración permite gestionar sucursales, roles y parámetros; CI/CD funcional; monitoreo completo.
14. Métricas de Éxito para el Próximo Hito

Después de completar las Fases 0-1, se espera alcanzar los siguientes indicadores:
| Indicador | Valor actual | Meta después de F0-1 |
| --- | --- | --- |
| Porcentaje de adherencia arquitectónica global | 72% | ≥85% |
| core/sales/ y core/inventory/ no vacíos | ❌ Vacíos | ✅ Con puertos y entidades |
| services/sales_service.py usa puertos (no ORM) | ❌ Violación | ✅ |
| Todos los modelos ORM dentro de adapters/db/models/ | ⚠️ User fuera | ✅ |
| Routers agrupados por dominio | ❌ Planos | ✅ |
| Frontend: páginas agrupadas por módulo | ❌ Planas | ✅ |
| Sidebar jerárquico colapsable | ❌ Lineal | ✅ |
| Botón "Salir" siempre visible en sidebar | ⚠️ Solo header | ✅ |
| Setup/Branding persistente en DB | ❌ Memoria | ✅ |
| MVP Restaurante entregado (salones, menú, comandas, takeaway, promociones básicas) | ❌ No | ✅ |
| Seriales implementados | ❌ No | ✅ |
| Delivery avanzado | ❌ No | ⏳ (Fase 2) |
| Facturación electrónica | ❌ No | ⏳ (V2) |
15. Recomendaciones para el Arquitecto y el Product Owner
Para el Arquitecto de Sistemas

    Respetar el orden de fases establecido:

        Fase 0 entrega funcionalidad al cliente (MVP Restaurante + Ferretería básica), con deudas temporales.

        Fase 1 corrige la arquitectura (D-01 a D-04, D-07 a D-09) antes de iniciar la Fase 2.

        Fase 2-4 agregan módulos nuevos y resuelven las deudas restantes según lo planificado.

    No comenzar Fase 2 sin completar Fase 1 al 100%. El costo de construir módulos nuevos sobre una arquitectura quebrada sería muy alto.

    Establecer un estándar de código para nuevas contribuciones:

        Todo nuevo dominio debe empezar con core/{dominio}/ports.py definiendo interfaces abstractas.

        Los servicios deben inyectar dependencias a través de los puertos.

        Los tests unitarios deben mockear los puertos (no usar la DB real).

    Implementar un event-driven architecture con RabbitMQ (ya desplegado). Definir eventos de dominio como SaleCreated, InventoryUpdated, KardexMovementRegistered para desacoplar módulos.

    Versionar la API (/api/v1/comercial/, /api/v1/restaurante/) al reorganizar los routers para permitir migraciones incrementales sin romper clientes.

    Configurar un pipeline de CI/CD que ejecute las pruebas de arquitectura (linter que verifique que services/ no importe de adapters/db/models/).

Para el Product Owner

    Comunicar al cliente que las funcionalidades acordadas se entregarán según el plan de fases: MVP Restaurante en Fase 0, delivery avanzado en Fase 2, facturación electrónica en V2. Esto asegura que el cliente no perderá las funcionalidades críticas.

    Aprobar la Fase 1 como un sprint de "limpieza técnica" sin nuevos features. El costo de no hacerlo ahora será mucho mayor cuando se agreguen 10+ módulos.

    Validar con el cliente la implementación de seriales usando ejemplos concretos (taladros, herramientas) para asegurar que entiende los beneficios de trazabilidad.

    El botón "Salir" solo en el sidebar (no en modales). Esta decisión debe quedar clara en la documentación para evitar confusiones en el equipo de desarrollo.

    Planificar la transición Pre-Operación → Operación: Definir qué datos del Simulador se migran al ERP operativo (plan de cuentas, proyecciones iniciales, productos base).

    Establecer un "consejo de arquitectura" semanal para revisar la adherencia durante el desarrollo de nuevos módulos.

16. Anexo: Resumen de Decisiones del Cliente
| Decisión | Respuesta del cliente | Impacto en el plan |
| --- | --- | --- |
| Multitenant | Cada empresa es un tenant separado. Usuarios solo de su tenant. | tenant_id en todas las tablas. Base de datos compartida. |
| MVP Restaurante | Salones, menú, comandas, takeaway, promociones básicas. | Entregado en Fase 0. |
| Cierre de comanda | Refinar para que cierre solo al cancelar pedido. | D-05 → Fase 2. |
| Delivery avanzado | Repartidores, zonas, tracking. | D-06 → Fase 2 (aceptado). |
| Facturación electrónica | Genérica, sin proveedor específico. V2. | D-20 → Fase 3 o 4 (V2). |
| Seriales en inventario | Implementar trazabilidad individual. | Se implementa en Fase 0. |
| Código de barras | No requerido inicialmente. Solo campo barcode. | Campo opcional, sin lógica de escáner. D-21 → Fase 2 opcional. |
| POS ferretería | Soporta ventas al por mayor y al detal. | Implementado en Fase 0. |
| Grupos de productos | 1 nivel de categoría (ej. "Fierros"). | Implementado en Fase 0. |
| Módulos compartidos | No se comparten bodegas, compras ni finanzas entre tipos de negocio. | Cada tenant tiene sus propios datos. |
| Botón Salir | Solo en el sidebar (no en modales). | Siempre visible en sidebar. Implementado en Fase 1. |

    Documento generado por: Agente de Arquitectura (consolidación de todas las respuestas del cliente)
    Siguiente paso: Revisar con el Arquitecto de Sistemas y el Product Owner, aprobar el plan, y asignar tareas a los equipos para iniciar la Fase 0.
    El plan está listo para ser ejecutado. ✅