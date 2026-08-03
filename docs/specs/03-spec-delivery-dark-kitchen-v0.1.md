# SPEC 03 — Módulo Delivery / Dark Kitchen (MVP Fase A)

- **Estado**: 🟢 **APROBADA E IMPLEMENTADA (2026-08-03)** — Fase A completa en producción (commits `0f13728`, `7f93642`, `6a4e210`, `7787a70`)
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-03
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (specs 01/02 como referencia de formato)

---

## 0. Decisiones (D1-D6 — RESUELTAS, aprobadas por Ron 2026-08-03)

| # | Decisión | Acuerdo final |
|---|---|---|
| D1 | Cuenta contable del fee de delivery | Cuenta **"40" (Ventas)** con descripción "Delivery fee" en Fase A. Crear cuenta 705 implica seed por tenant → **diferido** (se registrará como trabajo futuro; trazable por descripción para reclasificar). |
| D2 | Zonas iniciales | **Solo Zona 1 para arrancar**: Montenegro / Motupe / Canto Grande (SJL). Ubicación del local: 11°56'25.6"S 76°58'32.0"W. Valores propuestos: fee S/5.00 · min_order S/35 · ETA 30-40 min (ajustables). Más zonas se agregan luego vía CRUD staff. |
| D3 | Repartidores | **Internos** (tabla `couriers`) en Fase A; integración Rappi/PedidosYa diferida a Fase C. |
| D4 | Número Yape del negocio (titular) | Mostrar en checkout; **configurable** en `companies.settings` (fix D-03 habilita el render). |
| D5 | Horario de delivery | **19:00–24:00 por default, configurable** por ítem (`available_from`/`available_to`); NULL → rige `delivery_enabled`. |
| D6 | Atribución de campañas | `campaign_id` **solo en `delivery_orders`** (no tocar `sales` en Fase A). UTM crudo en `delivery_orders.utm`. |

---

## 1. Contexto y objetivo

El local de El Segoviano **no opera de noche**; el upgrade busca explotar esa capacidad instalada con
**Dark Kitchen / Delivery nocturno** dirigido a público con capacidad de compra, apoyado en marketing
digital con campañas (Meta/Google) y medición de ROAS. El ERP ya contabiliza todo (ventas → kárdex →
asientos), así que el delivery debe **insertarse en el motor de ventas existente**, no crear un flujo
paralelo.

**Objetivo de la Fase A (MVP):** pedido online desde una landing pública (menú nocturno) → checkout con
pago Yape/POS/contraentrega → pedido llega a cocina (kanban existente) → máquina de estados con
seguimiento → panel staff (zonas, repartidores, campañas) → atribución UTM para medir campañas.

**Fuera de alcance Fase A:** notificaciones WhatsApp (Fase B), pago online PSP (Fase C), integración
Rappi/PedidosYa (Fase C), seguimiento público en mapa (Fase C).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-03)

### 2.1 El motor de ventas YA soporta delivery (reutilización directa)

| Componente | Ubicación | Estado |
|---|---|---|
| `SaleService.create_sale` acepta `restaurant_data.order_type="delivery"` + `delivery_address` | `app/services/sales_service.py` (~L280, L681) | ✅ Listo |
| `RestaurantSale.order_type` incluye `delivery` | `app/adapters/db/models/sales.py` | ✅ Listo |
| Métodos de pago `yape / plin / cash / card / transfer` con `reference` | `models/sales.py` `SalePayment` | ✅ Yape ya soportado |
| Sesión POS **opcional** (`sales.session_id` nullable; migración `4bc771f43a4e`) | `sales_service.py` L285 | ✅ No bloquea checkout sin caja |
| Cocina realtime: `KitchenOrder` + `WsManager.broadcast_to_kitchen` + `ws/kitchen/{tenant_id}` | `models/restaurant.py`, `core/ws_manager.py`, `routers/restaurant.py` L544 | ✅ Reutilizable |
| Motor de promociones (`Promotion` + `apply_promotion`) | `models/restaurant.py`, `routers/restaurant.py` L465 | ✅ Reutilizable |
| Kárdex + asiento contable automático por venta (HU-F2-006, COGS 50/12, cuenta ingreso "40") | `sales_service.py` L702+ | ✅ Automático |
| Multi-tenant (`get_tenant_id`: X-Tenant-ID o JWT) | `core/tenant.py` | ✅ Staff |
| Rate limiting Redis sliding-window | `core/rate_limit.py` | ✅ Reutilizable en endpoints públicos |

