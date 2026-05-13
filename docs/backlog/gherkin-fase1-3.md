# Backlog Gherkin — Fases 1, 2 y 3

**Proyecto:** IaaS-RonSys  
**Origen:** [analysis-2026-05-12.md](../reports/analysis-2026-05-12.md)  
**Generado por:** PO Agent 📋  
**Fecha:** 2026-05-12  
**Total Historias:** 27 (F1: 8 | F2: 12 | F3: 7)

---

# Fase 1 — Fundamentos Estables

**Objetivo:** MVP desplegable con tipo de negocio configurable + flujo de caja proyectado.  
**Esfuerzo total estimado:** 7-9 días (backend 5-6d + frontend 2-3d)  
**Dependencia externa:** Ninguna (se construye sobre lo ya implementado).

---

### HU-F1-001: Definir tipo de negocio (business_type) en Company

**Como** administrador del sistema  
**Quiero** que cada empresa tenga un campo `business_type` enum en la base de datos  
**Para** que el sistema sepa si opera como restaurante, ferretería, retail o servicio y adapte su comportamiento.

**Criterios de aceptación:**
- [ ] Given una empresa existente sin `business_type` When se ejecuta la migración Then la columna se añade con DEFAULT 'restaurant' y CHECK sobre los valores permitidos
- [ ] Given una empresa con `economic_activity` que contenga "restaurante" When se ejecuta la migración de datos Then su `business_type` se actualiza a 'restaurant'
- [ ] Given una empresa con `economic_activity` que contenga "ferreter" When se ejecuta la migración de datos Then su `business_type` se actualiza a 'hardware'
- [ ] Given una empresa sin match en `economic_activity` When se ejecuta la migración Then su `business_type` se establece en 'retail'
- [ ] Given cualquier INSERT/UPDATE en companies When el valor de `business_type` no está en ('restaurant', 'hardware', 'retail', 'service') Then la DB rechaza la operación con constraint violation

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** Ninguna  
**Ficha técnica de referencia:** Sección §8.2-8.4 del analysis  
**Notas técnicas:**
- Migración Alembic: `ALTER TABLE companies ADD COLUMN business_type VARCHAR(20) NOT NULL DEFAULT 'restaurant'`
- Constraint: `CHECK (business_type IN ('restaurant', 'hardware', 'retail', 'service'))`
- Data migration con `UPDATE` condicional por `economic_activity ILIKE`
- Modelo SQLAlchemy: añadir campo `business_type` en `Company`

---

### HU-F1-002: Feature flags y tax_config en settings JSON de Company

**Como** administrador del sistema  
**Quiero** que cada empresa tenga feature flags y configuración tributaria en su campo `settings` JSON  
**Para** activar/desactivar funcionalidades específicas (mesas, propinas, delivery, factura) según el tipo de negocio sin cambiar código.

**Criterios de aceptación:**
- [ ] Given una empresa con `business_type = 'restaurant'` When consulto su settings Then contiene `features.tables_enabled: true`, `features.tips_enabled: true`, `features.recipe_explosion: true` y `tax_config.igv_included_in_price: true`
- [ ] Given una empresa con `business_type = 'hardware'` When consulto su settings Then contiene `features.warranty_tracking: true`, `features.invoice_required: true`, `tax_config.igv_included_in_price: false`
- [ ] Given un admin autenticado When hago PUT a `/api/admin/company/settings` con feature flags válidos Then los flags se persisten y la respuesta es 200
- [ ] Given un admin autenticado When hago PUT con un flag inexistente Then el sistema responde 422 con mensaje de validación
- [ ] Given la migración de Phase 1 When se ejecuta Then todas las empresas existentes reciben defaults de features según su `business_type`

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F1-001 (business_type debe existir)  
**Ficha técnica de referencia:** Sección §8.2, §8.3 del analysis  
**Notas técnicas:**
- Estructura JSON: `{ features: {...}, tax_config: {...} }`
- Backend: endpoint `PUT /api/admin/company/settings` o `PATCH /api/admin/company/{id}`
- Schema Pydantic con validación de feature flags permitidos
- Frontend: `useCompanySettings()` hook que expone `features` y `taxConfig`

---

### HU-F1-003: Adaptar UI según business_type y feature flags

**Como** usuario del sistema  
**Quiero** que la interfaz muestre solo las opciones relevantes para mi tipo de negocio  
**Para** no ver funcionalidades que no aplican (ej. un restaurante no necesita campos de garantía).

**Criterios de aceptación:**
- [ ] Given una empresa tipo 'restaurant' con `features.tables_enabled: true` When cargo el dashboard Then se muestra la sección de mesas/meseros en el layout
- [ ] Given una empresa tipo 'hardware' con `features.tables_enabled: false` When cargo el dashboard Then NO se muestra la sección de mesas/meseros
- [ ] Given `features.tips_enabled: true` When registro una venta Then el campo de propina es visible y editable
- [ ] Given `features.tips_enabled: false` When registro una venta Then el campo de propina está oculto
- [ ] Given `features.invoice_required: true` When emito un comprobante Then puedo elegir entre boleta y factura
- [ ] Given `features.invoice_required: false` When emito un comprobante Then solo se emite boleta por defecto

**Prioridad:** P2  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F1-002 (settings con feature flags deben existir)  
**Ficha técnica de referencia:** Sección §8.3 del analysis  
**Notas técnicas:**
- Hook `useCompanySettings()` en frontend, consume `GET /api/admin/company/settings`
- Renderizado condicional con feature flags, no con business_type directamente
- Tests unitarios con diferentes configuraciones de features

---

### HU-F1-004: Servicio de Flujo de Caja — vista proyectada (backend)

**Como** gerente financiero  
**Quiero** consultar el flujo de caja proyectado mes a mes  
**Para** anticipar necesidades de liquidez y tomar decisiones de inversión.

