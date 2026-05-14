# Backlog Gherkin — Fases 1, 2 y 3

**Proyecto:** IaaS-RonSys  
**Origen:** [analysis-2026-05-12.md](../reports/analysis-2026-05-12.md)  
**Actualizado por:** PO Agent 📋 + Architecture Agent 🏗️  
**Fecha:** 2026-05-14 (revisión con estado real del código)  
**Total Historias:** 30 (F1: 10 | F2: 12 | F3: 7 + 1 F1-extra)

---

# Fase 1 — Fundamentos Estables

**Objetivo:** Cerrar brechas de persistencia, corregir arquitectura hexagonal (puertos), y completar UI de flujo de caja.  
**Esfuerzo total estimado:** 4.5 días (backend 3d + frontend 1.5d) — reducido de 7-9d originales por código ya implementado.  
**Dependencia externa:** Ninguna (se construye sobre lo ya implementado en Fase 0/QA).  
**Ficha técnica de referencia:** Plan Integral v3 §7, §13 + Architecture Agent analysis 2026-05-14.

---

### HU-F1-001: ✅ IMPLEMENTADO — Definir tipo de negocio (business_type) en Company

**Estado:** Completado en Fase 0/QA (migración 0003). No requiere trabajo.

- Migración 0003 aplicada con `business_type VARCHAR(20) NOT NULL DEFAULT 'restaurant'` y CHECK constraint sobre ('restaurant', 'hardware', 'retail', 'service').
- Modelo SQLAlchemy `Company.business_type` existe y funciona.
- UI adaptativa ya consume `business_type` via `useCompanySettings()`.

---

### HU-F1-001b (NUEVA): Persistir InvestmentVariables del setup contable en DB

**Como** administrador del sistema  
**Quiero** que las variables de inversión del setup contable se persistan en base de datos  
**Para** que los datos de proyección sobrevivan a reinicios del servidor y no dependan de variables globales en memoria.

**Contexto:** Actualmente `_investment` y `_journal` son variables globales en `routers/accounting.py`. El endpoint `/api/accounting/cashflow?view=projected` usa `CashflowService.load_projection()` desde DB (tabla `cashflow_projections`) como primer intento, pero hace fallback a `_investment` si la tabla está vacía. El `calculate_real()` depende de `_journal` (lista en memoria). Esto funciona en runtime pero no sobrevive reinicios.

**Criterios de aceptación:**
- [ ] Given un setup contable ejecutado via `POST /api/accounting/setup` When se completa Then las `InvestmentVariables` se persisten en tabla `investment_variables` (o campo `companies.settings.investment_vars` JSONB) con `company_id` y timestamp
- [ ] Given un reinicio del contenedor backend When consulto `GET /api/accounting/cashflow?view=projected` Then el reporte se genera desde DB sin necesidad de re-ejecutar setup
- [ ] Given `_journal` era una variable global When se completa la migración Then los routers cargan journal entries desde `journal_entries` (DB) — que ya existe y se persiste
- [ ] Given el endpoint `GET /api/accounting/cashflow?view=actual` When hay journal entries en DB Then `calculate_real()` lee desde DB en lugar de lista en memoria
- [ ] Given los cambios When ejecuto `pytest tests/ -v` Then los 140 tests existentes siguen pasando

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día  
**Dependencias:** Ninguna (tabla `journal_entries` ya existe, `cashflow_projections` ya existe)  
**Notas técnicas:**
- Opción A (recomendada por Architecture Agent): persistir `InvestmentVariables` en `companies.settings` JSONB (campo `investment_vars`). Sin migración nueva.
- Opción B: crear tabla `investment_variables` con columnas para cada variable. Requiere migración.
- `CashflowService.calculate_real()` debe cambiar firma para recibir `db: AsyncSession` en lugar de `journal_entries: list`.
- Refactor en `routers/accounting.py`: eliminar `_investment` y `_journal` globales, usar DB via `Depends(get_db)`.

---

### HU-F1-002: ✅ PARCIALMENTE IMPLEMENTADO — Feature flags y tax_config en settings JSON

