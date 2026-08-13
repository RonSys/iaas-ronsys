# SPEC F2 — Central que No Pierde Llamadas (Asterisk + Trunk SIP + integración al ERP)

- **Estado**: 🟡 **PROPUESTA (2026-08-12)** — pendiente de aprobación por Ron (esfuerzo estimado 3–4 semanas)
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-12
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (spec 03 como referencia de formato; Fase R verificada en código 2026-08-12)

---

## 0. Decisiones (D1–D4 — PROPUESTAS, pendientes de aprobación)

| # | Decisión | Acuerdo propuesto |
|---|---|---|
| D1 | Plataforma PBX | **Asterisk autoalojado en Docker con `network_mode: host`** (imagen `asterisk/asterisk` **A20 LTS**, incluye AMI + ARI). Host network evita el docker-proxy UDP (proxy userland degrada RTP). Alternativa nativa (instalación directa en Debian 12) **solo si** el jitter/audio por Docker resultara inaceptable en pruebas reales. |
| D2 | Trunk SIP | **Trunk SIP de 4 canales** con proveedor peruano. Justificación Erlang B: con 1 Erlang de tráfico ofrecido, 4 canales → **~1.5% de pérdida** vs **~20%** con 2 canales. **Solo G.711 ulaw/alaw** (sin transcoding, sin G.729 licenciado). Pjsip: `externip=190.235.163.29`, `localnet=192.168.1.0/24`, `rtp_symmetric=yes`, `qualify_frequency=30`, `direct_media=no`. |
| D3 | Seguridad SIP | Credenciales largas/aleatorias (generadas por secret), **ACL por IPs del proveedor** en el endpoint del trunk, **fail2ban** con regex SIP (auth failures → ban). AMI/ARI **solo bind 127.0.0.1** (nunca expuestos). No exponer 5060 innecesariamente: port-forward UDP **solo** 5060 + RTP 10000–10100 desde la IP pública. |
| D4 | Integración por eventos | Adapter **`call-bridge`** (servicio Python nuevo) escucha **AMI** (eventos CDR/estado/grabación) + controla **ARI** (originate/click-to-call) → persiste `CallRecord` vía API del backend → publica eventos `call.new` / `call.ended` / `call.recording_ready` a RabbitMQ (cola `iaas-tasks`, `routing_key=iaas-tasks`, patrón fire-and-forget de Fase B). Click-to-call: **Originate vía ARI** desde endpoint autenticado del backend. El worker (`notify_worker`) debe **soportar `call.*` sin romper `delivery.*`** (verificado: hoy los ignora y hace ack — hay que añadir dispatch explícito, §3.5). |

---

## 1. Contexto y objetivo

El local recibe pedidos por teléfono sin registro ni seguimiento: **no hay evidencia de la llamada,
se pierden pedidos cuando el operador está ocupado y no existe trazabilidad** (quién llamó, cuándo,
si se convirtió en pedido). Además, el ERP ya contabiliza todo (ventas → kárdex → asientos), así que
una llamada convertida en pedido debe **reutilizar el motor de ventas existente**, no crear un flujo
paralelo.

**Objetivo de la F2 (MVP):** central telefónica con trunk SIP de 4 canales → la llamada entrante
aparece en un **panel en vivo** (WebSocket) con el número del cliente → el operador atiende
(click-to-call saliente) → **grabación obligatoria** → con un clic la llamada se convierte en
**pedido de delivery reusando `DeliveryService.create_order`** (Sale → kárdex → asiento → KitchenOrder
→ DeliveryOrder DLV- → cocina) → cada llamada queda registrada como `CallRecord` con duración,
estado y grabación → eventos `call.*` en RabbitMQ para consumidores futuros (transcripción, métricas,
CRM).

**Fuera de alcance F2:** transcripción de llamadas (solo `transcription_fk` reservado), IVR
multinivel, cola con espera musical, integración WhatsApp de la grabación, PSTN digital/analógico,
segundo DID.