**Criterios de aceptación:**
- [ ] Given una empresa con setup completado (InvestmentVariables definidas) When llamo a `CashflowService.generate_projection(company_id, year)` Then obtengo 12 líneas de flujo de caja proyectadas con conceptos: Ventas, Costo de Ventas, Alquiler, Servicios, Salarios, Marketing, Administración, Mantenimiento
- [ ] Given una empresa sin setup When llamo al servicio Then responde con error claro: "No hay datos de proyección. Ejecute el setup contable primero."
- [ ] Given una proyección generada When verifico Then `net_cashflow = total_income - total_expenses` y `closing_balance = opening_balance + net_cashflow`
- [ ] Given el endpoint `GET /api/accounting/cashflow?view=projected&year=2026` When lo consulto con JWT válido Then responde 200 con el reporte completo de proyección
- [ ] Given el endpoint sin autenticación When lo consulto Then responde 401

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** Ninguna (usa datos ya existentes en `InvestmentVariables` del setup contable)  
**Ficha técnica de referencia:** Sección §9.2, §9.4 del analysis  
**Notas técnicas:**
- Crear archivo `core/accounting/cashflow.py` con clase `CashflowService`
- Modelos: `CashflowLine` (month, year, concept, category, projected, actual, difference) y `CashflowReport` (company_id, from_date, to_date, lines, opening_balance, net_cashflow, closing_balance)
- Endpoint en `routers/accounting.py`: `GET /api/accounting/cashflow`
- Query params: `view` (projected|actual|comparison), `from` (YYYY-MM), `to` (YYYY-MM)
- Los datos de proyección vienen de `statements.py` — extraer la lógica de `monthly_flows` a `CashflowService`

---

### HU-F1-005: Endpoint Flujo de Caja — vista real (backend)

**Como** gerente financiero  
**Quiero** ver el flujo de caja real basado en transacciones contables registradas  
**Para** saber exactamente cuánto dinero entró y salió, no solo lo proyectado.

**Criterios de aceptación:**
- [ ] Given existen asientos contables en `journal_entries` con movimientos en cuenta 10 (Efectivo) When consulto `GET /api/accounting/cashflow?view=actual&from=2026-01&to=2026-06` Then obtengo entradas reales (ventas en efectivo, otros ingresos) y salidas reales (costos, gastos, impuestos) del período
- [ ] Given no hay transacciones en el período When consulto Then el reporte muestra todas las líneas con `actual: 0`
- [ ] Given existen movimientos de kárdex (salidas de inventario) When calculo el flujo real Then los costos de venta se obtienen del kárdex, no de proyecciones
- [ ] Given el período consultado no tiene saldo inicial When se calcula automáticamente el `opening_balance` desde el saldo de la cuenta 10 al cierre del período anterior

**Prioridad:** P2  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F1-004 (CashflowService base), HU-F2-005 y HU-F2-006 (integración ventas → contabilidad → journal real)  
**Ficha técnica de referencia:** Sección §9.2 (Vista 2) del analysis  
**Notas técnicas:**
- Método `CashflowService.calculate_real(company_id, from_date, to_date)`
- Lee `journal_entries` filtradas por cuenta 10 (Efectivo) + categorías de ingreso/gasto
- Requiere que las ventas generen asientos contables (dependencia Fase 2)
- Sin Sales implementado, esta vista devuelve datos parciales (solo gastos operativos si se registraron manualmente)

---

### HU-F1-006: Comparativa proyectado vs real + alertas automáticas

**Como** gerente financiero  
**Quiero** comparar el flujo de caja proyectado contra el real y recibir alertas automáticas  
**Para** detectar desviaciones temprano y tomar acciones correctivas.

**Criterios de aceptación:**
- [ ] Given existen tanto proyección como datos reales para el mismo período When consulto `GET /api/accounting/cashflow?view=comparison&from=2026-01&to=2026-06` Then cada línea del reporte incluye `projected`, `actual` y `difference`
- [ ] Given las ventas reales están 20%+ por debajo de lo proyectado When genero la comparativa Then se incluye una alerta `severity: red` con mensaje "Ventas reales X están 20%+ bajo lo proyectado Y"
- [ ] Given el costo de ventas real está entre 5% y 20% sobre lo proyectado When genero la comparativa Then se incluye alerta `severity: yellow`
- [ ] Given todos los indicadores están dentro del 5% de desviación When genero la comparativa Then no se generan alertas (o se genera info `severity: green`)
- [ ] Given el flujo de caja neto real es negativo y el proyectado era positivo When se genera alerta `severity: red` por deterioro de liquidez

**Prioridad:** P2  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F1-004 (proyectado), HU-F1-005 (real)  
**Ficha técnica de referencia:** Sección §9.2 (Vista 3) y §9.4 del analysis  
**Notas técnicas:**
- Método `CashflowService.compare(projected, actual) -> dict` con líneas comparativas + array de alerts
- Umbrales de alerta configurables (por ahora hardcodeados: 5% info, 20% yellow, 30%+ red)
- Las alertas viajan en el mismo response del endpoint `view=comparison`

---

### HU-F1-007: UI de Flujo de Caja con selector de período/vista

**Como** gerente financiero  
**Quiero** ver el flujo de caja en una interfaz con selector de período y tipo de vista  
**Para** navegar fácilmente entre proyección, datos reales y comparativa.

**Criterios de aceptación:**
- [ ] Given estoy en la sección "Flujo de Caja" When la página carga Then veo un selector de año/mes inicio y año/mes fin
- [ ] Given el selector de vista When selecciono "Proyectado" Then se muestran las 12 barras mensuales con ingresos y egresos proyectados
- [ ] Given el selector de vista When selecciono "Real" Then se muestran los datos de transacciones reales (si existen)
- [ ] Given el selector de vista When selecciono "Comparativa" Then cada mes muestra dos barras lado a lado (proyectado vs real) con colores distintos
- [ ] Given existen alertas en la vista comparativa When cargo la página Then se renderiza un banner/toast con las alertas activas
- [ ] Given la respuesta del endpoint tarda más de 2 segundos When espero Then se muestra un skeleton loader

**Prioridad:** P2  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F1-004, HU-F1-005, HU-F1-006 (endpoints deben existir)  
**Ficha técnica de referencia:** Sección §9.4 del analysis  
**Notas técnicas:**
- Componente `CashflowChart.tsx` — refactorizar el existente (actualmente con 26% coverage)
- Selector de período con `MonthPicker` o inputs controlados
- Gráfico de barras agrupadas para vista comparativa
- Integración con `useCashflow` hook que consume `GET /api/accounting/cashflow`

---

### HU-F1-008: Persistencia de proyecciones de flujo de caja

**Como** gerente financiero  
**Quiero** que las proyecciones de flujo de caja se persistan en base de datos  
**Para** no recalcularlas desde cero cada vez y poder versionar proyecciones anuales.

