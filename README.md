# IaaS-RonSys — Intelligence as a Service

> **Sistema ERP SaaS con Agentes de IA para Franquicia "El Segoviano"**
> Monorepo de la plataforma completa.

---

## 📋 Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Backend** | FastAPI (Python) | **3.12.x** ⚠️ |
| **Frontend Web** | React + Vite + Tailwind + TypeScript | Última LTS |
| **App Móvil** | React Native + Expo | Última LTS |
| **Base de Datos** | PostgreSQL + pgvector | 16 |
| **ORM** | SQLAlchemy + Alembic | 2.0 |
| **Cache** | Redis | 7+ |
| **Cola de mensajes** | RabbitMQ | 4+ |
| **Contenedores** | Docker + Docker Compose | Última |
| **CI/CD** | GitHub Actions | — |
| **Monitoreo** | Prometheus + Grafana | — |
| **Logs** | Loki + Grafana | Centralizados |
| **APM** | OpenTelemetry | Trazas distribuidas |
| **Alertas** | AlertManager | — |
| **LLM/IA** | OpenAI / Claude API + LangChain | — |

---

## 🗂️ Estructura del Monorepo

```
IaaS-RonSys/
│
├── apps/                           ← 📱 Aplicaciones del sistema
│   ├── backend/                    ← 🧠 FastAPI Monolito Modular + Hexagonal
│   │   ├── app/
│   │   │   ├── core/               ← Dominio puro (sin dependencias externas)
│   │   │   │   ├── accounting/     ←   Motor contable + Kárdex
│   │   │   │   ├── agents/         ←   Sistema de skills IA
│   │   │   │   ├── inventory/      ←   Gestión de inventarios
│   │   │   │   └── sales/          ←   Ventas / POS
│   │   │   ├── adapters/           ← Implementaciones concretas (DB, APIs)
│   │   │   │   ├── db/models/      ←   SQLAlchemy ORM models
│   │   │   │   ├── db/repositories/←   Implementaciones de puertos
│   │   │   │   └── alembic/        ←   Migraciones de BD
│   │   │   ├── routers/            ← Endpoints FastAPI
│   │   │   ├── schemas/            ← Pydantic (request/response)
│   │   │   ├── services/           ← Orquestación de lógica
│   │   │   └── monitoring/         ← Prometheus, health checks
│   │   ├── tests/                  ← 🧪 Tests (pytest)
│   │   ├── requirements.txt        ← Dependencias Python
│   │   ├── pyproject.toml          ← Proyecto Python
│   │   ├── Dockerfile              ← Imagen del backend
│   │   └── Makefile                ← Comandos útiles
│   │
│   ├── web/                        ← ⚛️ React (frontend de gestión)
│   │   └── ... (futuro)
│   │
│   └── mobile/                     ← 📱 React Native (app móvil)
│       └── ... (futuro)
│
├── infra/                          ← 🔧 DevOps compartido
│   ├── docker/                     ← Dockerfiles personalizados
│   │   ├── backend/
│   │   ├── web/
│   │   └── monitoring/             ← Prometheus, Grafana configs
│   ├── compose/                    ← Docker Compose por entorno
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.prod.yml
│   └── ci/                         ← CI/CD pipelines
│       └── .github/workflows/
│           ├── backend-ci.yml
│           └── deploy.yml
│
├── docs/                           ← 📚 Documentación del proyecto
│   ├── architecture.md             ← Referencia a proyecto-franquicia
│   └── setup.md                    ← Guía de setup local
│
├── scripts/                        ← 🛠️ Scripts auxiliares
├── .env.example                    ← Variables de entorno (template)
├── .gitignore
├── docker-compose.yml              ← Orquestación principal (levanta todo)
├── Makefile                        ← Comandos principales del monorepo
└── README.md                       ← ← Este archivo
```

---

## 🧠 Principio Arquitectónico

**Monolito Modular + Hexagonal (Ports & Adapters)**

