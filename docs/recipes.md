# 📋 Módulo de Recetas e Insumos — Documentación Técnica

> **Feature:** Caso 6 — Recetas por Plato  
> **Versión:** 0.5.0  
> **Estado:** ✅ Implementado  
> **Deuda técnica:** [TD-004](/CHANGELOG.md) (descuento automático de kardex)

---

## 1. Descripción General

El módulo de **Recetas** permite registrar los insumos (materia prima) que componen cada plato del menú con área de preparación "cocina". Cada plato puede tener cero o una receta; si tiene receta, se calcula automáticamente el **costo estimado** (basado en el costo promedio de cada producto) y el **margen** respecto al precio de venta.

> ⚠️ **Regla de negocio:** Solo los ítems con `preparation_area = "cocina"` pueden tener receta.  
> Los ítems de barra (`"barra"`) y los productos sin área (`"ninguno"`) son de compra-venta directa y no admiten receta.

---

## 2. Modelo de Datos

### 2.1. `Recipe` — Receta

| Columna       | Tipo       | Restricciones                        | Descripción                        |
|---------------|------------|--------------------------------------|------------------------------------|
| `id`          | `INT`      | PK, autoincrement                    | ID único de la receta              |
| `menu_item_id`| `INT`      | FK → `menu_items.id`, **UNIQUE**, NOT NULL | Plato al que pertenece     |
| `created_at`  | `DATETIME` | server_default = now()               | Fecha de creación                  |
| `updated_at`  | `DATETIME` | server_default/onupdate = now()      | Última modificación                |

- `cascade="all, delete-orphan"` sobre `ingredients` — al eliminar receta se eliminan sus ingredientes.
- Relación `menu_item` → `back_populates="recipe"`.

### 2.2. `RecipeIngredient` — Ingrediente de Receta

| Columna           | Tipo        | Restricciones                        | Descripción                               |
|-------------------|-------------|--------------------------------------|-------------------------------------------|
| `id`              | `INT`       | PK, autoincrement                    | ID único del ingrediente                  |
| `recipe_id`       | `INT`       | FK → `recipes.id`, NOT NULL          | Receta a la que pertenece                 |
| `product_id`      | `INT`       | FK → `products.id` (RESTRICT), NOT NULL | Producto de inventario usado como insumo |
| `quantity`        | `NUMERIC(12,4)` | NOT NULL, default=1              | Cantidad necesaria                        |
| `unit_of_measure` | `VARCHAR(10)`   | NOT NULL                          | Unidad de medida (g, kg, unidad, ml, l)   |
| `sort_order`      | `INT`       | NOT NULL, default=0                  | Orden de visualización                    |

- **`ondelete="RESTRICT"`** en `product_id` — no se puede eliminar un producto que esté siendo usado como insumo en alguna receta.
- Ordenado por `sort_order ASC` por defecto.

### 2.3. Relaciones ER

```
menu_items (1) ──── (0..1) recipe (1) ──── (0..N) recipe_ingredients (N) ──── (1) products
```

---

## 3. Endpoints API

> **Base URL:** `/api/v1/restaurant`  
> **Headers requeridos:** `X-Tenant-ID`, `Authorization: Bearer <token>`

### 3.1. Obtener Receta de un Plato

```
GET /menu/{item_id}/recipe
```

**Roles permitidos:** `admin`, `manager`, `operator`, `viewer`

**Response `200 OK`:**

```json
{
  "id": 1,
  "menu_item_id": 5,
  "menu_item_name": "Ceviche Clásico",
  "has_recipe": true,
  "ingredients": [
    {
      "product_id": 1,
      "product_name": "Pescado",
      "quantity": 200.0,
      "unit_of_measure": "g",
      "sort_order": 0,
      "average_cost": 0.015,
      "estimated_cost": 3.00
    },
    {
      "product_id": 2,
      "product_name": "Limón",
      "quantity": 3.0,
      "unit_of_measure": "unidad",
      "sort_order": 1,
      "average_cost": 0.25,
      "estimated_cost": 0.75
    },
    {
      "product_id": 3,
      "product_name": "Cebolla",
      "quantity": 1.0,
      "unit_of_measure": "unidad",
      "sort_order": 2,
      "average_cost": 0.50,
      "estimated_cost": 0.50
    },
    {
      "product_id": 4,
      "product_name": "Camote",
      "quantity": 100.0,
      "unit_of_measure": "g",
      "sort_order": 3,
      "average_cost": 0.0025,
      "estimated_cost": 0.25
    }
  ],
  "total_estimated_cost": 4.50,
  "menu_item_price": 25.00,
  "margin": 20.50,
  "margin_pct": 82.0,
  "created_at": "2026-05-27T10:00:00Z",
  "updated_at": "2026-05-27T10:00:00Z"
}
```

