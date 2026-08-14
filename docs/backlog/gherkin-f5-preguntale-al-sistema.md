# Backlog Gherkin — F5: "Pregúntale al Sistema" (NL2SQL controlado)

**Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
**Origen:** Spec 08 — `docs/specs/06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md` (APROBADA por Ron, 2026-08-13)
**Generado por:** PO Agent 📋
**Fecha:** 2026-08-13
**Estado:** ✅ Listo para desarrollo (spec aprobada + PoC validado 5/5: `spikes/f5-preguntale-al-sistema/`)
**Total Historias:** 10
**Alcance:** Chat NL2SQL controlado en el Panel del Dueño (`/panel`) — consultas DELIVERY con datos reales del ERP, sin SQL libre, multi-tenant, auditado

---

## 📌 Contexto

El dueño (Ron / El Segoviano) escribe en lenguaje natural en el panel ("¿cuál es el producto más
vendido hoy por delivery?", "¿cuánto vendió la Zona 1 esta semana?", "¿qué campaña tuvo mejor ROAS
el mes pasado?") → la IA interpreta la intención, **elige la consulta correcta de un CATÁLOGO
SEGURO** (tool calling / NL2SQL controlado, D1: **el LLM nunca escribe SQL**), la ejecuta contra
datos reales del ERP (R3: sin cache) y responde al instante.

F5 **revive el puerto hexagonal de skills** (`app/core/agents/base.py`, deuda #8: `BaseSkill`/
`AgentContext`/`SkillResult`/`SkillRegistry` — código muerto verificado) con el primer skill
concreto `DeliverySkill`, y reutiliza infra ya lista: `get_tenant_id` (`core/tenant.py`),
`RateLimiter` Redis (`core/rate_limit.py`), `require_role("admin","manager","viewer")`
(`core/dependencies.py`), y las métricas delivery ya probadas en `delivery_service.py` /
`owner_dashboard_service.py` (base del catálogo, cero fórmulas duplicadas).

Estas 10 historias cubren los **14 criterios de aceptación (CA-F5.1..14)** y las **9 reglas de
negocio (R1..R9)** de la spec, más los contratos §3.3 (`POST /ask`, `GET /catalog`, `GET /logs`),
el pipeline interno §3.3.2 (8 pasos), el catálogo MVP §3.4 (10 consultas delivery, ≥8 exigidas)
y la migración **`0020_assistant`** (la `0019` ya es de F3 voice_ai).

### 📋 Mapa de trazabilidad Spec → Historias

| Criterio / Regla | Historias |
|------------------|-----------|
| CA-F5.1 (top producto hoy → 200 con answer/data/catalog_query_used) | HU-F5-01 |
| CA-F5.2 (Zona 1 esta semana) | HU-F5-02 |
| CA-F5.3 (mejor ROAS mes pasado) | HU-F5-02 |
| CA-F5.4 (fuera de catálogo → fallback amable, nunca SQL) | HU-F5-03 |
| CA-F5.7 (inyección SQL → rechazo, BD intacta) | HU-F5-04 |
| CA-F5.5 (aislamiento multi-tenant) | HU-F5-05 |
| CA-F5.6 (auditoría query_logs) | HU-F5-06 |
| CA-F5.8 (sin LLM key → fallback, nunca 500) | HU-F5-07 |
| CA-F5.9 (params inválidos → 422) | HU-F5-08 |
| CA-F5.10 (rate limit → 429 por tenant) + CA-F5.11 (catalog por rol) + CA-F5.14 (401/403) | HU-F5-09 |
| CA-F5.12 (catálogo ≥8) + CA-F5.13 (frontend chat /panel) | HU-F5-10 |
| R1 (solo catálogo) / R3 (sin cache) / R7 (solo lectura) | HU-F5-01, HU-F5-03, HU-F5-04 |
| R2 (tenant scope siempre) | HU-F5-05 |
| R4 (auditoría) | HU-F5-06 |
| R5 (fallback "no entendí" con sugerencias) | HU-F5-03, HU-F5-07 |
| R6 (rate limit 10 req/min/tenant) / R8 (roles por consulta) | HU-F5-09 |
| R9 (fechas normalizadas por LLM + validación) | HU-F5-02, HU-F5-08 |

### 🔑 Supuestos de entrada (verificados)

- **PoC aprobado (spike, 2026-08-13, commit `ac13d31`)**: VentasSkill sobre `BaseSkill` con
  function calling DeepSeek (`deepseek-v4-flash`, API compatible OpenAI) → tool correcta 5/5;
  fallback determinista por palabras clave 100% (5/5) a 35–44ms; eval golden tool + data accuracy
  100%; demo read-only contra prod (S/ 494 hoy, canal `restaurant`).
- **Base de seguridad lista**: `get_tenant_id` (X-Tenant-ID → JWT fallback → 400), `RateLimiter`
  Redis sliding-window + fallback in-memory, `require_role("admin","manager","viewer")`.
- **Métricas delivery ya existen** y son tenant-scoped: `metrics_overview` (L814),
  `metrics_campaigns` (ROAS/AOV, L773), `get_owner_dashboard` (`_resolve_dates` default 30 días,
  `_top_platos`, `orders_by_zone`, `funnel`, `_comparison`, `_margins_by_channel`, `_channels`).
- **Config LLM**: `llm_provider="openai"`, `llm_model="gpt-4o"`, `llm_api_key` opcional desde
  `.env` — **hoy sin key** → modo degradado obligatorio (R5/CA-F5.8).
- **Hallazgo spike**: en prod el canal activo es `restaurant` (salón); delivery activo = 0
  (los DLV- son E2E canceladas) → el catálogo debe parametrizar canal/`business_type`.
- **Bug real corregido en spike**: `fecha=None` no filtraba por CURRENT_DATE → el MVP debe
  incluir la guarda `sale_date = CURRENT_DATE` en `sql_template`.

---

## Historias

---

### HU-F5-01: Chat de negocio — pipeline NL2SQL controlado con datos reales

**Como** dueño de El Segoviano (Ron)
**Quiero** preguntar en lenguaje natural ("¿cuál es el producto más vendido hoy por delivery?") y
recibir una respuesta en español con datos reales del ERP
**Para** tomar decisiones sin abrir dashboards ni esperar a un analista.

**Criterios de aceptación:**

- [ ] Given estoy autenticado con rol `viewer` (o superior) y X-Tenant-ID válido When `POST /api/v1/assistant/ask` con `{"question": "¿cuál es el producto más vendido hoy por delivery?"}` Then responde 200 con `answer` en español (ej. "Hoy el producto más vendido por delivery fue el Lomo Saltado (12 pedidos, S/ 486.00)"), `data` real, `catalog_query_used: {id, name: "top_products_delivery", skill: "delivery"}` y `params: {date_from: hoy, date_to: hoy, limit: 5}` (CA-F5.1)
- [ ] Given la pregunta When corre el pipeline interno (§3.3.2) Then el LLM elige SOLO `query_catalog_id` + `params` tipados vía tool calling — el LLM jamás aporta SQL (D1/R1)
- [ ] Given la consulta elegida del catálogo When el motor la ejecuta Then usa `sql_template` con **bound params** de SQLAlchemy `text()` — nunca interpolación de strings
- [ ] Given la consulta tiene `tenant_scope=true` When se ejecuta Then `:tenant_id` lo inyecta el motor desde `get_tenant_id` (nunca del LLM ni del usuario) y la data es tenant-scoped (R2)
- [ ] Given dos preguntas iguales seguidas When las ejecuto Then cada `ask` consulta PostgreSQL en vivo — sin capa de cache; la segunda refleja cambios de datos si los hubo (R3/CA-F5.1)
- [ ] Given el rol es `admin`/`manager`/`viewer` When uso `/assistant/*` Then solo lectura garantizada (R7): `sql_template` restringido a SELECT, sin endpoints de escritura en el asistente
- [ ] Given la pregunta sin rango de fechas explícito When el LLM no infiere fechas Then el motor aplica el default `_resolve_dates` (últimos 30 días)
- [ ] Given una consulta que delega en funciones existentes When se implementa Then se llama a `delivery_service`/`owner_dashboard_service` (misma fórmula, cero divergencia); `sql_template` solo si no existe función (decisión Spec Anchor §3.4)

**Prioridad:** P0
**Esfuerzo estimado:** 3 días (LLMClient + AssistantService pipeline + DeliverySkill)
**Dependencias:** HU-F5-10 (migración + seed catálogo), D3 (revivir `app/core/agents/base.py`)
**Notas técnicas:**
- Pipeline 8 pasos §3.3.2: sanitize → LLM tool calling → validar params → inyectar tenant → ejecutar → formatear → auditar → responder.
- Catálogo como "tools" del LLM: id + description_es + esquema de params (D1).
- Guarda del spike: si `fecha=None` → `sale_date = CURRENT_DATE` (bug corregido, obligatorio en `sql_template`).
- Hallazgo spike: parametrizar `business_type` (delivery|restaurant) por consulta — en prod hoy el canal activo es `restaurant`.

---

### HU-F5-02: Fechas relativas — "esta semana" y "el mes pasado" resueltas por el LLM

**Como** dueño de El Segoviano
**Quiero** usar fechas relativas ("hoy", "esta semana", "el mes pasado") sin escribir fechas manualmente
**Para** consultar métricas de períodos comunes con una sola frase.

**Criterios de aceptación:**

- [ ] Given pregunto "¿cuánto vendió la Zona 1 esta semana?" When corre el pipeline Then el LLM normaliza el rango a `date_from`/`date_to` (YYYY-MM-DD) de la semana en curso, elige `catalog_query_used=sales_by_zone` y la respuesta incluye ventas/pedidos reales de la Zona 1 (CA-F5.2)
- [ ] Given pregunto "¿qué campaña tuvo mejor ROAS el mes pasado?" When corre el pipeline Then el LLM normaliza el rango al mes anterior completo, elige `catalog_query_used=campaign_roas` y la respuesta identifica la campaña de mayor ROAS con `data` de campañas (CA-F5.3)
- [ ] Given una fecha relativa dicha por el usuario When el LLM la normaliza Then los params salen como `date_from`/`date_to` ISO — el motor jamás acepta expresiones SQL de fecha (D7/R9)
- [ ] Given pregunta sin fechas ("¿cuánto vendió la Zona 1?") When no hay rango inferido Then se aplica el default `_resolve_dates` (últimos 30 días) y la respuesta lo indica
- [ ] Given un rango con `date_from > date_to` (inferido o forzado) When valida el motor Then responde 422 con detalle del parámetro (R9)
- [ ] Given una fecha malformada ("13/13/2026") en params When valida el motor Then responde 422 con detalle del parámetro (CA-F5.9)
- [ ] Given "hoy" en una consulta de campañas When se resuelve Then el rango es hoy→hoy y la query `campaign_roas` devuelve el ROAS real del día (o 0/vacío honesto si no hay campañas)

**Prioridad:** P0
**Esfuerzo estimado:** 1.5 días (normalización de fechas en tool calling + validación)
**Dependencias:** HU-F5-01 (pipeline), HU-F5-10 (seed `sales_by_zone`, `campaign_roas`)
**Notas técnicas:**
- Patrón `_resolve_dates` de `owner_dashboard_service.py` (default 30 días) — reutilizado, no duplicado.
- R9: el LLM normaliza lenguaje natural → ISO; el motor solo valida (formato + `from ≤ to`).
- El rango resuelto queda en `params` (auditoría R4): permite reproducir la respuesta después.

---

### HU-F5-03: Rechazo amable — fuera de catálogo con sugerencias (fallback R5)

**Como** dueño de El Segoviano
**Quiero** que cuando pregunte algo que el sistema no sabe responder, me lo diga con educación y me sugiera qué sí puede responder
**Para** no quedarme sin guía ni recibir respuestas inventadas.

**Criterios de aceptación:**

- [ ] Given pregunto algo fuera de catálogo ("¿cuál es el apellido del dueño?") When `POST /ask` Then responde 200 con fallback amable `{answer: "Aún no sé responder eso. Puedo ayudarte con: …", catalog_query_used: null, data: null, suggestions: [...]}` — **nunca** se ejecuta SQL (CA-F5.4, R5)
- [ ] Given pido una acción de escritura ("borra la venta 5", "cambia el estado del pedido 12") When llega la pregunta Then responde fallback con sugerencias; no existe acción de escritura (R7) y se registra `rejected=true`
- [ ] Given pido SQL libre ("dame SQL de todo", "muéstrame la query completa") When llega la pregunta Then responde fallback R5; cero SQL del usuario se ejecuta (R1)
- [ ] Given una pregunta rechazada When se registra Then `query_logs` guarda la pregunta cruda con `rejected=true` y `query_catalog_id=null` (insumo para ampliar el catálogo, §3.2)
- [ ] Given el fallback When se construyen las sugerencias Then salen del catálogo activo y permitido para el rol (ej. "Top productos delivery", "Ventas por zona", "ROAS por campaña")
- [ ] Given una pregunta ambigua que podría mapear a 2 consultas When el LLM no elige con confianza Then aplica fallback R5 con sugerencias (nunca adivina la consulta)

**Prioridad:** P0
**Esfuerzo estimado:** 1 día (fallback + sugerencias + test de rechazo)
**Dependencias:** HU-F5-01 (pipeline), HU-F5-10 (catálogo para sugerencias)
**Notas técnicas:**
- R5: fallback amable con sugerencias del catálogo — nunca 500, nunca respuesta inventada.
- `rejected=true` en `query_logs` alimenta la ampliación futura del catálogo (misma filosofía que F3: datos reales, nunca alucinación).
- Las sugerencias usan `GET /api/v1/assistant/catalog` (mismo filtro de rol que el LLM).

---

### HU-F5-04: Anti-inyección SQL — el catálogo es el único SQL posible (R1)

**Como** plataforma IaaS-RonSys
**Quiero** que ningún intento de inyección SQL tenga efecto alguno
**Para** proteger los datos del ERP de El Segoviano y de todos los tenants.

**Criterios de aceptación:**

- [ ] Given pregunto "¿qué vendimos hoy?; DROP TABLE sales--" When `POST /ask` Then responde fallback R5 (CA-F5.4) con `rejected=true`; la BD queda intacta (CA-F5.7)
- [ ] Given pregunto "SELECT * FROM users" When llega la pregunta Then el LLM no la mapea a ningún `query_catalog_id` y responde fallback; la cadena del usuario jamás aparece en ejecución SQL (CA-F5.7)
- [ ] Given intento "… UNION SELECT …", "… OR 1=1 …" o comentarios SQL When llega la pregunta Then los params se validan contra el schema y se vinculan como **bound params** — el `sql_template` del catálogo es el único SQL ejecutable (R1)
- [ ] Given un param con payload malicioso ("zona": "x' OR 1=1--") When el LLM lo propone y valida el motor Then responde 422 (zona fuera de `allowed_values` / tipo inválido) — jamás se interpola
- [ ] Given cualquier texto de usuario When entra al pipeline Then pasa por sanitize (límite de chars, idioma es) antes de llegar al LLM (§3.3.2 paso 1)
- [ ] Given la suite de seguridad When corren los tests Then incluyen casos de inyección (DROP/UNION/SELECT * / comentarios) verificando rechazo + log `rejected=true` (CA-F5.7)

**Prioridad:** P0
**Esfuerzo estimado:** 1 día (sanitize + validación + tests de inyección)
**Dependencias:** HU-F5-01 (pipeline)
**Notas técnicas:**
- D1/R1: `query_catalog.sql_template` es el **único** lugar con SQL en todo el flujo; el usuario y el LLM jamás aportan SQL.
- Params vinculados con `SQLAlchemy text()` / bound params — nunca interpolación de strings (§3.2).
- Tests de inyección obligatorios en Fase 3 del plan (§4).

---

### HU-F5-05: Aislamiento multi-tenant — cada tenant solo ve sus datos (R2)

**Como** plataforma IaaS-RonSys (multi-tenant)
**Quiero** que la misma pregunta con distintos tenants devuelva solo los datos de cada uno
**Para** que El Segoviano y futuros tenants jamás vean ni afecten datos ajenos.

**Criterios de aceptación:**

- [ ] Given el tenant A y el tenant B tienen ventas delivery distintas When ambos preguntan "¿cuál es el producto más vendido hoy por delivery?" con su X-Tenant-ID Then cada uno recibe SOLO sus datos (CA-F5.5)
- [ ] Given toda consulta del catálogo MVP When se ejecuta Then tiene `tenant_scope=true` y `:tenant_id` lo inyecta el motor desde `get_tenant_id` — nunca proviene del LLM ni del texto del usuario (R2)
- [ ] Given una request sin X-Tenant-ID ni JWT con `company_id` válido When llega a `/assistant/*` Then responde 400 (`get_tenant_id`) — nada se ejecuta
- [ ] Given intento de consultar datos ajenos en lenguaje natural ("¿cuánto vendió la otra empresa?") When llega la pregunta Then no existe consulta de catálogo que lo resuelva → fallback R5 (CA-F5.4)
- [ ] Given una fila de `query_catalog` con `tenant_scope=false` When existe en BD Then el motor la excluye del catálogo activo (toda query MVP es `tenant_scope=true`)
- [ ] Given el aislamiento When corren los tests de QA Then incluyen la misma pregunta con X-Tenant-ID A vs B verificando cero cruce de datos (CA-F5.5)

**Prioridad:** P0
**Esfuerzo estimado:** 1 día (scoping + tests de aislamiento)
**Dependencias:** HU-F5-01 (pipeline), HU-F5-10 (migración — columna `tenant_scope`)
**Notas técnicas:**
- R2: `:tenant_id` inyectado por el motor en TODA query (`tenant_scope=true`), jamás por el LLM.
- Reutiliza `get_tenant_id` (`app/core/tenant.py`: X-Tenant-ID → fallback JWT `company_id` → 400).
- Tests de aislamiento obligatorios (CA-F5.5) — mismos escenarios que el patrón F3/R8.

---

### HU-F5-06: Auditoría total — toda pregunta queda en `query_logs` (R4)

**Como** administrador de la plataforma / de El Segoviano
**Quiero** que toda pregunta (resuelta o rechazada) quede registrada con su detalle
**Para** auditar el uso del asistente, medir consumo y mejorar el catálogo.

**Criterios de aceptación:**

- [ ] Given hago 3 preguntas resueltas + 1 rechazada When reviso `query_logs` Then hay 4 filas: `pregunta` cruda, `query_catalog_id` (null en el rechazo), `params` finales, `result_summary`, `tokens_used`, `latency_ms` y `rejected` correctos (CA-F5.6, R4)
- [ ] Given `result_summary` When se persiste Then contiene solo resumen `{rows, total?, first_rows}` — **nunca** la data completa (evita duplicar datos sensibles en logs, §3.2)
- [ ] Given `GET /api/v1/assistant/logs?from=&to=&rejected=` When lo consulta un rol `admin` Then responde 200 con los logs filtrados por rango y estado de rechazo (R4)
- [ ] Given `GET /api/v1/assistant/logs` When lo consulta un rol `manager` o `viewer` Then responde 403 (solo admin audita)
- [ ] Given una pregunta rechazada When se registra Then `rejected=true` queda con la pregunta cruda → insumo para ampliar el catálogo (mismo patrón F3: log de intents para anti-alucinación)
- [ ] Given el log de una consulta resuelta When lo inspecciono Then puedo reproducir la respuesta desde `query_catalog_id` + `params` (trazabilidad completa)

**Prioridad:** P0
**Esfuerzo estimado:** 1.5 días (tabla + escritura en pipeline + endpoint `GET /logs`)
**Dependencias:** HU-F5-10 (migración `query_logs`), HU-F5-01 (pipeline paso 7)
**Notas técnicas:**
- `query_logs`: `tenant_id` FK CASCADE, `user_id` FK SET NULL, `query_catalog_id` FK SET NULL, `result_summary` jsonb con resumen (nunca data completa), índice `(tenant_id, created_at DESC)` (§3.2).
- Paso 7 del pipeline: auditar en la misma request (R4) — el log se escribe aunque la respuesta sea fallback.
- `GET /logs` solo admin (R4) — `require_role("admin")`.

---

### HU-F5-07: Modo degradado sin LLM key — fallback determinista, nunca 500 (D2)

**Como** operación de El Segoviano
**Quiero** que el chat funcione aunque no haya API key de LLM configurada
**Para** no depender de terceros y que el panel nunca se caiga por falta de configuración.

**Criterios de aceptación:**

- [ ] Given `llm_api_key` NO configurada (`.env` sin key — estado actual verificado) When `POST /ask` Then responde 200 con fallback de sugerencias (R5) — **nunca 500 ni timeout colgado** (CA-F5.8)
- [ ] Given el modo degradado When la pregunta tiene palabras clave reconocibles ("top producto hoy", "ventas zona 1") Then el fallback determinista por palabras clave responde con la consulta correcta del catálogo (validado en spike: 100% de acierto a 35–44ms)
- [ ] Given el modo degradado When la pregunta es ambigua o fuera de catálogo Then responde "no entendí" con sugerencias (`catalog_query_used: null`)
- [ ] Given el LLM con key configurada When una llamada falla o excede el timeout Then el pipeline cae al fallback determinista — la respuesta sigue siendo 200 con sugerencias o consulta correcta (nunca 500)
- [ ] Given sin key When después se configura `llm_api_key` en `.env` Then el modo LLM se activa sin deploy (config desde `.env`, D2)
- [ ] Given el modo LLM activo When la pregunta es delivery Then usa tool calling con el catálogo real (validado: DeepSeek elige tool correcta 5/5, ~2.4s)

**Prioridad:** P0
**Esfuerzo estimado:** 1 día (LLMClient con fallback — ya prototipado en spike)
**Dependencias:** HU-F5-01 (pipeline), HU-F5-10 (catálogo para el matcher de palabras clave)
**Notas técnicas:**
- D2: `llm_provider="openai"`, `llm_model="gpt-4o"`; API compatible DeepSeek (cambiar provider/model). Sin key → modo degradado (nunca 500).
- Fallback determinista por palabras clave validado en el spike (`spikes/f5-preguntale-al-sistema/`): 100% accuracy, 35–44ms.
- El fallback y el LLM comparten el MISMO catálogo → mismo resultado de contrato.

---

### HU-F5-08: Validación de parámetros — params inválidos → 422 (R9)

**Como** sistema
**Quiero** validar los params contra el schema del catálogo antes de ejecutar cualquier consulta
**Para** nunca ejecutar queries con fechas, tipos o valores inválidos.

**Criterios de aceptación:**

- [ ] Given el LLM propone fecha "13/13/2026" en params When valida el motor contra el schema Then responde 422 con detalle del parámetro (CA-F5.9)
- [ ] Given params con `date_from > date_to` When valida el motor Then responde 422 con detalle (R9)
- [ ] Given una zona inexistente ("Zona 99") en una consulta con `allowed_values` de zonas When valida el motor Then responde 422 con detalle (CA-F5.9)
- [ ] Given un tipo incorrecto (`limit: "abc"` en vez de int) When valida el motor Then responde 422
- [ ] Given falta un param `required` (ej. sin `date_from` cuando el schema lo exige) When valida el motor Then responde 422 con detalle
- [ ] Given el canal en `campaign_roas` no está en el enum (`meta|google|tiktok|other`) When valida el motor Then responde 422 con detalle
- [ ] Given params válidos When valida el motor Then la consulta se ejecuta y responde 200 (nunca se rechaza un param válido)

**Prioridad:** P0
**Esfuerzo estimado:** 0.5 días (validador de schema + tests 422)
**Dependencias:** HU-F5-01 (pipeline paso 3)
**Notas técnicas:**
- Validación contra `query_catalog.params` (tipos, required, `allowed_values`, rango de fechas) — paso 3 del pipeline §3.3.2.
- 422 siempre con detalle del parámetro (nombre + motivo) — mismo patrón de validación del backend FastAPI.
- El motor solo acepta valores; jamás expresiones SQL (D7/R1).

---

### HU-F5-09: Seguridad de acceso — auth 401/403, roles por consulta y rate limit (R6/R7/R8)

**Como** plataforma IaaS-RonSys
**Quiero** controlar quién usa el asistente, qué consultas ve cada rol y cuánto puede consumir
**Para** proteger el sistema del abuso y de accesos no autorizados.

**Criterios de aceptación:**

- [ ] Given una request SIN autenticación When llama a `POST /ask` o `GET /catalog` Then responde 401 (CA-F5.14)
- [ ] Given un rol `staff` (sin `viewer`) autenticado When llama a `/assistant/*` Then responde 403 (CA-F5.14)
- [ ] Given un rol `admin`/`manager`/`viewer` When llama a `POST /ask` Then responde 200 — solo lectura (R7)
- [ ] Given el límite configurado en 10 req/min por tenant When hago 11+ requests en 1 minuto a `/ask` Then la 11ª responde 429 con header `Retry-After` (CA-F5.10, R6)
- [ ] Given el rate limit es POR TENANT When el tenant A excede el límite y el tenant B no Then B sigue recibiendo 200 mientras A recibe 429 (A no bloquea a B) (CA-F5.10)
- [ ] Given `GET /api/v1/assistant/catalog` con rol `viewer` When consulto Then responde 200 solo con consultas `active` y permitidas para el rol (CA-F5.11, R8)
- [ ] Given una consulta con `allowed_roles: ["admin"]` en el catálogo When un `viewer` usa el chat Then esa consulta no aparece ni en sus sugerencias ni como tool del LLM (R8)
- [ ] Given el catálogo para el LLM When se construye el contexto de tools Then solo incluye las consultas `active` y del rol del usuario (R8)

**Prioridad:** P0
**Esfuerzo estimado:** 1.5 días (router + rate limit + filtro de roles + tests 401/403/429)
**Dependencias:** HU-F5-01 (pipeline), HU-F5-10 (migración — columna `allowed_roles`)
**Notas técnicas:**
- Reuso: `require_role("admin","manager","viewer")` (`core/dependencies.py`), `RateLimiter` Redis sliding-window + fallback in-memory (`core/rate_limit.py`).
- `allowed_roles` jsonb en `query_catalog` filtra qué consultas ve el LLM y el dueño por rol (R8).
- 429 con `Retry-After`; límite ajustable, mismo orden que el checkout público (R6).
- 401/403 aplican a `/assistant/*` completo (ask, catalog, logs — este último además solo admin).

---

### HU-F5-10: Catálogo MVP + chat en el Panel del Dueño (CA-F5.12 / CA-F5.13)

**Como** dueño de El Segoviano
**Quiero** un chat dentro de `/panel` que me sugiera qué preguntar y me responda con datos del ERP
**Para** usar el sistema conversacionalmente sin salir del panel.

**Criterios de aceptación:**

- [ ] Given la migración `0020_assistant` aplicada (`alembic upgrade head`) When reviso `query_catalog` Then existen tablas `query_catalog` + `query_logs` y **≥8 consultas delivery activas seedeadas** — exactamente 10: `top_products_delivery`, `sales_by_zone`, `campaign_roas`, `delivery_overview`, `orders_by_status`, `avg_ticket_delivery`, `sales_by_hour_delivery`, `comparison_week`, `delivery_margins`, `sales_by_channel` (CA-F5.12, §3.4)
- [ ] Given el catálogo seedeado When ejecuto en QA las 3 preguntas de ejemplo del contexto Then las 3 se resuelven con datos reales: top producto hoy (CA-F5.1), ventas Zona 1 esta semana (CA-F5.2), mejor ROAS mes pasado (CA-F5.3) (CA-F5.12)
- [ ] Given el catálogo When valido su seguridad Then cada consulta tiene `params` jsonb tipados, `tenant_scope=true` y `allowed_roles` (R2/R8) — nada ejecutable sin el motor
- [ ] Given el frontend en `/panel` When cargo el Panel del Dueño Then veo el componente `AssistantChat` integrado en `DashboardOwner` con sugerencias del catálogo (CA-F5.13)
- [ ] Given escribo una pregunta en el chat When envío Then veo estado de carga y luego la respuesta con `answer` + dato real (data) (CA-F5.13)
- [ ] Given una respuesta de fallback o error de red When ocurre Then veo mensaje amigable con sugerencias — nunca pantalla rota ni error crudo (CA-F5.13)
- [ ] Given las sugerencias del chat When se muestran Then provienen de `GET /api/v1/assistant/catalog` (solo consultas del rol del usuario) (R8)
- [ ] Given una conversación multi-pregunta When pregunto algo nuevo Then cada `ask` es independiente (sin memoria multi-turno persistente — fuera de alcance MVP, §3.1)
- [ ] Given el catálogo por canal (hallazgo spike) When la consulta filtra por `business_type`/canal Then el MVP soporta `delivery` y puede consultar `restaurant` si el dueño lo pide (en prod hoy el canal activo es `restaurant`)

**Prioridad:** P0
**Esfuerzo estimado:** 2.5 días (migración + seed 10 consultas 1d; frontend `AssistantChat` + `assistantApi.ts` + tests 1.5d)
**Dependencias:** HU-F5-01 (endpoint `ask`), HU-F5-09 (catalog con roles), Fase 4 del plan (frontend al final)
**Notas técnicas:**
- Migración: la `0019` ya es de F3 (`voice_ai`) → F5 es **`0020_assistant`** (directiva Jarvis; la spec menciona `0017`/`0019` en secciones distintas — la numeración final la define el árbol Alembic, ver Preguntas Abiertas).
- Seed: 10 consultas que DELEGAN en `delivery_service`/`owner_dashboard_service` (Spec Anchor §3.4: `sql_template` solo para consultas sin función existente).
- Frontend: `apps/web/src/components/AssistantChat.tsx` + `services/assistantApi.ts` + tipos; tests jest + RTL (patrón `DashboardOwner.test.tsx`).
- El catálogo no se hardcodea en frontend: las sugerencias vienen del endpoint (R8).

---

## 📊 Resumen de Historias

| ID | Historia | Criterio(s) Spec | Capa | Esfuerzo |
|----|----------|:----------------:|------|:--------:|
| HU-F5-01 | Pipeline NL2SQL controlado — top producto hoy con datos reales | CA-F5.1 | Backend | 3d |
| HU-F5-02 | Fechas relativas — "esta semana" / "el mes pasado" | CA-F5.2, CA-F5.3 | Backend | 1.5d |
| HU-F5-03 | Rechazo amable — fuera de catálogo con sugerencias (R5) | CA-F5.4 | Backend | 1d |
| HU-F5-04 | Anti-inyección SQL — el catálogo es el único SQL (R1) | CA-F5.7 | Backend | 1d |
| HU-F5-05 | Aislamiento multi-tenant (R2) | CA-F5.5 | Backend | 1d |
| HU-F5-06 | Auditoría total en `query_logs` (R4) | CA-F5.6 | Backend | 1.5d |
| HU-F5-07 | Modo degradado sin LLM key — fallback determinista (D2) | CA-F5.8 | Backend | 1d |
| HU-F5-08 | Validación de params — inválidos → 422 (R9) | CA-F5.9 | Backend | 0.5d |
| HU-F5-09 | Seguridad: 401/403, roles por consulta, rate limit 429 (R6/R7/R8) | CA-F5.10, CA-F5.11, CA-F5.14 | Backend | 1.5d |
| HU-F5-10 | Catálogo MVP (migración `0020_assistant`) + chat en `/panel` | CA-F5.12, CA-F5.13 | Back+Front | 2.5d |

| **Total** | | | | **15 días (≈3 semanas)** |
|-----------|---------|------------|----------|------------|
| Backend | | | | 13d |
| Frontend | | | | 1.5d (incluidos) + tests |

---

## 🔗 Dependencias entre historias

```
HU-F5-10 (parte 1: migración 0020_assistant + seed 10 consultas) [base de datos]
  │
  ├── HU-F5-01 (pipeline NL2SQL controlado — núcleo, reviviendo BaseSkill D3)
  │     ├── HU-F5-02 (fechas relativas — usa catálogo sales_by_zone/campaign_roas)
  │     ├── HU-F5-03 (fallback R5 — rechazo fuera de catálogo)
  │     ├── HU-F5-04 (anti-inyección — sanitize + bound params)
  │     ├── HU-F5-05 (aislamiento tenant R2 — inyección de :tenant_id)
  │     ├── HU-F5-06 (auditoría R4 — paso 7 del pipeline)
  │     ├── HU-F5-07 (modo degradado — LLMClient con fallback, ya prototipado en spike)
  │     ├── HU-F5-08 (validación params → 422 — paso 3 del pipeline)
  │     └── HU-F5-09 (seguridad — router + rate limit + roles)
  │
  └── HU-F5-10 (parte 2: frontend AssistantChat en /panel — depende de HU-F5-01 + HU-F5-09)
```

### Orden de implementación recomendado (alineado con plan spec §4)

1. **HU-F5-10 (parte 1)** — Migración `0020_assistant` + seed catálogo (Fase 1: verificar CA-F5.12 en QA)
2. **HU-F5-07** — LLMClient + fallback determinista (ya validado en spike; desbloquea el pipeline)
3. **HU-F5-01** — Núcleo: SkillLoader + DeliverySkill + AssistantService + LLM tool calling (Fase 2)
4. **HU-F5-02** — Fechas relativas (R9) — con el pipeline corriendo
5. **HU-F5-08** — Validación de params → 422 (paso 3)
6. **HU-F5-03** — Fallback "no entendí" + sugerencias (R5)
7. **HU-F5-04** — Anti-inyección (tests de seguridad, Fase 3)
8. **HU-F5-05** — Aislamiento multi-tenant (tests obligatorios CA-F5.5)
9. **HU-F5-06** — Auditoría `query_logs` + `GET /logs` (R4)
10. **HU-F5-09** — Router + rate limit + roles (401/403/429, Fase 3)
11. **HU-F5-10 (parte 2)** — Frontend `AssistantChat` en `/panel` (Fase 4) + QA CA-F5.1..14 (Fase 5)

> **Nota:** F5 es independiente de telefonía (spec §0: "puede ir en paralelo con F4"). La migración
> `0020_assistant` NO choca con la `0019` de F3 (voice_ai).

---

## 🎯 Cobertura de Criterios de Aceptación (Spec §3.6)

| Criterio | Caso | Historias que lo cubren |
|:--------:|------|-------------------------|
| CA-F5.1 | "¿cuál es el producto más vendido hoy por delivery?" → 200 + answer + data + catalog_query_used | HU-F5-01 |
| CA-F5.2 | "¿cuánto vendió la Zona 1 esta semana?" → ventas de la semana en curso | HU-F5-02 |
| CA-F5.3 | "¿qué campaña tuvo mejor ROAS el mes pasado?" → campaña de mayor ROAS | HU-F5-02 |
| CA-F5.4 | Fuera de catálogo → fallback amable con sugerencias, nunca SQL, `rejected=true` | HU-F5-03 |
| CA-F5.5 | Aislamiento: misma pregunta X-Tenant-ID A vs B → datos propios | HU-F5-05 |
| CA-F5.6 | Auditoría: 3 resueltas + 1 rechazada → 4 filas correctas; `GET /logs` admin | HU-F5-06 |
| CA-F5.7 | Inyección SQL (DROP/UNION/SELECT *) → rechazo R5 + log, BD intacta | HU-F5-04 |
| CA-F5.8 | Sin `llm_api_key` → fallback con sugerencias, sin 500 | HU-F5-07 |
| CA-F5.9 | Params inválidos (fecha "13/13/2026", `from > to`) → 422 con detalle | HU-F5-08 |
| CA-F5.10 | Rate limit excedido (11+ req/min) → 429 con Retry-After, por tenant | HU-F5-09 |
| CA-F5.11 | `GET /catalog` con rol viewer → solo consultas activas y permitidas | HU-F5-09 |
| CA-F5.12 | Catálogo MVP ≥8 consultas (10 seedeadas); 3 preguntas ejemplo resueltas | HU-F5-10 |
| CA-F5.13 | Frontend `/panel`: chat con sugerencias, carga y error amigable | HU-F5-10 |
| CA-F5.14 | Sin auth → 401; rol no permitido (staff) → 403 | HU-F5-09 |

---

## 🔍 Preguntas abiertas para Jarvis / Backend (a resolver en desarrollo)

1. **Numeración de migración**: la spec menciona `0017_assistant` (§3.2/§5) y `0019_assistant`
   (§3.1) en secciones distintas; la directiva aprobada dice **`0020_assistant`** (la `0019` ya es
   de F3 voice_ai). Confirmar la numeración final en el árbol Alembic al implementar.
2. **Canal activo en prod (hallazgo spike)**: el canal real es `restaurant` (salón) y delivery
   activo = 0 (DLV- E2E canceladas). ¿El catálogo MVP consulta solo `business_type=delivery` o se
   parametriza por consulta para poder responder también del canal salón? Las historias asumen
   parametrización (último criterio de HU-F5-10).
3. **Paginación de `GET /logs`**: la spec define filtros `from/to/rejected` pero no paginación.
   ¿Se requiere paginación en el MVP? Asumido: filtros + paginación básica (limit/offset).
4. **Fallback determinista vs LLM**: ¿el modo con LLM key usa el fallback por palabras clave solo
   ante error/timeout/sin tool match, o también como pre-filtro rápido? Asumido: LLM primero;
   fallback ante cualquiera de esos casos (nunca 500).
5. **`result_summary.first_rows`**: ¿cuántas filas se incluyen en el resumen del log? Asumido:
   top N (≤5) o `null` si no aplica — para no duplicar data sensible.

---

*Documento generado por PO Agent 📋 a partir de la Spec 08 (F5 — "Pregúntale al Sistema", v0.1,
APROBADA 2026-08-13) y del PoC validado (`spikes/f5-preguntale-al-sistema/`, eval 5/5), con
trazabilidad completa a CA-F5.1..14 y reglas R1..R9. Mismo patrón de formato que
`docs/backlog/gherkin-f3-recepcionista-ia.md`.*
