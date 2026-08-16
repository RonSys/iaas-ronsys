# 🚀 Deploy Report — F6 Agenda de Citas (Spec 07): PROD + E2E en caliente

> **Autor:** DevOps Agent 🔧
> **Fecha:** 2026-08-16 00:50 UTC
> **Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
> **Spec:** `docs/specs/03-delivery/07-spec-agenda-citas-v0.1.md` (🟢 APROBADA)
> **Patrón replicado:** F3 (b75b5f0) / F5 (7be24dc) — backup previo → migración → rebuild → healthcheck → E2E en caliente → limpieza
> **Veredicto:** ✅ **DESPLIEGUE EXITOSO + E2E 18/18 OK + BD limpia**

---

## 1. 📦 Cambios desplegados (working tree, SIN commit — lo commitea Jarvis)

### Backend (`apps/backend`)
| Archivo | Tipo |
|---|---|
| `app/adapters/alembic/versions/0021_appointments.py` | **NUEVO** — tabla `appointments` + grants dashboard + CHECK voz `taking_reservation` (D5) |
| `app/adapters/db/models/appointments.py` | **NUEVO** — modelo ORM |
| `app/schemas/appointments.py` | **NUEVO** — schemas + settings D-03 |
| `app/services/appointments_service.py` | **NUEVO** — dominio: availability (R2/R3/D4), create (409/422), update (R5 + espejo D1), remind (R9) |
| `app/routers/appointments.py` | **NUEVO** — `/api/v1/appointments*` + rate-limit Redis (R7) |
| `scripts/appointment_reminders.py` | **NUEVO** — job recordatorio 24h (R9) |
| `services/notify_events.py`, `notify_worker.py` | Modificados — eventos `appointment.confirmed` / `appointment.reminder` (D6, dry-run) |
| `services/voice_ai_service.py`, `voice_providers.py` | Modificados — estado `taking_reservation` (D5) |
| `main.py`, `routers/setup.py`, `schemas/calls.py`, `Makefile` | Modificados — wiring + target `remind-appointments` |

### Frontend (`apps/web`)
| Archivo | Tipo |
|---|---|
| `src/pages/restaurante/AgendaPage.tsx` | **NUEVO** — ruta `/restaurante/agenda` |
| `src/services/appointmentsApi.ts` | **NUEVO** — cliente API F6 |
| `src/components/layout/Sidebar.tsx` | Modificado — item "📅 Agenda de Citas" |
| `src/pages/Settings.tsx` | Modificado — horarios D3 (ventana independiente 12:00–23:00) |

---

## 2. 🗄️ Paso 1 — Backup previo (patrón F3/F5)

```bash
docker exec iaas-postgres pg_dump -U ron -d iaas_ronsys -Fc -f /tmp/...dump
docker cp iaas-postgres:/tmp/...dump backups/iaas_ronsys_pre_f6_deploy_20260816.dump
```
- **Archivo:** `backups/iaas_ronsys_pre_f6_deploy_20260816.dump` (312 KB)
- **Integridad verificada:** `pg_restore --list` → 39 secciones TABLE DATA ✅

## 3. 🗃️ Paso 2 — Migración 0021 en BD prod

- `alembic_version` en prod ya apuntaba a `0021_appointments` (tabla existente, 0 filas).
- Re-verificado tras deploy: **`SELECT version_num FROM alembic_version` → `0021_appointments`** ✅
- Backend aplica `alembic upgrade head` en lifespan (`[startup] Alembic upgrade head — OK` en logs) ✅
- Esquema verificado: PK, UNIQUE `(tenant_id, table_id, starts_at)`, CHECKs status/source/guests/duration, índices `idx_appointments_tenant_date` / `_tenant_state` ✅

