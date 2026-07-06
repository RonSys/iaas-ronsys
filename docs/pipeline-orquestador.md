# 🔄 Pipeline de Orquestación — IaaS-RonSys

> **Autor:** Asistente (ChatBot)  
> **Fecha:** 2026-05-11  
> **Versión:** 1.0  
> **Propósito:** Documentar cómo el orquestador (Jarvis) coordina a los agentes,  
> y servir de base para la asignación de modelos por agente (OpenRouter).

---

## 📊 Diagrama General del Pipeline

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
│  • Coordina el pipeline vía sessions_send / sessions_spawn              │
│  • Entrega resultados finales a Ron                                     │
│                                                                         │
│  Modelo recomendado: DeepSeek V4 Pro / Kimi K2.6 (alta complejidad)     │
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
                    └──────┬───────┘                 │
                           │                         │
                           ▼                         │
                    ┌──────────────────────────────┐ │
                    │       🔧 DEVOPS Agent        │◄┘
                    │  • Docker Compose             │
                    │  • deploy.sh                  │
                    │  • Demo funcional             │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                              ┌─────────┐
                              │   RON   │
                              │ (Demo)  │
                              └─────────┘

   ┌──────────────────────────────────────────────┐
   │  📘 TechWriter (sub-agente de Jarvis)        │
   │  • Se invoca bajo demanda para docs           │
   │  • No forma parte del pipeline secuencial     │
   └──────────────────────────────────────────────┘
```

---

## 🔌 Cómo se Comunican los Agentes

| Mecanismo | Usado por | Efecto |
|-----------|-----------|--------|
| **`sessions_send`** | Jarvis → agentes persistentes | Envía mensaje al agente, espera su respuesta, retoma el pipeline |
| **`sessions_spawn`** | Jarvis → sub-agentes efímeros | Lanza tarea aislada, el sub-agente notifica al terminar |
| **`subagents` (steer/kill)** | Jarvis | Monitoreo y control de sub-agentes en vuelo |

### Agentes Persistentes vs Efímeros

| Tipo | Agentes | Sesión | Inicio |
|------|---------|--------|--------|
| **Persistente** | PO, Architecture, Backend, Frontend, QA, DevOps | `agent:<id>:main` | Deben estar corriendo (abiertos en Control UI) |
| **Efímero** | TechWriter | Sub-agente (`sessions_spawn`) | Se crea y destruye por tarea |

> ⚠️ **Los agentes persistentes DEBEN tener sesión activa** para recibir `sessions_send`.  
> Si el gateway se reinicia, sus sesiones se pierden y Jarvis debe esperar a que se reabran.

---

## 📋 Pipeline por Tipo de Requerimiento

### 1. Nueva Funcionalidad (con impacto arquitectónico)

```
PASO 0: PO Agent → Cuestionario PO→Cliente (11 categorías)
         │  Entrada: Requerimiento de Ron en lenguaje natural
         │  Salida:  Ficha de Proyecto (11 categorías con ~60 parámetros)
         │
PASO 1: Architecture Agent → Ficha técnica + decisión tecnológica
         │  Entrada: Ficha de Proyecto del PO
         │  Salida:  Documento de diseño (patrón, BD, cache, infra, riesgos)
         │
PASO 2: PO Agent → Historias Gherkin (Given/When/Then)
         │  Entrada: Ficha técnica del Architecture Agent
         │  Salida:  Historias de usuario con criterios de aceptación Gherkin
         │
PASO 3: Backend Agent + Frontend Agent (PARALELO) → Implementación
         │  Entrada: Historias Gherkin del PO
         │  Salida:  Código implementado + tests unitarios
         │
PASO 4: QA Agent → Validación
         │  ├── Unitarios: pytest (66 tests backend) + jest (43 tests frontend)
         │  ├── Type check: tsc --noEmit
         │  ├── Build: vite build
         │  └── E2E: Playwright (31 tests, 6 flujos de usuario)
         │  Salida: Matriz PASS/FAIL + bugs documentados + veredicto
         │
PASO 5: DevOps Agent → Demo / Deploy
         │  Entrada: Veredicto QA ✅
         │  Salida:  URL de demo + estado de servicios
         │
