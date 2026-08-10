# SPEC — Kárdex de Inventario (Promedio Ponderado + Seriales)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción; motor desde MVP, seriales en Fase 0 Ferretería)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: todos los tenants; motor puro + servicio DB; seriales para ferretería
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código
- **Relacionada**: `02-recetas-costos/02-spec-costos-variables-v0.1.md` (costos variables usa este kárdex)

---

## 1. Contexto y objetivo

El kárdex registra entradas y salidas de inventario con **costo promedio ponderado**, valoriza
stock en tiempo real y soporta trazabilidad por **seriales** (ferretería). Objetivo: documento
único del motor kárdex en sus dos capas (dominio puro + servicio de persistencia).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Arquitectura dual (verificada)

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| **Motor puro** (dominio, sin DB) | `app/core/accounting/kardex.py` (396 ln) | `KardexEngine`: registro de producto, entrada/salida con promedio ponderado, inventario inicial, valorización, costo de ventas, cierre de almacén |
| **Servicio DB** | `app/services/kardex_service.py` (265 ln) | `KardexDBService` con repositorio SQLAlchemy — reemplaza variables globales |
| **Router** | `app/routers/accounting.py:386` (kardex_router) | Endpoints `/api/accounting/kardex/*` |
| **Modelos** | `app/adapters/db/models/accounting.py` | `Product`, `ProductCategory`, `ProductUnit`, `KardexMovement` |
| **Migraciones** | `0001`, `0008`, `0009`, `0010` | Setup + categorías + unidades + seriales |

### 2.2 Motor puro — capacidades (verificadas en `kardex.py`)

- `register_product(code, name, unit)`: crea producto con stock 0.
- `record_entry(...)`: entrada → recalcula promedio ponderado:
  ```
  new_avg_cost = (current_stock × average_cost + quantity × unit_cost) / (current_stock + quantity)
  ```
  (redondeo 4 decimales; si stock final = 0 → `new_avg_cost = unit_cost`).
- `record_exit(...)`: salida valorizada al `average_cost` vigente (NO modifica el promedio).
- `record_initial_inventory(...)`: inventario inicial.
- `get_kardex(product_code)`: historial de movimientos.
- `get_total_inventory_value()`: valorización total.
- `get_cost_of_sales(...)`: costo de ventas del período.
- `warehouse_close(...)`: cierre de almacén (validación de existencias).

### 2.3 Seriales (Fase 0 Ferretería — migración 0009/0010)

- Productos con `is_serialized=True` exigen serial único por unidad.
- `POST /api/v1/inventory/products/{id}/serials` — registrar serial (unit_cost propio).
- `GET /api/v1/inventory/products/{id}/serials` — listar seriales (disponibles/vendidos).
- `GET /api/v1/inventory/serials/warranties/expiring` — garantías por vencer.
- `GET /api/v1/inventory/serials/{serial_number}/traceability` — trazabilidad completa del serial (entrada → venta).
- En venta (`sales_service.create_sale`): si el producto es serializado, valida stock de seriales disponibles (L412-417) y el costo de venta usa el promedio de seriales vendidos.

### 2.4 Endpoints del kárdex (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/accounting/kardex/products` | Registrar producto |
| POST | `/api/accounting/kardex/entry` | Entrada (compra) → recalcula promedio |
| POST | `/api/accounting/kardex/exit` | Salida (venta/consumo/receta) |
| GET | `/api/accounting/kardex/products` | Listar productos + valorización |
| GET | `/api/accounting/kardex/{product_code}` | Historial de un producto |
| GET | `/api/accounting/kardex/inventory/summary` | Resumen inventario valorizado |
| POST | `/api/accounting/kardex/warehouse-close` | Cierre de almacén |

---

## 3. Fase P — Contratos y reglas

### 3.1 Reglas de negocio (verificadas)

- **R1**: toda entrada recalcula el promedio ponderado; toda salida se valoriza al promedio vigente.
- **R2**: salidas NO modifican el promedio.
- **R3**: referencia por `reference_type`: `venta`, `receta`, `compra`, `merma`, etc. (Spec 01 añade `receta`).
- **R4**: producto serializado exige serial único; venta valida disponibilidad de seriales.
- **R5**: multi-tenant: toda consulta filtra `tenant_id` (vía `X-Tenant-ID`).

### 3.2 Criterios de aceptación (verificados)

- CA1: entrada recalcula promedio correctamente (fórmula R1). ✅
- CA2: salida valoriza al promedio vigente sin alterarlo. ✅
- CA3: valorización total = Σ(stock × average_cost). ✅
- CA4: cierre de almacén valida existencias. ✅
- CA5: seriales con trazabilidad completa (entrada → venta → garantía). ✅
- CA6: venta con producto serializado solo descuenta seriales disponibles. ✅

---

## 4. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Motor puro | `app/core/accounting/kardex.py` | §2.2 |
| Servicio DB | `app/services/kardex_service.py` | §2.1 |
| Router | `app/routers/accounting.py:386` | §2.4 |
| Seriales (inventario) | `app/routers/inventory.py`, `app/services/inventory_service.py` | §2.3 |
| Modelos | `app/adapters/db/models/accounting.py` | §2.1 |
| Migraciones | `0001`, `0008`, `0009`, `0010` | §2.1 |

> ⚠️ Si cambias la fórmula de promedio, movimientos, seriales o cierre de almacén, **actualiza esta spec** (Spec Anchor).
