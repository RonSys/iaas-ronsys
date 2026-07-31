# 🍽️ Guía de Usuario — Recetas y Kárdex por Consumo (Explosión de Recetas)

- **Versión del manual**: 1.0 (2026-07-31)
- **Funcionalidad**: Recetas por plato + descuento automático de ingredientes al vender
- **Spec asociada**: [`docs/specs/01-spec-recetas-productos-v0.2.md`](../specs/01-spec-recetas-productos-v0.2.md) — APROBADA e IMPLEMENTADA (criterios CA1–CA11 verificados en tenant 1)
- **Alcance**: tenant 1 (Admin Tenant, restaurant)

> Esta guía es de **usuario** (no técnica). Cada sección cita su trazabilidad con la spec
> (criterios de aceptación `CA#` y decisiones `D#`) para auditar que el manual y la
> implementación cuentan la misma historia (Spec Anchor).

---

## 1. 📋 Gestión de Recetas (UI)

*Trazabilidad: spec §3.1/§3.4 · CA2, CA9, CA10 · D1, D4, D5*

La gestión de recetas vive en el módulo **Restaurante → Menú**:

1. Entra al **Menú de platos** del restaurante.
2. Cada plato con área de preparación **🍳 Cocina** muestra el botón **📋 Receta**.
3. Al abrirlo verás el modal de receta:
   - **Lista de ingredientes** con selector de productos del inventario (búsqueda por nombre/código).
   - Por cada ingrediente: **cantidad** y **unidad de medida** (kg, und, L…).
   - **Costo estimado en vivo** = `average_cost del producto × cantidad` (se recalcula al editar).
   - **Margen** = precio de venta del plato − costo total de la receta.
4. **Guardar** (botón Guardar) persiste la receta completa (reemplaza la anterior).
   - Durante el guardado el botón muestra **"Guardando…"**.
   - Al éxito aparece un **banner verde "✅ Receta actualizada correctamente"** antes de cerrar.
   - Si algo falla, el banner rojo muestra el **detalle exacto del backend** (p. ej. unidad no
     coincide, ingrediente serializado, stock insuficiente).
   - Si la sesión expiró (401), el sistema **renueva el token automáticamente** y reintenta la
     petición; si el refresh falla, te redirige a login.
5. Si el plato aún no tiene receta, el modal muestra el estado vacío (costo 0, sin ingredientes) y permite crearla.

Reglas que aplican al guardar/editar (de la spec):

- Solo platos con `preparation_area='cocina'` pueden tener receta (`D1`). Bebidas/otros no.
- La **unidad** del ingrediente debe coincidir con la del producto (`D4`); si no, el guardado lo
  rechaza con error 400 **sin modificar la receta existente** (se normalizan abreviaturas:
  kg/kilo/kilogramo, und/unidad/unidades, g, L, mL, caja, paquete, docena, botella).
- Productos **serializados** no pueden ser ingredientes (`D5`); el guardado los rechaza.
- Los ingredientes deben pertenecer al **mismo tenant** que el plato (aislamiento multi-tenant).

---

## 2. 💳 Venta con Explosión de Receta (POS)

*Trazabilidad: spec §3.3 · CA3, CA4, CA5, CA11 · D2, D6, D8, D9*

Cuando vendes un **plato que tiene receta** y el tenant tiene activada la feature
**`recipe_explosion`** (tenant 1: ✅ activa por defecto), la venta hace esto automáticamente:

1. **Pre-valida stock de TODOS los ingredientes** de la receta.
   - Si algún ingrediente no alcanza → la venta se **rechaza (409)** con el detalle:
     `Stock insuficiente de '<ingrediente>': se necesitan X, disponible Y`.
   - La validación es **atómica**: no queda ningún movimiento parcial si falla (CA4).
2. Si hay stock suficiente, la venta se registra normal y **por cada ingrediente**:
   - Se descuenta del stock del producto (`products.current_stock`).
   - Se registra un movimiento de **kárdex tipo salida** con concepto **"Consumo por receta"**.
3. El costo de venta del plato pasa a ser **la suma del costo de sus ingredientes** (D9):
   el asiento contable incluye **Costo de Ventas (50)** contra **Inventarios (12)**.
4. **Sin doble descuento** (D2): si el plato tuviera también un `product_id` directo, solo
   se descuentan los ingredientes de la receta.

Si la feature `recipe_explosion` está **apagada**, la venta se comporta como antes:
**no descuenta ingredientes** (CA5).

> Nota v1: el POS vende productos del inventario; la explosión se dispara cuando el ítem
> de la venta incluye el `menu_item_id` del plato (el contrato API lo soporta — ver §7).

---

## 3. 📦 Kárdex Actualizado — Movimientos tipo `receta`

*Trazabilidad: spec §3.3 · CA3 · D6, D8*

