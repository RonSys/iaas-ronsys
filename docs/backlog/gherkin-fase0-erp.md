# Backlog Gherkin — Fase 0: MVP Restaurante + Ferretería Básico

> **Proyecto:** IaaS-RonSys  
> **Plan de referencia:** `Plan-Integral-de-Integración-de-Módulos-ERP-v3.md`  
> **Decisiones cliente incorporadas:** Seriales → F2, Sidebar + Salir en F0, Multitenant estandarizado, Fact. SUNAT → V3  
> **Generado por:** PO Agent 📋 vía Jarvis  
> **Fecha:** 2026-05-14  
> **Total Historias:** 15 (Backend: 10 | Frontend: 4 | Infra/Testing: 1)

---

# Fase 0 — MVP Restaurante + Ferretería Básico

**Objetivo:** Sistema funcional con ventas, inventario básico y módulo Restaurante (salones, menú, comandas, takeaway, promociones básicas).  
**Esfuerzo total actualizado:** ~18.5-21 días (backend 12-14d + frontend 5-6d + testing 1d + websockets 0.5d)  
**Deudas técnicas pospuestas:** D-05 (cierre comanda → F2), D-06 (delivery avanzado → F2), D-20 (fact. electrónica → F3/V2), D-21 (código barras → F2 opcional)

---

## HU-F0-001: Multitenant estandarizado con tenant_id

**Como** administrador del sistema  
**Quiero** que cada empresa (tenant) tenga un `tenant_id` consistente en todas las tablas del sistema  
**Para** asegurar el aislamiento de datos entre clientes y que ningún usuario acceda a datos de otro tenant.

**Criterios de aceptación:**

#### Migración de esquema
- [ ] Given la migración `XXXX_multitenant_standardization` When se ejecuta `alembic upgrade head` Then:
  - La columna `company_id` en `companies` pasa a llamarse `tenant_id`
  - La columna `company_id` en `pos_sessions`, `sales`, `users`, `refresh_tokens`, `simulation_scenarios`, `cashflow_projections` se renombra a `tenant_id`
  - Todas las tablas nuevas creadas en F0 tienen `tenant_id` como FK a `companies.id`
  - Los datos existentes se preservan íntegros
  - Los índices existentes se mantienen o recrean

#### Middleware de tenant
- [ ] Given un request sin header `X-Tenant-ID` When accede a un endpoint protegido Then el middleware respeta el JWT decodificado (usa `tenant_id` del token)
- [ ] Given un request con `X-Tenant-ID` incoherente con el JWT When se procesa Then el sistema rechaza con HTTP 403 y mensaje "Access denied to this tenant"
- [ ] Given un usuario autenticado del tenant A When consulta cualquier endpoint Then solo ve datos donde `tenant_id = A`
- [ ] Given un usuario autenticado del tenant B When intenta acceder por ID a un recurso del tenant A Then responde 404 (no filtra existencia de otros tenants)

#### Scoping en repositorios
- [ ] Given un repositorio SQLAlchemy con scoping de tenant When se ejecuta una query sin filtro explícito Then la query incluye automáticamente `WHERE tenant_id = <contexto_actual>`
- [ ] Given un INSERT desde un repositorio scoped When se crea un registro Then el `tenant_id` se asigna automáticamente del contexto

**Prioridad:** P1 (bloqueante)  
**Esfuerzo estimado:** 3-4 días (actualizado desde 1 día)  
**Dependencias:** Ninguna (primera tarea de F0)  
**Notas técnicas:**
- Enfoque: estandarizar `company_id` existente como `tenant_id` (opción a del architecture agent)
- Middleware `core/tenant.py` ya existe con `X-Tenant-ID` → adaptar para que use `tenant_id` del JWT como fallback
- Migración Alembic con renombrado de columnas: `ALTER TABLE ... RENAME COLUMN company_id TO tenant_id`
- Repositorios: BaseRepository que inyecta `WHERE tenant_id = ?` automáticamente
- NO se necesita agregar `tenant_id` a tablas que no tenían `company_id` (solo tablas existentes que ya lo tenían)

---

## HU-F0-002: Selección de tipo de negocio en setup de tenant

**Como** administrador del sistema  
**Quiero** seleccionar el tipo de negocio (restaurante, ferretería/retail, servicio) al crear/configurar un tenant  
**Para** que el sistema active los módulos y comportamientos correctos según el rubro.

**Criterios de aceptación:**

