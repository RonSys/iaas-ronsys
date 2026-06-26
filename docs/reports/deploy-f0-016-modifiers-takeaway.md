# Deploy Report — HU-F0-016: Modificadores en Take Away

**Fecha:** 2026-05-15  
**Agente:** DevOps Agent 🔧  
**Rama:** `fase0-real`  
**Commit base:** `c67507b` (fix: Fase 0 Real - agrupar items con modificadores distintos + precio correcto)

---

## Resumen

Deploy exitoso de HU-F0-016 que integra modificadores/adicionales (huevo frito, sin cebolla, con conchas, etc.) en el flujo de Take Away del módulo Restaurante.

## Cambios Desplegados

### Backend
| Archivo | Cambio |
|---------|--------|
| `apps/backend/app/services/restaurant_service.py` | Validación `max_select` + cálculo `price_adjustment` en modifiers |
| `apps/backend/app/routers/restaurant.py` | Ajustes menores de enrutamiento |

### Frontend
| Archivo | Cambio |
|---------|--------|
| `apps/web/src/pages/restaurante/TakeawayPage.tsx` | Integración de bottom sheet para modifiers |
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | **NUEVO** — Componente vaul bottom sheet |
| `apps/web/package.json` | Dependencia `vaul` agregada |

## Proceso de Deploy

### 1. Build
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache backend frontend
```
- **Backend:** Rebuild completo (sin cache de COPY . .) → Imagen `iaas-ronsys-backend:latest`
- **Frontend:** Rebuild completo → Imagen `iaas-ronsys-frontend:latest`
  - Bundle `TakeawayPage-B9iyLujm.js` (74.85 kB) incluye código de ModifierBottomSheet + vaul

### 2. Restart
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate backend frontend
```
- Contenedores recreados y healthy en ~25s

### 3. Migraciones
- Alembic estaba en `0006_scenarios`, migraciones `0007` y `0008` ya aplicadas (tablas existentes)
- Stamped: `alembic stamp 0008_product_categories_pricing` → head alcanzado

### 4. Hotfix: Columna `notes` en `takeaway_orders`
- El modelo SQLAlchemy (`TakeawayOrder`) incluye `notes: Mapped[str | None] = mapped_column(Text)`
- La tabla en PostgreSQL no tenía esa columna
- Solución: `ALTER TABLE takeaway_orders ADD COLUMN notes TEXT;`

## Verificación

### Health Checks
| Servicio | Estado |
|----------|--------|
| Backend (`:8000/health`) | ✅ `{"status":"ok"}` |
| Frontend (`:80`) | ✅ HTTP 200 |
| PostgreSQL | ✅ Healthy |
| Redis | ✅ Healthy |
| RabbitMQ | ✅ Healthy |

### API — Flujo Take Away con Modifiers

#### Crear pedido con modifiers
```json
POST /api/v1/restaurant/takeaway
{
  "customer_name": "Cliente Test HU-F0-016",
  "items": [
    {"menu_item_id": 10, "quantity": 1, "modifiers": [{"id": 3}]},
    {"menu_item_id": 12, "quantity": 1, "modifiers": [{"id": 7}]}
  ]
}
```

**Resultado:**
| Item | Precio Base | Modifier | Ajuste | Subtotal |
|------|------------|----------|--------|----------|
| Ceviche Clásico | S/28.00 | Con conchas (id=3) | +S/5.00 | S/33.00 ✅ |
| Lomo Saltado | S/35.00 | Huevo frito (id=7) | +S/3.00 | S/38.00 ✅ |
| **TOTAL** | | | | **S/71.00 ✅** |

#### Validación `max_select`
```json
// Huevo frito tiene max_select=3, se enviaron 4
POST ... {"modifiers": [{"id":7},{"id":7},{"id":7},{"id":7}]}
```
**Respuesta:** `422 — "Modificador 'Huevo frito': máximo 3, enviados 4"` ✅

#### Pickup
```json
PATCH /api/v1/restaurant/takeaway/1/pickup
```
**Respuesta:** `{"id": 1, "status": "picked_up"}` ✅

### Frontend
- Bundle `TakeawayPage-B9iyLujm.js` contiene:
  - Código de `ModifierBottomSheet` ✅
  - Librería `vaul` (2 referencias) ✅
  - Integración de modifiers en TakeawayPage ✅

## Modifiers Disponibles

| Menu Item | Modifier | Price Adjustment | Max Select |
|-----------|----------|-----------------|------------|
| Ceviche Clásico (10) | Sin cebolla (1) | S/0.00 | 1 |
| Ceviche Clásico (10) | Extra limón (2) | S/0.00 | 1 |
| Ceviche Clásico (10) | Con conchas (3) | S/5.00 | 1 |
| Lomo Saltado (12) | Término medio (4) | S/0.00 | 1 |
| Lomo Saltado (12) | Término 3/4 (5) | S/0.00 | 1 |
| Lomo Saltado (12) | Sin cebolla (6) | S/0.00 | 1 |
| Lomo Saltado (12) | Huevo frito (7) | S/3.00 | 3 |

## Issues Encontrados y Resueltos

| Issue | Solución |
|-------|----------|
| Docker COPY cache no invalidaba con `build` normal | Usar `--no-cache` para forzar rebuild |
| Columna `notes` faltante en `takeaway_orders` | `ALTER TABLE ADD COLUMN notes TEXT` |
| Migraciones 0007/0008 ya aplicadas pero no stamped | `alembic stamp 0008_product_categories_pricing` |
| Token JWT expira en 15 min | Renovar token para tests consecutivos |

## Estado Final

| Indicador | Valor |
|-----------|-------|
| Build Backend | ✅ Success |
| Build Frontend | ✅ Success |
| Health Checks | ✅ All healthy |
| API Modifiers Flow | ✅ Funcionando |
| max_select Validation | ✅ Funcionando |
| Pickup Flow | ✅ Funcionando |
| Frontend Bundle | ✅ ModifierBottomSheet + vaul incluidos |

---

**Veredicto:** ✅ **DEPLOY EXITOSO** — HU-F0-016 operativa en producción.
