# SPEC 08 — F5 "Pregúntale al Sistema" (NL2SQL controlado)

- **Estado**: 🟢 **APROBADA (2026-08-13)** — aprobada por Ron para implementación (D1–D7 aprobadas, presupuesto S/5,000–8,000); sin código en el ERP aún. **PoC validado (SPIKE, 2026-08-13):** `spikes/f5-preguntale-al-sistema/` — VentasSkill sobre `BaseSkill` con function calling DeepSeek, **eval golden 5/5 (tool + data accuracy)**, fallback determinista 100%, demo read-only contra prod (S/494 de hoy).
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-12 (actualizada 2026-08-13: resultados del spike + aprobación Ron)
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (specs 03/04 como referencia de formato)
- **Esfuerzo estimado**: 3–5 semanas (MVP delivery: ~2–3 semanas; replicación a otros dominios: post-MVP)
- **Dependencia**: ninguna de telefonía — **puede ir en paralelo con F4**

---

## 0. Decisiones (D1–D7 — APROBADAS por Ron, 2026-08-13)

| # | Decisión | Acuerdo aprobado |
|---|---|---|
| D1 | Mecanismo de interpretación | **NL2SQL controlado vía tool calling**: el LLM recibe el catálogo como "tools" (id + descripción + esquema de params) y **elige** `query_catalog.id` + llena `params` tipados. **El LLM NUNCA escribe SQL.** Solo el motor ejecuta el `sql_template` del catálogo con parámetros vinculados. |
| D2 | Proveedor LLM | Usar la config ya existente del proyecto: `llm_provider="openai"`, `llm_model="gpt-4o"`, `llm_api_key` desde `.env` (`app/config.py`). Compatible con DeepSeek (API compatible OpenAI) cambiando `llm_provider/llm_model`. **Texto, no realtime.** Sin key configurada → modo degradado: respuestas de sugerencia sin llamada al LLM (nunca 500). |
| D3 | Capa de skills | **Revivir el puerto hexagonal `app/core/agents/base.py`** (deuda #8): `BaseSkill`/`AgentContext`/`SkillResult`/`SkillRegistry` ya diseñados. El catálogo de consultas se agrupa por skill: `DeliverySkill` (MVP) → luego `SalesSkill`, `InventorySkill`, `FinanceSkill`, `ReportSkill` (replicables sin tocar el contrato). |
| D4 | Alcance MVP | **Solo delivery** (consultas sobre métricas delivery ya existentes en `delivery_service.py` + `owner_dashboard_service.py`). Salón, inventario, contabilidad y recetas se agregan después como más skills/catálogo, sin cambios de contrato de `/assistant`. |
| D5 | Frescura de datos | **Respuesta siempre con dato actual, sin cache** (R3). Cada `ask` ejecuta la query en vivo contra PostgreSQL. El costo es asumido (volumen bajo: uso humano en panel). |
| D6 | Seguridad de acceso | Roles `admin/manager/viewer` (solo lectura, misma convención que el Panel del Dueño — Spec 04 D5/D6). Tenant scoping obligatorio con `get_tenant_id` (`core/tenant.py`). Rate limit Redis por tenant (`core/rate_limit.py`). Auditoría total en `query_logs`. |
| D7 | Resolución de fechas | Parámetros de fecha resueltos con el patrón `_resolve_dates` de `owner_dashboard_service.py` (default = últimos 30 días). Las fechas relativas del lenguaje natural ("hoy", "esta semana", "el mes pasado") las normaliza el **LLM a `date_from`/`date_to` (YYYY-MM-DD) dentro del esquema de params** — el motor solo acepta valores, jamás expresiones SQL. |

---

## 1. Contexto y objetivo

El dueño (Ron / El Segoviano) escribe en lenguaje natural en el panel ("¿cuál es el producto más
vendido hoy por delivery?", "¿cuánto vendió la Zona 1 esta semana?", "¿qué campaña tuvo mejor
ROAS el mes pasado?") → la IA interpreta la intención, **elige la consulta correcta de un
CATÁLOGO SEGURO** (tool calling / NL2SQL controlado, **sin SQL libre jamás**), la ejecuta contra
datos reales del ERP y responde al instante.

**Objetivo del MVP:** chat dentro del Panel del Dueño (`/panel`) que responda consultas de
**delivery** con datos reales, con aislamiento multi-tenant, auditoría de todo lo ejecutado y
rechazo amable de lo que no está en el catálogo. Posteriormente el mismo mecanismo se replica a
salón, inventario, contabilidad y recetas.

**Por qué existe:** el ERP ya tiene TODAS las métricas calculadas (Panel del Dueño, Spec 04) y una
capa de skills IA **diseñada pero muerta** (deuda #8). F5 revive esa capa y la conecta a un LLM,
convirtiendo un panel de indicadores en un **asistente conversacional de negocio** sin exponer SQL.

**Fuera de alcance MVP:** SQL libre, acciones de escritura (crear/borrar ventas, cambiar estados),
memoria conversacional multi-turno compleja, telefono/WhatsApp (F4), voz, realtime de audio.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-12)

### 2.1 La capa de skills YA está diseñada pero es código muerto (deuda #8)

| Componente | Ubicación | Estado verificado |
|---|---|---|
| Puerto hexagonal `BaseSkill` (ABC: `name`, `description`, `execute(context, params) → SkillResult`) | `app/core/agents/base.py` | ✅ Diseñado |
| `AgentContext` (tenant_id, user_id, language, extra) + `SkillResult` (success, data, error, metadata) | `app/core/agents/base.py` | ✅ Diseñado |
| `SkillRegistry` singleton (`register/get/list_skills/get_skills_context`) | `app/core/agents/base.py` | ✅ Diseñado |
| Skills concretas (Sales/Inventory/Finance/Report) | — | ☠️ **NO existen** (TO-DO en base.py) |
| SkillLoader (descubrimiento), AgenteOrquestador, tests, conexión LLM | — | ☠️ **NO existen** (TO-DO en base.py) |
| Imports de `app.core.agents` en `app/` | — | ☠️ **0 imports** fuera de `agents/__init__.py` (re-export) — verificado con grep |

**Conclusión R1:** el puerto es sólido (stateless, context explícito, registry singleton) y se
reutiliza tal cual. F5 = implementar el primer skill concreto (`DeliverySkill`), el loader, el
orquestador y la conexión LLM que la deuda #8 dejó pendientes.

### 2.2 Infraestructura de seguridad reutilizable (sin trabajo nuevo)

| Componente | Ubicación | Estado |
|---|---|---|
| `get_tenant_id` (X-Tenant-ID → fallback JWT `company_id` → 400) | `app/core/tenant.py` | ✅ Listo |
| `RateLimiter` Redis sliding-window + fallback in-memory (`get_rate_limiter`) | `app/core/rate_limit.py` | ✅ Listo (ya usado en públicos/checkout) |
| `require_role("admin","manager","viewer")` | `app/core/dependencies.py` | ✅ Listo (usado en dashboard) |
| JWT + refresh rotation (auth multitenant) | spec-auth-multitenant | ✅ Listo |

### 2.3 Las métricas delivery YA existen — son la base del catálogo inicial

| Métrica | Función | Ubicación | Detalle verificado |
|---|---|---|---|
| Resumen delivery (pedidos, GMV, fee_total, avg_delivery_min, cancelled) | `metrics_overview` | `app/services/delivery_service.py` L814 | Solo `status="delivered"` para GMV; filtro por rango con `datetime.combine`; tenant-scoped |
| ROAS/AOV por campaña | `metrics_campaigns` | `app/services/delivery_service.py` L773 | `roas = gmv/spend`, `aov = gmv/orders`; filtro canal; tenant-scoped |
| Panel completo dueño (KPIs, ventas por hora, por día, canales, top platos, pagos, zonas, embudo, comparativa, márgenes, alertas) | `get_owner_dashboard` | `app/services/owner_dashboard_service.py` | Reusa `metrics_overview`/`metrics_campaigns` (no duplica); `_resolve_dates` default 30 días; excluye anuladas; tenant-scoped |
| Top platos por cantidad vendida | `_top_platos` | `owner_dashboard_service.py` | `SaleItem` join `Sale`; `is_voided=False` |
| Ventas por zona | `_delivery_block.orders_by_zone` | `owner_dashboard_service.py` | `DeliveryZone.name` + count `DeliveryOrder` |
| Embudo por estado | `_delivery_block.funnel` | `owner_dashboard_service.py` | 6 estados del CHECK de delivery |
| Comparativa período vs previo | `_comparison` | `owner_dashboard_service.py` | Deltas `*_pct` |
| Márgenes por canal | `_margins_by_channel` | `owner_dashboard_service.py` | Costo vía recetas (average_cost), margen declarado |
| Endpoints owner (contrato existente) | `GET /api/v1/dashboard/owner` + `/owner/export` | `app/routers/dashboard.py` | Roles admin/manager/viewer; `date_from/date_to` opcionales |

**Conclusión R2:** el catálogo inicial NO inventa queries — envuelve funciones ya probadas y
tenant-scoped. La ejecución del catálogo puede delegar en estos servicios (menos SQL duplicado)
o usar `sql_template` parametrizados equivalentes; la decisión de implementación (Spec Anchor) es
**delegar en los servicios existentes** para el MVP y reservar `sql_template` para consultas nuevas
que no existan como función.

### 2.4 Frontend — dónde vive el chat

| Componente | Ubicación | Estado |
|---|---|---|
| Panel del Dueño | `apps/web/src/pages/DashboardOwner.tsx` (ruta `/panel`) | ✅ Existe (Spec 04) |
| API client del panel | `apps/web/src/services/dashboardApi.ts` + `types/dashboard.ts` | ✅ Existe |
| Tests frontend existentes | `apps/web/src/__tests__/DashboardOwner.test.tsx` | ✅ Existen |

**Conclusión R3:** el chat se agrega como componente dentro de `DashboardOwner` (o widget
independiente en la misma ruta) sin tocar el resto del panel.

### 2.5 Config LLM

- `app/config.py`: `llm_provider: str = "openai"`, `llm_model: str = "gpt-4o"`,
  `llm_api_key: Optional[str] = None` (desde `.env`). **No hay key configurada actualmente** →
  el sistema debe degradar elegante (ver R5 y CA-F5.8).

### 2.6 Hallazgos incidentales (no bloquean; documentados)

- El módulo `agents/__init__.py` ya documenta el plan de la deuda #8 (SkillLoader, skills
  concretas, rate limiting por tenant, extracción a servicio independiente con RabbitMQ si el
  consumo sube). F5 materializa ese plan — se mantiene la nota de "extraer a servicio/cola si el
  uso crece" como trabajo futuro.
- No existe tabla de auditoría de consultas hoy: `query_logs` es trabajo nuevo.
- Sin cache en el panel: consistente con R3 (dato actual).

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (MVP delivery):**
- **Migración `0020_assistant`** (cadena real verificada: `0017_whatsapp_bsuid` → `0018_call_records` → `0019_voice_ai` [F3, ya existe] → **`0020_assistant`** — la `0019` fue tomada por F3; corregido 2026-08-13): tablas `query_catalog` + `query_logs` + seed del catálogo delivery (≥8 consultas, §3.4).
- Revivir `app/core/agents/`: `SkillLoader` (registro declarativo) + `DeliverySkill` (implementa `BaseSkill` sobre `delivery_service`/`owner_dashboard_service`).
- `AssistantService` (pipeline: LLM intención → selección de catálogo → ejecución tenant-scoped → respuesta en español → auditoría) + `LLMClient` (tool calling, proveedor OpenAI/DeepSeek-compatible).
- Router `/api/v1/assistant`: `POST /ask`, `GET /catalog`, `GET /logs` (admin) + rate limit Redis por tenant.
- Frontend: chat en `/panel` (componente `AssistantChat` + `assistantApi.ts`), con sugerencias de catálogo y estados de carga/error.
- Tests: unitarios (selección, tenant scope, auditoría, rate limit, fallback, inyección) + aislamiento multi-tenant.

**NO INCLUYE (límites MVP):**
- Otras skills (sales/inventory/finance/report) → post-MVP, misma maquinaria.
- Acciones de escritura (crear ventas, cambiar estados, anular) → jamás en este MVP.
- SQL libre / pregunta abierta sin catálogo.
- Streaming WS, memoria multi-turno persistente, voz, WhatsApp (F4).

### 3.2 Modelo de datos (migración `0020_assistant` — borrador redactado, SIN commitear)

```sql
query_catalog (
  id serial PK,
  skill varchar(50) NOT NULL,                 -- 'delivery' (MVP); luego sales|inventory|finance|report
  name varchar(100) NOT NULL UNIQUE,          -- slug interno: 'top_products_delivery', 'sales_by_zone', ...
  description_es text NOT NULL,               -- para el LLM (tool description) y para el dueño
  sql_template text NOT NULL,                 -- SELECT parametrizado (solo lectura), con :params
  params jsonb NOT NULL DEFAULT '[]',         -- [{name, type: 'date'|'int'|'enum', required, description_es, allowed_values?}]
  allowed_roles jsonb NOT NULL DEFAULT '["admin","manager","viewer"]',
  tenant_scope bool NOT NULL DEFAULT true,    -- toda query filtrada por tenant_id (R2)
  active bool NOT NULL DEFAULT true,
  created_at/updated_at timestamptz,
  CHECK (jsonb_typeof(params) = 'array')
)

query_logs (
  id bigserial PK,
  tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  user_id int FK users(id) ON DELETE SET NULL,
  pregunta text NOT NULL,                     -- texto crudo del dueño (auditoría)
  query_catalog_id int FK query_catalog(id) ON DELETE SET NULL,  -- null = rechazado/fallback
  params jsonb,                               -- params finales ejecutados (auditoría)
  result_summary jsonb,                       -- {rows:int, total?:float, first_rows:int} resumen, NUNCA data completa
  tokens_used int,                            -- consumo LLM
  latency_ms int,                             -- end-to-end
  rejected bool NOT NULL DEFAULT false,       -- true si no matcheó catálogo (R5)
  created_at timestamptz NOT NULL DEFAULT now(),
  INDEX (tenant_id, created_at DESC)
)
```

**Notas de diseño:**
- `query_catalog.sql_template` es el **único** lugar donde existe SQL en todo el flujo. El usuario
  y el LLM jamás aportan SQL (D1). Params se vinculan con `SQLAlchemy text()` / bound params —
  nunca interpolación de strings.
- `tenant_scope=true` + `:tenant_id` como parámetro **siempre inyectado por el motor** desde
  `get_tenant_id` (R2), nunca por el LLM.
- `query_logs.result_summary` guarda solo resumen (filas/total) — la data completa va al cliente,
  no a la BD (evita duplicar datos sensibles en logs).
- `rejected=true` registra también las preguntas no resueltas → insumo para ampliar el catálogo.

### 3.3 Contratos

#### 3.3.1 API REST (auth + tenant, roles admin/manager/viewer — mismo patrón Spec 04)

```
POST /api/v1/assistant/ask
  Request:  { question: "¿cuál es el producto más vendido hoy por delivery?" }
  → 200 { answer: "Hoy el producto más vendido por delivery fue el Lomo Saltado
                   (12 pedidos, S/ 486.00).",
           data: {...},                          // data real de la consulta (top N, etc.)
           catalog_query_used: { id: 3, name: "top_products_delivery", skill: "delivery" },
           params: { date_from: "2026-08-12", date_to: "2026-08-12", limit: 5 } }
  → 200 (fallback R5) { answer: "Aún no sé responder eso. Puedo ayudarte con: …",
           catalog_query_used: null, data: null,
           suggestions: ["Top productos delivery", "Ventas por zona", "ROAS por campaña"] }
  → 422 params inválidos (fecha malformada, zona inexistente) con detalle
  → 429 rate limit excedido (Retry-After)  |  401/403 sin auth/rol

GET /api/v1/assistant/catalog
  → 200 [{ id, skill, name, description_es, params_schema }]   // solo active + rol permitido
  Uso: poblar sugerencias del chat y el contexto de tools del LLM.

GET /api/v1/assistant/logs?from=&to=&rejected=
  → 200 [{ created_at, pregunta, query_catalog_id, params, result_summary,
           tokens_used, latency_ms, rejected }]                 // solo admin (auditoría R4)

WS /api/v1/assistant/ws   (opcional, Fase 2 — streaming de tokens; NO en MVP)
```

#### 3.3.2 Pipeline interno (AssistantService)

```
question ─► 1. sanitize (límite de chars, idioma es)
         ─► 2. LLM tool calling: tools = catálogo activo del tenant/rol
                → elige query_catalog_id + params (fechas normalizadas a ISO)
                → sin tool match ⇒ R5 (rechazo amable + sugerencias)
         ─► 3. validar params contra schema (tipos, required, allowed_values, rango fechas)
         ─► 4. inyectar :tenant_id (get_tenant_id) — R2
         ─► 5. ejecutar skill (DeliverySkill → servicios existentes o sql_template)
         ─► 6. formatear answer en español (template por consulta + data)
         ─► 7. escribir query_logs (R4) — misma request
         ─► 8. responder {answer, data, catalog_query_used, params}
```

### 3.4 Catálogo de consultas MVP (≥8, delivery — seed de `0020_assistant`)

| # | name (slug) | description_es (al LLM/dueño) | params | Fuente (función existente) |
|---|---|---|---|---|
| 1 | `top_products_delivery` | "Producto(s) más vendido(s) por delivery en un rango de fechas" | date_from, date_to, limit(int, default 5) | `_top_platos` ⚠️ sin filtro de canal hoy (ver nota delegación) |
| 2 | `sales_by_zone` | "Ventas/pedidos por zona de delivery en un rango" | date_from, date_to | `_delivery_block.orders_by_zone` |
| 3 | `campaign_roas` | "ROAS, AOV, GMV e inversión por campaña (canal opcional)" | date_from, date_to, channel(enum: meta\|google\|tiktok\|other, opcional) | `metrics_campaigns` |
| 4 | `delivery_overview` | "Resumen delivery: pedidos, GMV, fees, tiempo medio de entrega" | date_from, date_to | `metrics_overview` |
| 5 | `orders_by_status` | "Pedidos delivery por estado (embudo)" | date_from, date_to | `_delivery_block.funnel` |
| 6 | `avg_ticket_delivery` | "Ticket promedio de delivery" | date_from, date_to | `_kpis`/`_avg_ticket_by` (canal delivery) |
| 7 | `sales_by_hour_delivery` | "Ventas delivery por hora (0–23)" | date_from, date_to | `_sales_by_hour` (canal delivery) |
| 8 | `comparison_week` | "Comparativa de ventas/pedidos/ticket/%delivery vs período previo" | date_from, date_to | `_comparison` ⚠️ compara totales, no delivery-only (ver nota delegación) |
| 9 | `delivery_margins` | "Ingresos, costo y margen % del canal delivery" | date_from, date_to | `_margins_by_channel` (canal delivery) |
| 10 | `sales_by_channel` | "Ventas por canal (salón / para llevar / delivery)" | date_from, date_to | `_channels` |

- Las 10 cubren las 8+ exigidas y responden las 3 preguntas de ejemplo del contexto.
- Los `sql_template` equivalentes se escriben **solo si** no hay función existente que delegar;
  la implementación prioriza delegar en `delivery_service`/`owner_dashboard_service` (misma
  fórmula, cero divergencia) — decisión Spec Anchor.
- **Canal explícito (hallazgo spike 2026-08-13)**: en PROD el canal activo es `restaurant`
  (salón: S/ 494 en 12 ventas hoy); delivery real = 0 (los DLV- son E2E canceladas). Las 10
  consultas del catálogo filtran **explícitamente el canal `delivery`**
  (`RestaurantSale.order_type='delivery'` / `DeliveryOrder`), parametrizado en el seed — sin
  ese filtro devolverían datos del salón. Si delivery es 0, la IA responde "0 ventas" (R1:
  nunca inventa ni mezcla canales).
- **Guarda `sale_date = CURRENT_DATE` (bug del spike, §5 README)**: fecha ausente
  (`None`/`""` saneada por el LLM) NO debe omitir el filtro de fecha — el bug devolvía TODAS
  las ventas. El motor fija `sale_date = CURRENT_DATE` cuando el rango no viene; guarda
  obligatoria en todo `sql_template` con rango opcional.
- **Delegación verificada (2026-08-13)**: 8/10 consultas delegan directo en funciones
  existentes. Sin función delegable hoy: **#1 `top_products_delivery`** (`_top_platos` no
  filtra `order_type`) y **#8 `comparison_week`** (`_comparison` compara totales; solo
  `delivery_pct` es delta de share) → requieren `sql_template` nuevo con filtro
  `order_type='delivery'` o variante en `owner_dashboard_service`. #9 `delivery_margins`
  delega componiendo `_channels` + `_margins_by_channel` (2 llamadas).