- [ ] Given un admin autenticado creando un nuevo tenant When completa el formulario de setup Then hay un campo obligatorio `business_type` con opciones: `restaurant`, `hardware`, `retail`, `service`
- [ ] Given un tenant con `business_type = 'restaurant'` When se guarda Then `feature_flags` se inicializan con: `tables_enabled: true`, `tips_enabled: true`, `recipe_explosion: true`, `kitchen_display: true`
- [ ] Given un tenant con `business_type = 'hardware'` When se guarda Then `feature_flags` se inicializan con: `warranty_tracking: true`, `invoice_required: true`, `bulk_pricing: true`
- [ ] Given un tenant con `business_type = 'retail'` When se guarda Then `feature_flags` se inicializan con valores neutros: `invoice_required: false`, `bulk_pricing: false`
- [ ] Given un request con `business_type` inválido When se envía al backend Then responde 422 con validación de enum
- [ ] Given la migración ejecutada When verifico Then la columna `business_type` en `companies` tiene CHECK constraint sobre valores permitidos

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 día  
**Dependencias:** HU-F0-001 (tenant_id estandarizado)  
**Notas técnicas:**
- Migración ya existente `0003_business_type.py` — verificar si ya agregó la columna
- Feature flags como JSONB en tabla `companies` o en `company_settings` (nueva)
- Endpoint `PATCH /api/admin/company/settings` existente en `routers/admin.py`

---

## HU-F0-003: Modelos y migraciones para Restaurante

**Como** desarrollador backend  
**Quiero** crear los modelos ORM y migraciones para las tablas de Restaurante  
**Para** que el módulo Restaurante tenga persistencia en base de datos.

**Criterios de aceptación:**

#### Tabla: tables (mesas)
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `tables` con columnas: `id` (PK auto), `tenant_id` (FK companies.id CASCADE), `number` (INT), `capacity` (INT), `status` (ENUM: free/occupied/reserved/closed), `section` (VARCHAR(50), nullable), `qr_code` (VARCHAR(100), nullable), `created_at`, `updated_at`
- [ ] Given la migración ejecutada When verifico Then existe UNIQUE constraint sobre (`tenant_id`, `number`)
- [ ] Given la migración ejecutada When verifico Then existe índice sobre `tenant_id` y `status`

#### Tabla: menu_items (ítems del menú/carta)
- [ ] Given la migración ejecutada When verifico Then existe tabla `menu_items` con columnas: `id`, `tenant_id`, `name` (VARCHAR(100)), `description` (TEXT, nullable), `category` (VARCHAR(50)), `price` (NUMERIC 10,2), `cost` (NUMERIC 10,2, nullable), `unit` (VARCHAR(20): "plato", "porción", "unidad"), `image_url` (VARCHAR(255), nullable), `available` (BOOLEAN default true), `has_modifiers` (BOOLEAN default false), `created_at`, `updated_at`
- [ ] Given la migración ejecutada When verifico Then existe índice sobre (`tenant_id`, `category`)

#### Tabla: menu_modifiers (modificadores ej: "Sin huevo", "Extra queso")
- [ ] Given la migración ejecutada When verifico Then existe tabla `menu_modifiers` con: `id`, `menu_item_id` (FK menu_items.id CASCADE), `name` (VARCHAR(50)), `price_adjustment` (NUMERIC 10,2 default 0), `max_select` (INT default 1)

#### Tabla: kitchen_orders (comandas/pedidos a cocina)
- [ ] Given la migración ejecutada When verifico Then existe tabla `kitchen_orders` con: `id`, `tenant_id`, `sale_id` (FK sales.id, nullable), `table_id` (FK tables.id, nullable), `order_type` (ENUM: 'dine_in', 'takeaway', 'delivery'), `status` (ENUM: 'pending', 'preparing', 'ready', 'served', 'cancelled'), `items` (JSONB: [{menu_item_id, name, quantity, modifiers, notes}]), `priority` (INT default 0), `notes` (TEXT, nullable), `sent_at` (TIMESTAMP), `completed_at` (TIMESTAMP, nullable), `created_at`, `updated_at`
- [ ] Given la migración ejecutada When verifico Then existe índice sobre (`tenant_id`, `status`, `sent_at`)

#### Tabla: takeaway_orders (pedidos para llevar)
- [ ] Given la migración ejecutada When verifico Then existe tabla `takeaway_orders` con: `id`, `tenant_id`, `sale_id` (FK sales.id, nullable), `customer_name` (VARCHAR(100), nullable), `customer_phone` (VARCHAR(20), nullable), `status` (ENUM: 'pending', 'preparing', 'ready', 'picked_up', 'cancelled'), `items` (JSONB), `pickup_time` (TIMESTAMP, nullable), `created_at`, `updated_at`

#### Tabla: promotions (promociones)
- [ ] Given la migración ejecutada When verifico Then existe tabla `promotions` con: `id`, `tenant_id`, `name` (VARCHAR(100)), `type` (ENUM: 'combo', 'fixed_discount', 'percentage_discount', 'happy_hour'), `discount_value` (NUMERIC 10,2), `conditions` (JSONB: {min_items, min_amount, applicable_categories, applicable_menu_item_ids}), `start_date` (TIMESTAMP), `end_date` (TIMESTAMP, nullable), `active` (BOOLEAN default true), `max_uses` (INT, nullable), `current_uses` (INT default 0), `created_at`, `updated_at`
- [ ] Given la migración ejecutada When verifico Then existe índice sobre (`tenant_id`, `active`, `start_date`, `end_date`)

