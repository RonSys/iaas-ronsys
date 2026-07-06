# 🏗️ Evaluación Arquitectónica: DT-F0-009 — Módulo Ferretería

**Fecha:** 2026-05-16  
**Agente:** Architecture Agent 🏗️  
**Rama objetivo:** `fase0-real` (commit `96b4494`)  
**Solicitado por:** Jarvis  
**Documentos de entrada:**
- `docs/backlog/gherkin-f0-009-ferreteria.md` — 7 historias Gherkin
- `docs/backlog/deuda-tecnica-fase0.md` — § DT-F0-009
- `docs/backlog/gherkin-fase0-erp.md` — Historias HU-F0-010 a HU-F0-013
- `docs/reports/informe-transicion-fase0-fase1.md`
- Código real en `fase0-real` (inspeccionado: modelos, servicios, routers, migraciones, frontend)

---

## 🩺 Veredicto Final

# ⚠️ PROCEDE CON PRECAUCIÓN — Se requieren 2 prerequisites y 1 migración antes de empezar

**Resumen:** 3 de las 7 historias Gherkin (01, 02, 03) pueden comenzar inmediatamente. Las otras 4 (04, 05, 06, 07) dependen de infraestructura que **no existe** en la rama actual. El orden de dependencias asumido en las Gherkin es mayormente correcto, pero omite una dependencia oculta crítica: **HU-F0-011 (`product_units` + `has_serial`) nunca se implementó.**

---

## 1. Hallazgo Crítico: HU-F0-011 NO IMPLEMENTADA

### Evidencia

| Componente | Estado Esperado (Gherkin) | Estado Real (código) |
|---|---|---|
| Tabla `product_units` | ✅ Existente (desde HU-F0-011) | ❌ **NO EXISTE** — 0 referencias en modelos, 0 en migraciones |
| Columna `products.has_serial` | ✅ Existente | ❌ **NO EXISTE** — Product model no la tiene |
| Columna `products.warranty_months` | ✅ Existente | ❌ **NO EXISTE** — Solo en `HardwareSale`, no en `Product` |
| Columna `products.manufacturer` | ✅ Existente | ❌ **NO EXISTE** |
| Migración `0011_product_units_serials` | ✅ Aplicada | ❌ **NO EXISTE** — Las migraciones llegan hasta `0008` |

### Impacto

Las historias **HU-F0-009-04, 05, 06, 07** (4 de 7 = 57% del esfuerzo) dependen directa o indirectamente de `product_units` y `has_serial`. No pueden iniciarse sin esta base.

### Acción requerida (pre-requisito #1)

Implementar **HU-F0-011** como prerequisite inmediato antes de las historias 04-07. Esto incluye:
- Migración `0009_product_units_and_serials` con tabla `product_units` + columnas `has_serial`, `warranty_months`, `manufacturer` en `products`
- Modelo SQLAlchemy `ProductUnit`
- Schemas Pydantic: `SerialCreate`, `SerialBatchCreate`, `SerialResponse`

---

## 2. Hallazgo: HU-F0-010 Parcialmente Implementada

### Estado real

| Columna en Product | ¿Existe? | Nota |
|---|---|---|
| `retail_price` | ✅ | Migración 0008 |
| `wholesale_price` | ✅ | Migración 0008 |
| `wholesale_min_qty` | ✅ | Migración 0008 |
| `barcode` | ✅ | Migración 0008 |
| `warranty_months` | ❌ | **Falta** — solo en `hardware_sales`, no en `products` |
| `manufacturer` | ❌ | **Falta** |
| `has_serial` | ❌ | **Falta** |

### Lógica de pricing mayorista/detal

**NO implementada.** El `SalesService.create_sale()` no referencia `wholesale_price` ni `retail_price`. El `unit_price` se recibe del frontend sin validación de pricing automático. Esto es un **gap funcional** que HU-F0-009-03 debe resolver.

### Acción requerida (pre-requisito #2)

Extender HU-F0-010 con las columnas faltantes (`warranty_months`, `manufacturer`, `has_serial`) en la misma migración que crea `product_units`. Esto unifica el prerequisite en una sola migración `0009`.

---

## 3. Análisis de Riesgo por Historia

### HU-F0-009-01: Categorías — CRUD, jerarquía y contador
**Riesgo:** 🟢 **BAJO**

