# Backlog Gherkin — Fase 0 (ERP MVP)

**Proyecto:** IaaS-RonSys  
**Origen:** Plan Integral v3 §13.1 + Architecture Agent analysis  
**Generado por:** PO Agent 📋  
**Fecha:** 2026-05-14  
**Branch:** `fase0-real`  
**Commit base:** `6bfd61a` (snapshot pre-upgrade)  
**Total Historias:** 16  
**Ficha técnica:** Architecture Agent 🏗️ (2026-05-14) — decisiones incorporadas

---

# Fase 0 — MVP Restaurante + Ferretería Básico

**Objetivo:** Sistema funcional con ventas, inventario básico (con seriales opcionales), y módulo Restaurante (salones, menú, comandas, takeaway, promociones básicas).  
**Esfuerzo total estimado:** 17.5 días (backend 12.5d + frontend 4.5d + equipo 0.5d)  
**Dependencia externa:** Ninguna — se construye sobre lo ya existente en `6bfd61a`.

## ✅ Ya Implementado en 6bfd61a (punto de partida)

| Componente | Estado |
|------------|:------:|
| Migraciones 0001-0006 | ✅ |
| Auth JWT + refresh tokens + RBAC | ✅ |
| Motor contable (engine, kárdex, ratios) | ✅ |
| Sales/POS (9 endpoints + 6 tablas) | ✅ |
| Cashflow proyectado | ✅ |
| Business type enum | ✅ |
| X-Tenant-ID middleware | ✅ |
| Frontend: Login, Dashboard, POS, Sales, Kardex, Cashflow, Setup, Settings | ✅ |

---

## Historias Nuevas (15)

---

### HU-F0-001: Estandarizar multitenant — documentar equivalencia `company_id` = `tenant_id`

**Como** arquitecto del sistema  
**Quiero** que la documentación y el código dejen clara la equivalencia entre `company_id` (DB) y `tenant_id` (código)  
**Para** eliminar ambigüedad sin riesgo de rename masivo de columnas en Fase 0.

**Decisión Architecture Agent aplicada (2026-05-14):** NO renombrar columnas. Mantener `company_id` en DB con property wrapper `tenant_id` en código. Los 11 modelos usan `company_id` en DB. El código Python ya usa `tenant_id` como nombre de variable (~155 referencias). Hacer `ALTER TABLE RENAME COLUMN` en 11 tablas es destructivo (FKs, índices, constraints) y arriesga romper 9 endpoints funcionales. El rename real va en Fase 3 (cuando haya tests de integración HTTP).

**Contexto:** El middleware `get_tenant_id()` extrae correctamente el header `X-Tenant-ID`, el código Python usa `tenant_id` como variable, pero las columnas DB se llaman `company_id`. Son equivalentes.

**Criterios de aceptación:**
- [ ] Given el modelo base SQLAlchemy When se consulta `model.tenant_id` Then retorna `self.company_id` (property wrapper que documenta la equivalencia)
- [ ] Given el `README.md` o `docs/arquitectura.md` When se lee la sección multi-tenant Then explica: "En base de datos la columna es `company_id`. En código Python es `tenant_id`. Son el mismo valor extraído del header `X-Tenant-ID`."
- [ ] Given los modelos nuevos de Fase 0 (restaurant, product_units, product_categories) When se crean Then usan `company_id` para mantener consistencia con el esquema existente
- [ ] Given los routers/servicios When reciben `tenant_id = Depends(get_tenant_id)` Then lo pasan a queries como `Model.company_id == tenant_id` sin ambigüedad
- [ ] Given el cambio When ejecuto `pytest tests/ -v` Then los 140 tests pasan sin modificaciones

**Prioridad:** P0  
**Esfuerzo estimado:** 0.3 días  
**Dependencias:** Ninguna  
**Riesgo:** 🟢 Bajo — solo documentación + property wrapper, no toca DB.  
**Notas técnicas:**
- Crear `BaseModel` con `@property tenant_id → self.company_id` si no existe
- Actualizar `docs/arquitectura.md` o `README.md`
- El rename real (`ALTER TABLE RENAME COLUMN`) queda programado para Fase 3

---

### HU-F0-002: Modelos y migración — Restaurante (tables, menu_items, kitchen_orders)

**Como** desarrollador backend  
**Quiero** que existan las tablas `tables`, `menu_items` y `kitchen_orders` con sus modelos SQLAlchemy  
**Para** que el módulo de Restaurante pueda gestionar salones, carta y comandas.

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `tables` con columnas: id, tenant_id, number (VARCHAR(10)), capacity (INT), status (VARCHAR: 'available'|'occupied'|'reserved'|'cleaning'), section (VARCHAR(50)), created_at, updated_at
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `menu_items` con columnas: id, tenant_id, name, description, price, cost_price, category (VARCHAR(30)), item_type (VARCHAR: 'food'|'beverage'|'dessert'|'combo'), modifiers (JSON), image_url, active (BOOL), created_at, updated_at
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `kitchen_orders` con columnas: id, sale_id (FK UNIQUE), table_id (FK → tables.id), status (VARCHAR CHECK: 'pending'|'preparing'|'ready'|'served'|'cancelled'), priority (VARCHAR CHECK: 'normal'|'rush' DEFAULT 'normal'), items (JSON), notes (TEXT), ordered_at, started_at, completed_at
- [ ] Given inserto un `menu_item` con modifiers JSON `[{"name": "Sin cebolla", "price": 0}, {"name": "Extra queso", "price": 3.50}]` When consulto el item Then el campo modifiers preserva la estructura
- [ ] Given una mesa con status='available' When la actualizo a 'occupied' Then el CHECK constraint permite el cambio
- [ ] Given una mesa con status='occupied' When intento setear status='invalid_status' Then el CHECK constraint rechaza la operación

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F0-001 (tenant_id debe estar estandarizado para evitar doble migración)  
**Notas técnicas:**
- Modelos en `adapters/db/models/restaurant.py` (nuevo archivo)
- Migración: `0008_restaurant_core`
- `menu_items.modifiers`: JSON array of {name, price, max_select (opcional)}
- `kitchen_orders.items`: JSON array of {menu_item_id, name, quantity, modifiers_applied[], notes}
- Índices: `idx_tables_tenant_status` ON tables(tenant_id, status), `idx_menu_items_tenant_category` ON menu_items(tenant_id, category)
- Schemas Pydantic en `schemas/restaurant.py`

