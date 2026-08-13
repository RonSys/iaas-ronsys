# Backlog Gherkin — F3: Recepcionista IA por Voz (Pedidos Telefónicos Automáticos)

**Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
**Origen:** Spec 06 — `docs/specs/03-delivery/06-spec-recepcionista-ia-v0.1.md` (APROBADA por Ron, 2026-08-12)
**Generado por:** PO Agent 📋
**Fecha:** 2026-08-13
**Estado:** ✅ Listo para desarrollo (F2 implementada y desplegada en prod — base infraestructura)
**Total Historias:** 10
**Alcance:** Capa IA conversacional sobre F2 (STT→LLM→TTS), agente de dominio acotado (D6), resolución de zona (D7), transferencia a humano con contexto (D9), gobernanza de costo (D10), grabación + transcripción (D8)

---

## 📌 Contexto

F3 construye **sobre F2 (Central Telefónica), ya IMPLEMENTADA y DEPLOYADA en prod**: tabla `call_records`
(migración 0018, con `transcription_fk` reservada y `converted_order_id`), `call-bridge` AMI/ARI,
panel Central Telefónica y WS `/ws/calls/{tenant_id}`. F3 añade la **capa de IA conversacional** que
atiende la llamada: la IA se identifica como asistente automático (transparencia Meta 15-ene-2026 +
BSUID, §3.7), toma el pedido **contra el menú real** (`get_public_menu`, R1), resuelve zona por
distrito (D7), confirma en voz, crea el pedido **vía `create_order`** (nunca flujo paralelo, R7/R9,
§2.4) y dispara la confirmación WhatsApp (motor Fase B).

Estas 10 historias cubren los **13 criterios de aceptación (CA-F3-1..13)** y las **10 reglas de
negocio (R1..R10)** de la spec, más los contratos §3.5 (`/transcript`, `/ai-state`, `/transfer`,
`/complete`, `/ai-context`), la máquina de estados §3.6 (`greeting → taking_order → clarifying →
confirming → hangup | transfer`) y la config por tenant §3.3 (`companies.settings.voice_ai`).

### 📋 Mapa de trazabilidad Spec → Historias

| Criterio / Regla | Historias |
|------------------|-----------|
| CA-F3-1 (pedido completo por voz → `create_order` + `converted_order_id`) | HU-F3-01 |
| CA-F3-2 (evento `delivery.confirmed` → WhatsApp) | HU-F3-01 |
| CA-F3-9 (zona por distrito: Canto Grande/Montenegro; no reconocida → repregunta → transfer) | HU-F3-02 |
| CA-F3-4 (queja / fuera de dominio → transferencia con contexto) | HU-F3-03 |
| CA-F3-7 + CA-F3-12 (anti-alucinación, N=50) | HU-F3-04 |
| CA-F3-10 (kill-switch) + CA-F3-11 (presupuesto agotado / disabled) | HU-F3-05 |
| CA-F3-3 (transcripción recuperable) + CA-F3-8 (panel de costo) | HU-F3-06 |
| CA-F3-6 (concurrencia N=2) | HU-F3-07 |
| CA-F3-5 (latencia primera respuesta < 2s) | HU-F3-08 |
| R8 (aislamiento de tenant) | HU-F3-09 |
| CA-F3-13 (migración `0019_voice_ai` + downgrade) | HU-F3-10 |

### 🔑 Supuestos de entrada (verificados)

- F2 deployada en prod: `call_records` (migración 0018), `call-bridge`, WS `/ws/calls/{tenant_id}`,
  panel Central Telefónica, `companies.settings.calls` con `inbound_behavior`.
- Backend listo para reuso directo: `create_order` (L296), `get_public_menu` (L142),
  `get_public_zones` con `districts` jsonb (L248), motor WhatsApp Fase B (`notify_events` +
  `whatsapp_notifier`), `WsManager`, patrón `BaseSkill`/`AgentContext`.
- Trabajo nuevo F3: capa de voz (Stasis + External Media), tabla `call_transcriptions`, columnas IA
  en `call_records`, matcher distrito→zona, transferencia con contexto, kill-switch + presupuesto,
  ruteo `ai_receptionist`.

---

## Historias

---

### HU-F3-01: Pedido completo por voz — toma, confirmación, creación y WhatsApp

**Como** cliente que llama a El Segoviano (dark kitchen, 19:00–24:00)
**Quiero** dictar mi pedido completo por voz (items + modificadores + dirección + confirmación "sí")
y que la IA lo cree automáticamente
**Para** hacer mi pedido sin esperar a un operador humano en horas pico y recibir confirmación por WhatsApp.

**Criterios de aceptación:**

