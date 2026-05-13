# 🏗️ Arquitectura de Agentes y Pipeline — IaaS-RonSys

> **Autor:** Jarvis (Orquestador)  
> **Fecha:** 2026-05-11  
> **Versión:** 1.0

---

## 📊 Diagrama de Agentes

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              RON                                        │
│                     (Product Owner / Cliente)                           │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ requerimiento
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           🤖 JARVIS                                     │
│                      (Orquestador Central)                              │
│                                                                         │
│  • Recibe requerimientos de Ron                                        │
│  • Traduce a briefs para cada agente                                    │
│  • Coordina el pipeline                                                 │
│  • Entrega resultados finales                                           │
└───────┬──────────┬──────────┬──────────┬───────────┬────────────────────┘
        │          │          │          │           │
        ▼          ▼          ▼          ▼           ▼
   ┌─────────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
   │   📋    │ │ 🏗️  │ │  🧠   │ │  ⚛️   │ │    🔧        │
   │   PO    │ │ ARCH │ │ BACKEND│ │FRONTEND│ │   DEVOPS     │
   │  Agent  │ │Agent │ │  Agent │ │ Agent  │ │   Agent      │
   └────┬────┘ └──┬───┘ └───┬────┘ └───┬────┘ └──────┬───────┘
        │         │         │          │              │
        │    ┌────┘         │          │              │
        ▼    ▼              │          │              │
   ┌────────────────┐       │          │              │
   │  📋 Historias  │       │          │              │
   │    Gherkin     │       │          │              │
   └───────┬────────┘       │          │              │
           │                │          │              │
           └────────┬───────┘          │              │
                    │                  │              │
                    ▼                  ▼              │
              ┌──────────────────────────┐           │
              │   🧠 BACKEND + ⚛️ FRONTEND │          │
              │     (Implementación)      │           │
              └────────────┬─────────────┘           │
                           │                         │
                           ▼                         │
                    ┌──────────────┐                 │
                    │   🧪 QA      │                 │
                    │   Agent      │                 │
                    │              │                 │
                    │ • pytest     │                 │
                    │ • jest       │                 │
                    │ • tsc        │                 │
                    │ • Playwright │                 │
                    └──────┬───────┘                 │
                           │                         │
                           ▼                         │
                    ┌──────────────────────────────┐ │
                    │       🔧 DEVOPS Agent        │◄┘
                    │                              │
                    │  • Docker / deploy.sh         │
                    │  • Entornos QA + Prod         │
                    │  • Demo funcional             │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                              ┌─────────┐
                              │   RON   │
                              │ (Demo)  │
                              └─────────┘
```

---

## 🔄 Pipeline por Tipo de Requerimiento

### Nueva Funcionalidad
```
PASO 0: PO Agent → Cuestionario PO→Cliente (11 categorías)
         │
PASO 1: Architecture Agent → Ficha técnica + decisión tecnológica
         │
PASO 2: PO Agent → Historias Gherkin (Given/When/Then)
         │
PASO 3: Backend Agent + Frontend Agent (PARALELO) → Implementación
         │
PASO 4: QA Agent → Validación
         │    ├── Unitarios: pytest (backend) + jest (frontend)
         │    ├── Type check: tsc --noEmit
         │    ├── Build: vite build
         │    └── E2E: Playwright (31 tests, 6 flujos)
         │
PASO 5: DevOps Agent → Demo / Deploy
         │
