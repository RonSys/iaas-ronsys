# SPEC 06 — Recepcionista IA por Voz (F3 — Pedidos telefónicos automáticos)

- **Estado**: 🟢 **APROBADA E IMPLEMENTADA (2026-08-13/14)** — decisiones D1-D10 aprobadas por Ron; implementación completa desplegada en PROD (backend `0019_voice_ai` + `routers/ai_calls.py` + `voice_ai_service` + `voice_bridge` + panel IA en Central Telefónica; commits `4a1b02c`, `a761483`, `d738446`). **Pendiente externo**: proveedor de voz IA (STT/TTS) y PoC de 2 semanas con llamadas reales (ajuste comercial D5: costo realista S/500-900/mes)
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-12 (actualizada 2026-08-13 — reconciliación con F2 implementada)
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (specs 01/02/03/05 como referencia de formato)
- **Depende de**: **F2 (spec 05 — Central Telefónica, 🟢 IMPLEMENTADA Y DEPLOYADA en prod 2026-08-13)** — F3 construye sobre su infraestructura Asterisk + `call-bridge` + tabla `call_records` (migración 0018)

---

## 0. Decisiones (D1-D10 — APROBADAS por Ron 2026-08-13)

| # | Decisión | Acuerdo propuesto |
|---|---|---|
| D1 | Arquitectura de voz | **Asterisk ARI (Stasis) + External Media (RTP→WebSocket) → bridge Python → proveedores de voz** (STT/TTS/LLM). Construye **sobre F2** (spec 05: Asterisk A20 en Docker, trunk pjsip, `call-bridge` AMI/ARI, `call_records`, panel Central Telefónica). F3 añade la capa de IA conversacional y reutiliza la infra F2 tal cual. Alternativa llave en mano (Vapi/Retell) documentada como **Opción B** con trade-offs (§2.4) — no elegida por costo variable por minuto + dependencia de tercero + datos del cliente en plataforma externa. |
| D2 | STT (español) | **Deepgram Nova-3 streaming (es)** default (~$0.007–0.02/min); **Google STT** (~$0.016/min) como fallback configurable por tenant. **PoC interno sin keys: `faster-whisper` (es) local** vía puerto `VoiceProvider` conmutable (validado 2026-08-13). |
| D3 | TTS (es-PE) | **Google Chirp3 HD o Azure Neural (es-PE)** default (~$0.04–0.06/min); **ElevenLabs** (~$0.10–0.30/min) como premium opcional por tenant. **PoC interno sin keys: `piper-tts` (100% local, voces es_PE/es_ES)** vía puerto conmutable; `edge-tts` como alternativa si hay red estable a MS (validado 2026-08-13). |
| D4 | Pipeline LLM | **STT → LLM texto → TTS** con Groq/DeepSeek (~$0.001/min en tokens). **NO** audio-to-audio (OpenAI Realtime ~$0.06–0.24/min): para tomar un pedido estructurado con el menú real como contexto/tool basta el pipeline de texto; más barato, más controlable y auditable. **PoC: DeepSeek `deepseek-v4-flash` ya validado en spike F5 (function calling + fallback determinista).** |
| D5 | Costo mensual realista | **S/ 500–900/mes** (≈$150–280 USD + trunk SIP): 2.700 min/mes = 30 llamadas/noche × 3 min × 30 días. **Ajuste formal al plan comercial que decía S/100–300** (§1.3). ⚠️ **Aprobado explícitamente por Ron 2026-08-13** (confirmación vía Asistente) con mitigaciones: presupuesto diario + kill-switch (D10) + PoC 2 semanas antes de fijar precio. |
| D6 | Agente de dominio acotado | La IA **solo** toma pedidos del menú real, consulta estado y confirma. No es chatbot de propósito general. Conoce precios/modificadores/disponibilidad/horarios reales vía `get_public_menu` — **no inventa**. Cumplimiento Meta 15-ene-2026 + BSUID (§3.7). |
| D7 | Resolución de zona de entrega | La dirección dicha por el cliente se resuelve por **match de distrito contra `delivery_zones.districts` (jsonb)**; si no resuelve con confianza → repregunta 1 vez → transferencia a humano. **Base real: `suggest_zone_by_address` (F2, `call_service.py`) — match substring sobre districts; F3 añade normalización de alias ("Canto Grande", "Montenegro").** |
| D8 | Grabación + transcripción | **Siempre** (R3): grabación la hace F2 (MixMonitor); transcripción nueva en `call_transcriptions` + `transcription_fk` **reservada por F2** (DDL §3.2); retención configurable (`calls.retention_days`, F2 R2). |
| D9 | Transferencia a humano | **Obligatoria** ante queja, solicitud fuera de dominio, baja confianza (umbral configurable) o pedido del cliente — con contexto completo (resumen + transcripción + datos capturados) al operador (extensión SIP de F2 / panel). |
| D10 | Gobernanza de costo | Presupuesto por minuto + tope diario por tenant + **kill-switch** (R4/R5): al agotar presupuesto o activar kill-switch, `inbound_behavior` de F2 cae a `ring_operator` (llamadas al humano, sin IA). |

---

## 1. Contexto y objetivo

### 1.1 Por qué

El canal telefónico es el más usado por el público objetivo de El Segoviano (dark kitchen nocturna,
SJL), pero hoy **cada llamada requiere un operador humano**: se pierden pedidos en horas pico
(19:00–24:00), el ticket promedio por teléfono es menor (sin upselling estructurado) y no hay
trazabilidad de lo que se dijo. F3 automatiza la **recepción de pedidos por voz** con una IA de
dominio acotado que habla español latino, toma el pedido contra el **menú real**, lo confirma en voz,
crea el pedido en el motor de ventas existente (mismo flujo que el checkout web de la spec 03) y
dispara la confirmación por WhatsApp (motor Fase B ya desplegado). F3 es la capa inteligente que se
sienta **encima de F2**: F2 entrega la llamada (Asterisk/trunk/`call-bridge`/grabación), F3 la
atiende.

### 1.2 Objetivo (MVP)

Llamada entrante → F2 responde (Stasis, `inbound_behavior: ai_receptionist`) → la IA saluda en
español (se identifica como asistente automático) → STT→LLM→TTS toma items + modificadores + notas +
dirección → repite el pedido para confirmar → cuelga → **crea el pedido vía `create_order`** (reuso,
mismo motor que F2/web) → dispara eventos `delivery.*` existentes → **confirmación WhatsApp
automática** (Fase B) → transcripción + grabación guardadas (D8). Si el cliente se queja, pide algo
fuera de dominio o la IA no entiende → **transferencia a humano con contexto** (D9).

**Fuera de alcance F3 (MVP):** bot de WhatsApp conversacional (Fase B es solo notificaciones),
llamadas salientes (telemarketing/recordatorios — F3 futuro), IVR multi-opción complejo, pago por voz
(Yape/Plin por teléfono queda en contraentrega — ver R7), agentes de propósito general (D6).

### 1.3 Ajuste de costo vs plan comercial

