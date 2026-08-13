# SPEC 05 — Franquicia Conectada (multi-sucursal / F4)

- **Estado**: 🟡 **PROPUESTA (2026-08-12)** — Fase R verificada en código; D-1 pendiente de aprobación por Ron; borradores SIN commitear (Spec Anchor: spec primero)
- **Proyecto**: IaaS-RonSys — ERP SaaS (cliente: El Segoviano)
- **Alcance**: multi-tenant existente → N sucursales operando sobre el mismo motor (online + WhatsApp + llamadas por sucursal, monitoreo central del dueño)
- **Fecha**: 2026-08-12
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (specs 03/04 como referencia de formato)

---

## 0. Decisiones (D1-D5 — propuestas; D-1 es la decisión clave, PENDIENTE de Ron)

| # | Decisión | Acuerdo final (propuesta) |
|---|---|---|
| D1 | **Modelo de sucursal** | **Tabla `branches` hija del tenant** (NO tenant separado por sucursal). Análisis de trade-offs y justificación en §0.1. ⚠️ **PENDIENTE aprobación Ron.** |
| D2 | Teléfono/DID por sucursal | Cada sucursal tiene `phone` (línea/salida) + `did` (número entrante). El call-bridge de F2/F3 resuelve `incoming number → branch` y registra la llamada con `branch_id`. Config de salida (WhatsApp/alertas) por branch vía settings (R4). |
| D3 | Tablet de sucursal (modo kiosko) | Misma app web (React) en modo kiosko: **token kiosko** (JWT con `tenant_id` + `branch_id` fijos, revocable) — sin login complejo, sin navegación global. Pantalla única: kanban de cocina + pedidos online/WhatsApp/llamadas de SOLO esa branch. |
| D4 | `branch_id` en tablas de negocio | **Nullable en Fase 4** — las ventas legacy quedan `NULL` y el agregado del dueño las sigue viendo ("sin sucursal"); las operaciones nuevas de sucursal exigen `branch_id`. Análisis de impacto migratorio en §3.2. |
| D5 | House service (instalación por sucursal) | Cotizable **aparte** (referencia S/2.000 del benchmark, ver §6). Incluye: tablet + configuración DID + token kiosko + onboarding de menú/horarios/settings de la branch. Esfuerzo plataforma: 3-5 semanas (ver §4). |

### 0.1 D-1 — Análisis: ¿sucursal = nuevo tenant (`Company`) o tabla `branches`?

**Opción A — Sucursal = nuevo tenant (`Company`)**

| Pro | Contra |
|---|---|
| Aislamiento físico de datos ya probado (multi-tenant) | El dueño quiere ver **TODO en un panel** → requiere rol "owner multi-tenant" (NO existe: el JWT lleva UN `company_id` y los usuarios pertenecen a UN tenant) |
| Settings por tenant (patrón D-03) sin cambios | Catálogo/menú de marca compartido se duplicaría o habría que sincronizar |
| Superadmin ya crea companies | **Contabilidad fragmentada**: cada sucursal tendría plan de cuentas/kárdex propio → imposible consolidar por RUC sin otra capa |
| | Rompe el modelo mental "1 tenant = 1 negocio legal" y obliga a tocar auth/JWT/roles (riesgo alto sobre el core) |

**Opción B — Tabla `branches` hija del tenant (RECOMENDADA)**

| Pro | Contra |
|---|---|
| El tenant sigue siendo la unidad contable/legal (un RUC, un plan de cuentas, un kárdex): la franquicia consolida **naturalmente** | Toda query de negocio (sales/delivery/kitchen/calls) toca `branch_id` → migración + filtros nuevos |
| El dueño ve TODO en un panel: el owner_dashboard existente (spec 04) se extiende por **dimensión sucursal** (filtro/desglose), sin nueva auth | `ws_manager` pasa a agrupar por clave compuesta `(tenant_id, branch_id)` |
| Menú/catálogo único por tenant con disponibilidad por branch (settings heredables con override, R4) | El aislamiento entre sucursales es **lógico** (filtros R1), no físico |
| JWT actual NO cambia (payload `tenant_id` + `branch_id` opcional); superadmin intacto | — |
| Alta de sucursal en minutos (CA-F4-7): solo fila `branches` + DID + token kiosko, sin crear tenant | — |