**Criterios de aceptación:**
- [ ] Given una proyección generada para el año 2026 When se persiste Then se crean registros en `cashflow_projections` con company_id, month, year, concept, category, amount
- [ ] Given ya existe una proyección para el mismo (company_id, year, month, concept) When intento insertar Then la constraint UNIQUE rechaza el duplicado
- [ ] Given un cambio en los InvestmentVariables del setup When regenero la proyección Then los registros existentes se actualizan (UPSERT por month+year+concept)
- [ ] Given la tabla `cashflow_projections` existe When consulto Then tiene índices para búsqueda eficiente por company_id + year

**Prioridad:** P3  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** HU-F1-004 (CashflowService)  
**Ficha técnica de referencia:** Sección §9.3 del analysis  
**Notas técnicas:**
- Migración Alembic separada para `cashflow_projections`
- Modelo SQLAlchemy `CashflowProjection`
- Constraint: `UNIQUE(company_id, year, month, concept)`
- Método `CashflowService.save_projection()` con UPSERT

---

# Fase 2 — Módulos Comerciales

**Objetivo:** POS funcional con especialización restaurante/ferretería + Kárdex persistente.  
**Esfuerzo total estimado:** 12-15 días (backend 7-9d + frontend 5-6d)  
**Dependencia externa:** HU-F1-001 (business_type), HU-F1-002 (feature flags).

---

### HU-F2-001: Modelos ORM y migración — tablas base de ventas

**Como** desarrollador backend  
**Quiero** tener las tablas `pos_sessions`, `sales`, `sale_items` y `sale_payments` creadas con sus modelos SQLAlchemy  
**Para** que el sistema pueda registrar turnos de caja, ventas, sus ítems y los métodos de pago.

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `pos_sessions` con columnas: id, company_id, user_id, opened_at, closed_at, opening_cash, closing_cash, expected_cash, difference, status, notes
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `sales` con columnas: id, company_id, session_id, user_id, sale_number, sale_date, sale_time, customer_name, customer_doc, subtotal, discount_total, tax_total, tip_amount, total, business_type, is_voided, journal_entry_id
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `sale_items` con: id, sale_id (FK CASCADE), product_id, item_name, item_type, quantity, unit_of_measure, unit_price, discount_pct, discount_amount, tax_pct, tax_amount, total, kardex_movement_id
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `sale_payments` con: id, sale_id (FK CASCADE), payment_method, amount, reference
- [ ] Given un seed o insert de prueba When creo una venta con 2 ítems y 2 métodos de pago Then las relaciones FK se respetan y el CASCADE funciona al eliminar la venta

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F1-001 (business_type)  
**Ficha técnica de referencia:** Sección §7.1 del analysis  
**Notas técnicas:**
- Archivo de migración Alembic único para las 4 tablas
- Modelos SQLAlchemy en `models/sales.py` (nuevo archivo)
- Schemas Pydantic en `schemas/sales.py`
- `pos_sessions.status` con CHECK: 'open' | 'closed'
- `sale_payments.payment_method` con CHECK: 'cash' | 'card' | 'yape' | 'plin' | 'transfer'
- `sale_items.item_type` con CHECK: 'product' | 'service' | 'combo'

---

### HU-F2-002: Modelos ORM y migración — especialización por tipo de negocio

**Como** desarrollador backend  
**Quiero** tener las tablas `restaurant_sales` y `hardware_sales` como extensión 1:1 de `sales`  
**Para** almacenar campos específicos de cada tipo de negocio sin inflar la tabla base.

**Criterios de aceptación:**
- [ ] Given la migración ejecutada When verifico la DB Then existe `restaurant_sales` con: id, sale_id (UNIQUE FK CASCADE), table_number, guests, order_type, waiter_name, tip_amount, tip_pct, kitchen_notes
- [ ] Given la migración ejecutada When verifico la DB Then existe `hardware_sales` con: id, sale_id (UNIQUE FK CASCADE), invoice_type, delivery_address, requires_install, warranty_months
- [ ] Given una venta de restaurante When inserto en `sales` y `restaurant_sales` en la misma transacción Then ambas tablas reflejan la relación 1:1
- [ ] Given elimino una venta (CASCADE) When la venta tiene registro en `restaurant_sales` Then el registro en `restaurant_sales` también se elimina automáticamente

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** HU-F2-001 (tablas base deben existir)  
**Ficha técnica de referencia:** Sección §7.1 (Tablas de especialización) del analysis  
**Notas técnicas:**
- Misma migración que HU-F2-001 o migración adicional (según orden de implementación)
- Modelos en `models/sales.py`
- `restaurant_sales.order_type` CHECK: 'dine_in' | 'takeout' | 'delivery'
- `hardware_sales.invoice_type` CHECK: 'boleta' | 'factura'

---

### HU-F2-003: Endpoints de sesión POS (abrir, cerrar, consultar)

**Como** cajero  
**Quiero** abrir y cerrar turnos de caja en el POS  
**Para** tener control de arqueos diarios y responsabilidad sobre el efectivo manejado.

**Criterios de aceptación:**
- [ ] Given un usuario autenticado sin sesión abierta When hago POST `/api/sales/sessions/open` con `opening_cash: 200` Then se crea una sesión con status 'open', se retorna 201 con el objeto `pos_session`
- [ ] Given un usuario autenticado que YA tiene una sesión abierta When hago POST `/api/sales/sessions/open` Then el sistema responde 409 Conflict con mensaje "Ya existe una sesión abierta"
- [ ] Given una sesión abierta When hago GET `/api/sales/sessions/current` Then obtengo la sesión activa con sus ventas del turno y totales acumulados
- [ ] Given no hay sesión abierta When hago GET `/api/sales/sessions/current` Then responde 404 con mensaje "No hay sesión activa"
- [ ] Given una sesión abierta con ventas registradas When hago POST `/api/sales/sessions/{id}/close` con `closing_cash: 850` Then el sistema calcula `expected_cash = opening_cash + ventas_efectivo`, compara con `closing_cash` y retorna `difference` y status cambia a 'closed'
- [ ] Given intento cerrar una sesión ya cerrada When hago POST close Then responde 409 Conflict

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F2-001 (tablas deben existir)  
**Ficha técnica de referencia:** Sección §7.6 del analysis  
**Notas técnicas:**
- Archivo `routers/sales.py` (nuevo) + `services/sales_service.py` (nuevo)
- `POST /api/sales/sessions/open` → crea sesión, valida que no haya otra abierta para el mismo usuario+company
- `POST /api/sales/sessions/{id}/close` → calcula expected_cash desde sale_payments con method='cash', cierra sesión
- `GET /api/sales/sessions/current` → busca sesión con status='open' para company_id del tenant