- [ ] Given una llamada entrante a un DID con `voice_ai.enabled=true` y `inbound_behavior=ai_receptionist` When la IA atiende Then se identifica como "asistente automático de El Segoviano", avisa que la llamada puede ser grabada y saluda en español (estado `greeting`)
- [ ] Given el saludo When el cliente dice "quiero un ceviche mixto y una jalea, con su choclo extra" Then la IA pasa a `taking_order` y estructura `items: [{menu_item_id, qty}, ...]` con `modifiers: [{choclo extra}]` usando SOLO el menú real de `get_public_menu`
- [ ] Given los items capturados When el cliente dicta "av. Canto Grande 1234, San Juan de Lurigancho, mi nombre es Pedro y mi celular 999111222" Then la IA captura dirección, nombre y teléfono y resuelve `zone_id` por distrito
- [ ] Given el pedido completo When la IA repite el pedido con total, zona, fee de delivery y ETA estimada (estado `confirming`) y el cliente dice "sí" Then la IA responde despedida y cuelga (estado `hangup`)
- [ ] Given la confirmación "sí" When el bridge llama a `create_order(db, tenant_id, {zone_id, items, customer, payment:{method:"cash"}})` Then se crea Sale (order_type=delivery) + kárdex + asiento contable + KitchenOrder + WS `new_delivery` + DeliveryOrder con tracking `DLV-...` (CA-F3-1)
- [ ] Given el pedido creado When se persiste el cierre Then `call_records.converted_order_id` queda poblado y `ai_state=hangup`
- [ ] Given el pedido creado When el motor Fase B publica `delivery.confirmed` a RabbitMQ `iaas-tasks` Then llega confirmación WhatsApp al `customer_phone` (dry-run o real según config) con resumen del pedido y tracking (CA-F3-2)
- [ ] Given el cliente se equivoca al dictar un item When la IA detecta baja confianza o item inexistente Then pasa a `clarifying` (máx 2 intentos) y repregunta; si no resuelve → transferencia con motivo `low_confidence` (R2)
- [ ] Given el pedido confirmado y creado When el cliente intenta modificar/cancelar DESPUÉS del `create_order` Then la IA informa que el pedido ya está en cocina y ofrece transferir al operador (motivo `user_requested`) — jamás muta el pedido creado
- [ ] Given pago por voz When se crea el pedido Then `payment.method` es SIEMPRE `cash` (contraentrega, R7) — no se aceptan referencias Yape/Plin habladas

**Prioridad:** P0
**Esfuerzo estimado:** 5 días (Pipeline voz PoC 2d + agente dominio 2d + integración `create_order`/Fase B 1d)
**Dependencias:** F2 deployada (prerrequisito), HU-F3-02 (zona), HU-F3-10 (migración), spec 03 (motor pedidos/Fase B)
**Notas técnicas:**
- Reuso total §2.4: el bridge llama `create_order` directamente (mismo proceso), NO endpoint nuevo de pedido.
- `converted_order_id` y `transcription_fk` se llenan tras `create_order` (R9).
- Estados §3.6: `greeting → taking_order → clarifying → confirming → hangup`; cada transición hace
  `PATCH /api/v1/calls/{external_call_id}/ai-state` (panel en vivo).
- Greeting pre-generado en TTS local (no depende del LLM) para cumplir latencia < 2s (CA-F3-5).

---

### HU-F3-02: Resolución de zona de entrega por distrito (D7)

**Como** cliente que dicta su dirección por voz
**Quiero** que el sistema ubique automáticamente mi zona de entrega a partir del distrito que digo
**Para** que el pedido valide zona activa, fee y ETA correctos sin errores manuales del operador.

**Criterios de aceptación:**

- [ ] Given el menú tiene `delivery_zones` con `districts` jsonb (ej. Zona 1: ["Canto Grande","Montenegro","Motupe"]) When el cliente dice "estoy en Canto Grande" Then el matcher normaliza (mayúsculas/acentos/alias) y resuelve `zone_id` de la Zona 1 con confianza ≥ umbral
- [ ] Given el cliente dice "Montenegro" When el matcher busca en `delivery_zones.districts` Then resuelve el mismo `zone_id` (alias/abreviación aceptada)
- [ ] Given el cliente dice una dirección de un distrito NO listado (ej. "Villa El Salvador") When el matcher no encuentra match con confianza ≥ umbral (default 0.6) Then la IA repregunta 1 vez ("¿podría repetir su distrito?") en `clarifying`
- [ ] Given la repregunta When el cliente repite un distrito válido Then se resuelve `zone_id` y continúa el flujo normalmente
- [ ] Given la repregunta When el cliente vuelve a dar una dirección no reconocida (2 intentos fallidos) Then la IA transfiere al operador con `transfer_reason=low_confidence` y `context_summary` con la dirección dicha (CA-F3-9, R2)
- [ ] Given el distrito resuelto When `create_order` valida la zona Then usa `zone_id` resuelto, aplica `fee` y `min_order` de esa zona y rechaza el pedido si no alcanza el mínimo (mensaje claro al cliente antes de confirmar)
- [ ] Given el distrito coincide con una zona inactiva When el matcher encuentra match pero la zona está `active=false` Then la IA trata como no reconocido: repregunta 1 vez → transferencia `low_confidence` (jamás inventa zona)