**Decisión propuesta: Opción B — tabla `branches`.** Justificación: (1) el requisito central del dueño ("ver todo en un panel") exige datos del **mismo tenant** — la Opción A lo convierte en problema de auth multi-tenant que hoy no existe; (2) la franquicia emite con **un solo RUC**: la consolidación contable (ventas → kárdex → asientos, motor existente) solo funciona si las sucursales comparten tenant; (3) menor impacto: no toca auth/JWT/roles/tenant middleware; (4) el aislamiento operativo que sí importa (la sucursal B no ve pedidos de A) se garantiza por reglas de filtrado (R1) + separación de dispositivos (cada tablet tiene su `branch_id` en el token), no por aislamiento físico que aquí no aporta (no hay sub-empresas legales por sucursal).

---

## 1. Contexto y objetivo

El modelo ya funciona en **1 local** (El Segoviano, tenant 1): delivery nocturno (spec 03), cocina en
tiempo real, panel del dueño (spec 04), WhatsApp (Fase B spec 03). **F4 "Franquicia Conectada"** es el
salto a **N sucursales** con la misma plataforma:

- **Tablet/pantalla por sucursal** con sus propios pedidos en tiempo real (online + WhatsApp + llamadas).
- **Monitoreo central del dueño**: pedidos, ventas, demoras, llamadas atendidas/perdidas **por sucursal**.
- **Cada sucursal con su número** y enrutamiento de llamadas al local correcto (DID → branch).
- **House service**: instalación por sucursal (referencia S/2.000 del benchmark, cotizable aparte — D5).

**Objetivo de F4:** que abrir una sucursal nueva sea **configuración, no desarrollo** (CA-F4-7: alta en
minutos), manteniendo una sola contabilidad (RUC único), un panel centralizado del dueño y aislamiento
operativo por sucursal.

**Fuera de alcance F4:** sucursales como personas jurídicas separadas (multi-RUC → multi-tenant real,
futuro); apps móviles nativas (la tablet usa la misma web); central de llamadas multi-agente (solo
enrutamiento por DID + registro); inventario/stock por sucursal separado (se comparte el kárdex del
tenant — decisión contable, ver §6).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-12)

### 2.1 Lo que YA existe y se reutiliza

| Componente | Ubicación | Estado |
|---|---|---|
| Multi-tenant: `Company` es el tenant; `get_tenant_id` resuelve X-Tenant-ID con fallback JWT (`payload.company_id`) | `models/accounting.py` L50, `core/tenant.py` | ✅ Listo |
| Settings por tenant en `companies.settings` (JSONB, patrón D-03: DeliverySettings, WhatsAppSettings, branding) | `models/accounting.py`, `routers/setup.py` | ✅ Listo — base para override por branch |
| Realtime por tenant: `WsManager` agrupa `{tenant_id: [WebSocket]}` con `broadcast_to_kitchen`/`broadcast_to_waiter` | `core/ws_manager.py` | ✅ Listo — requiere extender a `branch_id` (clave compuesta) |
| Panel del dueño: `GET /api/v1/dashboard/owner` + export CSV/PDF; `owner_dashboard_service` | `routers/dashboard.py`, `services/owner_dashboard_service.py` | ✅ Listo — requiere dimensión sucursal |
| Panel superadmin: CRUD de companies/usuarios multi-tenant | `routers/superadmin.py` | ✅ Listo (NO se usa por sucursal — D-1) |
| Delivery/cocina: `delivery_orders`, `kitchen_orders`, `sales` con `tenant_id` + índices por tenant | `models/delivery.py`, `models/restaurant.py`, `models/sales.py` | ✅ Listo — requieren `branch_id` nullable |
| Frontend: `DeliveryPage.tsx`, `KitchenKanban.tsx`, `DashboardOwner.tsx` (misma app web por tenant) | `apps/web/src/pages/` | ✅ Listo — la tablet reutiliza estas páginas con `branch_id` |
| Motor contable: ventas → kárdex → asiento por tenant (consolidación por RUC) | `services/sales_service.py` | ✅ Listo — argumento clave para D-1 |

