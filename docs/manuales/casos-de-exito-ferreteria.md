# 🏪 Casos de Uso de Éxito — Módulo Ferretería (DT-F0-009)

**Versión:** v0.5-ferreteria
**Para probar por:** Ron
**Tenant de prueba:** `ferretero@elsegoviano.pe` / `ferreteria123`
**URL:** http://localhost:80

---

## 🎯 Caso 1 — Categorías + CRUD Productos

Cubre: HU-F0-009-01 (Categorías) + HU-F0-009-02 (CRUD Productos)

### Pasos

- [ ] 1. Inicia sesión con `ferretero@elsegoviano.pe`
- [ ] 2. Ve a **Inventario → Categorías**
- [ ] 3. Crea categoría "Fierros" → debe mostrar contador "0 producto(s)"
- [ ] 4. Crea subcategoría "Varillas de 1/2" con categoría padre "Fierros"
- [ ] 5. Ve a **Inventario → Productos**
- [ ] 6. Crea producto "Varilla de 1/2" asignado a categoría "Fierros > Varillas de 1/2"
- [ ] 7. Vuelve a Categorías → contador de "Varillas de 1/2" debe ser "1 producto(s)"
- [ ] 8. Edita el producto → cambia a otra categoría → contadores se actualizan
- [ ] 9. Elimina el producto → contador baja
- [ ] 10. Intenta eliminar categoría "Varillas de 1/2" que aún tiene productos → debe dar error **409**

---

## 🎯 Caso 2 — Precios Mayorista / Detal

Cubre: HU-F0-009-03

> ⚠️ **Nota:** El paso 6 (Cobrar) requiere sesión POS abierta — pendiente para Fase 1. Por ahora se valida hasta paso 5.

---

### ✅ Checklist

- [ ] **Paso 1:** Producto "Cemento Sol 42.5kg" creado con precios y barcode
- [ ] **Paso 2:** Página "Nueva Venta" cargó correctamente (sin 404, sin errores)
- [ ] **Paso 3:** 5 unid → precio S/25.00 c/u (minorista)
- [ ] **Paso 4:** 10 unid → precio S/22.00 c/u (mayorista)
- [ ] **Paso 5:** Barcode escaneado → producto agregado
- [ ] **Paso 6:** ⏳ Pendiente — requiere módulo de sesión POS

---

## 🎯 Caso 3 — Seriales + Trazabilidad

Cubre: HU-F0-009-04 (Registro) + HU-F0-009-05 (Venta) + HU-F0-009-06 (Anulación/Trazabilidad)

> ⚠️ **Nota:** Los pasos de venta (6-13) requieren sesión POS abierta. Se validan hasta paso 5 (registro de seriales).

---

### Paso 1 — Crear producto con seriales

#### Opción A: UI (Inventario → Productos → Nuevo Producto)
- Nombre: `Taladro Bosch GSB 13`
- Precio: `250.00`
- `has_serial = true` (toggle activado)
- `warranty_months = 12`
- Fabricante: `Bosch`
- Unidad: `unidad`
- Stock inicial: `0` (no aplica para seriales)

#### Opción B: API
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ferretero@elsegoviano.pe","password":"ferreteria123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

curl -s -X POST http://localhost:8000/api/v1/inventory/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" \
  -d '{
    "name": "Taladro Bosch GSB 13",
    "unit_of_measure": "unidad",
    "retail_price": 250.00,
    "has_serial": true,
    "warranty_months": 12,
    "manufacturer": "Bosch"
  }' | python3 -m json.tool
```
✅ **Esperado:** Producto creado con `has_serial: true` y `current_stock: 0`.

---

### Paso 2 — Abrir panel de seriales y registrar 3 seriales

> ⚠️ **Importante:** Registrar seriales se hace en una pantalla SEPARADA del formulario de crear producto.
> No busque los campos de seriales en el mismo formulario donde puso nombre y precio — eso ya se guardó.
> Los seriales se registran después, en un panel dedicado que se abre desde la tabla de productos.

#### UI: Ruta completa paso a paso

1. Vaya a **Inventario → Productos**
2. En la tabla de productos, ubique **"Taladro Bosch GSB 13"** (el que creó en el Paso 1)
3. Haga clic en el botón **"🔢 Seriales"** de esa fila → se abre un panel/modal flotante
4. En el panel, verá 2 pestañas: **"📋 Ver Seriales"** y **"➕ Registrar Seriales"**
5. **Cambie a la pestaña "➕ Registrar Seriales"** → aparecerá una tabla editable
6. Llene 3 filas (use "+ Agregar fila" para añadir la 2ª y 3ª):

   | # | Número de Serie | Fecha Compra | Precio Costo |
   |:-:|:---------------:|:------------:|:------------:|
   | 1 | BOSCH-001       | 2026-01-15   | 180.00       |
   | 2 | BOSCH-002       | 2026-02-01   | 185.00       |
   | 3 | BOSCH-003       | 2026-03-10   | 175.00       |

7. Presione **"Registrar 3 seriales"**

✅ **Esperado:** Los 3 seriales se crean con `status: "available"` y `warranty_expiry` = fecha_compra + 12 meses.
   Cambie a la pestaña "📋 Ver Seriales" para confirmar que los 3 aparecen en la tabla.

#### API (alternativa):
```bash
PRODUCT_ID=XX  # ← reemplazar con el id del paso 1