**Lo que ya existe:**
- ✅ Modelo `ProductCategory` completo (con `parent_id`, `sort_order`, `active`, `description`)
- ✅ `InventoryCategoriesService` con create/list/update/delete
- ✅ `CategoriesPage.tsx` con CRUD básico
- ✅ El endpoint `list_categories` ya incluye `product_count` via `COUNT(p.id)`

**Lo que falta (gaps vs Gherkin):**
- ❌ `GET /api/v1/inventory/categories?tree=true` — endpoint jerárquico
- ❌ Validación 409 al eliminar categoría con productos activos — actualmente usa `func.count(Product.id)` sin filtrar `active=true`
- ❌ `PATCH` no soporta `description`, `parent_id`, `sort_order`, `active` — solo `name`
- ❌ Frontend: vista de árbol colapsable, badge de `product_count`, dropdown de categoría padre
- ❌ Validación anti-ciclos en `parent_id`
- ❌ `active=false` → filtrar en selects y conteos

**Riesgo Fase 1:** Mínimo. Las categorías son datos maestros simples. Fase 1 refactoriza `routers/inventory.py` pero los endpoints mantienen el mismo contrato.

---

### HU-F0-009-02: Productos — Página CRUD dedicada
**Riesgo:** 🟡 **MEDIO**

**Lo que ya existe:**
- ✅ Modelo `Product` con `category_id`, precios, barcode
- ✅ `GET /api/v1/inventory/products` con filtros (search, category, active)
- ✅ `ProductResponse` schema en `inventory.py`

**Lo que falta (gaps vs Gherkin):**
- ❌ No existe `POST /api/v1/inventory/products` — creación de productos
- ❌ No existe `PATCH /api/v1/inventory/products/{id}` — edición
- ❌ No existe `DELETE /api/v1/inventory/products/{id}` — soft-delete
- ❌ No existe `ProductsPage.tsx` — página CRUD completa
- ❌ No existe `ProductFormModal.tsx` con campos: categoría (dropdown), unidad, precios, has_serial toggle, meses de garantía, fabricante, stock inicial
- ❌ Los campos `has_serial`, `warranty_months`, `manufacturer` no están en el modelo
- ❌ Servidor-side sorting y búsqueda con query params `?search=&sort_by=&order=`
- ❌ Indicador de seriales en tabla (`serial_count`)

**Riesgo Fase 1:** Medio. Fase 1 refactorizará `routers/inventory.py` hacia puertos abstractos. Si el CRUD de productos se implementa con SQL crudo en el router (como hace el actual `list_products`), la refactorización de Fase 1 requerirá reescribir esas queries. **Recomendación:** implementar con `InventoryProductsService` separado usando SQLAlchemy async (no raw SQL), facilitando la migración a puertos en Fase 1.

---

### HU-F0-009-03: Precios mayorista/detal — flujo operativo
**Riesgo:** 🟡 **MEDIO**

**Lo que ya existe:**
- ✅ Columnas `retail_price`, `wholesale_price`, `wholesale_min_qty` en Product
- ✅ `SalesService.create_sale()` con flujo de venta completo
- ✅ Frontend POS (`SalesNew.tsx`) funcional

**Lo que falta:**
- ❌ **Lógica de auto-aplicación de precio** en backend: `SalesService.create_sale()` no evalúa `wholesale_price` vs `retail_price`. El precio se recibe del frontend.
- ❌ Validación soft `wholesale_price > retail_price` → warning
- ❌ Comprobante que muestre precio unitario efectivo (mayorista vs minorista)
- ❌ `GET /api/v1/inventory/products?barcode=xxx` — búsqueda por código de barras (el endpoint actual no tiene filtro `barcode`)

**Riesgo Fase 1:** Medio. `SalesService.create_sale()` es uno de los archivos más modificados en Fase 1 (puertos abstractos). La lógica de pricing debería encapsularse en un helper o método separado (`_apply_wholesale_pricing`) para facilitar el refactoring.

---

### HU-F0-009-04: Seriales — registro, stock y CRUD
**Riesgo:** 🔴 **ALTO — Bloqueado por falta de prerequisite**

**Depende de:** `product_units` (no existe) + `has_serial` (no existe) + `warranty_months` (no existe en Product)