```
┌──────────────────────────────────────────────────────────────────┐
│                       ROUTERS (FastAPI)                          │
│  /api/accounting/*  /api/inventory/*  /api/agents/*  /api/sales │
└─────────────────────────┬────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│                        SERVICES (orquestación)                    │
│  SetupService  │  AccountingService  │  AgentOrchestrator         │
└─────────────────────────┬────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│                    CORE (dominio puro)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ Accounting  │  │   Agents     │  │    Inventory/Sales   │    │
│  │ Engine      │  │   BaseSkill  │  │    Domain models     │    │
│  │ Kardex      │  │   Loader     │  │                      │    │
│  │ Statements  │  │              │  │                      │    │
│  │ Cashflow    │  │              │  │                      │    │
│  │ Ratios      │  │              │  │                      │    │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘    │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
│              PUERTOS (interfaces abstractas)                     │
│    AccountingRepository  │  AgentRepository  │  InventoryRepo    │
└──────────────────────────┼───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    ADAPTERS (implementaciones)                    │
│  SQLAlchemyRepository  │  LLMClient  │  RedisCache  │  RabbitMQ  │
│  PostgreSQL            │  OpenAI     │  Sesiones    │  Colas     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🏭 Entornos

IaaS-RonSys tiene **2 entornos** separados, gestionados con `deploy.sh`:

| Característica | 🧪 QA | 🚀 Producción |
|---------------|-------|---------------|
| **Comando** | `./deploy.sh --env qa` | `./deploy.sh --env prod` |
| **Backend** | `:8001` (hot-reload) | `:8000` |
| **Frontend** | Vite dev server `:5173` | Nginx `:80` |
| **Base de datos** | `iaas_ronsys_qa` | `iaas_ronsys` |
| **SSL** | ❌ | Configurable |
| **Propósito** | Desarrollo y pruebas | Demo / cliente final |
| **Env file** | `.env.qa` | `.env.prod` |

```bash
# Entorno QA (pruebas)
./deploy.sh --env qa
# → Backend: http://localhost:8001
# → Frontend: http://localhost:5173

# Entorno Producción
./deploy.sh --env prod
# → Frontend: http://localhost (nginx :80)
# → Backend: http://localhost:8000
```

> 💡 Ambos entornos pueden correr **al mismo tiempo** sin conflictos — usan puertos y bases de datos separadas.

---

## 🚀 Deploy

El despliegue se automatiza con `deploy.sh`, un script **idempotente** (se puede ejecutar múltiples veces sin romper):

```bash
# Desplegar en producción
./deploy.sh --env prod

# Desplegar en QA
./deploy.sh --env qa

# Actualizar (pull + redeploy)
git pull && ./deploy.sh --env prod
```

**Qué hace el script (8 pasos):**
1. Verifica dependencias (Docker, Docker Compose)
2. Configura variables de entorno (genera SECRET_KEY si no existe)
3. Levanta infraestructura base (PostgreSQL + Redis)
4. Construye y levanta servicios del entorno
5. Ejecuta migraciones Alembic
6. Carga seed data (solo si BD vacía)
7. Verifica credenciales demo
8. Muestra resumen con URLs y comandos

📖 Manual completo: [`docs/manuales/guia-despliegue.md`](docs/manuales/guia-despliegue.md)

---

## 🚀 Cómo empezar

> ⚠️ **REQUISITO: Python 3.12.x**  
> El proyecto **NO funciona con Python 3.13+ ni 3.14**. Las dependencias
> nativas (`pydantic-core`, `asyncpg`) no compilan en versiones superiores.
> Usa Python 3.12 exactamente. El Dockerfile ya está configurado con `python:3.12-slim`.
>
> ```bash
> # Verificar versión:
> python3 --version   # Debe mostrar 3.12.x
>
> # Instalar Python 3.12 si es necesario:
> # Ubuntu/Debian: sudo apt install python3.12 python3.12-venv python3.12-dev
> # macOS:         brew install python@3.12
> # pyenv:         pyenv install 3.12 && pyenv local 3.12
> ```

### 1. Archivo .env único (raíz del proyecto)

```bash
cd /home/ron/projectos/IaaS-RonSys
cp .env.example .env
# Editar .env según sea necesario (solo este archivo)
```

**Un solo `.env`** en la raíz. Docker Compose lo lee y lo distribuye a cada servicio. No hay `.env` por subproyecto.

### 2. Opción A: Desarrollo local (sin Docker)

```bash
# Usar Python 3.12 (obligatorio)
cd apps/backend
python3.12 -m venv .venv
source .venv/bin/activate        # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Tener PostgreSQL, Redis y RabbitMQ corriendo localmente
# (o ajustar .env para apuntar a servicios externos)