---

### HU-F0-003: Modelos y migración — Restaurante (takeaway_orders, promotions)

**Como** desarrollador backend  
**Quiero** que existan las tablas `takeaway_orders` y `promotions` con sus modelos SQLAlchemy  
**Para** que el restaurante pueda gestionar pedidos para llevar y promociones.

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `takeaway_orders` con: id, sale_id (FK UNIQUE), customer_name (VARCHAR(200)), customer_phone (VARCHAR(20)), pickup_time (TIMESTAMPTZ), status (VARCHAR CHECK: 'pending'|'preparing'|'ready'|'delivered'|'cancelled'), notes (TEXT), created_at
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `promotions` con: id, tenant_id, name (VARCHAR(100)), description (TEXT), promo_type (VARCHAR CHECK: 'combo'|'discount_pct'|'discount_amount'|'2x1'), rules (JSON), discount_value (NUMERIC), valid_from (DATE), valid_to (DATE), active (BOOL), max_uses (INT nullable), created_at
- [ ] Given una promoción tipo 'combo' When inserto con rules `{"items": [1, 2, 3], "combo_price": 45.00}` Then el JSON se almacena correctamente
- [ ] Given una promoción tipo 'discount_pct' When inserto con `discount_value: 15.00` Then representa 15% de descuento
- [ ] Given una promoción con `valid_to < today` When consulto promociones activas Then esta promoción NO se incluye (filtro en queries)
- [ ] Given `promo_type='bogof'` (buy one get one free) When inserto con rules `{"buy_item_id": 5, "get_item_id": 5, "min_quantity": 2}` Then la lógica se documenta para implementar en HU-F0-005

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** HU-F0-002 (misma migración `0008_restaurant_core` o `0009_restaurant_extras`)  
**Notas técnicas:**
- Misma migración que HU-F0-002 o separada (0009)
- `promotions.rules`: JSON flexible según promo_type. Documentar schema para cada tipo.
- `takeaway_orders` comparte FK con `sales` (1:1, similar a restaurant_sales)
- Schemas Pydantic en `schemas/restaurant.py`

---

### HU-F0-004: Servicio y endpoints de Restaurante (mesas, menú, comandas)

**Como** mesero / administrador de restaurante  
**Quiero** endpoints para gestionar mesas, menú y comandas  
**Para** operar el salón: abrir mesas, tomar pedidos, enviar a cocina y cerrar cuentas.

**Criterios de aceptación:**
- [ ] Given un restaurante configurado When hago `GET /api/restaurant/tables` Then obtengo la lista de mesas con estado actual y filtro opcional `?status=available`
- [ ] Given una mesa 'available' When hago `POST /api/restaurant/tables/{id}/open` con `{"guests": 4, "waiter_name": "Carlos"}` Then la mesa cambia a 'occupied' y se retorna 200 con el objeto actualizado
- [ ] Given una mesa 'occupied' When hago `POST /api/restaurant/tables/{id}/open` Then responde 409 "Mesa ya está ocupada"
- [ ] Given el menú When hago `GET /api/restaurant/menu?category=platos` Then obtengo items filtrados por categoría
- [ ] Given un pedido When hago `POST /api/restaurant/kitchen-orders` con `{"table_id": 5, "items": [{"menu_item_id": 10, "quantity": 2, "modifiers": ["Sin cebolla"]}]}` Then se crea `kitchen_order` con status 'pending', se asocia al `sale_id` de la venta activa de la mesa, y se retorna 201
- [ ] Given una comanda en cocina When hago `PATCH /api/restaurant/kitchen-orders/{id}/status` con `{"status": "preparing"}` Then se actualiza el estado con timestamp `started_at`
- [ ] Given una comanda 'preparing' When hago `PATCH` a 'ready' Then se registra `completed_at`
- [ ] Given una mesa ocupada When hago `POST /api/restaurant/tables/{id}/close` Then se cierra la cuenta (genera venta si hay pedidos pendientes), la mesa vuelve a 'available', y se retorna 200 con resumen de consumo
- [ ] Given una mesa sin pedidos When hago close Then responde 200 y la mesa se libera (sin generar venta)
- [ ] Given el endpoint sin autenticación When consulto Then responde 401