### 3.5 Reglas de negocio

| # | Regla |
|---|---|
| R1 | **SOLO catálogo**: el motor ejecuta únicamente `query_catalog.sql_template` con params vinculados. El LLM elige id + params; el usuario/LLM jamás aportan SQL. Intento de inyección ("...; DROP TABLE", "dime todo de users") → rechazo R5, log `rejected=true` (CA-F5.7) |
| R2 | **Siempre tenant scope**: `:tenant_id` lo inyecta el motor desde `get_tenant_id` en TODA query (`tenant_scope=true`). Tests de aislamiento obligatorios (CA-F5.3) |
| R3 | **Dato actual, sin cache**: cada `ask` ejecuta contra PostgreSQL en vivo. Sin capa de cache |
| R4 | **Auditoría**: toda pregunta (resuelta o no) se registra en `query_logs` (pregunta, query_catalog_id, params, resumen, tokens, latencia, rejected). `GET /logs` solo admin |
| R5 | **Fallback "no entendí"**: sin match de catálogo o params inválidos → respuesta amable con sugerencias del catálogo (`catalog_query_used: null`). Sin LLM key → mismo fallback (nunca 500) |
| R6 | **Rate limit** Redis por tenant (`core/rate_limit.py`): propuesto 10 req/min por tenant en `/ask` (ajustable, mismo orden que checkout público) → 429 con Retry-After |
| R7 | **Solo lectura**: roles admin/manager/viewer; `sql_template` restringido a SELECT; sin endpoints de escritura en el asistente |
| R8 | **Roles por consulta**: `query_catalog.allowed_roles` filtra qué consultas ve el LLM y el dueño por rol |
| R9 | **Fechas**: el LLM normaliza lenguaje natural → `date_from/date_to` ISO; el motor valida formato y `from ≤ to` (patrón `_resolve_dates`, default 30 días) |