#### Modelos ORM
- [ ] Given los modelos definidos en `adapters/db/models/restaurant.py` When verifico Then extienden `Base` y usan `Mapped`/`mapped_column` de SQLAlchemy 2.0
- [ ] Given los modelos definidos When verifico las relaciones Then `Table` tiene relación con `KitchenOrder`, `MenuItem` tiene relación con `MenuModifier`

**Prioridad:** P1  
**Esfuerzo estimado:** 2.5 días (incluye 0.5d validación migraciones)  
**Dependencias:** HU-F0-001 (tenant_id)  
**Notas técnicas:**
- Archivo nuevo: `adapters/db/models/restaurant.py`
- Migración Alembic: `XXXX_restaurant_tables.py`
- `tenant_id` es FK a `companies.id` con ON DELETE CASCADE
- Validar migraciones en QA antes de pasar a prod

---

## HU-F0-004: Endpoints de Restaurante — Abrir mesa

**Como** mesero  
**Quiero** abrir una mesa asignándola a un cliente/comensal  
**Para** comenzar a tomar el pedido y asociarlo a esa mesa.

**Criterios de aceptación:**

- [ ] Given una mesa con `status = 'free'` When hago `POST /api/v1/restaurant/tables/{id}/open` con `waiter_id` (opcional) y `guest_count` Then la mesa pasa a `status = 'occupied'`, se registra `opened_at` y se retorna 200 con el estado actualizado
- [ ] Given una mesa con `status = 'occupied'` When intento abrirla Then responde 409 Conflict con "La mesa ya está ocupada"
- [ ] Given un `table_id` inexistente When intento abrirlo Then responde 404
- [ ] Given un request sin autenticación When intento abrir Then responde 401
- [ ] Given un usuario del tenant A When intento abrir una mesa del tenant B Then responde 404 (scoping de tenant)
- [ ] Given se abre una mesa When verifico la respuesta Then incluye: `id`, `number`, `status: "occupied"`, `opened_at`, `guest_count`, y un `session_token` para asociar pedidos subsecuentes

**Prioridad:** P1  
**Esfuerzo estimado:** Incluido en 5-6 días de 0.4  
**Dependencias:** HU-F0-003 (tabla tables creada)  
**Notas técnicas:**
- Nuevo router: `routers/restaurant.py` con prefijo `/api/v1/restaurant`
- Registrar en `main.py`

---

## HU-F0-005: Endpoints de Restaurante — Tomar pedido

**Como** mesero  
**Quiero** registrar los ítems del menú que un cliente solicita en una mesa  
**Para** que el pedido quede registrado y pueda enviarse a cocina.

**Criterios de aceptación:**

- [ ] Given una mesa ocupada When hago `POST /api/v1/restaurant/tables/{id}/order` con un array de `items` (cada uno: `menu_item_id`, `quantity`, `modifiers: []`, `notes`) Then se crea una orden pendiente y se retorna 201 con `order_id`, `items_count`, `total`
- [ ] Given un `menu_item_id` inexistente o desactivado When agrego al pedido Then responde 422 con "Item de menú no encontrado o no disponible"
- [ ] Given un ítem con modificadores When `modifiers` excede `max_select` del modificador Then responde 422 con validación
- [ ] Given una mesa NO ocupada (free/reserved/closed) When intento tomar pedido Then responde 409 con "La mesa no está ocupada"
- [ ] Given un pedido existente When hago `POST /api/v1/restaurant/tables/{id}/order` con más ítems Then los nuevos ítems se agregan a la orden existente (no se reemplazan)
- [ ] Given un pedido existente When hago `GET /api/v1/restaurant/orders/{order_id}` Then retorno el detalle completo: items, modificadores, notas, subtotal, estado, tiempo transcurrido

**Prioridad:** P1  
**Esfuerzo estimado:** Incluido en 5-6 días de 0.4  
**Dependencias:** HU-F0-004 (mesa abierta)  
**Notas técnicas:**
- Los items del pedido se almacenan en `kitchen_orders.items` como JSONB
- Calcular `total` sumando precio de menú + ajustes de modificadores

---

## HU-F0-006: Endpoints de Restaurante — Enviar a cocina (con WebSocket)

**Como** mesero  
**Quiero** enviar el pedido a la cocina cuando el cliente confirma  
**Para** que los cocineros vean la comanda en su pantalla y empiecen a preparar.

**Criterios de aceptación:**

- [ ] Given un pedido tomado pero no enviado When hago `POST /api/v1/restaurant/orders/{order_id}/send-to-kitchen` Then:
  - El `status` de la orden cambia a `'preparing'`
  - `sent_at` se registra con la hora actual
  - Se retorna 200 con el resumen de la comanda
- [ ] Given un pedido enviado previamente When intento re-enviar Then responde 409 con "La orden ya fue enviada a cocina"
- [ ] Given un pedido enviado a cocina When un cocinero actualiza `status` a `'ready'` via `PATCH /api/v1/restaurant/orders/{order_id}/status` con `status: "ready"` Then responde 200