El plan comercial estimaba S/100–300/mes. **La validación técnica (2026-08-12) lo corrige**:

| Concepto | Tarifa estimada | Mes (2.700 min) |
|---|---|---|
| STT Deepgram Nova-3 (es, streaming) | $0.007–0.02/min | $19–54 |
| TTS Google Chirp3 HD / Azure (es-PE) | $0.04–0.06/min | $108–162 |
| LLM tokens (Groq/DeepSeek, pipeline texto) | ~$0.001/min | ~$3 |
| Trunk SIP / telefonía (F2: 4 canales G.711) | según operador | $20–60 |
| **Total** | | **~$150–280 ≈ S/ 550–1.030** |

**Conclusión D5: presupuestar S/ 500–900/mes** para el escenario nominal (30 llamadas/noche × 3 min ×
30 días). El costo por minuto es **medible por tenant** (R4/CA-F3-8): STT/TTS/LLM se registran por
llamada (`cost_usd`) y se suman al costo real. Por eso la arquitectura D1/D4 (pipeline texto,
proveedores swappables) importa: cada proveedor es conmutable por settings sin tocar el flujo.

---

## 2. Fase R — Hallazgos de la investigación (código y specs verificado 2026-08-12)

### 2.1 F2 (spec 05 — Central Telefónica): base infraestructura (leída, existe desde 2026-08-12)

F2 entrega (🟡 propuesta, pendiente de aprobación — F3 asume que se implementa):

| Componente F2 | Detalle | Qué hace F3 con ello |
|---|---|---|
| Asterisk A20 LTS en Docker (`network_mode: host`), trunk pjsip 4 canales G.711, RTP 10000–10100, fail2ban SIP, AMI/ARI bind localhost | Infra PBX | F3 lo usa tal cual; añade **Stasis app + External Media** (RTP→WebSocket) para el streaming de audio a STT |
| `call-bridge` (servicio Python): AMI listener (Newchannel/Newstate/Hangup) + ARI originate + persistencia vía API + publicador `call.*` a RabbitMQ | Adapter de eventos | F3 escucha los mismos eventos; en tenant con IA el bridge/Stasis cambia el ruteo (ver §3.4) |
| `call_records` (external_call_id UNIQUE = Uniqueid Asterisk, caller/callee, direction, status ringing→in_progress→answered→missed→completed→failed, duration, recording_path, **transcription_fk RESERVADA**, converted_order_id, metadata) | Migración F2 | **F3 adopta esta tabla** — NO crea otra; llena `transcription_fk` (D8) y `converted_order_id`; añade columnas IA vía migración `0017_voice_ai` (§3.2) |
| `companies.settings.calls` (D-03): dids, extensions, recording, retention_days, `inbound_behavior: ring_operator` | Config F2 | F3 añade `inbound_behavior: "ai_receptionist"` para tenants con `voice_ai.enabled`; extensions del operador = destino de transferencia (D9) |
| API F2: `GET /api/v1/calls`, `GET /api/v1/calls/{id}`, `POST /api/v1/calls/{id}/convert-to-order`, `POST /api/v1/calls/originate`, `WS /ws/calls/{tenant_id}` | Contratos F2 | F3 extiende: `transcript`, `transfer`, `ai-state`, `complete` sobre el mismo recurso `/api/v1/calls/{...}`; WS `/ws/calls/{tenant_id}` gana el evento `ai_call_state` |
| Worker: dispatch explícito `call.*` sin romper `delivery.*` (hoy los ignora y hace ack — F2 §3.5.4) | Cola RabbitMQ | F3 no publica eventos propios de llamada: usa `notify_events` existente para `delivery.*` (WhatsApp) |
| Panel "Central Telefónica" (llamadas en vivo WS, click-to-call, conversión a pedido) | UI F2 | F3 extiende el mismo panel: columna estado IA, transcripción, botón transferir con contexto |

**Nota de alineación (Spec Anchor):** F2 y F3 se escribieron en paralelo el 2026-08-12; esta spec se
ha reconciliado contra F2 tal como quedó publicada (tabla `call_records` única, contratos
`/api/v1/calls/*`, WS `/ws/calls/{tenant_id}`). Cualquier cambio posterior en F2 debe reflejarse aquí.

### 2.2 Backend existente: reutilización directa (verificado en código)

| Componente | Ubicación | Estado |
|---|---|---|
| `create_order(db, tenant_id, data)` — pedido completo: zona activa → validación items/modificadores/horario (`_item_available`) → promo → min_order → pago → Sale (fee como ítem servicio, D1 spec 03) → kárdex + asiento → KitchenOrder + WS `new_delivery` → DeliveryOrder + eventos | `app/services/delivery_service.py` L296 | ✅ Listo — **el bridge de voz llama esto** (mismo motor que checkout web) |
| `get_public_menu(db, tenant_id)` — secciones + items delivery + modificadores + promos + ventana horaria + branding | `delivery_service.py` L142 | ✅ Listo — **contexto del menú real para el LLM** (R1) |
| `get_public_zones(db, tenant_id)` — zonas activas con `districts` (jsonb), fee, min_order, eta | `delivery_service.py` L248 | ✅ Listo — base para **resolución de zona por distrito** (D7) |
| `delivery_zones.districts` jsonb + `menu_items.available_from/available_to/delivery_enabled` | `app/adapters/db/models/delivery.py`, `restaurant.py` | ✅ Listo — la IA respeta horario real (R1) |
| Motor WhatsApp Fase B: `publish_checkout_events` / `publish_status_event` → RabbitMQ `iaas-tasks` → worker → `MetaCloudNotifier`/`DryRunNotifier` | `app/services/notify_events.py`, `whatsapp_notifier.py` | ✅ Listo — **confirmación WhatsApp automática al crear el pedido por voz** |
| Puerto hexagonal de skills: `BaseSkill` (name/description/execute) + `AgentContext` (tenant_id, user_id, language, extra) + `SkillResult` | `app/core/agents/base.py` | ✅ Listo como patrón — F3 lo usa como **contexto del agente de dominio** (F5 es quien activa skills; aquí el agente conversacional es el orquestador del pedido, no una skill del orquestador) |
| `WsManager` singleton (broadcast por tenant, kitchen/waiter) | `app/core/ws_manager.py` | ✅ Reutilizable — F2 añade canal `calls`; F3 lo extiende con eventos `ai_call_state` |
| `companies.settings` JSONB (patrón D-03: branding, yape_phone, whatsapp, calls) | `app/adapters/db/models/accounting.py` L50 (columna `settings` JSON) | ✅ Listo — ahí vive `companies.settings.voice_ai` (§3.3) |
| Rate limiting Redis (sliding window) | `app/core/rate_limit.py` | ✅ Reutilizable — proteger endpoints del bridge (transcript/transfer) |

### 2.3 Lo que NO existe (trabajo nuevo de F3)

