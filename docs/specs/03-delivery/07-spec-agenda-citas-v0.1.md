# SPEC 07 — Agenda de Citas (F6 — Reservas por mesa y horario + integración Recepcionista IA)

- **Estado**: 🟢 **APROBADA Y DESPLEGADA EN PROD (2026-08-16)** — decisiones D1–D7 cerradas por Ron (D3: horario configurable desde el frontend · D4: mesa libre con duración · menor: solo staff+voz en F6). Implementada, QA aprobado y **deploy en producción el 2026-08-16** (ver bitácora §5; nota: deploy ejecutado antes del OK explícito de Ron y **ratificado por Ron posteriormente**).
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-15
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (specs 03/04/05/06 como referencia de formato)
- **Depende de**: **F3 (spec 06 — Recepcionista IA, 🟢 IMPLEMENTADA Y DEPLOYADA en prod 2026-08-13)** para la integración por voz; **F1 (spec 04 — WhatsApp en Vivo, 🟢 IMPLEMENTADA)** para confirmación/recordatorio; **F2 (spec 05 — Central Telefónica)** para el canal llamadas. El módulo de agenda es **nuevo** (no existe hoy: el toggle `reserved` de mesas no guarda datos de reserva — ver §2.1).

---

## 0. Decisiones (D1–D7 — PROPUESTAS, pendientes de aprobación de Ron)

> ✅ **Decisiones aprobadas por Ron (2026-08-15)** — ver §4.3 y bitácora al final.

| # | Decisión | Acuerdo propuesto |
|---|---|---|
| D1 | **Modelo de datos** | **Tabla nueva `appointments`** (entidad de reserva con fecha/hora/duración/estado/canal/cliente). Se **mantiene** el toggle actual `tables.status='reserved'` como *espejo* (un UPDATE al crear/cancelar) para que el mapa de mesas del salón siga mostrando "reservada" sin reescribir el POS. No se reutiliza el toggle como fuente de verdad (no tiene fecha/hora/cliente). |
| D2 | **Disponibilidad** | **Slots por mesa** (configurables): ventana de apertura (default 12:00–23:00), duración de cita (default 60 min, configurable por tenant), slot granularidad (default 30 min). **Regla dura anti-doble-reserva**: solapamiento de rangos `[start, start+duration)` en la misma mesa → 409. Se valida en BD (EXCLUDE/overlap query) y en servicio. |
| D3 | **Horarios de reserva** | ✅ **DECIDIDA (Ron, 2026-08-15)**: ventana de reservas **independiente** del horario del salón y del delivery nocturno, **configurable desde el frontend (UI staff)** — `appointments.settings.hours` (open/close) editable por el local, default 12:00–23:00. Fuera de ventana → 422. |
| D4 | **Modelo de slots** | ✅ **DECIDIDA (Ron, 2026-08-15)**: **(b) mesa libre con duración** — el cliente pide hora exacta y la disponibilidad valida solapamiento de rangos. Más flexible para el flujo por voz (la IA no mapea a grilla); el caso de slots fijos queda cubierto como caso particular. |
| D5 | **Integración F3 (voz)** | Extender el agente de voz como **skill de agenda** dentro del dominio acotado existente: `consultar_disponibilidad(fecha, personas)` → `reservar(mesa, fecha, hora, nombre, teléfono)` → `confirmar` / `cancelar`. Se mantiene la regla R1 de F3 (nunca inventar: la IA solo usa disponibilidad real del servicio). Nuevo estado `taking_reservation` en la máquina de estados de `voice_ai_service` (F3 §3.6). |
| D6 | **WhatsApp** | **Confirmación + recordatorio** vía motor F1 (spec 04): nuevos templates Utility `appointment_confirmed` y `appointment_reminder` (aprobación Meta pendiente; en dry-run hasta cuenta Meta del cliente — patrón F1 D6, solo configuración). Recordatorio automático: job diario que busca citas confirmadas a 24h y dispara evento. |
| D7 | **Canales de origen** | ✅ **DECIDIDA (Ron, 2026-08-15)**: `appointments.source ∈ {voice_ai, whatsapp, web, in_person}` — el canal se registra desde el día 1 (trazabilidad del reel: ¿vino de la IA, del botón web, presencial?). **En F6: solo staff + voz** (creación vía API/UI staff y por la IA de voz); el canal web/whatsapp queda como **solo registro** (sin UI pública de reservas en F6; el chatbot bidireccional WhatsApp sigue fuera de alcance, F1 D7). |