### 3.6 Criterios de aceptación (MVP)

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F5.1 | "¿cuál es el producto más vendido hoy por delivery?" | 200 con `answer` en español + `data` real (top platos delivery de hoy, tenant-scoped) + `catalog_query_used=top_products_delivery` + params correctos |
| CA-F5.2 | "¿cuánto vendió la Zona 1 esta semana?" | 200 con ventas/pedidos de la Zona 1 de la semana en curso (rango resuelto por el LLM) |
| CA-F5.3 | "¿qué campaña tuvo mejor ROAS el mes pasado?" | 200 con la campaña de mayor ROAS del mes anterior + `data` de campañas |
| CA-F5.4 | Pregunta fuera de catálogo ("¿cuál es el apellido del dueño?", "borra la venta 5", "dame SQL de todo") | 200 fallback amable con sugerencias (`catalog_query_used: null`); **nunca** se ejecuta SQL; `query_logs.rejected=true` |
| CA-F5.5 | Aislamiento: misma pregunta con X-Tenant-ID A vs B | Cada tenant ve solo sus datos; consulta de datos cross-tenant imposible (R2) |
| CA-F5.6 | Auditoría: 3 preguntas resueltas + 1 rechazada | `query_logs` con 4 filas: pregunta cruda, query_catalog_id, params finales, result_summary, tokens, latencia, rejected correctos; `GET /logs` (admin) los expone |
| CA-F5.7 | Inyección SQL ("...; DROP TABLE sales--", "SELECT * FROM users") | Rechazo R5 + log `rejected=true`; BD intacta; sin rastro de SQL del usuario en ejecución |
| CA-F5.8 | Sin `llm_api_key` configurada | `/ask` responde fallback con sugerencias (sin 500, sin timeout colgado) |
| CA-F5.9 | Params inválidos (fecha "13/13/2026", `date_from > date_to`) | 422 con detalle del parámetro |
| CA-F5.10 | Rate limit excedido (11+ req/min) | 429 con `Retry-After`; el límite es por tenant (tenant A no bloquea a B) |
| CA-F5.11 | `GET /api/v1/assistant/catalog` con rol viewer | 200 solo con consultas `active` y permitidas para el rol |
| CA-F5.12 | Catálogo MVP | ≥8 consultas delivery seedeadas y ejecutables; las 3 preguntas de ejemplo del contexto resueltas con datos reales |
| CA-F5.13 | Frontend `/panel` | Chat visible en el Panel del Dueño: pregunta → respuesta + dato; sugerencias de catálogo; estado de carga; error amigable |
| CA-F5.14 | Sin auth en `/assistant/*` | 401; con rol no permitido (ej. `staff` sin viewer) → 403 |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

