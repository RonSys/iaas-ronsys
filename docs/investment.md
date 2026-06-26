# 💰 Módulo de Inversión — Puesta en Marcha — Documentación Técnica

> **Feature:** Caso 7 — Registro de Bienes de Inversión  
> **Versión:** 0.6.0  
> **Estado:** ✅ Implementado  
> **Gherkin:** `caso7-inversion-puesta-marcha.md`

---

## 1. Descripción General

El módulo de **Inversión / Puesta en Marcha** permite a los administradores del restaurante "El Segoviano" registrar los bienes de inversión adquiridos para la apertura y operación del local. Proporciona control de presupuesto estimado vs. gasto real, asociación de comprobantes y dashboard de progreso.

> 🔒 **Permisos:** Solo usuarios con rol `admin` pueden acceder a este módulo.
>
> Operadores y meseros NO ven el menú ni la ruta `/restaurante/inversion`.

---

## 2. Reglas de Negocio

| ID | Regla |
|----|-------|
| RN-INV-01 | Cada bien pertenece a una **categoría** de inversión predefinida |
| RN-INV-02 | Cada bien tiene un **costo estimado** (presupuestado) y un **costo real** opcional |
| RN-INV-03 | El costo real puede estar vacío si el bien aún no se ha adquirido |
| RN-INV-04 | Opcionalmente se puede asociar un **código de recibo/factura** |
| RN-INV-05 | Los bienes pueden marcarse como **adquirido** (`acquired`) o **pendiente** (`pending`) |
| RN-INV-06 | El dashboard muestra: total estimado, total real, diferencia y conteo de adquiridos |

---

## 3. Categorías Predefinidas

| Categoría (código) | Emoji | Ejemplos |
|-----|-------|----------|
| `infraestructura` | 🏗️ | Carpa calle, piso, instalación puerta, ventana |
| `mobiliario` | 🪑 | Mesas, sillas, separadores, barra, estantes |
| `equipamiento_cocina` | 🔥 | Cocina, campana, frios (barra metal), pozos |
| `instalaciones` | 🛠️ | Instalación puerta, instalación internet/cable |
| `vestimenta` | 👕 | Uniformes, mandiles |
| `dyl` | 📋 | Pintura, luces, letreros, utensilios, cartas (DyL = Decoración y Logística) |
| `tecnologia` | 📱 | Celular, equipo POS, tablet |
| `marketing` | 📣 | Grabación inauguración, live TikTok, streamer |
| `gastos_operativos` | 💰 | Garantía alquiler, alquiler, gastos instalación |

---

## 4. Modelo de Datos

### 4.1. `InvestmentItem` — Bien de inversión

**Tabla:** `investment_items`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| `id` | `INTEGER` | PK, autoincrement | ID único |
| `tenant_id` | `INTEGER` | FK → `companies.id` (CASCADE), NOT NULL, indexed | Empresa propietaria |
| `name` | `VARCHAR(150)` | NOT NULL | Nombre del bien |
| `category` | `VARCHAR(50)` | NOT NULL, CHECK en valores válidos | Categoría de inversión |
| `estimated_cost` | `NUMERIC(12,2)` | NOT NULL, CHECK >= 0 | Costo presupuestado |
| `actual_cost` | `NUMERIC(12,2)` | NULLABLE, CHECK NULL or >= 0 | Costo real |
| `receipt_code` | `VARCHAR(100)` | NULLABLE | Código de recibo/factura |
| `status` | `VARCHAR(20)` | NOT NULL, default `'pending'`, CHECK `IN ('pending','acquired')` | Estado del bien |
| `notes` | `TEXT` | NULLABLE | Notas adicionales |
| `created_at` | `DATETIME` | NOT NULL, server_default = now() | Fecha de creación |
| `updated_at` | `DATETIME` | NOT NULL, server_default/onupdate = now() | Última modificación |

**Índices:**

| Nombre | Columnas |
|--------|----------|
| `idx_investment_tenant_category` | `(tenant_id, category)` |
| `idx_investment_tenant_status` | `(tenant_id, status)` |

**Check Constraints:**

| Nombre | Expresión |
|--------|-----------|
| `ck_investment_estimated_cost` | `estimated_cost >= 0` |
| `ck_investment_actual_cost` | `actual_cost IS NULL OR actual_cost >= 0` |
| `ck_investment_status` | `status IN ('pending', 'acquired')` |
| `ck_investment_category` | `category IN ('infraestructura', 'mobiliario', ..., 'gastos_operativos')` |

---

## 5. API REST

**Base path:** `/api/v1/restaurant/investment`  
**Autenticación:** JWT (Bearer token) + X-Tenant-ID header  
**Permisos:** Todos los endpoints requieren `role=admin`

### 5.1. Listar bienes

```
GET /api/v1/restaurant/investment
```