**Prerrequisito de infraestructura (validado 2026-08-12):** el servidor ronpk (Debian 12, i3-6100,
7.1 GB RAM) tiene **~2.9 GB disponibles y swap 2.5/4 GB en uso** con load ~2.1. **Recomendar +8 GB
RAM** antes del go-live (Asterisk en idle usa ~150–250 MB, pero el host ya está justo; 4 canales G.711
con MixMonitor suman ~90–140 Kbps de red y CPU despreciable — el riesgo es la RAM del host, no la CPU).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-12)

### 2.1 La conversión llamada→pedido REUSA `create_order` (cero duplicación de lógica)

| Componente | Ubicación | Estado |
|---|---|---|
| `DeliveryService.create_order` encadena zona → validación de ítems → promoción → **`SaleService.create_sale`** → kárdex + asiento contable → `KitchenOrder` + broadcast WS cocina → `DeliveryOrder` (DLV-) → eventos `delivery.*` a RabbitMQ | `app/services/delivery_service.py` `create_order()` (~L296) | ✅ Listo para reuso |
| `_system_user_id` resuelve el primer usuario activo del tenant (acciones de sistema sin sesión de staff) | `delivery_service.py` L106 | ✅ Ya existe |
| `SaleService.create_sale` (order_type delivery, kárdex, asiento, pagos yape/plin/cash) | `app/services/sales_service.py` | ✅ Listo |
| **Única brecha**: `create_order` exige `zone_id` (L300) | `delivery_service.py` | ⚠️ El panel del operador debe **seleccionar/inferir zona por dirección** en `convert-to-order` |
| Idempotencia necesaria: `delivery_orders.sale_id` UNIQUE + `tracking_code` DLV- | `app/adapters/db/models/delivery.py` | ✅ El reuso la hereda |

### 2.2 WS por tenant ya existe → panel de llamadas en vivo = extender el patrón

| Componente | Ubicación | Estado |
|---|---|---|
| `WsManager` con dicts por tenant (`_kitchen`, `_waiters`) + `broadcast_to_*` con purga de sockets muertos | `app/core/ws_manager.py` L19 | ✅ Reutilizable |
| Endpoints `/ws/kitchen/{tenant_id}` (L542) y `/ws/waiter/{tenant_id}` (L556), ping/pong | `app/routers/restaurant.py` | ✅ Patrón a copiar → `/ws/calls/{tenant_id}` |

### 2.3 RabbitMQ: routing y dispatch VERIFICADOS (punto crítico para `call.*`)

| Componente | Hallazgo verificado |
|---|---|
| Publicador `notify_events.py` | Publica con `routing_key=settings.rabbitmq_queue` (= `iaas-tasks`, `.env` L31) y payload con `event` + `event_type`. Fire-and-forget: fallo de publish → warning, el flujo del pedido **nunca** depende del evento. |
| Consumidor `notify_worker.py` `_process_event` (L106) | Despacha por `payload.event_type` con `removeprefix("delivery.")`. **Eventos `call.*` HOY: no matchean plantilla → log "sin mapeo de plantilla — ignorado" y ack** (no rompen `delivery.*`, pero se descartan). |
| Conclusión de diseño | **Requisito F2**: añadir dispatch explícito para `call.*` (branch antes del flujo WhatsApp: log estructurado + ack; punto de anclaje para consumidores futuros: transcripción/métricas). Regresión guardada con CA-F2.7. `delivery.*` queda intacto. |

### 2.4 Configuración multi-tenant (patrón D-03) ya establecido

| Componente | Ubicación | Estado |
|---|---|---|
| `companies.settings` (JSONB) con `DeliverySettings` + `WhatsAppSettings` | `app/schemas/__init__.py` L244/L249, `CompanySettings` L271 | ✅ Añadir `CallSettings` (mismo patrón: DID del tenant, extensiones, flags) |
| Persistencia por tenant verificada (bug de objeto no-dirty corregido en Fase A) | spec 03 §5 (2026-08-03) | ✅ Patrón probado en prod |

### 2.5 Lo que NO existe (trabajo nuevo de F2)

| Gap | Detalle |
|---|---|
| Telefonía | **Cero** referencias a asterisk/sip/call_record/originate en el backend (grep verificado) |
| Infra Asterisk | No hay servicio en `docker-compose.yml` (solo postgres/redis/rabbitmq); puertos SIP libres |
| `call_records` | No existe tabla ni modelo |
| Panel de llamadas | No existe página ni endpoint `/calls` |
| `call-bridge` | No existe el adapter AMI/ARI |

