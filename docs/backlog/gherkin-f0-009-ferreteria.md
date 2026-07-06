# Backlog Gherkin — DT-F0-009: Módulo Ferretería (Validación Completa)

**Proyecto:** IaaS-RonSys  
**Origen:** DT-F0-009 del backlog de Deuda Técnica Fase 0  
**Generado por:** PO Agent 📋  
**Fecha:** 2026-05-15  
**Branch:** `fase0-real`  
**Deuda origen:** `docs/backlog/deuda-tecnica-fase0.md` § DT-F0-009  
**Total Historias:** 7  
**Alcance:** 4 sub-dominios (Categorías↔Productos, Precios Mayorista/Detal, Seriales/Trazabilidad, Productos sin Serial)

---

## 📌 Contexto

DT-F0-009 cubre la **validación funcional completa** del módulo Ferretería. Las historias previas HU-F0-010 a HU-F0-013 definen los modelos y migraciones base. Estas 7 historias **extienden y validan** esos cimientos con:
- Página CRUD dedicada a Productos
- Contador de productos por categoría + jerarquía de subcategorías
- Flujo operativo completo de precios mayorista/detal
- Trazabilidad bidireccional de seriales (producto↔venta)
- Anulación de ventas con devolución de seriales
- Garantía por producto
- Coexistencia de productos con y sin serial en la misma venta

### 📋 Relación con historias previas

| Historia base | Qué define | DT-F0-009 extiende con |
|---------------|------------|------------------------|
| HU-F0-010 | Migración precios, barcode, warranty_months | Flujo de venta mayorista/detal validado punta a punta + comprobante |
| HU-F0-011 | Modelo `product_units`, flag `has_serial` | Registro masivo de seriales, garantía, trazabilidad bidireccional |
| HU-F0-012 | Selección de seriales al vender | Anulación devuelve seriales, trazabilidad post-venta, venta mixta |
| HU-F0-013 | Tabla `product_categories`, migración de datos | Contador en UI, jerarquía navegable, CRUD completo de categorías |

---

## Historias

---

### HU-F0-009-01: Categorías — CRUD completo, jerarquía y contador de productos

**Como** administrador de ferretería  
**Quiero** crear, editar, eliminar y organizar categorías jerárquicamente, viendo cuántos productos tiene cada una  
**Para** mantener el inventario ordenado por familias (ej. "Fierros > Varillas de 1/2") y detectar categorías vacías.

**Criterios de aceptación:**