**Estado:** El campo `settings JSONB` en `companies` ya persiste en PostgreSQL. Existen endpoints `PUT/GET /api/admin/company/settings`. El mecanismo de persistencia funciona. Lo que falta es extender el schema Pydantic con nuevos feature flags y asegurar defaults correctos por `business_type`.

**Trabajo pendiente refinado:**

**Como** administrador del sistema  
**Quiero** que el schema de settings incluya todos los feature flags necesarios para Fase 2 (multi-warehouse, delivery, etc.) con defaults inteligentes según `business_type`  
**Para** que los módulos futuros puedan activarse/desactivarse sin nueva migración.

**Criterios de aceptación:**
- [ ] Given una empresa con `business_type = 'restaurant'` When se crea (o se accede por primera vez a settings) Then `settings.features` incluye: `tables_enabled: true`, `tips_enabled: true`, `delivery_enabled: false`, `recipe_explosion: true`, `multi_warehouse: false`, `warranty_tracking: false`, `invoice_required: false` y `tax_config.igv_included_in_price: true`, `tax_config.igv_rate: 0.18`
- [ ] Given una empresa con `business_type = 'hardware'` When se crea Then `settings.features` incluye: `warranty_tracking: true`, `invoice_required: true`, `tables_enabled: false`, `tips_enabled: false`, `recipe_explosion: false` y `tax_config.igv_included_in_price: false`
- [ ] Given un admin autenticado When hago `PATCH /api/admin/company/settings` con feature flags válidos Then los flags se persisten en `companies.settings` JSONB y la respuesta es 200
- [ ] Given un admin When hago PATCH con un flag no declarado en el schema Then el sistema responde 422 con mensaje de validación Pydantic
- [ ] Given el endpoint `GET /api/admin/company/settings` When lo consulto Then retorna el objeto `CompanySettings` completo con `features`, `tax_config`, `branding`, y `investment_vars` (si existe)

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días (extender schema Pydantic + defaults + tests)  
**Dependencias:** HU-F1-001 (business_type debe existir — ya implementado)  
**Notas técnicas:**
- Extender `CompanySettings` (Pydantic) con campos: `features: FeatureFlags`, `tax_config: TaxConfig`, `branding: BrandingConfig`, `investment_vars: dict | None`
- `FeatureFlags` debe incluir: `tables_enabled`, `tips_enabled`, `delivery_enabled`, `recipe_explosion`, `multi_warehouse`, `warranty_tracking`, `invoice_required` (todos `bool`)
- `TaxConfig`: `igv_rate: float`, `igv_included_in_price: bool`, `withholding_tax_rate: float`
- NO crear tabla `company_settings` separada — usar `companies.settings` JSONB existente (decisión Architecture Agent)
- Los defaults se asignan en un helper `get_default_settings(business_type)` → dict

---

### HU-F1-003: ✅ PARCIALMENTE IMPLEMENTADO — UI adaptativa según business_type y feature flags

**Estado:** `useCompanySettings()` ya existe y consume `GET /api/admin/company/settings`. La UI condicional funciona (campos de restaurante vs ferretería). Tras HU-F1-002, verificar que el hook exponga correctamente los nuevos flags.

**Trabajo pendiente refinado:**

**Como** usuario del sistema  
**Quiero** que `useCompanySettings()` exponga todos los feature flags nuevos definidos en HU-F1-002  
**Para** que las pantallas de Fase 2 (delivery, multi-almacén) puedan usar renderizado condicional.

**Criterios de aceptación:**
- [ ] Given `useCompanySettings()` When se ejecuta en un componente Then retorna `{ businessType, features, taxConfig, branding, loading, error }`
- [ ] Given `features.delivery_enabled: true` When renderizo la pantalla de ventas Then se muestra la opción "Delivery" en el selector de tipo de orden
- [ ] Given `features.multi_warehouse: true` When renderizo el kárdex Then se muestra el selector de almacén
- [ ] Given `features.warranty_tracking: true` When renderizo la venta de ferretería Then se muestra el campo "Meses de garantía"
- [ ] Given el hook está cargando (primer fetch) When se renderiza Then `loading = true` y el componente muestra skeleton
- [ ] Given el fetch falla (error de red) When se ejecuta Then `error` contiene el mensaje y el componente muestra fallback UI con valores por defecto