### 2.6 Frontend (punto de anclaje del panel)

- `apps/web/src/pages/restaurante/DeliveryPage.tsx` — panel delivery (kanban, pestañas) ✅ patrón de UI
- `apps/web/src/pages/public/PublicMenuPage.tsx` — landing `/menu/:slug` ✅ sin cambios
- Rutas en `App.tsx` + ítem en `Sidebar.tsx` (patrón "Delivery Nocturno") → nuevo "Central Telefónica"

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (F2):**
- Infra Asterisk A20 en Docker (`network_mode: host`): trunk pjsip 4 canales G.711, contexto de entrada
  con grabación MixMonitor, AMI/ARI bind localhost, RTP 10000–10100, fail2ban SIP, port-forward NAT
  documentado (§3.3).
- Migración `call_records` + `CallSettings` en `companies.settings` (patrón D-03) (§3.2).
- Adapter `call-bridge` (servicio Python): AMI listener + ARI originate + persistencia vía API
  backend + publicador `call.*` a RabbitMQ (§3.4).
- API: `GET /api/v1/calls`, `GET /api/v1/calls/{id}`, `POST /api/v1/calls/{id}/convert-to-order`,
  `POST /api/v1/calls/originate`, `WS /ws/calls/{tenant_id}` (§3.5).
- Worker: dispatch explícito de `call.*` sin tocar `delivery.*` (§3.5.4).
- Frontend: panel "Central Telefónica" (llamadas en vivo por WS, click-to-call, conversión a pedido
  con selección/inferencia de zona) (§3.6).
- Purga de grabaciones/registros > 90 días (R2).

**NO INCLUYE (límites F2):** transcripción (solo FK reservada), IVR/cola multimedia, segundo DID,
integración WhatsApp de grabaciones, VoIP sobre TLS/SRTP (queda como hardening futuro, D-03 permite
evolucionar), app móvil.

### 3.2 Modelo de datos (migración `call_records` — borrador redactado, SIN commitear)

```sql
call_records (
  id serial PK,
  tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  external_call_id varchar(64) NOT NULL UNIQUE,    -- Uniqueid de Asterisk (fuente de idempotencia)
  caller varchar(32) NOT NULL,                     -- ANI: número entrante (o destino en outbound)
  callee varchar(32) NOT NULL,                     -- DNIS: extensión/DID atendida (o origen en outbound)
  direction varchar(10) NOT NULL,                  -- inbound | outbound
  status varchar(20) NOT NULL DEFAULT 'ringing',
  started_at timestamptz NOT NULL,
  answered_at timestamptz,
  ended_at timestamptz,
  duration int NOT NULL DEFAULT 0,                 -- segundos (answered→ended)
  recording_path text,                             -- alias/ruta de la grabación MixMonitor (R1)
  transcription_fk int,                            -- RESERVADO: transcripción futura (fuera de alcance F2)
  metadata jsonb,                                  -- contexto asterisk, channel, queue, agente,
                                                   -- trunk, provider, hangup_cause, did_resuelto, ...
  converted_order_id int FK delivery_orders(id) ON DELETE SET NULL,  -- pedido creado desde la llamada
  created_at/updated_at timestamptz,
  CHECK (direction IN ('inbound','outbound')),
  CHECK (status IN ('ringing','in_progress','answered','missed','completed','failed')),
  CHECK (duration >= 0),
  CHECK (recording_path IS NULL OR duration >= 0)
)

-- CallSettings (JSONB en companies.settings, patrón D-03 — sin migración de tabla):
companies.settings.calls = {
  "enabled": true,
  "dids": ["+51 1 555 1234"],           -- DID(s) del tenant → resolución de tenant en inbound
  "extensions": ["100", "101"],         -- extensiones del operador (contexto from-internal)
  "recording": true,                    -- R1: grabación obligatoria
  "retention_days": 90,                 -- R2
  "inbound_behavior": "ring_operator"   -- MVP: ring al operador; cola real en versión futura
}
```