#### WebSocket (comunicación en tiempo real)
- [ ] Given un pedido enviado a cocina When hay una conexión WebSocket activa en `/ws/kitchen/{tenant_id}` Then se emite un evento `new_order` con los datos de la comanda
- [ ] Given la cocina marca una orden como "ready" When hay WebSocket activo en `/ws/waiter/{tenant_id}` Then se emite un evento `order_ready` con `order_id` y `table_number`
- [ ] Given no hay conexión WebSocket When se envía pedido Then el pedido queda persistido correctamente (sin depender de WebSocket para la operación crítica)
- [ ] Given la conexión WebSocket se cae When se reconecta Then se envía el estado actual de todas las órdenes activas (full state sync)

**Prioridad:** P1  
**Esfuerzo estimado:** Incluido en 5-6 días de 0.4 + 0.5 día WebSocket  
**Dependencias:** HU-F0-005 (pedido tomado)  
**Notas técnicas:**
- WebSocket con FastAPI: dependencia `fastapi.WebSocket` + administrador de conexiones por tenant
- Ruta WebSocket: `/ws/kitchen/{tenant_id}` para pantalla de cocina, `/ws/waiter/{tenant_id}` para notificaciones a meseros
- Fallback: polling cada 10s si WebSocket no está disponible (feature flag `ws_enabled`)
- El pedido siempre se persiste en DB primero, luego se emite por WS — nunca al revés

---

## HU-F0-007: Endpoints de Restaurante — Cerrar comanda (básico)

**Como** mesero  
**Quiero** cerrar la comanda de una mesa para generar la cuenta  
**Para** que el cliente pueda pagar y la mesa quede libre.

**Criterios de aceptación:**

- [ ] Given una mesa con órdenes en estado 'served' (todas entregadas) When hago `POST /api/v1/restaurant/tables/{id}/close-order` Then:
  - Se genera un resumen de cuenta con subtotal, IGV, total, ítems consumidos
  - Se retorna 200 con el resumen
  - La mesa NO cambia de estado todavía (depende del pago)
- [ ] Given una mesa con órdenes aún en 'preparing' o 'pending' When intento cerrar comanda Then responde 409 con "Hay órdenes pendientes de servir"
- [ ] Given una mesa cerrada exitosamente When se confirma el pago (POST /api/v1/restaurant/tables/{id}/pay) Then:
  - Se integra con el sistema de ventas existente (`POST /api/sales/sale`)
  - Se registra el pago en `sale_payments`
  - La mesa vuelve a `status = 'free'`
  - Se retorna 200 con el ticket de venta

**Prioridad:** P1  
**Esfuerzo estimado:** Incluido en 5-6 días de 0.4  
**Dependencias:** HU-F0-006 (orden enviada y servida)  
**Notas técnicas:**
- Integrar con sistema de ventas existente (`services/sales_service.py`)
- Cierre básico en F0, refinamiento (D-05) pasa a F2
- Calcular IGV: 18% sobre subtotal (configurable por feature flag)

---

## HU-F0-008: Endpoints de Restaurante — Promociones básicas

**Como** mesero / administrador  
**Quiero** aplicar promociones (combos y descuentos fijos) a los pedidos  
**Para** ofrecer ofertas especiales a los clientes.

**Criterios de aceptación:**

#### CRUD de promociones
- [ ] Given un admin autenticado When hago `POST /api/v1/restaurant/promotions` con `{name, type: "combo", discount_value, conditions}` Then se crea la promoción y se retorna 201
- [ ] Given un admin autenticado When hago `GET /api/v1/restaurant/promotions` Then listo promociones activas del tenant
- [ ] Given un admin autenticado When hago `PATCH /api/v1/restaurant/promotions/{id}` con `{active: false}` Then la promoción se desactiva

#### Aplicar promoción a pedido
- [ ] Given un pedido en una mesa abierta When hago `POST /api/v1/restaurant/orders/{order_id}/apply-promotion/{promotion_id}` y se cumplen las condiciones Then el descuento se aplica y el total se recalcula
- [ ] Given una promoción de tipo `combo` con `min_items: 2` When el pedido tiene solo 1 ítem Then el descuento NO se aplica y responde 422 con "No se cumplen las condiciones de la promoción"
- [ ] Given una promoción expirada (`end_date < now`) When intento aplicarla Then responde 410 con "Promoción expirada"
- [ ] Given una promoción con `max_uses` alcanzado When intento aplicarla Then responde 409 con "Límite de usos alcanzado"

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día (0.5 backend + 0.5 frontend)  
**Dependencias:** HU-F0-005 (pedido existe)  
**Notas técnicas:**
- Descuento: si es `percentage_discount`, aplicar % sobre subtotal del pedido
- Si es `fixed_discount`, restar monto fijo
- Si es `combo`, validar que los items del pedido cumplan condiciones

---

## HU-F0-009: Ferretería — Grupos/Categorías de productos

**Como** administrador de ferretería  
**Quiero** asignar productos a grupos/categorías de 1 nivel (ej: "Fierros", "Tuberías")  
**Para** organizar el inventario y facilitar la búsqueda.