### 2.2 Lo que NO existe (trabajo nuevo de Fase A)

| Gap | Detalle |
|---|---|
| Resolución pública de tenant | No hay slug en `companies`; los endpoints públicos deben resolver tenant por slug |
| Menú nocturno | `menu_items.active` es booleano; no hay ventana horaria ni flag de delivery |
| Zonas / repartidores / pedidos delivery | No existen modelos |
| Campañas / UTM | No hay atribución de ventas a campañas |
| Endpoints públicos | Todos los routers exigen JWT |
| Branding por tenant (D-03 conocido) | `setup.py` guarda settings en memoria global, no multi-tenant (bloquea render de logo/colores en landing) |

### 2.3 Patrón a NO copiar

`TakeawayOrder` **no crea Sale** → queda fuera de kárdex/contabilidad. Para delivery (pago al ordenar)
es inaceptable: **el checkout crea `Sale` directo** (`order_type="delivery"`), y `delivery_orders.sale_id`
es la única FK al motor de ventas. La integración a cocina usa `KitchenOrder.sale_id` (columna ya
existente, `unique`), sin columna duplicada.

### 2.4 Hallazgos incidentales (no bloquean Fase A; documentados)

- **Fresh install roto (preexistente)**: `alembic_version.version_num` es VARCHAR(32) pero revision ids
  de 36 chars (`0010_product_categories_missing_columns`) no caben → `upgrade head` desde BD vacía falla
  en 0010. En prod se ensanchó a VARCHAR(255) manualmente. Además `0002` siembra admin con
  `tenant_id=1` que falla sin company. **Fix recomendado (fuera de Fase A):** crear `alembic_version`
  con VARCHAR(255) en env.py.
- **Interacción baseline↔metadata**: `0000_baseline` ejecuta `Base.metadata.create_all` con la metadata
  ACTUAL; al registrar modelos delivery, un fresh install que ejecute el baseline crearía las tablas
  delivery antes de 0016 → conflicto. En prod no ocurre (baseline ya aplicada). Si se arregla fresh
  install: **stampear el merge**, no ejecutar baseline.
- **`psycopg[binary]==3.2.3` sin wheel para Python 3.14** (requerido por baseline sync): instalar
  `psycopg[binary]` ≥3.2.10 en el venv de desarrollo.

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (Fase A):**
- Migración `0016_delivery` (tablas + columnas, §3.2).
- Endpoints públicos rate-limited con resolución por slug (§3.4.1).
- Panel staff: CRUD zonas/repartidores/campañas + máquina de estados + asignación de repartidor (§3.4.2).
- Checkout que crea Sale directo (order_type=delivery) → kárdex + asiento automático.
- Integración cocina: `KitchenOrder` vinculada por `sale_id` + broadcast WS `new_delivery`.
- Captura UTM en checkout → `delivery_orders.utm` + resolución de `campaign_id` por match UTM.
- Fix D-03: branding persistente por tenant (leer/guardar en `companies.settings` JSONB) para la landing.
- Métricas de campañas: pedidos, GMV, ticket promedio, ROAS (por campaña/canal/fecha).

**NO INCLUYE (límites Fase A):**
- Notificaciones WhatsApp (Fase B), pago PSP online (Fase C), Rappi/PedidosYa (Fase C), mapa de
  seguimiento (Fase C), app móvil, menú diurno online (takeaway se mantiene como está).

### 3.2 Modelo de datos (migración `0016_delivery` — borrador redactado, SIN commitear)