**Lo que falta (todo):**
- ❌ Tabla `product_units` con: id, product_id, serial_number, status, purchase_date, cost_price, warranty_expiry, sale_id, sale_item_id, notes
- ❌ Columna `has_serial` en products
- ❌ `POST /api/v1/inventory/products/{id}/serials` — registrar serial
- ❌ `POST /api/v1/inventory/products/{id}/serials/batch` — registro masivo
- ❌ `GET /api/v1/inventory/products/{id}/serials` — listar seriales con filtro `?status=`
- ❌ `warranty_expiry = purchase_date + relativedelta(months=warranty_months)`
- ❌ Frontend: `SerialPanel.tsx`, `SerialTable.tsx`, `SerialBatchForm.tsx`

**Riesgo Fase 1:** Alto. Si se implementa con SQL crudo en el router, Fase 1 tendrá que reescribir todo. **Recomendación:** crear `SerialService` con puerto abstracto desde el día 1.

---

### HU-F0-009-05: Seriales en venta — modal selector
**Riesgo:** 🔴 **ALTO — Bloqueado por HU-F0-009-04**

**Riesgo adicional:** La Gherkin menciona "reserva temporal" vs "validación al confirmar". La decisión técnica debe ser explícita: para Fase 0, **validación al confirmar** (sin locks largos). Si dos cajeros venden el mismo serial simultáneamente, el segundo recibe error 409. Esto es aceptable para el MVP pero debe documentarse.

**Lo que falta:**
- ❌ Extensión de `SaleItemCreate` schema con `serials: list[str] | None`
- ❌ Validación en `SalesService.create_sale()`: si `product.has_serial`, `len(serials) == quantity`
- ❌ Validación de que cada serial existe, está 'available' y pertenece al producto
- ❌ `UPDATE product_units SET status='sold', sale_id=X, sale_item_id=Y WHERE serial_number IN (...)`
- ❌ Frontend: `SerialSelectorModal.tsx` integrado en flujo POS

**Riesgo Fase 1:** Alto (mismo motivo — `SalesService` se refactoriza en Fase 1). Encapsular lógica de seriales en helper separado.

---

### HU-F0-009-06: Seriales — anulación, trazabilidad y garantía
**Riesgo:** 🔴 **ALTO — Bloqueado por HU-F0-009-05**

**Riesgo adicional de integridad:** La anulación parcial (solo 1 item de una venta con 3 items, donde ese item tiene seriales) requiere:
1. Revertir seriales de ese item específico (no todos los de la venta)
2. Revertir kárdex solo para ese item
3. El contra-asiento debe reflejar la anulación parcial

El `SalesService.void_sale()` actual no soporta anulación parcial — anula toda la venta. Si se requiere anulación parcial, se necesita un nuevo endpoint `POST /api/sales/sale/{id}/items/{item_id}/void`.

**Lo que falta:**
- ❌ Extensión de `void_sale()` para devolver seriales a 'available'
- ❌ `GET /api/v1/inventory/serials/{serial_number}/traceability` — endpoint de trazabilidad
- ❌ JOIN `product_units` → `sale_items` → `sales` en `get_sale_detail()`
- ❌ Alerta de garantía por vencer (< 30 días)
- ❌ Frontend: `SerialTraceabilityPanel.tsx` con timeline

---

### HU-F0-009-07: Productos sin serial — coexistencia
**Riesgo:** 🟡 **MEDIO — Depende de 04, 05, 06**

Esta historia es en gran parte **validación de integridad** de lo construido en 04-06. No agrega nuevos endpoints o modelos, sino que verifica que:
- Productos con/sin serial coexistan en la misma venta, reportes y kárdex
- Las transiciones `has_serial` false↔true estén validadas
- El cálculo de valor de inventario sea correcto para ambos tipos

**Riesgo Fase 1:** Bajo — es mayormente tests y validaciones.

---

## 4. Endpoints — Evaluación de Soporte Actual

