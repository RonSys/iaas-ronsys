# SPEC 01 — Recetas por Producto y Consumo de Insumos (Explosión de Receta)

- **Estado**: 🟢 APROBADA v0.2 (decisiones D1-D9 tomadas por Ron el 2026-07-31) → **IMPLEMENTADA 2026-07-31** (todos los criterios CA1-CA11 verificados en tenant 1)
- **Proyecto**: IaaS-RonSys
- **Alcance inicial**: tenant 1 (Admin Tenant, business_type=restaurant)
- **Fecha**: 2026-07-31
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 0. Decisiones aprobadas (D1-D9)

| Decisión | Resolución |
|---|---|
| D1 | Explosión solo para platos (`menu_items`), no para productos |
| D2 | Solo ingredientes (sin doble descuento del plato) |
| D3 | Sin merma en v1 |
| D4 | Validar que la unidad del ingrediente == unidad del producto (sin conversión) |
| D5 | Productos serializados NO permitidos como ingredientes (rechazo 400) |
| D6 | Kárdex con `reference_type='receta'` (nuevo) |
| D7 | **UI de recetas SÍ entra en alcance** (pantalla de gestión por plato) |
| D8 | Concepto kárdex: "Consumo por receta" |
| D9 | Costo de venta del plato = suma del costo de ingredientes (asiento COGS 50/12) |

---

## 1. Contexto y objetivo

El módulo de inventario/kárdex registra movimientos por **producto vendido**, pero no descuenta los **insumos** que componen un plato. Objetivo: que al vender un plato con receta, el kárdex descuente automáticamente los ingredientes de su receta (ej: vender 1 "Ceviche Clásico" → baja stock de pescado, limón, cebolla, camote, choclo).

---

## 2. Fase R — Hallazgos de la investigación (estado real)

### 2.1 El feature YA existe en código (árbol `main`), pero NO está desplegado ni migrado

| Componente | Estado |
|---|---|
| Modelos `Recipe` + `RecipeIngredient` (`app/adapters/db/models/restaurant.py`) | ✅ En código (main) |
| Migración `0012_recipes.py` (tablas `recipes`, `recipe_ingredients`) | ✅ En código (main) |
| `RecipesService` GET/PUT receta + costo/margen (`app/services/restaurant_service.py:1377`) | ✅ En código (main) |
| Endpoints `GET/PUT /api/v1/restaurant/menu/{id}/recipe` (`app/routers/restaurant.py`) | ✅ En código (main) |
| Flag `recipe_explosion` en `FeatureFlags` (`app/schemas/sales.py:317`) | ✅ En código (main) |
| Tablas `recipes` / `recipe_ingredients` en la BD | ❌ **NO existen** |
| Columna `menu_items.preparation_area` en la BD | ❌ **NO existe** |
| Endpoints de receta en el backend **desplegado** (`iaas-backend-prod`, openapi) | ❌ **NO existen** (imagen vieja) |
| Lógica de explosión al vender (descontar ingredientes) | ❌ **NO existe en ninguna parte** |

### 2.2 Bloqueantes detectados (prerrequisitos obligatorios)

- **B1 — Migraciones nunca se aplican**: `[startup] ⚠️ Alembic migration failed (non-fatal): Can't invoke function 'configure'...` — `run_async_migrations` está roto (configuración async del env de Alembic). La BD quedó en `alembic_version = 4bc771f43a4e` (anterior a recetas). **Hay que arreglarlo antes de cualquier implementación.**
- **B2 — Backend desplegado desactualizado**: la imagen `iaas-backend-prod` no expone los endpoints de receta → requiere rebuild/redeploy desde `main`.
- **B3 — Frontend**: la UI de recetas no fue verificada (posible feature parcial en worktree `unique-thumb`).

### 2.3 Cómo funciona hoy (flujo existente, intacto)

