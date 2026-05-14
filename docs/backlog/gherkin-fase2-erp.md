# Backlog Gherkin — Fase 2: Módulos Comerciales

**Proyecto:** IaaS-RonSys  
**Franquicia:** El Segoviano  
**Generado por:** PO Agent 📋 + Architecture Agent 🏗️  
**Fecha:** 2026-05-14  
**Estado:** ✅ COMPLETADO — Validado por QA (12/12 historias)

---

## Resumen Ejecutivo

Fase 2 implementa el núcleo comercial del ERP: sesiones POS, ventas con múltiples ítems y métodos de pago, integración con kárdex (stock se descuenta automáticamente), asientos contables automáticos por cada venta, tickets térmicos, y UI completa de caja, venta especializada por tipo de negocio y listado de ventas.

**QA Final:** Backend 140/140 ✅ | Frontend 140/140 ✅ | tsc + build limpios ✅  
**12/12 historias validadas** contra código real  
**Brecha conocida:** `sale_number` usa `COUNT(*)` en lugar de `SELECT ... FOR UPDATE` (no bloqueante para MVP)

---

## Historias de Usuario

---

### HU-F2-001: Modelos ORM y migración — tablas base de ventas

**Estado:** ✅ COMPLETADO

**Como** desarrollador backend  
**Quiero** tener las tablas `pos_sessions`, `sales`, `sale_items` y `sale_payments` creadas  
**Para** que el sistema pueda registrar turnos de caja, ventas, ítems y pagos.

**Criterios de aceptación validados:**
- [x] Migración 0005 crea `pos_sessions` con: id, company_id, user_id, opened_at, closed_at, opening_cash, closing_cash, expected_cash, difference, status, notes
- [x] `sales` con: id, company_id, session_id, user_id, sale_number, sale_date, sale_time, customer_name, customer_doc, subtotal, discount_total, tax_total, tip_amount, total, business_type, is_voided, journal_entry_id
- [x] `sale_items` con: id, sale_id (FK CASCADE), product_id, item_name, item_type, quantity, unit_of_measure, unit_price, discount_pct, discount_amount, tax_pct, tax_amount, total, kardex_movement_id
- [x] `sale_payments` con: id, sale_id (FK CASCADE), payment_method, amount, reference
- [x] CHECK constraints: `pos_sessions.status` ('open'|'closed'), `sale_payments.payment_method` ('cash'|'card'|'yape'|'plin'|'transfer'), `sale_items.item_type` ('product'|'service'|'combo')
- [x] CASCADE funciona al eliminar venta padre

**Archivos:** Migración 0005, modelos en `adapters/db/models/sales.py`

---

### HU-F2-002: Modelos ORM y migración — especialización por tipo de negocio

**Estado:** ✅ COMPLETADO

**Como** desarrollador backend  
**Quiero** tener las tablas `restaurant_sales` y `hardware_sales` como extensión 1:1 de `sales`  
**Para** almacenar campos específicos de cada tipo de negocio.

**Criterios de aceptación validados:**
- [x] `restaurant_sales` con: id, sale_id (UNIQUE FK CASCADE), table_number, guests, order_type, waiter_name, tip_amount, tip_pct, kitchen_notes
- [x] `hardware_sales` con: id, sale_id (UNIQUE FK CASCADE), invoice_type, delivery_address, requires_install, warranty_months
- [x] CHECK: `order_type` ('dine_in'|'takeout'|'delivery'), `invoice_type` ('boleta'|'factura')
- [x] Relación 1:1 garantizada por UNIQUE en sale_id
- [x] CASCADE elimina registro de especialización al eliminar venta

---

### HU-F2-003: Endpoints de sesión POS (abrir, cerrar, consultar)

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** abrir y cerrar turnos de caja en el POS  
**Para** tener control de arqueos diarios.

**Criterios de aceptación validados:**
- [x] `POST /api/sales/sessions/open` → crea sesión con `opening_cash`, retorna 201
- [x] Sesión existente abierta → 409 "Ya existe una sesión abierta"
- [x] `GET /api/sales/sessions/current` → sesión activa con ventas y totales
- [x] Sin sesión abierta → 404 "No hay sesión activa"
- [x] `POST /api/sales/sessions/{id}/close` → calcula `expected_cash`, `difference`, status 'closed'
- [x] Sesión ya cerrada → 409 Conflict