| Endpoint requerido por Gherkin | ¿Soportado? | Router actual | Nota |
|---|---|---|---|
| `POST /api/inventory/categories` | ✅ | `inventory.py` → `/api/v1/inventory/categories` | Solo acepta `name`, no `description`, `parent_id` |
| `GET /api/inventory/categories` | ✅ | `inventory.py` | Ya incluye `product_count` |
| `GET /api/inventory/categories?tree=true` | ❌ | — | Requiere implementar armado de árbol |
| `PATCH /api/inventory/categories/{id}` | ⚠️ | `inventory.py` | Solo actualiza `name`, falta description, sort_order, parent_id |
| `DELETE /api/inventory/categories/{id}` | ⚠️ | `inventory.py` | No filtra `active=true` en conteo de productos |
| `GET /api/inventory/products` | ✅ | `inventory.py` → `/api/v1/inventory/products` | Con search, category_id, active. Falta sort, barcode |
| `POST /api/inventory/products` | ❌ | — | **No existe** |
| `PATCH /api/inventory/products/{id}` | ❌ | — | **No existe** |
| `DELETE /api/inventory/products/{id}` | ❌ | — | **No existe** |
| `POST /api/sales/sale` | ✅ | `sales.py` | Sin lógica de seriales ni wholesale pricing |
| `POST /api/sales/sale/{id}/void` | ✅ | `sales.py` | Sin reversión de seriales |
| `GET /api/sales/sale/{id}` | ✅ | `sales.py` | Sin seriales en items |
| `POST /api/inventory/products/{id}/serials` | ❌ | — | **Requiere product_units** |
| `POST /api/inventory/products/{id}/serials/batch` | ❌ | — | **Requiere product_units** |
| `GET /api/inventory/products/{id}/serials` | ❌ | — | **Requiere product_units** |
| `GET /api/inventory/serials/{sn}/traceability` | ❌ | — | **Requiere product_units** |

---

## 5. Orden de Implementación Recomendado (Corregido)

El orden del Gherkin es **mayormente correcto** pero omite un paso cero crítico:

```
PASO 0 — PREREQUISITE (1 día)
├── Migración 0009: product_units + has_serial + warranty_months + manufacturer
├── Modelo ProductUnit + columnas faltantes en Product
└── Schemas: SerialCreate, SerialResponse

PASO 1 — HU-F0-009-01: Categorías completas (1 día)
├── Extender PATCH/DELETE con validaciones faltantes
├── Endpoint tree=true
├── Frontend: árbol colapsable + product_count badge + dropdown parent_id

PASO 2 — HU-F0-009-02: CRUD Productos (1.5 días)
├── POST/PATCH/DELETE /api/v1/inventory/products
├── InventoryProductsService (SQLAlchemy async, no raw SQL)
├── ProductsPage.tsx + ProductFormModal.tsx
├── Sort server-side + barcode search

PASO 3 — HU-F0-009-04: Seriales CRUD (1 día)  ← ADELANTADO
├── Endpoints serials (individual + batch)
├── Stock calculado por COUNT(product_units)
├── SerialPanel.tsx + SerialBatchForm.tsx

PASO 4 — HU-F0-009-03: Wholesale pricing (0.5 días)
├── Lógica en SalesService (helper _apply_wholesale_pricing)
├── Warning wholesale_price > retail_price
├── Comprobante con precio efectivo

PASO 5 — HU-F0-009-05: Seriales en venta (1 día)
├── SaleItemCreate.serials: list[str]
├── Validación en create_sale()
├── SerialSelectorModal.tsx en POS

PASO 6 — HU-F0-009-06: Trazabilidad + anulación (1.5 días)
├── void_sale() revierte seriales
├── Traceability endpoint
├── Garantía vigente + alertas
├── SerialTraceabilityPanel.tsx

PASO 7 — HU-F0-009-07: Coexistencia (0.5 días)
├── Validaciones has_serial false↔true
├── Venta mixta en misma transacción
├── Valor de inventario mixto
```

### Cambios vs el orden original del Gherkin:

| Cambio | Razón |
|---|---|
| **Agregado Paso 0** (prerequisite) | `product_units` y `has_serial` no existen |
| **04 adelantado antes de 03** | 04 (seriales CRUD) es puramente catálogo. No toca `SalesService`. 03 (wholesale) sí. Separar reduce riesgo de conflictos. Además, tener seriales listos permite que 03 y 05 se hagan en paralelo si hay 2 devs. |
| **Posible paralelismo 03 ∥ 05** | Si 04 está completo, un dev puede hacer wholesale pricing mientras otro hace el modal de seriales en venta |

---

## 6. Gaps Arquitectónicos Detectados

### 6.1 Gaps en las Gherkin (lo que NO cubren)