**Notas de diseño:**
- `external_call_id` UNIQUE = Uniqueid de Asterisk → **idempotencia natural**: los eventos AMI
  (`Newchannel`/`Newstate`/`Hangup`) upsertan el mismo registro (patrón: `INSERT ... ON CONFLICT
  (external_call_id) DO UPDATE`); el adapter es re-arrancable sin duplicar llamadas.
- `direction` inbound/outbound; outbound nace del click-to-call (`Originate` vía ARI).
- `status` refleja el ciclo de vida AMI: `ringing → in_progress → answered → completed` (o `missed`/
  `failed` según hangup cause). `duration` solo cuenta tiempo answered.
- `metadata` jsonb crudo (contexto de Asterisk, causas de cuelgue, DID resuelto) — trazabilidad sin
  columnas nuevas.
- `transcription_fk` NULL en F2 (reservado para módulo futuro de transcripción).

### 3.3 Infraestructura Asterisk (D1/D2/D3)

**Servicio Docker** (`docker-compose.yml`, adición propuesta — no aplicada):

```yaml
  asterisk:
    image: asterisk/asterisk:20           # A20 LTS, incluye AMI + ARI
    container_name: iaas-asterisk
    network_mode: host                    # D1: evita docker-proxy UDP (jitter/RTP)
    restart: unless-stopped
    volumes:
      - ./deploy/asterisk/conf:/etc/asterisk:ro
      - asterisk_recordings:/var/spool/asterisk/monitor   # grabaciones MixMonitor (R1)
    environment:
      - ASTERISK_USER=asterisk
      - ASTERISK_GROUP=asterisk
```

**Configuración clave (borrador):**

```ini
; pjsip.conf — trunk del proveedor (D2, D3)
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

[provider-trunk]
type=endpoint
context=from-pstn                    ; contexto de entrada (grabación + ring operador)
disallow=all
allow=ulaw
allow=alaw                           ; SOLO G.711 (D2: sin transcoding, sin G.729)
direct_media=no                      ; media siempre por Asterisk (NAT-friendly)
rtp_symmetric=yes                    ; D2
force_rport=yes
qualify_frequency=30                 ; D2: keepalive NAT
permit=203.0.113.10/32               ; D3: ACL por IPs del proveedor (cambiar por las reales)
deny=0.0.0.0/0

[provider-trunk-auth]
type=auth
auth_type=userpass
username=<user_proveedor>
password=<LARGA-ALEATORIA-32+chars>  ; D3: generada por secret, nunca en el repo

[provider-trunk-aor]
type=aor
max_contacts=1
qualify_frequency=30

; rtp.conf
rtpstart=10000
rtpend=10100                          ; RTP acotado → port-forward reducido

; manager.conf (AMI — D4) y ari.conf (ARI — D4): SOLO 127.0.0.1
[general]
enabled=yes
bindaddr=127.0.0.1
port=5038
; user/password largos y aleatorios (D3)
```

**Contexto de entrada** (`extensions.conf`, borrador):

```ini
[from-pstn]
; R1: grabación obligatoria (MixMonitor) — la llamada continúa si la grabación falla
exten => s,1,NoOp(Llamada entrante: ${CALLERID(num)} → ${EXTEN})
 same => n,MixMonitor(${UNIQUEID}.wav,b)
 same => n,Set(CALL_RECORDING=1)
 same => n,Dial(PJSIP/100,30)          ; ring al operador (MVP: extensión 100)
 same => n,Hangup()

[from-internal]
; salida del operador → trunk (click-to-call Originate usa ARI hacia este contexto)
exten => _X.,1,NoOp(Outbound ${EXTEN})
 same => n,MixMonitor(${UNIQUEID}.wav,b)   ; R1 también en salientes
 same => n,Dial(PJSIP/${EXTEN}@provider-trunk,60)
 same => n,Hangup()
```

**NAT / exposición (D3):** en el router 190.235.163.29 → 192.168.1.35, port-forward **UDP 5060** y
**UDP 10000–10100** únicamente. AMI (5038) y ARI (8088) NO se exponen (bind 127.0.0.1; el
`call-bridge` corre en la misma máquina).