**Query params opcionales:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `category` | `str` | Filtrar por categoría |
| `status` | `str` | Filtrar por estado (`pending` / `acquired`) |

**Response:** `List[InvestmentResponse]`

```json
[
  {
    "id": 1,
    "name": "Cocina Industrial",
    "category": "equipamiento_cocina",
    "estimated_cost": 3500.0,
    "actual_cost": 3200.0,
    "receipt_code": "FAC-001",
    "status": "acquired",
    "notes": null,
    "created_at": "2026-05-27T10:00:00",
    "updated_at": "2026-05-27T10:00:00"
  }
]
```

### 5.2. Crear bien

```
POST /api/v1/restaurant/investment
```

**Request body:** `InvestmentCreate`

```json
{
  "name": "Cocina Industrial",
  "category": "equipamiento_cocina",
  "estimated_cost": 3500.0,
  "actual_cost": 3200.0,
  "receipt_code": "FAC-001",
  "status": "acquired",
  "notes": null
}
```

**Response:** `201 Created` — `InvestmentResponse`

### 5.3. Obtener bien por ID

```
GET /api/v1/restaurant/investment/{id}
```

**Response:** `InvestmentResponse`  
**Error:** `404 Not Found` si no existe o no pertenece al tenant

### 5.4. Actualizar bien

```
PUT /api/v1/restaurant/investment/{id}
```

**Request body:** `InvestmentUpdate` (todos los campos opcionales)

```json
{
  "actual_cost": 3100.0
}
```

**Response:** `InvestmentResponse` actualizado  
**Error:** `404 Not Found` si no existe

### 5.5. Eliminar bien

```
DELETE /api/v1/restaurant/investment/{id}
```

**Response:** `204 No Content`  
**Error:** `404 Not Found` si no existe

### 5.6. Resumen de inversión

```
GET /api/v1/restaurant/investment/summary
```

**Response:** `InvestmentSummary`

```json
{
  "total_estimated": 5700.0,
  "total_actual": 3950.0,
  "difference": 1750.0,
  "acquired_count": 2,
  "pending_count": 2,
  "total_count": 4
}
```

---

## 6. Schemas Pydantic

Definidos en `app/schemas/restaurant.py`:

| Schema | Propósito | Campos clave |
|--------|-----------|--------------|
| `InvestmentCreate` | Crear bien | name (required), category (pattern), estimated_cost (ge=0), actual_cost (ge=0, optional), receipt_code, status (pattern), notes |
| `InvestmentUpdate` | Actualizar bien | Todos opcionales. `actual_cost: None` significa "no cambiar"; no se puede enviar null para borrar |
| `InvestmentResponse` | Respuesta API | Incluye id, timestamps. `from_attributes=True` |
| `InvestmentSummary` | Resumen de totales | total_estimated, total_actual, difference, counts |

**Validación incluida en los schemas:**

- `name`: 1–200 caracteres
- `category`: debe coincidir exactamente con una de las 9 categorías (regex pattern)
- `estimated_cost`: >= 0
- `actual_cost`: >= 0 si se proporciona (nullable)
- `receipt_code`: máximo 50 caracteres
- `status`: debe ser `pending` o `acquired`
- `notes`: máximo 500 caracteres

---

## 7. Frontend

### 7.1. Estructura de Componentes

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| `InvestmentPage` | `pages/restaurante/InvestmentPage.tsx` | Dashboard principal con resumen + listado agrupado por categoría |
| `InvestmentModal` | `components/restaurante/InvestmentModal.tsx` | Modal de creación/edición con validación inline |
| `InvestmentDetail` | `components/restaurante/InvestmentDetail.tsx` | Vista detalle overlay con ahorro/exceso |

### 7.2. Ruta

- **Path:** `/restaurante/inversion`
- **Sidebar:** Solo visible para usuarios con rol `admin`

### 7.3. Flujo de UI

1. El admin navega a `/restaurante/inversion`
2. Se cargan los bienes y el resumen en paralelo
3. **Dashboard** con 4 tarjetas: Estimado, Real, Diferencia (verde/rojo), Adquiridos
4. **Listado** de bienes agrupados por categoría; cada bien muestra nombre, costos, estado y acciones
5. **Crear:** botón "Agregar Bien" → modal con formulario completo
6. **Editar:** botón ✏️ en cada item → modal precargado
7. **Ver detalle:** clic en nombre → overlay con todos los campos y cálculo de ahorro/exceso
8. **Eliminar:** botón 🗑️ → diálogo de confirmación → DELETE request

### 7.4. Estados de UI

| Estado | Comportamiento |
|--------|---------------|
| **Loading** | Skeleton placeholders en cards y listado |
| **Empty** | Mensaje "No hay bienes registrados. Agrega el primer bien." + botón de acción |
| **Error** | Banner rojo con mensaje y botón "Cerrar" |
| **Submitting** | Botón deshabilitado + spinner en modal |
| **Success/Error toast** | Notificación auto-dismiss (3.5s) en esquina superior derecha |

