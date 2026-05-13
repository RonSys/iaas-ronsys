# Reporte de Validación QA — Fase 2

> **Documento:** Cruce de Historias Gherkin vs Resultados Reales de Implementación.
> **Proyecto:** IaaS-RonSys
> **Fecha:** 2026-05-12
> **Pipeline ejecutado:** Backend + Frontend (paralelo) → QA (2 ciclos) → DevOps (deploy + fix)

---

## 📋 Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| HU planificadas (Fase 2) | **12 HU** (8 Backend + 4 Frontend) |
| HU implementadas | **12/12** ✅ |
| Tests backend | **128/128** ✅ |
| Tests frontend | **128/128** (19 suites) ✅ |
| TypeScript check | **0 errores** ✅ |
| Vite build | ✅ |
| Issues encontrados por QA | **5** (🔴 2 críticos, 🟡 3 medios) |
| Issues corregidos | **5/5** ✅ |
| Contenedores en producción | **5/5 healthy** ✅ |
| Veredicto final | **🟢 APROBADO** |

---

## 🗺️ Mapeo HU vs Resultados

### HU-F2-001: Tablas base POS/Sales (migración)

| Criterio Gherkin (Given/When/Then) | Resultado | Estado |
|---|---|---|
| Given migración `0005_sales_tables` When se ejecuta Then crea tablas: `pos_sessions`, `sales`, `sale_items`, `sale_payments` | ✅ Migración 0005 creada con 7 tablas (4 base + 3 especialización) | ✅ |
| Given migración aplicada When verifico Then todas las tablas tienen `primary_key=True` | ✅ Corregido en DEV-01 (todas las columnas id con primary_key) | ✅ |
| Given migración aplicada When verifico Then constraints y foreign keys creadas | ✅ FK a companies, users, products, journal_entries | ✅ |

**Archivos generados:**
- `apps/backend/migrations/versions/0005_sales_tables.py`
- `apps/backend/app/adapters/db/models/sales.py`

**Issues relacionados:**
| Issue | Descripción | Fix |
|-------|------------|-----|
| DEV-01 🔴 | `primary_key=True` faltante en 6 tablas | Añadido en todas las columnas `id` |

---

### HU-F2-002: Especialización (Restaurant + Hardware)

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given migración When aplica Then crea `restaurant_sales` y `hardware_sales` con FK a `sales` | ✅ Tablas creadas con FK y UNIQUE constraint | ✅ |
| Given RestaurantSale When guardo Then campos: mesa, comensales, tipo orden, mesero, propina, notas cocina | ✅ Modelo con todos los campos | ✅ |
| Given HardwareSale When guardo Then campos: tipo comprobante, RUC, garantía, dirección despacho, instalación | ✅ Modelo con todos los campos | ✅ |

**Archivos generados:**
- Migración 0005 (tablas `restaurant_sales`, `hardware_sales`)
- `models/sales.py` (clases `RestaurantSale`, `HardwareSale`)

**Issues relacionados:**
| Issue | Descripción | Fix |
|-------|------------|-----|
| QA-F2-02 🔴 | Key `"restaurant"` vs `"restaurant_data"` — ambos aceptados ahora | Fallback: `data.get("restaurant_data") or data.get("restaurant")` |
| QA-F2-04 🟡 | `table_number` como INTEGER, no VARCHAR(10) | Migración + modelo + schema corregidos |

---

### HU-F2-003: Sesiones POS (open/close/current)

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given POST `/api/sales/sessions/open` When sin sesión abierta Then 200 + sesión creada | ✅ Sesión creada con opening_cash y user_id | ✅ |
| Given POST `/api/sales/sessions/open` When ya hay sesión abierta Then 409 | ✅ `HTTPException(409, "Ya existe una sesión POS abierta")` | ✅ |
| Given GET `/api/sales/sessions/current` When hay sesión abierta Then 200 con datos | ✅ Retorna sesión + ventas del turno + totales por método pago | ✅ |
| Given POST `/api/sales/sessions/close` When sesión abierta Then cierre con arqueo | ✅ Calcula expected_cash = opening + efectivo, compara con closing_cash | ✅ |
| Given POST `/api/sales/sessions/close` When ya cerrada Then 409 | ✅ Validación de estado | ✅ |

**Archivos generados:**
- `apps/backend/app/services/sales_service.py` (PosSessionService)
- `apps/backend/app/routers/sales.py`
- `apps/web/src/pages/Pos.tsx`
- `apps/web/src/components/pos/PosSessionOpen.tsx`
- `apps/web/src/components/pos/PosSessionStatus.tsx`
- `apps/web/src/components/pos/PosSessionClose.tsx`
- `apps/web/src/hooks/usePosSession.ts`
- `apps/web/src/__tests__/PosSession.test.tsx`

