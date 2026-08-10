# SPEC 02 — Gestión de Costos Variables (Kárdex por Promedio Ponderado)

- **Estado**: 🟢 v0.1 — documentación de funcionalidad EXISTENTE + mejoras UI/UX implementadas (2026-07-31)
- **Proyecto**: IaaS-RonSys
- **Alcance**: multi-tenant (funcionalidad base); validado en tenant 1
- **Framework**: SDD / Spec Anchor — sincronizada con el código

---

## 1. Contexto

Los precios de compra de insumos varían (incluso por día); el precio de venta es casi estático
(se ajusta manualmente cuando suben los costos). El sistema ya soporta esto con **costo promedio
ponderado** en el kárdex: cada compra recalcula el costo, las salidas se valorizan al costo vigente
y las recetas usan ese `average_cost` para costear platos (spec 01, D9).

## 2. Funcionalidad existente (backend — sin cambios)

- **Entrada de inventario** `POST /api/accounting/kardex/entry` (`app/core/accounting/kardex.py`):
  recibe `product_code`, `quantity`, `unit_cost`, `concept`, `date` y recalcula:
  ```
  new_avg_cost = (current_stock × average_cost + quantity × unit_cost) / (current_stock + quantity)
  ```
  (redondeo a 4 decimales; si stock final = 0, `new_avg_cost = unit_cost`). Actualiza
  `products.current_stock` y `products.average_cost` y registra el movimiento `entrada`.
- **Salidas** (venta/consumo/receta): se valorizan a `average_cost` vigente y **NO modifican el promedio**.
- **Precios de venta**: `products.retail_price` / `wholesale_price` — estáticos, editables por API
  (`PATCH /api/v1/inventory/products/{id}`) y UI.
- **Recetas**: `recipe_ingredients.product_id → products.average_cost` → costo de plato (spec 01 §3.4).

## 3. UI/UX (pantallas y flujo)

### 3.1 Pantallas que intervienen

| Pantalla | Ruta / componente | Rol |
|---|---|---|
| Kárdex — lista de inventario | `apps/web/src/pages/Kardex.tsx` | Muestra stock, costo promedio y valor total por producto; botones + Entrada / - Salida |
| Modal **Registrar Entrada** | `KardexEntryModal` (en Kardex.tsx) | Formulario: Cantidad + Costo unitario + Concepto (default "Compra de insumos") |
| Editar producto (precios) | `ProductFormModal` (Inventario → Productos → Editar) | Precio Retail y Mayorista (estáticos, ajustables) |
| Receta | `RecipeModal` (spec 01) | Muestra costo estimado y margen usando `average_cost` |

### 3.2 Mejoras UI/UX implementadas (2026-07-31)

En el modal **Registrar Entrada** (`Kardex.tsx`), sin cambiar contratos:

1. **Contexto del producto**: muestra **Stock actual** y **Costo promedio actual** del insumo seleccionado.
2. **Preview del nuevo promedio**: calcula en vivo el **"Nuevo promedio estimado"** con la MISMA
   fórmula del backend (stock×avg + qty×cost) / (stock+qty), redondeado a 2 decimales para mostrar;
   se actualiza al tipear cantidad/costo y desaparece si la cantidad no es válida (≤0).
3. El formulario conserva el estado "Registrando…" durante el POST y el mensaje
   "Entrada registrada ✅" de la página al confirmar.

### 3.3 Flujo de usuario

1. **Inventario → Kárdex** → selecciona el insumo.
2. **+ Entrada** → ve el stock y costo promedio actuales → ingresa cantidad y costo del día →
   el preview muestra el nuevo promedio antes de confirmar.
3. **Registrar Entrada** → kárdex con movimiento `entrada`; stock y promedio actualizados.
4. Si los costos subieron y quieres trasladarlo: **Inventario → Productos → Editar** → ajusta
   Precio Retail/Mayorista.
5. El costo de las recetas refleja el nuevo `average_cost` automáticamente (spec 01).