**Prioridad:** P0
**Esfuerzo estimado:** 2 días (matcher distrito + alias + tests)
**Dependencias:** HU-F3-01 (flujo de pedido), `get_public_zones` existente
**Notas técnicas:**
- Matcher nuevo (gap F3): normalización de texto libre (unicode, mayúsculas, alias de distritos de SJL).
- Umbral configurable: `voice_ai.transfer.confidence_threshold` (default 0.6, §3.3).
- `max_clarify_attempts` (default 2) = 1 repregunta efectiva + 1 fallo → transfer (R2).
- El LLM extrae la dirección como texto libre; el MATCHER (código, no LLM) resuelve el distrito → zona (R1: la zona nunca la inventa el LLM).

---

### HU-F3-03: Transferencia a humano con contexto completo (D9)

**Como** cliente que necesita ayuda humana (queja, pedido especial o petición fuera del alcance de la IA)
**Quiero** ser transferido a un operador que ya conoce lo que dije
**Para** resolver mi caso sin repetir toda la información y sin que la IA improvise respuestas.

**Criterios de aceptación:**

- [ ] Given una llamada en curso When el cliente dice "esto es carísimo, quiero quejarme" Then la IA detecta intent `queja` y transfiere de inmediato con `transfer_reason=complaint` (R2, CA-F3-4)
- [ ] Given una llamada en curso When el cliente pide algo fuera de dominio (ej. "¿venden chicha?", "¿me prestas plata?", "¿cuál es tu nombre real?") Then la IA declina amablemente SIN inventar y transfiere con `transfer_reason=out_of_domain` (CA-F3-7)
- [ ] Given el cliente dice "quiero hablar con alguien" / "pásame con una persona" When la IA recibe la solicitud Then transfiere con `transfer_reason=user_requested`
- [ ] Given 2 intentos de aclaración fallidos o confianza < umbral When la IA no puede resolver el pedido Then transfiere con `transfer_reason=low_confidence`
- [ ] Given una transferencia When el bridge llama `POST /api/v1/calls/{external_call_id}/transfer {reason, context_summary}` Then Asterisk libera el canal IA y ringea a la extensión SIP del operador (F2 `calls.extensions`) y responde `{transferred_to: "6001", via: "sip"}` (CA-F3-4)
- [ ] Given la transferencia Then `context_summary` incluye: items capturados, dirección/zona, nombre/teléfono, estado `ai_state`, `transfer_reason` y link a la transcripción enlazada (R2/D9)
- [ ] Given la transferencia When el panel Central Telefónica recibe el evento WS `ai_call_state` Then muestra en vivo: `external_call_id`, caller, `ai_state=transfer`, `transfer_reason` y `context_summary` delante del operador (R10)
- [ ] Given una llamada transferida When finaliza la llamada con el operador Then `call_records` cierra con estado `transferred` y `recording_path` + transcripción completas (F2)
- [ ] Given el alias de compatibilidad When se llama `POST /api/v1/ai-calls/{external_call_id}/transfer` Then responde igual que el endpoint canónico `/api/v1/calls/.../transfer` (mismo handler)
- [ ] Given la transferencia con motivo `budget` o `complaint` When el operador atiende Then ve el motivo y el resumen antes de hablar (contexto visible en panel, no solo en audio)

**Prioridad:** P0
**Esfuerzo estimado:** 2 días (endpoint transfer + liberación de canal ARI + WS panel + resumen)
**Dependencias:** F2 (extensiones SIP, panel, WS), HU-F3-06 (transcripción enlazada)
**Notas técnicas:**
- Endpoint nuevo F3: `POST /api/v1/calls/{external_call_id}/transfer` (contrato §3.5.1).
- `transfer_reason` CHECK constraint: `complaint|out_of_domain|low_confidence|user_requested|budget` (§3.2).
- `context_summary` se actualiza incrementalmente con `PATCH /api/v1/calls/{id}/ai-context` durante la llamada.
- Alias `/api/v1/ai-calls/{id}/transfer` → mismo handler (compatibilidad con contrato original del encargo).

---

### HU-F3-04: Anti-alucinación — la IA solo habla del menú real (R1/CA-F3-12)

**Como** negocio (El Segoviano)
**Quiero** que la IA jamás invente precios, items, promos ni horarios fuera del menú real
**Para** proteger la operación (costo, inventario, cumplimiento Meta/BSUID) y la confianza del cliente.

**Criterios de aceptación:**