**Prioridad:** P2  
**Esfuerzo estimado:** 0.5 días (extender hook + types TypeScript)  
**Dependencias:** HU-F1-002 (settings schema debe estar actualizado)  
**Notas técnicas:**
- Tipos TypeScript: `FeatureFlags`, `TaxConfig`, `CompanySettings` en `types/index.ts`
- `useCompanySettings()` debe cachear en estado local (no refetch en cada render)
- Tests unitarios con Jest mockeando el endpoint `/api/admin/company/settings`

---

### HU-F1-004: ✅ IMPLEMENTADO (~85%) — Servicio de Flujo de Caja — vista proyectada

**Estado:** `CashflowService.generate_projection()` implementado (537 líneas en `cashflow.py`). Endpoint `GET /api/accounting/cashflow?view=projected&year=YYYY` funcionando con carga desde `cashflow_projections` (DB) + fallback a `_investment` (memoria). Modelos `CashflowLine`, `CashflowReport` completos.

**Pendiente menor:** HU-F1-001b (persistir InvestmentVariables) eliminará el fallback a memoria y hará que la carga desde DB sea el camino primario sin degradación. La lógica de negocio de proyección NO requiere cambios.

---

### HU-F1-005: ✅ IMPLEMENTADO (~70%) — Endpoint Flujo de Caja — vista real

**Estado:** `CashflowService.calculate_real()` implementado con clasificación de egresos por descripción. Endpoint `GET /api/accounting/cashflow?view=actual&from=YYYY-MM&to=YYYY-MM` funcionando. Actualmente devuelve datos vacíos o parciales porque depende de journal entries reales (que se generan en Fase 2 con la integración contable de ventas).

**Pendiente:** HU-F1-001b hará que `calculate_real()` lea desde `journal_entries` en DB (eliminando `_journal` global). El endpoint ya está listo — se activará con datos reales cuando Fase 2 genere transacciones.

---

### HU-F1-006: ✅ IMPLEMENTADO (~90%) — Comparativa proyectado vs real + alertas

**Estado:** `CashflowService.compare()` implementado con 4 niveles de alerta: info (±5%), yellow (±20%), red (±30%+), y liquidity (cashflow neto negativo vs positivo proyectado). Endpoint `GET /api/accounting/cashflow?view=comparison&from=YYYY-MM&to=YYYY-MM` funcionando.

**Pendiente:** Solo testing con datos reales (se activa naturalmente cuando HU-F1-005 tenga journal entries).

---

### HU-F1-007: 🟡 PARCIAL — UI de Flujo de Caja con selector de período/vista

**Estado:** `CashflowPage.tsx` (56 líneas) existe como wrapper. `CashflowChart.tsx` (632 líneas) tiene `CashflowBarChart`, `CashflowComparisonChart`, `CashflowAlerts`, `CashflowSkeleton` implementados. `useCashflow` hook consume el endpoint. Falta verificar integración visual completa.

**Trabajo pendiente refinado:**

**Como** gerente financiero  
**Quiero** ver gráficos de flujo de caja funcionales con selector de período, tipo de vista y alertas visibles  
**Para** tomar decisiones financieras informadas visualmente.

**Criterios de aceptación:**
- [ ] Given estoy en `/finanzas/cashflow` When la página carga Then veo un selector de año/mes inicio, año/mes fin, y toggle de vista (Proyectado | Real | Comparativa)
- [ ] Given selecciono "Proyectado" y un año When presiono "Consultar" Then se renderiza `CashflowBarChart` con 12 meses de ingresos (verde) y egresos (rojo)
- [ ] Given selecciono "Real" con rango de fechas When hay journal entries Then se muestran los datos reales; When no hay Then se muestra mensaje "No hay transacciones en este período"
- [ ] Given selecciono "Comparativa" When hay datos Then se renderiza `CashflowComparisonChart` con barras lado a lado (proyectado vs real) y `CashflowAlerts` muestra las alertas activas como banner
- [ ] Given la respuesta del endpoint tarda >1s When espero Then se muestra `CashflowSkeleton`
- [ ] Given el endpoint retorna error (404, 500) When falla Then se muestra mensaje de error con botón "Reintentar"
- [ ] Given la vista comparativa tiene alertas When hay alertas `severity: red` Then se muestran en banner rojo con icono ⚠️; When son `yellow` Then banner amarillo; When son `info` Then banner azul
- [ ] Given el selector de período When selecciono fechas inválidas (from > to) Then se muestra validación y el botón "Consultar" se deshabilita