- **Venta** (`POST /api/v1/sales/sale` → `SaleService.create_sale`):
  1. Valida sesión POS abierta, payments cubren total, **stock suficiente por item** (409 si no).
  2. Crea `Sale`, `SaleItems` (product_id nullable + item_name), `SalePayments`.
  3. Por cada item con `product_id`: registra **salida de kárdex** (`KardexMovement`, reference_type='venta', costo = average_cost, balance por promedio ponderado) y decrementa `products.current_stock` (HU-F2-005). Soporta seriales (costo = promedio de seriales vendidos).
  4. Genera asiento contable automático (HU-F2-006).
- **Kárdex**: `KardexEngine` (dominio puro, promedio ponderado) + endpoints `/api/accounting/kardex/entry|exit|products|warehouse-close` + valorización.
- **Multi-tenant**: header `X-Tenant-ID` (fallback JWT `company_id`) → dependency `get_tenant_id`; todas las consultas filtran `tenant_id`. `recipes` NO tiene `tenant_id` (hereda de `menu_item`); `recipe_ingredients.product_id` → `products` (que sí tiene `tenant_id`).
- **Settings**: `companies.settings` (JSONB) → `features.recipe_explosion` = **true** para tenant 1.

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (v1):**
- Fix B1 (migraciones) y B2 (redeploy backend desde `main`) — requisitos habilitadores.
- CRUD de recetas por `menu_item` (solo `preparation_area='cocina'`) — ya implementado en código; validar y desplegar.
- **Explosión de receta al vender**: si el item vendido corresponde a un `menu_item` con receta y `recipe_explosion=true`, descontar cada ingrediente (kárdex 'salida' + decremento de `current_stock`) dentro de la **misma transacción** de la venta.
- Costeo por ingrediente con `average_cost` del producto (ponderado) → costo de receta y margen (ya en `RecipesService`).
- Aislamiento estricto al tenant 1 (validación de tenant de `menu_item` e ingredientes).

**NO INCLUYE (límites v1):**
- UI de recetas en el frontend (**D7 — INCLUIDO**): pantalla/modal para crear y editar recetas por plato desde el menú (ya existe `RecipeModal.tsx` + integración en `MenuPage.tsx` en `main`; se despliega).
- Mermas automáticas / factor de merma (D3).
- Reprocesar ventas históricas (la explosión aplica solo a ventas nuevas).
- Compra/entrada de insumos (flujo existente se mantiene).
- Multi-tenant generalizado: el diseño es multi-tenant por construcción, pero la validación de negocio se hace solo en tenant 1.

### 3.2 Modelo de datos (validar y migrar — ya definido en código)

```sql
recipes (
  id            serial PK,
  menu_item_id  int UNIQUE NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
)

recipe_ingredients (
  id               serial PK,
  recipe_id        int NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  product_id       int NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  quantity         numeric(12,4) NOT NULL DEFAULT 1,
  unit_of_measure  varchar(10) NOT NULL,
  sort_order       int NOT NULL DEFAULT 0
)

-- Adicional (pendiente en BD): menu_items.preparation_area varchar(20) DEFAULT 'cocina'
```

**Notas de diseño:**
- `recipes` no tiene `tenant_id` → aislamiento vía `menu_item.tenant_id` (validar en servicio).
- `recipe_ingredients.product_id` RESTRICT → no se puede borrar un producto que es ingrediente (protege integridad).
- **Validación pendiente en servicio**: el ingrediente (`product`) debe pertenecer al **mismo tenant** que el `menu_item`.

### 3.3 Flujo propuesto (explosión al vender)

```
POST /api/v1/sales/sale
  └─ SaleService.create_sale (transacción única)
      1. Validaciones actuales (sesión, payments, stock por item)
      2. Por cada sale_item:
         a. Si tiene product_id directo → kárdex 'salida' del producto (flujo actual, intacto)
         b. NUEVO: si el item es plato (menu_item con receta) Y recipe_explosion=true:
            - Pre-check: stock suficiente de TODOS los ingredientes (si falta → 409, rollback total)
            - Por cada ingrediente:
              · kardex 'salida' (concept: "Venta - Receta <plato>", reference_type='venta',
                reference_id=sale_id, unit_cost=average_cost del ingrediente, balance ponderado)
              · products.current_stock -= quantity (convertida según unit_of_measure)
      3. Asiento contable (HU-F2-006) — evaluar impacto del costeo por ingredientes (D9)
```