**Prioridad:** P0  
**Esfuerzo estimado:** 3 días  
**Dependencias:** HU-F0-002, HU-F0-003 (tablas deben existir)  
**Notas técnicas:**
- Router: `routers/restaurant.py` con prefix `/api/restaurant`
- Servicio: `services/restaurant_service.py` — orquesta mesas, menú, comandas
- Flujo de comanda: abrir mesa → crear kitchen_order (pending) → cocina actualiza (preparing → ready → delivered) → mesero cierra mesa → se crea Sale (usando SaleService existente) + restaurant_sales
- `PATCH /kitchen-orders/{id}/status`: validar transiciones de estado permitidas
- `POST /tables/{id}/close`: integrar con `SalesService.create_sale()` para generar la venta final

---

### HU-F0-005: Lógica de promociones (combos, descuentos)

**Como** administrador de restaurante  
**Quiero** que el sistema aplique promociones automáticamente al calcular el total de una venta  
**Para** ofrecer combos y descuentos sin que el mesero tenga que calcularlos manualmente.

**Criterios de aceptación:**
- [ ] Given una promoción tipo 'combo' activa con items [1,2,3] y combo_price=45 When una venta incluye exactamente esos 3 items Then el total se ajusta a 45.00 en lugar de Σ precios individuales
- [ ] Given una promoción tipo 'discount_pct' de 15% When la venta se cierra en un día laborable (lun-vie) Then se aplica 15% de descuento al subtotal (antes de IGV)
- [ ] Given una promoción tipo 'discount_fixed' de S/ 10 When el subtotal supera S/ 50 Then se descuentan S/ 10 del total
- [ ] Given una promoción BOGOF (buy one get one free) con `min_quantity: 2` When la venta incluye 2 unidades del mismo item Then una unidad se cobra a S/ 0
- [ ] Given promociones solapadas (combo + descuento) When se calcula el total Then se aplica la de mayor beneficio para el cliente (no se acumulan)
- [ ] Given una promoción con `valid_to` expirada When se calcula el total Then NO se aplica
- [ ] Given la promoción se aplica When el ticket/detalle de venta muestra "Promoción: [nombre] -S/ XX.XX"

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-003 (tabla promotions), HU-F0-004 (endpoints restaurante)  
**Notas técnicas:**
- Servicio: `services/promotion_service.py` con `apply_promotions(sale_items, tenant_id) -> (adjusted_items, total_discount, applied_promotions[])`
- Evaluar en `SalesService.create_sale()` antes de calcular totales finales
- Regla de no acumulación: ordenar promociones por beneficio y aplicar solo la mejor (o regla configurable)
- `bogof`: cada 2 unidades del mismo producto, 1 gratis (división entera de qty/2)

---

### HU-F0-006: Frontend Restaurante — Mapa de Mesas

**Como** mesero  
**Quiero** ver un mapa visual de las mesas del salón con sus estados  
**Para** saber rápidamente qué mesas están libres, ocupadas o pendientes de limpieza.

**Criterios de aceptación:**
- [ ] Given estoy en `/restaurante/mesas` When la página carga Then veo un grid de mesas con número, capacidad y color de estado (verde=available, rojo=occupied, amarillo=reserved, gris=cleaning)
- [ ] Given paso el mouse sobre una mesa ocupada When muestro el tooltip Then veo: número de comensales, mesero asignado, hora de apertura, total acumulado provisional
- [ ] Given hago clic en una mesa 'available' When se abre el modal Then puedo ingresar número de comensales y nombre del mesero para abrirla
- [ ] Given hago clic en una mesa 'occupied' When se abre el drawer lateral Then veo los pedidos activos de esa mesa con opción de agregar items del menú
- [ ] Given estoy en móvil (viewport < 768px) When veo el mapa de mesas Then las mesas se muestran en lista vertical en lugar de grid (más fácil de tocar)
- [ ] Given el endpoint de mesas falla When cargo la página Then se muestra error con botón "Reintentar"
- [ ] Given el mapa de mesas When llega una actualización de estado (otro mesero cambió una mesa) Then se refresca automáticamente (polling cada 30s)

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-004 (endpoints mesas)  
**Notas técnicas:**
- Componentes: `TablesMap.tsx` (grid responsivo), `TableCard.tsx`, `OpenTableModal.tsx`, `TableDetailDrawer.tsx`
- Hook: `useTables()` con polling opcional (SWR o React Query)
- Colores de estado vía Tailwind: `bg-green-100 border-green-500`, `bg-red-100 border-red-500`, etc.
- Tests: renderizado de cada estado, modal open/close, polling

---

### HU-F0-007: Frontend Restaurante — Menú digital + Toma de Pedido

**Como** mesero  
**Quiero** un menú digital desde el cual pueda agregar ítems al pedido de una mesa  
**Para** tomar órdenes rápidamente y enviarlas a cocina sin papel.

**Criterios de aceptación:**
- [ ] Given estoy en el drawer de una mesa ocupada When veo el menú Then los items están agrupados por categoría (Platos, Bebidas, Postres, Combos) con foto (si tiene), nombre, precio y botón "Agregar"
- [ ] Given un item del menú tiene modifiers When hago clic en "Agregar" Then se abre modal para seleccionar modificadores (ej. "Sin cebolla", "Término medio", "Extra queso +S/3.50")
- [ ] Given selecciono modificadores y cantidad When confirmo Then el item se agrega al ticket de la mesa con los modificadores aplicados y precio ajustado
- [ ] Given el ticket de la mesa tiene items When reviso Then muestra: nombre del item, cantidad, modificadores, precio unitario, subtotal
- [ ] Given el ticket tiene items When presiono "Enviar a Cocina" Then se crea la kitchen_order, el ticket se limpia, y se muestra confirmación "Comanda enviada ✅"
- [ ] Given busco un item por nombre When escribo en el buscador Then el menú se filtra en tiempo real
- [ ] Given un item está agotado (active=false) When veo el menú Then aparece en gris con etiqueta "Agotado" y no se puede agregar

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-004 (endpoints menú, kitchen_orders), HU-F0-006 (mapa de mesas)  
**Notas técnicas:**
- Componentes: `MenuGrid.tsx`, `MenuItemCard.tsx`, `ModifierModal.tsx`, `TableTicket.tsx`
- Estado del ticket en React context `TableOrderContext` (un ticket por mesa activa)
- `ModifierModal`: renderiza lista de modificadores con checkbox, precio extra se suma al item
- Buscador: `useMemo` con filter por `item.name.toLowerCase()`
- Tests: búsqueda, modifiers, enviar comanda, item agotado

