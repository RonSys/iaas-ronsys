# Backlog Gherkin — F6: Agenda de Citas (Reservas por mesa y horario + integración Recepcionista IA)

**Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
**Origen:** Spec 07 — `docs/specs/03-delivery/07-spec-agenda-citas-v0.1.md` (BORRADOR, pendiente aprobación de Ron 2026-08-15)
**Generado por:** Jarvis (orquestador) 🤖
**Fecha:** 2026-08-15
**Estado:** 🟡 Listo para desarrollo **solo tras aprobación de la spec** (decisiones D3/D4 pendientes de Ron)
**Total Historias:** 10
**Alcance:** Entidad `appointments` (migración `0021`), disponibilidad anti-doble-reserva, CRUD + transiciones de estado, integración voz F3 (skill de agenda), confirmación/recordatorio WhatsApp (motor F1, dry-run), aislamiento multi-tenant, espejo del mapa de mesas.

---

## 📌 Contexto

F6 crea el **módulo de agenda/citas** que hoy no existe: la tabla `tables` solo tiene un toggle
`reserved` (sin fecha/hora/cliente). Se apoya en infraestructura ya desplegada:
- **F1 (WhatsApp)**: motor de eventos RabbitMQ `iaas-tasks` + `MetaCloudNotifier`/`DryRunNotifier` — para `appointment.confirmed` / `appointment.reminder` (dry-run sin cuenta Meta).
- **F3 (Recepcionista IA)**: `voice_ai_service` + `ConversationStateMachine` — se extiende con estado `taking_reservation` y skills de agenda (dominio acotado R1: nunca inventar).
- **F2 (Central Telefónica)**: `call_records` — trazabilidad `appointments.call_id` (grabación/transcripción).

Estas 10 historias cubren los **12 criterios de aceptación (CA-F6-1..12)** y las **10 reglas de
negocio (R1..R10)** de la spec, más los contratos §3.3 (availability, CRUD, transiciones, remind),
la config §3.2 (`companies.settings.appointments`) y la integración voz §3.3.

### 📋 Mapa de trazabilidad Spec → Historias

| Criterio / Regla | Historias |
|------------------|-----------|
| CA-F6-1 + CA-F6-4 (crear cita válida / datos inválidos) | HU-F6-01 |
| CA-F6-2 + R2 (doble reserva → 409) | HU-F6-02 |
| CA-F6-3 (disponibilidad por fecha/guests) | HU-F6-03 |
| CA-F6-5 (solicitada→confirmada + espejo mesa + WhatsApp) | HU-F6-04 |
| CA-F6-6 + R5 (transiciones cumplida/cancelada/no_show + espejo) | HU-F6-05 |
| CA-F6-7 + R9 (recordatorio automático idempotente) | HU-F6-06 |
| CA-F6-8 + R6 (reserva por voz con trazabilidad call_id) | HU-F6-07 |
| CA-F6-9 + R1 (IA sin disponibilidad → alternativas reales o transferencia) | HU-F6-08 |
| CA-F6-10 + R7 (aislamiento tenant + rate limit) | HU-F6-09 |
| CA-F6-11 + CA-F6-12 (migración 0021 + regresión suite) | HU-F6-10 |

### 🔑 Supuestos de entrada (verificados)

- F1/F2/F3 desplegadas en prod: motor WhatsApp (eventos + worker + notifier), `call_records` (0018), `voice_ai_service` (0019), `assistant` (0020). Head alembic actual = `0020_assistant` → F6 = `0021_appointments`.
- Backend listo para reuso: patrón D-03 (`companies.settings` JSONB), `rate_limit` Redis, WsManager, worker con dispatch por routing_key, `ConversationStateMachine` extensible.
- Trabajo nuevo F6: tabla `appointments` + servicio de disponibilidad (overlap) + router + eventos `appointment.*` + job recordatorio + estado `taking_reservation` + skills de agenda + UI mínima staff.
- **Decisiones aprobadas por Ron (2026-08-15)**: D3 ventana de reservas independiente 12:00–23:00 **configurable desde el frontend (UI staff)** · D4 **mesa libre con duración** (sin grilla fija) · menor: solo staff + voz en F6. La Gherkin asume estas decisiones.

---

## Historias

---

### HU-F6-01 — Crear cita en mesa libre (flujo feliz + validaciones)

**Como** personal del restaurante (o la IA por voz),
**quiero** registrar una cita con mesa, fecha, hora y datos del cliente,
**para** que la reserva quede en la agenda con estado `solicitada`.