## 4. Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA1 | Entrada con promedio ponderado (pescado 9.70 kg @ S/18.00 + compra 10 kg @ S/22.00) | Nuevo promedio = (9.70×18 + 10×22)/19.70 = **S/20.03**; stock = 19.70 kg; kárdex movimiento `entrada` |
| CA2 | Salida (venta/receta) con promedio vigente | Se valoriza a S/20.03 pero el `average_cost` del producto NO cambia |
| CA3 | Preview UI del nuevo promedio | Coincide con la fórmula del backend para los mismos inputs (verificación manual/visual) |
| CA4 | Ajuste de Precio Retail/Mayorista (ProductFormModal) | Persiste en `products`; no genera movimientos de kárdex ni toca promedios |
| CA5 | Receta tras una entrada más cara | `total_estimated_cost` del plato y margen se recalculan con el nuevo `average_cost` (spec 01 CA2) |
| CA6 | Entrada con cantidad ≤ 0 | UI no muestra preview y el backend rechaza (validación existente) |

## 5. Bitácora Spec Anchor

- **2026-07-31 (v0.1)**: spec creada documentando funcionalidad existente (promedio ponderado,
  salidas al costo vigente, precios estáticos). Mejoras UI/UX implementadas en `Kardex.tsx`
  (modal Entrada: stock actual + costo promedio actual + preview del nuevo promedio).
  Manual actualizado: `docs/manuales/guia-recetas-kardex.md` §7.
- Sin cambios de contrato API ni de modelo de datos.
- **2026-07-31 (verificación)**: CA1 validado en tenant 1 — registro ING-PES01 en engine (9.70 @ 18.00) + entrada 10 kg @ 22.00 → saldo 19.70 kg, promedio **20.0305** (≈ S/20.03), total 394.60.
- **Hallazgo (limitación conocida, sin fix en v0.1)**: `POST /api/accounting/kardex/entry` opera sobre el motor **en memoria** (`_kardex_engine`); los productos creados por `POST /api/v1/inventory/products` (BD) NO están registrados en el engine → la entrada falla con "Producto no encontrado" salvo que se registren antes vía `POST /api/accounting/kardex/products`. El summary combina engine (prioridad) + BD. Recomendación futura: respaldar el engine en BD (kardex_movements ya existe) o hacer `record_entry` DB-aware.
- UI implementada en Kardex.tsx (modal Entrada): stock actual, costo promedio actual y preview del nuevo promedio (misma fórmula del backend).
- **2026-07-31 (FIX DB-aware aplicado — Ron aprobó)**: la UI de Kárdex ahora usa los endpoints **HU-F2-012 `/db/*`** (KardexDBService persistente): `getKardexInventory → /db/inventory`, `getKardex → /db/{code}`, `registerKardexEntry → /db/entry`, `registerKardexExit → /db/exit`, `registerProduct → /db/products`, `warehouseClose → /db/warehouse-close` (api.ts). Fix de aislamiento en `SQLAlchemyInventoryRepository.get_product/get_products` (faltaba filtro `tenant_id` — los summaries DB habrían filtrado productos de otros tenants). Verificado en tenant 1: /db/entry ING-PES01 10kg@22 → producto 19.70 @ 20.0305, movimiento `entrada`/`compra` persistido en kardex_movements (id 40), /db/inventory solo tenant 1 (22 productos), historial completo. Los endpoints legacy `/entry`/`/exit` (engine in-memory) quedan para el flujo del simulador.
- **Hallazgo relacionado (no fixado)**: `searchKardexProducts` (POS) llama `GET /api/accounting/kardex/products?search=` que NO existe (solo POST); la ruta dinámica `GET /{product_code}` la absorbe → la búsqueda de productos en el POS devuelve 404. Pendiente de evaluar.
- **2026-07-31 (FIX búsqueda POS aplicado)**: añadido `GET /api/accounting/kardex/products?search=` (DB-aware, tenant-scoped, por nombre/código/barcode ILIKE, active + limit) DECLARADO ANTES de `GET /{product_code}` para que la ruta dinámica no lo capture (causa del 404). Verificado: search 'pescado' → 2 resultados (tenant 1). Aclaración: el buscador VISIBLE del POS (ProductSearch → `/api/v1/inventory/products?search=`) YA funcionaba; `searchKardexProducts` (hook useSales) era código muerto (sin consumidores) — el endpoint nuevo lo deja funcional por si se reutiliza. Aislamiento: user de tenant 1 recibe 403 al consultar con X-Tenant-ID 3 + filtro SQL por tenant.