---

### HU-F2-004: Endpoints de ventas (crear, listar, detalle, anular)

**Como** cajero  
**Quiero** registrar ventas con múltiples ítems y métodos de pago, consultarlas y anularlas  
**Para** operar el día a día del negocio.

**Criterios de aceptación:**
- [ ] Given una sesión POS abierta When hago POST `/api/sales/sale` con body que incluye items (mínimo 1) y payments (suma >= total) Then se crea la venta con sale_number auto-generado (VEN-YYYY-NNNNN), se asocia a la sesión y retorna 201
- [ ] Given intento crear una venta sin sesión abierta When hago POST Then responde 400 con "Debe abrir una sesión de caja primero"
- [ ] Given payments suman menos que el total de la venta When hago POST Then responde 422 con "El total de pagos no cubre el total de la venta"
- [ ] Given items incluyen `product_id` de un producto que existe en kárdex When se crea la venta Then se asocia el `kardex_movement_id` al item (si HU-F2-005 está implementada)
- [ ] Given ventas existentes When hago GET `/api/sales/sales?from=2026-05-01&to=2026-05-31&business_type=restaurant` Then obtengo lista paginada y filtrada de ventas del período
- [ ] Given una venta existente When hago GET `/api/sales/sale/{id}` Then obtengo cabecera, items, payments y datos de especialización (restaurant_sales o hardware_sales)
- [ ] Given una venta no anulada When hago POST `/api/sales/sale/{id}/void` con `reason` Then `is_voided=true`, se guarda `void_reason` y se revierten movimientos de kárdex asociados
- [ ] Given una venta ya anulada When intento anular de nuevo Then responde 409 "La venta ya está anulada"

**Prioridad:** P1  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F2-001, HU-F2-002, HU-F2-003 (sesión debe existir para crear venta)  
**Ficha técnica de referencia:** Sección §7.4, §7.6 del analysis  
**Notas técnicas:**
- `sale_number`: formato `VEN-{YYYY}-{seq:05d}` con secuencia por company+año (usar `SELECT FOR UPDATE` o secuencia DB)
- Endpoint `GET /api/sales/sales` con query params: `from`, `to`, `business_type`, `session_id`, `is_voided`, `page`, `limit`
- Anulación: revierte kárdex si existe, NO borra registros (soft delete con `is_voided`)
- Schemas: `SaleCreate`, `SaleItemCreate`, `SalePaymentCreate`, `SaleResponse`, `SaleDetailResponse`

---

### HU-F2-005: Integración Kárdex — salida automática de inventario al vender

**Como** administrador de inventario  
**Quiero** que al registrar una venta, el sistema descuente automáticamente los productos del kárdex  
**Para** mantener el inventario siempre actualizado sin intervención manual.

**Criterios de aceptación:**
- [ ] Given una venta con ítems que tienen `product_id` y `quantity` When se crea la venta Then se registra una salida en kárdex por cada ítem con `reference_type='venta'` y concepto "Venta VEN-YYYY-NNNNN"
- [ ] Given un ítem de venta sin `product_id` (producto no catalogado) When se crea la venta Then NO se genera movimiento de kárdex para ese ítem
- [ ] Given una venta de restaurante con productos que son combos/platos When se crea la venta Then el sistema aplica explosión de receta (si está definida) → múltiples salidas de insumos
- [ ] Given stock insuficiente para un ítem When intento crear la venta Then responde 409 con "Stock insuficiente para producto X: disponible Y, solicitado Z" y no se crea la venta
- [ ] Given se anula una venta When se ejecuta HU-F2-004 void Then los movimientos de kárdex asociados se revierten (entrada de devolución)

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F2-001, HU-F2-004 (venta debe existir), HU-F2-012 (kárdex persistente para referencia)  
**Ficha técnica de referencia:** Sección §7.4 del analysis  
**Notas técnicas:**
- Lógica en `SalesService.create_sale()` — después de persistir la venta, iterar ítems con `product_id`
- Llamar a `kardex_engine.record_exit(product_code, quantity, concept, reference_type='venta')`
- Guardar `kardex_movement_id` en `sale_items`
- TODO futuro: explosión de receta (requiere tabla de recetas/combos)

---

### HU-F2-006: Integración contable — asiento automático de venta

**Como** contador  
**Quiero** que cada venta genere automáticamente su asiento contable  
**Para** que los libros contables reflejen los ingresos en tiempo real sin conciliación manual.

**Criterios de aceptación:**
- [ ] Given una venta de ferretería por S/ 118 (S/ 100 + IGV S/ 18) When se crea la venta Then se genera automáticamente un asiento contable que debita Caja (10) por 118, acredita Ventas (40) por 100, acredita IGV por pagar (201) por 18, debita Costo de Ventas (50) por costo, acredita Inventarios (12) por costo
- [ ] Given una venta de restaurante por S/ 71.50 (incluye IGV + propina S/ 6.50) When se crea la venta Then se genera un asiento que incluye cuenta 24 "Propinas por pagar" por S/ 6.50
- [ ] Given una venta pagada 100% con tarjeta When se genera el asiento Then se debita "Cuentas por Cobrar Tarjeta" en lugar de Caja
- [ ] Given una venta con múltiples métodos de pago When se genera el asiento Then se registran líneas separadas por cada método (efectivo → Caja, tarjeta → Ctas Cobrar, yape/plin → Caja)
- [ ] Given la venta tiene `journal_entry_id` poblado When consulto el asiento Then existe y está balanceado (suma débitos = suma créditos)
- [ ] Given se anula una venta When se ejecuta HU-F2-004 void Then se genera un contra-asiento que revierte el asiento original

**Prioridad:** P1  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F2-004 (venta), HU-F2-005 (kárdex para costo), Motor Contable (existente)  
**Ficha técnica de referencia:** Sección §7.5 del analysis  
**Notas técnicas:**
- Método en `SalesService`: `_generate_sale_journal_entry(sale, items)` o delegar a `AccountingEngine`
- Reutiliza `engine.py` — método existente de generación de asientos
- El plan de cuentas PCGE ya tiene las cuentas necesarias (10, 12, 40, 50, 201, 24)
- Mapeo de payment_method a cuenta contable: cash→10, card→121, yape→10, plin→10, transfer→104
- El `Cost of Sales` (50) se calcula desde kárdex (costo promedio del producto × cantidad)