- [ ] Given la IA atiende una llamada When arma el contexto del LLM Then el prompt incluye SOLO el output real de `get_public_menu(db, tenant_id)` (secciones, items delivery, modificadores, promos, ventana horaria) y `get_public_zones` — nada hardcodeado
- [ ] Given el cliente pregunta por un item que NO está en el menú (ej. "¿tienen lomo saltado?") When el LLM no encuentra el item en el contexto Then responde que no lo tiene disponible y ofrece alternativas reales del menú o transfiere — NUNCA confirma el item
- [ ] Given el cliente pregunta "¿cuánto cuesta el ceviche mixto?" When el precio está en `get_public_menu` Then la IA responde el precio EXACTO del menú real
- [ ] Given el cliente pregunta por un precio de algo fuera del menú o por un descuento inventado When la IA no tiene el dato en contexto Then declina y transfiere (`out_of_domain`) — jamás improvisa un precio (CA-F3-7)
- [ ] Given el cliente pregunta "¿abren a las 3 de la tarde?" When la ventana horaria real (19:00–24:00) está en el menú Then la IA responde con el horario real
- [ ] Given el cliente pregunta por horarios/promos fuera del contexto cargado When la IA no tiene el dato Then declina y transfiere — no opina sobre horarios que no estén en el contexto (R1)
- [ ] Given una promo activa real en `get_public_menu` When el cliente pregunta por promos Then la IA la menciona tal cual aparece en el menú real (sin inventar condiciones)
- [ ] Given la prueba anti-alucinación (CA-F3-12) When se ejecutan N=50 llamadas de prueba con el log de intents habilitado Then el diff valida que el LLM NUNCA emitió un precio/item/promo fuera del contexto de `get_public_menu` (0 violaciones, de lo contrario la historia falla)
- [ ] Given el item pedido existe pero está fuera de ventana horaria o `delivery_enabled=false` When el cliente lo pide Then la IA informa indisponibilidad REAL (validada por `create_order`/`_item_available`) y sugiere alternativas o transfiere

**Prioridad:** P0
**Esfuerzo estimado:** 2 días (prompt de dominio + log de intents + suite N=50)
**Dependencias:** HU-F3-01, `get_public_menu` existente (L142)
**Notas técnicas:**
- D6: agente de dominio acotado — `tomar_pedido`, `confirmar_pedido`, `consultar_estado`, `modificar`/`cancelar` (solo antes de crear). Todo lo demás → `out_of_domain`.
- El log de intents (todos los outputs del LLM) es el insumo del diff de CA-F3-12; auditable en QA.
- Validación final SIEMPRE en `create_order` (el motor rechaza items inválidos/inagotables aunque el LLM alucine) — doble barrera R1.
- Cumplimiento §3.7: la IA se identifica como asistente automático al inicio (Meta 15-ene-2026 + BSUID).

---

### HU-F3-05: Kill-switch y presupuesto — gobernanza de costo (R4/R5/D10)

**Como** administrador de El Segoviano
**Quiero** poder apagar la IA de inmediato (kill-switch) y acotar su costo diario por minuto
**Para** que un incidente o un gasto inesperado nunca me deje sin operador humano ni sin control del gasto.

**Criterios de aceptación:**

- [ ] Given `companies.settings.voice_ai.kill_switch=true` When llega la siguiente llamada entrante Then rutea a `inbound_behavior=ring_operator` (F2: ringea a extensiones del operador) SIN pasar por la IA, sin deploy y de forma inmediata (CA-F3-10, R5)
- [ ] Given `kill_switch=true` When la llamada entra Then `ai_state` nunca arranca (no hay estado `greeting`; `call_records` sin columnas IA pobladas) (CA-F3-10)
- [ ] Given una llamada EN CURSO con la IA When el admin activa `kill_switch=true` a mitad de la llamada Then la llamada actual termina su flujo normal (no se corta en medio) y las SIGUIENTES van a `ring_operator`
- [ ] Given `voice_ai.enabled=false` (o tenant sin config `voice_ai`) When llega una llamada Then entra directo al operador humano; la IA jamás arranca (CA-F3-11)
- [ ] Given presupuesto diario `daily_budget_usd=10.0` When el acumulado del día alcanza/excede el tope (suma de `cost_usd` del día) Then las siguientes llamadas rutean `ring_operator` y la IA no arranca (CA-F3-11, R4)
- [ ] Given presupuesto por minuto `max_usd_per_minute=0.15` When una llamada en curso supera el costo/minuto estimado Then se transfiere al operador con `transfer_reason=budget` (R4)
- [ ] Given presupuesto agotado o kill-switch activo When el panel Central Telefónica muestra la llamada Then el estado IA aparece como `ring_operator`/sin IA (visible para el staff)
- [ ] Given el cambio de config (`PATCH /api/settings`) When se activa/desactiva `kill_switch` o `enabled` Then el ruteo cambia en la siguiente llamada sin reiniciar servicios ni hacer deploy (R5)
- [ ] Given kill-switch activado por incidente When el admin lo desactiva Then las llamadas vuelven a `ai_receptionist` (restauración inmediata)

**Prioridad:** P0
**Esfuerzo estimado:** 1.5 días (enforcement presupuesto + kill-switch + tests de ruteo)
**Dependencias:** F2 (`inbound_behavior`, `call_records`), HU-F3-06 (cost_usd medible)
**Notas técnicas:**
- D10: al agotar presupuesto o activar kill-switch, `inbound_behavior` de F2 cae a `ring_operator`.
- Acumulado diario: `SUM(cost_usd)` de `call_records` del tenant en el día (UTC/local del tenant).
- `cost_usd` lo reporta el bridge en `POST /api/v1/calls/{id}/complete` (cierre) y/o `cost_estimate` de STT en `transcript`.
- Config §3.3 vía `PATCH /api/settings` (mismo mecanismo D-03 spec 03 §3.4.3).

---

### HU-F3-06: Transcripción recuperable y panel de costo (CA-F3-3 / CA-F3-8)