PASO 6: Jarvis → Reporte a Ron
```

### Bug Fix
```
PASO 1: Frontend Agent / Backend Agent → Fix
PASO 2: QA Agent → Validación + Regresión
PASO 3: DevOps Agent → Demo / Deploy
PASO 4: Jarvis → Reporte a Ron
```

### Documentación
```
PASO 1: TechWriter (sub-agente) → Manuales, guías, README
PASO 2: Jarvis → Reporte a Ron
```

---

## 🤖 Tabla de Agentes

| # | Agente | Session Key | Rol | Herramientas |
|---|--------|------------|-----|-------------|
| 1 | **Jarvis** | `agent:jarvis:main` | 🎯 Orquestador | `sessions_send`, `sessions_spawn` |
| 2 | **PO Agent** | `agent:product-owner-agent:main` | 📋 Historias Gherkin | Cuestionario PO→Cliente, Gherkin |
| 3 | **Architecture** | `agent:architecture-agent:main` | 🏗️ Decisiones técnicas | `web_search`, `web_fetch` |
| 4 | **Backend Dev** | `agent:backend-dev-agent:main` | 🧠 FastAPI + PostgreSQL | `edit`, `write`, `exec` |
| 5 | **Frontend Dev** | `agent:frontend-dev-agent:main` | ⚛️ React + Vite | `edit`, `write`, `exec` |
| 6 | **QA Agent** | `agent:qa-agent:main` | 🧪 Pruebas | pytest, jest, tsc, Playwright |
| 7 | **DevOps Agent** | `agent:devops-agent:main` | 🔧 Docker + Deploy | Docker Compose, `deploy.sh` |
| 8 | **TechWriter** | Sub-agente de Jarvis | 📘 Documentación | `write`, `edit`, `read` |

---

## 📊 Suite de Calidad

```
┌────────────────────────────────────────────────────────────┐
│                    🧪 QA VALIDATION                        │
│                                                            │
│  Nivel 1: Unitarios                                        │
│  ├── Backend: pytest (66 tests)                            │
│  ├── Frontend: jest (43 tests)                             │
│  └── Type check: tsc --noEmit                              │
│                                                            │
│  Nivel 2: Build + Integración                              │
│  ├── Build: vite build                                     │
│  └── Coverage: pytest --cov + jest --coverage              │
│                                                            │
│  Nivel 3: E2E (Playwright)                                 │
│  ├── login.spec.ts (7 tests)                               │
│  ├── dashboard.spec.ts (5 tests)                           │
│  ├── simulador.spec.ts (5 tests)                           │
│  ├── reportes.spec.ts (4 tests)                            │
│  ├── kardex.spec.ts (6 tests)                              │
│  └── settings.spec.ts (4 tests)                            │
│                                                            │
│  TOTAL: 140 tests                                          │
└────────────────────────────────────────────────────────────┘
```

---

## 🏭 Entornos

```
┌── QA (:8001 + :5173) ──────────────────────────┐
│  docker compose -f docker-compose.yml            │
│                  -f docker-compose.qa.yml        │
│                                                  │
│  Backend:  hot-reload, DEBUG=true                │
│  Frontend: Vite dev server                       │
│  DB:       iaas_ronsys_qa                        │
│  Uso:      Desarrollo y pruebas                  │
└──────────────────────────────────────────────────┘

┌── PRODUCCIÓN (:8000 + :80) ─────────────────────┐
│  docker compose -f docker-compose.yml            │
│                  -f docker-compose.prod.yml      │
│                                                  │
│  Backend:  estable, DEBUG=false                  │
│  Frontend: nginx estático                        │
│  DB:       iaas_ronsys                           │
│  Uso:      Demo / Cliente final                  │
└──────────────────────────────────────────────────┘

┌── Infra Compartida ─────────────────────────────┐
│  PostgreSQL 16    :5432                          │
│  Redis 7          :6379                          │
│  RabbitMQ 4       :5672                          │
└──────────────────────────────────────────────────┘
```

---

## 📁 Workspaces

| Agente | Ruta |
|--------|------|
| Jarvis (orquestador) | `/home/ron/.openclaw/workspace/` |
| Backend Dev | `~/projectos/segoviano/agents/backend-dev/` |
| Frontend Dev | `~/projectos/segoviano/agents/frontend-dev/` |
| DevOps | `~/projectos/segoviano/agents/devops/` |
| Product Owner | `~/projectos/segoviano/agents/product-owner/` |
| QA | `~/projectos/segoviano/agents/qa/` |
| Architecture | `~/projectos/segoviano/agents/architecture-agent/` |
| TechWriter | `~/projectos/segoviano/agents/tech-writer/` |

---

> **Nota:** Jarvis usa `sessions_send` para delegar a agentes independientes y `sessions_spawn` para sub-agentes (TechWriter). Los agentes independientes tienen sesiones persistentes; los sub-agentes son efímeros.