### 2.2 Lo que NO existe (trabajo nuevo de F4)

| Gap | Detalle |
|---|---|
| **Concepto de sucursal** | NO hay tabla `branches` ni campo `branch` en `delivery_orders`/`kitchen_orders`/`sales`/`call_records` (verificado: todos los modelos solo tienen `tenant_id`). Es la brecha central (D-1). |
| WS por sucursal | `ws_manager` agrupa SOLO por `tenant_id` — dos sucursales del mismo tenant compartirían la misma pantalla de cocina (fuga de pedidos entre sucursales). |
| Enrutamiento de llamadas por número | F2/F3 (calls) hoy conciben el trunk **por negocio**; para N sucursales se necesita **DID por sucursal** + mapeo `incoming number → branch` en el call-bridge, y que el registro de la llamada lleve `branch_id`. |
| Panel dueño por sucursal | `owner_dashboard_service` agrega por tenant; no hay filtro/desglose por branch (pedidos, ventas, demoras, llamadas atendidas/perdidas por sucursal). |
| Modo kiosko | No existe token de dispositivo/sucursal; hoy toda pantalla exige login completo + navegación global. |
| Alta de sucursal | No hay CRUD de branches ni contrato de configuración rápida (DID + token + settings heredados). |

### 2.3 Restricciones verificadas

- `sales`/`delivery_orders`/`kitchen_orders` tienen `tenant_id` NOT NULL con FKs a `companies` — la
  columna `branch_id` nueva será **nullable** (D4) para no romper data legacy ni el motor contable.
- `companies.slug` es UNIQUE a nivel global — si en el futuro una sucursal requiere landing propia,
  el slug debe ser `tenant + branch` (diferido; F4 usa una sola landing por tenant).
- El `UniqueConstraint("tenant_id", "name")` de zonas/campañas y `uq_*_tenant_*` existentes sugieren
  el mismo patrón para `branches`: UNIQUE por tenant.

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (F4):**
- Migración `0017_branches` (§3.2): tabla `branches` + `branch_id` nullable en `delivery_orders`/`kitchen_orders`/`sales` (y contrato para `call_records` cuando F2/F3 exista).
- CRUD `/api/v1/branches` + endpoint de settings por branch (merge con `companies.settings`, R4).
- WS por sucursal: clave compuesta `(tenant_id, branch_id)` en `ws_manager`; ruta `/ws/kitchen/{tenant}/{branch}`.
- Modo kiosko: token kiosko por branch (JWT con tenant+branch fijos, revocable) + pantalla tablet.
- Panel dueño: dimensión sucursal — agregado (todas) + desglose/filtro por branch (pedidos, ventas, demoras, llamadas atendidas/perdidas).
- Enrutamiento DID→branch: mapeo en el call-bridge (F2/F3) + registro de llamada con `branch_id`.

**NO INCLUYE (límites F4):**
- Multi-RUC (sucursales como empresas separadas) — eso es multi-tenant real, otro proyecto.
- Central telefónica multi-agente, IVR avanzado, grabaciones (depende del alcance de F2/F3).
- Stock/almacén separado por sucursal (el kárdex es único por tenant por decisión contable D-1).
- App nativa para tablet (se usa la misma web en modo kiosko).

### 3.2 Modelo de datos (migración `0017_branches` — borrador redactado, SIN commitear)