En el módulo **Inventario → Kárdex** verás los movimientos generados por las ventas de platos.
Los que provienen de recetas se identifican así:

| Campo | Valor para explosión de receta | Significado |
|---|---|---|
| `movement_type` | `salida` | Sale stock del ingrediente |
| `concept` | `Consumo por receta` | Origen del movimiento (D8) |
| `reference_type` | `receta` | Tipo de documento origen (D6 — nuevo, distinto de `venta`/`compra`) |
| `reference_id` | id de la venta | La venta que disparó el consumo |
| `quantity` | cantidad consumida | = cantidad en receta × unidades vendidas del plato |
| `unit_cost` | `average_cost` del ingrediente | Costo ponderado al momento del consumo |
| `total` | quantity × unit_cost | Valorización del movimiento |
| `balance_quantity` / `balance_avg_cost` / `balance_total` | saldo resultante | Estado del ingrediente tras el movimiento |

Los movimientos de tipo `compra`/`venta`/`ajuste` (productos vendidos directamente) siguen
funcionando igual que antes; los `receta` son **adicionales** para los ingredientes.

---

## 4. 💰 Costeo del Plato y Margen

*Trazabilidad: spec §3.4 · CA2 · D9*

- **Costo del plato** = Σ (cantidad_ingrediente × average_cost_del_ingrediente).
  Se muestra en vivo en el modal de receta (sección 1) y en la respuesta de
  `GET /api/v1/restaurant/menu/{id}/recipe` como `total_estimated_cost`.
- **Margen** = precio de venta del plato − costo de la receta (absoluto y %).
- **Contablemente** (D9): al vender un plato con receta, el asiento registra
  `50 Costo de Ventas` (débito) y `12 Inventarios` (crédito) por el costo total de
  ingredientes consumidos. Así el costo real del plato queda reflejado en resultados.

---

## 5. ⚠️ Límites de la Versión v1

*Trazabilidad: spec §3.1 · D3, D5, D4, D1 · CA8*

La versión v1 **NO incluye** (alineado con el alcance aprobado):

- ❌ **Mermas / factor de desperdicio** por ingrediente (D3 — pendiente de decisión futura).
- ❌ **Productos serializados como ingredientes** (D5 — rechazados con error).
- ❌ **Conversión de unidades** (D4 — la unidad del ingrediente debe ser exactamente la del producto).
- ❌ **Explosión para productos** que no sean platos de menú (D1 — solo `menu_items` de cocina).
- ❌ **Reproceso de ventas históricas** (CA8 — la explosión aplica solo a ventas nuevas).
- ❌ **UI de venta de platos en el POS** (la gestión de recetas SÍ tiene UI — D7; la explosión
  por API está operativa, la integración visual del POS queda como mejora).

---

## 6. 🧪 Flujo de Prueba Recomendado (tenant 1 — datos [DEMO])

*Trazabilidad: CA2 → CA3 → CA11*

Los datos demo ya están cargados en tenant 1:

- **Ingredientes**: `[DEMO] Pescado fresco` (10 kg), `[DEMO] Mariscos mixtos` (8 kg),
  `[DEMO] Limón` (50 und), `[DEMO] Cebolla` (5 kg), `[DEMO] Camote` (5 kg),
  `[DEMO] Choclo` (4 kg), `[DEMO] Arroz` (10 kg), `[DEMO] Ají amarillo` (3 kg).
- **Recetas**: Ceviche Clásico (5 ingredientes, costo 4.27), Ceviche Mixto (6 ing., 5.88),
  Arroz con Mariscos (4 ing., 4.82).

### Paso a paso

1. **Ver la receta de un plato** (CA2/CA9): Menú → plato "Ceviche Clásico" → 📋 Receta.
   Confirma ingredientes, costo estimado (≈4.27) y margen.
2. **Verificar stock inicial** (CA3): Inventario → Productos → `[DEMO] Pescado fresco` = 10 kg.
3. **Vender 1 Ceviche Clásico** (CA3/CA11): POS → agrega el plato (menú) → cobra S/ 28.
   La venta debe registrarse con éxito.
4. **Verificar kárdex** (CA3): Inventario → Kárdex → filtro por el producto pescado:
   aparece una **salida "Consumo por receta"** de 0.15 kg (reference_type=`receta`,
   reference_id = id de la venta). Pescado queda en **9.85 kg**; limón −2 (48), cebolla −0.05 (4.95),
   camote −0.10 (4.90), choclo −0.05 (3.95).
5. **Verificar asiento** (CA11): Contabilidad → asiento de la venta: líneas
   `50 Costo de Ventas 4.28` y `12 Inventarios 4.28`.
6. **Probar stock insuficiente** (CA4, opcional): baja el pescado a <0.15 kg e intenta
   vender otro Ceviche Clásico → la venta se **rechaza con 409** y no deja movimientos parciales.