1. **Fase 1 — Migración**: `0020_assistant` (query_catalog + query_logs) + seed catálogo delivery (10 consultas). `alembic upgrade head` en QA; verificar CA-F5.12 (catálogo).
2. **Fase 2 — Núcleo backend**: `SkillLoader` + `DeliverySkill` (sobre `delivery_service`/`owner_dashboard_service`); `AssistantService` pipeline (sanitize → LLM tool calling → validar params → inyectar tenant → ejecutar → formatear → auditar); `LLMClient` (OpenAI/DeepSeek-compatible, tool calling, timeout, sin key → fallback). Tests unitarios.
3. **Fase 3 — Router + seguridad**: `POST /ask`, `GET /catalog`, `GET /logs` (admin); rate limit Redis por tenant (R6); roles (R8); validación 422/429. Tests de aislamiento (CA-F5.5) e inyección (CA-F5.7).
4. **Fase 4 — Frontend**: `AssistantChat` en `/panel` (DashboardOwner) + `assistantApi.ts` + tipos; sugerencias desde `/catalog`; estados de carga/error; tests (jest + RTL).
5. **Fase 5 — QA + deploy**: ejecutar CA-F5.1–CA-F5.14 en QA; `./deploy.sh --env prod` con backup `.bak-<fecha>` (patrón spec 01/03).
6. **Post-MVP (replicación)**: `SalesSkill`/`InventorySkill`/`FinanceSkill`/`ReportSkill` + ampliar catálogo (salón, inventario, contabilidad, recetas) — sin cambios de contrato `/assistant`; evaluar streaming WS y cola RabbitMQ si el uso crece.

