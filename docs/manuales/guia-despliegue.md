# 🚀 Guía de Despliegue — IaaS-RonSys

> ERP SaaS con motor contable, autenticación multi-tenant, flujo de caja, kárdex, POS y simulador financiero.
> Versión: v0.2.0 | Stack: FastAPI + React 19 + PostgreSQL 16 + Redis 7 + RabbitMQ 4

---

## 📋 Índice

1. [Requisitos Previos](#1-requisitos-previos)
2. [Despliegue Rápido](#2-despliegue-rápido)
3. [Verificación](#3-verificación)
4. [Credenciales Demo](#4-credenciales-demo)
5. [Arquitectura de Servicios](#5-arquitectura-de-servicios)
6. [Comandos Útiles](#6-comandos-útiles)
7. [Troubleshooting](#7-troubleshooting)
8. [Entornos](#8-entornos)
9. [Playwright E2E Tests](#9-playwright-e2e-tests)
10. [Actualizar el Proyecto](#10-actualizar-el-proyecto)

---

## 1. Requisitos Previos

| Dependencia | Versión Mínima | Verificación |
|-------------|---------------|--------------|
| **Sistema Operativo** | Linux Mint 22+ / Ubuntu 24.04+ | `cat /etc/os-release` |
| **Docker** | 24+ | `docker --version` |
| **Docker Compose** | v2 (incluido con Docker) | `docker compose version` |
| **Node.js** | 20.x | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Git** | 2+ | `git --version` |

### Instalación rápida (Ubuntu/Linux Mint)

```bash
# Docker + Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar para aplicar el grupo docker

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Git
sudo apt install -y git
```

> ⚠️ **Nota sobre Python**: El backend se ejecuta en Docker con `python:3.12-slim`. **No necesitas Python 3.12 en el host.** Si tu host tiene Python 3.13+, no hay problema — Docker se encarga.

---

## 2. Despliegue Rápido

### Opción A: Script automático (recomendado)

```bash
git clone https://github.com/tu-org/IaaS-RonSys.git
cd IaaS-RonSys
chmod +x deploy.sh
./deploy.sh
```

El script es **idempotente** — puedes ejecutarlo múltiples veces sin romper nada. Detecta si es primer deploy o redeploy.

### Opción B: Paso a paso manual

```bash
# 1. Clonar
git clone https://github.com/tu-org/IaaS-RonSys.git && cd IaaS-RonSys

# 2. Configurar entorno
cp .env.example .env
# Generar SECRET_KEY:
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env

# 3. Levantar infraestructura
docker compose up -d postgres redis
# Esperar ~10s a que estén healthy

# 4. Construir y levantar backend
docker compose build backend
docker compose up -d backend

# 5. Migraciones
docker exec -w /app iaas-backend env PYTHONPATH=/app alembic upgrade head

# 6. Seed data
docker exec -w /app iaas-backend env PYTHONPATH=/app python scripts/seed_db.py

# 7. Frontend
cd apps/web
npm install
npm run dev &

# 8. Volver a raíz
cd ../..
```

---

## 3. Verificación

### Health Check

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"IaaS-RonSys","version":"0.1.0"}
```

### Login

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@elsegoviano.pe","password":"admin123"}'
# → access_token + refresh_token + user info
```

### Estado de Resultados (PYG)

```bash
# Primero obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@elsegoviano.pe","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Cargar simulación contable
curl -s -X POST http://localhost:8000/api/accounting/setup \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{"capital":50000,"loan_amount":30000,"loan_rate_annual":0.12,"loan_term_months":12,"equipment_cost":20000,"furniture_cost":5000,"computer_cost":3000,"software_cost":1000,"guarantee_deposit":3000,"initial_inventory":5000,"monthly_sales":[25000,25000,25000,25000,25000,25000,25000,25000,25000,25000,25000,25000],"monthly_cost_pct":0.4,"monthly_rent":1500,"monthly_utilities":800,"monthly_salaries":5000,"monthly_marketing":500,"monthly_admin":300,"monthly_maintenance":200}'

# Consultar PYG
curl -s http://localhost:8000/api/accounting/pyg \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 1"
```

### Frontend

Abre http://localhost:5173 en el navegador. Deberías ver la página de login.

### Docker

```bash
docker compose ps
# Debe mostrar: postgres (healthy), redis (healthy), backend (running)
```

---

## 4. Credenciales Demo

| Email | Password | Rol |
|-------|----------|-----|
| **admin@elsegoviano.pe** | **admin123** | admin |

> ⚠️ **CAMBIAR en producción.** El script `deploy.sh` resetea la contraseña a `admin123` en cada ejecución para consistencia en desarrollo.

### Otros usuarios de prueba

| Email | Rol | Notas |
|-------|-----|-------|
| test@elsegoviano.pe | operator | Creado por migración |
| locktest@elsegoviano.pe | viewer | Para tests de bloqueo de cuenta |

---

## 5. Arquitectura de Servicios

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                         │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ postgres │   │  redis   │   │ rabbitmq │            │
│  │   :5432  │   │  :6379   │   │ :5672    │            │
│  └────┬─────┘   └────┬─────┘   └──────────┘            │
│       │              │                                   │
│  ┌────┴──────────────┴─────┐                            │
│  │        backend          │                            │
│  │    FastAPI :8000        │                            │
│  │  Python 3.12-slim       │                            │
│  └──────────┬──────────────┘                            │
│             │                                            │
└─────────────┼────────────────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    │     frontend       │  ← Vite dev server (:5173)
    │   React + Vite     │    Proxy /api/* → :8000
    └────────────────────┘
```

### Puertos

| Servicio | Puerto | Protocolo |
|----------|--------|-----------|
| Frontend (Vite) | 5173 | HTTP |
| Backend (FastAPI) | 8000 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |
| RabbitMQ | 5672 | AMQP |
| RabbitMQ Mgmt | 15672 | HTTP |

---

## 6. Comandos Útiles

```bash
# Ver estado de servicios
docker compose ps

# Logs
docker logs -f iaas-backend
docker logs -f iaas-postgres

# Reiniciar backend tras cambios de código
docker compose restart backend

# Reconstruir backend (si cambian dependencias)
docker compose build backend && docker compose up -d backend

# Conectarse a PostgreSQL
docker exec -it iaas-postgres psql -U ron -d iaas_ronsys

# Conectarse a Redis
docker exec -it iaas-redis redis-cli

# Parar todo
docker compose down

# Parar todo Y borrar volúmenes (base de datos)
docker compose down -v  # ⚠️ Borra TODOS los datos
```

---

## 7. Troubleshooting

### "Puerto 80 requiere permisos de root"

El puerto 80 es privilegiado (requiere sudo). Si Nginx no puede bindear:

```bash
# Opción 1: Usar puerto alternativo
# En .env.prod: FRONTEND_PORT=8080
# → Acceder en http://localhost:8080

# Opción 2: Dar capabilities a Nginx
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/docker
# (Requiere reiniciar Docker)
```

### "Puerto 5432/6379/8000 ya está en uso"

```bash
# Ver qué proceso ocupa el puerto
sudo lsof -i :5432
sudo lsof -i :6379
sudo lsof -i :8000

# Si es otro PostgreSQL/Redis local, detenerlo:
sudo systemctl stop postgresql
sudo systemctl stop redis-server

# O cambiar puertos en .env (ajustar docker-compose.yml también)
```

### "El backend está unhealthy"

El health check de Docker pega a `/health`. Verifica:

```bash
curl http://localhost:8000/health
# Debe responder {"status":"ok",...}

# Si no responde, ver logs:
docker logs iaas-backend --tail 30
```

### "Error: python3.12 no encontrado"

No necesitas Python 3.12 en el host. El backend corre en Docker con `python:3.12-slim`. Si estás intentando correr el backend fuera de Docker, necesitas Python 3.12 exactamente — no funciona con 3.13+.

### "ModuleNotFoundError: No module named 'app'"

Dentro del contenedor Docker, el PYTHONPATH no incluye `/app`. Usa siempre:

```bash
docker exec -w /app iaas-backend env PYTHONPATH=/app <comando>
```

### "Permiso denegado al ejecutar docker"

Asegúrate de que tu usuario pertenezca al grupo `docker`:

```bash
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

### "login rate limited (429)"

El rate limiting bloquea tras 5 intentos fallidos en 15 minutos. Espera o reinicia Redis:

```bash
docker compose restart redis
```

### "No hay asientos. Ejecuta /api/accounting/setup primero"

La API contable usa estado en memoria. Tras reiniciar el backend, debes llamar al endpoint `/api/accounting/setup` con los datos de inversión. Ver sección [Verificación](#3-verificación).

### "Connection refused al frontend"

Vite dev server no está corriendo:

```bash
cd apps/web && npm run dev &
```

### "No se encuentra .env.qa o .env.prod"

```bash
# Crear a partir del template
cp .env.example .env.qa
cp .env.example .env.prod

# Editar variables específicas:
# .env.qa → POSTGRES_DB=iaas_ronsys_qa, BACKEND_PORT=8001
# .env.prod → POSTGRES_DB=iaas_ronsys, BACKEND_PORT=8000
```

### "Nginx no sirve archivos estáticos"

```bash
# Verificar que dist/ existe
docker exec iaas-frontend-prod ls /usr/share/nginx/html/
# Debe mostrar: index.html, assets/

# Si no, reconstruir:
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d frontend
```

### "QA y Prod en conflicto"

Si ambos entornos intentan usar el mismo puerto:
- QA backend usa `:8001`, Prod usa `:8000` → sin conflicto
- QA frontend usa `:5173` (Vite en host), Prod usa `:80` (Nginx en Docker) → sin conflicto
- Ambos comparten PostgreSQL `:5432` y Redis `:6379` pero con bases de datos diferentes

---

## 8. Entornos (QA vs Producción)

IaaS-RonSys tiene **2 entornos independientes** que pueden correr simultáneamente:

```
┌──────────────────────────────────────────────────────────────┐
│                     ENTORNO QA (:5173 + :8001)               │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────────┐     │
│  │ postgres │   │  redis   │   │  backend-qa (:8001) │     │
│  │  :5432   │   │  :6379   │   │  Python 3.12-slim   │     │
│  └────┬─────┘   └────┬─────┘   └──────────┬──────────┘     │
│       │              │                     │                 │
│       └──────────────┼─────────────────────┘                 │
│                      │                                       │
│  BD: iaas_ronsys_qa  │                                       │
│                                                              │
│  ┌────────────────────┴────────────────────────────────┐    │
│  │  Frontend QA: Vite dev server (:5173)               │    │
│  │  Hot-reload activo  |  Proxy /api → :8001            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                 ENTORNO PRODUCCIÓN (:80 + :8000)             │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────────┐     │
│  │ postgres │   │  redis   │   │  backend-prod (:8000)│     │
│  │  :5432   │   │  :6379   │   │  Python 3.12-slim   │     │
│  └────┬─────┘   └────┬─────┘   └──────────┬──────────┘     │
│       │              │                     │                 │
│       └──────────────┼─────────────────────┘                 │
│                      │                                       │
│  BD: iaas_ronsys     │                                       │
│                                                              │
│  ┌────────────────────┴────────────────────────────────┐    │
│  │  Frontend Prod: Nginx (:80) ← proxy /api → :8000   │    │
│  │  Archivos estáticos compilados con Vite              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Tabla Comparativa

| Característica | 🧪 QA | 🚀 Producción |
|---------------|-------|---------------|
| **Comando** | `./deploy.sh --env qa` | `./deploy.sh --env prod` |
| **Frontend** | Vite dev server `:5173` | Nginx `:80` |
| **Backend** | `:8001` (uvicorn reload) | `:8000` |
| **Base de datos** | `iaas_ronsys_qa` | `iaas_ronsys` |
| **Env file** | `.env.qa` | `.env.prod` |
| **Hot-reload backend** | ✅ | ❌ |
| **Hot-reload frontend** | ✅ (HMR + Vite) | ❌ (compilado) |
| **SSL** | ❌ | Configurable |
| **Propósito** | Pruebas y desarrollo | Demo / cliente final |

### Desplegar Cada Entorno

```bash
# QA — entorno de pruebas
./deploy.sh --env qa
# → Backend:  http://localhost:8001
# → Frontend: http://localhost:5173
# → Swagger:  http://localhost:8001/docs

# Producción
./deploy.sh --env prod
# → Frontend: http://localhost       (nginx :80)
# → Backend:  http://localhost:8000
# → Swagger:  http://localhost:8000/docs
```

> 💡 Ambos entornos pueden ejecutarse **al mismo tiempo** sin conflictos de puertos ni datos.

### Verificar Cada Entorno

```bash
# QA
curl http://localhost:8001/health
# → {"status":"ok","service":"IaaS-RonSys","version":"0.1.0"}
curl http://localhost:5173/  # Frontend QA

# Producción
curl http://localhost:8000/health
curl http://localhost/       # Frontend Prod
```

### Parar Cada Entorno

```bash
# Parar QA
docker compose -f docker-compose.yml -f docker-compose.qa.yml down

# Parar Producción
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Parar TODO (ambos entornos + infraestructura compartida)
docker compose -f docker-compose.yml -f docker-compose.qa.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose down  # Infraestructura base (postgres, redis)
```

### Puertos de Cada Entorno

| Entorno | Servicio | Puerto | Contenedor |
|---------|----------|--------|------------|
| **Compartido** | PostgreSQL | 5432 | `iaas-postgres` |
| **Compartido** | Redis | 6379 | `iaas-redis` |
| **QA** | Backend | 8001 | `iaas-backend-qa` |
| **QA** | Frontend (Vite) | 5173 | Host (`npm run dev`) |
| **Prod** | Backend | 8000 | `iaas-backend-prod` |
| **Prod** | Frontend (Nginx) | 80 | `iaas-frontend-prod` |

---

## 9. Playwright E2E Tests

### Requisitos

| Dependencia | Versión |
|-------------|---------|
| Node.js | 20.x |
| Playwright | 1.52+ |
| Navegadores Chromium | incluido en playwright install |

> ⚠️ Playwright requiere Ubuntu ≤24.04 con libs del sistema. En Ubuntu 26.04+ puede fallar por dependencias no disponibles.

### Instalación

```bash
cd apps/web
npm install                     # playwright ya está en devDependencies
npx playwright install chromium # instala el navegador
```

### Ejecución

```bash
# Todos los tests
npx playwright test

# Un archivo específico
npx playwright test e2e/login.spec.ts

# Con UI
npx playwright test --ui

# Con navegador visible
npx playwright test --headed

# Debug
npx playwright test --debug

# Reporte HTML
npx playwright show-report
```

### Requisitos para ejecutar tests

1. Backend corriendo en `http://localhost:8000`
2. Frontend corriendo en `http://localhost:5173`
3. Usuario `admin@elsegoviano.pe` con contraseña `admin123`

### Workaround para Ubuntu 26.04+

Si las libs del sistema no están disponibles, usar Docker:

```bash
docker run --rm --network host -v $(pwd):/app -w /app \
  mcr.microsoft.com/playwright:v1.52.0-jammy \
  npx playwright test
```

---

## 10. Actualizar el Proyecto

```bash
cd IaaS-RonSys
git pull
./deploy.sh
```

El script es idempotente — aplica migraciones nuevas, reinstala dependencias si es necesario, y solo carga seed data si la BD está vacía.

---

## 📦 Estructura del Proyecto

```
IaaS-RonSys/
├── deploy.sh                 ← Script de despliegue automático
├── docker-compose.yml        ← Orquestación Docker
├── .env.example              ← Template de variables de entorno
├── .gitignore
├── Makefile
├── apps/
│   ├── backend/              ← FastAPI + SQLAlchemy + Alembic
│   │   ├── Dockerfile        ← python:3.12-slim
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── scripts/seed_db.py
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── routers/      ← health, auth, accounting, admin
│   │   │   ├── core/         ← Motor contable, kárdex, security
│   │   │   ├── adapters/     ← DB, Alembic, repositorios
│   │   │   └── models/       ← User, RefreshToken
│   │   └── tests/
│   └── web/                  ← React 19 + Vite 6 + Tailwind
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── vite.config.ts
│       ├── src/
│       │   ├── pages/        ← Dashboard, Login, Reports, etc.
│       │   ├── components/   ← KPICard, AppShell, PrivateRoute
│       │   ├── contexts/     ← AuthContext
│       │   └── services/     ← API client, authStore
│       └── e2e/              ← Playwright tests
├── docs/                     ← Documentación
│   ├── manuales/
│   │   ├── guia-despliegue.md  ← Este archivo
│   │   ├── manual-admin.md
│   │   └── manual-usuario.md
│   ├── architecture/
│   └── stories/
└── infra/                    ← Config Docker (monitoreo)
    └── docker/monitoring/
```

---

> 🐟 **IaaS-RonSys** — ERP SaaS para El Segoviano. Motor contable peruano PCGA con simulación financiera y kárdex valorizado.