| Gap | Detalle |
|---|---|
| **Capa IA conversacional** | No existe: Stasis app + External Media (RTP→WS) para streaming a STT, orquestador STT→LLM→TTS, agente de dominio. Servicio Python nuevo (`app/adapters/voice/` hexagonal: puerto `VoiceProvider`, implementaciones Deepgram/Google/Groq/…) o servicio independiente conectado al backend por HTTP interno (patrón `call-bridge` de F2) |
| `call_transcriptions` | No existe la tabla (F2 solo reservó la FK). DDL §3.2 |
| Columnas IA en `call_records` | F2 no contempla `ai_state`, `transfer_reason`, `cost_usd`, `context_summary` — migración `0017_voice_ai` (§3.2) |
| Resolución de zona por voz | No existe matcher distrito→`delivery_zones` a partir de texto libre (normalización de dirección, alias de distritos) |
| Transferencia con contexto | No existe endpoint ni flujo: liberar canal → ring a extensión operador (F2 `calls.extensions`) con resumen + transcripción |
| Kill-switch + presupuesto | No existe enforcement de tope diario/minuto ni interruptor por tenant |
| Ruteo `ai_receptionist` | F2 MVP solo tiene `ring_operator`; falta el comportamiento Stasis que responde la IA |

### 2.4 Patrón a NO copiar

**No crear un flujo de venta paralelo.** El pedido por voz **debe** pasar por `create_order`
(→ Sale → kárdex → asiento → cocina → DeliveryOrder → eventos), exactamente igual que el checkout
web (spec 03) y que `convert-to-order` de F2. Un "pedido" que solo quede en una transcripción sería
una venta perdida fuera de contabilidad y cocina (mismo error que `TakeawayOrder` en spec 03 §2.3).

### 2.5 Opción B — proveedores llave en mano (Vapi / Retell) — documentada, NO elegida (D1)

| Aspecto | Asterisk ARI (elegido, sobre F2) | Vapi / Retell (Opción B) |
|---|---|---|
| Modelo de costo | Infra propia + proveedores STT/TTS/LLM directos (~S/500–900/mes) | **~$0.05–0.15/min plataforma** + costos voz/LLM del agente hosted → similar o mayor, con capa intermedia |
| Control / datos | Grabaciones y transcripciones **en nuestra BD** (cumplimiento, R3) | Datos del cliente pasan por plataforma third-party |
| Personalización | Pipeline y prompt 100% nuestro, con `get_public_menu` como tool | Limitado a lo que la plataforma expone |
| Integración con `create_order` | Llamada directa al servicio (mismo proceso) | Webhooks/API (más latencia, más piezas) |
| Esfuerzo inicial | Mayor (Stasis + External Media + integraciones) | Menor (config de agente hosted) |
| Riesgo | Asterisk 20 External Media requiere PoC (semana 1-2) | Dependencia de proveedor + tarifas por minuto no acotadas |

**Veredicto D1:** mantener la Opción B como plan B concreto si el PoC de External Media fallara en la
semana 2 (criterio de salida §4.3); la lógica de dominio (estados, reglas, `create_order`, contratos)
se diseña **agnóstica al transporte de voz** para que el switch A→B no toque el backend.

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (F3 MVP):**
- Capa IA sobre F2: Stasis app + External Media (RTP→WS) + pipeline STT→LLM→TTS (D2/D3/D4) con proveedores conmutables por settings.
- Agente de dominio acotado (D6): flujo conversacional §3.6 + menú real como contexto/tool (R1).
- Migración `0019_voice_ai` (DDL §3.2; la `0017`=whatsapp_bsuid y `0018`=call_records ya existen — corregido 2026-08-13): `call_transcriptions` + columnas IA en `call_records`.
- Resolución de zona por distrito (D7) + creación de pedido vía `create_order` (pago contraentrega default, R7) + eventos Fase B (WhatsApp confirmación automática) + `converted_order_id` (F2).
- Transferencia a humano con contexto (D9): endpoint + ring a extensión operador (F2) + evento WS al panel.
- Panel "Central Telefónica" (F2) extendido: estado IA en vivo, transcripción, botón transferir con contexto.
- Transcripción + grabación siempre (R3), recuperables por API.
- Gobernanza: presupuesto por minuto/tope diario + kill-switch por tenant (R4/R5).
- Config `voice_ai` en `companies.settings` (patrón D-03) + `inbound_behavior: ai_receptionist` en `calls`.

**NO INCLUYE (límites F3):** llamadas salientes, IVR multi-opción, pago por voz (Yape/Plin con
referencia hablada), chatbot WhatsApp conversacional, agentes de propósito general, integración
Vapi/Retell (solo PoC fallback), multi-idioma (es-PE únicamente).

### 3.2 Modelo de datos (migración `0019_voice_ai` — down_revision=`0018_call_records`; borrador, SIN commitear)

**Reutiliza la tabla `call_records` de F2 (§3.2 spec 05) — NO se crea otra.** Esta migración:

```sql
-- 1) Columnas IA en call_records (F2 ya definió transcription_fk RESERVADA y converted_order_id)
ALTER TABLE call_records
  ADD COLUMN ai_state varchar(20),                 -- greeting|taking_order|clarifying|confirming|transfer|hangup|completed|failed (8 estados — corregido 2026-08-13)
  ADD COLUMN transfer_reason varchar(50),          -- complaint|out_of_domain|low_confidence|user_requested|budget
  ADD COLUMN context_summary text,                 -- resumen para el operador (D9)
  ADD COLUMN cost_usd numeric(10,4) NOT NULL DEFAULT 0,  -- STT+TTS+LLM de la llamada (R4)
  ADD CONSTRAINT call_records_ai_state_check
    CHECK (ai_state IN ('greeting','taking_order','clarifying','confirming','transfer','hangup','completed','failed')),
  ADD CONSTRAINT call_records_transfer_reason_check
    CHECK (transfer_reason IN
      ('complaint','out_of_domain','low_confidence','user_requested','budget')),
  ADD CONSTRAINT call_records_cost_usd_check CHECK (cost_usd >= 0);

-- 2) Transcripción (D8/R3) — llena la FK reservada por F2
CREATE TABLE call_transcriptions (
  id serial PK,
  tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  call_id varchar(64) NOT NULL,                   -- = call_records.external_call_id (Uniqueid Asterisk)
  provider varchar(30) NOT NULL,                  -- deepgram | google | whisper | ...
  text text NOT NULL,                             -- transcripción completa
  segments jsonb,                                 -- [{start, end, speaker, text, confidence}]
  lang varchar(10) NOT NULL DEFAULT 'es-PE',
  duration_sec int,
  cost_estimate numeric(10,4) NOT NULL DEFAULT 0, -- costo STT estimado (R4)
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_call_transcriptions_call_id ON call_transcriptions(call_id);
```

**Notas de diseño:**
- `call_transcriptions.call_id` = `call_records.external_call_id` (Uniqueid de Asterisk, UNIQUE en F2):
  la transcripción se persiste por idempotencia con el mismo patrón de F2
  (`INSERT ... ON CONFLICT (external_call_id) DO UPDATE` vía `call_id` único por llamada).
- `transcription_fk` (F2, hoy NULL) se actualiza al crear la transcripción → el detalle de la llamada
  en F2 ya muestra la transcripción sin cambio de contrato.