```sql
branches (
  id serial PK,
  tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  name varchar(120) NOT NULL,                 -- "Sucursal SJL", "Local Centro", ...
  code varchar(20),                           -- código corto interno (SJL-01) — UNIQUE por tenant
  address varchar(300),
  phone varchar(20),                          -- teléfono de línea (contacto/salida)
  did varchar(20),                            -- número entrante (DID) → enrutamiento de llamadas (D2)
  settings jsonb,                             -- override de companies.settings (patrón D-03, R4)
  active bool NOT NULL DEFAULT true,
  kiosk_token_hash varchar(64),               -- hash del token kiosko activo (D3; revocable)
  created_at/updated_at timestamptz,
  UNIQUE (tenant_id, code),
  UNIQUE (tenant_id, did) NULLS NOT DISTINCT, -- un DID no se comparte entre sucursales del tenant
  CHECK (char_length(name) > 0)
)

-- Columnas nuevas (nullable — D4, análisis de impacto migratorio abajo)
delivery_orders:  branch_id int FK branches(id) ON DELETE SET NULL,
                  Index idx_delivery_orders_tenant_branch_status (tenant_id, branch_id, status)
kitchen_orders:   branch_id int FK branches(id) ON DELETE SET NULL,
                  Index idx_kitchen_orders_tenant_branch_status (tenant_id, branch_id, status)
sales:            branch_id int FK branches(id) ON DELETE SET NULL,
                  Index idx_sales_tenant_branch_date (tenant_id, branch_id, sale_date)
call_records:     branch_id int FK branches(id) ON DELETE SET NULL   -- contrato reservado para F2/F3
```

**Análisis de impacto migratorio (D4):**
- `branch_id` **nullable** → `0017_branches` no bloquea ni requiere backfill: las filas legacy quedan
  `NULL` y el panel del dueño las agrupa como "sin sucursal" hasta reasignación opcional (script
  `UPDATE ... SET branch_id = X WHERE ...` por sucursal real, manual, fuera del alcance de la migración).
- `ON DELETE SET NULL`: borrar una branch no destruye su historial de ventas/pedidos (contabilidad intacta).
- Los CHECK/constraints existentes por tenant (`tenant_id` NOT NULL) no cambian — solo se agrega dimensión.
- Contrato de integridad: cualquier operación NUEVA originada en una sucursal (checkout delivery con
  `branch_id`, comanda de cocina, llamada entrante) exige `branch_id` NOT NULL a nivel de servicio
  (validación 400 si falta), aunque la columna sea nullable a nivel BD (R6).

### 3.3 Contratos

#### 3.3.1 CRUD de sucursales (staff — rol admin/owner del tenant)

```
CRUD  /api/v1/branches
  GET    → 200 [{id, tenant_id, name, code, address, phone, did, settings, active}]
  POST   → 201 (body: name, code, address?, phone?, did?, settings?)  — valida UNIQUE (tenant, code|did)
  PATCH  /{id}  → 200 (campos parciales; did se reasigna si cambia → call-bridge se re-suscribe)
  DELETE /{id}  → 204 (branch_id en filas de negocio → SET NULL; si hay pedidos activos → 409 con conteo)
GET/PATCH /api/v1/branches/{id}/settings  → lee/escribe el override JSONB (merge con companies.settings, R4)
POST  /api/v1/branches/{id}/kiosk-token   → genera/rota el token kiosko (D3); revoca el anterior (hash)
```

#### 3.3.2 Panel del dueño — dimensión sucursal (extiende spec 04)

```
GET /api/v1/dashboard/owner?date_from=&date_to=&branch_id=      ← branch_id OPCIONAL
  sin branch_id   → agregado de TODAS las sucursales + desglose por branch (array branches:[{id,name,orders,gmv,avg_delay}])
  con branch_id   → KPIs de UNA sucursal (misma forma que el agregado, filtrado)
  nuevas métricas por sucursal: pedidos, ventas (GMV), demoras (avg_delay vs SLA),
  llamadas atendidas/perdidas (branch_id en call_records, F2/F3) → {answered, missed} por branch
```

#### 3.3.3 WebSocket por sucursal (extiende ws_manager)

```
WS /ws/kitchen/{tenant_id}/{branch_id}     ← pantalla de cocina/pedidos de UNA sucursal
  - ws_manager agrupa por clave compuesta (tenant_id, branch_id):
    _kitchen: {(tenant_id, branch_id): [WebSocket]}
  - broadcast_to_kitchen(tenant_id, branch_id, event, data) — solo a pantallas de esa branch
  - eventos: new_delivery / delivery_ready / new_order / call_ringing (llamada entrante a esa sucursal)
  - Backward compatible: broadcast sin branch_id conserva el comportamiento actual (toda la tenant)
```