---

### HU-F2-004: Endpoints de ventas (crear, listar, detalle, anular)

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** registrar ventas con múltiples ítems y métodos de pago, consultarlas y anularlas  
**Para** operar el día a día del negocio.

**Criterios de aceptación validados:**
- [x] `POST /api/sales/sale` → crea venta con `sale_number` auto-generado (`VEN-YYYY-NNNNN`)
- [x] Sin sesión abierta → 400 "Debe abrir una sesión de caja primero"
- [x] Pagos insuficientes → 422 "El total de pagos no cubre el total de la venta"
- [x] `GET /api/sales/sales?from=&to=&business_type=` → lista paginada y filtrada
- [x] `GET /api/sales/sale/{id}` → cabecera + items + payments + especialización
- [x] `POST /api/sales/sale/{id}/void` → `is_voided=true`, revierte kárdex
- [x] Venta ya anulada → 409 "La venta ya está anulada"

**9 endpoints funcionando en `routers/sales.py`**

---

### HU-F2-005: Integración Kárdex — salida automática de inventario al vender

**Estado:** ✅ COMPLETADO

**Como** administrador de inventario  
**Quiero** que al registrar una venta, el sistema descuente automáticamente los productos del kárdex  
**Para** mantener el inventario siempre actualizado.

**Criterios de aceptación validados:**
- [x] `create_sale()` registra salida en kárdex por cada ítem con `reference_type='venta'`
- [x] Concepto: `"Venta #{sale_number}"`
- [x] `kardex_movement_id` guardado en `sale_items`
- [x] Ítem sin `product_id` → no genera movimiento de kárdex
- [x] Anulación de venta → reversión de movimientos de kárdex
- [x] Stock insuficiente → 409 "Stock insuficiente para producto X: disponible Y, solicitado Z"

---

### HU-F2-006: Integración contable — asiento automático de venta

**Estado:** ✅ COMPLETADO

**Como** contador  
**Quiero** que cada venta genere automáticamente su asiento contable  
**Para** que los libros contables reflejen los ingresos en tiempo real.

**Criterios de aceptación validados:**
- [x] `_generate_journal_entry()` genera asiento automático al crear venta
- [x] Débito: Caja (10) / Cuentas por Cobrar Tarjeta (121) según payment_method
- [x] Crédito: Ventas (40), IGV por pagar (201), Propinas por pagar (24)
- [x] Débito: Costo de Ventas (50) / Crédito: Inventarios (12)
- [x] Venta pagada con tarjeta → debita 121 en lugar de 10
- [x] Múltiples métodos de pago → líneas separadas por cada uno
- [x] Asiento balanceado (suma débitos = suma créditos)
- [x] Anulación → contra-asiento que revierte el original
- [x] `journal_entry_id` poblado en la venta

---

### HU-F2-007: Endpoints de ticket y métodos de pago

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** obtener un ticket de venta y consultar los métodos de pago activos  
**Para** entregar comprobantes a los clientes.

**Criterios de aceptación validados:**
- [x] `GET /api/sales/sale/{id}/ticket?format=json` → objeto con cabecera, items, totales, pagos
- [x] `GET /api/sales/sale/{id}/ticket?format=text` → texto plano 42 columnas (ticket térmico)
- [x] `GET /api/sales/payment-methods` → lista de métodos según feature flags
- [x] Ticket de restaurante incluye: mesa, mesero, tipo de orden
- [x] `TicketPreview.tsx` en frontend

---

### HU-F2-008: UI de apertura y cierre de caja

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** una interfaz para abrir y cerrar mi turno de caja  
**Para** iniciar operaciones y realizar el arqueo.

**Criterios de aceptación validados:**
- [x] Sin sesión abierta → formulario con monto inicial + botón "Abrir Caja"
- [x] Monto inválido (negativo/vacío/0) → validación en campo
- [x] POST exitoso → interfaz cambia a "Caja Abierta" con hora de apertura
- [x] Sesión abierta → resumen: hora apertura, total ventas, total efectivo, total tarjeta, total yape/plin + botón "Cerrar Caja"
- [x] Modal de arqueo: efectivo esperado, campo efectivo real, diferencia automática, notas
- [x] Confirmación → resumen final: total ventas, diferencia, hora de cierre