**Como** staff / administrador de El Segoviano
**Quiero** recuperar la transcripción completa de cualquier llamada IA y ver su costo por llamada/día/mes
**Para** resolver disputas, auditar lo dicho por el cliente y controlar el gasto real de STT/TTS/LLM.

**Criterios de aceptación:**

- [ ] Given una llamada IA finalizada When `POST /api/v1/calls/{external_call_id}/transcript` persistió la transcripción (streaming o final) Then se crea `call_transcriptions` con `provider`, `text` completo, `segments` (start/end/speaker/text/confidence), `lang=es-PE`, `duration_sec` y `cost_estimate` y responde `201 {transcription_id}` (R3/D8)
- [ ] Given la transcripción creada When se persiste Then `call_records.transcription_fk` (FK reservada por F2) se actualiza apuntando a la transcripción — el detalle de la llamada en F2 la muestra sin cambio de contrato
- [ ] Given una llamada con transcripción When `GET /api/v1/calls/{id}/transcript` Then devuelve transcripción completa + segmentos + provider + lang (CA-F3-3)
- [ ] Given una llamada con grabación When `GET /api/v1/calls/{id}` Then devuelve `recording_path` accesible (grabación F2 MixMonitor) junto a `ai_state`, `context_summary`, `cost_usd` y `transcription` (CA-F3-3)
- [ ] Given una llamada IA finalizada When el bridge llama `POST /api/v1/calls/{external_call_id}/complete {duration_sec, cost_usd}` Then `call_records.cost_usd` queda poblado con el costo real STT+TTS+LLM de la llamada (R4)
- [ ] Given el panel de costo When consulto por llamada Then veo `cost_usd` por llamada (CA-F3-8)
- [ ] Given el panel de costo When consulto el resumen diario/mensual por tenant Then veo la suma ≈ STT+TTS+LLM reales (CA-F3-8)
- [ ] Given el acumulado del día When excede `daily_budget_usd` Then las siguientes llamadas rutean `ring_operator` y la última llamada IA queda marcada para transferencia motivo `budget` (R4, CA-F3-8)
- [ ] Given una transcripción mayor a `calls.retention_days` (F2 R2, default 90 días) When corre la purga Then la transcripción y grabación se eliminan junto con el resto de la llamada (R3)

**Prioridad:** P0
**Esfuerzo estimado:** 2 días (tabla + endpoints transcript/complete + vistas de costo en panel)
**Dependencias:** F2 (`call_records.transcription_fk`, `recording_path`, retención), HU-F3-10 (migración)
**Notas técnicas:**
- `call_transcriptions.call_id` = `call_records.external_call_id` (Uniqueid Asterisk, UNIQUE en F2);
  persistencia idempotente `INSERT ... ON CONFLICT (external_call_id) DO UPDATE` (mismo patrón F2).
- Costo: `cost_usd` (llamada) + `cost_estimate` (STT) → métricas por minuto y por día (CA-F3-8).
- Endpoints §3.5.1: `POST /transcript`, `POST /complete`, `GET /calls/{id}/transcript` (§3.5.2).
- Rate-limit Redis en endpoints del bridge (R8).

---

### HU-F3-07: Concurrencia — 2 llamadas simultáneas atendidas por la IA (R6/CA-F3-6)

**Como** operación de El Segoviano en hora pico
**Quiero** que la IA atienda varias llamadas a la vez (hasta el máximo configurado)
**Para** no perder pedidos cuando varias personas llaman simultáneamente (19:00–24:00).

**Criterios de aceptación:**

- [ ] Given `voice_ai.max_calls_concurrent=2` y trunk F2 con 4 canales G.711 When llegan 2 llamadas al mismo tiempo Then AMBAS son atendidas por la IA sin degradación de latencia (CA-F3-6)
- [ ] Given 2 llamadas simultáneas atendidas por IA When cada una avanza Then cada llamada tiene su propio `external_call_id`, `ai_state`, transcripción y `call_records` INDEPENDIENTES (sin mezcla de audio ni contexto) (CA-F3-6)
- [ ] Given 2 llamadas IA en curso (N=2 alcanzado) When llega una 3ª llamada Then esta rutea a `ring_operator` (cola/operador humano) porque no hay canales IA libres (R6)
- [ ] Given 2 llamadas IA en curso When una cuelga/termina Then el slot se libera y la siguiente llamada entrante vuelve a ser atendida por la IA
- [ ] Given 2 llamadas simultáneas When una transfiere a humano y la otra crea pedido Then cada flujo es independiente: `transfer_reason` en una, `converted_order_id` en la otra, sin cruzarse
- [ ] Given N canales IA ocupados When el admin monitorea el panel Then ve ambos `ai_call_state` en vivo por llamada (WS `/ws/calls/{tenant_id}`) con sus estados distintos (R10)