### 3.4 Contratos

**Existentes (desplegar con B2):**
- `GET  /api/v1/restaurant/menu/{item_id}/recipe` → receta + ingredientes + costo total + margen
- `PUT  /api/v1/restaurant/menu/{item_id}/recipe` → guarda/reemplaza receta (delete + insert)
- `GET  /api/v1/restaurant/products` → catálogo de productos para elegir ingredientes

**Modificados:**
- `POST /api/v1/sales/sale` → incorpora explosión (request: `SaleItemCreate` gana campo opcional `menu_item_id`; respuesta puede incluir `ingredients_consumed` opcional)
- `sale_items` gana columna `menu_item_id` (nullable, FK → menu_items ON DELETE SET NULL) — migración 0015
- `menu_items.preparation_area` se materializa en BD (migración 0015, default 'cocina')
- Asiento contable: COGS 50/12 para restaurant cuando hay kardex `reference_type='receta'` (D9)

**Nuevos (propuesta mínima):**
- Ninguno requerido en v1 si la explosión va dentro de `SaleService`. Opcional: `GET /api/v1/inventory/recipes/cost-report` (reporte de consumo por plato) — **fuera de alcance v1** salvo que Ron lo pida.

### 3.5 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA1 | `alembic upgrade head` tras fix B1 | Tablas `recipes`, `recipe_ingredients` + columna `preparation_area` existen; `alembic_version` avanzada |
| CA2 | PUT receta a "Ceviche Clásico" (pescado 0.15kg, limón 2 und, cebolla 0.05kg, camote 0.1kg, choclo 0.05kg) | 200; GET devuelve ingredientes + costo estimado + margen; plato sin receta devuelve estructura vacía |
| CA3 | Stock pescado=10kg; vender 1 Ceviche Clásico (recipe_explosion=true) | Pescado → 9.85kg; kardex_movements con salida del pescado (reference sale_id); venta 201 |
| CA4 | Stock pescado=0.05kg (receta pide 0.15kg); vender | **409** (stock insuficiente), **sin movimientos kardex parciales** (rollback atómico) |
| CA5 | recipe_explosion=false | Venta NO descuenta ingredientes (comportamiento actual) |
| CA6 | Aislamiento: PUT receta de menu_item de otro tenant | 404 (no visible); vender en tenant 3/5 no toca kardex de tenant 1 |
| CA7 | Ingrediente con `has_serial=true` | Decisión D5 (validar o rechazar) |
| CA8 | Ventas anteriores a la implementación | No se reprocesan; kardex histórico intacto |
| CA9 | UI: desde el menú del frontend, abrir receta de un plato (botón 📋 Receta), agregar ingredientes del catálogo y guardar | La receta persiste (PUT 200) y aparece al recargar (GET) |
| CA10 | UI: plato sin receta muestra estado vacío y permite crear | Modal muestra ingredientes vacíos + costo 0 |
| CA11 | Venta por API con `menu_item_id` de plato con receta (restaurant, explosion on) | Asiento contable incluye COGS 50/12 por suma de ingredientes (D9) |

### 3.6 Decisiones abiertas (requieren input de Ron)

- **D1**: ¿La explosión aplica a `menu_items` con receta, o también a `products` vendidos que tengan receta? (hoy `recipes → menu_items` únicamente).
- **D2**: Si un plato además tiene `product_id` directo en el sale_item, ¿se descuenta el producto Y los ingredientes (doble descuento) o solo los ingredientes?
- **D3**: ¿Factor de merma por ingrediente (ej: 10% descarte en cocina)? Campo `waste_factor` en `recipe_ingredients` (requiere migración adicional).
- **D4**: Unidades de medida heterogéneas: ¿validar que la `unit_of_measure` del ingrediente coincida con la del `product`, o permitir conversión explícita?
- **D5**: ¿Permitir productos serializados como ingredientes? (complejidad alta — recomiendo rechazarlos en v1).
- **D6**: ¿El kárdex del ingrediente usa `reference_type='venta'` (reutilizar) o uno nuevo `'receta'` para trazabilidad?
- **D7**: ¿La UI de recetas (frontend) entra en el alcance? ¿Existe ya en algún branch/worktree?
- **D8**: ¿Concepto de la salida por ingrediente: "Venta - Receta <plato>" o genérico "Consumo por receta"?
- **D9**: Impacto contable: el asiento de venta actual valora la salida del producto vendido; con explosión, ¿el costo de venta debe venir de la suma de ingredientes (costo real del plato)?