PASO 6: Jarvis → Reporte a Ron
          Entrada: Resultados de todos los pasos
          Salida:  Resumen ejecutivo con URLs, veredictos, bugs
```

### 2. Bug Fix

```
PASO 1: Backend Agent / Frontend Agent → Fix
         │  Según dónde esté el bug
         │
PASO 2: QA Agent → Validación + Regresión
         │  Corre la suite completa para confirmar que no hay regresiones
         │
PASO 3: DevOps Agent → Demo / Deploy
         │
PASO 4: Jarvis → Reporte a Ron
```

### 3. Documentación

```
PASO 1: TechWriter (sub-agente vía sessions_spawn) → Documento
         │  Entrada: Tema + contexto del proyecto
         │  Salida:  Archivo .md en docs/
         │
PASO 2: Jarvis → Reporte a Ron
```

### 4. Infraestructura / Configuración

```
PASO 1: DevOps Agent directamente → Deploy / fix de infra
         │
PASO 2: Jarvis → Reporte a Ron
```

---

## 🤖 Perfiles de Agentes (para asignación de modelos)

### Matriz de Complejidad

| Agente | Complejidad | Razonamiento | Herramientas | Tokens/sesión | Modelo (Realista) |
|--------|:-----------:|:------------:|-------------|:-------------:|--------------------|
| **Jarvis** | 🔴 Alta | Alto (orquestación) | `sessions_send`, `sessions_spawn` | Alto (coordina todo) | **DeepSeek V4 Pro** |
| **Architecture** | 🔴 Alta | Alto (investigación) | `web_search`, `web_fetch` | Medio-Alto | **Grok 4.3** |
| **Backend Dev** | 🔴 Alta | Alto (código complejo) | `edit`, `write`, `exec` | Medio-Alto | **Kimi K2.6** |
| **Frontend Dev** | 🟡 Media | Medio (UI/components) | `edit`, `write`, `exec` | Medio | **Kimi K2.6** |
| **PO Agent** | 🟡 Media | Medio (análisis reqs) | `read`, `write` | Bajo-Medio | **Kimi K2.6** |
| **QA Agent** | 🟢 Baja-Media | Bajo (ejecución) | `exec` (pytest, jest) | Bajo | **Ring-2.6-1T 🆓** |
| **DevOps Agent** | 🟢 Baja-Media | Bajo (ejecución) | `exec` (docker) | Bajo | **Ring-2.6-1T 🆓** |
| **TechWriter** | 🟢 Baja | Bajo (redacción) | `write`, `edit` | Bajo | **Owl Alpha 🆓** |

### Fichas Técnicas por Agente

---

#### 🤖 Jarvis — Orquestador Central

| Campo | Valor |
|-------|-------|
| **Agent ID** | `jarvis` |
| **Session Key** | `agent:jarvis:main` |
| **Workspace** | `/home/ron/.openclaw/workspace/` |
| **Tipo** | Persistente |
| **Rol** | Coordinar el pipeline completo |
| **Herramientas clave** | `sessions_send`, `sessions_spawn`, `subagents` |
| **Entradas** | Requerimiento de Ron en lenguaje natural |
| **Salidas** | Reporte ejecutivo con URLs, veredictos, bugs |
| **No hace** | No implementa código, no ejecuta tests, no despliega |
| **Complejidad** | 🔴 Alta — razonamiento multi-step, coordinación de dependencias |
| **Modelo** | **DeepSeek V4 Pro** — necesita máxima capacidad de razonamiento |
| **Modelo Realista** | ⬆ Mismo — cerebro central, el único que justifica premium |

---

#### 📋 Product Owner Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `product-owner-agent` |
| **Session Key** | `agent:product-owner-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/product-owner/` |
| **Tipo** | Persistente |
| **Rol** | Traducir requerimientos a historias Gherkin |
| **Herramientas clave** | `read`, `write` |
| **Entradas** | Requerimiento de Jarvis (brief) |
| **Salidas** | Historias de usuario + criterios Gherkin + Ficha de Proyecto |
| **No hace** | No toca código, infraestructura ni pruebas |
| **Cuestionario** | 11 categorías (~60 parámetros) para funcionalidades nuevas |
| **Complejidad** | 🟡 Media — análisis estructurado, formato consistente |
| **Modelo** | **Kimi K2.6** — buena relación costo/calidad para análisis |
| **Modelo Realista** | ⬆ Mismo — Gherkin estructurado, formato consistente |

---

#### 🏗️ Architecture Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `architecture-agent` |
| **Session Key** | `agent:architecture-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/architecture-agent/` |
| **Tipo** | Persistente |
| **Rol** | Investigar y decidir patrones de arquitectura |
| **Herramientas clave** | `web_search`, `web_fetch`, `read`, `write` |
| **Entradas** | Ficha de Proyecto del PO Agent |
| **Salidas** | Documento de diseño técnico (patrón, BD, cache, infra, riesgos) |
| **No hace** | No implementa código ni infraestructura |
| **Complejidad** | 🔴 Alta — investigación web + síntesis técnica |
| **Modelo** | **Grok 4.3** — razonamiento + 1M contexto, mitad de precio que DeepSeek |
| **Modelo Realista** | ⬆ Mismo — research web con máximo contexto |

---

#### 🧠 Backend Developer Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `backend-dev-agent` |
| **Session Key** | `agent:backend-dev-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/backend-dev/` |
| **Tipo** | Persistente |
| **Rol** | Implementar APIs, lógica de negocio, migraciones, tests |
| **Herramientas clave** | `edit`, `write`, `exec` (pytest, alembic, pip) |
| **Stack** | FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Python 3.12 |
| **Entradas** | Historias Gherkin del PO Agent |
| **Salidas** | Código implementado en `apps/backend/` + tests unitarios |
| **No hace** | No toca frontend, no despliega, no hace docs de usuario |
| **Complejidad** | 🔴 Alta — arquitectura hexagonal, motor contable, auth JWT |
| **Modelo** | **Kimi K2.6** — código complejo, 4× más barato que DeepSeek |
| **Modelo Realista** | ⬆ Mismo — coding specialist, la mejor relación costo/calidad |

---

#### ⚛️ Frontend Developer Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `frontend-dev-agent` |
| **Session Key** | `agent:frontend-dev-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/frontend-dev/` |
| **Tipo** | Persistente |
| **Rol** | Construir componentes UI, conectar APIs, probar interfaz |
| **Herramientas clave** | `edit`, `write`, `exec` (npm, jest, tsc) |
| **Stack** | React 18 + Vite + TailwindCSS + TypeScript |
| **Entradas** | Historias Gherkin del PO Agent (parte visual) |
| **Salidas** | Componentes en `apps/web/src/` + tests |
| **No hace** | No toca backend, no despliega |
| **Complejidad** | 🟡 Media — componentes, hooks, formularios, charts |
| **Modelo** | **Kimi K2.6** — buen rendimiento en código frontend |
| **Modelo Realista** | ⬆ Mismo — React/TS, consistencia con Backend |

---

#### 🧪 QA Automation Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `qa-agent` |
| **Session Key** | `agent:qa-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/qa/` |
| **Tipo** | Persistente |
| **Rol** | Ejecutar batería de pruebas, dar veredicto |
| **Herramientas clave** | `exec` (pytest, jest, tsc, Playwright) |
| **Suites** | Backend: 66 tests (pytest) · Frontend: 43 tests (jest) · E2E: 31 tests (Playwright) |
| **Entradas** | Código implementado + historias Gherkin |
| **Salidas** | Matriz PASS/FAIL + bugs + veredicto ✅/❌ |
| **No hace** | No implementa fixes, no despliega |
| **Complejidad** | 🟢 Baja-Media — ejecución de comandos, análisis de output |
| **Modelo** | **Ring-2.6-1T (FREE)** — tareas de ejecución, no generación |
| **Modelo Realista** | ⬆ Mismo — ejecución de suites no justifica modelo pago |

---

#### 🔧 DevOps / Platform Agent

| Campo | Valor |
|-------|-------|
| **Agent ID** | `devops-agent` |
| **Session Key** | `agent:devops-agent:main` |
| **Workspace** | `~/projectos/segoviano/agents/devops/` |
| **Tipo** | Persistente |
| **Rol** | Mantener infraestructura, desplegar, reportar estado |
| **Herramientas clave** | `exec` (docker, docker compose, deploy.sh) |
| **Stack** | Docker Compose V2, PostgreSQL 16, Redis 7, RabbitMQ 4, Nginx |
| **Entradas** | Veredicto QA ✅ + necesidad de demo |
| **Salidas** | URLs de servicios + estado de salud |
| **No hace** | No implementa features, no escribe tests |
| **Complejidad** | 🟢 Baja-Media — comandos Docker, verificación de salud |
| **Modelo** | **Ring-2.6-1T (FREE)** — tareas operativas repetitivas |
| **Modelo Realista** | ⬆ Mismo — tareas operativas no justifican modelo pago |

---

#### 📘 TechWriter (Documentador)

| Campo | Valor |
|-------|-------|
| **Agent ID** | `tech-writer` (sub-agente) |
| **Session Key** | N/A — se invoca con `sessions_spawn` |
| **Workspace** | `~/projectos/segoviano/agents/tech-writer/` |
| **Tipo** | Efímero (sub-agente) |
| **Rol** | Crear/actualizar documentación |
| **Herramientas clave** | `write`, `edit`, `read` |
| **Entradas** | Tema + contexto del proyecto |
| **Salidas** | Archivos .md en `docs/` |
| **No hace** | No implementa código, no despliega |
| **Complejidad** | 🟢 Baja — redacción estructurada, uso de templates |
| **Modelo** | **Owl Alpha (FREE)** — 1M contexto, tool use nativo |
| **Modelo Realista** | ⬆ Mismo — documentación no justifica modelo pago |

---

## 💰 Estrategia de Modelos por Agente (OpenRouter)

### Modelos disponibles (precios reales OpenRouter API)

| Modelo | Input/1M | Output/1M | Contexto | Tools | Especialidad |
|--------|:--------:|:---------:|:--------:|:-----:|-------------|
| **Claude 4.6 Sonnet** | $3.00 | $15.00 | 200K | ✅ | Mejor coding + razonamiento |
| **DeepSeek V4 Pro** | ~$2.50 | ~$10.00 | 128K | ✅ | Tu modelo actual, probado |
| **Mistral Medium 3.5** | $1.50 | $7.50 | 262K | ✅ | 128B params, agentic coding |
| **Kimi K2.6** | ~$0.55 | ~$2.65 | 262K | ✅ | Coding agent, 1T params, 32B activos |
| **Grok 4.3** | $1.25 | $2.50 | 1M | ✅ | Reasoning, instruction-following |
| **Gemini 3.1 Flash Lite** | $0.25 | $1.50 | 1M | ✅ | Multimodal, ultra-barato |
| **Ring-2.6-1T** 🆓 | $0 | $0 | 262K | ✅ | 1T params, coding agent |
| **Owl Alpha** 🆓 | $0 | $0 | 1M | ✅ | Agentic, tool use nativo |
| **Laguna M.1** 🆓 | $0 | $0 | 131K | ✅ | Poolside coding flagship |
| **CoBuddy** 🆓 | $0 | $0 | 131K | ✅ | Baidu code generation |

---

## 🎯 3 Escenarios de Presupuesto

> **Criterio clave:** Todos los modelos seleccionados están enfocados en **codificación y agentes**. No se sacrifica calidad de código en ningún escenario — la diferencia está en cuántos agentes usan modelos premium vs value vs free.

---

### 🟢 ESCENARIO PESIMISTA — "Frugal pero Potente"

**Presupuesto: ~$3-5/mes** · 3 agentes con modelos pagos · 5 agentes con modelos FREE

| Agente | Modelo | Input/1M | Output/1M | ¿Por qué? |
|--------|--------|:--------:|:---------:|-----------|
| 🤖 Jarvis | **Kimi K2.6** | $0.55 | $2.65 | Orquestador con coding specialist de 1T params |
| 🏗️ Architecture | **Grok 4.3** | $1.25 | $2.50 | Razonamiento + 1M contexto para research |
| 🧠 Backend Dev | **Kimi K2.6** | $0.55 | $2.65 | Código Python/FastAPI — su especialidad |
| ⚛️ Frontend Dev | **Ring-2.6-1T 🆓** | $0 | $0 | 1T params, 63B activos, coding agent, tools |
| 📋 PO Agent | **Owl Alpha 🆓** | $0 | $0 | 1M contexto, tool use nativo, agentic |
| 🧪 QA Agent | **Ring-2.6-1T 🆓** | $0 | $0 | Ejecuta comandos, analiza outputs |
| 🔧 DevOps | **Laguna M.1 🆓** | $0 | $0 | Coding flagship de Poolside, tools |
| 📘 TechWriter | **Owl Alpha 🆓** | $0 | $0 | 1M contexto para documentación larga |

| 💵 Costo mensual | **~$3.00** |
|---|---|
| Modelos pagos | 3 (Jarvis, Architecture, Backend) |
| Modelos gratis | 5 |
| Crédito mínimo | $5/mes |

---

### 🟡 ESCENARIO REALISTA — "Sweet Spot" ⭐ RECOMENDADO

**Presupuesto: ~$5-8/mes** · 5 agentes con modelos pagos · Solo Jarvis usa DeepSeek

| Agente | Modelo | Input/1M | Output/1M | ¿Por qué? |
|--------|--------|:--------:|:---------:|-----------|
| 🤖 Jarvis | **DeepSeek V4 Pro** | $2.50 | $10.00 | Cerebro central — el único que justifica premium |
| 🏗️ Architecture | **Grok 4.3** | $1.25 | $2.50 | Razonamiento + 1M contexto, mitad de DeepSeek |
| 🧠 Backend Dev | **Kimi K2.6** | $0.55 | $2.65 | Coding specialist, 4× más barato que DeepSeek |
| ⚛️ Frontend Dev | **Kimi K2.6** | $0.55 | $2.65 | React/TS — consistencia con Backend |
| 📋 PO Agent | **Kimi K2.6** | $0.55 | $2.65 | Gherkin estructurado, análisis de requisitos |
| 🧪 QA Agent | **Ring-2.6-1T 🆓** | $0 | $0 | Ejecución de suites, análisis de resultados |
| 🔧 DevOps | **Ring-2.6-1T 🆓** | $0 | $0 | Docker, health checks, deploy |
| 📘 TechWriter | **Owl Alpha 🆓** | $0 | $0 | Documentación, 1M contexto |

| 💵 Costo mensual | **~$5.00** |
|---|---|
| Modelos pagos | 5 (Jarvis, Arch, Backend, Frontend, PO) |
| Modelos gratis | 3 |
| Crédito mínimo | $10/mes (sobra margen) |

---

### 🔴 ESCENARIO OPTIMISTA — "Sin Límites"

**Presupuesto: ~$15-25/mes** · Los mejores modelos de codificación · 6 agentes pagos

| Agente | Modelo | Input/1M | Output/1M | ¿Por qué? |
|--------|--------|:--------:|:---------:|-----------|
| 🤖 Jarvis | **Claude 4.6 Sonnet** | $3.00 | $15.00 | El mejor para orquestación y razonamiento |
| 🏗️ Architecture | **Grok 4.3** | $1.25 | $2.50 | 1M contexto, razonamiento, web search |
| 🧠 Backend Dev | **Claude 4.6 Sonnet** | $3.00 | $15.00 | Código de producción de máxima calidad |
| ⚛️ Frontend Dev | **DeepSeek V4 Pro** | $2.50 | $10.00 | UI compleja, TypeScript avanzado |
| 📋 PO Agent | **Kimi K2.6** | $0.55 | $2.65 | Gherkin — no necesita modelo top |
| 🧪 QA Agent | **Kimi K2.6** | $0.55 | $2.65 | Análisis de fallos, debugging |
| 🔧 DevOps | **Ring-2.6-1T 🆓** | $0 | $0 | Comandos operativos |
| 📘 TechWriter | **Owl Alpha 🆓** | $0 | $0 | Documentación |

| 💵 Costo mensual | **~$18.00** |
|---|---|
| Modelos premium | 3 (Claude ×2, DeepSeek) |
| Modelos value | 3 (Grok, Kimi ×2) |
| Modelos gratis | 2 |
| Crédito mínimo | $20/mes |

---

## 📊 Comparativa de Escenarios

| | 🟢 Pesimista | 🟡 Realista ⭐ | 🔴 Optimista |
|---|:--:|:--:|:--:|
| **Costo/mes** | ~$3.00 | ~$5.00 | ~$18.00 |
| **Crédito sugerido** | $5 | $10 | $20 |
| **Modelos pagos** | 3 | 5 | 6 |
| **Modelos FREE** | 5 | 3 | 2 |
| **Jarvis** | Kimi K2.6 | DeepSeek V4 Pro | Claude 4.6 Sonnet |
| **Architecture** | Grok 4.3 | Grok 4.3 | Grok 4.3 |
| **Backend Dev** | Kimi K2.6 | Kimi K2.6 | Claude 4.6 Sonnet |
| **Frontend Dev** | Ring-2.6-1T 🆓 | Kimi K2.6 | DeepSeek V4 Pro |
| **PO Agent** | Owl Alpha 🆓 | Kimi K2.6 | Kimi K2.6 |
| **QA Agent** | Ring-2.6-1T 🆓 | Ring-2.6-1T 🆓 | Kimi K2.6 |
| **DevOps** | Laguna M.1 🆓 | Ring-2.6-1T 🆓 | Ring-2.6-1T 🆓 |
| **TechWriter** | Owl Alpha 🆓 | Owl Alpha 🆓 | Owl Alpha 🆓 |
| **Calidad de código** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🚀 Plan de Acción Recomendado

1. **Empezar con escenario REALISTA** ($10 crédito OpenRouter)
2. Configurar OpenRouter como provider en OpenClaw (`base_url: https://openrouter.ai/api/v1`)
3. Asignar modelos según la tabla del escenario Realista
4. Evaluar después de 1 mes:
   - Si Kimi K2.6 rinde bien en Backend → mantener
   - Si necesita más calidad → subir Backend a DeepSeek V4 Pro
   - Si el costo es muy bajo → considerar subir a Optimista
   - Si el presupuesto aprieta → bajar a Pesimista