**Prioridad:** P1
**Esfuerzo estimado:** 2 días (semáforo de canales en bridge + aislamiento de contexto por llamada + tests)
**Dependencias:** F2 (trunk 4 canales G.711), PoC External Media (semana 1-2)
**Notas técnicas:**
- `max_calls_concurrent` (default 4, §3.3) ≤ canales del trunk (F2: 4); por encima → `ring_operator`.
- Cada llamada mantiene su propio contexto LLM (menú + items + dirección) en memoria del bridge,
  keyed por `external_call_id` — nunca compartido entre llamadas (R8).
- Prueba de carga: 2 llamadas simultáneas con latencia individual < 2s (CA-F3-5 + CA-F3-6).

---

### HU-F3-08: Latencia — primera respuesta del agente < 2s (CA-F3-5)

**Como** cliente que llama
**Quiero** escuchar el saludo de la IA casi de inmediato
**Para** no sentir que la llamada "no conectó" y no colgar antes de que responda.

**Criterios de aceptación:**

- [ ] Given una llamada entrante con `ai_receptionist` When Asterisk responde el canal (Stasis) Then la IA emite el saludo TTS en < 2s desde el fin del saludo de Asterisk hasta el audio del saludo de la IA (CA-F3-5)
- [ ] Given el saludo When se mide la latencia en PoC y QA Then el promedio y el p95 de la primera respuesta son < 2s (medido en N llamadas de prueba)
- [ ] Given el saludo inicial When se genera Then NO depende del LLM: es un audio pre-generado (TTS local/pre-cache del greeting configurado §3.3) mientras el STT/LLM se inicializan en paralelo
- [ ] Given latencia de primera respuesta ≥ 2s en QA (regresión) When se corre la prueba de rendimiento Then la historia se marca como fallida hasta optimizar (streaming STT, pre-warm de conexiones)
- [ ] Given una llamada con latencia de red alta del proveedor STT When el cliente habla Then el streaming permite que la IA responda por fragmentos sin esperar el audio completo (percepción de fluidez)

**Prioridad:** P1
**Esfuerzo estimado:** 1 día (medición + optimización; el greeting pre-generado es parte del PoC)
**Dependencias:** PoC External Media (semana 1-2) — criterio de salida del PoC (§4.2)
**Notas técnicas:**
- Estrategia §3.6: saludo pre-generado en TTS local (no espera al LLM) → primera respuesta instantánea.
- Medición: timestamp al terminar el saludo de Asterisk → timestamp del primer frame de audio TTS del agente.
- Si External Media falla en la semana 2 → Opción B (Vapi/Retell, §2.5) sin tocar contratos (§4.2).

---

### HU-F3-09: Aislamiento de tenant (R8)

**Como** plataforma IaaS-RonSys (multi-tenant)
**Quiero** que las llamadas, transcripciones, configs y costos de cada tenant estén completamente aislados
**Para** que ningún tenant vea ni afecte datos de otro (diseño multi-tenant por construcción).

**Criterios de aceptación:**

- [ ] Given dos tenants A y B con `voice_ai` configurado When una llamada IA de A persiste transcripción y `cost_usd` Then `call_transcriptions` y `call_records` de A tienen `tenant_id=A` y B no puede leerlos (filtro X-Tenant-ID/JWT en todas las queries) (R8)
- [ ] Given el endpoint `GET /api/v1/calls` del panel When el staff del tenant A consulta Then solo ve llamadas de A, aunque existan llamadas de B (filtro por tenant en lista y detalle)
- [ ] Given el WS `/ws/calls/{tenant_id}` When una llamada de A emite `ai_call_state` Then solo los clientes WS conectados con `tenant_id=A` reciben el evento (broadcast aislado por tenant, patrón WsManager)
- [ ] Given `external_call_id` (Uniqueid Asterisk) When dos llamadas de tenants distintos ocurren Then el ID es único global (UNIQUE en F2) y no hay colisión entre tenants (R8)
- [ ] Given el bridge interno When llama a `POST /transcript` o `POST /transfer` con service-token Then el backend valida que el `external_call_id` pertenece al tenant del token y rechaza con 403 si no coincide
- [ ] Given endpoints del bridge When hay abuso/rapidez excesiva Then el rate-limit Redis (sliding window) limita las peticiones por tenant y responde 429 (R8)
- [ ] Given el tenant A tiene `voice_ai.enabled=false` y B `true` When llamadas entran a ambos Then A ringea operador y B atiende IA (config aislada por tenant)
- [ ] Given el presupuesto diario de A When A agota su `daily_budget_usd` Then solo A cae a `ring_operator`; B sigue con IA normal (aislamiento de gobernanza de costo)

**Prioridad:** P0
**Esfuerzo estimado:** 1 día (revisión de filtros + tests de aislamiento)
**Dependencias:** F2 (modelo `call_records` con `tenant_id`, WS por tenant), rate-limit Redis existente
**Notas técnicas:**
- R8: todo filtrado por tenant (X-Tenant-ID/JWT); patrón ya estándar del backend (Company simple con company_id).
- `call_transcriptions.tenant_id` FK a companies ON DELETE CASCADE (§3.2).
- Rate limiting reutilizable: `app/core/rate_limit.py` (sliding window).

---

### HU-F3-10: Migración `0019_voice_ai` — tabla y columnas IA (CA-F3-13)