```sql
delivery_zones (
  id serial PK, tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  name varchar(100) NOT NULL, description text,
  districts jsonb,                    -- distritos cubiertos (Fase A); polígono en Fase C
  fee numeric(10,2) NOT NULL DEFAULT 0, min_order numeric(10,2) NOT NULL DEFAULT 0,
  eta_min int NOT NULL DEFAULT 45, active bool NOT NULL DEFAULT true,
  created_at/updated_at timestamptz,
  UNIQUE (tenant_id, name), CHECK (fee >= 0), CHECK (min_order >= 0), CHECK (eta_min >= 0)
)

couriers (
  id serial PK, tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  user_id int FK users(id) ON DELETE SET NULL,     -- opcional: repartidor con cuenta ERP
  name varchar(100) NOT NULL, phone varchar(20), vehicle varchar(50),
  status varchar(20) NOT NULL DEFAULT 'available',  -- available | on_delivery | offline
  active bool NOT NULL DEFAULT true, created_at/updated_at timestamptz,
  CHECK (status IN ('available','on_delivery','offline'))
)

marketing_campaigns (
  id serial PK, tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  name varchar(100) NOT NULL, channel varchar(20) NOT NULL DEFAULT 'meta',  -- meta|google|tiktok|other
  utm_source varchar(50), utm_medium varchar(50), utm_campaign varchar(100),
  budget numeric(12,2) NOT NULL DEFAULT 0, spend numeric(12,2) NOT NULL DEFAULT 0,
  starts_on date, ends_on date, active bool NOT NULL DEFAULT true, notes text,
  created_at/updated_at timestamptz, UNIQUE (tenant_id, name),
  CHECK (budget >= 0), CHECK (spend >= 0)
)

delivery_orders (
  id serial PK, tenant_id int NOT NULL FK companies(id) ON DELETE CASCADE,
  sale_id int UNIQUE FK sales(id) ON DELETE SET NULL,     -- 1:1 con el motor de ventas
  zone_id int FK delivery_zones(id) ON DELETE SET NULL,
  courier_id int FK couriers(id) ON DELETE SET NULL,
  campaign_id int FK marketing_campaigns(id) ON DELETE SET NULL,  -- D6: solo aquí, no en sales
  tracking_code varchar(20) NOT NULL UNIQUE,             -- formato DLV-<base36>
  customer_name varchar(100), customer_phone varchar(20),
  customer_address varchar(300) NOT NULL, lat numeric(9,6), lng numeric(9,6),
  fee numeric(10,2) NOT NULL DEFAULT 0, eta_min int,
  status varchar(20) NOT NULL DEFAULT 'received',
  utm jsonb,                                             -- source/medium/campaign/term/content
  notes text,
  received_at/preparing_at/ready_at/out_for_delivery_at/delivered_at/cancelled_at timestamptz,
  created_at/updated_at timestamptz,
  CHECK (status IN ('received','preparing','ready','out_for_delivery','delivered','cancelled')),
  CHECK (fee >= 0)
)

-- Columnas nuevas en tablas existentes
menu_items:  delivery_enabled bool NOT NULL DEFAULT true,
             available_from time, available_to time,       -- ventana nocturna (D5: 19:00–24:00)
             delivery_surcharge numeric(10,2) NOT NULL DEFAULT 0
companies:   slug varchar(100) UNIQUE                      -- URL pública /menu/{slug}
```

**Notas de diseño:**
- `delivery_orders.sale_id` UNIQUE → 1 pedido delivery = 1 venta (nada de pagos parciales fuera del motor).
- Timestamps por transición → SLAs y métricas de tiempo de entrega sin tablas extra.
- `utm` se guarda crudo en el pedido (trazabilidad) y `campaign_id` se resuelve por match
  (utm_source+utm_medium+utm_campaign) contra `marketing_campaigns` activas.
- El fee NO es un item de venta: va en `delivery_orders.fee`; el total del Sale incluye el fee (D1).
- El borrador de modelos (`app/adapters/db/models/delivery.py`) y migración ya existen en el worktree
  **SIN commitear**; quedan a la espera de aprobación de esta spec (Spec Anchor: spec primero).

**Zona 1 — seed inicial (D2, aprobada):**