---

### HU-F0-008: Frontend Restaurante — Pantalla de Cocina

**Como** cocinero  
**Quiero** una pantalla que muestre las comandas pendientes en tiempo real  
**Para** saber qué preparar y en qué orden, y marcar los platos como listos.

**Criterios de aceptación:**
- [ ] Given estoy en `/restaurante/cocina` (pantalla de cocina) When la página carga Then veo columnas tipo Kanban: Pendientes, Preparando, Listos, Entregados
- [ ] Given una comanda en "Pendientes" When arrastro la tarjeta a "Preparando" Then se hace `PATCH` al endpoint y la tarjeta se mueve de columna
- [ ] Given una comanda en "Preparando" When presiono el botón "✅ Listo" Then la tarjeta se mueve a "Listos" con timestamp
- [ ] Given nuevas comandas llegan When la pantalla está abierta Then aparecen automáticamente en "Pendientes" (polling cada 10s o WebSocket)
- [ ] Given una comanda pendiente tiene más de 15 minutos When el tiempo excede Then la tarjeta se resalta en naranja (warning); >30 min en rojo (crítico)
- [ ] Given la pantalla de cocina When está en un monitor grande (1920x1080) Then se optimiza para vista horizontal con fuente grande legible a distancia
- [ ] Given presiono "🗑️ Cancelar" en una comanda When confirmo Then la comanda pasa a estado 'cancelled' con motivo (modal para ingresar razón)

**Prioridad:** P0  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** HU-F0-004 (endpoint kitchen_orders)  
**Notas técnicas:**
- Componentes: `KitchenKanban.tsx`, `KitchenOrderCard.tsx`, `KitchenColumn.tsx`
- Polling con `setInterval` cada 10s o `useSWR` con `refreshInterval`
- Estados coloreados: pending=gris, preparing=azul, ready=verde, delivered=gris-claro
- Timer: `ordered_at` → calcular minutos transcurridos con `Date.now() - new Date(order.ordered_at)`
- Tests: drag and drop (simulado), polling, timer warning, cancel

---

### HU-F0-009: Frontend Restaurante — TakeAway y Promociones

**Como** mesero / administrador  
**Quiero** pantallas para gestionar pedidos TakeAway y administrar promociones  
**Para** ofrecer servicio completo de restaurante.

**Criterios de aceptación:**
- [ ] Given estoy en `/restaurante/takeaway` When la página carga Then veo formulario: nombre del cliente, teléfono, hora estimada de recojo, y selector de items del menú (igual que HU-F0-007 pero sin mesa)
- [ ] Given completo el pedido takeaway When presiono "Confirmar Pedido" Then se crea la venta + takeaway_order, y se muestra pantalla de confirmación con número de pedido y hora estimada
- [ ] Given pedidos takeaway activos When veo la lista Then se muestran en estados: Pendiente, Preparando, Listo, Recogido
- [ ] Given estoy en `/restaurante/promociones` When la página carga Then veo la lista de promociones activas con: nombre, tipo, descuento, vigencia
- [ ] Given soy admin When veo promociones Then puedo crear nueva promoción seleccionando tipo, items involucrados, valor de descuento y fechas
- [ ] Given una promoción activa When presiono "Desactivar" Then `active=false` y la UI lo refleja inmediatamente

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-003 (tablas), HU-F0-004 (endpoints), HU-F0-005 (lógica promos)  
**Notas técnicas:**
- Componentes: `TakeAwayForm.tsx`, `TakeAwayList.tsx`, `PromotionsList.tsx`, `PromotionForm.tsx`
- TakeAway reutiliza `MenuGrid` y `ModifierModal` de HU-F0-007
- Promotions admin: formulario con selects para items, date pickers para vigencia
- Tests: flujo takeaway completo, CRUD promociones

---

### HU-F0-010: POS — Precios mayorista/detal en productos

**Como** administrador de ferretería  
**Quiero** que cada producto tenga precio minorista y mayorista (con cantidad mínima)  
**Para** vender al por mayor y detal con precios diferenciados automáticamente.