**fail2ban (D3):** jail `asterisk-sip` con regex de fallos de registro/invite
(`Registration from '.*' failed for '<ip>'`, `SecurityEventAuthFailure`), baneo 15 min tras 5
fallos; whitelist de IPs del proveedor.

**RAM (prerrequisito):** +8 GB RAM al servidor antes del go-live (validación 2026-08-12: 2.9 GB
disponibles, swap 2.5/4 GB en uso, load ~2.1).

### 3.4 Adapter `call-bridge` (servicio Python nuevo — D4)

Servicio separado (mismo patrón de imagen Python 3.12-slim que el worker, sin API propia):
conecta a **AMI** (eventos) y **ARI** (control), y habla con el backend por HTTP interno.

**Flujo inbound (llamada entrante):**

1. Asterisk: llamada entra por el trunk → contexto `from-pstn` → MixMonitor + ring al operador.
2. `call-bridge` recibe eventos AMI (`Newchannel` → `Newstate`/`Newconnectedline` → `Hangup`) y
   construye/actualiza el `CallRecord` vía `POST /api/v1/calls/events` (token interno de servicio,
   no JWT de staff).
3. El backend hace upsert por `external_call_id` (idempotente), resuelve `tenant_id` por DID
   (`companies.settings.calls.dids`; MVP: 1 tenant) y hace **broadcast WS `/ws/calls/{tenant_id}`**
   (`call.incoming` / `call.answered` / `call.ended` / `call.recording_ready`).
4. El backend publica **`call.new` / `call.ended` / `call.recording_ready`** a RabbitMQ
   (`routing_key=iaas-tasks`, fire-and-forget, patrón `notify_events`).

**Flujo outbound (click-to-call):**

1. `POST /api/v1/calls/originate` (JWT staff) → backend valida tenant/operador → pide al
   `call-bridge` (HTTP interno) un **Originate vía ARI**:
   `POST /ari/ari/channels?endpoint=PJSIP/<target>@provider-trunk&extension=100&context=from-internal&app=...`.
2. El `CallRecord` outbound nace con el primer evento AMI (`Newchannel`), idempotente por
   `external_call_id`.

**Diseño de eventos RabbitMQ (D4):**

| Evento | payload (mínimo) |
|---|---|
| `call.new` | `event_type`, `tenant_id`, `external_call_id`, `caller`, `callee`, `direction`, `status`, `started_at` |
| `call.ended` | `...` + `duration`, `ended_at`, `hangup_cause` |
| `call.recording_ready` | `...` + `recording_path`, `size_bytes?` |

- Mismo contrato que Fase B: `event` = `call.<event_type>`, `event_type` crudo, `tenant_id`.
- **El pedido/llamada NUNCA dependen del evento** (R3 — fire-and-forget, idéntico a `notify_events`).

### 3.5 Contratos de API

#### 3.5.1 Llamadas (staff, auth JWT + X-Tenant-ID)

```
GET /api/v1/calls?status=&direction=&from=&to=&limit=&offset=
  → 200 { items: [{id, external_call_id, caller, callee, direction, status,
           started_at, answered_at, ended_at, duration, recording_path,
           converted_order_id, metadata}], total }
  Filtros: status (ringing|in_progress|answered|missed|completed|failed),
    direction (inbound|outbound), rango started_at. SIEMPRE filtrado por tenant (R4).

GET /api/v1/calls/{id}
  → 200 detalle completo | 404 (o 404 si no pertenece al tenant)

POST /api/v1/calls/{id}/convert-to-order
  Request: { zone_id, items: [{menu_item_id, quantity, modifiers:[{id, quantity}]}],
             customer: {name?, phone?, address}, payment: {method: "yape"|"plin"|"cash", reference?},
             notes? }
  Validaciones:
    - La llamada debe estar `answered` o `completed` (422 si sigue ringing);
    - **1 sola conversión por llamada** (409 si `converted_order_id` ya existe — idempotencia);
    - zona requerida (brecha Fase R §2.1): el panel la ofrece por selector + **sugerencia por
      distrito de la dirección** (match sobre `delivery_zones.districts` jsonb); si el cliente no
      tiene dirección, el operador la captura (la llamada ya trae `caller` como phone default).
  Efectos (transacción única — REUSA `DeliveryService.create_order`, §2.1):
    Sale (order_type=delivery, sistema vía `_system_user_id`) → kárdex → asiento → KitchenOrder +
    broadcast WS cocina → DeliveryOrder (DLV-) → eventos `delivery.confirmed/new_order` →
    se vincula `call_records.converted_order_id` + broadcast WS `/ws/calls` (`call.converted`).
  → 201 { tracking_code, sale_id, sale_number, status: "received", totals, call_id }
  → 409 conversión duplicada | 422 estado/ítems inválidos | 404 llamada inexistente

POST /api/v1/calls/originate
  Request: { target: "+51 999 999 999", extension: "100" }
  → 202 { external_call_id, status: "ringing" }   (CallRecord outbound nace con evento AMI)
  → 400 número inválido | 409 el operador ya tiene una llamada activa (1 línea activa por operador)
```