### 7.5. Keyboard Handlers

| Tecla | Contexto | Acción |
|-------|----------|--------|
| `Enter` | Modal crear/editar | Submit formulario |
| `Escape` | Modal crear/editar | Cerrar modal |
| `Escape` | Confirmación eliminar | Cerrar diálogo |
| `Escape` | Vista detalle | Cerrar overlay |
| `Enter` | Confirmación eliminar | Confirmar eliminación |

---

## 8. Seguridad

- Todos los endpoints API protegidos con `require_role("admin")` (definido en `app/core/dependencies.py`)
- El frontend oculta la entrada del sidebar y redirige si el usuario no es admin
- Validación multi-tenant: `tenant_id` se extrae del header `X-Tenant-ID` y se cruza con el JWT
- Schemas Pydantic evitan inyección de campos no esperados en POST/PUT
- Check constraints a nivel de base de datos proporcionan una segunda capa de validación

---

## 9. Migración (Alembic)

**Migration ID:** `0013_investment_items`  
**Revises:** `4b731e20252e`

```python
revision = "0013_investment_items"
down_revision = "4b731e20252e"
```

### Upgrade

1. Crea tabla `investment_items` con todas las columnas y constraints
2. Crea índices `idx_investment_tenant_category` y `idx_investment_tenant_status`

### Downgrade

1. Elimina índices
2. Elimina tabla `investment_items`

---

## 10. Tests

**Archivo:** `tests/test_caso7_investment.py`  
**Cantidad:** 18 tests · 523 líneas  
**Framework:** pytest + unittest.mock (AsyncMock)

### Cobertura

| Test | Propósito |
|------|-----------|
| `test_create_item_success` | Creación exitosa con datos completos |
| `test_create_item_invalid_category` | Categoría inválida → HTTP 422 |
| `test_create_item_negative_cost` | Costo negativo → HTTP 422 |
| `test_create_item_invalid_status` | Status inválido → HTTP 422 |
| `test_create_item_default_status_pending` | Status por defecto es `pending` |
| `test_list_items` | Listar todos los bienes |
| `test_list_items_filter_by_category` | Filtrar listado por categoría |
| `test_list_items_filter_by_status` | Filtrar listado por estado |
| `test_get_item` | Obtener bien por ID |
| `test_get_item_not_found` | Bien inexistente → HTTP 404 |
| `test_update_item` | Actualizar costo real |
| `test_update_item_change_status` | Cambiar estado a `acquired` |
| `test_delete_item` | Eliminar bien existente |
| `test_delete_item_not_found` | Eliminar bien inexistente → HTTP 404 |
| `test_get_summary_with_items` | Resumen con 4 items (Escenario 6) |
| `test_get_summary_empty` | Resumen sin items → todo en cero |
| `test_all_valid_categories` | Parametrizado: 9 categorías válidas |
| `test_escenario_6_dashboard_multiple_items` | Escenario 6 del Gherkin: verificar totales |

---

## 11. Archivos del Módulo

```
apps/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   └── investment.py              ← Router con 6 endpoints
│   │   ├── services/
│   │   │   └── investment_service.py      ← Lógica de negocio
│   │   ├── schemas/
│   │   │   └── restaurant.py              ← InvestmentCreate/Update/Response/Summary
│   │   └── adapters/
│   │       ├── db/models/restaurant.py    ← Modelo ORM InvestmentItem
│   │       └── alembic/versions/
│   │           └── 0013_investment_items.py  ← Migración
│   └── tests/
│       └── test_caso7_investment.py       ← 18 tests
└── web/
    └── src/
        ├── pages/restaurante/
        │   └── InvestmentPage.tsx         ← Página principal con dashboard
        ├── components/restaurante/
        │   ├── InvestmentModal.tsx        ← Modal crear/editar
        │   └── InvestmentDetail.tsx       ← Vista detalle
        └── types/
            └── restaurant.ts              ← Interfaces TypeScript
```

---

## 12. Deuda Técnica

| ID | Descripción |
|----|-------------|
| **TD-005** | No hay edición masiva de bienes (ej: marcar varios como adquiridos) |
| **TD-006** | No hay exportación del listado a CSV/Excel |
| **TD-007** | No hay filtro combinado categoría + estado en el frontend (solo existe en API) |

---

## 13. Referencias

- [Gherkin: Caso 7 — Inversión Puesta en Marcha](/home/rony/.openclaw/workspace-orchestr/projects/iaas-ronsys/gherkins/caso7-inversion-puesta-marcha.md)
- [CHANGELOG — v0.6.0](/CHANGELOG.md#060--2026-05-27)
- [Arquitectura Frontend](arquitectura-frontend.md)