**Criterios de aceptación:**
- [ ] Given el modelo `Product` When se ejecuta la migración Then se agregan columnas: `retail_price NUMERIC(12,2)`, `wholesale_price NUMERIC(12,2)`, `wholesale_min_qty NUMERIC(12,2)`, `barcode VARCHAR(50) UNIQUE`
- [ ] Given un producto con `wholesale_min_qty=10` y `wholesale_price=8.50` When registro una venta con cantidad 12 Then el sistema aplica automáticamente precio mayorista (S/ 8.50) en lugar del precio retail
- [ ] Given un producto con `wholesale_min_qty=10` When registro una venta con cantidad 5 Then se aplica precio retail (no mayorista)
- [ ] Given un producto SIN wholesale_price (NULL) When registro cualquier cantidad Then siempre se usa `retail_price`
- [ ] Given el endpoint `POST /api/accounting/kardex/products` When creo un producto Then acepta los nuevos campos opcionales
- [ ] Given `GET /api/accounting/kardex/products` When consulto Then la respuesta incluye `retail_price`, `wholesale_price`, `wholesale_min_qty`, `barcode`
- [ ] Given el frontend de registro de producto When creo/edito un producto Then puedo ingresar precio retail, precio mayorista, cantidad mínima mayorista y código de barras

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-001 (tenant_id estandarizado preferible)  
**Notas técnicas:**
- Migración: `0010_product_pricing_barcode`
- SQLAlchemy: añadir columnas a `Product` en `models/accounting.py`: `retail_price NUMERIC(12,2)`, `wholesale_price NUMERIC(12,2)`, `wholesale_min_qty NUMERIC(12,2)`, `barcode VARCHAR(50) UNIQUE`, `warranty_months INT DEFAULT 0`, `manufacturer VARCHAR(100)`
- Schema Pydantic: `ProductCreate` y `ProductResponse` extendidos
- Lógica en `sales_service.py`: ya existe código que chequea `wholesale_price`. Solo necesita los campos en el modelo.
- Documentar: `retail_price` = precio de lista/catálogo. `unit_price` en `sale_items` = precio efectivo de venta (puede diferir por descuento/promoción). `barcode` = código de barras escaneable (opcional, sin lógica de escáner en F0).

---

### HU-F0-011: Seriales en inventario — modelo y migración

**Como** administrador de ferretería  
**Quiero** que los productos puedan tener números de serie individuales para trazabilidad  
**Para** saber exactamente qué unidad vendí a qué cliente (ej. herramientas, equipos).

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `product_units` con: id, product_id (FK), serial_number (VARCHAR(100) UNIQUE), status (VARCHAR CHECK: 'available'|'sold'|'reserved'|'rma'), purchase_date (DATE), cost_price (NUMERIC(12,2)), warranty_expiry (DATE, calculado: purchase_date + product.warranty_months), sale_id (FK → sales.id nullable), sale_item_id (FK nullable), notes (TEXT), created_at
- [ ] Given la migración ejecutada When verifico la DB Then la tabla `products` tiene nueva columna `has_serial BOOLEAN DEFAULT FALSE`
- [ ] Given un producto `has_serial=true` When inserto 5 seriales en `product_units` con status='available' Then `current_stock` del producto debe coincidir con COUNT de product_units WHERE status='available'
- [ ] Given un producto `has_serial=false` When verifico Then NO tiene registros en `product_units` y `current_stock` se maneja como cantidad agregada (comportamiento actual)
- [ ] Given un producto `has_serial=true` When intento insertar un serial duplicado Then la DB rechaza con UNIQUE constraint violation
- [ ] Given `product_units` con status='sold' When tiene `sale_id` y `sale_item_id` poblados Then puedo trazar qué venta vendió ese serial (trazabilidad forward y reverse)

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F0-001 (tenant_id), HU-F0-010 (warranty_months en Product)  
**Notas técnicas:**
- Migración: `0011_product_units_serials`
- Modelos: `ProductUnit` en `models/accounting.py` (o `models/inventory.py` nuevo)
- `warranty_expiry` = `purchase_date + INTERVAL 'product.warranty_months months'` (calculado al insertar)
- `sale_id` FK directo permite trazabilidad inversa (de serial → venta)
- Constraint: stock virtual para productos con serial = COUNT(product_units WHERE status='available')
- Validación en venta: si `has_serial=true`, el cliente DEBE seleccionar seriales específicos (cantidad de seriales = quantity)
- No se requiere lector de código de barras — ingreso manual de seriales

---

### HU-F0-012: Seriales en venta — selección de seriales al vender

**Como** cajero de ferretería  
**Quiero** que al vender un producto con seriales, el sistema me pida seleccionar los seriales específicos  
**Para** mantener la trazabilidad exacta de cada unidad vendida.

**Criterios de aceptación:**
- [ ] Given un producto con `has_serial=true` y 5 seriales 'available' When agrego el item a la venta con cantidad 2 Then el sistema muestra un modal/paso para seleccionar 2 seriales de los 5 disponibles
- [ ] Given el modal de selección de seriales When busco por número de serie Then se filtran los disponibles
- [ ] Given selecciono 2 seriales y confirmo When se crea la venta Then esos seriales cambian a status='sold' con `sale_item_id` referenciando el SaleItem
- [ ] Given intento vender cantidad 3 de un producto con solo 2 seriales 'available' When valido Then el sistema rechaza con "Stock insuficiente: solo 2 seriales disponibles"
- [ ] Given un producto `has_serial=false` When lo vendo Then NO se requiere selección de seriales (comportamiento normal)
- [ ] Given se anula una venta con seriales When ejecuto HU-F2-004 void Then los seriales vuelven a 'available' (se desasocian del sale_item)
- [ ] Given el endpoint `POST /api/accounting/kardex/products` When creo un producto con `has_serial=true` Then acepto registrar seriales iniciales en el mismo request o endpoint separado

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F0-011 (tabla product_units)  
**Notas técnicas:**
- Backend: extender `SalesService.create_sale()` — si `has_serial=true`, validar que `item.serials[]` tenga exactamente `quantity` elementos
- Endpoint: `POST /api/sales/sale` acepta `serials: list[str]` en `SaleItemCreate`
- Frontend: `SerialSelectorModal.tsx` — lista de seriales disponibles con checkboxes, buscador
- Reversión en void: `SalesService.void_sale()` ya revierte kárdex; añadir reversión de seriales