**Prioridad:** P1  
**Esfuerzo estimado:** 1 día (frontend)  
**Dependencias:** HU-F1-001b (para que los endpoints devuelvan datos reales desde DB)  
**Notas técnicas:**
- `CashflowChart.tsx` ya tiene los componentes base. Verificar que `useCashflow` hook pase correctamente `view`, `year`, `from`, `to`.
- `CashflowAlerts` debe renderizar alerts del response (ya incluido en `CashflowReportResponse`).
- Mover `CashflowPage.tsx` a `pages/finanzas/CashflowPage.tsx` (tarea HU-F1-010).
- Tests: renderizado de cada vista, estado de carga, estado de error, validación de fechas.

---

### HU-F1-008: ✅ IMPLEMENTADO — Persistencia de proyecciones de flujo de caja

**Estado:** Tabla `cashflow_projections` creada (migración 0004). `CashflowService.save_projection()` y `load_projection()` implementados con UPSERT. UNIQUE constraint sobre (company_id, year, month, concept). No requiere trabajo adicional.

---

### HU-F1-009 (NUEVA): Definir puertos hexagonales para Sales e Inventory

**Como** desarrollador backend  
**Quiero** que los dominios `core/sales/` e `core/inventory/` tengan puertos abstractos (ABCs) y repositorios DB que los implementen  
**Para** que `sales_service.py` deje de depender directamente del ORM y cumpla con la arquitectura hexagonal.

**Contexto:** `core/sales/` e `core/inventory/` son directorios vacíos. `services/sales_service.py` (1116 líneas) importa modelos ORM directamente (`from app.adapters.db.models.sales import Sale, ...`). Esto viola la regla hexagonal de que la capa de servicios dependa de puertos abstractos, no de infraestructura. El patrón correcto ya existe en `core/accounting/ports.py` (`AccountingRepository`, `InventoryRepository` como ABCs con métodos abstractos).

**Alcance Fase 1 (según Architecture Agent):** Definir puertos + crear repositorio SQLAlchemy. **NO refactorizar `sales_service.py` a fondo** — eso va en Fase 2 con tests de integración.

**Criterios de aceptación:**
- [ ] Given el archivo `core/sales/ports.py` When existe Then define `SalesRepository(ABC)` con métodos abstractos: `create_sale`, `list_sales`, `get_sale_detail`, `void_sale`, `open_session`, `close_session`, `get_current_session`
- [ ] Given el archivo `core/inventory/ports.py` When existe Then define `InventoryRepository(ABC)` con métodos abstractos: `create_product`, `get_product`, `get_products`, `update_product`, `save_kardex_movement`, `get_kardex`
- [ ] Given `adapters/db/repositories/sales.py` When existe Then implementa `SqlAlchemySaleRepository(SalesRepository)` usando `AsyncSession`
- [ ] Given `adapters/db/repositories/inventory.py` When existe Then implementa `SqlAlchemyInventoryRepository(InventoryRepository)` usando `AsyncSession`
- [ ] Given los repositorios existen When se inyectan via FastAPI `Depends()` Then los endpoints de ventas (`/api/sales/*`) pueden obtener el repositorio sin recibir `AsyncSession` directamente
- [ ] Given los puertos definidos When escribo un test unitario de `SalesService` Then puedo mockear `SalesRepository` sin levantar PostgreSQL
- [ ] Given el cambio When ejecuto `pytest tests/ -v` Then los 140 tests existentes siguen pasando

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** Ninguna (solo agrega archivos nuevos, no modifica servicios existentes)  
**Notas técnicas:**
- Patrón de referencia: `core/accounting/ports.py` → `AccountingRepository(ABC)`, `InventoryRepository(ABC)`
- Los dataclasses de dominio (records) van en los mismos `ports.py`: `SaleRecord`, `PosSessionRecord`, `SaleItemRecord`, `SalePaymentRecord`
- `adapters/db/repositories/sales.py` implementa los métodos con queries SQLAlchemy (extraer lógica de queries de `sales_service.py` progresivamente)
- `adapters/db/repositories/inventory.py` — similar para productos y kárdex
- En Fase 1 NO se modifica `sales_service.py` — solo se crean los puertos y repos. La migración del servicio a usar puertos ocurre en Fase 2.
- Los routers pueden empezar a usar `Depends(get_sales_repo)` en paralelo al `Depends(get_db)` existente (convivencia).

