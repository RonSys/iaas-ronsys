# Deploy Report — HU-F0-016 v2: Modificadores (Tipos Visuales)

**Fecha:** 2026-05-15  
**Agente:** DevOps Agent 🔧  
**Rama:** `fase0-real`  
**Commit base:** `c67507b`

---

## Resumen

Deploy de HU-F0-016 v2, que agrega **tres tipos visuales de modificadores** en el bottom sheet: cuantificables (−/+), booleanos (checkbox) y grupos excluyentes (radio buttons). Incluye fix en backend para soportar `quantity` en modifiers cuantificables.

## Cambios Desplegados

### Backend
| Archivo | Cambio |
|---------|--------|
| `apps/backend/app/services/restaurant_service.py` | Soporte para `quantity` en modifiers: `mod_counts[mid] += max(1, mod.get("quantity", 1))` (OrderService + TakeawayService) |
| `apps/backend/tests/test_restaurant_takeaway.py` | **NUEVO** — 11 tests unitarios |

### Frontend
| Archivo | Cambio |
|---------|--------|
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | **386 líneas** — 3 tipos: cuantificables (−/+), booleanos (checkbox), radio groups |
| `apps/web/src/pages/restaurante/TakeawayPage.tsx` | Ajustes para cantidad en modifiers |

## Proceso de Deploy

### 1. Build
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache backend frontend
```
- Backend: rebuild completo con fix de `quantity` → `iaas-ronsys-backend:latest`
- Frontend: rebuild completo con 3 tipos visuales → `iaas-ronsys-frontend:latest`

### 2. Restart
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate backend
```
- Backend recreado y healthy en ~15s
- Frontend permaneció running (ya estaba actualizado)

### 3. Hotfix: `quantity` en modifiers
- **Problema:** El backend contaba cada entrada de modifier como 1, ignorando el campo `quantity`
- **Solución:** Cambiar `mod_counts[mid] = mod_counts.get(mid, 0) + 1` → `mod_counts[mid] = mod_counts.get(mid, 0) + max(1, mod.get("quantity", 1))`
- **Archivos afectados:** `restaurant_service.py` líneas 355 (OrderService) y 692 (TakeawayService)

## Verificación

### Health Checks
| Servicio | Estado |
|----------|--------|
| Backend (`:8000/health`) | ✅ `{"status":"ok"}` |
| Frontend (`:80`) | ✅ HTTP 200 |
| PostgreSQL | ✅ Healthy |
| Redis | ✅ Healthy |

### API — Modificadores Cuantificables

| Prueba | Entrada | Resultado | Veredicto |
|--------|---------|-----------|:---------:|
| 2 huevos fritos (quant) | `{"id":7,"quantity":2}` | S/41.00 (35 + 3×2) | ✅ |
| 3 huevos fritos (max) | `{"id":7,"quantity":3}` | S/44.00 (35 + 3×3) | ✅ |
| 4 huevos fritos (excede) | `{"id":7,"quantity":4}` | 422: "máximo 3, enviados 4" | ✅ |
| 1 huevo frito (default) | `{"id":7}` | S/38.00 (35 + 3×1) | ✅ |

### Frontend
- Bundle `TakeawayPage-*.js` contiene 5+ referencias a `groupModifiers`, `selectRadio`, tipos de modifier ✅
- Componente `ModifierBottomSheet.tsx` (386 líneas) con soporte para 3 tipos visuales ✅

## Tipos de Modificadores Implementados

| Tipo | UI | Ejemplo | Lógica |
|------|----|---------|--------|
| 🔢 **Cuantificable** | Botones −/+ | Huevo frito (max 3) | `modifier_group_id = NULL`, `max_select > 1` |
| ☑️ **Booleano** | Checkbox | Sin cebolla | `max_select = 1`, sin grupo |
| 🔘 **Grupo excluyente** | Radio buttons | Término (medio, 3/4, cocido) | Mismo `modifier_group_id` |

## Issues Encontrados y Resueltos

| Issue | Solución |
|-------|----------|
| Backend ignoraba `quantity` en modifiers | Fix en `restaurant_service.py` (2 ubicaciones): usar `max(1, mod.get("quantity", 1))` |
| Rebuild necesario post-fix | Solo backend requirió rebuild; frontend ya estaba actualizado |

## Estado Final

| Indicador | Valor |
|-----------|-------|
| Build Backend | ✅ Success |
| Build Frontend | ✅ Success |
| Health Checks | ✅ All healthy |
| Quantifiable modifiers | ✅ Funcionando |
| max_select c/ quantity | ✅ Funcionando |
| Frontend 3 tipos visuales | ✅ Incluidos en bundle |
| Manual actualizado | ✅ Sección 1.1 + 3.2 + 3.3 + 3.6 + FAQ |

---

**Veredicto:** ✅ **DEPLOY EXITOSO** — HU-F0-016 v2 operativa en producción con 3 tipos de modificadores y fix de `quantity`.