---

### HU-F0-013: Grupos de productos — categorías con tabla dedicada

**Como** administrador de inventario  
**Quiero** gestionar categorías de productos en una tabla dedicada  
**Para** organizar el inventario por grupos (ej. "Fierros", "Cemento", "Pinturas", "Platos", "Bebidas") con posibilidad de más niveles en el futuro.

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `product_categories` con: id, tenant_id, name (VARCHAR(50)), description (TEXT), parent_id (FK self, nullable), active (BOOL), sort_order (INT), created_at
- [ ] Given la migración ejecutada When verifico la DB Then `products.category` cambia de String(20) a `category_id INTEGER FK → product_categories(id)`
- [ ] Given categorías existentes When creo un producto Then puedo asignarle `category_id`
- [ ] Given `GET /api/inventory/categories` When consulto Then obtengo lista plana o árbol (si hay parent_id)
- [ ] Given `POST /api/inventory/categories` When creo una categoría Then se valida nombre único por tenant
- [ ] Given `PATCH /api/inventory/categories/{id}` When actualizo Then puedo cambiar nombre, descripción, orden, activo
- [ ] Given categorías con `parent_id` When consulto Then puedo navegar jerarquía (para futuro: subcategorías)
- [ ] Given la migración de datos When existían productos con `category` string Then se migran a la nueva estructura (se crea categoría automáticamente si no existe)

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F0-001 (tenant_id)  
**Notas técnicas:**
- Migración: `0012_product_categories`  
- Data migration: leer `DISTINCT category` de products, crear `product_categories` por cada valor, actualizar `products.category_id`
- Router: `routers/inventory.py` (nuevo) con prefix `/api/inventory`
- Soporte jerárquico con `parent_id` (self-referencial) — en Fase 0 solo 1 nivel, pero la estructura soporta profundidad
- Schemas: `ProductCategoryCreate`, `ProductCategoryUpdate`, `ProductCategoryResponse` (con `children: list[Self]` opcional)

---

### HU-F0-014: Sidebar jerárquico colapsable con "Salir" siempre visible

**Como** usuario del sistema  
**Quiero** una barra lateral con navegación agrupada por módulos y secciones colapsables  
**Para** encontrar rápidamente lo que necesito sin scroll infinito cuando hay 20+ módulos.

**Criterios de aceptación:**
- [ ] Given el sidebar When se renderiza Then los módulos se agrupan en secciones colapsables: 🏗️ Proyecto de Inversión, 🏪 Ventas/POS, 🍽️ Restaurante, 📦 Inventario, 💰 Finanzas, ⚙️ Configuración
- [ ] Given una sección colapsada When hago clic en el título de sección Then se expande mostrando sus sub-ítems con animación
- [ ] Given `useCompanySettings().businessType === 'hardware'` When el sidebar se renderiza Then la sección 🍽️ Restaurante NO se muestra
- [ ] Given `useCompanySettings().businessType === 'restaurant'` When el sidebar se renderiza Then la sección Restaurante SÍ se muestra con sub-ítems: Salones, Menú, Cocina, TakeAway, Promociones
- [ ] Given estoy en desktop (viewport ≥ 768px) When veo el sidebar Then "🚪 Cerrar Sesión" está sticky al fondo, siempre visible sin importar scroll o secciones expandidas
- [ ] Given estoy en mobile (< 768px) When abro el menú hamburguesa Then "Cerrar Sesión" aparece al final del menú overlay
- [ ] Given el sidebar When la ruta activa es `/restaurante/mesas` Then "Salones" se resalta como activo y la sección "Restaurante" se auto-expande
- [ ] Given colapso manualmente una sección When navego a otra ruta Then las secciones colapsadas manualmente mantienen su estado (no se auto-expanden)

**Prioridad:** P0  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F0-006 a HU-F0-009 (rutas de restaurante deben existir)  
**Notas técnicas:**
- **Decisión Architecture Agent:** Extraer `Sidebar.tsx` como componente separado (colapsable lateral). AppShell se simplifica a ~50 líneas (solo layout: sidebar + header + contenido).
- Componentes nuevos: `Sidebar.tsx`, `SidebarSection.tsx`, `SidebarItem.tsx`, `SidebarLogout.tsx`
- Estado colapsable: `useState` por sección, persistir en `localStorage` para recordar preferencia
- Auto-expandir sección activa al navegar (si no fue colapsada manualmente)
- "Cerrar Sesión": `position: sticky; bottom: 0;` con fondo y borde superior
- Responsive: sidebar fijo en desktop (w-64), overlay/drawer en mobile
- Tests: expandir/colapsar sección, ocultar restaurante en hardware, logout sticky, ruta activa

---

### HU-F0-015: Documentar deudas técnicas (D-05, D-06, D-20, D-21)

**Como** equipo de desarrollo  
**Quiero** que las deudas técnicas acordadas con el cliente queden formalmente documentadas  
**Para** que sean visibles en el backlog y no se pierdan entre fases.