**Criterios de aceptación:**

- [ ] Given un admin autenticado When hago `POST /api/v1/inventory/categories` con `{name: "Fierros"}` Then se crea la categoría y se retorna 201
- [ ] Given un admin autenticado When hago `GET /api/v1/inventory/categories` Then listo las categorías del tenant
- [ ] Given una categoría existente When hago `POST /api/v1/accounting/kardex/products` con `{code, name, category_id}` Then el producto queda asociado a la categoría
- [ ] Given un producto con categoría When consulto `GET /api/v1/inventory/products?category=Fierros` Then solo veo productos de esa categoría
- [ ] Given una categoría sin productos asignados When intento eliminarla con `DELETE /api/v1/inventory/categories/{id}` Then se elimina correctamente (204)
- [ ] Given una categoría con productos asignados When intento eliminarla Then responde 409 con "Categoría con productos asignados"

**Prioridad:** P2  
**Esfuerzo estimado:** 0.5 día  
**Dependencias:** HU-F0-003 (estructura de productos existente)  
**Notas técnicas:**
- Tabla nueva: `product_categories` con `id, tenant_id, name, created_at, updated_at`
- Relación: `products.category_id` FK a `product_categories.id`
- 1 nivel de jerarquía (sin subcategorías)

---

## HU-F0-010: Ferretería — Ventas al por mayor y detal

**Como** vendedor de ferretería  
**Quiero** registrar ventas con precios diferenciados por cantidad (mayor/menor)  
**Para** que los clientes mayoristas tengan descuento por volumen y los minoristas paguen precio unitario.

**Criterios de aceptación:**

- [ ] Given un producto con `unit_price: 10.00`, `wholesale_price: 8.50`, `wholesale_min_qty: 12` When creo una venta con cantidad = 15 Then se aplica `wholesale_price: 8.50` por unidad
- [ ] Given el mismo producto When creo una venta con cantidad = 5 Then se aplica `unit_price: 10.00`
- [ ] Given una venta con cantidad exactamente igual a `wholesale_min_qty` When se procesa Then se aplica precio mayorista
- [ ] Given una venta mixta When hay ítems con precio unitario y otros con precio mayorista en la misma transacción Then cada ítem se calcula según su cantidad individual

#### Integración con Kárdex
- [ ] Given una venta de ferretería confirmada When se registra la salida Then se descuenta del stock en kárdex usando el costo promedio ponderado (CPP)
- [ ] Given una venta anulada When se revierte Then el stock se restablece en kárdex (contra-asiento)

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-001, sistema de ventas existente  
**Notas técnicas:**
- Modificar `POST /api/sales/sale` para aceptar `pricing_type: 'retail' | 'wholesale'` por ítem
- Alternativa: calcular automáticamente según cantidad vs `wholesale_min_qty`
- Columnas nuevas en `products`: `wholesale_price`, `wholesale_min_qty`

---

## HU-F0-011: Sidebar jerárquico con botón Salir siempre visible

**Como** usuario del sistema  
**Quiero** un menú lateral (sidebar) jerárquico que agrupe los módulos por dominio de negocio  
**Para** navegar fácilmente entre las funcionalidades, con el botón "Cerrar Sesión" siempre visible en la parte inferior izquierda.

**Criterios de aceptación:**

#### Sidebar jerárquico
- [ ] Given un usuario autenticado en cualquier página When se renderiza el layout Then el sidebar está visible con la siguiente estructura:
  ```
  🐟 El Segoviano (logo + nombre)
  ─────────────────────────────────
  ▸ 🏗️ PROYECTO DE INVERSIÓN
      📊 Dashboard   🏗️ Setup   🎮 Simulador
  ▸ 🏪 ERP
      🧾 Ventas (expandible)
      🍽️ Restaurante (expandible)
      📦 Inventario (expandible)
  ─────────────────────────────────
  🚪 Cerrar Sesión  ← SIEMPRE VISIBLE
  ```
- [ ] Given un usuario en la página Dashboard When el sidebar se renderiza Then Dashboard aparece resaltado como activo
- [ ] Given un usuario en la página Restaurante/Mesas When el sidebar se renderiza Then Restaurante está expandido y "Mesas" aparece resaltado

#### Botón "Cerrar Sesión" siempre visible
- [ ] Given un usuario autenticado en cualquier módulo o submódulo When se renderiza cualquier página Then el botón "🚪 Cerrar Sesión" está visible en la **parte inferior izquierda** del sidebar, sin importar el scroll
- [ ] Given un modal abierto (ej: modal de crear producto, modal de pago) When el modal está visible Then el botón "Cerrar Sesión" NO aparece dentro del modal
- [ ] Given un usuario en mobile (viewport < 768px) When el menú hamburguesa está abierto Then el botón "Cerrar Sesión" aparece al final del menú mobile

#### Funcionalidad de logout
- [ ] Given un usuario autenticado When hace clic en "🚪 Cerrar Sesión" Then:
  - Se ejecuta `logout()` del AuthContext
  - Se limpian tokens de sessionStorage
  - Se redirige a `/login`
  - Se muestra un mensaje de "Sesión cerrada exitosamente"