#### 3.5.2 Evento interno (solo call-bridge → backend, token de servicio)

```
POST /api/v1/calls/events        { external_call_id, tenant_id?, caller, callee, direction,
                                   status, started_at, answered_at?, ended_at?, duration?,
                                   recording_path?, metadata? }
  → 200 { id, created: bool }    (upsert por external_call_id; broadcast WS + publish call.* )
  → 401 sin token de servicio | 403 IP no autorizada (allowlist del call-bridge)
```

#### 3.5.3 WebSocket panel en vivo (extensión del patrón existente §2.2)

```
WS /ws/calls/{tenant_id}         (mismo mecanismo que /ws/kitchen: tenant en path + ping/pong)
  eventos del servidor → cliente:
    call.incoming       { external_call_id, caller, callee, started_at }
    call.answered       { external_call_id, caller, answered_at }
    call.ended          { external_call_id, caller, duration, status, hangup_cause }
    call.recording_ready{ external_call_id, recording_path }
    call.converted      { external_call_id, tracking_code, sale_id }
  Implementación: WsManager gana `_calls` dict + connect/disconnect/broadcast_to_calls
    (clon del patrón `_kitchen`/`_waiters`, incl. purga de sockets muertos).
```

#### 3.5.4 Worker (`notify_worker.py`) — soporte `call.*` sin romper `delivery.*`

- En `_process_event` (hoy L106): **branch por prefijo antes del flujo WhatsApp**:
  - `call.*` → log estructurado + **ack** (punto de anclaje: consumidores futuros de transcripción/
    métricas consumen de la misma cola o del broadcast WS; el ack evita redelivery infinito).
  - `delivery.*` → flujo actual intacto (`_recipient_and_template` + notifier).
- Guardas: `call.*` nunca entra a `_recipient_and_template` (regresión cubierta por CA-F2.7); el
  worker no puede crashear por un `call.*` malformado (validación de campos con defaults).

### 3.6 Frontend — panel "Central Telefónica"

- `pages/restaurante/CallCenterPage.tsx` (patrón `DeliveryPage.tsx`):
  - **Llamadas en vivo**: tarjetas por llamada (número, dirección, estado, timer) vía
    `WS /ws/calls/{tenant_id}`; histórico con filtros (status/dirección/rango).
  - **Click-to-call**: botón en cada llamada → `POST /api/v1/calls/originate` → la saliente aparece
    en el panel.
  - **Convertir a pedido**: modal reusando el flujo de checkout de DeliveryPage (items del menú +
    zona con **sugerencia por distrito** + pago) → `POST /api/v1/calls/{id}/convert-to-order` →
    redirige al kanban delivery con el DLV- creado.
  - **Grabación**: link de descarga/escucha cuando `call.recording_ready` llega (R1).
- `App.tsx`: ruta `/restaurante/central`; `Sidebar.tsx`: ítem "Central Telefónica" (patrón Delivery).