7. **Probar flag off** (CA5, opcional): apaga `recipe_explosion` en settings del tenant,
   vende el plato → **no descuenta ingredientes**. Vuelve a encenderlo.

### Verificación rápida por API (alternativa para Ron)

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@elsegoviano.pe","password":"***"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

# Abrir sesión POS (si no hay una abierta)
curl -s -X POST "http://localhost:8000/api/sales/sessions/open?opening_cash=100" \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: 1"

# Vender 1 Ceviche Clásico (plato menu_item_id=10 con receta)
curl -s -X POST http://localhost:8000/api/sales/sale \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: 1" -H 'Content-Type: application/json' \
  -d '{"items":[{"menu_item_id":10,"item_name":"Ceviche Clásico","item_type":"product",
       "quantity":1,"unit_of_measure":"unidad","unit_price":28,"discount_pct":0,
       "discount_amount":0,"tax_pct":0,"tax_amount":0,"total":28}],
       "payments":[{"payment_method":"cash","amount":28}]}'
```

---

## 7. 💰 Gestión de Costos Variables

*Trazabilidad: spec 02 · CA1–CA5* · relación con spec 01 (CA2, D9)

Los precios de compra de los insumos cambian (incluso por día); el sistema maneja eso con
**costo promedio ponderado** en el Kárdex. El precio de venta, en cambio, es casi estático y
se ajusta manualmente cuando conviene.

### 7.1 Registrar una compra (Kárdex → + Entrada)

1. Ve a **Inventario → Kárdex** y selecciona el insumo (ej. `[DEMO] Pescado fresco`).
2. Pulsa **+ Entrada** y completa el formulario:
   - **Cantidad** comprada (ej. 10 kg).
   - **Costo unitario del día** (ej. S/ 22.00).
   - **Concepto** (default: "Compra de insumos").
3. El formulario muestra **Stock actual**, **Costo promedio actual** y el **Nuevo promedio
   estimado** en vivo (misma fórmula que el backend) — así sabes el resultado antes de confirmar.
4. Al registrar, el kárdex crea una **entrada** y el stock/average_cost se actualizan.

### 7.2 Cómo recalcula el promedio ponderado

Fórmula: `nuevo_promedio = (stock_actual × costo_promedio + cantidad × costo_unitario) / (stock_actual + cantidad)`

**Ejemplo real (tenant 1):** pescado fresco con **9.70 kg a S/ 18.00** de promedio → compra de
**10 kg a S/ 22.00** →
`(9.70 × 18.00 + 10 × 22.00) / (9.70 + 10) = 394.60 / 19.70 = S/ 20.03`

### 7.3 Las salidas NO cambian el promedio

Las ventas/consumos (incluidas las **salidas por receta**) se valorizan al **costo promedio
vigente** del momento, pero **no alteran el promedio**: solo las entradas (compras) lo recalculan.

### 7.4 Ajustar el precio de venta

Cuando los costos suben y quieres trasladarlo al cliente:

1. **Inventario → Productos → Editar** el producto.
2. Ajusta **Precio Retail** (y Mayorista si aplica) en `ProductFormModal`.
3. Guarda — el precio de venta es estático hasta que lo cambies; no afecta el kárdex.

### 7.5 Relación con las recetas

El **costo de una receta** = Σ (cantidad_ingrediente × `average_cost` del producto). Por eso, al
registrar una compra más cara, el costo del plato y su margen se recalculan automáticamente
(ver §4 y spec 01 CA2/D9).

---

## 8. 🔗 Trazabilidad con Spec

**Spec**: `docs/specs/01-spec-recetas-productos-v0.2.md` (APROBADA → IMPLEMENTADA, 2026-07-31)

| Sección del manual | Spec (sección) | Criterios de aceptación | Decisiones |
|---|---|---|---|
| §1 Gestión de Recetas (UI) | §3.1 Alcance · §3.4 Contratos | CA2, CA9, CA10 | D1, D4, D5, D7 |
| §2 Venta con explosión (POS) | §3.3 Flujo | CA3, CA4, CA5, CA11 | D2, D6, D8, D9 |
| §3 Kárdex tipo `receta` | §3.3 Flujo | CA3 | D6, D8 |
| §4 Costeo y margen | §3.4 Contratos | CA2, CA11 | D9 |
| §5 Límites v1 | §3.1 Alcance | CA8 | D1, D3, D4, D5, D7 |
| §6 Flujo de prueba | §3.5 Criterios | CA2, CA3, CA4, CA5, CA11 | D9 |
| §7 Gestión de Costos Variables | Spec 02 (costos variables) · Spec 01 §3.4 | CA1–CA5 (spec 02) · CA2, D9 (spec 01) | D9 |

**Nota de Spec Anchor**: si el código cambia (p. ej. se agrega merma D3, UI de POS o conversión
de unidades), este manual Y la spec deben actualizarse juntos para mantener la trazabilidad.