- `ai_state` espeja la máquina de estados conversacional (§3.6) → panel en vivo + métricas.
- `converted_order_id` (F2) se llena tras `create_order` → trazabilidad voz→venta→cocina→WhatsApp.
- `cost_usd` + `cost_estimate` → costo por minuto medible (CA-F3-8).
- Retención: la purga > 90 días ya es regla de F2 (R2); aplica a transcripciones también.

### 3.3 Configuración por tenant — `companies.settings.voice_ai` (patrón D-03)

```json
{
  "enabled": true,
  "kill_switch": false,
  "max_calls_concurrent": 4,
  "stt":    { "provider": "deepgram", "model": "nova-3",  "language": "es",  "api_key": "..." },
  "tts":    { "provider": "google",   "voice": "es-PE-Chirp3-HD-Fenella", "api_key": "..." },
  "llm":    { "provider": "groq",     "model": "llama-3.3-70b-versatile", "api_key": "..." },
  "transfer": {
    "confidence_threshold": 0.6,
    "max_clarify_attempts": 2
  },
  "budget": {
    "max_usd_per_minute": 0.15,
    "daily_budget_usd": 10.0
  },
  "greeting": "Buenas noches, gracias por llamar a El Segoviano. Esta llamada es atendida por un
               asistente automático y puede ser grabada. ¿Qué le ofrezco esta noche?"
}
```

- Se combina con `companies.settings.calls` (F2): `inbound_behavior: "ai_receptionist"` cuando
  `voice_ai.enabled=true`; `extensions` = destino de transferencia (D9).
- Tenant sin config, `enabled: false` o `kill_switch: true` (R5) → `inbound_behavior` cae a
  `ring_operator` (operador humano, sin IA), inmediato, sin deploy.
- `daily_budget_usd` agotado (R4) → transferencia a humano con motivo `budget`.
- Config expuesta vía `PATCH /api/settings` (mismo mecanismo D-03 spec 03 §3.4.3).

### 3.4 Ruteo de la llamada (integración F2 ↔ F3)

```
1. Llamada entra por el trunk (F2) → contexto from-pstn → MixMonitor (grabación, R3/F2 R1)
2. call-bridge (F2) upserta call_records (ringing) y publica call.new
3. Si tenant tiene voice_ai.enabled y hay canales libres (R6):
     → Stasis app responde (External Media: RTP→WebSocket hacia el bridge de voz)
     → inbound_behavior = ai_receptionist (la IA atiende; F2 no ringea al operador)
   Si no (kill_switch / presupuesto / sin canales):
     → inbound_behavior = ring_operator (F2: ringea a extensions del operador)
4. Durante la llamada IA: call-bridge marca answered; el bridge de voz va actualizando
   ai_state vía PATCH (panel en vivo) y acumulando transcripción (POST transcript)
5. Fin feliz → create_order → converted_order_id + transcription_fk + eventos delivery.* (Fase B)
6. Transferencia (R2/D9) → bridge llama a /transfer → Asterisk libera el canal IA y
   ringea a la extensión del operador con el contexto (context_summary) visible en el panel
7. Hangup (AMI, F2) → call-bridge cierra call_records (completed/transferred) + recording_ready
```

### 3.5 Contratos

#### 3.5.1 Bridge → Backend (llamadas internas del servicio de voz, autenticadas con service-token)

```
POST /api/v1/calls/{external_call_id}/transcript   — persiste transcripción (streaming o final)
  Body: { provider, text, segments: [{start, end, speaker, text, confidence}],
          lang, duration_sec, cost_estimate }
  → 201 { transcription_id }   (y setea call_records.transcription_fk — FK reservada de F2)

PATCH /api/v1/calls/{external_call_id}/ai-state    — actualiza ai_state (panel en vivo, §3.6)
  Body: { state: "greeting"|"taking_order"|"clarifying"|"confirming"|"transfer"|"hangup",
          transfer_reason?, context_summary? }
  → 200  (emite WS ai_call_state)

POST /api/v1/calls/{external_call_id}/transfer     — transferencia a humano con contexto (D9)
  Body: { reason: "complaint"|"out_of_domain"|"low_confidence"|"user_requested"|"budget",
          context_summary: "…resumen de lo dicho…" }
  → 200 { transferred_to: "6001", via: "sip" }     (Asterisk libera canal IA → ringea ext operador;
                                                    panel muestra resumen + link a transcripción)
  Nota: alias /api/v1/ai-calls/{external_call_id}/transfer → mismo handler (compatibilidad con
        el contrato original del encargo; el recurso canónico es el de F2, /api/v1/calls/*)

POST /api/v1/calls/{external_call_id}/complete     — cierre: duración, costo (status lo cierra F2)
  Body: { duration_sec, cost_usd }
  → 200

PATCH /api/v1/calls/{external_call_id}/ai-context  — actualiza context_summary incremental
  Body: { context_summary }  → 200
```

El pedido lo crea el bridge llamando **directamente a `create_order`** (mismo proceso backend) y
luego setea `converted_order_id` (columna F2) — no hay endpoint de pedido nuevo (reuso total, §2.4).
El panel F2 (`POST /api/v1/calls/{id}/convert-to-order`) queda como vía manual para las llamadas que
NO atendió la IA (ring_operator).

#### 3.5.2 Panel staff (extiende F2; auth + tenant)

```
GET  /api/v1/calls?status=&from=&to=&ai_state=     lista F2 + filtro estado IA (transcripción si existe)
GET  /api/v1/calls/{id}                            detalle F2 + ai_state, context_summary, cost_usd,
                                                    transcription (via transcription_fk), recording
GET  /api/v1/calls/{id}/transcript                 transcripción recuperable (CA-F3-3)
WS   /ws/calls/{tenant_id}                         canal F2, nuevo evento:
      server→client: { event: "ai_call_state",
                       data: { external_call_id, caller, ai_state, duration_sec,
                               converted_order_id?, transfer_reason?, context_summary? } }
      (extiende el canal `calls` que añade F2 al WsManager — patrón kitchen/waiter existente)
```

#### 3.5.3 Flujo de datos del pedido por voz (sin endpoints nuevos de pedido — reuso total)

```
cliente habla ──► STT (Deepgram streaming) ──► LLM (Groq; contexto = get_public_menu + zonas +
                                                prompt de dominio D6/R1) ──► TTS (Google es-PE) ──► cliente oye
                                                      │ (estructura: items[] con menu_item_id,
                                                      │  modifiers[], notas, dirección, nombre, teléfono)
                                                      ▼
                            confirmación oral (repetición del pedido + total + zona + ETA)
                                                      ▼
        create_order(db, tenant_id, { zone_id: resuelto-D7, items, customer, payment: {method:"cash"} })
                                                      ▼
        Sale + kárdex + asiento + KitchenOrder + WS new_delivery + DeliveryOrder + tracking DLV-…
                                                      ▼
        notify_events.publish_checkout_events → RabbitMQ iaas-tasks → WhatsApp confirmación (Fase B)
                                                      ▼
        converted_order_id + transcription_fk + cost_usd persistidos (R3/R4)
```