**Criterios de aceptación:**
- [ ] Given el archivo `docs/deuda-tecnica.md` When existe Then contiene entradas formateadas para:
  - **D-05 (DT-REST-01):** "Cierre de comanda solo al pagar (debe ser al cancelar pedido)" — severidad 🟡 Media, fase F2, esfuerzo 0.5d
  - **D-06 (DT-REST-02):** "Delivery sin repartidores, zonas, tracking" — severidad 🟡 Media, fase F2, esfuerzo 2d
  - **D-20 (DT-FERR-01):** "Facturación electrónica genérica pospuesta a V2" — severidad 🟢 Baja, fase F3/F4, esfuerzo 1d
  - **D-21 (DT-INV-01):** "Código de barras — solo campo en DB, sin lógica de escáner" — severidad 🟢 Baja, fase F2 opcional, esfuerzo 0.5d
- [ ] Given las entradas de deuda When incluyen Then: ID, título, descripción del problema, impacto, solución propuesta, fase de resolución, esfuerzo estimado, severidad
- [ ] Given el archivo When está en formato Markdown Then es legible en GitHub/GitLab y renderiza tablas correctamente
- [ ] Given el README.md When se actualiza Then referencia `docs/deuda-tecnica.md` en la sección de "Deuda Técnica"

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** Ninguna  
**Notas técnicas:**
- Crear `docs/deuda-tecnica.md` con tabla de deudas formateada
- Incluir metadatos: ID, severidad, fase_resolucion, esfuerzo, fecha_registro
- Actualizar `README.md` §Deuda Técnica para enlazar al nuevo archivo

---

# Resumen de Dependencias Fase 0

```
HU-F0-001 (tenant_id estandarizado)
  ├── HU-F0-002 (modelos restaurante core: tables, menu, kitchen)
  │     ├── HU-F0-003 (takeaway + promos)
  │     ├── HU-F0-004 (endpoints restaurante)
  │     │     ├── HU-F0-005 (lógica promociones)
  │     │     ├── HU-F0-006 (frontend mapa mesas)
  │     │     │     └── HU-F0-007 (frontend menú + pedido)
  │     │     ├── HU-F0-008 (frontend cocina)
  │     │     └── HU-F0-009 (frontend takeaway + promos)
  │     │           └── HU-F0-016 (modificadores takeaway — bottom sheet + bugfix)
  │     └── HU-F0-014 (sidebar jerárquico — depende de rutas existir)
  │
  ├── HU-F0-010 (POS wholesale/retail + barcode)
  │
  ├── HU-F0-011 (seriales modelo)
  │     └── HU-F0-012 (seriales en venta)
  │
  └── HU-F0-013 (categorías de productos)

HU-F0-015 (deuda técnica) — independiente
```

# Resumen de Esfuerzo

| # | Historia | Capa | Esfuerzo |
|---|----------|------|:--------:|
| HU-F0-001 | tenant_id estandarizado (docs + wrapper) | Backend | 0.3d |
| HU-F0-002 | Modelos restaurante (core) | Backend | 1.5d |
| HU-F0-003 | Modelos restaurante (takeaway, promos) | Backend | 0.5d |
| HU-F0-004 | Endpoints restaurante | Backend | 3d |
| HU-F0-005 | Lógica promociones | Backend | 1d |
| HU-F0-006 | Frontend mapa mesas | Frontend | 1d |
| HU-F0-007 | Frontend menú + pedido | Frontend | 1d |
| HU-F0-008 | Frontend cocina | Frontend | 0.5d |
| HU-F0-009 | Frontend takeaway + promos | Frontend | 1d |
| HU-F0-010 | POS wholesale/retail + barcode | Backend | 1d |
| HU-F0-011 | Seriales modelo | Backend | 1.5d |
| HU-F0-012 | Seriales en venta | Backend+Frontend | 1.5d |
| HU-F0-013 | Categorías productos | Backend | 1d |
| HU-F0-014 | Sidebar jerárquico colapsable | Frontend | 2d |
| HU-F0-015 | Documentar deudas | Equipo | 0.5d |
| HU-F0-016 | Modificadores Take Away (bottom sheet + bugfix) | Backend+Frontend | 1.5d |

| **Total** | | | **18.8 días** |
|-----------|---------|----------|------------|
| Backend | 11 historias | | 11.8d |
| Frontend | 6 historias | | 6.5d |
| Equipo | 1 historia | | 0.5d |

---

### HU-F0-016: Modificadores en Take Away (Bottom Sheet + Bugfix Backend)

**Como** mesero usando el módulo Take Away en una tablet táctil  
**Quiero** seleccionar modificadores/adicionales al agregar ítems del menú al carrito  
**Para** personalizar pedidos para llevar (ej. "huevo frito +S/2.00", "sin cebolla") y que el precio total refleje correctamente los ajustes.

**Contexto:** El Take Away (`/restaurante/takeaway`) ya permite crear pedidos pero no expone el selector de modificadores. En el flujo de Mesas (`TablesMap.tsx`) sí existe, pero usa un modal centrado no óptimo para tablets táctiles. El Architecture Agent 🏗️ analizó y recomendó usar **Bottom Sheet (vaul)** — en tablet se comporta como sheet (sube desde abajo, swipe-to-dismiss, zona del pulgar natural) y en desktop como dialog centrado, una sola implementación.

**Bug crítico confirmado:** `TakeawayService.create()` (línea ~428) guarda los modifiers en el JSON de items pero **NO** suma `price_adjustment` al `unit_price` del ítem. Ej: Hamburguesa S/12 + huevo frito S/2 → total S/12 (debería ser S/14).