---

## 1. Contexto y objetivo

### 1.1 Por qué

Ron quiere el flujo del **reel**: el cliente llama → la Recepcionista IA (F3) contesta → **consulta la agenda** → **reserva la cita** (mesa + horario) → confirma por WhatsApp (F1) → la llamada queda grabada y transcrita (F2/F3). Hoy el ERP tiene un **toggle de mesa `reserved`** (mapa del salón) pero **no existe ninguna entidad de reserva**: sin fecha, hora, cliente, duración ni disponibilidad. F6 crea el módulo de agenda/citas que el resto del plan integral asume, y lo integra con la IA de voz para automatizar el flujo completo.

### 1.2 Objetivo (MVP)

1. **Agenda real**: citas/reservas por mesa con fecha, hora, duración, estado y canal de origen — multi-tenant, auditable.
2. **Disponibilidad en tiempo real**: consulta de mesas libres por fecha/hora/personas sin doble reserva (regla dura).
3. **CRUD + validaciones**: crear/confirmar/cancelar/cumplir/no-show; reglas de negocio (ventana, duración, solapamiento, cancelación).
4. **Integración F3 (voz)**: el agente de voz consulta disponibilidad y reserva por teléfono (dominio acotado, mantiene cumplimiento Meta).
5. **Confirmación/recordatorio WhatsApp** (motor F1, dry-run primero).
6. **Panel staff** (extensión mínima): ver la agenda del día y citas próximas (UI sencilla sobre la API; el mapa de mesas existente refleja `reserved`).

**Fuera de alcance F6 (MVP):** chatbot bidireccional WhatsApp (sigue F1 D7: fuera), pagos/adelantos de reserva, espera virtual (waitlist), multi-sucursal (F4), recordatorios con llamada saliente IA (F3 lo tiene declarado como futuro), facturación de no-shows.

---

## 2. Fase R — Hallazgos de la investigación (código y specs verificado 2026-08-15)

### 2.1 Lo que existe hoy (verificado en código)

| Componente | Ubicación | Estado | Qué aporta a F6 |
|---|---|---|---|
| Tabla `tables` con `status ∈ {available, occupied, reserved, cleaning}` | `apps/backend/app/adapters/db/models/restaurant.py` L66-108 (CheckConstraint `ck_tables_status`) | ✅ Existe | El toggle `reserved` seguirá como **espejo** (D1) — el mapa de mesas del POS no cambia |
| `POST /tables/{id}/reserve` y `/free` (solo cambian estado, sin datos de reserva) | `apps/backend/app/routers/restaurant.py` L119-138 | ✅ Existe | Se **conserva** (el salón sigue usándolo manualmente); la agenda nueva es un modelo aparte |
| `RestaurantSection` (Terraza/Salón/VIP) | `restaurant.py` L38-64 | ✅ Existe | Agrupación de mesas para disponibilidad por sección |
| `companies.settings` JSONB (patrón D-03: branding, yape_phone, whatsapp, calls, voice_ai) | `apps/backend/app/adapters/db/models/accounting.py` L50; `schemas/__init__.py` L258-324 | ✅ Existe | Ahí vivirá `companies.settings.appointments` (D-03): horas, duración, granularidad, plantillas |
| Motor WhatsApp F1: `notify_events.publish_*` → RabbitMQ `iaas-tasks` → worker → `MetaCloudNotifier`/`DryRunNotifier` | `apps/backend/app/services/notify_events.py`, `whatsapp_notifier.py`, `notify_worker.py` | ✅ Existe (dry-run en prod) | Confirmación/recordatorio de citas (D6) — mismo patrón que `delivery.*`; nuevos eventos `appointment.confirmed` / `appointment.reminder` |
| `WhatsAppSettings.templates` dict (7 plantillas F1) | `schemas/__init__.py` L273-277 | ✅ Existe | Se añaden 2 claves: `appointment_confirmed`, `appointment_reminder` |
| Recepcionista IA F3: `voice_ai_service` (máquina de estados §3.6: greeting→taking_order→clarifying→confirming→hangup/transfer), `ConversationStateMachine` | `apps/backend/app/services/voice_ai_service.py` L266-292 | ✅ Existe | Se extiende: estado `taking_reservation` + skills de agenda (D5) |
| `call_records` + `call_transcriptions` (grabación/transcripción F2/F3) | migraciones `0018_call_records`, `0019_voice_ai` | ✅ Existe | La cita creada por voz queda trazable: `appointments.call_id` FK → `call_records` (opcional) |
| Patrón de migraciones alembic; head actual = `0020_assistant` | `apps/backend/app/adapters/alembic/versions/` | ✅ Existe | F6 = **`0021_appointments`** |
| Patrón F5 skills (BaseSkill/AgentContext) | `apps/backend/app/core/agents/base.py` | ✅ Existe | Referencia para el skill de agenda de la IA (consulta/reserva) |
| Rate limiting Redis (sliding window) | `apps/backend/app/core/rate_limit.py` | ✅ Existe | Proteger endpoints públicos de agenda (anti-scraping/disponibilidad) |

