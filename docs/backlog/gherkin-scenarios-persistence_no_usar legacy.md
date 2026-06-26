# Backlog Gherkin — Persistencia de Escenarios del Simulador

**Proyecto:** IaaS-RonSys  
**Origen:** [scenarios-persistence.md](../reports/scenarios-persistence.md)  
**Generado por:** PO Agent 📋  
**Fecha:** 2026-05-12  
**Total Historias:** 2 (1 backend + 1 frontend)

---

## HU-SIM-001: Persistencia de escenarios del Simulador — Backend

**Como** usuario del Simulador Financiero  
**Quiero** guardar, listar, consultar, actualizar y eliminar escenarios de simulación en la base de datos  
**Para** no perder mis escenarios al recargar la página y poder compararlos entre sesiones.

### Criterios de aceptación

#### Guardar escenario
- [ ] Given un usuario autenticado con menos de 4 escenarios guardados When hago `POST /api/simulator/scenarios` con `name: "Realista"`, `input_data` (InvestmentInput completo) y `results` (cache del FinancialReport) Then el escenario se persiste en la tabla `scenarios`, se retorna 201 con `id`, `name`, `input_data`, `results`, `created_at` y `updated_at`
- [ ] Given un usuario autenticado que YA tiene 4 escenarios guardados When hago `POST /api/simulator/scenarios` Then responde 409 Conflict con mensaje "Máximo 4 escenarios por empresa. Elimina uno antes de guardar."
- [ ] Given un request sin `name` o con `name` vacío When hago POST Then responde 422 con error de validación
- [ ] Given un request sin `input_data` When hago POST Then responde 422 con error de validación
- [ ] Given un request sin autenticación When hago POST Then responde 401

#### Listar escenarios
- [ ] Given un usuario autenticado con 2 escenarios guardados When hago `GET /api/simulator/scenarios` Then responde 200 con `scenarios: [...]` (ordenados por `created_at` DESC), `total: 2` y `max_allowed: 4`
- [ ] Given un usuario sin escenarios guardados When hago GET Then responde 200 con `scenarios: []`, `total: 0`, `max_allowed: 4`
- [ ] Given un usuario autenticado en company A When hago GET Then solo veo escenarios de mi company, no de otras

#### Obtener detalle
- [ ] Given un escenario existente de mi company When hago `GET /api/simulator/scenarios/{id}` Then responde 200 con el `ScenarioResponse` completo incluyendo `input_data` y `results`
- [ ] Given un `id` que no existe When hago GET Then responde 404 con "Escenario no encontrado"
- [ ] Given un escenario de otra company When intento acceder por id Then responde 404 (no se filtra información de otros tenants)

#### Actualizar escenario
- [ ] Given un escenario existente When hago `PUT /api/simulator/scenarios/{id}` con `name: "Optimista v2"` Then el nombre se actualiza y `updated_at` cambia
- [ ] Given un escenario existente When hago PUT con nuevos `results` (re-cálculo de simulación) Then los resultados cacheados se actualizan sin tocar `input_data`
- [ ] Given un escenario existente When hago PUT con `input_data` modificado Then el input se actualiza (útil si el usuario re-simula con otros sliders)

#### Eliminar escenario
- [ ] Given un escenario existente When hago `DELETE /api/simulator/scenarios/{id}` Then responde 200 con `{status: "deleted", id: N}` y el escenario desaparece de la lista
- [ ] Given un `id` que no existe When hago DELETE Then responde 404 con "Escenario no encontrado"

#### Migración
- [ ] Given la migración ejecutada When verifico la DB Then existe tabla `scenarios` con: id, company_id (FK CASCADE), user_id (FK SET NULL), name VARCHAR(100), input_data JSONB, results JSONB, created_at, updated_at
- [ ] Given la migración ejecutada When verifico Then existe índice `idx_scenarios_company` sobre `company_id`

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** Auth (JWT + X-Tenant-ID existentes), `get_db` (AsyncSession existente), Alembic (0005_sales_tables o anterior)  
**Ficha técnica de referencia:** scenarios-persistence.md §2-§8  
**Notas técnicas:**
- Modelo ORM en `adapters/db/models/simulator.py` (nuevo)
- Schemas Pydantic en `schemas/simulator.py` (nuevo): `ScenarioCreate`, `ScenarioUpdate`, `ScenarioResponse`, `ScenarioListResponse`
- Service en `services/simulator_service.py` (nuevo): `ScenarioService` con validación de límite 4
- Router en `routers/simulator.py` (nuevo): prefijo `/api/simulator`
- Registrar router en `main.py`
- Constante `MAX_SCENARIOS = 4` por company (no por usuario)
- `user_id` nullable con `ON DELETE SET NULL` para que el escenario sobreviva si se elimina el usuario
- `results` es nullable — permite crear escenario sin haber ejecutado simulación

---