### 3.7 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R1 | **Grabación obligatoria**: toda llamada (in/out) se graba con MixMonitor; si la grabación falla, la llamada continúa y `metadata.recording_failed=true` (alerta al panel, no bloquea). |
| R2 | **Retención 90 días**: job diario purga `call_records` + grabaciones con `ended_at < now() - 90d` (configurable en `CallSettings.retention_days`). |
| R3 | **El evento nunca bloquea la llamada ni el pedido**: publicar a RabbitMQ es fire-and-forget (patrón Fase B); fallo de publish/worker → warning, flujo intacto. |
| R4 | **Multi-tenant**: tenant resuelto por DID en inbound (`companies.settings.calls.dids`); toda query filtra tenant; WS por tenant; `CallSettings` aislado por tenant (D-03). |
| R5 | **Seguridad SIP (D3)**: credenciales aleatorias largas, ACL de IPs del proveedor, fail2ban, AMI/ARI solo localhost, port-forward mínimo. |
| R6 | **Una conversión por llamada**: `converted_order_id` setea una vez; segundo intento → 409. |
| R7 | **Conversión reusa `create_order`**: Sale → kárdex → asiento → KitchenOrder → DeliveryOrder (DLV-) → cocina; el operador selecciona zona (sugerida por distrito de la dirección). |
| R8 | **Idempotencia por `external_call_id`**: upsert de eventos AMI nunca duplica registros (re-arranque seguro del call-bridge). |

### 3.8 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F2.1 | Llamada entrante real (teléfono → DID) | `call_records` con `status=ringing` → `answered` → `completed`, `caller/callee/direction` correctos, duración = answered→ended; evento `call.new` publicado en RabbitMQ (cola `iaas-tasks`) |
| CA-F2.2 | Llamada con MixMonitor | Archivo `.wav` en el volumen de grabaciones + `recording_path` en el registro + evento `call.recording_ready` |
| CA-F2.3 | `convert-to-order` válido (zona + items + pago) | 201 con DLV-; en BD: `sales` (order_type=delivery, usuario sistema) + kárdex descontado + asiento contable + `kitchen_orders` + `delivery_orders`; `call_records.converted_order_id` vinculado; WS cocina + `call.converted` + eventos `delivery.*`; **segundo POST → 409** |
| CA-F2.4 | Concurrencia de 4 canales | 4 llamadas simultáneas (simulador SIP o tráfico real) sin pérdida (Erlang B ~1.5%); todas registradas y grabadas |
| CA-F2.5 | Endpoints `/api/v1/calls*` sin token | 401 (staff); `POST /api/v1/calls/events` sin token de servicio o IP no autorizada → 401/403 |
| CA-F2.6 | Aislamiento de tenant | Llamadas de tenant A invisibles en `GET /api/v1/calls` de tenant B; WS `/ws/calls/{tenant}` de A no recibe eventos de B |
| CA-F2.7 | Eventos `call.*` en RabbitMQ + worker | `call.new`/`call.ended`/`call.recording_ready` consumidos y acked (sin redelivery); **`delivery.confirmed`/`status_changed` siguen disparando WhatsApp exactamente igual** (regresión delivery.* = 0) |
| CA-F2.8 | Click-to-call | `POST /api/v1/calls/originate` → 202; llamada saliente suena en la extensión 100, se registra como outbound y aparece en el panel en vivo |
| CA-F2.9 | Retención (R2) | Job purga registros/grabaciones > 90 días (simulado con datos con `ended_at` viejo) |
| CA-F2.10 | RTP/NAT (D2) | Llamada real a través del NAT: audio bidireccional sin jitter (host network + `rtp_symmetric` + `direct_media=no`); SDP responde con `externip=190.235.163.29` |
| CA-F2.11 | `alembic upgrade head` | Tabla `call_records` creada; `downgrade` revierte; sin cambios en tablas existentes (solo adición) |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada — 3–4 semanas)

1. **Semana 1 — Infra Asterisk (D1/D2/D3)**: servicio Docker `asterisk` (`network_mode: host`),
   config pjsip (trunk 4 canales G.711, ACL proveedor), contexto `from-pstn` + MixMonitor, AMI/ARI
   localhost, fail2ban; **+8 GB RAM al servidor (prerrequisito)**; port-forward UDP 5060 +
   10000–10100; prueba de llamada real con el proveedor (audio, NAT, jitter) → decidir Docker vs
   nativo si jitter inaceptable (D1).