**Criterios de aceptación:**
- Dado un tenant con mesas activas (ej. mesa 3, capacidad 4, sección Salón) y ventana de reserva 12:00–23:00
- Cuando el staff crea una cita `POST /api/v1/appointments` con `{table_id: 3, date: 2026-08-20, time: "19:00", guests: 4, customer_name: "Juan Pérez", customer_phone: "+51987654321", source: "in_person"}`
- Entonces la API responde **201** con la cita creada, estado `solicitada`, `source: in_person`, y `starts_at` = 2026-08-20T19:00 local
- Y la cita NO se solapa con ninguna cita activa de la mesa 3
- Y el mapa de mesas **NO cambia** (la mesa sigue `available` hasta confirmar — R4)

**Escenarios de rechazo (422):**
- `time: "11:00"` (fuera de ventana 12:00–23:00) → 422 con detalle
- `guests: 10` en mesa de capacidad 4 → 422
- `guests: 0` o `duration_min: 10` → 422 (CHECKs 1–50 y 15–240)
- `customer_name` vacío → 422

---

### HU-F6-02 — Doble reserva rechazada (anti-solapamiento)

**Como** sistema de agenda,
**quiero** rechazar citas que se solapen en la misma mesa,
**para** que nunca haya doble reserva (R2).

**Criterios de aceptación:**
- Dado una cita activa en mesa 3 de 19:00 a 20:00 (estado `confirmada`)
- Cuando se intenta crear otra cita en mesa 3 con `time: "19:30"` y duración 60 min (solapamiento 19:30–20:30)
- Entonces la API responde **409** (conflicto de disponibilidad) y NO crea ninguna fila
- Y tampoco se crea si el rango es idéntico (`19:00` con 60 min → UNIQUE `(tenant_id, table_id, starts_at)`)
- Y tampoco si la cita existente está `solicitada` (solo `cumplida`, `cancelada`, `no_show` liberan la mesa)

---

### HU-F6-03 — Consultar disponibilidad en tiempo real

**Como** staff (o la IA por voz),
**quiero** consultar qué mesas están libres en una fecha/hora con N personas,
**para** ofrecer alternativas reales al cliente.

**Criterios de aceptación:**
- Dado un tenant con mesas 1-6 (capacidades 2/4/6/8) y una cita confirmada en mesa 3 a las 19:00
- Cuando se consulta `GET /api/v1/appointments/availability?date=2026-08-20&guests=4&from=18:00&to=21:00`
- Entonces la respuesta 200 incluye la mesa 3 como NO disponible en el rango solapado
- Y las demás mesas con capacidad ≥ 4 aparecen disponibles con `table_id`, `table_number`, `section`, `capacity`, `start`, `end`
- Y la respuesta está rate-limited (Redis) — abuso → 429

---

### HU-F6-04 — Confirmar cita → espejo de mesa + WhatsApp

**Como** staff (o la IA),
**quiero** confirmar una cita `solicitada`,
**para** que la mesa quede reservada en el mapa y el cliente reciba confirmación.

**Criterios de aceptación:**
- Dado una cita `solicitada` con `table_id: 3` y `customer_phone` válido
- Cuando se hace `PATCH /api/v1/appointments/{id}` con `{status: "confirmada"}`
- Entonces la API responde 200 con estado `confirmada`
- Y `tables.status` de la mesa 3 pasa a `reserved` (espejo D1/R4)
- Y se publica el evento `appointment.confirmed` a RabbitMQ `iaas-tasks` (worker → WhatsApp; **dry-run** si no hay cuenta Meta: cero HTTP, log)
- Y transición inválida (ej. `solicitada → cumplida`) → 422

---

### HU-F6-05 — Ciclo de vida: cumplida / cancelada / no_show

**Como** staff,
**quiero** avanzar el estado de la cita,
**para** que la agenda refleje la realidad y las mesas se liberen.

**Criterios de aceptación:**
- Dado una cita `confirmada` en mesa 3
- Cuando se marca `cumplida` → 200; `tables.status` → `available` (si no hay otra cita activa en la mesa)
- Cuando se marca `cancelada` → 200; mesa liberada; evento opcional de aviso (template `appointment_cancelled` si existe)
- Cuando se marca `no_show` → 200; mesa liberada
- Y una cita `cumplida` NO puede volver a `confirmada` (terminal — 422)
- Y una cita inexistente → 404; sin rol staff → 403

---

### HU-F6-06 — Recordatorio automático 24h (idempotente)

**Como** sistema,
**quiero** enviar recordatorio de cita confirmada 24h antes,
**para** reducir no-shows (R9).