- [ ] Given el endpoint `POST /api/inventory/categories` When creo la categoría "Fierros" con `{"name": "Fierros", "description": "Materiales de fierro"}` Then se crea con `product_count: 0` y `parent_id: null`
- [ ] Given la categoría "Fierros" existe (id=1) When creo subcategoría `{"name": "Varillas de 1/2", "parent_id": 1}` Then se crea correctamente con `parent_id=1` y `product_count: 0`
- [ ] Given `GET /api/inventory/categories` When consulto Then la respuesta incluye `product_count` para cada categoría (COUNT de products WHERE category_id = cat.id AND active = true)
- [ ] Given `GET /api/inventory/categories?tree=true` When consulto Then obtengo estructura jerárquica anidada: cada categoría con `children: [...]` ordenado por `sort_order`
- [ ] Given la subcategoría "Varillas de 1/2" (id=2) When creo el producto "Varilla de 1/2 corrugada" asignado a `category_id=2` Then el `product_count` de "Varillas de 1/2" sube a 1 y también se refleja en el endpoint
- [ ] Given el producto está asignado a "Varillas de 1/2" When edito el producto para cambiar a `category_id=1` ("Fierros") Then el contador de "Varillas de 1/2" baja a 0 y "Fierros" sube a 1
- [ ] Given el producto está en "Fierros" When elimino (soft-delete) el producto Then el contador de "Fierros" baja a 0
- [ ] Given `PATCH /api/inventory/categories/{id}` When actualizo el nombre o `sort_order` Then se actualiza correctamente
- [ ] Given una categoría con productos activos When intento `DELETE /api/inventory/categories/{id}` (hard delete) Then el sistema rechaza con 409 "Categoría tiene X producto(s) activo(s). Reasígneos primero."
- [ ] Given una categoría sin productos When `DELETE` Then se elimina (o soft-delete `active=false`)
- [ ] Given el frontend en `/inventario/categorias` When la página carga Then veo lista/tabla de categorías con: nombre, descripción, `product_count` como badge, botones editar/eliminar
- [ ] Given existen subcategorías When veo la lista Then puedo expandir/colapsar el árbol (flechita ▶/▼) para navegar la jerarquía
- [ ] Given creo/edito una categoría When selecciono "Categoría padre" Then el dropdown muestra solo categorías sin padre o con profundidad < N (evitar ciclos)

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día (Backend 0.5d + Frontend 0.5d)  
**Dependencias:** HU-F0-013 (tabla `product_categories` debe existir)  
**Notas técnicas:**
- `product_count` se calcula con subquery o COUNT en el endpoint (no columna almacenada, para evitar inconsistencia)
- Self-referential: validar que `parent_id` no genere ciclos (no puede ser ancestro de sí mismo)
- Endpoint jerárquico: `GET /api/inventory/categories?tree=true` → arma árbol en Python con recursión o dict lookup
- Frontend: `CategoriesPage.tsx` con componente `CategoryTree.tsx` recursivo
- Soft-delete: si `active=false`, no cuenta en `product_count` ni aparece en selects de asignación
- Validación de eliminación: verificar `COUNT(products WHERE category_id=X AND active=true) > 0` antes de permitir

---

### HU-F0-009-02: Productos — Página CRUD dedicada

**Como** administrador de ferretería  
**Quiero** una página dedicada para crear, listar, buscar, editar y eliminar productos  
**Para** gestionar el catálogo completo sin depender del flujo de ventas/POS.

**Criterios de aceptación:**

- [ ] Given estoy en `/inventario/productos` When la página carga Then veo una tabla con columnas: Nombre, Categoría, Precio Retail, Precio Mayorista, Stock, Seriales (Sí/No), Código de Barras, Acciones
- [ ] Given la tabla de productos When escribo en el buscador Then se filtra por nombre, categoría o código de barras (debounce 300ms)
- [ ] Given la tabla When hago clic en encabezado de columna (Nombre, Precio, Stock) Then se ordena ascendente/descendente
- [ ] Given presiono "Nuevo Producto" When se abre el formulario Then puedo ingresar: nombre, descripción, categoría (dropdown de categorías activas), unidad de medida, precio retail, precio mayorista, cantidad mínima mayorista, código de barras, `has_serial` (toggle), meses de garantía, fabricante, stock inicial (si no tiene seriales)
- [ ] Given completo el formulario y presiono "Guardar" When el producto se crea Then aparece en la tabla y el contador de su categoría se actualiza
- [ ] Given un producto existente When presiono "Editar" Then se abre formulario pre-poblado y puedo modificar cualquier campo
- [ ] Given cambio la categoría de un producto vía edición When guardo Then el contador de la categoría anterior baja y el de la nueva sube
- [ ] Given un producto When presiono "Eliminar" Then se muestra confirmación "¿Eliminar [nombre]?" y al confirmar se hace soft-delete (`active=false`), el contador de categoría baja
- [ ] Given un producto con `has_serial=true` When veo la fila en la tabla Then la columna "Seriales" muestra "✅ Sí" con tooltip mostrando cuántos seriales disponibles/totales
- [ ] Given un producto con seriales vendidos When intento eliminar Then el sistema permite soft-delete (mantiene trazabilidad histórica) pero advierte "Producto tiene seriales vendidos. Se desactivará pero no se eliminará físicamente."
- [ ] Given el formulario de producto When cambio el toggle `has_serial` de false→true y guardo Then se habilita la sección de registro de seriales
- [ ] Given el formulario When dejo campos obligatorios vacíos (nombre, precio retail) Then se muestra validación inline y no se envía

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días (Backend 0.5d + Frontend 1d)  
**Dependencias:** HU-F0-009-01 (categorías con contador), HU-F0-010 (campos pricing en Product), HU-F0-011 (campo `has_serial`)  
**Notas técnicas:**
- Página nueva: `ProductsPage.tsx` en `/inventario/productos`
- Componentes: `ProductsTable.tsx`, `ProductFormModal.tsx`, `ProductSearchBar.tsx`
- Backend: extender endpoints existentes `GET/POST/PATCH /api/accounting/kardex/products` o crear nuevos en `routers/inventory.py`
- Soft-delete: `active=false` — queries existentes de ventas deben filtrar `active=true` (o mantener visibilidad de históricos en ventas)
- Indicador de seriales en tabla: subquery `COUNT(product_units WHERE status='available')` como `serial_count`
- Formulario condicional: si `has_serial=true`, mostrar sección "Seriales iniciales" (grid para ingresar N seriales)
- Ordenación y búsqueda: server-side con query params `?search=&sort_by=&order=`