---

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-13 (APROBACIÓN RON + validación de implementación)**: spec aprobada por Ron
  (D1–D7 APROBADAS, presupuesto S/5,000–8,000) → estado 🟢 APROBADA. Ajustes validados:
  - **Migración renombrada a `0020_assistant`**: la `0019` ya está tomada por F3
    (`0019_voice_ai.py`, down_revision `0018_call_records`, verificada en código). Cadena:
    `0018_call_records → 0019_voice_ai → 0020_assistant`.
  - **Catálogo parametriza canal `delivery` explícitamente** (§3.4): en PROD el canal activo
    es `restaurant` (salón); delivery real = 0 → sin filtro por canal, las 10 consultas
    devolverían datos del salón. Seed con `order_type='delivery'` + filtro por estado.
  - **Guarda `sale_date = CURRENT_DATE`** (bug del spike: `fecha=None` devolvía TODAS las
    ventas) documentada en §3.4 — el motor fija CURRENT_DATE ante rango ausente.
  - **Delegación verificada**: 8/10 consultas delegan en `delivery_service` /
    `owner_dashboard_service`; **#1 `top_products_delivery` y #8 `comparison_week` NO tienen
    función delegable delivery-only** (requieren `sql_template` nuevo o variante); #9
    compone `_channels` + `_margins_by_channel`.
  - **Tool calling**: 10 tools del catálogo caben holgadas en contexto (~2–3k tokens de
    descripciones; DeepSeek/GPT-4o ≥ 8k) — descripciones de 1–2 frases, params tipados y
    validación server-side; si el catálogo supera ~20–30 tools, chunking por skill
    (selección en 2 etapas: skill → consulta).

