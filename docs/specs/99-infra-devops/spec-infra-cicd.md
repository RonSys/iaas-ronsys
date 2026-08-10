# SPEC — Infraestructura, Deploy y CI/CD (DevOps)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción en este host; hardening GH Actions 2026-08)
- **Proyecto**: IaaS-RonSys — ERP SaaS
- **Alcance**: entornos dev/qa/prod, contenedores, despliegue, CI/CD, monitoreo, e2e
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

La plataforma se despliega como contenedores Docker en este host (entornos QA y Prod
separados), con CI/CD en GitHub Actions (lint + tests), monitoreo (Prometheus/Grafana) y
pruebas E2E con Playwright contra prod. Objetivo: documentar la operación completa.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Entornos y despliegue

| Componente | Ubicación | Estado |
|---|---|---|
| Compose raíz | `docker-compose.yml` (postgres, redis, rabbitmq — infra de dev; backend/web se levantan con deploy.sh/compose prod) | ✅ Infra dev |
| `docker-compose.qa.yml` | raíz | ✅ QA (backend :8001, frontend :5173) |
| `docker-compose.prod.yml` | raíz | ✅ Producción (nginx :80, backend :8000) |
| `deploy.sh` (20 KB) | raíz | ✅ Script de despliegue (build, migraciones, restart) |
| Dockerfiles | `apps/backend/Dockerfile`, `apps/web/Dockerfile` (infra/docker/ solo tiene `monitoring/prometheus.yml`) | ✅ Build real |
| GH Actions | `.github/workflows/ci.yml` | ✅ CI (lint + tests) |

### 2.2 Hardening CI/CD (2026-08, verificado en commits `0937a23`, `c8f6ae9`)

- Pins SHA para acciones de terceros.
- Permisos mínimos (`permissions: contents: read`).
- `npm ci` (no `npm install`) + `npm audit` no bloqueante.
- Lint backend con flake8 (imports sin usar F401/F841 limpiados).
- Python 3.12.x obligatorio (README).

### 2.3 Monitoreo (verificado)

| Componente | Ubicación | Estado |
|---|---|---|
| Prometheus config | `infra/docker/monitoring/prometheus.yml` | ✅ Versionado en repo |
| **Stack Loki/Grafana/Prometheus** | `/mnt/disco_ssd/infra/logging/` (docker-compose + loki-config + promtail-config) | ⚠️ **FUERA del repo** (no versionado) |
| Health/Ready endpoints | `app/routers/health.py` (47 ln) | ✅ Desplegado |
| Metrics + rate limit + security headers | `app/monitoring/` | ✅ Implementado |

### 2.4 E2E Playwright (verificado)

| Spec | Archivo | Estado |
|---|---|---|
| Login | `e2e/login.spec.ts` | ✅ |
| Dashboard | `e2e/dashboard.spec.ts` | ✅ |
| Kardex | `e2e/kardex.spec.ts` | ✅ |
| Reportes | `e2e/reportes.spec.ts` | ✅ |
| Settings | `e2e/settings.spec.ts` | ✅ |
| Simulador | `e2e/simulador.spec.ts` | ✅ |
| Delivery landing | `e2e/delivery-landing.spec.ts` | ✅ |
| Delivery staff (11 tests CRUD zonas/campañas/kanban) | `e2e/delivery-staff.spec.ts` | ✅ |
| Config prod | `e2e/playwright.config.prod.ts` | ✅ (contra prod) |
| **Sin e2e**: POS/ventas, mesas/takeaway, superadmin, inventario | — | ⚠️ Pendiente |

### 2.5 Estado prod verificado (2026-08-10)

- Contenedores `iaas-backend-prod` (03-ago 08:14) + `iaas-frontend-prod` (03-ago 05:36) en este host.
- BD prod en migración `0016_delivery` (head).
- Delivery operativo: 8 órdenes reales, zona 1 (SJL), menú público `el-segoviano` 200 OK.
- Recetas: 3 recetas / 15 ingredientes en prod.

---

## 3. Fase P — Operación

### 3.1 Comandos (verificados en README/Makefile)

```bash
# Desplegar producción
./deploy.sh prod
# Desplegar QA
./deploy.sh qa
# Actualizar (pull + redeploy)
./deploy.sh update
# Migraciones (primera vez)
make migrate  # o alembic upgrade head
```

### 3.2 Criterios de aceptación (verificados)

- CA1: `docker compose up` levanta stack completo (dev) con health OK. ✅
- CA2: deploy.sh despliega backend + frontend + migraciones. ✅
- CA3: CI ejecuta lint (flake8) + tests antes de merge. ✅
- CA4: e2e prod (delivery-staff) 11/11 PASS. ✅
- CA5: `/health` y `/ready` responden 200 en prod. ✅

---

## 4. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Compose | `docker-compose*.yml` (raíz) | §2.1 |
| Deploy | `deploy.sh`, `Makefile` | §2.1, §3.1 |
| Dockerfiles | `infra/docker/*` | §2.1 |
| CI/CD | `.github/workflows/*` | §2.2 |
| Monitoreo | `infra/docker/monitoring`, `app/monitoring/`, `app/routers/health.py` | §2.3 |
| E2E | `apps/web/e2e/*` | §2.4 |

> ⚠️ Si cambias entornos, deploy, CI/CD, monitoreo o agregas e2e, **actualiza esta spec** (Spec Anchor).