---

### HU-F0-009-03: Precios mayorista/detal — flujo operativo completo

**Como** cajero / administrador de ferretería  
**Quiero** que el sistema aplique automáticamente el precio correcto (minorista o mayorista) según la cantidad vendida  
**Para** evitar errores de pricing manual y asegurar que las ventas al por mayor tengan el descuento correspondiente.

**Criterios de aceptación:**

- [ ] Given creo el producto "Cemento Sol 42.5kg" con `retail_price=S/25.00`, `wholesale_price=S/22.00`, `wholesale_min_qty=10` When verifico el producto Then ambos precios se guardan correctamente
- [ ] Given el producto "Cemento Sol 42.5kg" When agrego 5 unidades a una venta en el POS Then el precio unitario aplicado es S/25.00 (minorista) porque 5 < 10 (cantidad mínima mayorista)
- [ ] Given el mismo producto When agrego 10 unidades a una venta Then el precio unitario aplicado es S/22.00 (mayorista) porque 10 >= 10
- [ ] Given el mismo producto When agrego 15 unidades Then el precio unitario es S/22.00 (todas las unidades a precio mayorista)
- [ ] Given un producto SIN `wholesale_price` (NULL) When agrego cualquier cantidad Then siempre se usa `retail_price`
- [ ] Given un producto con `wholesale_min_qty=NULL` pero `wholesale_price` definido When agrego cualquier cantidad Then se usa `retail_price` (cantidad mínima es obligatoria para activar mayorista)
- [ ] Given el producto "Cemento Sol 42.5kg" con `barcode="7751234567890"` When escaneo/ingreso el código de barras en el POS Then el producto se agrega al ticket con su precio correcto
- [ ] Given completo la venta de 10 unidades When el comprobante se genera Then muestra "Cemento Sol 42.5kg — 10 unid × S/22.00 = S/220.00" (precio unitario mayorista claramente visible)
- [ ] Given completo la venta de 5 unidades When el comprobante se genera Then muestra "Cemento Sol 42.5kg — 5 unid × S/25.00 = S/125.00"
- [ ] Given el formulario de creación/edición de producto When ingreso `wholesale_price > retail_price` Then el sistema muestra advertencia "Precio mayorista es mayor que el minorista. ¿Está seguro?" (no bloquea, pero advierte)
- [ ] Given edito el producto y cambio `wholesale_min_qty` de 10 a 20 When las ventas futuras de 10-19 unidades Then se van a precio minorista