**Criterios de aceptación:**
- [ ] Given un ítem del menú **con** modificadores (ej. Hamburguesa con modifiers: "Huevo frito +S/2.00", "Sin cebolla +S/0.00") When hago clic en el ítem desde Take Away Then se abre un Bottom Sheet (`vaul`) mostrando la lista de modificadores disponibles con checkbox/toggle, nombre y ajuste de precio
- [ ] Given el Bottom Sheet abierto When selecciono "Huevo frito" y "Sin cebolla" y presiono "Agregar al pedido" Then el ítem se agrega al carrito con `modifiers: [{id, name, price_adjustment}]` poblado, y el subtotal del ítem refleja `precio_base + Σ price_adjustment`
- [ ] Given un ítem del menú **sin** modificadores (`modifiers: []` o `null`) When hago clic en el ítem Then se agrega directamente al carrito SIN mostrar Bottom Sheet (flujo actual preservado)
- [ ] Given el carrito tiene ítems con modificadores When veo el resumen Then cada ítem muestra sus modificadores aplicados (ej. "Hamburguesa (huevo frito, sin cebolla)")
- [ ] Given el carrito con ítems con modificadores When presiono "Confirmar Pedido" Then el payload enviado al backend incluye `modifiers: [{id, name, price_adjustment}]` por cada ítem que los tenga
- [ ] Given el backend recibe un payload con `modifiers` en `TakeawayService.create()` When calcula el `item_total` Then suma `Σ price_adjustment` de cada modifier al `unit_price` base → `item_total = quantity * (unit_price + Σ price_adjustment)`
- [ ] Given el backend recibe modifiers con selecciones que exceden `max_select` de un modifier group When valida Then rechaza con 422 y mensaje "Modificador 'X': máximo N, enviados M" (misma lógica que `KitchenOrdersService.create_order()`)
- [ ] Given el pedido se crea correctamente con modifiers When la cocina ve la comanda en el Kanban Then los items muestran los modificadores aplicados
- [ ] Given estoy en una tablet táctil (viewport < 768px o dispositivo táctil) When se abre el selector de modificadores Then se comporta como Bottom Sheet (sube desde abajo, swipe-to-dismiss, CTA fijo abajo, zona del pulgar natural)
- [ ] Given estoy en desktop (viewport ≥ 768px, puntero mouse) When se abre el selector de modificadores Then `vaul` se comporta como dialog centrado automáticamente (comportamiento nativo de vaul)
- [ ] Given el Bottom Sheet abierto When hago swipe hacia abajo o presiono fuera del sheet Then el sheet se cierra sin agregar el ítem al carrito

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días (Backend 0.5d + Frontend 1d)  
**Dependencias:** HU-F0-003 (tabla `takeaway_orders`), HU-F0-004 (endpoints restaurante), HU-F0-009 (pantalla Take Away base)  
**Riesgo:** 🟡 Medio — Bug de pricing ya en producción. El frontend Bottom Sheet requiere instalar `vaul` (npm) y adaptar `CartItem`.

**Notas técnicas:**

**Backend — Fix en `TakeawayService.create()`:**
- Replicar la lógica de `KitchenOrdersService.create_order()` (líneas ~310-340 de `restaurant_service.py`):
  - Validar `max_select` por modifier group consultando `MenuModifier`
  - Calcular `mods_total = Σ (price_adjustment * count)`
  - `item_total = qty * (unit_price + mods_total)`
- El payload ya incluye `modifiers: [{id, name, price_adjustment}]` — el fix es solo aritmético y de validación.

**Frontend — Bottom Sheet con vaul:**
- Instalar `vaul` (`npm install vaul`)
- Crear componente `ModifierBottomSheet.tsx`:
  - Props: `item: MenuItem`, `isOpen: boolean`, `onClose: () => void`, `onConfirm: (modifiers: SelectedModifier[]) => void`
  - Internamente usa `<Drawer>` de vaul con `shouldScaleBackground` y `snapPoints`
  - Lista de modificadores con checkbox + nombre + badge de precio (verde si +S/0, azul si +S/>0)
  - CTA "Agregar al pedido — S/XX.XX" sticky en la parte inferior del sheet con precio total actualizado en tiempo real
  - Vaul automáticamente adapta: en mobile/tablet → bottom sheet, en desktop → dialog centrado
- Modificar `CartItem` interface:
  ```ts
  interface CartItem {
    menuItem: MenuItemSimple;
    quantity: number;
    modifiers: { id: number; name: string; price_adjustment: number }[];
  }
  ```
- Modificar `addToCart` en `TakeawayPage.tsx`:
  - Si `item.modifiers && item.modifiers.length > 0` → abrir `ModifierBottomSheet`
  - Si no tiene modifiers → agregar directo (comportamiento actual)
- Modificar `cartTotal` para incluir `Σ modifier.price_adjustment`
- Mostrar modifiers en el resumen del carrito: `{item.name} ({mods.map(m => m.name).join(", ")})`
- El payload POST debe incluir `modifiers` en cada item
- `vaul` NO requiere configuración especial mobile vs desktop — detecta el dispositivo automáticamente

**Archivos modificados:**
| Archivo | Cambio |
|---------|--------|
| `apps/backend/app/services/restaurant_service.py` | Fix `TakeawayService.create()` — sumar price_adjustment + validar max_select |
| `apps/web/src/pages/restaurante/TakeawayPage.tsx` | Integrar Bottom Sheet, extender CartItem, mostrar modifiers en carrito |
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | **NUEVO** — Componente Bottom Sheet con vaul |

---

*Documento generado por PO Agent 📋 basado en Plan Integral v3 §13.1 + gap analysis sobre commit `6bfd61a`. Pendiente de revisión Architecture Agent.*