- **2026-08-13 (SPIKE PoC — validación de arquitectura, aprobado por Ron)**: se ejecutó el spike
  `spikes/f5-preguntale-al-sistema/` (commiteado a main `ac13d31`) con resultados que **confirman
  las decisiones D1–D7**:
  - **VentasSkill mínimo implementado** sobre `BaseSkill` (sin tocar `app/core/agents/base.py`):
    3 tools SOLO LECTURA (`ventas_del_dia`, `top_productos_dia`, `ventas_por_zona_dia`), catálogo
    cerrado con validación de args (solo keys del schema, strings vacíos → None).
  - **Function calling con DeepSeek real** (`deepseek-v4-flash`, API compatible OpenAI): eligió la
    tool correcta **5/5** solo con las descripciones (~2.4s). **Fallback determinista por palabras
    clave: 100% (5/5) a 35–44ms** → respaldo de degradación elegante confirmado (R5/CA-F5.8).
  - **Eval golden (Bloque C en miniatura)**: 5 golden queries con respuesta esperada calculada
    contra la BD real → **tool accuracy 100% + data accuracy 100%** en ambos modos (fallback y LLM).
  - **Demo read-only contra PROD**: "¿cuánto vendimos hoy en el salón?" → S/ 494 en 12 ventas
    (restaurant, 2026-08-13); "¿qué plato se vendió más?" → top real con fees; "¿ayer?" → delivery
    S/ 0 (correcto). Confirma que las tools SELECT puro son seguras contra prod.
  - **Hallazgo de canal**: en prod el canal activo es `restaurant` (salón); delivery activo = 0
    (los DLV- son E2E canceladas). Las tools del MVP deben parametrizar `business_type`
    (delivery|restaurant) — ver §3.4 (catálogo por canal).
  - **Bug real corregido en el spike**: `fecha=None` no filtraba por CURRENT_DATE (devolvía todas
    las ventas) → `sale_date = CURRENT_DATE`. El MVP debe incluir esta guarda en `sql_template`.
  - **Pendiente**: aprobación de Ron (decisiones D1–D7) para implementar en el ERP.