#### 3.3.4 Enrutamiento de llamadas DID→branch (call-bridge F2/F3)

```
Registro: branches.did (D2) es la fuente de verdad del mapeo:
  incoming_number → lookup branches WHERE tenant_id=<t> AND did=<incoming_number>
  hit  → enruta al local de esa sucursal (ring group / aviso WS call_ringing a /ws/kitchen/{t}/{branch})
         y escribe call_records.branch_id=<branch>
  miss → reglas actuales F2/F3 (trunk por negocio) / cola general del tenant
Re-suscripción: PATCH /api/v1/branches/{id} con did nuevo → el call-bridge refresca el mapeo (evento interno)
```

### 3.4 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R1 | **Cada sucursal ve SOLO sus pedidos**: toda pantalla de sucursal (WS, APIs de kanban, kiosko) filtra por `branch_id` resuelto del token/WS; sin branch_id → sin datos (nunca "todos") |
| R2 | **El dueño ve todas**: endpoints del owner pueden omitir `branch_id` (agregado) o filtrar/desglosar por sucursal; roles admin/manager/viewer del tenant (spec 04 D6) |
| R3 | **Llamada entrante enruta por DID**: incoming number → `branches.did` → branch (call-bridge); la llamada se registra con `branch_id`; sin match → flujo F2/F3 actual |
| R4 | **Settings heredables con override**: `branch.settings` (JSONB) hace merge sobre `companies.settings` — keys ausentes heredan del tenant (menú/horarios/WhatsApp/alertas por branch, patrón D-03) |
| R5 | **Kiosko**: la tablet autentica con token kiosko (JWT tenant+branch fijos, revocable vía hash); sin login complejo ni navegación global; el token solo expone su branch (R1) |
| R6 | **branch_id nullable solo a nivel BD**: operaciones nuevas originadas en sucursal exigen `branch_id` (validación de servicio 400); data legacy NULL se muestra como "sin sucursal" en el agregado |
| R7 | **Contabilidad consolidada**: todas las sucursales comparten tenant → ventas → kárdex → asiento únicos (D-1); no hay asientos por sucursal |

### 3.5 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F4-1 | `alembic upgrade head` (BD con 0016 aplicada) | Tabla `branches` + columnas `branch_id` (nullable) en `delivery_orders`/`kitchen_orders`/`sales`; head = `0017_branches`; `downgrade 0016` revierte todo; data legacy intacta (NULLs, sin backfill) |
| CA-F4-2 | `POST /api/v1/branches` (admin) | 201; GET lista del tenant la muestra; UNIQUE (tenant, code) y (tenant, did) respetados (409 si se duplica) |
| CA-F4-3 | **Aislamiento**: pedido/comanda creado en sucursal A | NO aparece en la pantalla (WS/API) de la sucursal B; broadcast `new_delivery` solo a pantallas de A |
| CA-F4-4 | Dueño: `GET /dashboard/owner` sin `branch_id` | Agregado de TODAS las sucursales + desglose `branches[]` con pedidos/GMV/demoras por sucursal; con `branch_id=B` → solo B |
| CA-F4-5 | Llamada entrante al DID de B | Call-bridge resuelve DID→B, enruta al local de B, `call_records.branch_id=B`; llamada a número sin DID → flujo F2/F3 actual |
| CA-F4-6 | Tablet kiosko con token de B | Abre kanban/pedidos de B sin login complejo; token de B NO ve datos de A (R1); token revocado → 401 |
| CA-F4-7 | Alta de sucursal en minutos | POST branch + asignar DID + generar token kiosko + settings heredados (R4) → sucursal operativa sin migración ni despliegue adicional |
| CA-F4-8 | `PATCH /api/v1/branches/{id}/settings` | Override persiste en `branch.settings` (JSONB); keys no overrideadas heredan de `companies.settings`; sobrevive reinicio (patrón D-03) |
| CA-F4-9 | Ventas legacy sin `branch_id` | Siguen visibles en el agregado del dueño como "sin sucursal"; kárdex/asientos intactos (R7) |
| CA-F4-10 | `DELETE /api/v1/branches` con pedidos activos | 409 con conteo de pedidos activos (no se borra con operación en curso); con historial cerrado → 204 y SET NULL |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

