# Diagrama de Flujo del Pipeline — IaaS-RonSys

> **Documento:** Mapeo completo del pipeline de agentes, archivos generados y flujo de datos entre ellos.
> **Basado en:** Ejecución real de la Fase 1 + Fase 2.
> **Fecha:** 2026-05-12

---

## 📋 Índice

> ⚡ **Principio de Arquitectura del Pipeline**
>
> Los agentes **no se pasan archivos entre sí** — todos leen y escriben en el
> **mismo monorepo en disco** (`/home/ron/projectos/IaaS-RonSys/`), y Jarvis
> coordina quién hace qué mediante **mensajes con rutas de archivos**.
>
> ```
> Jarvis ──→ "Backend, implementa HU-F1-001 basada en docs/backlog/gherkin-*.md"
> Backend ──→ (escribe en apps/backend/*) 
> Backend ──→ "Listo. 102 tests OK. Archivos en apps/backend/app/core/..."
> Jarvis ──→ "QA, valida lo que backend escribió en apps/backend/*"
> ```
>
> No hay transferencia de archivos vía mensajería. Solo instrucciones + rutas.

1. [Visión General del Pipeline](#1-visión-general-del-pipeline)
2. [Actores y sus Responsabilidades](#2-actores-y-sus-responsabilidades)
3. [Flujo de Archivos entre Agentes](#3-flujo-de-archivos-entre-agentes)
4. [Ejemplo: Fase 1 Completa](#4-ejemplo-fase-1-completa)
5. [Tipos de Pipeline según el Requerimiento](#5-tipos-de-pipeline-según-el-requerimiento)
6. [Estrategia de Archivos Compartidos](#6-estrategia-de-archivos-compartidos)

---

## 1. Visión General del Pipeline

```
                    ┌──────────────────────────────────────────────┐
                    │               RON (Cliente/PO)               │
                    │  "Necesito X funcionalidad en el ERP"        │
                    └────────────────────┬─────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │          JARVIS (Orquestador) 🤖             │
                    │  • Analiza requerimiento                     │
                    │  • Decide pipeline (feature/bug/infra/docs)  │
                    │  • Delega al agente correcto                 │
                    │  • Encadena resultados                       │
                    │  • Reporta a Ron                             │
                    └────────────────────┬─────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌──────────────────┐     ┌────────────────────┐     ┌──────────────────┐
    │ NUEVA FUNCIONALIDAD│    │   BUG FIX          │     │  CONFIG/INFRA    │
    │ (Pipeline completo)│    │ (Pipeline corto)   │     │  (Pipeline mín.) │
    └────────┬──────────┘     └────────┬───────────┘     └────────┬─────────┘
             │                         │                          │
             ▼                         ▼                          ▼
     ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
     │ Architecture │          │ QA / Backend │          │   DevOps     │
     │    Agent     │          │  / Frontend  │          │    Agent     │
     └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
            │                         │                          │
            ▼                         ▼                          ▼
     ┌──────────────┐          ┌──────────────┐
     │  PO Agent    │          │ QA Regresión │
     └──────┬───────┘          └──────┬───────┘
            │                         │
            ▼                         ▼
     ┌──────────────┐          ┌──────────────┐
     │ Backend +    │          │   DevOps     │
     │ Frontend     │          │   Agent      │
     │ (paralelo)   │          │   (demo)     │
     └──────┬───────┘          └──────┬───────┘
            │                         │
            ▼                         ▼
     ┌──────────────┐          ┌──────────────┐
     │   QA Agent   │          │   ¡Demo! 🚀  │
     └──────┬───────┘          │   URL a Ron  │
            │                  └──────────────┘
            ▼
     ┌──────────────┐
     │  DevOps      │
     │  Agent       │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  ¡Demo! 🚀   │
     │  URL a Ron   │
     └──────────────┘
```

---

## 2. Actores y sus Responsabilidades

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ECOSISTEMA DE AGENTES                              │
│                     (Todos usan deepseek-v4-pro vía DeepSeek)                │
├──────────┬──────────────────────────┬──────────────────┬────────────────────┤
│  Agente  │      Sesión ID          │  Rol             │  Modelo            │
├──────────┼──────────────────────────┼──────────────────┼────────────────────┤
│  🤖     │ agent:jarvis:main       │ Orquestador      │ deepseek-v4-flash  │
│  🏗️     │ architecture-agent:main │ Diseño técnico   │ deepseek-v4-pro    │
│  📋     │ product-owner-agent:main│ Historias Gherkin│ deepseek-v4-pro    │
│  🐍     │ backend-dev-agent:main  │ APIs + DB        │ deepseek-v4-pro    │
│  ⚛️     │ frontend-dev-agent:main │ UI React         │ deepseek-v4-pro    │
│  🧪     │ qa-agent:main          │ Pruebas + QA     │ deepseek-v4-pro    │
│  🚀     │ devops-agent:main      │ Infra + Deploy   │ deepseek-v4-pro    │
│  💬     │ chatbot:main           │ Chat directo Ron  │ deepseek-v4-flash  │
└──────────┴──────────────────────────┴──────────────────┴────────────────────┘
```

### Comunicación entre Agentes

Los agentes **no se pasan archivos directamente**. Usan el sistema de mensajería de OpenClaw:

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   Jarvis → sessions_send(sessionKey, mensaje) → Agente destino     ║
║                                                                    ║
║   • Jarvis le dice al Agente: "Trabaja en el archivo /ruta/X"     ║
║   • El Agente lee/escribe X en el sistema de archivos compartido   ║
║   • El Agente responde con confirmación + resumen                  ║
║   • Jarvis encadena al siguiente agente con la misma estrategia    ║
║                                                                    ║
║   🗄️ Sistema de archivos = repositorio compartido (monorepo)       ║
║   📁 /home/ron/projectos/IaaS-RonSys/                              ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 3. Flujo de Archivos entre Agentes

```
                            SISTEMA DE ARCHIVOS COMPARTIDO
                   ┌───────────────────────────────────────────┐
                   │   /home/ron/projectos/IaaS-RonSys/         │
                   │                                            │
                   │   docs/                                    │
                   │     ├── backlog/                           │
                   │     ├── reports/                           │
                   │     └── ...                                │
                   │   apps/                                    │
                   │     ├── backend/                           │
                   │     │     ├── app/                         │
                   │     │     │    ├── core/                   │
                   │     │     │    ├── routers/                │
                   │     │     │    ├── schemas/                │
                   │     │     │    ├── services/               │
                   │     │     │    ├── adapters/               │
                   │     │     │    │    ├── db/models/         │
                   │     │     │    │    └── alembic/versions/  │
                   │     │     │    └── main.py                 │
                   │     │     └── tests/                       │
                   │     └── web/                               │
                   │           ├── src/                         │
                   │           │    ├── pages/                  │
                   │           │    ├── components/             │
                   │           │    ├── hooks/                  │
                   │           │    ├── types/                  │
                   │           │    └── __tests__/              │
                   │           └── dist/                        │
                   ├── docker-compose*.yml                      │
                   └── .env                                     │
                   └────────────────────────────────────────────┘

CADA AGENTE ESCRIBE EN SU CAPA CORRESPONDIENTE:

  Arquitecto ───→ docs/reports/analysis-*.md
                      │
                      ▼
  PO Agent ──────────→ docs/backlog/gherkin-*.md
                      │
              ┌───────┴───────┐
              │               │
              ▼               ▼
     Backend Agent      Frontend Agent
     apps/backend/       apps/web/src/
       ├── core/*          ├── pages/*
       ├── routers/*       ├── components/*
       ├── models/*        ├── hooks/*
       ├── schemas/*       ├── types/*
       ├── services/*      └── __tests__/*
       ├── migrations/*
       └── tests/*
              │               │
              └───────┬───────┘
                      │
                      ▼
              QA Agent
              Verifica todo el monorepo
              └── reports en sessions
                      │
                      ▼
              DevOps Agent
              ├── docker-compose*.yml
              ├── Dockerfile
              └── docker compose up -d --build
```

---

## 4. Ejemplo: Fase 1 Completa

### 4.1 Traza paso a paso

```
═══════════════════════════════════════════════════════════════════════════════
  PASO 0: INICIO
═══════════════════════════════════════════════════════════════════════════════

  Ron: "Lanza el pipeline para Fase 1, 2 y 3"
       │
       ▼
  Jarvis: Delega al Architecture Agent
       │
       ▼
  sessions_send(sessionKey="agent:architecture-agent:main", 
                mensaje="Analiza el proyecto completo y genera un reporte")
       │
       ▼
  🏗️ Architecture Agent:
     • Lee el monorepo completo
     • Ejecuta pytest, jest, tsc
     • Verifica endpoints con curl
     • Revisa DB, migraciones, contenedores
     • Genera diagnóstico + fichas técnicas + plan priorizado
       │
       └──→ 📄 Escribe: docs/reports/analysis-2026-05-12.md  (33 KB)
       │
       └──→ Responde: "Reporte completo en analysis-2026-05-12.md"
       │
       ▼
  Jarvis: recibe, analiza y decide el pipeline

═══════════════════════════════════════════════════════════════════════════════
  PASO 1: PO AGENT
═══════════════════════════════════════════════════════════════════════════════

  Jarvis: "PO, lee el analysis-2026-05-12.md y genera 27 Gherkin HU"
       │
       ▼
  sessions_send(sessionKey="agent:product-owner-agent:main",
                mensaje="Extrae §§7-9 del analysis y genera Gherkin")
       │
       ▼
  📋 PO Agent:
     • Lee: docs/reports/analysis-2026-05-12.md  (input)
     • Extrae fichas técnicas de Sales/POS, Cashflow, Business Type
     • Genera 27 HU con Given/When/Then
       │
       └──→ 📄 Escribe: docs/backlog/gherkin-fase1-3.md  
       │
       └──→ Responde: "27 HU generadas:
                        F1: 8 HU (6 BE + 2 FE) 
                        F2: 12 HU (8 BE + 4 FE)
                        F3: 7 HU (6 BE + 1 FE)"
       │
       ▼
  Jarvis: Revisa con Ron → Ron da el OK

═══════════════════════════════════════════════════════════════════════════════
  PASO 2: BACKEND + FRONTEND (PARALELO)
═══════════════════════════════════════════════════════════════════════════════

  Jarvis: Dispara ambos agentes en paralelo
       │
       ├── sessions_send("backend-dev-agent", "Implementa Fase 1: 6 HU")
       │      │
       │      ▼
       │  🐍 Backend Agent:
       │     • Lee: docs/backlog/gherkin-fase1-3.md (Gherkin specs)
       │     • Implementa HU-F1-001 a HU-F1-008
       │        HU-F1-001 → 📄 apps/backend/migrations/versions/0003_business_type.py
       │                      📄 apps/backend/app/adapters/db/models/company.py
       │        HU-F1-002 → 📄 apps/backend/app/schemas/settings.py  
       │                      📄 apps/backend/app/routers/admin.py (PUT /settings)
       │        HU-F1-004 → 📄 apps/backend/app/core/accounting/cashflow.py
       │                      📄 apps/backend/app/routers/accounting.py (GET /cashflow)
       │        HU-F1-005 → 📄 apps/backend/app/core/accounting/cashflow.py (+calculate_real)
       │        HU-F1-006 → 📄 apps/backend/app/core/accounting/cashflow.py (+compare)
       │        HU-F1-008 → 📄 apps/backend/migrations/versions/0004_cashflow_projections.py
       │     • Tests: pytest tests/ -v  →  102/102 ✅
       │     • Responde: "102 tests pasando. Fase 1 completa."
       │
       └── sessions_send("frontend-dev-agent", "Implementa Fase 1: 2 HU")
              │
              ▼
          ⚛️ Frontend Agent:
             • Lee: docs/backlog/gherkin-fase1-3.md (Gherkin specs)
             • Implementa HU-F1-003 y HU-F1-007
                HU-F1-003 → 📄 apps/web/src/hooks/useCompanySettings.ts
                            📄 apps/web/src/components/layout/AppShell.tsx
                            📄 apps/web/src/__tests__/CompanySettings.test.tsx
                HU-F1-007 → 📄 apps/web/src/pages/Cashflow.tsx
                            📄 apps/web/src/components/ui/AlertsBanner.tsx
                            📄 apps/web/src/components/dashboard/CashflowChart.tsx
                            📄 apps/web/src/__tests__/Cashflow.test.tsx
             • Tests: npx tsc --noEmit && npx jest   →  115 tests ✅
             • Responde: "115 tests, 16 suites. tsc 0 errores."

═══════════════════════════════════════════════════════════════════════════════
  PASO 3: QA AGENT
═══════════════════════════════════════════════════════════════════════════════

  Jarvis: "QA, valida la Fase 1 completa"
       │
       ▼
  sessions_send(sessionKey="agent:qa-agent:main",
                mensaje="Ejecuta tests, verifica contenedores, endpoints reales")
       │
       ▼
  🧪 QA Agent:
     • Ejecuta: pytest → 102/102 ✅
     • Ejecuta: npx jest → 115/115 ✅
     • Ejecuta: npx tsc --noEmit → ✅
     • Ejecuta: npx vite build → ✅
     • Build y levanta: docker compose up -d --build
     • Verifica endpoints reales con JWT:
        curl http://localhost:8000/health → 200 ✅
        curl POST /api/auth/login → JWT ✅
        curl GET /api/accounting/cashflow?view=projected → 96 líneas ✅
        curl GET /api/admin/company/settings → feature flags ✅
     • Encuentra ISSUES (5 en total):
        QA-05 🔴 Migraciones no aplicadas en startup → backend fix
        QA-02 🟡 Settings JSON sin persistencia → backend fix  
        QA-01 🟡 (= QA-05, duplicado)
        QA-03 🟡 AlertsBanner sin coverage → frontend fix
        QA-04 🟡 Frontend prod desactualizado → frontend fix
       │
       ├── sessions_send("backend-dev-agent",  "Arregla QA-05, QA-02")
       ├── sessions_send("frontend-dev-agent", "Arregla QA-03, QA-04")
       │
       ▼
  🔧 Backend + 🎨 Frontend corrigen → QA re-testa
       │
       ▼
  🧪 QA: 102 + 115 → 207 tests ✅
     └──→ Veredicto: 🟢 APROBADO
       │
       └──→ sessions_send("devops-agent", "Fase 1 APROBADA. Desplegar.")

═══════════════════════════════════════════════════════════════════════════════
  PASO 4: DEVOPS AGENT
═══════════════════════════════════════════════════════════════════════════════

  sessions_send(sessionKey="agent:devops-agent:main",
                mensaje="Despliega Fase 1 en producción")
       │
       ▼
  🚀 DevOps Agent:
     • Revisa docker-compose.prod.yml
     • Crea entorno producción (iaas-backend-prod)
     • Sembrado datos de prueba
     • Verifica migraciones en DB producción (→ 0005)
     • Healthcheck de todos los servicios
     • Encuentra issues de infra:
        DEV-01 🔴: missing primary_key en migración 0005 → escalado a Backend
        DEV-02 🟡: asyncio.run() anidado → workaround CLI
        DEV-03 🟡: password admin aleatorio → reseteada
     • Reporta URLs de demo
       │
       └──→ 📄 Reporte: responde con resumen completo + URLs
       │
       ▼
  Jarvis: Reporta a Ron → URLs + estado final

═══════════════════════════════════════════════════════════════════════════════
  PASO 5: CIERRE
═══════════════════════════════════════════════════════════════════════════════

  ✅ Pipeline Fase 1 COMPLETO

  Contenedores activos:
     iaas-backend-prod   :8000  (healthy)  → FastAPI
     iaas-frontend-prod  :80     (healthy)  → React/Vite  
     iaas-postgres       :5432  (healthy)  → PostgreSQL 16
     iaas-redis          :6379  (healthy)  → Redis 7
     iaas-rabbitmq       :5672  (healthy)  → RabbitMQ 4

  Tests:
     Backend:  102/102 ✅
     Frontend: 115/115 ✅ (16 suites)
═══════════════════════════════════════════════════════════════════════════════
```

### 4.2 Mapa de Archivos Generados en Fase 1

```
docs/
├── reports/
│   └── analysis-2026-05-12.md          ← 🏗️ Architecture Agent (33 KB)
│
├── backlog/
│   └── gherkin-fase1-3.md              ← 📋 PO Agent (27 HU, 200+ líneas)

apps/backend/
├── migrations/versions/
│   ├── 0003_business_type.py           ← 🐍 Backend (HU-F1-001)
│   └── 0004_cashflow_projections.py    ← 🐍 Backend (HU-F1-008)
│
├── app/
│   ├── core/accounting/
│   │   └── cashflow.py                 ← 🐍 Backend (HU-F1-004/005/006)
│   │                                    • CashflowService.generate_projection()
│   │                                    • CashflowService.calculate_real()
│   │                                    • CashflowService.compare()
│   │
│   ├── routers/
│   │   ├── accounting.py               ← 🐍 Backend (cashflow endpoints)
│   │   └── admin.py                    ← 🐍 Backend (settings endpoint)
│   │
│   └── schemas/
│       └── sales.py                    ← 🐍 Backend (feature flags schemas)
│
├── tests/
│   ├── test_cashflow.py                ← 🐍 Backend (cashflow tests)
│   └── test_settings.py                ← 🐍 Backend (settings tests)
│
└── DEBT.md                             ← 🐍 Backend (deuda actualizada)

apps/web/src/
├── hooks/
│   └── useCompanySettings.ts           ← ⚛️ Frontend (HU-F1-003)
├── pages/
│   └── Cashflow.tsx                    ← ⚛️ Frontend (HU-F1-007)
├── components/
│   ├── layout/
│   │   └── AppShell.tsx                ← ⚛️ Frontend (conditional nav)
│   ├── ui/
│   │   └── AlertsBanner.tsx            ← ⚛️ Frontend (HU-F1-007)
│   └── dashboard/
│       └── CashflowChart.tsx           ← ⚛️ Frontend (refactored)
├── types/
│   ├── company.ts                      ← ⚛️ Frontend (feature flags types)
│   └── cashflow.ts                     ← ⚛️ Frontend (cashflow types)
├── __tests__/
│   ├── CompanySettings.test.tsx        ← ⚛️ Frontend (9 tests)
│   └── Cashflow.test.tsx              ← ⚛️ Frontend (4 tests)
└── DEBT.md                             ← ⚛️ Frontend (deuda actualizada)
```

### 4.3 Tabla de Comunicación entre Agentes (Fase 1)

```
┌──────────┬──────────────────────┬──────────────────┬──────────────────────────┐
│  Emisor  │       Mensaje       │    Receptor      │  Archivo/s compartido/s  │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Ron      │ "Lanza Fase 1"      │ Jarvis           │ —                        │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Jarvis   │ "Analiza el         │ Architecture     │ docs/reports/            │
│          │  proyecto"          │ Agent            │ analysis-2026-05-12.md   │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Jarvis   │ "Genera Gherkin     │ PO Agent         │ ↑ analysis.md (input)    │
│          │  desde el analysis"  │                  │ docs/backlog/gherkin-*   │
│          │                      │                  │ (output)                 │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Jarvis   │ "Implementa Fase 1" │ Backend Agent    │ ↑ gherkin*.md (input)    │
│          │                      │                  │ apps/backend/* (output)  │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Jarvis   │ "Implementa Fase 1" │ Frontend Agent   │ ↑ gherkin*.md (input)    │
│          │                      │                  │ apps/web/* (output)      │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ Jarvis   │ "Valida Fase 1"     │ QA Agent         │ ↑ apps/* (todo el código)│
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ QA       │ "Fixes: QA-05,      │ Backend Agent    │ ↑ tests output           │
│          │  QA-02"             │                  │                           │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ QA       │ "Fixes: QA-03,      │ Frontend Agent   │ ↑ tests output           │
│          │  QA-04"             │                  │                           │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ QA       │ "Fase 1 APROBADA.   │ DevOps Agent     │ ↑ Verificación completa  │
│          │  Desplegar."        │                  │                           │
├──────────┼──────────────────────┼──────────────────┼──────────────────────────┤
│ DevOps   │ "Fase 1 desplegada  │ QA / Jarvis      │ docker-compose.prod.yml  │
│          │  en :8000 / :80"    │                  │ contenedores activos     │
└──────────┴──────────────────────┴──────────────────┴──────────────────────────┘
```

---

## 5. Tipos de Pipeline según el Requerimiento

### 5.1 Nueva Funcionalidad (con definición de arquitectura)

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐
│ Paso 0  │────▶│ Paso 1   │────▶│ Paso 2   │────▶│ Paso 3    │
│ Ron ──▶ │     │ PO ──▶   │     │ Backend +│── ─▶│ QA        │
│ Arquitect│     │ Arquitect│     │ Frontend │  │  │ (pruebas) │
│ Reporte  │     │ ──▶ PO  │     │ (paralelo)│  │  └─────┬─────┘
│ (Ficha)  │     │ ──▶     │     └──────────┘  │        │
└─────────┘     │ Gherkin │                    │   ╔════╧════╗
                └──────────┘                    │   ║ ¿PASA?  ║
                          ┌──────────┐         │   ╚════╤════╝
                          │          │─────────┘    NO  │  SÍ
                          │  FIX 🔧  │                │   │
                          │ (Backend │◀───────────────┘   │
                          │  o       │                    │
                          │  Frontend│                    ▼
                          │  según   │             ┌──────────┐
                          │  aplique) │             │ Paso 3b  │
                          └──────────┘             │ QA genera│
                                                    │ Reporte  │
                                                    │ Validac. │
                                                    │ (HU vs   │
                                                    │  real)   │
                                                    └────┬─────┘
                                                         │
                                                         ▼
                                                  ┌──────────┐
                                                  │ Paso 4   │
                                                  │ DevOps   │
                                                  │ (demo)   │
                                                  └────┬─────┘
                                                       │
                                                       ▼
                                                ╔══════════════╗
                                                ║ ¿Ron prueba  ║
                                                ║ y aprueba?   ║
                                                ╚════╤═══╤════╝
                                                     │   │
                                                     │   │  NO 🔄
                                                     │   │
                                                     │   ▼
                                                     │  ┌──────────┐
                                                     │  │ FIX 🛠️   │
                                                     │  │ (Backend │
                                                     │  │  o        │
                                                     │  │ Frontend)│
                                                     │  └────┬─────┘
                                                     │       │
                                                     │  ┌────▼─────┐
                                                     │  │ Rebuild  │
                                                     │  │ docker   │
                                                     │  │ compose  │
                                                     │  └────┬─────┘
                                                     │       │
                                                     └──▶───┘
                                                         SÍ
                                                         │
                                                         ▼
                                                ┌──────────┐
                                                │ APROBADO │
                                                │ (OK Ron) │
                                                └────┬─────┘
                                                     │
                                                     ▼
                                                ╔══════════════╗
                                                ║ ¿Cliente     ║
                                                ║ final revisa ║
                                                ║ manuales +   ║
                                                ║ da VB?       ║
                                                ╚════╤═══╤════╝
                                                     │   │
                                                     │   │  NO 🔄
                                                     │   │
                                                     │   ▼
                                                     │  ┌──────────┐
                                                     │  │ Ajustes  │
                                                     │  │ en       │
                                                     │  │ manuales │
                                                     │  │ + UI     │
                                                     │  │ (Jarvis  │
                                                     │  │ coordina)│
                                                     │  └────┬─────┘
                                                     │       │
                                                     │  ┌────▼─────┐
                                                     │  │ Rebuild  │
                                                     │  │ docker   │
                                                     │  │ compose  │
                                                     │  └────┬─────┘
                                                     │       │
                                                     └──▶───┘
                                                         SÍ
                                                         │
                                                         ▼
                                                ┌──────────────┐
                                                │ 🟢 APROBADO  │
                                                │ VB Cliente   │
                                                │ Final        │
                                                │ (Pipeline    │
                                                │  cerrado)    │
                                                └──────────────┘
```

> **Nota:** El loop QA → Fix → QA re-test (pasos 3→3a→3) puede iterar múltiples veces
> hasta que QA dé el APROBADO. En Fase 1 ocurrió 1 iteración con 5 issues.
> En Fase 2 ocurrió 1 iteración con 5 bugs más 1 fix post-DevOps (QA-F2-02b).
>
> **Post-Deploy Feedback Loop** (paso 5): Después del deploy, Ron prueba la UI y puede
> encontrar issues de navegación, visuales o funcionales. Estos se corrigen directamente
> (Backend/Frontend → rebuild docker) sin pasar por QA, a menos que el cambio sea crítico.
> En Fase 2 ocurrió 1 iteración: nav links faltantes (🧾 Caja, ➕ Nueva Venta) corregidos
> + manuales actualizados + frontend rebuild.
>
> **User Acceptance (VB Cliente Final)** (paso 6): El usuario final del ERP revisa los
> manuales y la UI, y da el Visto Bueno (VB). Si encuentra discrepancias (ej: botón
> "Cerrar Sesión" que existe en el manual pero no en la UI), Jarvis coordina fixes
> directos (Backend/Frontend) + rebuild + actualización de manuales. El pipeline se
> cierra solo cuando el cliente final da su VB.
>
> **📄 Reporte de validación:** Cada ciclo completo genera:
> `docs/reports/qa-validation-faseX.md`
> con cruce de cada HU (Given/When/Then) vs su resultado real.

### 5.2 Bug Fix

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Reporte  │────▶│ Backend  │────▶│ QA       │────▶│ DevOps   │
│ (QA/BE/FE)│    │ o        │     │ regresión│     │ demo     │
│          │     │ Frontend │     └──────────┘     └──────────┘
└──────────┘     │ (fix)    │
                 └──────────┘
```

### 5.3 Configuración / Infra

```
┌──────────┐     ┌──────────┐
│ Ron      │────▶│ DevOps   │
│          │     │ (directo) │
└──────────┘     └──────────┘
```

### 5.4 Documentación

Se activa en 3 momentos del pipeline:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MOMENTOS DE DOCUMENTACIÓN                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📌 Momento 1: Durante implementación (Backend / Frontend)          │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Backend  │────▶│ Actualiza        │     │ Ej: DB schema,    │    │
│  │ Agent    │     │ apps/backend/    │     │ endpoints,        │    │
│  │          │     │ DEBT.md          │     │ migraciones       │    │
│  └──────────┘     └──────────────────┘     └──────────────────┘    │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Frontend │────▶│ Actualiza        │     │ Ej: componentes,  │    │
│  │ Agent    │     │ apps/web/        │     │ hooks, tipos      │    │
│  │          │     │ DEBT.md          │     │                   │    │
│  └──────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                      │
│  📌 Momento 2: Post-QA (Reporte de Validación)                      │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│              │     │ docs/reports/    │     │ Cada HU contra   │    │
│  │ Reporte  │────▶│ qa-validation-   │     │ su resultado     │    │
│  │ Validac. │     │ faseX.md         │     │ real + issues    │    │
│  │          │     │ (ej: qa-         │     │ corridos QA y    │    │
│  │          │     │  validation-     │     │ fixes aplicados  │    │
│  │          │     │  fase1.md)       │     │                   │    │
│  └──────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                      │
│  📌 Momento 3: Post-Pipeline (Documentación General)               │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Orquest. │────▶│ docs/pipeline-   │     │ Flujo, archivos,  │    │
│  │ (Jarvis) │     │ flow.md          │     │ agentes, lecciones│    │
│  └──────────┘     └──────────────────┘     └──────────────────┘    │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Tech-    │────▶│ docs/manuals/    │     │ Guías de usuario, │    │
│  │ Writer   │     │ guia-*.md        │     │ manuales, README  │    │
│  └──────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Estrategia de Archivos Compartidos

### Principio: Archivos en disco, no adjuntos

Los agentes **no se envían archivos como adjuntos**. Todos trabajan sobre el mismo monorepo en disco:

```
/home/ron/projectos/IaaS-RonSys/
```

### Convención de directorios

| Directorio | Qué contiene | Escrito por |
|------------|-------------|-------------|
| `docs/reports/` | Reportes de análisis técnico | 🏗️ Architecture Agent |
| `docs/reports/qa-validation-*.md` | Validación HU vs resultados | 🧪 QA Agent |
| `docs/backlog/` | Historias Gherkin | 📋 PO Agent |
| `docs/pipeline-flow.md` | Diagrama de flujo del pipeline | 🤖 Jarvis |
| `docs/manuals/` | Guías de usuario y manuales | 📝 TechWriter |
| `apps/backend/app/core/` | Lógica de dominio | 🐍 Backend Agent |
| `apps/backend/app/routers/` | Endpoints HTTP | 🐍 Backend Agent |
| `apps/backend/app/schemas/` | Schemas Pydantic | 🐍 Backend Agent |
| `apps/backend/app/services/` | Servicios de aplicación | 🐍 Backend Agent |
| `apps/backend/app/adapters/db/models/` | Modelos ORM | 🐍 Backend Agent |
| `apps/backend/app/adapters/alembic/versions/` | Migraciones DB | 🐍 Backend Agent |
| `apps/backend/tests/` | Tests backend | 🐍 Backend Agent |
| `apps/backend/DEBT.md` | Deuda técnica backend | 🐍 Backend Agent |
| `apps/web/src/pages/` | Páginas React | ⚛️ Frontend Agent |
| `apps/web/src/components/` | Componentes React | ⚛️ Frontend Agent |
| `apps/web/src/hooks/` | Custom hooks | ⚛️ Frontend Agent |
| `apps/web/src/types/` | Tipos TypeScript | ⚛️ Frontend Agent |
| `apps/web/src/__tests__/` | Tests frontend | ⚛️ Frontend Agent |
| `apps/web/DEBT.md` | Deuda técnica frontend | ⚛️ Frontend Agent |
| `apps/web/dist/` | Build de producción | ⚛️ Frontend Agent |

### Flujo de datos entre agentes

```
                    ┌──────────────────────────────────────┐
                    │          AGENTE EMISOR               │
                    │                                      │
                    │  1. Lee archivo/s del disco          │
                    │  2. Procesa/intelige/se transforma    │
                    │  3. Escribe resultado en disco        │
                    │  4. Responde vía sessions_send()     │
                    │     con: qué hizo, archivos creados   │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │          JARVIS (Orquestador)        │
                    │                                      │
                    │   Recibe confirmación del agente      │
                    │   Lee el archivo generado si necesita  │
                    │   Delega al siguiente agente          │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │          AGENTE RECEPTOR             │
                    │                                      │
                    │  1. Recibe mensaje + ruta(s)         │
                    │  2. Lee archivo/s del disco          │
                    │  3. Trabaja sobre lo existente        │
                    │  4. Escribe nuevo archivo/s en disco  │
                    │  5. Responde confirmación             │
                    └──────────────────────────────────────┘
```

**Importante:** No hay transferencia de archivos vía mensajería. Los mensajes solo contienen:
- Ruta del archivo a leer/procesar
- Instrucciones de qué hacer
- Confirmaciones de finalización + métricas

---

*Documento generado por Jarvis basado en la ejecución real del pipeline de Fase 1 + Fase 2.*
*Modelos: DeepSeek V4 Pro (agentes) / DeepSeek V4 Flash (Jarvis + Chatbot).*