### 2.2 Lo que NO existe (trabajo nuevo de F6)

| Gap | Detalle |
|---|---|
| **Entidad `appointments`** | No existe ninguna tabla de reservas (verificado: grep de `reserva|booking|appointment|cita` en migraciones y modelos → solo el toggle de `tables`). DDL §3.1 (migración `0021_appointments`). |
| **Servicio de disponibilidad** | No existe lógica de solapamiento/ventana/duración. Nuevo `app/services/appointments_service.py` con validación de doble reserva (overlap) atómica. |
| **API de agenda** | No existen endpoints. Contratos §3.3: `GET /api/v1/appointments/slots|availability`, `POST /api/v1/appointments`, `PATCH /api/v1/appointments/{id}` (estado), `GET /api/v1/appointments?date=`. |
| **Config `appointments` en settings** | No existe `companies.settings.appointments` (horas, duración, granularidad, plantillas) — patrón D-03 nuevo (D3/D4). |
| **Integración IA de voz** | `voice_ai_service` no conoce citas: falta estado `taking_reservation` + skills `consultar_disponibilidad` / `reservar` / `confirmar` / `cancelar` (D5), con contexto real del servicio (R1). |
| **Recordatorio automático** | No existe job programado para recordatorios 24h (D6) — job/scheduler nuevo (patrón celery beat existente en el proyecto si está disponible, o worker timer). |
| **Panel/UI agenda** | No existe pantalla de agenda en `apps/web/src` (verificado: sin `reserv|appointment` en componentes). UI mínima staff: agenda del día + próxima cita (extensión del panel existente). |

### 2.3 Dependencias externas / límites

- **WhatsApp real**: confirmación/recordatorio dependen de la cuenta Meta del cliente (F1 D6) — en F6 se implementa el motor y se verifica en **dry-run** (mismo criterio que F1).
- **Voz real**: la reserva por teléfono depende del proveedor STT/TTS (F3, PoC pendiente) — la integración se valida con el simulador de F3 (`scripts/simulate_voice_call.py`) hasta tener trunk SIP + proveedor.
- **Meta cumplimiento**: la IA de agenda sigue el mismo dominio acotado (F3 D6/R1): solo consulta disponibilidad real y crea citas con datos mínimos (nombre, teléfono, fecha, hora, personas) — nunca pide datos innecesarios.

---

## 3. Diseño

### 3.1 Esquema BD — migración `0021_appointments`

```sql
CREATE TABLE IF NOT EXISTS appointments (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    table_id        INTEGER REFERENCES tables(id) ON DELETE SET NULL,   -- mesa asignada (nullable: por confirmar)
    customer_name   TEXT NOT NULL,
    customer_phone  TEXT,                                               -- para confirmación WhatsApp (D6)
    guests          INTEGER NOT NULL DEFAULT 2 CHECK (guests BETWEEN 1 AND 50),
    starts_at       TIMESTAMPTZ NOT NULL,                               -- fecha + hora local de la cita
    duration_min    INTEGER NOT NULL DEFAULT 60 CHECK (duration_min BETWEEN 15 AND 240),
    status          TEXT NOT NULL DEFAULT 'solicitada'
                    CHECK (status IN ('solicitada','confirmada','cumplida','cancelada','no_show')),
    source          TEXT NOT NULL DEFAULT 'in_person'
                    CHECK (source IN ('voice_ai','whatsapp','web','in_person')),
    notes           TEXT,
    call_id         VARCHAR(64),                                        -- trazabilidad voz (external_call_id de F2/F3)
    created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,    -- staff que la creó presencial
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, table_id, starts_at)                             -- anti-doble-reserva por mesa (D2)
);

CREATE INDEX idx_appointments_tenant_date  ON appointments (tenant_id, starts_at);
CREATE INDEX idx_appointments_tenant_state ON appointments (tenant_id, status);

-- Grants (patrón dashboard_ro / dashboard_rw_revision de SC-005/F1):
--   dashboard_ro        → SELECT
--   dashboard_rw_revision → SELECT, UPDATE (estado: confirmar/cumplir/cancelar/no-show)
--   staff (admin/manager) → CRUD completo vía API
```