**Esfuerzo estimado: 3-5 semanas plataforma + instalación por sucursal (house service, D5 — cotizable aparte).**

1. **Fase 1 — Migración**: commit `0017_branches` + modelo `branches.py` + columnas `branch_id`; `alembic upgrade head` en QA (desechable prod-equivalente); verificar CA-F4-1.
2. **Fase 2 — Backend branches**: CRUD `/api/v1/branches`, settings override (merge, R4), token kiosko (D3, R5), reglas R1/R6 en servicios. Tests.
3. **Fase 3 — WS por sucursal**: clave compuesta `(tenant_id, branch_id)` en `ws_manager`, ruta `/ws/kitchen/{tenant}/{branch}`, eventos por branch. Tests (CA-F4-3).
4. **Fase 4 — Panel dueño por sucursal**: `owner_dashboard_service` con `branch_id` opcional + desglose + métricas de llamadas (filtro por call_records.branch_id). Tests (CA-F4-4).
5. **Fase 5 — DID→branch (call-bridge)**: mapeo por `branches.did`, re-suscripción al PATCH, registro con `branch_id` (CA-F4-5). Depende del estado de F2/F3 (calls).
6. **Fase 6 — Frontend**: `BranchesPage` (CRUD), modo kiosko (ruta tablet por token, reuso de DeliveryPage/KitchenKanban con branch_id), DashboardOwner con selector/desglose de sucursal. `tsc -b` + `vite build` + tests de render.
7. **Fase 7 — QA + deploy + house service**: ejecutar CA-F4-1..10 en QA; deploy `./deploy.sh --env prod` con backup `.bak-<fecha>`; kit de instalación por sucursal (tablet, DID, token, onboarding) como servicio cotizable aparte.

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-12 (v0.1)**: spec creada. Fase R completa — verificadas en código: `Company` es el tenant
  (`models/accounting.py` L50) y **no existe concepto de sucursal** (grep `branch` en modelos: solo
  `tenant_id` en delivery_orders/kitchen_orders/sales); `ws_manager` agrupa por `tenant_id`
  (`core/ws_manager.py`); `owner_dashboard` + `owner_dashboard_service` sin dimensión sucursal;
  settings por tenant en `companies.settings` (patrón D-03) listos para override; call-bridge F2/F3
  con trunk por negocio (requiere DID por sucursal). **D-1 recomendada: tabla `branches`** (análisis
  §0.1) — pendiente de aprobación por Ron. Borradores (migración `0017_branches`, modelo
  `branches.py`) redactados durante R/P — **SIN commitear**, a la espera de aprobación de esta spec.

---

## 6. Referencias

- Spec 03 (delivery/dark kitchen — patrones de migración, settings D-03, WS, machine de estados): `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Spec 04 (panel del dueño — owner_dashboard, roles, métricas): `docs/specs/04-panel-indicadores/spec-panel-dueño.md`
- Spec auth multi-tenant (JWT, roles, tenant middleware): `docs/specs/00-mvp-core/spec-auth-multitenant.md`
- Spec superadmin (CRUD companies/usuarios multi-tenant): `docs/specs/01-fase0-restaurante-ferreteria/spec-superadmin-tenants.md`
- Informe ejecutivo cliente (requerimiento multi-sucursal / monitoreo central): `docs/reports/informe-ejecutivo-cliente-2026-08-10.md`
- Benchmark "Top 10 negocios Perú 2026" (house service S/2.000 de referencia — instalación por sucursal, D5)
- F2/F3 (calls): trunk por negocio existente en diseño; esta spec define la extensión DID→branch