**Prioridad:** P0  
**Esfuerzo estimado:** 0.5 días (Backend — validación + ajustes en SalesService)  
**Dependencias:** HU-F0-010 (columnas `retail_price`, `wholesale_price`, `wholesale_min_qty`, `barcode` en Product), HU-F0-009-02 (CRUD productos para crear/editar precios)  
**Notas técnicas:**
- Lógica de pricing en `SalesService.create_sale()` o helper `apply_pricing(item, product)`:
  ```python
  if product.wholesale_price and product.wholesale_min_qty and item.quantity >= product.wholesale_min_qty:
      unit_price = product.wholesale_price
  else:
      unit_price = product.retail_price
  ```
- El frontend del POS (`SalesNew.tsx`) ya existe — solo necesita que el backend responda con `retail_price` y `wholesale_price` en los endpoints de búsqueda de producto
- La lógica de auto-aplicación es backend (para evitar manipulación desde frontend)
- El comprobante/ticket debe mostrar el precio unitario efectivo, no el precio de lista
- Advertencia `wholesale_price > retail_price`: validación soft (warning, no error)
- Código de barras: búsqueda por `barcode` en endpoint `GET /api/accounting/kardex/products?barcode=xxx`

---

### HU-F0-009-04: Seriales — registro, stock y CRUD de seriales

**Como** administrador de ferretería  
**Quiero** registrar números de serie para productos marcados como `has_serial=true`, con su fecha de compra y precio de costo  
**Para** tener trazabilidad individual de cada unidad y que el stock refleje exactamente los seriales disponibles.

**Criterios de aceptación:**

- [ ] Given el producto "Taladro Bosch GSB 13" con `has_serial=true` y `warranty_months=12` When registro 3 seriales: BOSCH-001 (compra 2026-01-15, costo S/180), BOSCH-002 (2026-02-01, S/185), BOSCH-003 (2026-03-10, S/175) Then los 3 se crean con status='available' y `warranty_expiry` = fecha_compra + 12 meses
- [ ] Given los 3 seriales registrados When consulto el stock del producto Then `current_stock=3` (COUNT de product_units WHERE status='available')
- [ ] Given `GET /api/inventory/products/{id}/serials` When consulto los seriales de un producto Then obtengo lista con: serial_number, status, purchase_date, cost_price, warranty_expiry, sale_id (si vendido)
- [ ] Given `GET /api/inventory/products/{id}/serials?status=available` When filtro por disponibles Then solo veo seriales no vendidos
- [ ] Given intento registrar un serial duplicado (BOSCH-001 ya existe) When hago `POST` Then responde 409 "Número de serie BOSCH-001 ya existe"
- [ ] Given un producto `has_serial=false` When intento registrar seriales Then responde 422 "Este producto no usa control por seriales"
- [ ] Given `POST /api/inventory/products/{id}/serials/batch` When envío array de seriales `[{serial_number, purchase_date, cost_price}]` Then se crean todos en una transacción (rollback si alguno falla)
- [ ] Given el endpoint de producto (`GET /api/inventory/products/{id}`) When consulto Then incluye `serial_available_count`, `serial_total_count` y array de seriales inline (limitado a 50) o endpoint separado
- [ ] Given el frontend en la página de Productos When veo un producto con `has_serial=true` Then hay botón "🔢 Seriales" que abre panel/modal con lista de seriales y botón "Registrar Seriales"
- [ ] Given el panel de seriales When presiono "Registrar Seriales" Then se abre formulario con tabla editable: columnas Serial Number, Fecha Compra, Precio Costo, y botón "+ Agregar fila" para registro masivo
- [ ] Given registros masivos When guardo Then se crean todos los seriales y la tabla se refresca

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día (Backend 0.5d + Frontend 0.5d)  
**Dependencias:** HU-F0-011 (tabla `product_units` debe existir)  
**Notas técnicas:**
- `warranty_expiry` calculado: `purchase_date + relativedelta(months=product.warranty_months)`. Si `warranty_months=0` → NULL.
- Endpoints de seriales en `routers/inventory.py`: `GET/POST /products/{id}/serials`, `POST /products/{id}/serials/batch`
- Registro masivo: endpoint batch que recibe `List[SerialCreate]` y ejecuta `INSERT ... RETURNING` en lote con `session.add_all()` + `commit()`
- Stock calculado dinámicamente: `SELECT COUNT(*) FROM product_units WHERE product_id=X AND status='available'`
- Panel de seriales en frontend: `SerialPanel.tsx` con `SerialTable.tsx`, `SerialBatchForm.tsx`
- Validación: nombre de producto + `has_serial=true` requerido antes de permitir registro