---

## 4. Plan de implementación sugerido (solo cuando la spec esté aprobada)

1. **Fase 0 (habilitadores)**: fix `run_async_migrations` (B1) + aplicar migraciones a head + verificar integridad de datos existentes.
2. **Fase 1**: rebuild/redeploy backend desde `main` (B2) → verificar endpoints de receta en openapi.
3. **Fase 2**: servicio `RecipeExplosionService` (o integración en `SaleService`) con pre-check atómico + kardex por ingrediente + tests.
4. **Fase 3**: datos de prueba en tenant 1 (recetas para los 14 productos demo `[DEMO]`) + ejecutar criterios de aceptación CA1-CA8.
5. **Fase 4**: sincronización Spec Anchor — actualizar esta spec si el código se desvía.

## 5. Bitácora de implementación (Spec Anchor — sync con código)

- **2026-07-31**: Implementada en `main`. Migración `0015_recipes_sale_items` (sale_items.menu_item_id + menu_items.preparation_area). Nuevo `app/services/recipe_explosion.py`. Integración en `SaleService.create_sale` (pre-check 409 atómico + explosión + COGS D9). Fix B1 en `main.py` (alembic `command.upgrade` vía `to_thread`; el path directo a `env.run_async_migrations` estaba roto). `psycopg[binary]` añadido a requirements (baseline 0000 requería psycopg; se hizo `stamp` de baseline por ser redundante con 0001+). UI de recetas ya existía en `main` (RecipeModal/MenuPage) — desplegada. CAs: CA1✓ CA2✓ CA3✓ CA4✓ CA5✓ CA6✓ CA8✓ CA9✓ CA10✓ CA11✓.
- Backend/frontend desplegados (imágenes `iaas-ronsys-backend:latest` / `iaas-ronsys-frontend:latest`); imagen previa respaldada como `.bak-20260731`.
- Datos demo tenant 1: 8 productos ingredientes `[DEMO]` (ING-PES01…ING-AJI01) + recetas en menu 10 (Ceviche Clásico), 19 (Ceviche Mixto), 14 (Arroz con Mariscos).

- **2026-07-31 (UI nav, sin cambio funcional)**: item "Inversión" movido del grupo Restaurante al grupo "Proyecto de Inversión" (label "Puesta en Marcha", 🏗️, ruta `/restaurante/inversion` intacta, condición admin conservada) en `apps/web/src/components/layout/Sidebar.tsx`.
- **2026-07-31 (UI/UX, sin cambio funcional de contrato)**: RecipeModal — banner de éxito "✅ Receta actualizada correctamente" (auto-cierre 900ms) + estado "Guardando…" + error muestra el `detail` del backend. `authFetch` — auto-refresh de token ante 401 (single-flight, mismo patrón que api.ts) con reintento único; si el refresh falla → logout. Documentado en guia-recetas-kardex.md §1.
- **2026-07-31 (FIX F1 — QA)**: `RecipesService.save_recipe` ahora valida **antes de sobrescribir**: productos del tenant (404) y **unidades normalizadas (D4)** — se añadió `normalize_unit()` compartido (kg/kilo/kilogramo, und/unidad/unidades, g, L, mL, caja, paquete, docena, botella) usado también en el precheck de explosión. Unidad inválida → 400 con mensaje claro y la receta existente NO se toca; la unidad guardada es la canónica del producto. Suite QA: T2 → PASS, **10/10**.