- **2026-08-12 (v0.1)**: spec creada por architecture-agent + backend-dev + qa (validación técnica
  JARVIS). Fase R completa — verificado en código:
  - `app/core/agents/base.py` leído completo: puerto hexagonal diseñado (BaseSkill/AgentContext/
    SkillResult/SkillRegistry singleton), TO-DOs explícitos (SalesSkill/InventorySkill/FinanceSkill/
    ReportSkill, SkillLoader, AgenteOrquestador, tests, conexión LLM); grep confirma **0 imports**
    en `app/` (solo re-export en `agents/__init__.py`) → ☠️ código muerto confirmado.
  - `core/tenant.py` (`get_tenant_id`: X-Tenant-ID → JWT fallback → 400) y `core/rate_limit.py`
    (RateLimiter Redis sliding-window + fallback in-memory, `get_rate_limiter`) verificados → listos.
  - `owner_dashboard_service.py` y `delivery_service.py` verificados: `metrics_overview`,
    `metrics_campaigns` (ROAS=gmv/spend, AOV), `get_owner_dashboard` (KPIs, horas, canales, top
    platos, zonas, embudo, comparativa, márgenes, alertas) — todas tenant-scoped, patrón
    `_resolve_dates` (default 30 días) → base del catálogo MVP (10 consultas, ≥8 exigidas).
  - `routers/dashboard.py` verificado: `GET /api/v1/dashboard/owner` + `/owner/export`, roles
    admin/manager/viewer → patrón de contrato para `/assistant`.
  - Config LLM verificada (`app/config.py`): `llm_provider="openai"`, `llm_model="gpt-4o"`,
    `llm_api_key` opcional; **sin key configurada hoy** → diseño degrada elegante (R5/CA-F5.8).
  - Frontend verificado: `DashboardOwner.tsx` (ruta `/panel`), `dashboardApi.ts`,
    `types/dashboard.ts` → punto de integración del chat.
  - Borrador de migración `0017_assistant` + modelo de datos redactados durante R/P — **SIN
    commitear**, a la espera de aprobación de esta spec (Spec Anchor: spec primero).
  - **Pendiente**: aprobación de Ron (decisiones D1–D7). No hay código implementado en esta spec.

---

## 6. Referencias

- Spec 03 (delivery/dark kitchen — métricas ROAS/AOV/GMV y patrones de seguridad/rate limit):
  `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Spec 04 (Panel del Dueño — métricas ejecutivas, roles D5/D6, patrón `_resolve_dates`):
  `docs/specs/04-panel-indicadores/spec-panel-dueño.md`
- Puerto hexagonal de skills (deuda #8, código muerto a revivir):
  `apps/backend/app/core/agents/base.py` + `apps/backend/app/core/agents/__init__.py`
- Tenant scoping: `apps/backend/app/core/tenant.py` · Rate limiting: `apps/backend/app/core/rate_limit.py`
- Servicios base del catálogo: `apps/backend/app/services/delivery_service.py` (L773/L814),
  `apps/backend/app/services/owner_dashboard_service.py`
- Router de referencia: `apps/backend/app/routers/dashboard.py` · Config LLM: `apps/backend/app/config.py`
- Frontend: `apps/web/src/pages/DashboardOwner.tsx`, `apps/web/src/services/dashboardApi.ts`
- Specs index: `docs/specs/README.md`