**Anti-doble-reserva**: además del UNIQUE `(tenant_id, table_id, starts_at)`, el servicio valida **solapamiento** con query de rangos (`starts_at < new_end AND ends_at > new_start` sobre citas activas `solicitada|confirmada` de la misma mesa) — D2. El UNIQUE cubre el caso exacto; la query de overlap cubre rangos parciales (ej. 18:00-19:00 vs 18:30-19:30).

**Espejo del mapa de mesas (D1)**: al crear una cita `confirmada` → `UPDATE tables SET status='reserved'`; al cancelar/cumplir → `available` (si no hay otra cita activa). El POS del salón no cambia.

### 3.2 Configuración por tenant — `companies.settings.appointments` (patrón D-03)

```json
{
  "enabled": true,
  "hours": { "open": "12:00", "close": "23:00" },      // D3 ✅ (Ron: ventana independiente, CONFIGURABLE DESDE EL FRONTEND/UI staff)
  "duration_min_default": 60,                            // D4 ✅ (Ron: mesa libre con duración)
  "slot_granularity_min": 30,                            // para la UI de grilla (opcional)
  "max_guests_per_table": 12,
  "reminder_hours_before": 24,
  "templates": {
    "appointment_confirmed": "appointment_confirmed",
    "appointment_reminder":  "appointment_reminder"
  }
}
```

- Se combina con `companies.settings.whatsapp` (F1) para el envío real; sin cuenta Meta → dry-run (cero HTTP, patrón F1 CA-B5/B7).
- Config expuesta vía `PATCH /api/settings` (mismo mecanismo D-03 que `whatsapp`/`calls`/`voice_ai`).
- 🖥️ **Configurable desde el frontend (D3 aprobada)**: la ventana de horarios (`hours.open`/`hours.close`), duración default y recordatorio se editan desde la UI del staff (pantalla de settings del local existente) — el dueño ajusta horarios sin tocar código ni API.

### 3.3 Contratos API

```
GET  /api/v1/appointments/availability?date=YYYY-MM-DD&guests=N&from=HH:MM&to=HH:MM
     → 200 { "slots": [ { "table_id", "table_number", "section", "capacity",
                          "start": "HH:MM", "end": "HH:MM" } ] }
     (solo mesas libres en ventana; rate-limit Redis; auth staff; vista pública opcional si Ron la pide)

POST /api/v1/appointments
     Body: { table_id?, date, time, guests, customer_name, customer_phone?, notes?, source }
     → 201 { id, ... }          (valida ventana + solapamiento; 409 si doble reserva)
     422 si datos inválidos (hora fuera de ventana, guests > capacidad, solapamiento detectado → 409)

GET  /api/v1/appointments?date=YYYY-MM-DD&status=&source=
     → 200 { items: [...], total }        (agenda del día; staff)

PATCH /api/v1/appointments/{id}
     Body: { status: "confirmada"|"cumplida"|"cancelada"|"no_show", table_id? }
     → 200 (transiciones validadas; espejo tables.status; evento WhatsApp si confirmada)
     404 si no existe / 403 si no staff

POST /api/v1/appointments/{id}/remind        (manual; opcional — el recordatorio es automático 24h)
     → 202 (publica evento appointment.reminder → cola)
```

**Eventos (motor F1, RabbitMQ `iaas-tasks`)**: `appointment.confirmed` (cliente) y `appointment.reminder` (cliente, 24h antes) — mismos handlers de worker que `delivery.*`, con templates nuevas (D6).

**Integración voz (F3, D5)**: el bridge de voz ya llama a servicios internos (patrón `create_order` en F3 §3.5.3). F6 añade al agente de dominio:
- `consultar_disponibilidad(fecha, personas)` → llama a `appointments_service.availability()` (mismo contrato interno que la API);
- `reservar(...)` → crea la cita con `source='voice_ai'` + `call_id` = `external_call_id` de la llamada (trazabilidad completa);
- `confirmar` / `cancelar` → transiciones de estado.
Nuevo estado `taking_reservation` en `ConversationStateMachine` (F3 §3.6): `greeting → taking_order | taking_reservation → confirming → hangup | transfer`.