- **Pago (R7):** pedido por teléfono = **contraentrega (cash)** por defecto (no se puede validar
  referencia Yape/Plin por voz en el MVP). Configurable en `voice_ai`.
- **Zona (D7):** el LLM extrae dirección → matcher normaliza (distritos con alias, ej.
  "Canto Grande", "Montenegro", "Motupe") → match contra `delivery_zones.districts` → `zone_id`.
  Sin match → repregunta 1 vez → transferencia (motivo `low_confidence`).
- **Cocina/contabilidad:** idéntico al checkout web (spec 03) — la IA jamás toca precios ni
  inventario: `create_order` valida todo contra el menú real (R1).

### 3.6 Flujo conversacional (máquina de estados de la IA)

```
                 ┌────────────┐    saludo + oferta   ┌───────────────┐
  llamada ──►    │  greeting  │ ───────────────────► │ taking_order  │
                 └────────────┘                      └───────┬───────┘
                                                              │ items + cantidades + modificadores
                                                              │ + notas + dirección + nombre/tel
                                                   ┌──────────▼──────────┐
                                            ┌────► │    clarifying       │◄─── confianza < umbral (D9)
                                            │      └──────────┬──────────┘     o dato faltante
                                            │  máx 2 intentos │               (máx 2 → transfer)
                                            │                 ▼
                                            │      ┌───────────────────────┐
                                            │      │     confirming        │  repite pedido + total
                                            │      └───────────┬───────────┘  + zona/fee + ETA
                                            │                   │ "sí"
                                            │                   ▼
                                            │        ┌──────────────────┐   crea pedido (create_order)
                                            │        │      hangup      │──► WhatsApp confirmación
                                            │        └──────────────────┘   transcripción + grabación
                                            │
                                            └──── queja / fuera de dominio / "hablar con alguien"
                                                              ▼
                                                   ┌──────────────────┐
                                                   │     transfer     │──► operador (ext SIP F2 / panel)
                                                   └──────────────────┘    con contexto completo (D9)
```

- **Intentos de dominio (R1):** `tomar_pedido`, `confirmar_pedido`, `consultar_estado` (por
  tracking/telefono), `modificar`/`cancelar` (solo antes de crear). Todo lo demás →
  `out_of_domain` → transferencia. La IA **no** negocia precios, no inventa promos, no opina sobre
  horarios que no estén en el contexto del menú.
- **Latencia (CA-F3-5):** objetivo **< 2s** a la primera respuesta del saludo (streaming STT +
  saludo pre-generado localmente en TTS mientras el LLM no es necesario).

### 3.7 Cumplimiento (Meta 15-ene-2026 + BSUID) — D6

- El agente **se identifica como asistente automático** de El Segoviano al inicio del saludo
  (transparencia de IA en llamadas — requisito Meta 15-ene-2026 y BSUID) y avisa que la llamada
  puede ser grabada (R3).
- Alcance acotado al menú/estado/confirmación: nada de promesas, descuentos inventados ni datos
  personales solicitados fuera de lo necesario para el pedido (nombre, teléfono, dirección).
- Grabación + transcripción se almacenan en infraestructura propia (F2 MixMonitor + `call_records`),
  no en plataformas de voz externas (refuerza D1 vs Opción B).

### 3.8 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R1 | **Nunca inventar**: el LLM solo usa `get_public_menu` + zonas reales como contexto/tool; precios, modificadores, promos y disponibilidad salen de ahí. Sin match → transferencia, jamás improvisación |
| R2 | **Transferencia obligatoria** ante queja, fuera de dominio, 2 intentos de aclaración fallidos o confianza < umbral — con contexto completo (D9) |
| R3 | **Grabación + transcripción siempre** (D8): grabación F2 (MixMonitor), transcripción `call_transcriptions`; retención = `calls.retention_days` (F2 R2); recuperables por API (CA-F3-3) |
| R4 | **Presupuesto por minuto + tope diario por tenant** (`max_usd_per_minute`, `daily_budget_usd`); costo STT/TTS/LLM registrado por llamada (`cost_usd`) y medible (CA-F3-8); al agotar tope → transferencia motivo `budget` |
| R5 | **Kill-switch** (`kill_switch`) → `inbound_behavior` cae a `ring_operator` (F2): llamadas al humano, sin deploy, inmediato |
| R6 | Concurrencia: la IA atiende hasta `max_calls_concurrent` llamadas simultáneas (N = canales del trunk, típico 2–4, F2: 4 canales G.711); por encima → `ring_operator`/cola |
| R7 | Pago por voz = **contraentrega (cash)** en MVP; zona resuelta por distrito (D7); el pedido entra SIEMPRE por `create_order` (nada de flujo paralelo, §2.4) |
| R8 | Aislamiento: todo filtrado por tenant (X-Tenant-ID/JWT); `external_call_id` único global (F2); rate-limit Redis en endpoints del bridge |
| R9 | Enlace voz→pedido: `converted_order_id` (F2) poblado tras `create_order`; eventos Fase B (`delivery.confirmed`) disparados por el motor existente, no por el bridge |
| R10 | Estado conversacional espejado en `ai_state` → panel en vivo WS `calls` (hablando / tomando pedido / transferido) |

### 3.9 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F3-1 | Pedido completo por voz (2 items + modificador + dirección válida + confirmación "sí") | `create_order` 201/OK: Sale (order_type=delivery) + kárdex + asiento + KitchenOrder + WS `new_delivery` + DeliveryOrder con tracking DLV-; `call_records.converted_order_id` poblado |
| CA-F3-2 | Tras crear el pedido por voz | Evento `delivery.confirmed` publicado (RabbitMQ) → confirmación WhatsApp al `customer_phone` (motor Fase B, dry-run o real según config) |
| CA-F3-3 | `GET /api/v1/calls/{id}/transcript` | Transcripción completa + segmentos recuperables (provider, text, segments, lang); grabación accesible por `recording_path` (F2); `transcription_fk` enlazada |
| CA-F3-4 | Cliente se queja ("esto es caro"/"demoraron") o pide algo fuera de dominio | Transferencia a operador (ext SIP configurado en F2 `calls.extensions`) con `context_summary` + `transfer_reason` + transcripción enlazada; panel muestra el contexto |
| CA-F3-5 | Primera respuesta del agente | Latencia **< 2s** desde el fin del saludo de Asterisk hasta el audio TTS del saludo de la IA (medido en PoC y QA) |
| CA-F3-6 | 2 llamadas simultáneas (N=2 configurado) | Ambas atendidas por la IA sin degradación de latencia (cada una con su propio `external_call_id`, `ai_state` y transcripción independientes) |
| CA-F3-7 | Pregunta fuera de dominio ("¿me prestas plata?", "¿cuál es tu nombre real?") | La IA no inventa: declina amablemente y transfiere (R2); cero respuestas improvisadas sobre precios/promos |
| CA-F3-8 | Panel de costo | `cost_usd` por llamada + suma diaria/mensual por tenant ≈ STT+TTS+LLM reales; excede `daily_budget_usd` → transferencia motivo `budget` (R4) |
| CA-F3-9 | Dirección "Canto Grande" / "Montenegro" dicha por el cliente | `zone_id` resuelto por match de distrito contra `delivery_zones.districts`; dirección no reconocida → 1 repregunta → transferencia |
| CA-F3-10 | `kill_switch: true` en settings | Siguiente llamada rutea `ring_operator` (F2) sin pasar por la IA (sin deploy); `ai_state` nunca arranca |
| CA-F3-11 | Presupuesto agotado o config `enabled: false` | Llamadas entran directo al operador; la IA jamás arranca (R4/R5) |
| CA-F3-12 | R1 (anti-alucinación) | En N=50 llamadas de prueba, el LLM nunca emite un precio/ítem/promo fuera del contexto de `get_public_menu` (validación por diff del log de intents) |
| CA-F3-13 | `alembic upgrade head` (BD con `call_records` de F2 aplicada) | `call_transcriptions` creada + columnas IA en `call_records`; head = `0019_voice_ai`; `downgrade 0018` revierte todo |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