---

### HU-F0-009-05: Seriales en venta — modal selector y flujo de venta con seriales

**Como** cajero de ferretería  
**Quiero** que al vender un producto con seriales, el sistema me muestre un selector para elegir qué seriales específicos entrego  
**Para** mantener trazabilidad exacta de cada unidad vendida y evitar vender seriales que ya no están disponibles.

**Criterios de aceptación:**

- [ ] Given el producto "Taladro Bosch GSB 13" con 3 seriales disponibles When agrego 1 unidad al ticket del POS Then se abre modal "Seleccionar Serial" mostrando los 3 seriales disponibles con su fecha de compra y precio costo
- [ ] Given el modal de selección When selecciono "BOSCH-001" y confirmo Then el item se agrega al ticket con el serial anotado, y el modal se cierra
- [ ] Given el mismo producto When agrego otra unidad (segunda) al ticket Then el modal muestra solo 2 seriales (BOSCH-002, BOSCH-003) porque BOSCH-001 ya está seleccionado en este ticket
- [ ] Given completo la venta con BOSCH-001 When se confirma Then BOSCH-001 cambia a status='sold', `sale_id` y `sale_item_id` se pueblan, y el stock del producto baja a 2
- [ ] Given intento vender 3 unidades del taladro (quedan 2 seriales disponibles) When agrego al POS Then el sistema muestra error "Stock insuficiente: solo 2 seriales disponibles para Taladro Bosch" y no permite agregar
- [ ] Given el modal de selección When hay muchos seriales (>20) Then hay un buscador/filtro por número de serie para encontrar rápidamente
- [ ] Given un producto `has_serial=false` ("Arena Fina x m³") When agrego al ticket Then NO se muestra modal de seriales — se agrega directamente con cantidad numérica
- [ ] Given el ticket tiene productos con y sin serial When veo el resumen Then los items con serial muestran el/los seriales seleccionados junto al nombre del producto
- [ ] Given el ticket When presiono "Anular" antes de completar la venta Then los seriales seleccionados (no confirmados) se liberan y vuelven a estar disponibles para otras ventas
- [ ] Given el POS en el frontend When agrego un producto con serial Then el componente `SerialSelectorModal.tsx` se renderiza con lista de seriales disponibles (excluyendo los ya reservados en el ticket actual)

**Prioridad:** P0  
**Esfuerzo estimado:** 1 día (Backend 0.5d + Frontend 0.5d)  
**Dependencias:** HU-F0-009-04 (registro de seriales), HU-F0-012 (endpoint de selección de seriales en venta)  
**Notas técnicas:**
- Backend: extender `POST /api/sales/sale` — el campo `serials: list[str]` en `SaleItemCreate` debe validarse:
  - Si `product.has_serial` → `len(serials) == quantity` (obligatorio)
  - Cada serial debe existir, estar 'available', pertenecer al producto correcto
  - En la misma transacción: `UPDATE product_units SET status='sold', sale_id=X, sale_item_id=Y WHERE serial_number IN (...)`