# Ejecutar pruebas
pytest -v

# Ver demo del motor contable
python scripts/seed.py

# Iniciar servidor de desarrollo
make dev
```

### 3. Opción B: Con Docker (todo incluido) ✅ Recomendado

```bash
# Levantar todos los servicios
docker-compose up -d

# Verificar health
curl http://localhost:8000/api/health

# Ver logs
docker-compose logs -f backend

# Ejecutar migraciones (primera vez)
docker-compose exec backend alembic upgrade head

# Acceder a la documentación de la API
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

### 4. Verificar que todo funciona

| Servicio | URL |
|----------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |

---

## 🧪 Tests

### Suites

| Suite | Tests | Tecnología | Comando |
|-------|:-----:|------------|---------|
| 🧠 **Backend** | **66** (6 suites) | pytest | `pytest -v` |
| ⚛️ **Frontend** | **43** (8 suites) | Jest + RTL | `npx jest --verbose` |
| 🎭 **E2E** | **31** (6 flujos) | Playwright | `npx playwright test` |
| **TOTAL** | **140** | — | `make test-all` |

### Comandos

```bash
# Backend
cd apps/backend
pytest -v                          # Todos los tests (66)
pytest tests/test_accounting_engine.py  # Solo motor contable
pytest -v --cov=app --cov-report=term   # Con cobertura

# Frontend
cd apps/web
npx jest --verbose                 # 43 tests, 8 suites
npx jest --coverage                # Con cobertura
npx tsc --noEmit                   # TypeScript check

# E2E (Playwright)
cd apps/web
npx playwright test                # 31 tests, 6 flujos
npx playwright test --ui           # Con interfaz gráfica
npx playwright show-report         # Ver reporte HTML

# Desde la raíz
make test
```

### Flujos E2E

| # | Flujo | Tests |
|---|-------|:-----:|
| 1 | Login / Logout | 5 |
| 2 | Dashboard KPIs | 3 |
| 3 | Setup Wizard → Simulación | 4 |
| 4 | Reportes (PYG, Balance, BCSS, Ratios) | 7 |
| 5 | Kárdex (CRUD productos, entradas, salidas) | 8 |
| 6 | Settings / Branding | 4 |

---

## 📚 Documentación Vinculada

| Proyecto | Ruta | Propósito |
|----------|------|-----------|
| **proyecto-franquicia** | `../proyecto-franquicia/` | Visión general, gestión, backlog |
| **simulador-financiero** | `../simulador-financiero/` | Documentación técnica detallada del motor |

---

## 🏗️ Módulos del Backend

| # | Módulo | Estado | Documentación |
|---|--------|:------:|---------------|
| 1 | 🧾 **Setup + Accounting Engine** | ✅ | `simulador-financiero/docs/03-logica-contable.md` |
| 2 | 📦 **Kárdex / Inventory** | ✅ | `simulador-financiero/docs/10-kardex.md` |
| 3 | 📊 **Financial Statements (PYG + Balance)** | ✅ | `simulador-financiero/docs/04-estados-financieros.md` |
| 4 | 💰 **Ratios Financieros** | ✅ | `simulador-financiero/docs/06-ratios.md` |
| 5 | 🛣️ **Endpoints REST + Schemas** | ✅ | `apps/backend/app/routers/` |
| 6 | 🗄️ **DB Adapters + Alembic** | ✅ | `apps/backend/app/adapters/` |
| 7 | 📡 **Monitoreo (Prometheus + Logging)** | ✅ | `apps/backend/app/monitoring/` |
| 8 | 🎨 **API Settings / Branding** | ✅ | `apps/backend/app/routers/setup.py` |
| 9 | 🔐 **Auth Multi-Tenant (JWT + RBAC)** | ✅ | `docs/architecture/auth-multi-tenant-design.md` |
| 10 | 💰 **Flujo de Caja** | 🟡 Parcial | `simulador-financiero/docs/05-flujo-caja.md` |
| 11 | 🤖 **Agentes IA (skills)** | 🟡 Puerto diseñado | `simulador-financiero/docs/07-integracion-erp.md` |
| 12 | 🧾 **Sales / POS** | ⬜ Futuro | — |