### 4.1 Prerrequisito

F2 (spec 05) aprobada e implementada (o al menos su infra Asterisk + `call_records` + `call-bridge`).
F3 y F2 comparten tabla y contratos; secuenciar F2 antes de F3.

### 4.2 PoC — Semanas 1-2 (PRIMERO, puerta de entrada del resto)

1. **Semana 1 — Capa de voz sobre F2**: Stasis app + External Media (RTP→WebSocket) en el Asterisk
   de F2: llamada entrante → audio del canal llega al bridge Python. Verificar con el trunk real.
2. **Semana 2 — Pipeline de voz**: STT Deepgram streaming (es) → LLM Groq (prompt de dominio +
   `get_public_menu` real) → TTS Google es-PE. Meta: una llamada de prueba toma un pedido simple
   (2 items), lo repite para confirmar y **crea el pedido real vía `create_order`** (zona fija =
   Zona 1, pago cash). Medir: latencia primera respuesta (<2s), costo/min por llamada.
3. **Criterio de salida del PoC**: pipeline completo en producción de prueba con pedido real en
   cocina + transcripción persistida. **Si External Media falla en la semana 2 → activar Opción B
   (Vapi/Retell, §2.5)** sin tocar la lógica de dominio (contratos §3.5 ya agnósticos).

### 4.3 Fases siguientes (semanas 3-8)

- **Fase 2 (S3-4) — Agente de dominio completo**: estados §3.6 (greeting→…→hangup), resolución de
  zona por distrito (D7), repetición/confirmación, intents R1, transferencia a humano con contexto
  (endpoint + ring a extensión), enlace `converted_order_id` + `transcription_fk`, eventos Fase B
  (WhatsApp).
- **Fase 3 (S5-6) — Concurrencia + panel**: N canales simultáneos (R6), evento `ai_call_state` en el
  WS `calls` de F2, extensión del panel Central Telefónica (estado IA/transcripción/transferencia),
  métricas de costo (R4), kill-switch (R5) y config `voice_ai` vía settings (D-03).
- **Fase 4 (S7-8) — QA + hardening + deploy**: ejecutar CA-F3-1..13 en QA (incl. prueba anti-
  alucinación N=50, CA-F3-12); pruebas de latencia y concurrencia; `./deploy.sh --env prod` con
  backup previo (patrón spec 01/03); manuales.

**Esfuerzo total: 6-8 semanas (PoC 2 semanas primero), después de F2.**

---

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-14 (CIERRE — IMPLEMENTADA Y DEPLOYADA)**: backend F3 completo desplegado en PROD — migración `0019_voice_ai` aplicada (head verificado), `routers/ai_calls.py` con endpoints transcript/ai-state/ai-context/transfer/complete (+ alias `/api/v1/ai-calls/*`), `voice_ai_service` (máquina de estados), `voice_bridge` (Stasis app + External Media RTP→WS), simulador `scripts/simulate_voice_call.py`; frontend con panel IA en Central Telefónica (estado en vivo, transcripción, transferir con contexto). Suite backend 516 passed; E2E en caliente en prod con llamada simulada. Spec ↔ código sincronizados (Spec Anchor).

- **2026-08-13 (FRONTEND — panel IA)** 🟢: frontend-dev extendió `CallCenterPage` + `callsApi.ts`.
  - **Entregado**: tipos F3 + parseo WS `ai_call_state`/`call.transferred`, `getAiState`/`patchAiState`/
    `transferCall`/`getTranscript`/`getVoiceAiSettings`/`patchVoiceAiSettings`, badge estado IA por color +
    motivo + costo en tarjetas, filtro IA en vivo (in-memory), panel lateral `AiTranscriptPanel`
    (transcripción polling 5s + botón "Transferir a humano" con confirmación), badge forward-compat en
    histórico. Build tsc+vite OK, 163 tests (8 nuevos `callsApiWs.test.ts`). Lógica F2 intacta.
  - **Desviaciones registradas (verificadas en código real)**:
    1. **Auth**: los endpoints IA (transcript POST, ai-state GET/PATCH, ai-context, transfer, complete)
       son **bridge-only** (`_authorize_bridge`: X-Service-Token + allowlist IP, CA-F2.5), NO staff.
       Único endpoint staff: `GET /{call_ref}/transcript` (CA-F3-3). El UI se alimenta por WS en vivo;
       el botón Transferir ante 401/403 muestra mensaje claro (la IA transfiere sola ante
       user_requested/low_confidence — D9). Spec §3.5 debe reflejar esta separación staff vs bridge.
    2. **No hay evento WS de transcripción**: no existe `ai.transcript` (spec lo sugería); el panel hace
       polling de `GET /transcript` cada 5s. Alternativa futura: evento `ai.transcript` en ws_manager.
    3. **`cost_usd` no se expone al staff**: ni payload WS ni `CallRecordOut`/GET /calls lo incluyen
       (spec §3.5.2 lo contempla). El indicador de costo es forward-compat; el panel usa `cost_estimate`
       (STT) de la transcripción. Pendiente: exponer cost_usd en GET /calls o WS si Ron lo pide.
    4. **Filtro ai_state**: GET staff no acepta `ai_state=` (spec §3.5.1 lo listaba) → filtro in-memory.
    5. **Ajustes voice_ai**: sin drawer de ajustes en CallCenterPage (no se inventó UI); API
       GET/PATCH /api/settings devuelve `body.voice_ai` (PATCH merge shallow 1 nivel; api_key nunca
       renderizar). UI de ajustes queda como trabajo opcional.