```sql
INSERT INTO delivery_zones (tenant_id, name, description, districts, fee, min_order, eta_min, active)
VALUES (1, 'Montenegro / Motupe / Canto Grande',
        'Zona 1 de lanzamiento — radio cercano al local (SJL, límite Montenegro–Motupe)',
        '["Montenegro", "Motupe", "Canto Grande"]', 5.00, 35.00, 35, true);
```

- Ubicación del local: **11°56'25.6"S 76°58'32.0"W** (SJL, límite Montenegro y Motupe).
- Fee S/5.00 · min_order S/35.00 · ETA 30–40 min (valor 35). Ajustables por CRUD staff sin migración.

### 3.3 Máquina de estados

```
received ──► preparing ──► ready ──► out_for_delivery ──► delivered
    │            │           │              │
    └────────────┴───────────┴──────────────┴──► cancelled
```

- Transiciones válidas: desde `received|preparing|ready|out_for_delivery` → `cancelled`;
  `received→preparing→ready→out_for_delivery→delivered` (sin saltos).
- Transición inválida → **400** con detalle de las transiciones permitidas.
- Cada transición setea su timestamp (`preparing_at`, `ready_at`, ...) e `updated_at`.
- `received` se crea en el checkout; `ready` además notifica WS a cocina/meseros (evento `delivery_ready`).

### 3.4 Contratos

#### 3.4.1 Endpoints públicos (SIN JWT, rate-limited Redis, tenant resuelto por slug)

```
GET  /api/public/{slug}/menu
  → 200 { sections: [{id, name, items: [{id, name, description, price,
        delivery_surcharge, modifiers: [{id,name,price_adjustment,max_select}],
        image_url, available: bool}] }], promotions: [{id, name, promo_type, discount_value, ...}],
        delivery_window: {from: "19:00", to: "24:00"}, currency: "PEN" }
  → 404 slug inexistente | 503 delivery cerrado (fuera de ventana global si aplica)
  Regla: solo items con active=true AND delivery_enabled=true AND dentro de available_from/to
  (si available_* es NULL, rige delivery_enabled). Stock no se expone (solo disponible/agotado).

GET  /api/public/{slug}/zones
  → 200 [{id, name, fee, min_order, eta_min, districts}]   (solo active)

POST /api/public/{slug}/orders
  Request: { items: [{menu_item_id, quantity, modifiers: [{id, quantity}]}],
             customer: {name, phone, address, lat?, lng?},
             zone_id, payment: {method: "yape"|"plin"|"cash", reference?},
             utm: {source, medium, campaign, term?, content?}, notes? }
  Validaciones: menú disponible en este momento (422 si item fuera de horario/inactivo);
    stock suficiente (409, rollback atómico — patrón spec 01 CA4); min_order de la zona (422);
    yape/plin requieren reference (400); promos vigentes aplicadas automáticamente (motor existente).
  Efectos (transacción única): crea Sale (order_type=delivery, incluye fee en total, pago según
    method) → kárdex/explosión de recetas → asiento contable → KitchenOrder (sale_id) + broadcast WS
    → DeliveryOrder (tracking_code DLV-xxxx, utm, campaign_id resuelto).
  → 201 { tracking_code, sale_id, sale_number, status: "received", eta_min, totals: {
           subtotal, discount_total, fee, total }, payment: {method, status: "pending_confirm"} }

GET  /api/public/orders/{tracking_code}/status
  → 200 { tracking_code, status, timestamps: {received_at, preparing_at, ready_at,
           out_for_delivery_at, delivered_at, cancelled_at}, eta_min }
  → 404 código inexistente
```

#### 3.4.2 Endpoints staff (auth + tenant — panel Fase A)