---

## ⚠️ Puntos de Atención

### Sesiones persistentes
- Los 6 agentes principales (PO, Arch, Backend, Frontend, QA, DevOps) dependen de sesiones activas
- Si el gateway se reinicia, **todas las sesiones se pierden** y deben reabrirse desde la Control UI
- Jarvis (orquestador) no puede enviar `sessions_send` a un agente sin sesión activa

### Workspaces aislados
- Cada agente tiene su propio workspace — no comparten contexto de conversación
- Jarvis debe incluir **TODO el contexto necesario** en cada `sessions_send`
- Los archivos en `/home/ron/projectos/IaaS-RonSys/` son accesibles por todos los agentes

### Dependencias del pipeline
```
PO ──→ Architecture ──→ PO ──→ Backend + Frontend ──→ QA ──→ DevOps
 │          │              │          │                   │        │
 │          │              │          └─ PARALELO ────────┘        │
 │          │              └─ Secuencial (PO necesita ficha Arch)  │
 │          └─ Secuencial (Arch necesita Ficha de PO)              │
 └─ Secuencial (PO necesita requerimiento de Jarvis)               │
                                                                    │
 └── Todo secuencial después de Backend+Frontend ──────────────────┘
```

---

## 🚀 Flujo de Inicio Rápido

```
1. Ron abre Control UI → inicia sesión de JARVIS
2. Ron da requerimiento a JARVIS
3. JARVIS analiza → determina tipo de pipeline
4. JARVIS verifica que los agentes necesarios tengan sesión activa
5. JARVIS ejecuta el pipeline paso a paso con sessions_send
6. JARVIS entrega reporte final a Ron
```

---

> **Próximo paso:** Configurar OpenRouter en OpenClaw y asignar modelos según esta matriz.  
> **Referencia:** `../proyecto-franquicia/gestion/recordatorios.md`