---

### HU-F2-007: Endpoints de ticket y métodos de pago

**Como** cajero  
**Quiero** obtener un ticket/comprobante de venta y consultar los métodos de pago activos  
**Para** entregar comprobantes a los clientes y saber qué medios de pago acepta mi empresa.

**Criterios de aceptación:**
- [ ] Given una venta existente When hago GET `/api/sales/sale/{id}/ticket?format=json` Then obtengo un objeto con cabecera, items, totales y métodos de pago en formato ticket
- [ ] Given una venta existente When hago GET `/api/sales/sale/{id}/ticket?format=text` Then obtengo texto plano formateado como ticket térmico (40 columnas)
- [ ] Given el endpoint `GET /api/sales/payment-methods` When lo consulto Then retorna la lista de métodos de pago habilitados para la company según feature flags: cash, card, yape, plin, transfer (todos por defecto)
- [ ] Given el endpoint de ticket When la venta tiene restaurant_sales Then el ticket incluye número de mesa, mesero, tipo de orden

**Prioridad:** P2  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F2-004 (venta debe existir)  
**Ficha técnica de referencia:** Sección §7.6 del analysis  
**Notas técnicas:**
- `GET /api/sales/sale/{id}/ticket` con query param `format` (json|text)
- `GET /api/sales/payment-methods` lee feature flags de la company para filtrar métodos
- El formato texto imita ticket térmico estándar (40 chars, alineación monoespaciada)

---

### HU-F2-008: UI de apertura y cierre de caja

**Como** cajero  
**Quiero** una interfaz para abrir y cerrar mi turno de caja  
**Para** iniciar operaciones y realizar el arqueo al final del turno.

**Criterios de aceptación:**
- [ ] Given no hay sesión abierta When entro al POS Then veo un formulario para ingresar el monto de caja inicial y un botón "Abrir Caja"
- [ ] Given ingreso monto inicial inválido (negativo, vacío, 0) When presiono "Abrir Caja" Then se muestra validación en el campo
- [ ] Given el monto es válido When presiono "Abrir Caja" Then se envía POST a `/api/sales/sessions/open`, se muestra confirmación y la interfaz cambia a "Caja Abierta" con hora de apertura
- [ ] Given una sesión abierta When estoy en el POS Then veo un resumen del turno: hora apertura, total ventas del turno, total en efectivo, total tarjeta, total yape/plin y un botón "Cerrar Caja"
- [ ] Given presiono "Cerrar Caja" When la sesión tiene ventas Then se muestra un modal de arqueo con: efectivo esperado (calculado), campo para efectivo real contado, diferencia automática y campo de notas
- [ ] Given confirmo el cierre When se envía POST close Then se muestra resumen final: total ventas, diferencia de caja, hora de cierre

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F2-003 (endpoints sesión POS deben existir)  
**Ficha técnica de referencia:** Sección §7.1, §7.6 del analysis  
**Notas técnicas:**
- Componentes: `PosSessionOpen.tsx`, `PosSessionClose.tsx`, `PosSessionStatus.tsx`
- Hook: `usePosSession()` que maneja estado de sesión actual
- Ruta: `/pos/session` o integrado en el layout del POS
- Tests: validación de formulario, flujo open→operar→close, manejo de error 409

---

### HU-F2-009: UI de registro de venta base

**Como** cajero  
**Quiero** una interfaz para registrar ventas con búsqueda de productos, cantidades y múltiples métodos de pago  
**Para** atender clientes rápidamente.

**Criterios de aceptación:**
- [ ] Given una sesión abierta When entro a "Nueva Venta" Then veo un formulario con: buscador de productos, lista de ítems agregados, subtotal/descuento/IGV/total, y sección de pagos
- [ ] Given busco un producto por nombre o código When escribo en el buscador Then se sugieren productos desde el kárdex con precio y stock disponible
- [ ] Given agrego un ítem al ticket When especifico cantidad > stock Then se muestra advertencia de stock insuficiente
- [ ] Given agrego 3 ítems al ticket When reviso Then subtotal = Σ(precio × cantidad), IGV se calcula según tax_config, descuento aplica, total es correcto
- [ ] Given tengo ítems en el ticket When agrego un pago en efectivo Then la sección de pagos muestra lo pagado y el saldo pendiente
- [ ] Given los pagos cubren el total When presiono "Cobrar" Then se envía POST a `/api/sales/sale`, se muestra confirmación y opción de imprimir ticket
- [ ] Given los pagos NO cubren el total When presiono "Cobrar" Then se muestra error "Falta S/ X.XX por pagar"
- [ ] Given hay un error del servidor al crear la venta When presiono "Cobrar" Then se muestra mensaje de error y NO se pierden los datos del ticket

**Prioridad:** P1  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F2-004 (endpoint venta), HU-F2-005 (kárdex), HU-F2-008 (sesión abierta requerida)  
**Ficha técnica de referencia:** Sección §7.4, §7.6 del analysis  
**Notas técnicas:**
- Componentes: `SaleForm.tsx`, `ProductSearch.tsx`, `SaleItemsList.tsx`, `PaymentSection.tsx`
- Estado del ticket en React context o estado local rico
- ProductSearch consume endpoint de kárdex existente (`GET /api/accounting/kardex/products`)
- Cálculo de IGV según `tax_config.igv_included_in_price` del feature flag
- Tests: validación de totales, flujo de pago completo, error handling

---

### HU-F2-010: UI de venta especializada por tipo de negocio

**Como** cajero de restaurante / cajero de ferretería  
**Quiero** ver campos específicos de mi tipo de negocio en la pantalla de venta  
**Para** registrar información relevante como mesa y mesero (restaurante) o tipo de comprobante y garantía (ferretería).

**Criterios de aceptación:**
- [ ] Given una empresa tipo 'restaurant' con `features.tables_enabled: true` When estoy en la pantalla de venta Then veo campos: número de mesa, número de comensales, tipo de orden (dine_in/takeout/delivery), nombre del mesero
- [ ] Given una empresa tipo 'restaurant' con `features.tips_enabled: true` When estoy en la pantalla de venta Then veo campo de propina (monto o porcentaje) y se suma al total
- [ ] Given una empresa tipo 'restaurant' When agrego un ítem al ticket Then puedo añadir notas de cocina ("Sin cebolla", "Término medio")
- [ ] Given una empresa tipo 'hardware' When estoy en la pantalla de venta Then NO veo campos de mesa, mesero ni propina
- [ ] Given una empresa tipo 'hardware' con `features.invoice_required: true` When estoy en la pantalla de venta Then veo selector boleta/factura y campo de RUC/DNI del cliente
- [ ] Given una empresa tipo 'hardware' con `features.warranty_tracking: true` When la venta incluye productos con garantía Then veo campos de meses de garantía y dirección de despacho