- Frontend: `SerialSelectorModal.tsx` recibe `productId`, `quantity` (ya seleccionada), lista de disponibles, y callback `onConfirm(serials: string[])`
- Estado de "reserva temporal": mientras el ticket está abierto, los seriales NO se bloquean en DB (para evitar locks largos). Se validan al confirmar la venta. Si otro cajero los vendió mientras tanto, se muestra error.
- Alternativa: reservar con status='reserved' al agregar al ticket, y limpiar con un job o al cancelar/confirmar. Para Fase 0, validación al confirmar es suficiente.
- Buscador en modal: `filter(serial => serial.toLowerCase().includes(query.toLowerCase()))`

---

### HU-F0-009-06: Seriales — anulación, trazabilidad y garantía

**Como** administrador de ferretería  
**Quiero** que al anular una venta los seriales vuelvan a estar disponibles, y poder consultar la historia completa de un serial (compra → venta → posible anulación) en ambas direcciones  
**Para** tener control total de trazabilidad y gestionar devoluciones y garantías.

**Criterios de aceptación:**

- [ ] Given la venta #123 que incluye el serial BOSCH-001 When anulo (void) la venta completa Then BOSCH-001 vuelve a status='available', `sale_id` y `sale_item_id` se limpian (NULL), y el stock del producto sube a 3
- [ ] Given la anulación de la venta #123 When consulto la trazabilidad de BOSCH-001 Then muestra:
  - Fecha de registro: 2026-01-15, costo S/180
  - Vendido en: Venta #123, fecha 2026-04-20, cliente Juan Pérez
  - Anulado: 2026-04-21, motivo "Cliente devolvió producto defectuoso"
  - Estado actual: Disponible
- [ ] Given el endpoint `GET /api/inventory/serials/{serial_number}/traceability` When consulto Then obtengo lista cronológica de eventos: `registered` → `sold` → `voided` (cada uno con timestamp, usuario, y referencia)
- [ ] Given consulto una venta específica When la respuesta incluye `items` Then cada item con serial muestra los seriales vendidos: `"serials": ["BOSCH-001", "BOSCH-002"]`
- [ ] Given el endpoint `GET /api/sales/sale/{id}` When consulto una venta con seriales Then en `sale_items[]` cada item incluye `serials: [{serial_number, warranty_expiry}]`
- [ ] Given un serial con `warranty_expiry = 2027-01-15` When consulto la trazabilidad Then se muestra "Garantía vigente hasta: 2027-01-15" (y badge verde si vigente, rojo si vencida)
- [ ] Given un serial vendido y con garantía vigente When el cliente trae el producto por garantía Then puedo buscar por número de serie en el POS/dashboard y ver: fecha de venta, cliente, fecha de compra original, costo, y si está en garantía
- [ ] Given el dashboard de inventario When hay seriales con garantía por vencer (< 30 días) Then se muestra alerta "X seriales con garantía por vencer"
- [ ] Given `POST /api/sales/sale/{id}/void` When anulo solo 1 item de una venta que tenía 3 items (y ese item tenía seriales) Then solo los seriales de ese item vuelven a 'available', el resto de la venta sigue vigente

**Prioridad:** P0  
**Esfuerzo estimado:** 1.5 días (Backend 1d + Frontend 0.5d)  
**Dependencias:** HU-F0-009-05 (venta con seriales), HU-F0-011 (modelo `product_units`), HU-F0-010 (campo `warranty_months`)  
**Notas técnicas:**
- Trazabilidad: endpoint dedicado `GET /api/inventory/serials/{serial_number}/traceability` que consulta:
  - `product_units` (registro inicial)
  - `sale_items` JOIN `sales` (venta)
  - `void_log` o `sale.voided_at` (anulación)
  - Arma timeline ordenado por timestamp
- Anulación de venta con seriales: extender `SalesService.void_sale()`:
  ```python
  # Para cada sale_item con seriales:
  UPDATE product_units SET status='available', sale_id=NULL, sale_item_id=NULL
  WHERE sale_item_id = :sale_item_id AND status='sold'
  ```