```
CRUD  /api/v1/delivery/zones            GET lista | POST | PATCH /{id} | DELETE /{id}
CRUD  /api/v1/delivery/couriers         GET | POST | PATCH /{id} (incluye status) | DELETE /{id}
GET   /api/v1/delivery/orders?status=   kanban (filtro multi-status, excluye terminales por defecto)
GET   /api/v1/delivery/orders/{id}      detalle + items del Sale + timestamps
PATCH /api/v1/delivery/orders/{id}/status   { status } (máquina de estados §3.3)
POST  /api/v1/delivery/orders/{id}/assign-courier  { courier_id } (marca courier on_delivery)
CRUD  /api/v1/delivery/campaigns        GET | POST | PATCH /{id} | DELETE /{id}
GET   /api/v1/delivery/metrics/campaigns?from=&to=&channel=
  → [{campaign_id, name, channel, spend, orders, gmv, aov, roas}]   (roas = gmv/spend; aov = gmv/orders)
GET   /api/v1/delivery/metrics/overview?from=&to=   pedidos, GMV, fee total, tiempo medio de entrega
```

#### 3.4.3 Fix D-03 (habilitador de la landing)

- `GET/PATCH /api/settings` pasan a leer/escribir `companies.settings` (JSONB) en lugar de la variable
  global `_current_settings` (setup.py). Sin cambio de contrato para el frontend existente.

### 3.5 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R1 | Ventana de delivery por ítem: `available_from`/`available_to` (D5: 19:00–24:00); NULL → rige `delivery_enabled` |
| R2 | Fee por zona (`delivery_zones.fee`); total = subtotal − descuento + fee; `min_order` validado contra subtotal |
| R3 | Promos: motor existente (`Promotion.active` + `valid_from/to`); aplicadas en checkout |
| R4 | UTM capturados en el primer clic → `delivery_orders.utm`; `campaign_id` por match exacto de UTM |
| R5 | Pago Fase A: yape (reference obligatorio) \| plin (reference) \| cash (contraentrega); sin PSP |
| R6 | Checkout crea `Sale` (order_type=delivery) → kárdex + asiento; sesión POS no requerida |
| R7 | Pre-check de stock atómico: si falta algún insumo (explosión) o ítem → 409, sin efectos parciales |
| R8 | Cocina: `KitchenOrder.sale_id` + broadcast WS `new_delivery`; `ready` → WS `delivery_ready` |
| R9 | Aislamiento: públicos por slug; staff por X-Tenant-ID/JWT; toda query filtra tenant resuelto |
| R10 | `tracking_code` = `DLV-` + timestamp base36; UNIQUE en BD |
| R11 | Fee contable: cuenta "40" con descripción "Delivery fee" (D1) |

### 3.6 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA1 | `alembic upgrade head` (BD con 0015 aplicada) | Tablas `delivery_zones`, `couriers`, `marketing_campaigns`, `delivery_orders` + columnas en `menu_items`/`companies`; head = `0016_delivery`; `downgrade 0015` revierte todo |
| CA2 | `GET /api/public/el-segoviano/menu` con item delivery_enabled dentro de ventana | 200 solo con items disponibles; item fuera de `available_from/to` o `delivery_enabled=false` excluido |
| CA3 | `POST /api/public/el-segoviano/orders` válido (items + zona + pago yape con reference) | 201; en BD: `sales` (order_type=delivery) + `delivery_orders` (tracking_code, utm) + kárdex descontado + asiento contable (fee en cuenta 40) + `kitchen_orders` creada + WS `new_delivery` |
| CA4 | Checkout con item fuera de horario | 422 con detalle del item |
| CA5 | Subtotal < `min_order` de la zona | 422 indicando el mínimo |
| CA6 | Stock insuficiente (ítem o ingrediente de receta) | 409, **sin** movimientos kárdex ni venta parciales (rollback) |
| CA7 | Pago yape/plin sin `reference` | 400 |
| CA8 | `GET /api/public/orders/DLV-xxxx/status` tras transiciones | status + timestamps correctos |
| CA9 | `PATCH status` con transición inválida (ej. received→delivered) | 400 con transiciones permitidas |
| CA10 | Checkout con UTM de campaña activa | `delivery_orders.utm` poblado y `campaign_id` resuelto |
| CA11 | Aislamiento: `GET /api/public/{slug}` de otro tenant | 404 (slug no existe para ese tenant); datos nunca cruzados |
| CA12 | Endpoints públicos sin token | 200/201 (rate-limit aplica); staff sin token → 401 |
| CA13 | `GET /metrics/campaigns` con spend registrado | ROAS = gmv/spend; AOV = gmv/pedidos; filtro por rango/canal |
| CA14 | `assign-courier` | courier pasa a `on_delivery`; al `delivered`/`cancelled` vuelve a `available` |
| CA15 | Fix D-03: PATCH settings desde tenant A | Persiste en `companies.settings`; tenant B NO lo ve; sobrevive reinicio |
| CA16 | Landing renderiza logo/colores del tenant | Se sirve desde `companies.settings` (D-03) |

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