**Response `200 OK` (plato sin receta):**

```json
{
  "id": null,
  "menu_item_id": 5,
  "menu_item_name": "Ceviche Clásico",
  "has_recipe": false,
  "ingredients": [],
  "total_estimated_cost": 0.0,
  "menu_item_price": 25.00,
  "margin": 25.00,
  "margin_pct": 100.0,
  "created_at": null,
  "updated_at": null
}
```

**Response `400 Bad Request`** (plato sin preparación "cocina"):

```json
{
  "detail": "Solo los items con 'preparation_area=cocina' pueden tener receta"
}
```

### 3.2. Guardar/Actualizar Receta

```
PUT /menu/{item_id}/recipe
```

**Roles permitidos:** `admin`, `manager`

**Ejemplo de Request:**

```json
{
  "ingredients": [
    {
      "product_id": 1,
      "quantity": 200.0,
      "unit_of_measure": "g",
      "sort_order": 0
    },
    {
      "product_id": 2,
      "quantity": 3.0,
      "unit_of_measure": "unidad",
      "sort_order": 1
    },
    {
      "product_id": 3,
      "quantity": 1.0,
      "unit_of_measure": "unidad",
      "sort_order": 2
    },
    {
      "product_id": 4,
      "quantity": 100.0,
      "unit_of_measure": "g",
      "sort_order": 3
    }
  ]
}
```

**Response `200 OK`:**

```json
{
  "id": 1,
  "menu_item_id": 5,
  "menu_item_name": "Ceviche Clásico",
  "has_recipe": true,
  "ingredients": [
    {
      "product_id": 1,
      "product_name": "Pescado",
      "quantity": 200.0,
      "unit_of_measure": "g",
      "sort_order": 0,
      "average_cost": 0.015,
      "estimated_cost": 3.00
    }
  ],
  "total_estimated_cost": 4.50,
  "menu_item_price": 25.00,
  "margin": 20.50,
  "margin_pct": 82.0,
  "created_at": "2026-05-27T10:00:00Z",
  "updated_at": "2026-05-27T10:05:00Z"
}
```

> 💡 **Comportamiento:** Este endpoint **reemplaza completamente** todos los ingredientes.  
> Si la receta no existía, se crea una nueva. Si ya existía, se eliminan los ingredientes anteriores y se insertan los nuevos (transaccional).

**Response `400 Bad Request`:**

```json
{
  "detail": "Solo los items con 'preparation_area=cocina' pueden tener receta"
}
```
```json
{
  "detail": "El producto #99 no existe en el inventario del tenant"
}
```

### 3.3. Listar Productos para Selector de Insumos

```
GET /products
```

**Roles permitidos:** `admin`, `manager`, `operator`, `viewer`

**Response `200 OK`:**

```json
[
  {
    "id": 1,
    "name": "Pescado",
    "unit_of_measure": "g",
    "average_cost": 0.015,
    "current_stock": 5000.0
  },
  {
    "id": 2,
    "name": "Limón",
    "unit_of_measure": "unidad",
    "average_cost": 0.25,
    "current_stock": 120.0
  },
  {
    "id": 3,
    "name": "Cebolla",
    "unit_of_measure": "unidad",
    "average_cost": 0.50,
    "current_stock": 30.0
  }
]
```

---

## 4. Cálculos

### Costo Estimado por Ingrediente

```
estimated_cost = quantity × product.average_cost
```

Donde `average_cost` proviene del kárdex (costo promedio ponderado del producto).

### Costo Total Estimado de la Receta