**Issues relacionados:** Ninguno.

---

### HU-F2-004: Ventas CRUD (create/list/detail/void)

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given POST `/api/sales/sale` When items + payments válidos Then 200 + venta creada | ✅ Venta creada con validación de items, payments y stock | ✅ |
| Given POST `/api/sales/sale` When payments no cubren total Then 422 | ✅ `raise HTTPException(422, "Payments don't cover total")` | ✅ |
| Given GET `/api/sales/sales` When filtros Then lista paginada | ✅ Listado con filtros por fecha, tipo, método pago | ✅ |
| Given GET `/api/sales/sale/{id}` When existe Then detalle completo | ✅ Detalle con items + payments + datos especialización | ✅ |
| Given POST `/api/sales/sale/{id}/void` When existe Then anulación | ✅ Venta marcada como is_voided + void_reason + voided_at | ✅ |
| Given POST `/api/sales/sale/{id}/void` When no existe Then 404 | ✅ Validación de existencia | ✅ |

**Archivos generados:**
- `apps/backend/app/services/sales_service.py` (SaleService)
- `apps/backend/app/routers/sales.py`
- `apps/backend/tests/test_sales_routes.py` (26 tests)
- `apps/web/src/pages/SalesNew.tsx`
- `apps/web/src/pages/SalesListPage.tsx`
- `apps/web/src/hooks/useSales.ts`

**Issues relacionados:**
| Issue | Descripción | Fix |
|-------|------------|-----|
| QA-F2-02b 🔴 | `GET /api/sales/sale/{id}` no serializaba `restaurant_data` | Fallback query directa a `restaurant_sales` / `hardware_sales` |
| — | `UnboundLocalError` en `void_sale` | `HTTPException` movido antes del primer uso |

---

### HU-F2-005: Integración Kárdex (salida automática)

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given venta con productos de inventario When se crea Then salida automática de kárdex | ✅ `kardex_engine.record_exit()` llamado en creación de venta | ✅ |
| Given venta creada When verífico Then kardex_movement_id en sale_item | ✅ FK a kardex_movements | ✅ |
| Given stock insuficiente When se intenta vender Then error | ✅ Validación de stock antes de crear | ✅ |

**Archivos generados:**
- `apps/backend/app/services/sales_service.py` (kárdex integration en create_sale)
- `apps/backend/app/core/accounting/kardex.py` (record_exit)

**Issues relacionados:** Ninguno.

---

### HU-F2-006: Asiento contable automático

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given venta creada When se procesa Then asiento contable generado con: Caja/10, Ventas/40, IGV/201, Costo/50, Inventarios/12 | ✅ Asiento de partida doble generado automáticamente | ✅ |
| Given venta restaurante When procesa Then asiento incluye propina | ✅ Asiento separado para propina (cuenta 24) | ✅ |
| Given venta anulada When proceso Then asiento de reversión | ✅ void_sale genera asiento inverso | ✅ |

**Archivos generados:**
- `apps/backend/app/services/sales_service.py` (generación de journal_entry)
- `apps/backend/app/routers/sales.py` (void → reversión)

**Issues relacionados:** Ninguno.

---

### HU-F2-007: Ticket + payment methods

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given GET `/api/sales/sale/{id}/ticket` When existe Then ticket formateado (JSON + texto) | ✅ Ticket con: encabezado, items, subtotal, IGV, propina, total, pagos | ✅ |
| Given GET `/api/sales/payment-methods` When consulto Then lista métodos habilitados | ✅ 5 métodos: cash, card, yape, plin, transfer | ✅ |
| Given GET `/api/sales/payment-methods` When business_type=restaurant Then métodos filtrados según features | ✅ Feature flags aplicados | ✅ |

**Archivos generados:**
- `apps/backend/app/services/sales_service.py` (TicketService)
- `apps/backend/tests/test_sales_routes.py` (4 tests ticket/payments)

**Issues relacionados:** Ninguno.

---

### HU-F2-008: UI Caja (Pos.tsx)

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given estoy en Caja When no hay sesión abierta Then botón "Abrir Turno" visible | ✅ PosSessionOpen.tsx renderizado condicional | ✅ |
| Given abro turno When ingreso monto apertura Then sesión creada + estado visible | ✅ Hook usePosSession con POST /api/sales/sessions/open | ✅ |
| Given sesión activa When cierro Then modal de arqueo con: opening, ventas efectivo, expected, closing, difference | ✅ PosSessionClose.tsx con cuadre de caja | ✅ |