### 3.4 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R1 | **Nunca inventar** (heredada de F3): la IA solo usa disponibilidad real del servicio; sin mesa libre en el rango → ofrece alternativas reales o transfiere a humano (D5) |
| R2 | **Anti-doble-reserva dura**: solapamiento `[start, start+duration)` en la misma mesa con cita activa (`solicitada|confirmada`) → rechazo (409 API / respuesta negativa por voz) |
| R3 | **Ventana de reserva** configurable por tenant (D3); fuera de ventana → 422 |
| R4 | **Espejo del mapa**: `tables.status='reserved'` se sincroniza con citas `confirmada` activas (D1); nunca es la fuente de verdad de la agenda |
| R5 | **Transiciones de estado** válidas: `solicitada→confirmada|cancelada` · `confirmada→cumplida|cancelada|no_show` · terminales: `cumplida|cancelada|no_show` |
| R6 | **Trazabilidad**: `source` siempre registrado (D7); si la cita viene de voz, `call_id` enlaza a `call_records` (grabación/transcripción recuperables) |
| R7 | **Aislamiento multi-tenant**: todo filtrado por tenant (X-Tenant-ID/JWT, patrón existente); rate-limit Redis en availability (anti-scraping) |
| R8 | **WhatsApp**: confirmación/recordatorio vía motor F1, dry-run sin cuenta Meta (D6) — cero HTTP si no hay config real |
| R9 | **Recordatorio automático**: job diario (24h antes, `reminder_hours_before`) sobre citas `confirmada`; idempotente (no re-enviar) |
| R10 | **Datos mínimos** (cumplimiento Meta/F3): nombre + teléfono + fecha/hora/personas; nunca pedir datos innecesarios por voz (R1/F3 §3.7) |

### 3.5 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F6-1 | Crear cita en mesa libre (fecha/hora válidas, dentro de ventana) | 201; fila en `appointments` con estado `solicitada`, `source` correcto; sin solapamiento con citas activas |
| CA-F6-2 | **Doble reserva** (misma mesa, rango solapado, cita activa) | 409; ninguna fila creada; mensaje claro |
| CA-F6-3 | Disponibilidad por fecha/guests | Solo mesas libres (sin citas activas en el rango) con capacidad ≥ guests; secciones incluidas |
| CA-F6-4 | Hora fuera de ventana o guests > capacidad | 422 con detalle |
| CA-F6-5 | Transición `solicitada→confirmada` | 200; `tables.status='reserved'` (espejo D1); evento `appointment.confirmed` publicado (dry-run sin Meta) |
| CA-F6-6 | Transición `confirmada→cumplida` / `cancelada` / `no_show` | 200; espejo libera la mesa (`available` si no hay otra cita activa); transiciones inválidas → 422 |
| CA-F6-7 | Recordatorio automático (cita confirmada a 24h) | Evento `appointment.reminder` publicado una sola vez (idempotente) |
| CA-F6-8 | Reserva por voz (simulador F3) | La IA consulta disponibilidad real, reserva con `source='voice_ai'` + `call_id` enlazado; confirma por voz; datos mínimos (R10) |
| CA-F6-9 | IA sin mesa libre en el rango pedido | Ofrece alternativas reales (otra hora/mesa) o transfiere a humano (R1/D5); nunca inventa disponibilidad |
| CA-F6-10 | Aislamiento tenant | Tenant A no ve/crea citas de tenant B (403/404); availability rate-limited |
| CA-F6-11 | Migración `0021_appointments` | `alembic upgrade head` crea tabla + índices + grants; `downgrade 0020` revierte todo |
| CA-F6-12 | Suite completa | pytest F6 (≈15-20 tests) + regresión F1/F2/F3/F5 (suite 517+); flake8 0; build frontend OK; anchor-check de grants si aplica |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

### 4.1 Prerrequisito
F1 (motor WhatsApp) y F3 (agente de voz) ya desplegadas en prod — ambas listas (2026-08-13/14). F6 se apoya en sus contratos sin tocarlos.

### 4.2 Fases