```
total_estimated_cost = Σ(estimated_cost) para todos los ingredientes
```

### Margen

```
margin = menu_item_price - total_estimated_cost
margin_pct = (margin / menu_item_price) × 100
```

---

## 5. Reglas de Negocio

| Regla | Descripción |
|-------|-------------|
| **RN-REC-01** | Solo platos con `preparation_area = "cocina"` pueden tener receta |
| **RN-REC-02** | Un plato solo puede tener una receta (relación 1:1, FK unique) |
| **RN-REC-03** | La receta no es obligatoria — un plato puede venderse sin receta |
| **RN-REC-04** | Al guardar receta se **reemplazan** todos los ingredientes (no es incremental) |
| **RN-REC-05** | No se puede eliminar un producto del inventario si está siendo usado como insumo en alguna receta (`ondelete=RESTRICT`) |
| **RN-REC-06** | La cantidad del ingrediente debe ser > 0 |
| **RN-REC-07** | El costo estimado se calcula con el `average_cost` actual del producto al momento de la consulta |
| **RN-REC-08** | Solo roles `admin` y `manager` pueden crear/editar recetas |
| **RN-REC-09** | Los ingredientes se ordenan por `sort_order` ascendente |

---

## 6. Frontend

### 6.1. Componentes

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| `MenuPage` | `.../MenuPage.tsx` | Botón "📋 Receta" visible solo en items con `preparation_area === "cocina"` |
| `RecipeModal` | `.../RecipeModal.tsx` | Modal de gestión de recetas: selector de productos, cantidades, costo en tiempo real |

### 6.2. Flujo de Usuario

1. El usuario navega a **Restaurante → Menú** (`/restaurante/menu`)
2. Solo los platos con badge "🍳 Cocina" muestran el botón **📋 Receta**
3. Al hacer clic, se abre el **RecipeModal** que:
   - Muestra los ingredientes actuales (si existe receta)
   - Permite buscar y seleccionar productos del inventario
   - Asigna cantidad y unidad de medida (heredada del producto)
   - Calcula y muestra el costo estimado en tiempo real
4. Al guardar, se envía `PUT /menu/{id}/recipe` con el listado completo de ingredientes
5. Al consultar el detalle, se muestran:
   - Lista de ingredientes con cantidad y unidad
   - Costo total estimado de la receta
   - Margen (absoluto y porcentaje) vs precio de venta

---

## 7. Migración de Base de Datos

**Migration file:** `apps/backend/app/adapters/alembic/versions/0012_recipes.py`

```python
# Tablas creadas:
# - recipes       (pk, menu_item_id fk unique, created_at, updated_at)
# - recipe_ingredients (pk, recipe_id fk, product_id fk, quantity, unit_of_measure, sort_order)
```

---

## 8. Deuda Técnica

| ID | Descripción | Estado |
|----|-------------|--------|
| **TD-004** | Descuento automático de kardex al confirmar venta (recipe_explosion) — al vender un plato con receta, se deben descontar automáticamente los insumos del inventario multiplicando cantidades por la cantidad vendida | 🔮 Futuro |

---

## 9. Tests

**Archivo:** `apps/backend/tests/test_caso6_recipes.py`

- Verifica que solo platos de cocina puedan tener receta
- Verifica creación, lectura y actualización de recetas
- Verifica reemplazo completo de ingredientes
- Verifica cálculo correcto de costos y márgenes
- Verifica validación de productos existentes

---

## 10. Ejemplos de Uso

### curl — Obtener receta

```bash
curl -s -H "X-Tenant-ID: 1" \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/restaurant/menu/5/recipe | jq
```

### curl — Guardar receta

```bash
curl -s -X PUT \
  -H "X-Tenant-ID: 1" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ingredients":[{"product_id":1,"quantity":200,"unit_of_measure":"g","sort_order":0}]}' \
  http://localhost:8000/api/v1/restaurant/menu/5/recipe | jq
```

### curl — Listar productos

```bash
curl -s -H "X-Tenant-ID: 1" \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/restaurant/products | jq
```

---

> **Documentación generada el:** 2026-05-27  
> **Responsable:** Docs Worker — Pipeline SDD