1. **Fase 1 — Migración**: commit de `0016_delivery` + modelos; `alembic upgrade head` en QA; verificar CA1.
2. **Fase 2 — Backend público**: resolución por slug (`get_tenant_by_slug`), `GET menu`, `GET zones`,
   `POST orders` (DeliveryService: crea Sale → kárdex → asiento → KitchenOrder → WS → DeliveryOrder),
   `GET tracking`. Rate-limit Redis. Tests.
3. **Fase 3 — Backend staff**: CRUD zonas/repartidores/campañas, máquina de estados, assign-courier,
   métricas (ROAS/AOV). Tests.
4. **Fase 4 — Fix D-03**: `companies.settings` persistente (settings router + landing).
5. **Fase 5 — Frontend**: panel delivery (plantilla TakeawayPage), CRUD campañas, métricas; landing
   pública (menú + checkout + tracking) en ruta `/menu/{slug}`.
6. **Fase 6 — QA + deploy**: ejecutar CA1-CA16 en QA; deploy `./deploy.sh --env prod`; respaldo de
   imágenes previas (patrón spec 01: `.bak-<fecha>`).

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-03 (v0.1)**: spec creada. Fase R completa (verificado en código: motor de ventas listo para
  delivery; gaps identificados). Borrador de migración `0016_delivery` + modelos `delivery.py`
  redactados durante R/P — **SIN commitear**, a la espera de aprobación de esta spec.
  Validación del borrador: cadena alembic head único, upgrade/downgrade/upgrade en Postgres 16
  desechable (prod-equivalente: merge stamped), 17 constraints verificados.
- **2026-08-03 (v0.1 → decisiones D1-D6 aprobadas por Ron)**: D1 fee → cuenta "40" (705 diferido);
  D2 zona 1 (Montenegro/Motupe/Canto Grande, fee 5, min 35, ETA 35) como seed inicial; D3
  repartidores internos; D4 Yape configurable en `companies.settings`; D5 horario 19:00–24:00
  default configurable; D6 `campaign_id` solo en `delivery_orders`. **Spec lista para implementar.**
- **2026-08-03 (Fase 1 — migración implementada y validada)**: commit `0f13728`. Migración
  `0016_delivery` + modelos `delivery.py` + columnas (menu_items/companies) + **seed Zona 1
  (tenant 1)** + slug `el-segoviano`. Validado en Postgres 16 desechable: upgrade/downgrade/upgrade,
  seed idempotente (no se duplica).