**Criterios de aceptación:**
- Dado una cita `confirmada` con `starts_at` = mañana 19:00 y `reminder_hours_before: 24`
- Cuando corre el job diario de recordatorios
- Entonces se publica `appointment.reminder` con el payload de la cita (dry-run sin Meta)
- Y si el job vuelve a correr en el mismo día, **NO** re-envía (idempotencia: marca `reminded_at` o filtro por ventana)
- Y una cita `solicitada` o ya `cumplida/cancelada` NO genera recordatorio

---

### HU-F6-07 — Reserva por voz (Recepcionista IA F3)

**Como** cliente que llama,
**quiero** que la IA consulte la agenda y reserve mi mesa por teléfono,
**para** completar el flujo del reel (contestar → consultar agenda → reservar → confirmar).

**Criterios de aceptación:**
- Dado el agente de voz F3 activo (simulador `simulate_voice_call.py` o trunk SIP) y el estado `taking_reservation` en la máquina de estados
- Cuando el cliente dice "¿tienen mesa para 4 el viernes a las 8?" 
- Entonces la IA consulta `availability()` real (R1: nunca inventa) y responde con alternativas reales
- Cuando el cliente confirma "reserva la mesa 3 a las 8" y da nombre + teléfono
- Entonces se crea la cita con `source: "voice_ai"` y `call_id` = `external_call_id` de la llamada (R6)
- Y la IA confirma por voz (repetición de fecha/hora/mesa) y dispara `appointment.confirmed` (WhatsApp si el cliente dio teléfono)
- Y la grabación/transcripción de la llamada queda enlazada vía `call_records` (CA-F6-8)

---

### HU-F6-08 — IA sin disponibilidad → alternativas reales o transferencia

**Como** Recepcionista IA,
**quiero** manejar el caso de agenda llena,
**para** nunca prometer una mesa que no existe (R1, F3 D9).

**Criterios de aceptación:**
- Dado que no hay mesas libres en el rango pedido (ej. viernes 20:00 completo)
- Cuando el cliente pide esa hora
- Entonces la IA ofrece alternativas reales (otra hora con disponibilidad, otra mesa/sección)
- Y si el cliente insiste o pide algo fuera de dominio → **transferencia a humano con contexto** (motivo `low_confidence`/`out_of_domain`, contexto = fecha/hora/personas solicitadas)
- Y en ningún caso la IA inventa una mesa/hora que no esté en la disponibilidad real

---

### HU-F6-09 — Aislamiento multi-tenant + rate limit

**Como** plataforma,
**quiero** que cada negocio vea solo su agenda,
**para** mantener la separación por tenant (R7).

**Criterios de aceptación:**
- Dado tenant A con cita en mesa 3 y tenant B sin citas
- Cuando B consulta `GET /api/v1/appointments?date=...` con su token
- Entonces B ve solo sus citas (0) y NO las de A
- Y B intenta `PATCH` la cita de A → 404 (no existe para B)
- Y `availability` sin auth o con abuso de requests → 401/429 (rate-limit Redis)

---

### HU-F6-10 — Migración 0021 + regresión completa

**Como** equipo,
**quiero** aplicar la migración sin romper nada existente,
**para** cumplir CA-F6-11/12 y el Spec Anchor.

**Criterios de aceptación:**
- Dado el árbol alembic en head `0020_assistant`
- Cuando se ejecuta `alembic upgrade head`
- Entonces se crea `appointments` (columnas + CHECKs + UNIQUE + índices + grants dashboard_ro/dashboard_rw_revision)
- Y `downgrade` a `0020_assistant` revierte todo (tabla eliminada)
- Y la suite completa corre verde: pytest F6 (≈15-20 nuevos) + regresión F1/F2/F3/F5 (517+ existentes) + flake8 0 + build frontend OK
- Y `make anchor-check` (o equivalente de grants del proyecto) sin drift

---

## 📊 Resumen

| Historias | Criterios/Reglas cubiertos | Esfuerzo estimado |
|---|---|---|
| HU-F6-01..03 (CRUD + disponibilidad) | CA-F6-1..4 · R2/R3/R7 | 4–6 h |
| HU-F6-04..06 (estados + WhatsApp + recordatorio) | CA-F6-5..7 · R4/R5/R8/R9 | 4–6 h |
| HU-F6-07..08 (integración voz) | CA-F6-8..9 · R1/R6/R10 | 4–5 h |
| HU-F6-09..10 (tenant + migración) | CA-F6-10..12 · R7 | 3–4 h |
| **Total** | **CA-F6-1..12 · R1..R10** | **~16–21 h** |

**Estado:** ✅ **APROBADA por Ron (2026-08-15)** — Spec 07 🟢 APROBADA (D3/D4/menor cerradas). Lista para implementación cuando Ron lo indique.