**Como** equipo de desarrollo
**Quiero** una migración Alembic que cree `call_transcriptions` y las columnas IA en `call_records`
**Para** que la capa de voz tenga persistencia sin tocar la tabla de F2 y con downgrade limpio.

**Criterios de aceptación:**

- [ ] Given BD con `call_records` de F2 aplicada (migración 0018) When corro `alembic upgrade head` Then se crea la tabla `call_transcriptions` (id, tenant_id FK companies CASCADE, call_id, provider, text, segments jsonb, lang default 'es-PE', duration_sec, cost_estimate, created_at) con índice `ix_call_transcriptions_call_id` (CA-F3-13, §3.2)
- [ ] Given `alembic upgrade head` When termina Then `call_records` tiene las columnas nuevas: `ai_state varchar(20)`, `transfer_reason varchar(50)`, `context_summary text`, `cost_usd numeric(10,4) NOT NULL DEFAULT 0` con sus CHECK constraints (`ai_state` IN los **8 estados** incl. `completed`/`failed` — corregido 2026-08-13 en implementación; `transfer_reason` IN los 5 motivos; `cost_usd >= 0`) (CA-F3-13)
- [ ] Given las CHECK constraints When se intenta insertar un `ai_state='hacking'` o `transfer_reason='other'` Then la BD rechaza (constraint violation) — el dominio queda blindado a nivel de datos
- [ ] Given la migración aplicada When consulto `alembic current` Then head = `0019_voice_ai` (CA-F3-13)
- [ ] Given la migración aplicada When corro `alembic downgrade 0018` Then se revierte TODO (tabla `call_transcriptions` eliminada + columnas IA eliminadas) sin afectar `call_records` de F2 (CA-F3-13)
- [ ] Given `call_records` de F2 con datos existentes When se aplica la migración Then las filas previas quedan con `ai_state=NULL`, `transfer_reason=NULL`, `cost_usd=0` (default) sin pérdida de datos (F2 intacta)
- [ ] Given una llamada IA exitosa When `create_order` devuelve el pedido Then `converted_order_id` (columna F2) se actualiza vía el mismo flujo F2 (sin duplicar la columna)
- [ ] Given retención de F2 When se purgan llamadas > `retention_days` Then las transcripciones asociadas se purgan en cascada (consistencia grabación + transcripción)

**Prioridad:** P0
**Esfuerzo estimado:** 0.5 días (migración + tests up/down)
**Dependencias:** F2 (migración 0018 `call_records` debe existir), se ejecuta ANTES de HU-F3-01/03/06
**Notas técnicas:**
- NO se crea otra tabla de llamadas: F3 adopta `call_records` de F2 y llena sus FK reservadas (`transcription_fk`, `converted_order_id`).
- DDL borrador en spec §3.2; la migración real debe respetar CHECK constraints exactos.
- Orden: `0019_voice_ai` es POSTERIOR a la 0018 de F2 en el orden real de cabeceras (numeración interna puede variar; el nombre de archivo del proyecto manda).
- `downgrade 0018` revierte solo lo de F3 (F2 permanece).

---

## 📊 Resumen de Historias

| ID | Historia | Criterio(s) Spec | Capa | Esfuerzo |
|----|----------|:----------------:|------|:--------:|
| HU-F3-01 | Pedido completo por voz → `create_order` + WhatsApp | CA-F3-1, CA-F3-2 | Backend (voz) | 5d |
| HU-F3-02 | Resolución de zona por distrito (D7) | CA-F3-9 | Backend | 2d |
| HU-F3-03 | Transferencia a humano con contexto (D9) | CA-F3-4 | Back+Panel | 2d |
| HU-F3-04 | Anti-alucinación (R1, N=50) | CA-F3-7, CA-F3-12 | Backend (LLM) | 2d |
| HU-F3-05 | Kill-switch + presupuesto (D10) | CA-F3-10, CA-F3-11 | Backend | 1.5d |
| HU-F3-06 | Transcripción recuperable + panel de costo | CA-F3-3, CA-F3-8 | Back+Panel | 2d |
| HU-F3-07 | Concurrencia N=2 (R6) | CA-F3-6 | Backend (bridge) | 2d |
| HU-F3-08 | Latencia primera respuesta < 2s | CA-F3-5 | Backend (voz) | 1d |
| HU-F3-09 | Aislamiento de tenant (R8) | R8 | Backend | 1d |
| HU-F3-10 | Migración `0019_voice_ai` | CA-F3-13 | Backend (DB) | 0.5d |

| **Total** | | | | **19 días** |
|-----------|---------|------------|----------|------------|
| Backend (incl. voz/bridge) | | | | 17d |
| Panel / WS (extiende F2) | | | | 2d (incluidos) |

---

## 🔗 Dependencias entre historias