- **2026-08-03 (Fases 2-4 — backend público + staff + D-03 implementado)**: commit `← este`.
  - `schemas/delivery.py`, `services/delivery_service.py`, `routers/public.py`, `routers/delivery.py`;
    routers registrados en `main.py`; `PromotionsService.compute_discount` extraído (reutilizable
    cart-level, refactor sin cambio de contrato); `setup.py` persistente en `companies.settings` (D-03).
  - **Decisiones de implementación (Spec Anchor — sync con §3)**:
    - El fee se registra como **ítem de servicio "Delivery fee"** en el Sale (no solo en
      `delivery_orders.fee`) para que pagos/totales/asiento cuadren en el motor (D1: ingresa en
      cuenta 40 dentro de "Ingresos por ventas", sin kárdex).
    - `SaleService.create_sale` retorna `{sale: {...}}` (no plano) — el servicio lee `sale.id`.
    - Horario evaluado en **America/Lima** (el servidor corre en UTC; usar hora local habría
      desplazado la ventana 19:00–24:00).
    - `companies.settings` (JSON): al persistir se asigna **copia nueva del dict** — asignar el
      mismo objeto no marca la columna como dirty en SQLAlchemy (bug real detectado y corregido).
    - Promo en checkout: se aplica la **mejor promoción simple** (no stacking) descontando del
      primer ítem vía `discount_amount` del motor (R3).
    - `tracking_code` = `DLV-` + timestamp hex (10 chars), UNIQUE.
    - Endpoints públicos: rate-limit Redis (fallback in-memory), 10 req/min checkout.
  - **Smoke test end-to-end (Postgres 16 desechable, prod-equivalente)**: menú público (200, excluye
    no-delivery, respeta ventana), checkout yape 201 (sale + fee item + asiento balanceado
    Caja10/Ventas40/IGV201 + kitchen_orders + delivery_orders con UTM), plin 201, 422 fuera de
    horario, 422 min_order, 400 transición inválida, tracking con timestamps, CRUD couriers/campañas,
    assign-courier → on_delivery, métricas (ROAS 0.8 = 40/50, AOV, GMV, fee_total, avg_delivery),
    atribución UTM → campaign_id, 404 slug inexistente, 401 staff sin token, D-03 PATCH → BD → GET.
  - Suite: **300 passed** (2 fallos preexistentes en `test_caso6_recipes`, ajenos a esta spec).
  - **Pendiente Fase 5 (frontend)**: panel delivery + landing pública `/menu/{slug}`; Fase 6 (QA+deploy).
- **2026-08-03 (Fase 5 — frontend + manuales implementados)**: commit `← este`.
  - `services/deliveryApi.ts` (staff) + `services/publicMenuApi.ts` (público sin auth).
  - `pages/restaurante/DeliveryPage.tsx`: 5 pestañas — Pedidos (kanban por estado con
    transiciones + asignación de repartidor), Zonas (CRUD), Repartidores (CRUD + estados),
    Campañas (CRUD + link UTM autogenerado), Métricas (ROAS/AOV/GMV/tarjetas).
  - `pages/public/PublicMenuPage.tsx`: landing `/menu/:slug` sin auth — catálogo nocturno,
    carrito con modificadores (ModifierBottomSheet reutilizado), checkout (zona/pago
    Yape-Plin-contraentrega/referencia), UTM del primer clic desde la URL, pantalla de éxito
    con tracking_code, seguimiento con timeline; branding del tenant aplicado (paleta/logo
    desde `companies.settings` — D-03) sin auth.
  - `App.tsx`: ruta pública `/menu/:slug` (fuera de AppShell/PrivateRoute, como `/login`) +
    ruta staff `/restaurante/delivery`; `Sidebar.tsx`: ítem "Delivery Nocturno" en Restaurante.
  - Backend (sync): `PublicMenuResponse` + menú público ahora incluyen `branding`
    `{palette, logo_url}` (D-03) y `yape_phone` leído de `settings.delivery.yape_phone`.
  - Build: `tsc -b` 0 errores + `vite build` OK (chunks DeliveryPage 23.9 kB, PublicMenuPage 17.2 kB).
  - Manuales: nuevo `docs/manuales/manual-delivery-dark-kitchen.md` (flujo cliente + staff +
    FAQ) y `docs/manuales/manual-admin.md` §5.3/§5.4/§10.5 (config Yape/horarios/zonas/campañas,
    endpoints).
  - **Pendiente Fase 6**: QA + deploy (`./deploy.sh --env prod`, backup `.bak-<fecha>`).