2. **Semana 1–2 — Backend**: migración `call_records` + `CallSettings` (D-03); `WsManager` gana
   `_calls`; routers `calls.py` (list/detail/convert-to-order/originate/events) + `WS
   /ws/calls/{tenant_id}`; `CallService` (upsert por `external_call_id`, resolución DID→tenant,
   broadcast WS, publish `call.*`); `convert-to-order` reusa `create_order` + sugerencia de zona por
   distrito + idempotencia 409. Tests.
3. **Semana 2–3 — `call-bridge` + worker**: adapter AMI listener + ARI originate (contenedor
   Python 3.12-slim, token de servicio, allowlist IP); publicador `call.*` (fire-and-forget);
   `notify_worker` branch `call.*` (ack + log) sin tocar `delivery.*`. Tests + verificación en vivo
   de CA-F2.7.
4. **Semana 3 — Conversión + ajustes**: flujo completo llamada→pedido con el proveedor real;
   grabaciones y purga 90 días (R1/R2); edge cases (missed/failed, llamada sin conversión).
5. **Semana 3–4 — Frontend**: `CallCenterPage.tsx` (panel en vivo WS, histórico, click-to-call,
   modal convertir con sugerencia de zona, link de grabación); ruta `/restaurante/central` +
   Sidebar. Build `tsc -b` + `vite build` limpios.
6. **Semana 4 — QA + deploy**: ejecutar CA-F2.1…CA-F2.11 en QA; suite backend completa (sin
   regresiones en delivery.*); deploy `./deploy.sh --env prod` con respaldo `.bak-<fecha>` +
   `pg_dump` previo (patrón spec 03 Fase 6); monitoreo de grabaciones y RAM.

---

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-12 (v0.1)**: spec creada. Fase R completa — verificada en código:
  - `DeliveryService.create_order` reutilizable para la conversión (encadena SaleService.create_sale
    → kárdex + asiento + KitchenOrder + DeliveryOrder DLV- + eventos delivery.*; `_system_user_id`
    en L106 para acciones de sistema). **Única brecha**: `create_order` exige `zone_id` → el panel
    debe seleccionarla (sugerencia por distrito en `delivery_zones.districts`).
  - `WsManager` por tenant + `/ws/kitchen` y `/ws/waiter` verificados → `/ws/calls/{tenant_id}`
    extiende el patrón.
  - RabbitMQ: publicador usa `routing_key=iaas-tasks` y el worker despacha por `payload.event_type`
    (`removeprefix("delivery.")`) — **verificado que hoy `call.*` se descartarían (ack silencioso)**;
    la spec exige dispatch explícito con CA-F2.7 de no-regresión.
  - `companies.settings` JSONB con DeliverySettings/WhatsAppSettings → `CallSettings` sigue el
    patrón D-03; cero telefonía existente en el código (grep).
  - Infra validada por DevOps: ronpk Debian 12, i3-6100, 7.1 GB RAM (2.9 libres, swap 2.5/4 GB),
    load ~2.1, IP pública 190.235.163.29 → 192.168.1.35 NAT; puertos SIP libres.
  - **Pendiente**: aprobación de D1–D4 por Ron. Esfuerzo estimado 3–4 semanas. Prerrequisito
    RAM +8 GB antes del go-live.

---

## 6. Referencias

- Spec 03 (dark kitchen — motor de ventas, `create_order`, WS, eventos RabbitMQ Fase B, patrón D-03):
  `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Spec 01 (patrón de transacción atómica y pre-check 409): `docs/specs/02-recetas-costos/01-spec-recetas-productos-v0.2.md`
- Erlang B (cálculo de canales trunk): 1 Erlang ofrecido → 4 canales ≈ 1.5% bloqueo; 2 canales ≈ 20%
- Plan de exposición pública (NAT/port-forward/red): `docs/plan-exposicion-publica-v0.5.md`
- Manuales operativos (patrón de documentación para el panel): `docs/manuales/manual-delivery-dark-kitchen.md`
- Infra Docker Compose (postgres/redis/rabbitmq): `docker-compose.yml` (raíz del proyecto)