```
F2 (Central Telefónica) [IMPLEMENTADA en prod]
  │
  └── HU-F3-10 (migración 0019_voice_ai — DB base de F3)
        │
        ├── HU-F3-08 (latencia < 2s — PoC External Media, semana 1-2)
        │     └── HU-F3-01 (pedido completo por voz — usa pipeline STT→LLM→TTS)
        │           ├── HU-F3-02 (zona por distrito — entrada del pedido)
        │           ├── HU-F3-04 (anti-alucinación — prompt/contexto del LLM)
        │           └── HU-F3-06 (transcripción + costo — persistencia del flujo)
        │                 ├── HU-F3-03 (transferencia con contexto — usa transcripción enlazada)
        │                 └── HU-F3-05 (kill-switch + presupuesto — usa cost_usd)
        │                       └── HU-F3-07 (concurrencia — slots sobre F2)
        │                             └── HU-F3-09 (aislamiento — cross-cutting, validar en todas)
```

### Orden de implementación recomendado

1. **HU-F3-10** — Migración (cimientos de datos; desbloquea todo lo demás)
2. **HU-F3-08** — PoC latencia/pipeline de voz (puerta de entrada, §4.2: criterio de salida = pedido real vía `create_order`)
3. **HU-F3-01** — Pedido completo por voz (núcleo del MVP)
4. **HU-F3-02** — Zona por distrito (requisito de HU-F3-01 completo)
5. **HU-F3-04** — Anti-alucinación (hardening del LLM, corre con HU-F3-01)
6. **HU-F3-06** — Transcripción + costo (persistencia y medición)
7. **HU-F3-03** — Transferencia con contexto (usuario real del panel)
8. **HU-F3-05** — Kill-switch + presupuesto (gobernanza, antes de abrir a tráfico real)
9. **HU-F3-07** — Concurrencia (escalar a hora pico)
10. **HU-F3-09** — Aislamiento (validación cross-cutting en QA, puede correr en paralelo)

> ⚠️ Si el PoC de External Media falla en la semana 2 → activar **Opción B (Vapi/Retell)** según §2.5/§4.2: la lógica de dominio (estados, reglas, `create_order`, contratos §3.5) es agnóstica al transporte de voz; solo HU-F3-08 y la parte de streaming de HU-F3-01 cambian de implementación.

---

## 🎯 Cobertura de Criterios de Aceptación (Spec §3.9)

| Criterio | Caso | Historias que lo cubren |
|:--------:|------|-------------------------|
| CA-F3-1 | Pedido completo por voz → Sale/kárdex/asiento/Kitchen/Delivery + `converted_order_id` | HU-F3-01 |
| CA-F3-2 | Evento `delivery.confirmed` → WhatsApp | HU-F3-01 |
| CA-F3-3 | Transcripción + segmentos recuperables, `transcription_fk`, grabación | HU-F3-06 |
| CA-F3-4 | Queja / fuera de dominio → transferencia con contexto | HU-F3-03 |
| CA-F3-5 | Primera respuesta < 2s | HU-F3-08 |
| CA-F3-6 | 2 llamadas simultáneas sin degradación | HU-F3-07 |
| CA-F3-7 | Pregunta fuera de dominio → declina y transfiere | HU-F3-03, HU-F3-04 |
| CA-F3-8 | Panel de costo por llamada/día/mes; exceso → motivo `budget` | HU-F3-06, HU-F3-05 |
| CA-F3-9 | "Canto Grande"/"Montenegro" → `zone_id`; no reconocida → repregunta → transfer | HU-F3-02 |
| CA-F3-10 | `kill_switch: true` → `ring_operator` sin deploy | HU-F3-05 |
| CA-F3-11 | Presupuesto agotado / `enabled: false` → operador, IA nunca arranca | HU-F3-05 |
| CA-F3-12 | Anti-alucinación N=50 (0 violaciones) | HU-F3-04 |
| CA-F3-13 | `alembic upgrade head` → `0019_voice_ai`; `downgrade 0018` revierte | HU-F3-10 |

---

## 🔍 Preguntas abiertas para Jarvis / Backend (a resolver en desarrollo)

1. **`max_clarify_attempts=2`** (spec §3.3) vs **"repregunta 1 vez"** (D7/CA-F3-9): ¿el conteo incluye la primera captura fallida o solo las repreguntas? Las historias asumen: 1ª captura fallida + 1 repregunta fallida = transfer (2 intentos totales).
2. **Costos STT/TTS/LLM**: ¿`cost_usd` lo calcula el bridge (tarifas por minuto conocidas) o el backend consulta las APIs de los proveedores? Asumido: bridge calcula con tarifas config.
3. **N=50 (CA-F3-12)**: ¿se ejecuta en QA con llamadas reales (trunk) o con simulador de audio? Asumido: QA con trunk real + log de intents.
4. **Orden de migraciones**: F2 publicó `0018`; F3 es `0019_voice_ai` (confirmado 2026-08-13 en reconciliación: 0017=whatsapp_bsuid, 0018=call_records) en el árbol de Alembic al implementar.

---

*Documento generado por PO Agent 📋 a partir de la Spec 06 (F3 — Recepcionista IA por Voz, v0.1, APROBADA 2026-08-12), con trazabilidad completa a CA-F3-1..13 y reglas R1..R10. F2 (Central Telefónica) verificada como implementada y desplegada en prod.*