| Gap | Descripción | Severidad |
|---|---|---|
| **Anulación parcial** | Las Gherkin asumen `POST /api/sales/sale/{id}/void` anula toda la venta. HU-F0-009-06 pide "anular solo 1 item". El endpoint actual no lo soporta. Se requiere `POST /api/sales/sale/{id}/items/{item_id}/void` o similar. | 🟡 Media |
| **Reserva de seriales** | HU-F0-009-05 menciona "validación al confirmar" sin bloqueo intermedio. Si dos cajeros venden el mismo serial, el segundo recibe 409. Esto es aceptable para MVP pero debe documentarse como limitación conocida. | 🟡 Media |
| **Migración de datos** | Si hay productos existentes con `category` string (previo a HU-F0-013), la migración 0008 no migra datos. Si se ejecutó en vacío, no hay problema. Si hay datos, se necesita data migration. | 🟢 Baja |
| **Kárdex para seriales** | Las Gherkin mencionan que productos con serial generan entradas de kárdex, pero no especifican si la salida debe registrar el `cost_price` individual del serial o el `average_cost` del producto. Esto afecta el costo de ventas. | 🟡 Media |
| **Índices faltantes** | `product_units` necesita índices: `(product_id, status)`, `(serial_number UNIQUE)`, `(sale_id)`, `(warranty_expiry)` para queries de alertas. No especificados en las Gherkin. | 🟢 Baja |
| **Rutas inconsistentes** | Los endpoints actuales usan `/api/v1/inventory/` pero las Gherkin piden `/api/inventory/`. Decidir si se mantiene el prefijo `/v1` o se quita. | 🟢 Baja |

### 6.2 Gaps de Modelo

| Elemento | Estado | Acción |
|---|---|---|
| `ProductUnit` (modelo) | ❌ No existe | Crear en `adapters/db/models/accounting.py` o nuevo `inventory.py` |
| `Product.has_serial` | ❌ No existe | Agregar Boolean DEFAULT FALSE |
| `Product.warranty_months` | ❌ No existe | Agregar Integer DEFAULT 0. **No confundir con `HardwareSale.warranty_months`** — son cosas distintas: uno es del producto (catálogo), otro es de la venta (override). |
| `Product.manufacturer` | ❌ No existe | Agregar VARCHAR(100) |
| `SaleItem.serials` | ❌ No existe en DB | No se almacena en `sale_items` — se almacena en `product_units.sale_item_id`. OK, pero requiere JOIN para mostrar seriales en detalle de venta. |
| `sale_items` → `product_units` | ❌ Sin FK inversa | `product_units.sale_item_id` FK → `sale_items.id` es suficiente para trazabilidad |

---

## 7. Notas para Dev Agents

### Para Backend Agent

1. **Migración 0009 — Hacerla PRIMERO.** Crea `product_units`, agrega `has_serial`, `warranty_months`, `manufacturer` a `products`. Una sola migración atómica.

2. **Usar SQLAlchemy async, NO raw SQL.** El `list_products` actual usa `sa_text`. Para nuevo código, usar el ORM. Facilita el refactoring de Fase 1.

3. **Encapsular lógica de seriales.** Crear `services/serial_service.py` con `SerialService`:
   - `register_serials(db, product_id, serials: list[SerialCreate])`
   - `validate_serials_for_sale(db, product_id, serial_numbers, quantity)`
   - `assign_serials_to_sale(db, sale_item_id, serial_numbers)`
   - `release_serials(db, sale_item_id)`
   - `get_traceability(db, serial_number)`

4. **Encapsular lógica de wholesale.** En `SalesService`, crear helper `_resolve_unit_price(product, quantity) -> float` que aplique la regla de wholesale automáticamente. El frontend puede seguir enviando `unit_price` pero el backend lo sobreescribe según la regla.

5. **Validación de integridad de seriales.** Al vender, usar `SELECT ... FOR UPDATE` en la transacción para evitar race conditions entre dos cajeros.

6. **Rutas de endpoints.** Mantener prefijo `/api/v1/inventory/` como ya existe en el código. No cambiar a `/api/inventory/` como sugieren las Gherkin (consistencia con el resto de la API).

7. **Anulación parcial.** Evaluar si se necesita YA (HU-F0-009-06 pide "anular solo 1 item"). Si se necesita, implementar `POST /api/sales/sale/{id}/items/{item_id}/void`.

### Para Frontend Agent

1. **Nuevas páginas a crear:**
   - `pages/inventario/ProductsPage.tsx` — CRUD de productos (HU-F0-009-02)
   - `pages/inventario/CategoriesPage.tsx` — extender existencia con árbol y badges (HU-F0-009-01)