- Garantía vigente: `warranty_expiry > today`. Si `warranty_expiry` es NULL (sin garantía), mostrar "Sin garantía".
- Alerta de garantía por vencer: query `SELECT COUNT(*) FROM product_units WHERE status='sold' AND warranty_expiry BETWEEN today AND today+30`
- Frontend: `SerialTraceabilityPanel.tsx` con timeline vertical, búsqueda de serial por número
- En consulta de venta (`GET /api/sales/sale/{id}`): JOIN con `product_units` para incluir seriales vendidos

---

### HU-F0-009-07: Productos sin serial — coexistencia y validación de integridad

**Como** administrador de inventario  
**Quiero** que los productos sin control de seriales funcionen con stock numérico tradicional y coexistan sin problemas con los productos serializados en el mismo sistema, misma venta y mismos reportes  
**Para** no tener dos sistemas de inventario separados.

**Criterios de aceptación:**

- [ ] Given el producto "Arena Fina x m³" con `has_serial=false` y `current_stock=50` When registro el producto Then se crea con stock numérico (sin registros en `product_units`)
- [ ] Given vendo 5 m³ de "Arena Fina" When confirmo la venta Then `current_stock` baja a 45 (actualización numérica directa)
- [ ] Given la venta de 5 m³ de "Arena Fina" When anulo la venta Then `current_stock` vuelve a 50
- [ ] Given una venta mixta: 1 "Taladro Bosch" (serial BOSCH-001) + 5 "Arena Fina" (sin serial) When confirmo Then:
  - BOSCH-001 cambia a 'sold'
  - Arena Fina baja de 50 a 45
  - Ambos cambios ocurren en la misma transacción
- [ ] Given `GET /api/inventory/products` When consulto la lista de productos Then veo productos con y sin serial mezclados, con su stock correcto (serial_count para serializados, current_stock para no serializados)
- [ ] Given el reporte de inventario When consulto Then el valor total del inventario se calcula correctamente:
  - Productos con serial: Σ(cost_price de seriales disponibles)
  - Productos sin serial: current_stock × cost_price (o avg_cost)
- [ ] Given un producto `has_serial=false` When intento registrar seriales Then el sistema rechaza con 422
- [ ] Given un producto `has_serial=true` When intento modificar `current_stock` manualmente (sin pasar por registro de seriales) Then el sistema rechaza o advierte "Use el panel de seriales para ajustar el stock"
- [ ] Given edito un producto y cambio `has_serial` de false → true When el producto tiene `current_stock > 0` Then el sistema advierte: "Stock actual es X. No se migrará automáticamente a seriales. Debe registrar seriales manualmente."
- [ ] Given edito un producto y cambio `has_serial` de true → false When tiene seriales registrados Then el sistema rechaza: "No puede desactivar seriales. Elimine primero los X seriales registrados."
- [ ] Given el kárdex When se registran movimientos de productos con y sin serial Then ambos tipos generan entradas de kárdex consistentes (entrada/salida con cantidad y referencia)

**Prioridad:** P0  
**Esfuerzo estimado:** 0.5 días (Backend 0.3d + Frontend 0.2d)  
**Dependencias:** HU-F0-009-04 (seriales), HU-F0-009-05 (venta con seriales), HU-F0-009-06 (anulación)  
**Notas técnicas:**
- Validación de integridad en `SalesService.create_sale()`:
  ```python
  if product.has_serial:
      validate_serials(item.serials, quantity)
      # stock se deduce al vender seriales (UPDATE product_units)
  else:
      validate_numeric_stock(product.current_stock, quantity)
      # stock se deduce: product.current_stock -= quantity
  ```
- Cambio de `has_serial`: validar en `PATCH /api/inventory/products/{id}`:
  - false→true: warning si `current_stock > 0`, permitir (stock queda en 0 hasta registrar seriales)
  - true→false: rechazar si `COUNT(product_units) > 0`