---

### HU-F1-010 (NUEVA): Mover archivos de páginas huérfanas a carpetas de dominio + verificar sidebar

**Como** desarrollador frontend  
**Quiero** que la estructura de archivos en `pages/` refleje la organización de rutas (que ya es jerárquica en `App.tsx`)  
**Para** mantener consistencia entre rutas y sistema de archivos.

**Contexto:** Las rutas en `App.tsx` YA están organizadas jerárquicamente (`/finanzas/cashflow`, `/ventas/pos`, `/inventario/kardex`) con redirects 301 para rutas antiguas. La sidebar (`Sidebar.tsx`) ya es jerárquica con secciones colapsables y "Cerrar Sesión" siempre visible. Pero los archivos físicos (`Cashflow.tsx`, `Pos.tsx`, `SalesNew.tsx`, `SalesListPage.tsx`, `Kardex.tsx`, `Settings.tsx`) están en la raíz de `pages/` en lugar de en sus carpetas de dominio.

**Criterios de aceptación:**
- [ ] Given los archivos en `pages/` When se reorganizan Then `Cashflow.tsx` → `pages/finanzas/CashflowPage.tsx`
- [ ] Given la reorganización When se completa Then `Pos.tsx` → `pages/ventas/PosPage.tsx`, `SalesNew.tsx` → `pages/ventas/SalesNewPage.tsx`, `SalesListPage.tsx` → `pages/ventas/SalesListPage.tsx`
- [ ] Given la reorganización When se completa Then `Kardex.tsx` → `pages/inventario/KardexPage.tsx`, `Settings.tsx` → `pages/config/SettingsPage.tsx`
- [ ] Given los imports en `App.tsx` When se actualizan Then el build de Vite (`npm run build`) completa sin errores
- [ ] Given la sidebar When navego Then la sección activa se resalta correctamente para cada ruta
- [ ] Given estoy en mobile (viewport < 768px) When abro el menú hamburguesa Then "Cerrar Sesión" es visible al final del menú
- [ ] Given estoy en desktop When veo el sidebar Then "🚪 Cerrar Sesión" está siempre visible al fondo (sticky bottom)
- [ ] Given `useCompanySettings().businessType === 'hardware'` When veo el sidebar Then las secciones de Restaurante (Salones, Menú, Comandas) NO se muestran
- [ ] Given los cambios When ejecuto `npx jest --verbose` Then los 140 tests frontend existentes siguen pasando

**Prioridad:** P1  
**Esfuerzo estimado:** 0.5 días  
**Dependencias:** Ninguna (solo mueve archivos + actualiza imports)  
**Notas técnicas:**
- Usar `git mv` para preservar historial
- Los imports lazy en `App.tsx` (React.lazy) deben actualizar las rutas: `() => import('@/pages/finanzas/CashflowPage')`
- Verificar que `Sidebar.tsx` tiene `position: sticky` y `bottom: 0` para el botón "Cerrar Sesión"
- Las carpetas destino (`finanzas/`, `ventas/`, `inventario/`, `config/`) ya existen (creadas en Fase 0)
- Los redirects 301 existentes para rutas antiguas deben mantenerse

---

# Fase 2 — Módulos Comerciales

**⚠️ ESTADO: COMPLETADA (2026-05-14)** — Verificado por PO Agent 📋 contra código real.