## 4. 🏗️ Paso 3 — Rebuild + redeploy prod

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend frontend worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend frontend worker
```
- `backend Built · frontend Built · worker Built` ✅
- Contenedores recreados: `iaas-backend-prod`, `iaas-frontend-prod`, `iaas-worker-prod` ✅

## 5. 🩺 Paso 4 — Healthchecks

| Check | Resultado |
|---|---|
| Backend `GET /health` | ✅ `{"status":"ok","service":"IaaS-RonSys","version":"0.1.0"}` |
| Frontend `:8081` | ✅ HTTP 200 (healthy) |
| Contenedor backend | ✅ Up (healthy) |
| Contenedor frontend | ✅ Up (healthy) |
| Worker | ✅ Up — `whatsapp dry-run: evento appointment.confirmed` procesado (D6/R8, sin Meta) |
| Alembic | ✅ `0021_appointments` |

### Endpoints F6 con auth (tenant 3)
| Endpoint | Resultado |
|---|---|
| `GET /api/v1/appointments/availability?date&guests&from&to` | ✅ 200 (slots reales) |
| `GET /api/v1/appointments?date=` | ✅ 200 `{"items":[],"total":0}` |

---

## 6. 🧪 Paso 5 — E2E EN CALIENTE (e2e-hot-f6-agenda.cjs)

**Script:** `apps/web/scripts/e2e-hot-f6-agenda.cjs` (patrón e2e-hot-f5-asistente.cjs)
**⚠️ REQUISITO RON cumplido:** todos los fixtures/payloads con **tenant-id = 3** (login `admincevicheria@elsegoviano.pe`, X-Tenant-ID: 3, JWT company_id=3).

**Flujo ejecutado (18/18 OK):**
1. **P0** Login API staff → JWT `company_id=3` ✅
2. **P1** Fixtures: 2 mesas de prueba tenant 3 (`F6E2E-1`, `F6E2E-2`) via `POST /restaurant/tables` ✅
3. **P1.1** Availability devuelve mesas reales (42 slots) ✅
4. **P2** Login UI → `/restaurante/agenda` cargada ✅
5. **P3** Modal "＋ Nueva cita" → slots reales de disponibilidad ✅
6. **P4** Cita creada (201, mesa real desde availability, source=in_person) ✅
7. **P5** Cita visible en lista (solicitada) + **tenant_id=3 verificado en la cita** ✅
8. **P6** Confirmar → `confirmada` + **espejo `tables.status='reserved'` (D1)** + UI muestra Confirmada ✅
9. **P7** Cancelar → `cancelada` + **espejo vuelve a `available`** + UI muestra Cancelada ✅
10. **P8/P9** Limpieza completa → citas tenant 3 = 0, mesas fixture = 0 ✅

### 📸 Evidencias (`docs/reports/evidencias-f6-e2e-prod/` — 6 PNG + resumen.json)
| Archivo | Contenido |
|---|---|
| `01-agenda.png` | Agenda cargada (empty state) |
| `02-modal-disponibilidad.png` | Modal Nueva cita con slots de mesas reales |
| `03-cita-creada.png` | Cita creada en lista (Solicitada) |
| `04-cita-confirmada.png` | Cita Confirmada en lista (filtrada por fecha) |
| `05-cita-cancelada.png` | Cita Cancelada en lista |
| `06-estado-final.png` | Estado final tras limpieza |
| `resumen.json` | 18 resultados detallados |

## 7. 🧹 Paso 6 — Limpieza post-E2E (BD limpia, patrón F3/F5)

| Tabla | Antes | Después E2E | Estado |
|---|---:|---:|---|
| `appointments` (tenant 3) | 0 | 0 | ✅ (creadas y eliminadas) |
| `appointments` (total) | 0 | 0 | ✅ |
| `tables` (tenant 3) | 0 | 0 | ✅ (fixtures eliminadas via API 204) |
| `tables` (tenant 1) | 21 | 21 | ✅ intactas |
| `query_logs` | 13 | 13 | ✅ sin tocar (histórico F5) |
| `call_records` | 0 | 0 | ✅ |

## 8. 🔥 Smoke API

```
GET /api/v1/appointments?date=2026-08-16 (token staff tenant 3) → HTTP 200 {"items":[],"total":0}
```

## 9. 🟢 Estado final de contenedores (antes = después)

| Contenedor | Estado |
|---|---|
| iaas-backend-prod | ✅ healthy |
| iaas-frontend-prod | ✅ healthy |
| iaas-worker-prod | ✅ Up |
| iaas-postgres / redis / rabbitmq / asterisk / grafana / prometheus | ✅ healthy |
| Otros dominios (dash, segoviano, eyfimport, stratify, smart, consultoria) | ✅ sin cambios (up weeks) |

---

**Veredicto:** ✅ **F6 AGENDA DE CITAS DESPLEGADO EN PROD** — migración 0021 aplicada, endpoints vivos, E2E en caliente 18/18 con tenant-id=3, espejo de mesas D1 verificado, BD 100% limpia post-E2E, sin impacto en otros servicios. **Sin commits realizados** (working tree intacto — lo commitea Jarvis).