- Reporte de inventario: endpoint `GET /api/inventory/products/value` que calcula valor total
- Kárdex: ambos tipos generan entradas en `kardex_entries` con `entry_type='sale'` o `'void'`, `quantity`, `unit_cost` — el motor contable es el mismo
- Frontend: en `ProductsTable.tsx`, columna "Stock" muestra `current_stock` para no-serializados y `serial_available_count` para serializados

---

## 📊 Resumen de Historias

| ID | Historia | Sub-dominio | Capa | Esfuerzo |
|----|----------|:-----------:|------|:--------:|
| HU-F0-009-01 | Categorías — CRUD, jerarquía y contador | Catálogo | Back+Front | 1d |
| HU-F0-009-02 | Productos — Página CRUD dedicada | Catálogo | Back+Front | 1.5d |
| HU-F0-009-03 | Precios mayorista/detal — flujo completo | Precios | Backend | 0.5d |
| HU-F0-009-04 | Seriales — registro, stock y CRUD | Seriales | Back+Front | 1d |
| HU-F0-009-05 | Seriales en venta — modal selector | Seriales | Back+Front | 1d |
| HU-F0-009-06 | Seriales — anulación, trazabilidad y garantía | Seriales | Back+Front | 1.5d |
| HU-F0-009-07 | Productos sin serial — coexistencia | Mixto | Back+Front | 0.5d |

| **Total** | | | | **7 días** |
|-----------|---------|------------|----------|------------|
| Backend | | | | 4.8d |
| Frontend | | | | 2.2d |

---

## 🔗 Dependencias entre historias

```
HU-F0-001 (tenant_id estandarizado) [existente]
  │
  ├── HU-F0-010 (pricing + barcode) [existente]
  │     └── HU-F0-009-03 (flujo precios mayorista/detal)
  │
  ├── HU-F0-011 (seriales modelo) [existente]
  │     └── HU-F0-009-04 (registro seriales + stock)
  │           ├── HU-F0-009-05 (seriales en venta)
  │           │     └── HU-F0-009-06 (anulación + trazabilidad)
  │           └── HU-F0-009-07 (coexistencia con/sin serial)
  │
  └── HU-F0-013 (tabla categorías) [existente]
        └── HU-F0-009-01 (CRUD categorías + contador)
              └── HU-F0-009-02 (CRUD productos dedicado)
                    ├── HU-F0-009-03 (precios — necesita productos creados)
                    └── HU-F0-009-04 (seriales — necesita has_serial en producto)
```

### Orden de implementación recomendado

1. **HU-F0-009-01** — Categorías (base para asignar categorías a productos)
2. **HU-F0-009-02** — CRUD Productos (usa categorías, crea el canvas para precios y seriales)
3. **HU-F0-009-03** — Precios mayorista/detal (extiende el formulario de producto + lógica en ventas)
4. **HU-F0-009-04** — Registro de seriales (extiende el panel de producto con gestión de seriales)
5. **HU-F0-009-05** — Seriales en venta (modal selector en POS)
6. **HU-F0-009-06** — Trazabilidad + anulación (depende de ventas con seriales existentes)
7. **HU-F0-009-07** — Coexistencia (validación cruzada de todo lo anterior)

---

## 🎯 Cobertura de Casos de Uso de Éxito

| Caso | Descripción | Historias que lo cubren |
|:----:|-------------|-------------------------|
| 1 | Categorías + CRUD Productos | HU-F0-009-01, HU-F0-009-02 |
| 2 | Precios Mayorista/Detal | HU-F0-009-03 |
| 3 | Seriales + Trazabilidad | HU-F0-009-04, HU-F0-009-05, HU-F0-009-06 |
| 4 | Productos sin serial | HU-F0-009-07 |

---

*Documento generado por PO Agent 📋 basado en DT-F0-009 del backlog de deuda técnica, validado contra historias existentes HU-F0-010 a HU-F0-013.*
