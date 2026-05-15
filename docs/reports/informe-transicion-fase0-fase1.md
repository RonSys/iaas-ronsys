# Informe: Transición de Fase 0 → Fase 1 con Deudas Técnicas

**Fecha:** 2026-05-15
**Agentes consultados:** Architecture Agent 🏗️, PO Agent 📋
**Solicitado por:** Ron

---

## Pregunta 1: ¿Es recomendable pasar a la Fase 1 con las deudas de Fase 0?

**Sí. Es recomendable y necesario.** Ambos agentes coinciden.

### Razones

1. **Ninguna DT-F0 bloquea técnicamente el trabajo de Fase 1.** Son deudas funcionales (UX, validaciones, features faltantes). Fase 1 es refactoring arquitectónico puro (D-01 a D-09 del Plan v3 §7).
2. **Fase 1 no agrega features** — no compite con las DT-F0 por recursos.
3. **Fase 1 habilita Fase 2** — que resolverá naturalmente varias DT-F0.
4. **El riesgo de NO hacer Fase 1 es mayor** — construir Fase 2 sobre arquitectura quebrada cuesta 2-3× más corregir después.

> ⚠️ Plan v3 §15.1.2: *"No comenzar Fase 2 sin completar Fase 1 al 100%. El costo de construir módulos nuevos sobre una arquitectura quebrada sería muy alto."*

---

## Pregunta 2: ¿Curar durante Fases 1-4 (pre-v1.0) o postergar a v1.1+?

**Mixto.** Se propusieron 2 ajustes de timing:

| DT-F0 | Antes | Ahora → | Razón |
|-------|:-----:|:-------:|-------|
| **DT-F0-006** 🔼 | v1.9 | **Fase 1** | Bug user-facing: botón "Crear" de Promos no funciona. Esfuerzo 0.3d. |
| **DT-F0-004** 🔼 | v1.2 | **Fase 2** | Cancelar comanda + notificar mesero. Sinergia con tarea D-05 del mismo código. |

### Resto sin cambios

| DT-F0 | Versión | Justificación |
|-------|:-------:|---------------|
| DT-F0-001 | v1.2 | UX táctil — requiere tablet física para validar |
| DT-F0-002 | v1.2 | Kanban filtra items — mejora UX, no bloquea |
| DT-F0-003 | v1.2 | Validación contable — motor ya funciona |
| DT-F0-005 | v2.x | Módulo Pérdidas — requiere recetas (Fase 2) |
| DT-F0-007 | v1.2 | Promociones — pulido de edge cases |
| DT-F0-008 | v3/v3.5 | IA + roles cocina — visión futuro |
| DT-F0-009 | v1.1 | Ferretería catálogo — post-Fase 4 |

### Condición del Architecture Agent 🏗️

> **Validar Ferretería (DT-F0-009) al cierre de Fase 1.** Fase 1 refactoriza `core/sales/` e `core/inventory/` — los dominios que Ferretería usa. No cerrar Fase 1 sin verificar que Ferretería sigue funcionando.

---

## Roadmap resultante

```
Fase 0   →  MVP entregado ✅ (9 deudas funcionales registradas)
Fase 1   →  Arquitectura corregida + DT-F0-006 (bug Promociones)
Fase 2   →  Cocina/Delivery/Compras + DT-F0-004 (cancelar comanda) + DT-F0-005 (pérdidas)
Fase 3   →  Inventario completo + Finanzas
Fase 4   →  Reportes + Infraestructura + CI/CD
─── v1.0 🚀 Release ───
v1.1     →  DT-F0-009 (validar catálogo ferretería)
v1.2     →  DT-F0-001, 002, 003, 007 (pulido UX + validaciones)
v2.x     →  DT-F0-005 completo (módulo pérdidas)
v3.x     →  DT-F0-008 (IA + niveles cocina)
```

---

*Fuente: Architecture Agent 🏗️ + PO Agent 📋*
*Archivo relacionado: `docs/backlog/deuda-tecnica-fase0.md`*