**Archivos generados:**
- `apps/web/src/pages/Pos.tsx`
- `apps/web/src/components/pos/PosSessionOpen.tsx`
- `apps/web/src/components/pos/PosSessionClose.tsx`
- `apps/web/src/components/pos/PosSessionStatus.tsx`
- `apps/web/src/hooks/usePosSession.ts`
- `apps/web/src/__tests__/PosSession.test.tsx`
- `apps/web/src/__tests__/PosPage.test.tsx` (+3 tests)

**Issues relacionados:** Ninguno.

---

### HU-F2-009: UI Venta base

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given formulario de venta When cargo Then buscador de productos, cantidades, precios | ✅ SalesNew.tsx con ProductSearch y SaleItemsList | ✅ |
| Given agrego productos When selecciono Then items en lista con cálculo automático de totales | ✅ Cálculo automático de subtotal, IGV, total | ✅ |
| Given sección de pagos When selecciono método Then soporta cash, card, yape, plin, transfer | ✅ PaymentSection.tsx con 5 métodos | ✅ |

**Archivos generados:**
- `apps/web/src/pages/SalesNew.tsx`
- `apps/web/src/components/sales/ProductSearch.tsx`
- `apps/web/src/components/sales/SaleItemsList.tsx`
- `apps/web/src/components/sales/PaymentSection.tsx`
- `apps/web/src/hooks/useSales.ts`
- `apps/web/src/__tests__/SalesNewPage.test.tsx` (+5 tests)
- `apps/web/src/__tests__/SalesComponents.test.tsx`

**Issues relacionados:** Ninguno.

---

### HU-F2-010: UI Venta especializada

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given business_type=restaurant When registro venta Then campos: mesa, comensales, tipo orden, mesero, propina, notas cocina | ✅ RestaurantSaleFields.tsx con todos los campos | ✅ |
| Given business_type=hardware When registro venta Then campos: boleta/factura, RUC, garantía, dirección despacho | ✅ HardwareSaleFields.tsx con todos los campos | ✅ |
| Given `features.tips_enabled=false` When cargo venta Then campo propina oculto | ✅ Renderizado condicional por feature flags | ✅ |
| Given `features.warranty_tracking=false` When cargo venta Then campo garantía oculto | ✅ Renderizado condicional | ✅ |

**Archivos generados:**
- `apps/web/src/components/sales/RestaurantSaleFields.tsx`
- `apps/web/src/components/sales/HardwareSaleFields.tsx`
- `apps/web/src/types/sales.ts`

**Issues relacionados:**
| Issue | Descripción | Fix |
|-------|------------|-----|
| QA-F2-01 🔴 | `igv_included_in_price` no se procesaba en cálculo de items | Lógica de descomposición IGV agregada en ambos loops de procesamiento |

---

### HU-F2-011: UI Listado de ventas

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given listado de ventas When cargo Then tabla con: #venta, fecha, cliente, total, método pago, estado | ✅ SalesListPage.tsx con tabla completa | ✅ |
| Given filtros disponibles When selecciono Then filtra por fecha, tipo, método pago | ✅ Filtros: fecha desde/hasta, business_type, payment_method | ✅ |
| Given botón detalle When click Then modal/página con info completa | ✅ SaleDetail.tsx con detalle | ✅ |
| Given botón anular When confirmo Then venta anulada + refresca lista | ✅ void_sale con confirmación | ✅ |

**Archivos generados:**
- `apps/web/src/pages/SalesListPage.tsx`
- `apps/web/src/components/sales/SaleFilters.tsx`
- `apps/web/src/components/sales/SaleDetail.tsx`
- `apps/web/src/components/sales/SalesList.tsx`
- `apps/web/src/__tests__/SalesListPage.test.tsx` (+5 tests)
- `apps/web/src/__tests__/SalesList.test.tsx`

**Issues relacionados:** Ninguno.

---

### HU-F2-012: Kárdex persistente en DB

| Criterio Gherkin | Resultado | Estado |
|---|---|---|
| Given kárdex en memoria When migro a DB Then KardexDBService creado con repositorio SQLAlchemy | ✅ `kardex_service.py` creado con métodos DB-backed | ✅ |
| Given productos registrados When consulto kárdex DB Then historial completo | ✅ 6 endpoints DB-backed bajo `/kardex/db/*` | ✅ |
| Given movimientos de entrada/salida When registro Then persistencia en DB asegurada | ✅ Operaciones DB-backed con transacciones | ✅ |

**Archivos generados:**
- `apps/backend/app/services/kardex_service.py` (KardexDBService)
- `apps/backend/app/routers/accounting.py` (+6 endpoints kárdex DB)
- `apps/backend/tests/test_sales_routes.py` (test auth endpoints)

**Issues relacionados:** Ninguno.