- **2026-08-03 (Camino C — E2E Playwright + Trace Viewer)**: commit `← este`.
  - `e2e/playwright.config.prod.ts`: config PROD (baseURL https://www.ronsyserp.com, sin
    webServer, workers=1, trace/video/screenshot ON, `executablePath` al Chrome for Testing
    151 del .35, `chromiumSandbox:false` por AppArmor userns=1).
  - `e2e/delivery-landing.spec.ts` (6 tests): menú/horario, Yape 912057784, carrito+zona+fee,
    min_order, checkout real con UTM → DLV- (se CANCELA en afterAll vía API), tracking.
  - `e2e/delivery-staff.spec.ts` (5 tests): panel, kanban, CRUD zona, CRUD campaña con link
    UTM, métricas. Fixture con login API 1 vez + reinyección del refresh token ROTADO
    (single-use + family revocation) — el storageState no sirve (sessionStorage).
  - Hallazgos corregidos en el camino: (1) Playwright no instala chromium/ffmpeg en
    ubuntu26.04 → CfT 151 por executablePath + ffmpeg bajado del CDN de Playwright a
    `~/.cache/ms-playwright/ffmpeg-1011`; (2) **bug backend real**: PATCH parcial de
    zonas/repartidores/campañas daba 422 (schemas full con `name` requerido) → nuevos
    `ZoneUpdate/CourierUpdate/CampaignUpdate` (todo opcional) — afectaba el toggle
    Pausar/Activar del panel en prod; (3) selector `font-mono.font-bold` sin punto =
    type-selector CSS (0 matches) → `getByText(/^DLV-/)`.
  - Scripts: `test:e2e:prod`, `test:e2e:prod:report` (sirve en 0.0.0.0:9323 para la .39).
  - **Resultado: 11/11 PASS contra prod** (41.6s); limpieza verificada (0 E2E en prod).
- **2026-08-03 (Fase 6 — deploy prod + fix yape_phone)**: commit `← este`.
  - Deploy prod: backup imágenes `bak-2026-08-03` + `pg_dump` previo; `./deploy.sh --env prod`;
    alembic prod → `0016_delivery`; QA suite 10/10 PASS pre y post deploy; smoke en
    https://www.ronsyserp.com OK (landing, zonas, checkout DLV-9fc6268b79 con UTM, min-order 422,
    tracking, cancelación staff). Nota: deploy.sh resetea passwords demo (admin→admin123).
  - **Fix (gap detectado en smoke)**: `CompanySettings` no tenía campo `delivery` →
    `PATCH /api/settings {"delivery":{"yape_phone":...}}` devolvía 200 pero Pydantic descartaba
    el campo y el menú público seguía con `yape_phone: null`. Fix: `DeliverySettings` +
    campo `delivery` en `CompanySettings`; `setup.py` persiste `settings.delivery` FUERA de
    `settings.branding` (merge + update_palette también corregidos). Tests: 2 nuevos
    (schema + persistencia). Verificado en prod: menú público devuelve `yape_phone` configurado.
- **2026-08-03 (verificación E2E visual + cierre Fase A)**: estado de la spec → 🟢 APROBADA E
  IMPLEMENTADA (header actualizado). Verificación en vivo con browser controlado por el agente en
  el monitor físico del servidor (.35): login admin@elsegoviano.pe → Dashboard → panel Delivery
  Nocturno (`/restaurante/delivery`, kanban Recibido/En cocina/Listo/En ruta/Entregado/Cancelado,
  pestañas Pedidos/Zonas/Repartidores/Campañas/Métricas) — todo operativo en
  https://www.ronsyserp.com. Infraestructura de prueba documentada en
  `docs/reports/guia-pruebas-e2e-browser-2026-08-03.md` (monitor físico + CfT 151 + plugin browser
  + Gateway con DISPLAY=:0). Fase A CERRADA; siguientes fases (B: WhatsApp/métricas avanzadas;
  C: PSP/Rappi) quedan como trabajo futuro fuera del alcance de esta spec.

---

## 6. Referencias

- Spec 01 (explosión de recetas — patrón de pre-check 409 atómico y COGS): `docs/specs/01-spec-recetas-productos-v0.2.md`
- Spec 02 (costos variables / kárdex promedio ponderado): `docs/specs/02-spec-costos-variables-v0.1.md`
- Plan integral v3 — deuda D-06 (delivery en Fase 2): `Plan-Integral-de-Integración-de-Módulos-ERP-v3.md`
- Informe de investigación "Top 10 negocios Perú 2026" (dark kitchens: 35k soles, margen 12-18%, éxito 50-55%)
- Informe de upgrade consolidado: `docs/reports/informe-upgrade-dark-kitchen-delivery-2026-08-03.md`
