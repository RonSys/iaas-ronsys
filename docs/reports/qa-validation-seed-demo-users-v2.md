# QA Validation Report — seed_db.py Fix re-validación

**Fecha:** 2025-07-16  
**QA Agent:** 🧪 QA Agent  
**Historia:** Fix de seed_db.py — modelo ProductCategory + company_id→tenant_id  
**Branch/Commit:** Verificado en workspace actual  
**Veredicto Final:** ⚠️ **PENDIENTE DE FIX MENOR** (usuarios ✅, categorías ❌)

---

## Resumen Ejecutivo

| Suite | Resultado | Detalle |
|-------|:---------:|---------|
| Backend pytest | ✅ | **151/151** tests pasan |
| seed_db.py — Empresas | ✅ | 2 empresas creadas/verificadas |
| seed_db.py — Simulación | ✅ | 152 asientos, balance cuadrado |
| seed_db.py — Usuarios demo | ✅ | 4 usuarios, 2 creados, 2 existentes |
| seed_db.py — Categorías | ❌ | Schema mismatch ORM vs DB |
| seed_db.py — Productos | ⏸️ | No se llega (categorías falla antes) |
| Login mesero1 | ✅ | `mesero123`, operator, El Segoviano |
| Login cocinero1 | ✅ | `cocinero123`, operator, El Segoviano |
| Login ferretero | ✅ | `ferreteria123`, admin, Ferretería (hardware) |
| Login admin | ✅ | `admin123`, admin |
| Idempotencia usuarios | ✅ | "Usuarios demo ya existen — omitiendo" |
| Idempotencia empresas | ✅ | "Ferretería ya existe" |

---

## 1. Tests — 151/151 ✅

```
======================= 151 passed, 2 warnings in 2.28s ========================
```

Sin regresiones.

---

## 2. seed_db.py — Ejecución completa ✅ (hasta usuarios)

### 2.1 Empresas ✅

```
🏢 Empresa ya existe: El Segoviano
🏢 Ferretería creada: Ferretería El Segoviano (ID: 6)
```

- Nueva Ferretería con RUC `20777555552` creada ✅
- El Segoviano existente verificado ✅

### 2.2 Simulación ✅

```
📊 Simulación completada: 152 asientos
   Ventas: S/ 300,000.00
   Utilidad Neta: S/ 51,606.00
   Balance: ✅ Cuadra
```

### 2.3 Usuarios demo ✅

```
👤 Usuarios demo: 2 creados, 2 ya existían
   ✅ mesero1@elsegoviano.pe (operator) → mesero123
   ✅ cocinero1@elsegoviano.pe (operator) → cocinero123
```

| Email | Password | Estado | Rol | Empresa | ID |
|-------|----------|:------:|------|---------|:--:|
| admin@elsegoviano.pe | admin123 | Existente | admin | Admin Tenant* | 1 |
| ferretero@elsegoviano.pe | ferreteria123 | Existente | admin | Ferretería El Segoviano | 7 |
| mesero1@elsegoviano.pe | mesero123 | **NUEVO** | operator | El Segoviano | 13 |
| cocinero1@elsegoviano.pe | cocinero123 | **NUEVO** | operator | El Segoviano | 14 |

*\*En deployment fresco seed_db.py asigna `tenant_id=company_id` (El Segoviano).*

### 2.4 Login de nuevos usuarios ✅

```
mesero1@elsegoviano.pe   → role=operator, company_id=3 (El Segoviano, restaurant) ✅
cocinero1@elsegoviano.pe → role=operator, company_id=3 (El Segoviano, restaurant) ✅
```

---

## 3. ❌ Schema Mismatch: Categorías

### Error

```
sqlalchemy.exc.ProgrammingError: column product_categories.description does not exist
```

### Causa raíz

El modelo ORM `ProductCategory` tiene columnas que **no existen** en la tabla real de BD:

| Columna | En ORM | En DB (migration 0008) |
|---------|:------:|:----------------------:|
| id | ✅ | ✅ |
| tenant_id | ✅ | ✅ |
| name | ✅ | ✅ |
| description | ✅ `Text` | ❌ |
| parent_id | ✅ FK | ❌ |
| active | ✅ Boolean | ❌ |
| sort_order | ✅ Integer | ❌ |
| created_at | ✅ | ✅ |
| updated_at | ✅ | ✅ |

### DB real (5 columnas)

```
product_categories: id, tenant_id, name, created_at, updated_at
```

### ORM (9 columnas)

```python
# accounting.py
class ProductCategory(Base):
    __tablename__ = "product_categories"
    id: Mapped[int]
    tenant_id: Mapped[int]
    name: Mapped[str] = String(50)
    description: Mapped[str | None] = Text          # ❌ no existe
    parent_id: Mapped[int | None]                   # ❌ no existe
    active: Mapped[bool]                            # ❌ no existe  
    sort_order: Mapped[int]                         # ❌ no existe
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### Fix requerido

**Opción A (recomendada):** Eliminar columnas que no existen del ORM
```python
# Mantener solo lo que migration 0008 creó
class ProductCategory(Base):
    __tablename__ = "product_categories"
    id: Mapped[int]
    tenant_id: Mapped[int]
    name: Mapped[str] = String(50)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

Y eliminar `description` references de `_get_categories()` en seed_db.py.

**Opción B:** Crear nueva migration para agregar las 4 columnas faltantes a la tabla.

---

## 4. Idempotencia ✅

Segunda ejecución de seed_db.py:

```
🏢 Empresa ya existe: El Segoviano
🏢 Ferretería ya existe: Ferretería El Segoviano (ID: 6)
👤 Usuarios demo ya existen — omitiendo
```

- Sin duplicados (11 usuarios total) ✅
- Sin empresas duplicadas (4 total) ✅
- Falla en categorías por el mismo schema mismatch ✅ (esperado, consistente)

---

## 5. Criterios de Aceptación

| # | Criterio | Estado |
|---|----------|:------:|
| 1 | Tests pasan (151) | ✅ |
| 2 | seed_db.py corre sin errores | ⚠️ Parcial (llega hasta usuarios) |
| 3 | 4 usuarios creados con contraseñas correctas | ✅ |
| 4 | 11 categorías creadas (6 restaurant + 5 hardware) | ❌ Schema mismatch |
| 5 | 5 productos asignados a categorías | ⏸️ No se llega |
| 6 | Idempotente | ✅ (usuarios + empresas) |

---

## Veredicto

⚠️ **PENDIENTE DE FIX MENOR** — La sección de usuarios demo funciona perfectamente. La sección de categorías falla por un schema mismatch entre el modelo ORM `ProductCategory` y la tabla real `product_categories` (migration 0008).

**Lo que funciona:**
- ✅ 151 tests pasan
- ✅ seed_db.py crea/verifica las 2 empresas
- ✅ 4 usuarios demo creados correctamente
- ✅ Login funciona para todos
- ✅ Idempotente (usuarios y empresas)

**Lo que falta:**
- ❌ `ProductCategory` ORM tiene 4 columnas que no existen en la DB (`description`, `parent_id`, `active`, `sort_order`)
- ❌ La sección de categorías/productos de seed_db.py no se ejecuta

**Fix sugerido:** Alinear el modelo ORM con la tabla real (solo 5 columnas: id, tenant_id, name, created_at, updated_at) y remover `description` de `_get_categories()`.

---

*Reporte generado por QA Agent 🧪 — IaaS-RonSys Quality Gate*