curl -s -X POST "http://localhost:8000/api/v1/inventory/products/$PRODUCT_ID/serials/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" \
  -d '{
    "serials": [
      {"serial_number": "BOSCH-001", "purchase_date": "2026-01-15", "cost_price": 180.00},
      {"serial_number": "BOSCH-002", "purchase_date": "2026-02-01", "cost_price": 185.00},
      {"serial_number": "BOSCH-003", "purchase_date": "2026-03-10", "cost_price": 175.00}
    ]
  }' | python3 -m json.tool
```
✅ **Esperado:** 3 seriales creados con `status: "available"` y `warranty_expiry` calculado (fecha_compra + 12 meses).

---

### Paso 3 — Verificar stock

```bash
curl -s "http://localhost:8000/api/v1/inventory/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" | python3 -c "
import sys,json
d = json.load(sys.stdin)
print(f\"Stock disponible: {d.get('serial_available_count')} / {d.get('serial_total_count')} totales\")
"
```
✅ **Esperado:** `Stock disponible: 3 / 3 totales`

---

### Paso 4 — Serial duplicado (debe dar error)

```bash
curl -s -X POST "http://localhost:8000/api/v1/inventory/products/$PRODUCT_ID/serials" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" \
  -d '{"serial_number": "BOSCH-001", "purchase_date": "2026-01-15", "cost_price": 180.00}' \
  | python3 -m json.tool
```
✅ **Esperado:** `HTTP 409` con `{"detail": "Número de serie BOSCH-001 ya existe"}`

---

### Paso 5 — Listar seriales con filtros

```bash
# Todos los seriales
curl -s "http://localhost:8000/api/v1/inventory/products/$PRODUCT_ID/serials" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" | python3 -m json.tool

echo "---"

# Solo disponibles
curl -s "http://localhost:8000/api/v1/inventory/products/$PRODUCT_ID/serials?status=available" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 5" | python3 -c "
import sys,json
d = json.load(sys.stdin)
print(f\"{len(d.get('serials',[]))} disponibles\")
"
```
✅ **Esperado:** 3 seriales listados. Filtro `?status=available` devuelve 3.

---

### Pasos 6-13 (Venta con seriales) — ⏳ Pendiente por sesión POS

Requiere módulo de sesión POS. Flujo esperado:
1. Abrir sesión POS
2. Ir a Nueva Venta
3. Agregar Taladro → se abre modal selector de seriales
4. Seleccionar BOSCH-001 → se agrega al ticket
5. Cobrar → stock baja a 2
6. Anular venta → stock vuelve a 3
7. Trazabilidad: timeline Registrado → Vendido → Anulado
8. Garantía de BOSCH-002: "Vigente" con días restantes

---

### ✅ Checklist

- [ ] **Paso 1:** Producto "Taladro Bosch GSB 13" con `has_serial=true`, `warranty_months=12`
- [ ] **Paso 2:** 3 seriales registrados (BOSCH-001, 002, 003)
- [ ] **Paso 3:** Stock muestra 3 disponibles
- [ ] **Paso 4:** Serial duplicado → error 409
- [ ] **Paso 5:** Listado de seriales funciona con filtros
- [ ] **Pasos 6-13:** ⏳ Pendiente — requiere sesión POS

---

## 🎯 Caso 4 — Productos sin serial (tradicional)

Cubre: HU-F0-009-07

### Pasos

- [ ] 1. Crea producto "Arena Fina x m³" con:
  - `has_serial = false`
  - Stock inicial: **50 m³**
  - Precio: S/ 35.00
- [ ] 2. Verifica stock → **50 unidades**
- [ ] 3. Ve a **Ventas → Nueva Venta**
- [ ] 4. Vende **5 m³** de "Arena Fina x m³"
  - → No debe abrirse modal de seriales (es sin serial)
- [ ] 5. Completa la venta → stock debe ser **45**
- [ ] 6. Anula la venta → stock debe volver a **50**

---

## 🎯 Caso 5 — Coexistencia mixta (opcional)

- [ ] 1. Crea una venta que incluya **1 producto con serial** + **1 producto sin serial**
- [ ] 2. Verifica que ambos tipos conviven en el mismo comprobante
- [ ] 3. Verifica que el kárdex refleja correctamente ambos movimientos

---

## 📊 Resumen de Cobertura

| Caso | ¿Qué valida? | Historias |
|:----:|-------------|:---------:|
| 1 🏗️ | Categorías + CRUD Productos | HU-F0-009-01, 02 |
| 2 💰 | Precios Mayorista/Detal | HU-F0-009-03 |
| 3 🔢 | Seriales + Trazabilidad | HU-F0-009-04, 05, 06 |
| 4 📦 | Productos sin serial | HU-F0-009-07 |
| 5 🔀 | Coexistencia mixta | HU-F0-009-07 |

---

*Documento generado por Jarvis — 2026-05-20 (actualizado con pasos detallados)*
*Basado en: `docs/backlog/gherkin-f0-009-ferreteria.md`*