- [ ] Given un usuario en el flujo de logout When la API responde error Then la sesión se cierra igualmente (cleanup local forzado)

#### Colapsabilidad
- [ ] Given el sidebar visible When hago clic en "▸ 🏪 ERP" Then los submódulos se expanden/contraen con animación suave
- [ ] Given los submódulos de ERP expandidos When selecciono un submódulo Then el sidebar mantiene el estado expandido

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día (resuelve D-08 y D-09)  
**Dependencias:** Ninguna (puede hacerse en paralelo al backend)  
**Notas técnicas:**
- Modificar `AppShell.tsx`: reemplazar navegación lineal por sidebar jerárquico
- Componentes: `Sidebar.tsx`, `SidebarSection.tsx`, `SidebarItem.tsx`
- Estado colapsable: `useState` o `useReducer` con key en sessionStorage para persistir preferencias
- Botón "Salir": CSS `position: fixed` o `sticky` dentro del sidebar, en la parte inferior
- NO va en modales (cliente confirmó explícitamente)

---

## HU-F0-012: Rutas frontend organizadas por dominio

**Como** desarrollador frontend  
**Quiero** reorganizar las rutas del frontend agrupadas por dominio de negocio  
**Para** que la estructura del código refleje la organización de módulos.

**Criterios de aceptación:**

- [ ] Given la estructura actual de rutas planas (`/kardex`, `/cashflow`, `/caja`, `/ventas`) When se migra a la nueva estructura Then:
  - `/kardex` → `/inventario/kardex`
  - `/cashflow` → `/finanzas/cashflow`
  - `/caja` → `/ventas/pos`
  - `/ventas/nueva` → `/ventas/nueva`
  - `/ventas` → `/ventas/historial`
  - `/reportes` → `/inversiones/reportes`
- [ ] Given las rutas nuevas configuradas When un usuario hace clic en un enlace del sidebar Then la navegación funciona correctamente
- [ ] Given un usuario que tenía un marcador/bookmark en la ruta antigua When accede Then el frontend redirige 301 a la nueva ruta sin perder el estado de la aplicación
- [ ] Given las páginas agrupadas en `pages/investment/`, `pages/ventas/`, `pages/inventario/`, `pages/finanzas/` y `pages/config/` When verifico el code-splitting Then cada página sigue siendo un chunk independiente (React.lazy intacto)

**Prioridad:** P2  
**Esfuerzo estimado:** 0.5 día  
**Dependencias:** HU-F0-011 (sidebar con estructura definida)  
**Notas técnicas:**
- Mover archivos de `pages/` plano a `pages/{dominio}/`
- Actualizar imports en `App.tsx` (React.lazy)
- Agregar redirects: `<Route path="/kardex" element={<Navigate to="/inventario/kardex" />} />`
- NO romper enlaces del E2E tests — actualizar también Playwright specs

---

## HU-F0-013: Takeaway — Pedidos para llevar

**Como** cliente / cajero  
**Quiero** registrar pedidos para llevar (takeaway) sin asociar a una mesa  
**Para** que los clientes puedan pedir comida y recogerla en el local.

**Criterios de aceptación:**

- [ ] Given un cajero autenticado When hago `POST /api/v1/restaurant/takeaway` con `{customer_name, customer_phone, items: [{menu_item_id, quantity, modifiers}], pickup_time}` Then se crea el pedido takeaway con status `'pending'` y se retorna 201 con `order_id` y `estimated_pickup_time`
- [ ] Given un pedido takeaway creado When el sistema procesa la creación Then se envía automáticamente a cocina (HU-F0-006) sin intervención manual
- [ ] Given un pedido takeaway When hago `GET /api/v1/restaurant/takeaway?status=pending` Then listo pedidos pendientes de preparar
- [ ] Given un pedido takeaway listo (`status = 'ready'`) When hago `PATCH /api/v1/restaurant/takeaway/{id}/pickup` Then el status cambia a `'picked_up'` y se registra `picked_up_at`
- [ ] Given un pedido takeaway no recogido después de 30 minutos de `pickup_time` When consulto el listado Then aparece con indicador visual "⚠️ Atrasado"

**Prioridad:** P1  
**Esfuerzo estimado:** Incluido en 5-6 días de 0.4  
**Dependencias:** HU-F0-003 (tabla takeaway_orders), HU-F0-006 (envío cocina)  
**Notas técnicas:**
- No requiere mesa — el pedido va directo a cocina
- Integrar con sistema de ventas al momento de pago (como en HU-F0-007)
- Cola de espera: ordenada por `pickup_time` ascendente

---

## HU-F0-014: Páginas frontend para Restaurante

**Como** mesero / cajero / administrador  
**Quiero** interfaces visuales para gestionar mesas, menú, comandas, takeaway y promociones  
**Para** operar el restaurante desde el sistema.

**Criterios de aceptación:**