**Prioridad:** P2  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F2-009 (UI base de venta), HU-F1-003 (feature flags en UI)  
**Ficha técnica de referencia:** Sección §7.2, §8.3 del analysis  
**Notas técnicas:**
- Componentes especializados: `RestaurantSaleFields.tsx`, `HardwareSaleFields.tsx`
- Renderizado condicional por `useCompanySettings().features`
- Los campos extra se envían al endpoint de creación de venta que persiste en `restaurant_sales` o `hardware_sales`
- Tests: verificar que campos de restaurante NO se renderizan en contexto ferretería y viceversa

---

### HU-F2-011: UI de listado de ventas con filtros y ticket

**Como** administrador  
**Quiero** consultar el historial de ventas con filtros por fecha, tipo, sesión y ver el ticket de cada venta  
**Para** hacer seguimiento de ingresos y resolver disputas con clientes.

**Criterios de aceptación:**
- [ ] Given ventas registradas When entro a "Historial de Ventas" Then veo una tabla paginada con: número de venta, fecha/hora, total, método de pago, estado (activa/anulada), cajero
- [ ] Given el selector de filtros When selecciono rango de fechas Then la tabla se actualiza con ventas del período
- [ ] Given el filtro de tipo de negocio When selecciono "Restaurante" Then solo se muestran ventas con `business_type='restaurant'`
- [ ] Given el filtro de sesión When selecciono una sesión específica Then solo se muestran ventas de ese turno
- [ ] Given una venta en la lista When hago clic en "Ver detalle" Then se abre un drawer/modal con todos los ítems, pagos y datos de especialización
- [ ] Given el detalle de una venta When presiono "Imprimir Ticket" Then se muestra el ticket formateado (vista previa) con opción de imprimir
- [ ] Given una venta no anulada When soy admin o cajero del turno Then veo botón "Anular" que abre confirmación con campo de motivo
- [ ] Given confirmo la anulación con motivo When se ejecuta Then la venta se marca como anulada y desaparece de la lista activa (queda en filtro "Anuladas")

**Prioridad:** P2  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F2-004 (endpoints list/detail/void), HU-F2-007 (ticket endpoint)  
**Ficha técnica de referencia:** Sección §7.6 del analysis  
**Notas técnicas:**
- Componentes: `SalesList.tsx`, `SaleDetail.tsx`, `SaleFilters.tsx`, `TicketPreview.tsx`
- Paginación infinita o tradicional con `page`/`limit`
- Ticket preview usa `GET /api/sales/sale/{id}/ticket?format=text` y lo renderiza en `<pre>` con fuente monoespaciada
- Tests: filtrado, paginación, flujo de anulación con confirmación

---

### HU-F2-012: Migrar Kárdex de variables en memoria a repositorio DB

**Como** administrador del sistema  
**Quiero** que el kárdex persista sus datos en base de datos en lugar de variables en memoria  
**Para** que los datos de inventario sobrevivan a reinicios del servidor y sean consistentes.