---

## 🔌 Endpoints del Backend

Base URL: `http://localhost:8000`

### Health
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Health check básico |
| `GET` | `/api/ready` | Readiness (verifica DB) |

### Auth (Multi-Tenant)
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login — retorna access + refresh tokens |
| `POST` | `/api/auth/refresh` | Renovar access token (refresh rotativo) |
| `POST` | `/api/auth/logout` | Revocar refresh token |
| `GET` | `/api/auth/me` | Perfil del usuario actual |

### Admin Users
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/admin/users` | Crear usuario (admin) |
| `GET` | `/api/admin/users` | Listar usuarios del tenant (admin) |

### Contabilidad
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/accounting/setup` | Simulación financiera completa |
| `GET` | `/api/accounting/bcss` | Balance de Comprobación |
| `GET` | `/api/accounting/pyg` | Estado de Resultados |
| `GET` | `/api/accounting/balance` | Balance General |
| `GET` | `/api/accounting/ratios` | Ratios con semáforo 🟢🟡🔴 |
| `POST` | `/api/accounting/transaction` | Registrar transacción manual |
| `POST` | `/api/accounting/validate` | Validar consistencia contable |

### Kárdex / Inventario
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/accounting/kardex/products` | Registrar producto |
| `POST` | `/api/accounting/kardex/entry` | Entrada (compra) |
| `POST` | `/api/accounting/kardex/exit` | Salida (venta/merma) |
| `GET` | `/api/accounting/kardex/{code}` | Kárdex de un producto |
| `GET` | `/api/accounting/kardex/inventory/summary` | Inventario actual |
| `POST` | `/api/accounting/kardex/warehouse-close` | Cierre de almacén |

### Configuración / Branding
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/settings` | Configuración completa |
| `PATCH` | `/api/settings` | Actualizar configuración |
| `GET` | `/api/settings/palette` | Solo paleta de colores |
| `PATCH` | `/api/settings/palette` | Cambiar paleta |

> 📖 Schemas completos en `apps/backend/app/schemas/__init__.py`  
> 📖 Swagger UI en `http://localhost:8000/docs`

## 📘 Manuales de Usuario

| Documento | Audiencia | Contenido |
|-----------|-----------|-----------|
| [**Guía de Inicio Rápido**](docs/manuales/guia-inicio-rapido.md) | Todos los usuarios | Primeros pasos, credenciales, navegación |
| [**Manual de Usuario**](docs/manuales/manual-usuario.md) | Todos los usuarios | Guía completa de cada módulo |
| [**Manual de Administrador**](docs/manuales/manual-admin.md) | Rol `admin` | Gestión de usuarios, seguridad, troubleshooting |
| [**Guía de Despliegue**](docs/manuales/guia-despliegue.md) | DevOps / TI | Entornos, deploy, infraestructura |

---

## 👥 Equipo

| Persona | Rol | Código |
|---------|-----|--------|
| 🧑‍💻 Ron | Backend + IA + Devops + Frontend | `apps/backend/`, `infra/` |
| 👨‍🍳 Nilton | Operaciones (no código) | — |

---

## ⏰ Recordatorios Técnicos

**Al tocar código de agentes IA o tareas pesadas** → diseñar interfaces hexagonales (puertos abstractos) primero.

Ver `../proyecto-franquicia/gestion/recordatorios.md`