---

## 🔍 Ciclo de QA (Re-Test Loop)

### Ciclo 1: QA inicial (sobre código ya escrito)

```
Backend 🐍 + Frontend ⚛️ (paralelo)
  │ Ya existía ~70% del código de Fase 2 de ejecuciones previas
  │
  ├── Backend:  kárdex persistente + tests HTTP sales (26 tests)  
  ├── Frontend: PosPage, SalesNewPage, SalesListPage + tests
  │
  ▼
🧪 QA — 1er ciclo
  │
  ├── pytest backend     → 128/128 ✅
  ├── npx jest           → 128/128 (19 suites) ✅
  ├── npx tsc --noEmit   → 0 errors ✅
  ├── npx vite build     → ✅
  │
  └── Encuentra ISSUES ──────────→ Backend/Frontend corrigen
        │                                │
        ├── QA-F2-01 🔴 ·················│····→ igv_included fix + subtotal base
        ├── QA-F2-02 🔴 ·················│····→ key "restaurant" vs "restaurant_data"
        ├── QA-F2-03 🟡 ·················│····→ delivery_enabled default verificado
        ├── QA-F2-04 🟡 ·················│····→ table_number INTEGER→VARCHAR(10)
        └── QA-F2-02b 🔴 ················│····→ serialización restaurant_data en GET
                                         │
                                         ▼
                                  QA re-testa
                                  │ 128 + 128 → 256 tests ✅
                                  │
                                  ▼
                            🟢 APROBADO → DevOps

🚀 DevOps — despliegue en producción
  │
  ├── Build + levanta backend prod → :8000
  ├── Frontend prod → :80
  ├── Migraciones OK → 0005
  ├── Seed data
  │
  ├── Verifica QA-F2-02b → restaurant_data visible en JSON ✅
  │
  └── Reporte final a QA + Jarvis con URLs

🧪 QA (smoke test post-deploy)
  │
  ├── Confirma restaurant_data en JSON: ✅ {table_number: "M5", guests: 2, ...}
  │
  └── 0 bugs pendientes. Fase 2 cerrada. ✅
```

---

## 📊 Tabla Final: HU vs Estado

| HU | Descripción | Tests (BE) | Tests (FE) | QA Issues | Veredicto |
|:--:|-------------|:----------:|:----------:|:---------:|:---------:|
| F2-001 | Tablas base POS/Sales | migración | — | DEV-01 🔴 | ✅ |
| F2-002 | Especialización (Rest/Hard) | migración | — | QA-F2-02, QA-F2-04 | ✅ |
| F2-003 | Sesiones POS | 5 HTTP | PosPage (3) | — | ✅ |
| F2-004 | Ventas CRUD | 9 HTTP | SalesNew (5) + SalesList (5) | QA-F2-02b | ✅ |
| F2-005 | Integración Kárdex | integrado en create_sale | — | — | ✅ |
| F2-006 | Asiento contable auto | integrado en create_sale | — | — | ✅ |
| F2-007 | Ticket + payments | 4 HTTP | — | — | ✅ |
| F2-008 | UI Caja | — | 3 tests | — | ✅ |
| F2-009 | UI Venta base | — | 5 tests | — | ✅ |
| F2-010 | UI Especializada | — | SalesComponents | QA-F2-01 🔴 | ✅ |
| F2-011 | UI Listado | — | 5 tests | — | ✅ |
| F2-012 | Kárdex persistente | auth tests + endpoints | — | — | ✅ |

```
Total: 12/12 HU ✅ implementadas y validadas
       256 tests (128 BE + 128 FE) ✅
       5 issues QA corregidos ✅
       1 issue DevOps corregido ✅
       5 contenedores healthy en producción ✅
```

---

## 🧠 Lecciones Aprendidas (Fase 2)

1. **IGV incluido vs desglosado** — La lógica de `igv_included_in_price` requiere descomponer el subtotal en base imponible + IGV. Fácil de olvidar en el cálculo de items.
2. **Claves anidadas en POST** — El body de venta acepta tanto `"restaurant"` como `"restaurant_data"`. Mejor estandarizar desde el principio.
3. **selectinload** — Las relaciones de especialización en SQLAlchemy no siempre se cargan con `selectinload`. Tener fallback query directa por si acaso.
4. **Migraciones con errores de schema** — `primary_key=True` y tipos de columna (INTEGER vs VARCHAR) deben verificarse con un `alembic check` antes del deploy.

---

*Generado por Jarvis basado en la ejecución real del pipeline de Fase 2.*
*Cruce: Gherkin HU (docs/backlog/gherkin-fase1-3.md §Fase2) vs resultados de Backend, Frontend, QA y DevOps.*