**Criterios de aceptación:**
- [ ] Given el sistema inicia When se registra un producto y un movimiento de entrada Then los datos se persisten en `kardex_movements` (o tabla equivalente) en PostgreSQL
- [ ] Given reinicio el contenedor del backend When vuelvo a consultar el kárdex de un producto Then los movimientos registrados antes del reinicio siguen disponibles
- [ ] Given existían variables globales `_kardex_engine` en los routers When se completa la migración Then los routers obtienen el kárdex desde el repositorio DB inyectado por dependencia
- [ ] Given el cambio de arquitectura When ejecuto los tests existentes de kárdex (`test_kardex.py`, 20 tests) Then los 20 tests siguen pasando con el repositorio DB (usando fixture de test DB o mock)
- [ ] Given dos requests concurrentes modifican el kárdex del mismo producto When se procesan Then no hay race conditions (la DB maneja la concurrencia con locks)

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** Ninguna (el kárdex ya existe en memoria, es migración de persistencia)  
**Ficha técnica de referencia:** Sección §3.3 (hallazgo #5) del analysis  
**Notas técnicas:**
- Implementar `KardexRepository` como adaptador DB del puerto de kárdex
- Modelo `KardexMovement` si no existe ya como tabla (verificar si la migración está creada)
- Inyectar `KardexRepository` via FastAPI `Depends()` en lugar de variable global `_kardex_engine`
- Los routers actuales (`accounting.py`) ya usan `_kardex_engine` — refactorizar
- Tests: usar `TestClient` con override de dependencia para inyectar repositorio con DB de prueba

---

# Fase 3 — Agentes de IA

**Objetivo:** Skills de IA funcionales con orquestador LLM y endpoint de consulta conversacional.  
**Esfuerzo total estimado:** 9-11 días (backend 7-8d + frontend 2-3d)  
**Dependencia externa:** Fase 1 y Fase 2 completas (las skills requieren datos reales de ventas, inventario y finanzas).

---

### HU-F3-001: SalesSkill — skill de IA para consultas de ventas

**Como** gerente  
**Quiero** poder preguntar en lenguaje natural sobre las ventas del negocio  
**Para** obtener insights sin tener que navegar reportes manualmente.

**Criterios de aceptación:**
- [ ] Given la skill `SalesSkill` registrada en el `SkillRegistry` When consulto su nombre Then es 'sales'
- [ ] Given datos de ventas existentes When ejecuto `SalesSkill.execute(context, {"query": "ventas totales de mayo 2026"})` Then el `SkillResult` contiene total de ventas del mes, desglose por tipo y comparación con mes anterior
- [ ] Given el parámetro `action: "top_products"` When ejecuto la skill Then retorna los 10 productos más vendidos con cantidades e ingresos
- [ ] Given el parámetro `action: "sales_by_hour"` When ejecuto la skill Then retorna distribución de ventas por hora del día
- [ ] Given el parámetro `action: "payment_methods"` When ejecuto la skill Then retorna desglose de ventas por método de pago (efectivo, tarjeta, yape, plin)
- [ ] Given la skill se ejecuta sin datos de ventas (empresa nueva) When retorna Then `SkillResult.success=true` con mensaje "Aún no hay datos de ventas registrados"

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F2-004 (datos de ventas deben existir en DB)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `core/agents/skills/sales_skill.py`
- Extiende `BaseSkill` (clase abstracta con `name`, `description`, `execute`)
- `execute()` recibe `AgentContext` y `params: dict` con `action` y filtros opcionales
- Consulta modelos `Sale`, `SaleItem`, `SalePayment` via SQLAlchemy
- `description` debe describir capacidades para que el LLM sepa cuándo invocarla

---

### HU-F3-002: InventorySkill — skill de IA para consultas de inventario

**Como** administrador de inventario  
**Quiero** consultar en lenguaje natural el estado del inventario, stock bajo y rotación  
**Para** tomar decisiones de compra sin tener que revisar manualmente el kárdex.

**Criterios de aceptación:**
- [ ] Given la skill `InventorySkill` registrada When consulto su nombre Then es 'inventory'
- [ ] Given productos con stock When ejecuto `action: "low_stock"` Then retorna productos con stock por debajo del mínimo configurado
- [ ] Given un producto específico When ejecuto `action: "product_detail", product_code="X"` Then retorna stock actual, costo promedio, última entrada/salida y rotación
- [ ] Given ejecuto `action: "inventory_value"` Then retorna valorización total del inventario a costo promedio
- [ ] Given ejecuto `action: "rotation"` Then retorna productos con mayor y menor rotación en los últimos 30/60/90 días
- [ ] Given un producto sin movimientos When consulto su rotación Then se indica "Sin movimiento en el período"

**Prioridad:** P2  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-F2-012 (kárdex persistente debe existir)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `core/agents/skills/inventory_skill.py`
- Extiende `BaseSkill`
- Consulta modelos de kárdex (movimientos, productos, costo promedio)
- `low_stock`: necesita campo `min_stock` o umbral configurable por company
- `inventory_value`: Σ(stock × costo_promedio) para todos los productos

---

### HU-F3-003: FinanceSkill — skill de IA para consultas financieras

**Como** gerente financiero  
**Quiero** consultar en lenguaje natural sobre ratios, flujo de caja, rentabilidad y proyecciones  
**Para** tener una vista financiera rápida sin necesidad de generar reportes completos.

**Criterios de aceptación:**
- [ ] Given la skill `FinanceSkill` registrada When consulto su nombre Then es 'finance'
- [ ] Given datos contables existentes When ejecuto `action: "ratios"` Then retorna los 9 ratios financieros con semáforo, NPV, IRR y payback
- [ ] Given ejecuto `action: "cashflow"` con período When retorna resumen de flujo de caja (proyectado si no hay real, comparativa si ambos existen)
- [ ] Given ejecuto `action: "profitability"` When retorna margen bruto, margen operativo, margen neto, ROA, ROE del período
- [ ] Given ejecuto `action: "alerts"` When retorna alertas financieras activas: cashflow negativo, ratios en rojo, desviaciones >20%
- [ ] Given ejecuto `action: "breakeven"` When retorna punto de equilibrio basado en costos fijos y margen de contribución
- [ ] Given una consulta no reconocida When ejecuto con action inválido Then retorna `SkillResult.success=false` con mensaje de acciones disponibles

**Prioridad:** P2  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F1-004 (cashflow), Motor Contable + Ratios (existentes)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `core/agents/skills/finance_skill.py`
- Reutiliza `ratios.py`, `cashflow.py` (nuevo), `statements.py` existentes
- `breakeven`: punto de equilibrio = costos fijos / (1 - costo_variable_pct)
- La skill actúa como fachada que orquesta los servicios contables existentes

---

### HU-F3-004: SkillLoader con decorador @skill y auto-registro

**Como** desarrollador  
**Quiero** que las skills se registren automáticamente al iniciar la aplicación mediante un decorador  
**Para** no tener que registrar manualmente cada skill nueva.

**Criterios de aceptación:**
- [ ] Given una clase que extiende `BaseSkill` y está decorada con `@register_skill` When la aplicación inicia Then la skill aparece automáticamente en el `SkillRegistry`
- [ ] Given dos skills con el mismo nombre When se intentan registrar Then se lanza `ValueError` con mensaje claro
- [ ] Given el endpoint `GET /api/agents/skills` When lo consulto Then retorna la lista de skills registradas con nombre y descripción
- [ ] Given una skill se registra exitosamente When consulto `skill_registry.get_skills_context()` Then genera texto descriptivo para enviar al LLM
- [ ] Given el `SkillRegistry` es un singleton When múltiples módulos lo importan Then todos comparten la misma instancia

**Prioridad:** P2  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F3-001, HU-F3-002, HU-F3-003 (skills concretas deben existir para probar registro)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `core/agents/loader.py` (nuevo)
- Decorador: `@register_skill` que llama a `skill_registry.register(instance)`
- Auto-descubrimiento: escanear `core/agents/skills/` e importar módulos, o usar entry_points
- Inicialización en `app/main.py` durante startup
- El `SkillRegistry` singleton ya existe en `base.py`

---

### HU-F3-005: AgentOrchestrator con conexión OpenRouter

**Como** usuario del sistema  
**Quiero** que el orquestador de agentes entienda mis preguntas en lenguaje natural y ejecute la skill correcta  
**Para** obtener respuestas sin saber qué skills existen ni cómo invocarlas.

**Criterios de aceptación:**
- [ ] Given una pregunta "¿cuánto vendimos este mes?" When llega al `AgentOrchestrator` Then el LLM (vía OpenRouter) clasifica la intención como `sales` y ejecuta `SalesSkill` con los parámetros adecuados
- [ ] Given una pregunta ambigua "¿cómo va el negocio?" When llega al orquestador Then el LLM puede decidir ejecutar múltiples skills (sales + finance) y consolidar la respuesta
- [ ] Given el LLM no puede clasificar la intención When procesa Then responde amablemente indicando qué tipo de preguntas puede responder
- [ ] Given el LLM falla (timeout, error de API) When el orquestador detecta el error Then retorna `SkillResult.success=false` con mensaje de error y no crashea
- [ ] Given la respuesta del LLM + skills When se retorna al usuario Then incluye `metadata` con: skills ejecutadas, tiempo de respuesta, tokens usados

**Prioridad:** P1  
**Esfuerzo estimado:** 2 días  
**Dependencias:** HU-F3-001, HU-F3-002, HU-F3-003, HU-F3-004 (skills + loader deben existir)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `core/agents/orchestrator.py` (nuevo)
- Usa `openai` Python SDK apuntando a OpenRouter base_url (`https://openrouter.ai/api/v1`)
- System prompt: incluye `skill_registry.get_skills_context()` para que el LLM conozca las skills
- Flujo: user_query → LLM decide skill + params → ejecutar skill → LLM formula respuesta amigable
- Configuración: `OPENROUTER_API_KEY` y `OPENROUTER_MODEL` en variables de entorno
- Rate limiting y retry con exponential backoff para llamadas a OpenRouter

---

### HU-F3-006: Endpoint de consulta conversacional con IA

**Como** usuario del sistema  
**Quiero** un endpoint único donde enviar preguntas en lenguaje natural  
**Para** obtener respuestas inteligentes sobre ventas, inventario y finanzas.

**Criterios de aceptación:**
- [ ] Given un usuario autenticado When hago POST `/api/agents/query` con `{"query": "¿cuánto vendí en mayo?"}` Then el sistema orquesta la skill correcta y retorna 200 con la respuesta en lenguaje natural
- [ ] Given un request sin autenticación When hago POST Then retorna 401
- [ ] Given un request con `query` vacío When hago POST Then retorna 422 con error de validación
- [ ] Given un request con `conversation_id` existente When hago POST Then el orquestador recupera el contexto de conversación previa
- [ ] Given el body incluye `stream: true` When hago POST Then la respuesta es Server-Sent Events (SSE) con tokens en tiempo real (opcional, nice-to-have)
- [ ] Given el endpoint recibe múltiples requests concurrentes When proceso Then cada request se maneja independientemente sin mezclar contextos

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** HU-F3-005 (AgentOrchestrator debe existir)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Archivo: `routers/agents.py` (nuevo)
- Schema: `AgentQueryRequest(query: str, conversation_id: Optional[str], stream: bool = False)`
- Schema: `AgentQueryResponse(answer: str, skills_used: list[str], metadata: dict)`
- El `conversation_id` permite historial de conversación (requiere tabla `agent_conversations` opcional o almacenar en Redis)
- Registrar router en `main.py`

---

### HU-F3-007: UI de consulta conversacional con IA

**Como** gerente  
**Quiero** un chat integrado en la aplicación donde pueda hacer preguntas sobre el negocio  
**Para** obtener insights sin salir del sistema.

**Criterios de aceptación:**
- [ ] Given estoy autenticado When abro el panel de "Asistente IA" Then veo una interfaz de chat con un campo de texto y botón de enviar
- [ ] Given escribo una pregunta y presiono enviar When el endpoint responde Then veo la respuesta formateada en la burbuja del asistente
- [ ] Given la respuesta incluye datos numéricos (totales, porcentajes, cantidades) When se renderiza Then los números clave se destacan visualmente (bold, color)
- [ ] Given estoy esperando respuesta del servidor When el request está en vuelo Then se muestra indicador de "escribiendo..." (tres puntos animados)
- [ ] Given el servidor retorna error When el request falla Then se muestra mensaje de error amigable y puedo reintentar
- [ ] Given el chat tiene múltiples mensajes When hago scroll hacia arriba Then se muestra el historial completo de la conversación
- [ ] Given el panel de chat cuando la pantalla es pequeña (móvil) When se renderiza Then el chat ocupa pantalla completa como drawer o bottom sheet
- [ ] Given la respuesta del asistente When incluye suggestions Then se muestran chips con preguntas sugeridas para continuar la conversación

**Prioridad:** P2  
**Esfuerzo estimado:** 2.5 días  
**Dependencias:** HU-F3-006 (endpoint debe existir)  
**Ficha técnica de referencia:** Sección §5.3 del analysis  
**Notas técnicas:**
- Componentes: `AgentChat.tsx`, `ChatBubble.tsx`, `ChatInput.tsx`, `SuggestionChips.tsx`
- Hook: `useAgentQuery()` que consume `POST /api/agents/query`
- Estado de conversación en memoria (si no hay persistencia) o con `conversation_id`
- Opcional (P3): streaming con SSE y `EventSource`
- Responsive: panel lateral en desktop (>1024px), drawer en tablet/móvil
- Tests: renderizado de mensajes, estado de carga, manejo de errores

---

# Resumen de Dependencias entre Fases

```
Fase 1 (Fundamentos)
  HU-F1-001 business_type ──┬── HU-F1-002 feature_flags ── HU-F1-003 UI adaptativa
                             │
                             └── HU-F1-004 cashflow_proj ── HU-F1-005 cashflow_real ── HU-F1-006 comparativa
                                      │                         │
                                      └── HU-F1-008 persistencia  └── HU-F1-007 UI cashflow

Fase 2 (Comerciales)
  HU-F2-001 tablas_base ── HU-F2-002 especializacion
       │
       ├── HU-F2-003 sessions ── HU-F2-008 UI caja
       │
       ├── HU-F2-004 ventas ──┬── HU-F2-005 kardex_integration
       │                      ├── HU-F2-006 contable_integration
       │                      ├── HU-F2-007 ticket
       │                      ├── HU-F2-009 UI venta_base ── HU-F2-010 UI especializada
       │                      └── HU-F2-011 UI listado
       │
       └── HU-F2-012 kardex_persistente

Fase 3 (IA)
  HU-F3-001 SalesSkill ──┬── HU-F3-004 SkillLoader ── HU-F3-005 Orchestrator ── HU-F3-006 endpoint ── HU-F3-007 UI chat
  HU-F3-002 InventorySkill ──┤
  HU-F3-003 FinanceSkill ────┘
```

# Resumen por Fase

| Fase | Historias | Backend | Frontend | Esfuerzo Total |
|------|-----------|---------|----------|----------------|
| Fase 1 — Fundamentos | 8 | HU-F1-001, 002, 004, 005, 006, 008 | HU-F1-003, 007 | 7-9 días |
| Fase 2 — Comerciales | 12 | HU-F2-001, 002, 003, 004, 005, 006, 007, 012 | HU-F2-008, 009, 010, 011 | 12-15 días |
| Fase 3 — Agentes IA | 7 | HU-F3-001, 002, 003, 004, 005, 006 | HU-F3-007 | 9-11 días |
| **TOTAL** | **27** | **20 backend** | **7 frontend** | **28-35 días** |

---

*Documento generado automáticamente por PO Agent con base en el Architecture Analysis 2026-05-12.*
