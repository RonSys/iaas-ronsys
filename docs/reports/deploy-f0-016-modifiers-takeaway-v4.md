# Deploy Report — HU-F0-016 v4: Hotfix Bottom Sheet Colapso por Re-render

**Fecha:** 2026-05-15  
**Agente:** DevOps Agent 🔧  
**Rama:** `fase0-real`  
**Commit base:** `c67507b`

---

## Resumen

Hotfix v4 para HU-F0-016: el bottom sheet de Vaul (Radix Dialog) se cerraba al hacer clic en un modifier porque React re-renderizaba sincrónicamente durante el evento `pointerdown`, reemplazando el DOM antes del `pointerup`. Radix no encontraba el elemento original y lo interpretaba como "outside click".

## Bug

| Problema | Causa raíz |
|----------|-----------|
| Bottom sheet se cerraba al hacer clic en cualquier modifier | `useState` → `setQuantities` disparaba re-render síncrono durante `pointerdown`. Radix Dialog perdía la referencia al elemento clickeado entre `pointerdown` y `pointerup` y lo interpretaba como outside click. |

## Fix

| Archivo | Cambio |
|---------|--------|
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | Migración de `useState` a `useRef` + `requestAnimationFrame` para diferir el re-render 1 frame después del evento |

**Patrón aplicado:**
- `useRef` para almacenar `quantitiesRef` (sin triggers de re-render)
- `requestAnimationFrame` para diferir la actualización de UI al siguiente frame
- `cancelAnimationFrame` en cleanup para evitar memory leaks

## Proceso de Deploy

### 1. Build
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend
```
→ `iaas-ronsys-frontend:latest` (solo frontend)

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
| rAF/useRef fix en bundle | ✅ 3 referencias confirmadas |
| Backend sin cambios | ✅ Healthy |

## Estado Final

| Indicador | Valor |
|-----------|-------|
| Build Frontend | ✅ Success |
| Health Checks | ✅ All healthy |
| Fix en bundle | ✅ `requestAnimationFrame` + `useRef` + `rAFRef` presentes |

---

**Veredicto:** ✅ **HOTFIX DESPLEGADO** — Bottom sheet permanece abierto durante selección de modifiers. Re-render diferido vía rAF.