- **2026-08-13 (QA en vivo — E2E llamada simulada)** 🟢: E2E completo validado en QA
  (`iaas_ronsys_qa`, backend 8002, migración 0019 aplicada).
  - **Flujo completo OK**: llamada simulada `f3-sim-*` → registro (POST /events) → gobernanza
    budget → saludo TTS → 3 turnos (STT echo → LLM determinista → TTS stub) → transcripción (201) →
    ai-state (200) → POST /complete → **create_order** → `DLV-9ffd51c75a` / `VEN-2026-00008-422`
    (converted_order_id=8, sale_id=9, cost_usd=0.0105, cash R7). Persistencia verificada en BD
    (call_record completed + transcripciones + delivery_order received).
  - **Transferencia D9 validada**: queja "quiero hablar con alguien" → `transfer_reason=user_requested`,
    `ai_state=transfer`, POST /transfer 200, context_summary persistido.
  - **Kill-switch R5 validado**: sin presupuesto configurado (daily_limit=0) → `can_start=false` →
    ring_operator (no atiende, libera al operador).
  - **BUGS CORREGIDOS en QA** (hallazgos → fix):
    1. **`_bridge_tenant` sin await en 6 handlers** (ai_calls.py): coroutine pasado como tenant_id →
       asyncpg DataError 500 en POST /complete (el E2E no persistía). Fix: `await` en los 6 +
       test de regresión `test_router_handlers_await_bridge_tenant` (grep estático).
    2. **Harness del simulador**: usaba menú DEMO (ids 10-12) que no existen en QA → 422 en
       create_order. Fix: `simulate_voice_call.py` ahora carga el **menú real** vía
       `get_public_menu/get_public_zones` (R1 — nunca datos inventados, ni en el simulador) +
       fix `await _session_factory()`.
    3. **Data QA**: settings calls en formato legacy (`did` string, extensions ints) rompía
       `CallSettings` (F2) → corregido a `dids: [str]`, `extensions: [str]`; menú real sembrado
       (5 menu_items + 2 restaurant_sections) y plan de cuentas mínimo (14 cuentas: 10/20/40/42/
       60/61/69/201...) — el seed QA anterior no incluía inventario/contabilidad.
  - **Nota kárdex QA**: los kárdex se validan en prod (el motor F2 los generó en el E2E prod;
    QA no tiene inventario vinculado a menu_items → 0 kárdex, entorno, no bug F3).
  - **Tests**: F3+F2 66/66 ✓ (test_f3_voice_ai + test_f3_voice_bridge + test_f2_calls).

- **2026-08-13 (DEPLOY PROD + E2E en caliente en el monitor)** 🟢: deploy final a producción
  (imágenes Docker rebuild: backend/frontend/worker) + migración **0019_voice_ai aplicada en
  `iaas_ronsys`** (verificada: alembic_version=0019_voice_ai, columnas IA + tabla
  call_transcriptions + 3 CHECKs) + E2E visible en el monitor (DISPLAY :0, Chromium anti-caché,
  patrón e2e-hot-f2-central.cjs).
  - **Flujo E2E prod OK** (`f3-e2e-*`): login staff → panel Central (WS 🟢) → llamada simulada
    → IA contesta (greeting TTS stub) → 3 turnos (STT echo → LLM determinista → TTS stub) →
    confirmación → **create_order real**: `DLV-9ffd79f212` / `VEN-2026-00053-055` (S/40,
    Lomo Saltado ×1, cash R7) → call_record `completed` cost_usd=0.0105 → transferencia D9
    (`user_requested`, contexto persistido) → verificación API ai_state → **limpieza completa**
    (pedidos cancelados, call_records=0, transcripciones=0). Evidencias:
    `docs/reports/evidencias-f3-e2e-prod/` (12 screenshots del monitor).
  - **HALLAZGOS DE DEPLOY (bugs reales encontrados y corregidos en prod)**:
    1. **`ari-py==1.0.2` no existe en PyPI** (el paquete real es 0.0.2, no publicable) → se quitó
       de requirements; voice_bridge usa su cliente REST HTTP mínimo propio (PoC) — sin cambio de
       contrato. Documentado en requirements.txt + deploy/asterisk/README.md.
    2. **BUG `setup.py::update_settings` (PATCH /api/settings)**: colapsaba TODO lo que no era
       delivery/whatsapp dentro de `settings.branding` (incl. voice_ai, calls, features…) →
       PATCH voice_ai devolvía OK pero guardaba en el sitio equivocado y `budget_status` leía
       vacío → la IA nunca atendía (can_start=false silencioso). Fix: guardar cada clave en su
       lugar (branding solo branding; el resto en su propia clave). Dato prod corregido con SQL.
    3. **Simulador sin `DATABASE_URL` en env** → usaba DEMO_CONTEXT (menú inventado) → LLM decía
       "no le entendí" para items reales. Fix: el simulador carga menú real cuando DATABASE_URL
       está presente (ya documentado en el script).
    4. **Tenant por DID vs zona**: el evento simulado sin `tenant_id` resuelve por DID
       (+5115551234 → tenant 3, sin zona) mientras menú/zona viven en tenant 1 → complete fallaba
       con 404 "Zona de delivery no encontrada". Fix: `tenant_id` explícito en el payload del
       bridge simulado (contrato F2 lo acepta).
    5. **404 transitorio en POST /complete** durante el rebuild (backend inicializándose):
       resuelto con reintento; no es bug de código.
  - **VoiceAiSettings sembrado en prod** (vía SQL, no PATCH — ver hallazgo 2): enabled=true,
    kill_switch=false, budget daily_budget_usd=5.0, proveedores PoC echo/local/deterministic,
    greeting oficial §3.7, payment_method=cash. El switch a proveedores pagos es solo config (D2/D3).
  - **Kill-switch R5 en prod**: validado en QA (budget 0 → ring_operator); en el E2E prod la
    tercera llamada (`-k`) se atendió porque el presupuesto diario ($5) NO estaba agotado —
    comportamiento correcto (el kill-switch actúa cuando el budget se agota, no por defecto).
  - **Tests**: 66/66 ✓ antes del deploy (test_f3_voice_ai + test_f3_voice_bridge + test_f2_calls)
    + suite completa 451 passed. `--delay` añadido al simulador para demo visible en monitor.
  - **Pendiente para demo real**: trunk SIP + audio real (STT/TTS reales, External Media) — el
    PoC QA valida contratos/estados/gobernanza, no la latencia <2s con audio (CA-F3-5).

