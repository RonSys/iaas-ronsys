# Deploy Report — HU-F0-016 v3: Hotfix Bottom Sheet Cierre

**Fecha:** 2026-05-15  
**Agente:** DevOps Agent 🔧  
**Rama:** `fase0-real`  
**Commit base:** `c67507b`

---

## Resumen

Hotfix para HU-F0-016 v3: el bottom sheet de modifiers se cerraba al seleccionar un modificador porque todos los modifiers sin `modifier_group_id` se agrupaban bajo la clave `null` y se trataban como radio group.

## Bug

| Problema | Causa |
|----------|-------|
| Bottom sheet se cerraba al seleccionar un modifier | `groupModifiers()` agrupaba todos los modifiers sin `modifier_group_id` bajo la clave `null`, tratándolos como grupo excluyente. Al seleccionar uno, ejecutaba `onSelect()` y cerraba el sheet. |

## Fix

| Archivo | Cambio |
|---------|--------|
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | Cada modifier sin grupo recibe clave única `single_${mod.id}` en vez de agruparse bajo `null` + `stopPropagation` en handlers |

```typescript
// Antes: todos los modifiers sin grupo se agrupaban bajo null
const key = mod.modifier_group_id ?? null;

// Ahora: clave única por modifier
: `single_${mod.id}`;
```

## Proceso de Deploy

### 1. Build
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend
```
→ `iaas-ronsys-frontend:latest` (solo frontend, backend sin cambios)

### 2. Restart
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate frontend
```
→ Recreado y healthy

### 3. QA Pre-deploy
| Check | Resultado |
|-------|:---------:|
| `npx tsc --noEmit` | ✅ Limpio |
| `npx vite build` | ✅ 765 módulos |
| Tests frontend | ✅ 138 |

## Verificación

| Prueba | Resultado |
|--------|:---------:|
| Health check frontend | ✅ HTTP 200 |
| Fix `single_` en bundle | ✅ Confirmado |
| Backend sin cambios | ✅ Healthy |

## Estado Final

| Indicador | Valor |
|-----------|-------|
| Build Frontend | ✅ Success |
| Health Checks | ✅ All healthy |
| Fix en bundle | ✅ `single_` key presente |

---

**Veredicto:** ✅ **HOTFIX DESPLEGADO** — El bottom sheet ya no se cierra al seleccionar modifiers individuales.