**Archivo:** `PosPage.tsx` (10KB)

---

### HU-F2-009: UI de registro de venta base

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** una interfaz para registrar ventas con búsqueda de productos y pagos  
**Para** atender clientes rápidamente.

**Criterios de aceptación validados:**
- [x] Formulario: buscador de productos, lista de ítems, subtotal/descuento/IGV/total, pagos
- [x] Búsqueda por nombre o código con sugerencias desde kárdex
- [x] Advertencia de stock insuficiente si cantidad > stock
- [x] Cálculos automáticos: subtotal = Σ(precio × cantidad), IGV según tax_config
- [x] Pagos → saldo pendiente actualizado en tiempo real
- [x] "Cobrar" → POST a `/api/sales/sale`, confirmación + opción ticket
- [x] Pagos insuficientes → "Falta S/ X.XX por pagar"
- [x] Error de servidor → mensaje sin perder datos del ticket

**Archivos:** `SalesNewPage.tsx`, `ProductSearch.tsx`, `SaleForm.tsx`

---

### HU-F2-010: UI de venta especializada por tipo de negocio

**Estado:** ✅ COMPLETADO

**Como** cajero  
**Quiero** que la interfaz de venta se adapte al tipo de negocio  
**Para** capturar datos específicos de restaurante o ferretería.

**Criterios de aceptación validados:**
- [x] `business_type = 'restaurant'` → campos: mesa, comensales, tipo orden, mesero, notas cocina
- [x] `business_type = 'hardware'` → campos: tipo comprobante, dirección entrega, requiere instalación, meses garantía
- [x] Selector de tipo de orden: dine_in / takeout / delivery
- [x] Feature flags controlan visibilidad de campos

**Archivos:** `RestaurantSaleFields.tsx`, `HardwareSaleFields.tsx`

---

### HU-F2-011: UI listado y detalle de ventas

**Estado:** ✅ COMPLETADO

**Como** administrador  
**Quiero** ver el listado de ventas con filtros y poder ver el detalle de cada una  
**Para** dar seguimiento a las operaciones del negocio.

**Criterios de aceptación validados:**
- [x] Listado paginado con: fecha, número, cliente, total, método pago, tipo
- [x] Filtros: rango fechas, tipo negocio, método pago, estado (activa/anulada)
- [x] Modal de detalle con: cabecera, ítems, pagos, especialización, ticket
- [x] Vista de ticket dentro del detalle
- [x] Estados: loading, empty ("No hay ventas en este período"), error

**Archivos:** `SalesListPage.tsx`, `SaleFilters.tsx`, `SaleDetail.tsx`

---

### HU-F2-012: Kárdex persistente (cierre almacén, resumen)

**Estado:** ✅ COMPLETADO

**Como** administrador de inventario  
**Quiero** que el kárdex tenga persistencia en base de datos con cierre de almacén funcional  
**Para** tener trazabilidad completa del inventario.

**Criterios de aceptación validados:**
- [x] DB-backed: `KardexEngine` con `KardexMovement` persistido
- [x] `GET /api/accounting/kardex/inventory/summary` → resumen con stocks y costos
- [x] `POST /api/accounting/kardex/warehouse-close` → cierra período y calcula diferencias
- [x] 19 tests de kárdex cubriendo: registro, entrada, salida, historial, cierre

**Archivos:** `KardexPage.tsx` (19KB), `KardexEngine`

---

## Brecha de Concurrencia

`sales_service.py:392-400` — generación de `sale_number`:

```python
count = await db.execute(select(func.count(Sale.id)).where(...))
sale_number = f"VEN-{year}-{count + 1:05d}"
```

**Riesgo:** `COUNT(*)` sin `SELECT ... FOR UPDATE`. Bajo concurrencia alta (2+ writes simultáneos), puede generar número duplicado.

**Severidad:** Media — no bloqueante para MVP con tráfico bajo.
**Fix recomendado:** Lock explícito o `INSERT ... RETURNING` con número calculado en DB.

---

*Documento generado por PO Agent 📋 con datos reales del deploy, 2026-05-14.*