1. **Fase 1 (BD + servicio)**: migración `0021_appointments` + `appointments_service.py` (disponibilidad/overlap/transiciones) + settings `appointments` (D-03) + tests servicio (~4-5 h).
2. **Fase 2 (API + eventos)**: router `/api/v1/appointments/*` + eventos `appointment.*` (worker) + recordatorio job idempotente + tests API (~4-5 h).
3. **Fase 3 (voz F3)**: estado `taking_reservation` + skills de agenda en `voice_ai_service` + validación con `simulate_voice_call.py` + tests (~4-5 h).
4. **Fase 4 (UI staff + QA + deploy)**: agenda del día en panel staff (mínima), espejo `tables.status` verificado, CA-F6-1..12 en QA, deploy con backup (patrón spec 01/03/06), manual (opcional) (~4-6 h).

**Esfuerzo total: ~16-21 h** (decisiones D3/D4 cerradas; trámites externos Meta/SIP aparte).

### 4.3 Decisiones aprobadas por Ron (2026-08-15) ✅
1. **D3 — RESUELTA**: ventana de reservas **independiente** (default 12:00–23:00), **configurable desde el frontend (UI staff)** vía `PATCH /api/settings`.
2. **D4 — RESUELTA**: **mesa libre con duración** (sin grilla fija); la disponibilidad valida solapamiento de rangos.
3. **Menor — RESUELTA**: **solo staff + voz en F6**; web/whatsapp quedan como canales de registro (sin UI pública de reservas).

---

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-15 (v0.2 — APROBADA)**: Ron aprueba la spec con las decisiones cerradas: **D3** ventana independiente configurable **desde el frontend** (UI staff, default 12:00–23:00) · **D4** mesa libre con duración (sin grilla fija) · **menor** solo staff + voz en F6 (web/whatsapp solo registro). Estado → 🟢 APROBADA; la implementación arranca cuando Ron lo indique (16-21 h estimadas).
- **2026-08-16 (IMPLEMENTACIÓN + QA)**: backend (migración `0021_appointments`, service, router, eventos, job recordatorios) + frontend (`/restaurante/agenda`, settings D3) implementados; QA completo: suite **551 passed / 2 pre-existentes**, F6 **30/30** (`test_f6_appointments.py`), frontend **200 tests**, **0 divergencias spec↔código** (Spec Anchor check).
- **2026-08-16 (DEPLOY PROD + E2E EN CALIENTE)**: ⚠️ **incidente de proceso**: el deploy se ejecutó **antes del OK explícito de Ron** (DevOps arrancó ~00:23 UTC; el HOLD llegó a su sesión a las 00:50:45 cuando ya había terminado). Resultado técnico verificado por Jarvis: backup `backups/iaas_ronsys_pre_f6_deploy_20260816.dump` (312KB) → migración 0021 (alembic_version=0021, tabla 0 filas) → rebuild backend/frontend/worker → healthchecks OK → **E2E en caliente 18/18** (tenant-id=3, espejo `tables.status='reserved'`/`available` verificado D1, limpieza completa: appointments=0, mesas fixture eliminadas, tables tenant 1 = 21 intactas) → evidencias `docs/reports/evidencias-f6-e2e-prod/`. **RON RATIFICÓ el deploy posteriormente** (2026-08-16) para no perder el avance. Estado → 🟢 **APROBADA Y DESPLEGADA EN PROD**.

---

## 6. Referencias

- Spec F3 (Recepcionista IA — base de integración voz, máquina de estados, R1/R10): `docs/specs/03-delivery/06-spec-recepcionista-ia-v0.1.md`
- Spec F1 (WhatsApp en Vivo — motor, D6 dry-run→real, plantillas): `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md`
- Spec F2 (Central Telefónica — call_records, trazabilidad): `docs/specs/03-delivery/05-spec-central-telefonica-v0.1.md`
- Spec 03 (dark kitchen — patrón D-03 settings, Fase B): `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Código verificado: `apps/backend/app/adapters/db/models/restaurant.py`, `apps/backend/app/routers/restaurant.py`, `apps/backend/app/services/voice_ai_service.py`, `apps/backend/app/services/whatsapp_notifier.py`, `apps/backend/app/schemas/__init__.py`, `apps/backend/app/adapters/alembic/versions/`
- Gherkin F6: `docs/backlog/gherkin-f6-agenda-citas.md`
- Informe ejecutivo cliente §5.3 fila 7 (requerimiento registrado 2026-08-15)