#### Mapa de mesas (TablesPage)
- [ ] Given un usuario con rol `waiter` o superior When accede a `/restaurante/mesas` Then ve un mapa visual con todas las mesas del salón, cada una con:
  - Número de mesa
  - Estado (colores: 🟢 libre, 🟡 ocupada, 🔴 reservada, ⚫ cerrada)
  - Capacidad (ej: "4 pax")
  - Al hacer clic en mesa libre → opción "Abrir mesa"
  - Al hacer clic en mesa ocupada → opción "Ver pedido" y "Cerrar cuenta"
- [ ] Given una mesa ocupada When hago clic en "Ver pedido" Then se abre una vista detallada con los ítems consumidos, total parcial y opción "Agregar ítems"

#### Página de Menú (MenuPage)
- [ ] Given un admin autenticado When accede a `/restaurante/menu` Then ve el listado de ítems del menú agrupados por categoría, con precio, disponibilidad y opción de editar
- [ ] Given un admin When hace clic en "Nuevo ítem" Then se abre un formulario con: nombre, descripción, categoría, precio, costo, unidad, modificadores, imagen
- [ ] Given un admin When edita un ítem y cambia `available: false` Then el ítem deja de aparecer en el menú del POS/mesero

#### Pantalla de Comandas (KitchenOrdersPage)
- [ ] Given un cocinero autenticado When accede a `/restaurante/comandas` Then ve una pantalla tipo "tablero Kanban" con columnas: Pendiente → Preparando → Listo
- [ ] Given una nueva orden enviada a cocina When la pantalla está abierta (con WebSocket activo) Then aparece automáticamente en la columna "Pendiente" sin recargar la página
- [ ] Given un cocinero When hace clic en "Iniciar preparación" sobre una orden pendiente Then la orden pasa a la columna "Preparando"
- [ ] Given un cocinero When hace clic en "Listo" sobre una orden en preparación Then la orden pasa a "Listo" y se notifica al mesero (WebSocket)

#### Takeaway Page
- [ ] Given un cajero When accede a `/restaurante/takeaway` Then ve un listado de pedidos takeaway ordenados por hora de recogida, con estados: Pendiente, En preparación, Listo, Recogido
- [ ] Given un cajero When hace clic en "Nuevo takeaway" Then se abre un formulario con: nombre del cliente, teléfono, selección de ítems del menú, hora de recogida estimada
- [ ] Given un pedido takeaway marcado como "Listo" When pasan 30+ minutos sin recoger Then el pedido aparece destacado en rojo como "Atrasado"

#### Promociones Page
- [ ] Given un admin When accede a `/restaurante/promociones` Then ve el listado de promociones activas e inactivas
- [ ] Given un admin When hace clic en "Nueva promoción" Then se abre un formulario con: nombre, tipo (combo/descuento fijo/porcentaje/happy hour), valor del descuento, condiciones, fechas de vigencia, límite de usos

#### Estados de carga
- [ ] Given cualquier página de Restaurante cargando When la data no ha llegado Then se muestra un `<Skeleton />` animado
- [ ] Given cualquier página con error de red When la API falla Then se muestra un banner de error con botón "Reintentar"
- [ ] Given cualquier página sin datos When no hay mesas/ítems/órdenes creadas Then se muestra un estado vacío con mensaje amigable y CTA

**Prioridad:** P1  
**Esfuerzo estimado:** 5 días (3 según plan original, ajustado a 5 por complejidad)  
**Dependencias:** HU-F0-003 a HU-F0-008 (endpoints backend)  
**Notas técnicas:**
- Kanban de cocina: usar librería como `react-beautiful-dnd` o `@dnd-kit` para drag & drop entre columnas
- Mapa de mesas: grid visual con posiciones configurables (feature flag)
- WebSocket: mismo canal que HU-F0-006
- Priorizar: Mapa de mesas > Comandas > Takeaway > Menú > Promociones

---

## HU-F0-015: Ferretería — Frontend de ventas y grupos

**Como** vendedor de ferretería  
**Quiero** una interfaz para registrar ventas con precios mayoristas/menoristas y gestionar categorías de productos  
**Para** operar el negocio de compra/venta desde el sistema.

**Criterios de aceptación:**

- [ ] Given un vendedor en `/ventas/pos` When selecciona un producto con `wholesale_price` y la cantidad supera `wholesale_min_qty` Then el precio unitario mostrado cambia automáticamente al precio mayorista
- [ ] Given el POS de ferretería When se muestra la interfaz Then los productos se filtran por categoría (combobox o tabs)
- [ ] Given un admin When accede a `/inventario/productos` Then ve una tabla con: código, nombre, categoría, stock, precio unitario, precio mayorista, cant. mín. mayorista
- [ ] Given un admin When hace clic en "Editar" sobre un producto Then puede modificar `wholesale_price` y `wholesale_min_qty`
- [ ] Given un admin When accede a `/inventario/categorias` Then puede crear, editar y eliminar categorías de 1 nivel