## HU-SIM-002: Persistencia de escenarios del Simulador — Frontend

**Como** usuario del Simulador Financiero  
**Quiero** que mis escenarios se persistan automáticamente al backend y se carguen al abrir la página  
**Para** no perder mi trabajo al recargar (F5) y poder gestionar mis escenarios guardados.

### Criterios de aceptación

#### Hook useScenarios
- [ ] Given el componente Simulator se monta estando autenticado When el hook `useScenarios` se inicializa Then ejecuta `GET /api/simulator/scenarios` y carga los escenarios existentes en el estado
- [ ] Given no hay sesión autenticada When el hook se inicializa Then no hace fetch y `scenarios` es array vacío
- [ ] Given el backend responde con error (500, timeout) When el fetch ocurre Then el hook expone `error` con mensaje descriptivo y `loading` pasa a false

#### Guardar escenario
- [ ] Given el usuario tiene resultados de simulación visibles When presiona "Guardar Escenario" Then se llama `POST /api/simulator/scenarios` con `name`, `input_data` (InvestmentInput actual) y `results` (FinancialReport cache), y el escenario aparece en la lista
- [ ] Given ya existen 4 escenarios guardados When intenta guardar Then se muestra mensaje de error "Máximo 4 escenarios" y NO se agrega a la lista
- [ ] Given la llamada POST falla (409, 422, 500) When presiona guardar Then se muestra el error y el escenario NO desaparece de la UI (no hay pérdida de datos)

#### Actualizar escenario
- [ ] Given un escenario guardado When el usuario re-simula con otros sliders y guarda cambios Then se llama `PUT /api/simulator/scenarios/{id}` actualizando `name` y/o `results`, y la lista refleja los cambios

#### Eliminar escenario
- [ ] Given un escenario en la lista When el usuario presiona el botón de eliminar y confirma Then se llama `DELETE /api/simulator/scenarios/{id}`, el escenario desaparece de la lista y el contador se actualiza
- [ ] Given la llamada DELETE falla When intenta eliminar Then el escenario permanece en la lista y se muestra el error

#### Indicadores de estado
- [ ] Given los escenarios se están cargando When `loading = true` Then la sección de escenarios muestra un skeleton o spinner
- [ ] Given ocurrió un error de red When `error` no es null Then se muestra un mensaje de error con opción de reintentar
- [ ] Given hay 4 escenarios guardados When se muestra la UI Then aparece un indicador "4/4 escenarios" y el botón de guardar se deshabilita o muestra tooltip

#### Refactor Simulator.tsx
- [ ] Given el usuario guarda un escenario, recarga la página (F5) y vuelve a la sección Simulador When la página carga Then los escenarios guardados anteriormente siguen visibles en la lista (persistencia real)
- [ ] Given el refactor está completo When reviso el código Then NO quedan referencias al `useState<ScenarioSnapshot[]>` viejo — toda la gestión pasa por `useScenarios()`

**Prioridad:** P1  
**Esfuerzo estimado:** 1.5 días  
**Dependencias:** HU-SIM-001 (endpoints deben existir), AuthContext + API client (existentes)  
**Ficha técnica de referencia:** scenarios-persistence.md §9  
**Notas técnicas:**
- Nuevo archivo `types/simulator.ts`: `ScenarioData`, `ScenarioCreate`, `ScenarioUpdate`
- Nuevo archivo `hooks/useScenarios.ts`: hook con `fetchScenarios`, `saveScenario`, `updateScenario`, `deleteScenario`, estados `loading`/`error`
- Refactor `pages/Simulator.tsx`: reemplazar `useState<ScenarioSnapshot[]>` por `useScenarios()`
- El hook debe usar los helpers de API existentes (`apiGet`, `apiPost`, `apiPut`, `apiDelete`)
- Tests unitarios con Jest para el hook (mock de API client) y para el componente Simulator
- No alterar la lógica de simulación financiera — solo cambiar la capa de persistencia

---

## Resumen

| Historia | Capa | Endpoints/Componentes | Esfuerzo |
|----------|------|----------------------|----------|
| HU-SIM-001 | Backend | 1 tabla + 5 endpoints REST | 1.5 días |
| HU-SIM-002 | Frontend | Hook + types + refactor Simulator.tsx | 1.5 días |
| **TOTAL** | — | — | **3 días** |

### Dependencia lineal
```
HU-SIM-001 (backend) → HU-SIM-002 (frontend)
```
El backend debe estar listo antes de que el frontend conecte los endpoints reales. El frontend puede empezar con mocks mientras el backend se completa.

### Reglas de negocio
- Máximo 4 escenarios por company
- `results` se cachea para evitar re-ejecutar simulación al cargar
- `input_data` guarda el InvestmentInput completo (no solo sliders)
- No se modifica la lógica de simulación existente

---

*Documento generado por PO Agent con base en la Ficha Técnica scenarios-persistence.md (2026-05-12).*