2. **Nuevos componentes:**
   - `components/inventario/CategoryTree.tsx` — árbol recursivo colapsable
   - `components/inventario/ProductsTable.tsx` — tabla con sort, search, filtros
   - `components/inventario/ProductFormModal.tsx` — formulario completo con campos condicionales
   - `components/inventario/SerialPanel.tsx` — panel de gestión de seriales
   - `components/inventario/SerialTable.tsx` — tabla de seriales
   - `components/inventario/SerialBatchForm.tsx` — formulario de registro masivo
   - `components/sales/SerialSelectorModal.tsx` — modal de selección en POS
   - `components/inventario/SerialTraceabilityPanel.tsx` — timeline de trazabilidad

3. **Modificaciones a componentes existentes:**
   - `SalesNew.tsx` — integrar `SerialSelectorModal` cuando el producto tiene `has_serial`
   - `Sidebar.tsx` — agregar enlaces a `/inventario/productos` y `/inventario/categorias`
   - `CategoriesPage.tsx` — extender con vista de árbol y badge `product_count`

4. **Rutas a agregar en el router:**
   - `/inventario/productos` → `ProductsPage`
   - `/inventario/categorias` → `CategoriesPage` (mejorada)

5. **API client:** Los endpoints de productos están en `/api/v1/inventory/`. Mantener consistencia con prefijo `/v1`.

---

## 8. Riesgos de Fase 1 sobre Fase 0

### Evaluación de impacto

| Componente construido en DT-F0-009 | ¿Fase 1 lo refactoriza? | Riesgo de rotura | Mitigación |
|---|---|---|---|
| `ProductUnit` (modelo) | No directamente — es un modelo nuevo | 🟢 Bajo | Fase 1 agrega puertos abstractos, no cambia modelos DB |
| `routers/inventory.py` | **Sí** — se mueve a puertos | 🟡 Medio | Usar `InventoryProductsService` separado del router |
| `SalesService.create_sale()` | **Sí** — se abstrae con puertos | 🟡 Medio | Encapsular wholesale + seriales en helpers privados |
| `SerialService` (nuevo) | **Sí** — debe tener puerto abstracto | 🟡 Medio | Definir interfaz `SerialRepository` desde el inicio |
| `CategoriesPage.tsx` | No — frontend no se refactoriza en Fase 1 | 🟢 Bajo | N/A |
| `ProductsPage.tsx` (nuevo) | No | 🟢 Bajo | N/A |

### Recomendación clave

> **Cada nuevo Service que se cree para DT-F0-009 debe exponer un puerto abstracto** (interfaz/protocol) aunque en Fase 0 tenga una sola implementación concreta (SQLAlchemy). Así Fase 1 solo cambia el adapter, no la lógica.

Ejemplo:
```python
# ports/inventory_port.py
from abc import ABC, abstractmethod

class SerialRepository(ABC):
    @abstractmethod
    async def register(self, product_id: int, serials: list[dict]) -> list[ProductUnit]: ...
    @abstractmethod
    async def get_available(self, product_id: int) -> list[ProductUnit]: ...
    @abstractmethod
    async def assign_to_sale(self, serial_numbers: list[str], sale_item_id: int) -> None: ...
    @abstractmethod
    async def release_from_sale(self, sale_item_id: int) -> None: ...
    @abstractmethod
    async def get_traceability(self, serial_number: str) -> list[dict]: ...

# adapters/db/repositories/serial_repository.py
class SqlAlchemySerialRepository(SerialRepository):
    # Implementación concreta con SQLAlchemy
    ...
```

---

## 9. Resumen de Decisión

| Decisión | Valor |
|---|---|
| **Veredicto** | ⚠️ PROCEDE CON PRECAUCIÓN |
| **Bloqueante** | `product_units` + `has_serial` + `warranty_months` no existen → Paso 0 prerequisite |
| **Esfuerzo adicional** | +1 día (Paso 0) sobre los 7 días estimados → **Total: 8 días** |
| **Historias desbloqueadas ya** | HU-F0-009-01 (Categorías) y 02 (Productos CRUD) pueden comenzar sin prerequisite |
| **Orden corregido** | 01 → 02 → **Paso 0** → 04 → 03 ∥ 05 → 06 → 07 |
| **Riesgo Fase 1** | 🟡 Medio — mitigable con puertos abstractos desde el día 1 |
| **Gaps en Gherkin** | 6 gaps identificados (anulación parcial, reserva seriales, data migration, kárdex seriales, índices, rutas inconsistentes) |

---

*Documento generado por Architecture Agent 🏗️ basado en inspección de código en `fase0-real` (commit `96b4494`) y análisis de las 7 historias Gherkin de DT-F0-009.*