**Prioridad:** P2  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-009 (grupos backend), HU-F0-010 (precios mayoristas backend)  
**Notas técnicas:**
- Reutilizar componentes existentes de SaleForm y Kardex
- Agregar columnas de precio mayorista a la tabla de productos

---

## HU-F0-016: Testing integral de Fase 0

**Como** desarrollador  
**Quiero** pruebas automatizadas que validen todas las funcionalidades de Fase 0  
**Para** asegurar calidad antes de pasar a Fase 1.

**Criterios de aceptación:**

#### Backend — Tests unitarios
- [ ] Given los nuevos modelos ORM de Restaurante When ejecuto pytest Then hay tests que verifican:
  - Creación correcta de cada modelo con datos válidos
  - Constraints UNIQUE, CHECK y FK se respetan
  - Scoping de tenant_id se aplica automáticamente
- [ ] Given los endpoints de Restaurante When ejecuto pytest Then hay tests para:
  - Abrir/cerrar mesa (éxito y casos borde)
  - Tomar pedido con/sin modificadores
  - Enviar a cocina y cambiar estados
  - Aplicar promociones (éxito, condiciones no cumplidas, expiradas)

#### Backend — Tests de integración HTTP
- [ ] Given FastAPI TestClient configurado When ejecuto `pytest tests/test_restaurant_routes.py` Then todos los endpoints REST de Restaurante se prueban con requests HTTP simuladas
- [ ] Given los tests de integración When se ejecutan Then verifican códigos HTTP (200, 201, 4xx), estructura de respuesta JSON y persistencia en DB

#### Frontend — Tests de componentes
- [ ] Given los componentes de Restaurante When ejecuto `npx jest` Then hay tests para:
  - TablesMap: renderiza mesas con estados correctos
  - KitchenKanban: muestra órdenes y permite cambiar estados
  - MenuForm: validación de campos obligatorios
  - TakeawayForm: creación de pedido takeaway

#### Frontend — Tests E2E
- [ ] Given Playwright configurado When ejecuto `npx playwright test` Then hay un flujo E2E que:
  - Inicia sesión como admin
  - Navega al sidebar y expande "Restaurante"
  - Abre una mesa
  - Toma un pedido del menú
  - Envía a cocina
  - Marca como listo
  - Cierra la cuenta

#### WebSocket
- [ ] Given WebSocket implementado When ejecuto pytest Then hay tests que verifican:
  - Conexión exitosa a `/ws/kitchen/{tenant_id}`
  - Recepción de evento `new_order` al enviar pedido a cocina
  - Recepción de evento `order_ready` al marcar orden como lista
  - Reconexión y full state sync

**Prioridad:** P2  
**Esfuerzo estimado:** 1 día  
**Dependencias:** Todas las HU anteriores de F0  
**Notas técnicas:**
- Tests de WebSocket con `pytest-asyncio` y WebSocketTestClient de Starlette/FastAPI
- Mínimo: 80% de cobertura en código nuevo de F0
- NO bloquear entrega de F0 por cobertura < 80% (aceptar deuda temporal)
- Meta: 100% de los escenarios Gherkin cubiertos por al menos 1 test

---

# Apéndice: Resumen de Cobertura Gherkin vs Actividades del Plan

| Actividad Plan | HU Gherkin | Estado | Esfuerzo |
|:--------------:|:----------:|:------:|:--------:|
| 0.1 Multitenant | HU-F0-001 | ✅ 8 escenarios | 3-4 días |
| 0.2 Business type | HU-F0-002 | ✅ 6 escenarios | 0.5 día |
| 0.3 Modelos Restaurante | HU-F0-003 | ✅ 7 sub-tablas validadas | 2.5 días |
| 0.4 Endpoints Restaurante | HU-F0-004 a F0-008 | ✅ ~30 escenarios | 5-6 días |
| 0.5 Ferretería básico | HU-F0-010 | ✅ 6 escenarios | 1 día |
| 0.6 Frontend Restaurante | HU-F0-014 | ✅ ~20 escenarios | 5 días |
| 0.7 Frontend Ferretería | HU-F0-015 | ✅ 5 escenarios | 1 día |
| 0.9 Grupos productos | HU-F0-009 | ✅ 6 escenarios | 0.5 día |
| 0.10 Sidebar + Salir | HU-F0-011 | ✅ ~10 escenarios | 1 día |
| 0.11 Rutas por dominio | HU-F0-012 | ✅ 5 escenarios | 0.5 día |
| WebSockets | HU-F0-006 (anexo) | ✅ 5 escenarios | 0.5 día |
| Testing F0 | HU-F0-016 | ✅ ~15 escenarios | 1 día |
| **TOTAL** | **15 HU** | **~100+ escenarios** | **~18.5-21 días** |

---

> **Próximo paso:** Revisar con el Arquitecto de Sistemas y el Product Owner para validar escenarios antes de pasar a implementación.  
> **Formato basado en:** Gherkin (Given/When/Then) — estándar BDD  
> **Nota:** Las User Stories se afinarán con el archivo actualizado de Ron.
