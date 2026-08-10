# SPEC — Inventario Ferretería (Categorías, Productos, Seriales, Garantías)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción; Fase 0 Ferretería, migraciones `0008`, `0009`, `0010`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant (business_type=ferreteria)
- **Alcance**: tenants ferretería; diseño multi-tenant por construcción
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

El módulo de inventario da soporte a la ferretería: **categorías jerárquicas, productos con
unidades y precios, seriales para trazabilidad (herramientas/equipos) y alerta de garantías**.
Se integra con el kárdex (spec 00-kardex) para valorización y con el POS para ventas.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Router inventario | `app/routers/inventory.py` (340 ln) | ✅ Desplegado |
| Service | `app/services/inventory_service.py` (1,131 ln) | ✅ Implementado |
| Modelos | `ProductCategory`, `Product`, `ProductUnit` (`models/accounting.py`) | ✅ Implementado |
| Migraciones | `0008_product_categories_pricing`, `0009_product_units_and_serials`, `0010_product_categories_missing_columns` | ✅ Aplicadas en prod |
| Frontend | `pages/inventario/ProductsPage.tsx`, `pages/ferreteria/CategoriesPage.tsx`, `Kardex.tsx` | ✅ Desplegado |
| Tests | `test_ferreteria_f0_009.py`, `test_business_type.py` | ✅ 2 archivos |
| E2E | `e2e/kardex.spec.ts` | ✅ Parcial |

### 2.2 Endpoints (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/categories` | Crear categoría (201) |
| GET | `/api/v1/inventory/categories` | Listar categorías |
| PATCH | `/api/v1/inventory/categories/{id}` | Editar categoría |
| DELETE | `/api/v1/inventory/categories/{id}` | Eliminar categoría (204) |
| POST | `/api/v1/inventory/products` | Crear producto (201) |
| GET | `/api/v1/inventory/products` | Listar productos (filtros) |
| GET | `/api/v1/inventory/products/value` | Valorización de inventario |
| GET | `/api/v1/inventory/products/{id}` | Detalle producto |
| PATCH | `/api/v1/inventory/products/{id}` | Editar producto (precios, stock) |
| DELETE | `/api/v1/inventory/products/{id}` | Eliminar producto (204) |
| POST | `/api/v1/inventory/products/{id}/serials` | Registrar serial (201) |
| POST | `/api/v1/inventory/products/{id}/serials/batch` | Registrar seriales en lote |
| GET | `/api/v1/inventory/products/{id}/serials` | Listar seriales del producto |
| GET | `/api/v1/inventory/serials/warranties/expiring` | Garantías por vencer |
| GET | `/api/v1/inventory/serials/{serial_number}/traceability` | Trazabilidad del serial |

### 2.3 Modelo de datos (verificado)

```sql
product_categories (id, tenant_id, name, parent_id NULL, sort_order, is_active)  -- mig. 0008 + 0010 (columnas faltantes)
product_units (id, tenant_id, code, name)                                        -- mig. 0009
products (
  id, tenant_id, category_id, unit_id,
  code UNIQUE, name, description,
  retail_price numeric, wholesale_price numeric,
  current_stock numeric, average_cost numeric,
  is_serialized bool DEFAULT false,               -- mig. 0009
  is_active bool, created_at, updated_at
)
product_serials (id, product_id, serial_number UNIQUE, unit_cost, status[disponible|vendido], warranty_months, sold_at, sale_item_id)
```

### 2.4 Reglas de negocio (verificadas)

- **R1**: categorías jerárquicas (`parent_id`) con edición y borrado lógico.
- **R2**: precios retail/mayorista editables por API y UI (Spec 02 costos).
- **R3**: `is_serialized` → venta valida seriales disponibles (ver spec kárdex §2.3).
- **R4**: garantía en meses por serial → alerta de expiración.
- **R5**: business_type `ferreteria` habilita flujo ferretería (test_business_type).

### 2.5 Criterios de aceptación (verificados)

- CA1: CRUD de categorías y productos aislado por tenant. ✅
- CA2: valorización `/products/value` consistente con kárdex. ✅
- CA3: seriales: registro, listado, trazabilidad, garantías por vencer. ✅
- CA4: producto serializado no vendible sin serial disponible. ✅
- CA5: `test_ferreteria_f0_009` y `test_business_type` PASS. ✅

---

## 3. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Router | `app/routers/inventory.py` | §2.2 |
| Service | `app/services/inventory_service.py` | §2.1 |
| Modelos | `models/accounting.py` (Product, ProductCategory, ProductUnit) | §2.3 |
| Migraciones | `0008`, `0009`, `0010` | §2.1 |
| Frontend | `ProductsPage.tsx`, `CategoriesPage.tsx`, `Kardex.tsx` | §2.1 |
| Tests | `test_ferreteria_f0_009.py`, `test_business_type.py` | §2.5 |

> ⚠️ Si cambias categorías/productos/seriales/garantías o la valorización, **actualiza esta spec** (Spec Anchor).