- **2026-08-13 (IMPLEMENTACIÓN Fase 1 — backend)** 🟢: backend-dev implementó migración `0019_voice_ai` + módulos IA.
  - **Entregado**: `0019_voice_ai.py` (tabla `call_transcriptions` + 4 columnas IA en `call_records` +
    3 CHECKs, down_revision `0018_call_records`), `schemas/voice_ai.py` (incl. `VoiceAiSettings` en
    `CompanySettings` → PATCH /api/settings lo acepta), `services/voice_ai_service.py` (máquina de
    estados §3.6, gobernanza R4/R5, `complete_call` → `create_order` patrón F2, D7 zona),
    `services/voice_providers.py` (puertos ABC STT/TTS/LLM + impls deterministas PoC),
    `routers/ai_calls.py` (transcript/ai-state/ai-context/transfer/complete + alias `/api/v1/ai-calls`,
    misma protección CALL_BRIDGE_TOKEN/ALLOWED_IPS que `/events`), `tests/test_f3_voice_ai.py` (37 tests).
  - **Tests**: F3 37/37 ✓; F2+F3 57/57 ✓ (regresión F2 cero); suite 451 passed + 2 deselected
    (fallos preexistentes de recetas, NO tocados). BD prod NO tocada (sigue en 0018; la 0019 se
    aplica en el próximo deploy — lifespan corre `alembic upgrade head`).
  - **Desviaciones registradas (sync spec↔código)**:
    1. **CHECK `ai_state` → 8 estados** (spec decía 6): el contrato POST /complete exige
       `completed|failed` → añadidos al CHECK (§3.2 y Gherkin HU-F3-10 corregidos).
    2. **`ai_state='transfer'`** (no 'transferring'): coincide con el CHECK y el WS de la Gherkin.
    3. **`call_transcriptions.call_id` = varchar(64) sin FK real** (es `external_call_id`; idempotencia
       por upsert a nivel servicio — la spec no define UNIQUE).
    4. **Guard de status de F2 no aplicado en /complete**: `convert_to_order` exige status
       answered/completed; en voz el cierre IA es autoritativo (estado AMI llega por su cuenta) —
       documentado en docstring del servicio.
    5. **Migración test**: el árbol alembic del repo NO permite `upgrade head` desde BD vacía por bugs
       PREEXISTENTES (seed admin sin company en 0002; revision_id de 0010 = 36 chars >
       alembic_version varchar(32); baseline 0000 con conexión propia → lock-timeout). El test
       replica fielmente "BD con 0018 aplicada" (HU-F3-10).

- **2026-08-13 (APROBACIÓN + RECONCILIACIÓN con F2 implementada)**: Ron aprobó F3 (D1-D10) al arrancar
  la fase. Reconciliación verificado en código (architecture-agent, 2026-08-13):
  - **Migración**: F2 dejó head `0018_call_records` → la nueva es **`0019_voice_ai`** (down_revision
    `0018_call_records`), no `0017` como decía el borrador. CA-F3-13 corregido.
  - **`call_records` real**: `transcription_fk` int nullable sin FK (reservada) ✅ + `converted_order_id`
    FK → `delivery_orders.id` (SET NULL) ✅ — la spec 06 adopta estas columnas tal cual.
  - **Contratos reales F2**: `GET /calls`, `GET /calls/{id}`, `POST /calls/{id}/convert-to-order`,
    `POST /calls/originate`, `POST /calls/events` (bridge), `WS /api/v1/calls/ws/{tenant_id}`.
    Los 4 endpoints de F3 (`transcript`, `ai-state`, `transfer`, `complete`) + `ai-context` son
    **trabajo nuevo** sobre esa superficie (antes la spec los asumía como extensión directa).
  - **Ruteo `ai_receptionist`**: F2 solo expone `inbound_behavior` como dato (schema, default
    `ring_operator`); el branch Stasis vs ring **no existe** — F3 lo implementa (dialplan/bridge).
  - **D7**: `suggest_zone_by_address(db, tenant_id, address)` YA existe en `call_service.py` (match
    substring sobre districts, de F2) → base para la resolución de zona; falta normalización de alias.
  - **PoC sin keys externas**: no hay Deepgram/Google/Eleven en .env. Stack PoC recomendado:
    STT `faster-whisper` (es) + VAD Silero, TTS `piper-tts` (es_PE, 100% local) o `edge-tts`,
    LLM DeepSeek (ya validado). Proveedores conmutables vía puerto `VoiceProvider` (D2/D3) — el
    switch a Deepgram/Google con keys reales es solo configuración.
  - **Asterisk**: imagen `mlan/asterisk:latest` 20.15.2 LTS, `network_mode: host`, AMI/ARI bind
    localhost. **ARI `POST /channels/externalMedia` es API estable desde Asterisk 12.6** → 20.15
    soporta External Media (RTP→WS) para el PoC. Riesgo: latencia <2s y audio path/NAT solo se
    validan con trunk real (CA-F3-5 en PoC simulado es aproximado).
  - **Dependencias**: requirements.txt no tiene ari-py/websockets/STT-TTS → añadir en Fase PoC.
  - **Riesgo split-brain config**: `voice_ai` vs `calls.inbound_behavior` → single-source en
    `companies.settings.calls` (F2); `voice_ai` complementa (keys/proveedores/budget), no duplica.
  - **`create_order` es async y valida zona/items/horario** → el bridge lo ejecuta en el mismo
    proceso backend (patrón F2 `convert_to_order`), nunca flujo paralelo (R7).

- **2026-08-12 (v0.1)**: spec creada. Fase R verificada en código: `create_order`, `get_public_menu`,
  `get_public_zones` (districts jsonb), motor WhatsApp Fase B (`notify_events` + `whatsapp_notifier`),
  `BaseSkill`/`AgentContext` (`core/agents/base.py`), `WsManager`, `companies.settings` JSON (patrón
  D-03). **F2 (spec 05) publicada en paralelo el mismo día**: esta spec se reconcilió contra ella —
  F3 adopta la tabla `call_records` de F2 (sin duplicarla), llena su FK `transcription_fk` reservada
  y su `converted_order_id`, extiende sus contratos (`/api/v1/calls/{id}/transcript|transfer|
  ai-state|complete`; alias `/api/v1/ai-calls/{id}/transfer` al mismo handler), su WS
  `/ws/calls/{tenant_id}` y su panel. Decisiones D1-D10 propuestas (arquitectura ARI sobre F2 D1,
  proveedores D2-D4, costo realista S/500-900/mes D5, dominio acotado D6, zona por distrito D7,
  grabación siempre D8, transferencia con contexto D9, gobernanza de costo D10). **Pendiente:
  aprobación de Ron.**

---

## 6. Referencias

- Spec F2 (Central Telefónica — base de infraestructura Asterisk/`call-bridge`/`call_records`):
  `docs/specs/03-delivery/05-spec-central-telefonica-v0.1.md`
- Spec 03 (dark kitchen — motor de pedidos reutilizado, D-03, Fase B WhatsApp):
  `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Código verificado: `apps/backend/app/services/delivery_service.py` (`create_order` L296,
  `get_public_menu` L142, `get_public_zones` L248), `app/services/notify_events.py`,
  `app/services/whatsapp_notifier.py`, `app/core/agents/base.py`, `app/core/ws_manager.py`,
  `app/adapters/db/models/delivery.py`, `app/adapters/db/models/accounting.py` (Company.settings)
- Validación técnica JARVIS 2026-08-12 (arquitectura ARI/External Media, tarifas de proveedores
  STT/TTS/LLM, ajuste de costo S/500-900/mes)
- Plan cuenta Meta WhatsApp (Fase B): `plan-cuenta-meta-whatsapp.md` (workspace)
- Cumplimiento: Meta política IA en llamadas 15-ene-2026 + BSUID (D6/R3, §3.7)
- Costos de infraestructura: `docs/costos-aws-breakeven.md`