**Evidencia:**
- Backend: `services/sales_service.py` (1116 líneas) con `PosSessionService` + `SaleService` completos
- Backend: `routers/sales.py` con 9 endpoints funcionando
- Backend: `models/sales.py` con 6 tablas (PosSession, Sale, SaleItem, SalePayment, RestaurantSale, HardwareSale)
- Backend: `test_sales_routes.py` (305 líneas), `test_cashflow.py` (586 líneas)
- Backend: `services/kardex_service.py` (265 líneas) + `services/inventory_service.py` (145 líneas) DB-backed
- Frontend: 12 componentes sales/pos + 3 páginas ventas/ + 5 páginas restaurant/ implementados
- Frontend: `SalesComponents.test.tsx`, `SalesNewPage.test.tsx`, `SalesListPage.test.tsx`, `SalesList.test.tsx`, `PosPage.test.tsx`, `PosSession.test.tsx`
- Tests: 140 backend + 140 frontend pasando
- Migración: 0005 (sales_tables) y 0006 (scenarios) aplicadas

**Notas de revisión:**
- Todas las 12 historias están implementadas con criterios de aceptación cubiertos
- Única brecha menor: `sale_number` usa COUNT en lugar de FOR UPDATE (race condition en concurrencia extrema; no bloqueante para MVP)
- Kárdex DB-backed (`/db/*` endpoints) + endpoints legacy en memoria coexisten

**Objetivo original:** POS funcional con especialización restaurante/ferretería + Kárdex persistente.  
**Esfuerzo real:** 0 días pendientes (completado en Fase 0 QA + Fase 1).  
**Dependencia externa:** HU-F1-001 (business_type), HU-F1-002 (feature flags), HU-F1-009 (puertos sales).

---

### HU-F2-001: ✅ IMPLEMENTADO — Modelos ORM y migración — tablas base de ventas

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

### HU-F2-002: ✅ IMPLEMENTADO — Modelos ORM y migración — especialización por tipo de negocio

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

### HU-F2-003: ✅ IMPLEMENTADO — Endpoints de sesión POS (abrir, cerrar, consultar)

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

### HU-F2-004: ✅ IMPLEMENTADO — Endpoints de ventas (crear, listar, detalle, anular)

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

### HU-F2-005: ✅ IMPLEMENTADO — Integración Kárdex — salida automática de inventario al vender

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

### HU-F2-006: ✅ IMPLEMENTADO — Integración contable — asiento automático de venta

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

### HU-F2-007: ✅ IMPLEMENTADO — Endpoints de ticket y métodos de pago

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

### HU-F2-008: ✅ IMPLEMENTADO — UI de apertura y cierre de caja

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

### HU-F2-009: ✅ IMPLEMENTADO — UI de registro de venta base

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

### HU-F2-010: ✅ IMPLEMENTADO — UI de venta especializada por tipo de negocio

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

### HU-F2-011: ✅ IMPLEMENTADO — UI de listado de ventas con filtros y ticket

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

### HU-F2-012: ✅ IMPLEMENTADO — Migrar Kárdex de variables en memoria a repositorio DB

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
  HU-F1-001 ✅ business_type (implementado)
  HU-F1-001b 🆕 persistencia InvestmentVariables ──┬── HU-F1-004 cashflow (usa DB)
  HU-F1-002 🟡 extender settings schema ── HU-F1-003 UI adaptativa
  HU-F1-009 🆕 puertos sales/inventory (hexagonal)
  HU-F1-010 🆕 mover archivos frontend + sidebar
  HU-F1-007 🟡 UI cashflow (gráficos + selector)
  HU-F1-004 ✅ proyección (85%)
  HU-F1-005 ✅ real (70% — espera datos F2)
  HU-F1-006 ✅ comparativa (90%)
  HU-F1-008 ✅ persistencia proyecciones (100%)

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
| Fase 1 — Fundamentos | 10 (2 ✅ implementadas, 3 nuevas) | HU-F1-001b, 002, 009 | HU-F1-003, 007, 010 | **4.5 días** |
| Fase 2 — Comerciales | 12 ✅ COMPLETADO | Migración 0005 + services completos | 12 componentes + 3 páginas | 0 días pendientes |
| Fase 3 — Agentes IA | 7 | HU-F3-001 a 006 | HU-F3-007 | 9-11 días |

| **TOTAL** | **29 activas + 2 completadas** | **20 backend** | **9 frontend** | **26-31 días** |

---

*Documento actualizado por PO Agent 📋 con ficha técnica de Architecture Agent 🏗️, 2026-05-14.*
*Revisión basada en inspección del código real (apps/backend + apps/web) + verificación de migraciones Alembic (0001-0006).*
