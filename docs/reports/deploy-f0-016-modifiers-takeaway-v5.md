# Deploy Report — HU-F0-016 v5: Hotfix data-vaul-no-drag

**Fecha:** 2026-05-15  
**Agente:** DevOps Agent 🔧  
**Rama:** `fase0-real`  
**Commit base:** `c67507b`

---

## Resumen

Hotfix v5: el drawer de modifiers se cerraba al tocar opciones en tablets táctiles porque vaul detectaba el micro-movimiento natural del dedo como drag de cierre.

## Bug

| Problema | Causa |
|----------|-------|
| Bottom sheet se cerraba al tocar cualquier opción en tablet | Vaul mide la velocidad del toque. El micro-movimiento natural del dedo al tocar elementos interactivos superaba el threshold de cierre de vaul. |

## Fix

| Archivo | Cambio |
|---------|--------|
| `apps/web/src/components/restaurante/ModifierBottomSheet.tsx` | `data-vaul-no-drag` agregado en 6 puntos: botones −/+, labels checkbox/radio, contenedor lista, y CTA |

El atributo `data-vaul-no-drag` le dice a vaul que ignore esos elementos para drag detection. El swipe-to-dismiss sigue funcionando desde el handle bar y bordes del drawer.

## Proceso de Deploy

### 1. Build
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend
```
→ Solo frontend

### 2. Restart
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate frontend
```
→ Healthy

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
| `data-vaul-no-drag` en bundle | ✅ 5 ocurrencias |
| Backend sin cambios | ✅ Healthy |

## Estado Final

| Indicador | Valor |
|-----------|-------|
| Build Frontend | ✅ Success |
| Health Checks | ✅ All healthy |

---

**Veredicto:** ✅ **HOTFIX DESPLEGADO** — Toques en elementos interactivos ya no cierran el drawer. Swipe-to-dismiss sigue funcional desde handle bar.
