# 📜 Archivo Histórico — Documentos de mayo 2026

Extraído de la rama legacy `ron/simulador-financiero` (commit `7eb49ca`, 14-may-2026)
el 2026-08-10, por decisión de Ron (opción 2: extraer docs valiosos sin tocar código ni specs).

> ⚠️ **Los specs SDD en `docs/specs/` son la fuente de verdad vigente** (Spec Anchor).
> Estos documentos son **referencia histórica** del desarrollo inicial — algunos escenarios,
> criterios y rutas ya cambiaron con la evolución posterior del sistema.

## Contenido

| Documento | Qué es | Valor |
|---|---|---|
| `gherkin-fase1-erp.md` | Historias Gherkin de la Fase 1 (núcleo contable-financiero) | Referencia de requerimientos iniciales |
| `gherkin-fase2-erp.md` | Historias Gherkin de la Fase 2 (módulos comerciales) | Referencia de requerimientos iniciales |
| `diagramas-acceso-auth.md` | Diseño completo del flujo de autenticación (JWT, refresh, lockout, OAuth2) | El más valioso: arquitectura auth documentada |
| `cuadros-seguimiento-ERP.txt` | Gantt de deuda técnica + seguimiento por fases (mayo 2026) | Contexto de deuda histórica |
| `informe-cierre-fase1.md` | Informe de cierre de Fase 1 (280 tests, módulos implementados) | Registro del hito 14-may |

## Notas

- **No se extrajo** `gherkin-fase0-erp.md` de la rama: la versión de `main` es la evolucionada
  con el desarrollo real (16 HU) — la de la rama era la planificación original (15 HU) y archivar
  ambas confundiría.
- **Ports hexagonales descartados** (`core/sales/ports.py`, `core/inventory/ports.py`): fueron un
  experimento de arquitectura de la rama que `main` reemplazó por el enfoque actual (servicios
  directos + puertos solo en `core/accounting/`). No se extraen — documentado aquí para registro.
- `ve.md` / `ve.txt` de la rama eran copias temporales del Plan Integral — basura, no se extrajeron.
- La password de la BD QA mencionada en `informe-cierre-fase1.md` fue enmascarada (`***`).

## Estado

- Rama `ron/simulador-financiero`: permanece en `origin` como registro histórico (sin merge).
- Decisión registrada: opción 2 (extracción selectiva) — código y specs intactos.
