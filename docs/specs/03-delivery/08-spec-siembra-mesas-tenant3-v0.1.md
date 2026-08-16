# SPEC 08 — Siembra de Mesas/Secciones Reales del Tenant Operativo (F6 Agenda)

- **Estado**: 🟢 **EJECUTADA (2026-08-16 01:45 UTC)** — D2/D3/D4 completados y verificados por Jarvis (BD + evidencias). Tenant 1 normalizado (3 secciones, 19 mesas, agenda 399 slots) · tenant 3 limpio (entidad sin data) · E2E 21/21 en monitor.
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Fecha**: 2026-08-16
- **Framework**: SDD / Spec Anchor — esta spec se sincroniza con el código y la BD
- **Depende de**: **F6 (spec 07 — Agenda de Citas, 🟢 APROBADA Y EN PROD 2026-08-16)** — la agenda necesita mesas reales del tenant operativo para mostrar disponibilidad y crear citas
- **Autorización**: ✅ OK EXPLÍCITO DE RON (2026-08-16 01:07 UTC) para sembrar mesas/secciones reales, bajo CHECKPOINT DE PRODUCCIÓN R1-R2 (solo Ron autoriza prod; DevOps ejecuta con orden que incluya el OK)

---

## 1. Contexto y objetivo

### 1.1 Por qué
F6 (Agenda de Citas) está desplegada en prod con E2E 18/18, pero el **tenant 3 (El Segoviano) no tiene mesas sembradas** — el E2E creó mesas fixture temporales y las eliminó. Para que el local opere la agenda de verdad (disponibilidad real por mesa, reservas, espejo `tables.status='reserved'` en el mapa del salón), el tenant operativo necesita su **inventario real de mesas y secciones**.

### 1.2 Objetivo (MVP)
1. Sembrar en prod las **secciones reales** del local (Salón, Terraza, VIP — según layout confirmado por Ron).
2. Sembrar las **mesas reales** (número, capacidad, sección, estado inicial `available`).
3. Verificar integración con F6: `GET /api/v1/appointments/availability` devuelve las mesas reales; el mapa POS las muestra.
4. **No tocar otros tenants** (mesas de tenant 1 y tenant 5 intactas).

---

## 2. Fase R — Hallazgos de la investigación (verificado en BD prod 2026-08-16 01:10 UTC)

### 2.1 ⚠️ Discrepancia crítica de tenant — VEREDICTO (investigación 2026-08-16 01:20 UTC)

**El tenant operativo real es el 1, NO el 3.** Evidencia verificada en BD prod + specs + seeds:

| Evidencia | Tenant 1 ("Admin Tenant", slug `el-segoviano`) | Tenant 3 ("El Segoviano", sin slug) |
|---|---|---|
| Slug `el-segoviano` (menú público `menu/el-segoviano`) | ✅ **SÍ** | ❌ NULL |
| Mesas | ✅ **21** (secciones sucias) | ❌ 0 |
| Secciones (`restaurant_sections`) | ✅ 10 | ❌ 0 |
| Menú (`menu_items`) | ✅ 11 | ❌ 0 |
| Zonas delivery | ✅ 1 | ❌ 0 |
| Ventas 30d | ✅ **47** | ❌ 0 |
| Pedidos delivery (DLV-) | ✅ **38** | ❌ 0 |
| `settings.voice_ai` (F3) | ✅ enabled=true (greeting El Segoviano) | ❌ — |
| `settings.whatsapp` (F1) | ✅ presente (enabled=false, sin Meta) | ❌ — |
| `settings.delivery` / `branding` / `tax_config` / `features` | ✅ | ❌ — |
| `settings.calls` (F2) | ❌ — | ✅ enabled=true (DID +5115551234 placeholder, ext 100/101) |
| Usuarios staff | ✅ admin/mesero/cocinero | ✅ admincevicheria/mesero1/cocinero1 (seed) |

**Lectura:** el negocio real (menú, mesas, ventas, delivery, voz IA F3) vive **100% en tenant 1**. El tenant 3 es un tenant legacy/secundario que SOLO tiene `settings.calls` configurado (F2, DID placeholder) — probablemente creado para el E2E de central telefónica. La hipótesis de Ron ("solo tenant 3 tenga data") **no se sostiene con la evidencia**: tenant 1 tiene toda la operación real.

**Sobre el requisito "tenant-id=3" en QA/E2E de F6:** fue un requisito de fixtures para las PRUEBAS (evitar ensuciar el tenant real), no la realidad operativa. De hecho el E2E F6 usó mesas fixture tenant 3 que luego eliminó (0 residuales). Los specs 04/05/06/07 dicen "Alcance: tenant 1 (El Segoviano)" y el E2E F3 usa `--tenant-id 1` (el negocio real).

**Conclusión D1 (REVISADA):** la siembra/verificación de mesas para la Agenda de Citas debe ir a **tenant 1** (ya tiene las 21 mesas → normalizar/limpiar y verificar agenda), NO a tenant 3. El tenant 3 no tiene data real que operar.

### 2.2 Layout documentado (referencia — pendiente confirmación D2)

El manual de usuario (`docs/manuales/manual-usuario.md` §Secciones) documenta un escenario didáctico del local:

| Sección | Mesas | Descripción |
|---|---|---|
| Terraza | 6 | Mesas al aire libre, vista al mar |
| Salón Principal | 10 | Zona interior del restaurante |
| VIP | 4 | Zona exclusiva para eventos |
| **Total** | **20** | |

> ⚠️ **No se asume como layout real**: es un escenario del manual. **D2**: Ron confirma el layout real del salón (secciones + nº de mesas + capacidades) — o autoriza usar el del manual.

### 2.3 Mesas existentes en tenant 1 (21) — estado actual

| Sección (nombre en BD) | Mesas | Nota |
|---|---|---|
| Salón Principal | 3 (5, 6, 7) | nombres inconsistentes |
| Terraza | 4 (1, 2, 3, 4) | — |
| Salón VIP | 1 (100) | — |
| VIP | 4 (10, 11, 12, 24, 50 = 5 en realidad) | — |
| Zions vip | 1 (104) | typo en BD |
| be | 1 (9) | typo |
| terraza (minúscula) | 2 (1000, 105) | duplicada en nombre |
| vip (minúscula) | 1 (14) | duplicada |
| zona vip | 1 (31) | duplicada |
| Prueba | 1 (101) | mesa de prueba |
| sin sección | 1 (30) | NULL |

> Las 21 mesas del tenant 1 tienen **nombres de sección inconsistentes** (typos, duplicados, mayúsculas mezcladas, una "Prueba"). **D3**: ¿se limpian/normalizan las secciones del tenant 1, o la siembra es solo para tenant 3 y el tenant 1 queda como está?

### 2.4 Infraestructura de siembra disponible

| Mecanismo | Ubicación | Estado |
|---|---|---|
| `POST /api/sections` + `POST /api/restaurant/tables` (o endpoint de mesas) | API existente F0 | ✅ Usado por el E2E F6 (creó mesas fixture tenant 3 vía API y las eliminó con 204) |
| Seed histórico `seed_clean.py` (tenant 2, layout SALA/AFUERA/TERRAZA) | `apps/backend/scripts/seed_clean.py` | Referencia de formato, NO aplica a prod |
| Backup previo | `backups/iaas_ronsys_pre_f6_deploy_20260816.dump` | ✅ Disponible (patrón F3/F5) |

---

## 3. Diseño

### 3.1 Decisiones (D1 resuelta por evidencia; D2–D3 pendientes de Ron)

| # | Decisión | Estado | Impacto |
|---|---|---|---|
| D1 | **Tenant objetivo** | ✅ **RESUELTA por evidencia: tenant 1** (tiene la operación real). Tenant 3 = legacy sin data real | Define el plan completo |
| D2 | **Normalización tenant 1** | ✅ **APROBADA (Ron 01:23 UTC)**: normalizar secciones sucias (typos "Zions vip"/"be"/"zona vip", duplicados VIP/vip y Terraza/terraza) + **eliminar mesa "Prueba" (101) y la sin sección (30)** + verificar agenda F6 | Alcance del trabajo en tenant 1 |
| D3 | **Limpieza tenant 3** | ✅ **APROBADA (Ron 01:23 UTC)**: **limpiar TODA la data del tenant 3** (usuarios seed, call_records, query_logs, settings.calls, appointments, lo que exista) — **conservar el tenant como entidad** (companies id=3), su data no. Para E2E desde cero | Alcance de limpieza en tenant 3 |
| D4 | **E2E en prod + monitor** | ✅ **APROBADA (Ron 01:23 UTC)**: E2E en PRODUCCIÓN visible en el **monitor del servidor** (modo `--demo` con pausas, navegador abierto en DISPLAY :0) | Requisito de demo en vivo |

### 3.2 Plan de ejecución APROBADO (Ron 01:23 UTC) — secuencia oficial

```
0. Backup BD prod (obligatorio, patrón F3/F5) → backups/iaas_ronsys_pre_mesas_<fecha>.dump (verificado tamaño > 0)

1. NORMALIZACIÓN TENANT 1 (D2):
   a. Secciones: unificar nombres (typos "Zions vip"→VIP, "be"→?, "zona vip"→VIP, duplicados VIP/vip, Terraza/terraza)
   b. Mesas: eliminar "Prueba" (101) y la sin sección (30) — verificar que no tengan ventas/pedidos asociados antes
   c. Verificación agenda F6: GET availability?date=<mañana>&guests=2 → slots reales (mesas del tenant 1)

2. LIMPIEZA TENANT 3 (D3) — dejar entidad, sin data:
   a. Inventariar TODA la data del tenant 3 (ver §3.3 tabla de registros)
   b. Eliminar: appointments, call_records, query_logs, settings.calls (reset), usuarios seed, lo que exista
   c. Verificación: 0 registros residuales por tabla del tenant 3 (solo companies id=3 intacta)

3. E2E EN CALIENTE VISIBLE EN MONITOR (D4):
   a. Navegador abierto en el monitor del servidor (DISPLAY :0), modo --demo con pausas visibles
   b. Flujo tenant 1: agenda → availability mesas reales → crear cita → confirmar (espejo reserved) → cancelar → limpiar
   c. Flujo tenant 3: desde cero (data limpia) → validar disponibilidad
   d. Evidencias en docs/reports/evidencias-f6-e2e-prod/ (screenshots + resumen)

4. Docs: bitácora spec 08 + informe ejecutivo (si aplica) + reporte final a Ron
   (hash backup, secciones tenant 1 antes/después, tablas/registros eliminados del tenant 3, resumen E2E, confirmación monitor)
```

### 3.3 Validaciones / reglas

| # | Regla |
|---|---|
| R1 | **No duplicar**: antes de crear, verificar que no existan mesas/secciones con el mismo nombre en el tenant objetivo (siembra idempotente) |
| R2 | **Aislamiento multi-tenant**: toda creación con el tenant correcto (X-Tenant-ID / auth del tenant objetivo); nunca tocar mesas de otro tenant |
| R3 | **Backup previo** obligatorio (patrón F3/F5) — sin backup verificado → abortar |
| R4 | **Checkpoint R1-R2**: ejecución solo con el OK explícito de Ron ya recibido (2026-08-16 01:07 UTC) — sin necesidad de re-pedir si D1–D3 se confirman en el mismo hilo |
| R5 | **Sin datos inventados**: el layout se siembra según D2 confirmado por Ron; nada de mesas inventadas |
| R6 | **Estado inicial**: mesas `available` (la agenda las gestiona; el espejo D1 de F6 las pasa a `reserved` al confirmar citas) |

### 3.4 Criterios de aceptación

| # | Caso | Resultado esperado |
|---|---|---|
| CA-SM-1 | Secciones sembradas en tenant objetivo | Listadas vía API + UI (mapa POS) con nombres correctos según D2 |
| CA-SM-2 | Mesas sembradas con capacidad correcta | Count coincide con D2; estado inicial `available` |
| CA-SM-3 | Disponibilidad F6 operativa | `GET /api/v1/appointments/availability` devuelve las mesas reales del tenant (slots > 0) |
| CA-SM-4 | Ciclo cita completo (smoke) | Crear → confirmar → espejo `reserved` → cancelar → espejo `available` → limpieza (patrón E2E F6 18/18) |
| CA-SM-5 | No duplicación | Re-ejecutar siembra → 0 duplicados (idempotente) |
| CA-SM-6 | Otros tenants intactos | Count mesas/secciones de tenants no objetivo = antes (verificado en BD) |
| CA-SM-7 | Backup verificado | Dump pre-siembra existe, tamaño > 0, listado OK |

---

## 4. Plan de ejecución (solo tras D1–D3)

1. **Confirmación Ron**: D1 tenant objetivo · D2 layout · D3 limpieza (vía chatbot dashboard).
2. **Coordinar DevOps** (`agent:devops:main`): backup → siembra → verificación F6 → limpieza smoke → reporte.
3. **Jarvis verifica** de forma independiente (BD + API + UI) y actualiza docs.
4. **Reporte a Ron** vía chatbot dashboard.

**Esfuerzo estimado:** ~1-2 h (siembra vía API + verificación + docs), más tiempo de confirmación de Ron.

---

## 5. Bitácora Spec Anchor (sync spec ↔ código/BD)

- **2026-08-16 01:07 UTC (v0.1)**: borrador inicial — siembra de mesas/secciones reales para F6.
- **2026-08-16 01:20 UTC (v0.2 — VEREDICTO D1 RESUELTO)**: investigación completa contra BD prod + specs + seeds + E2E: **el tenant operativo real es el 1** (slug `el-segoviano`, 21 mesas, 11 menú items, 1 zona delivery, 47 ventas/38 pedidos 30d, voice_ai enabled, whatsapp config, delivery/branding/tax_config) — el tenant 3 solo tiene `settings.calls` (F2 placeholder) y usuarios seed, sin data real. La hipótesis inicial ("solo tenant 3") **no se sostiene**; el requisito tenant-id=3 era de fixtures de prueba F6. Plan actualizado → normalizar/verificar mesas del **tenant 1**. Estado → 🟡 BORRADOR.
- **2026-08-16 01:23 UTC (v0.3 — D2/D3/D4 APROBADOS por Ron)**: plan de ejecución finalizado con OK explícito: D2 normalizar secciones tenant 1 (typos/duplicados) + eliminar mesas Prueba (101) y sin sección (30); D3 limpiar TODA la data del tenant 3 (conservar entidad companies id=3); D4 E2E en prod visible en monitor (--demo).
- **2026-08-16 01:45 UTC (v0.4 — EJECUTADA, verificación Jarvis independiente)**: backup `iaas_ronsys_pre_mesas_20260816.dump` (313KB, SHA-256 `3c0b798b...`) · tenant 1 normalizado: **10 secciones → 3** (Terraza 6 mesas · Salón Principal 4 · VIP 9); eliminadas mesa "Prueba" (101) y sin sección (30) (0 refs en sales/appointments/pos_sessions; 1 kitchen_order cancelada 2026-05-15 conservada como historial con table_id=NULL por FK ON DELETE SET NULL) · agenda F6 tenant 1: availability **399 slots** reales · **tenant 3 limpio**: 0 residuales en 24 tablas tenant-scoped (users, refresh_tokens, journal_entries+lines, kardex_movements, products, categories, settings→{}) conservando `companies` id=3 · E2E en caliente **21/21 en MONITOR** (DISPLAY :0, --demo) — flujo A tenant 1 (crear→confirmar→espejo reserved→cancelar→espejo available→limpiar) + flujo B tenant 3 desde cero (availability 0, agenda 0, usuario temp eliminado) · evidencias 7 PNG + resumen.json · estado post: appointments=0, query_logs 13 intactos, alembic 0021, contenedores healthy, tenants 1/5 intactos · hallazgo menor: `GET /api/v1/restaurant/tables/{id}` → 500 (MissingGreenlet pre-existente, deuda técnica escalada). Estado → 🟢 **EJECUTADA** — verificado por Jarvis (BD + evidencias).
- **2026-08-16 01:25–01:40 UTC (EJECUCIÓN COMPLETA — DevOps)**:
  - Backup previo: `backups/iaas_ronsys_pre_mesas_20260816.dump` (313 KB, sha256 `3c0b798b…`, 39 secciones TABLE DATA OK).
  - **D2 tenant 1**: 10 secciones sucias → 3 limpias (Terraza 6 mesas · Salón Principal 4 · VIP 9). Mesas Prueba (number 101, id 21) y sin sección (number 30, id 23) eliminadas (0 refs en kitchen_orders activas/sales/appointments; 1 kitchen_order cancelada 2026-05-15 quedó con table_id NULL por FK SET NULL — registrada). Availability F6: 399 slots con mesas reales.
  - **D3 tenant 3**: eliminados 37 refresh_tokens, 3040 journal_entry_lines, 5 kardex_movements, 1520 journal_entries, 5 products, 6 product_categories, 3 users; settings → `{}`. Entidad companies id=3 conservada. Verificación: 0 residuales en las 24 tablas tenant-scoped.
  - **D4 E2E en monitor**: `DISPLAY :0` modo `--demo` (pausas visibles) — 21/21 OK: flujo A tenant 1 (crear→confirmar→espejo reserved→cancelar→espejo available→limpiar) + flujo B tenant 3 desde cero (0 mesas/0 citas + usuario temp eliminado). Evidencias: 7 PNG + resumen.json.
  - Estado final: appointments=0 (todos los tenants), mesas t1=19, secciones t1=3, users t3=0, companies id=3 con settings `{}`, alembic `0021_appointments`. Otros servicios/dominios intactos.
- Estado: 🟢 **APROBADA Y EJECUTADA (2026-08-16 01:40 UTC)** — bitácora completa en `docs/reports/deploy-f6-agenda-citas-2026-08-16.md`.

---

## 6. Referencias

- Spec 07 (F6 Agenda de Citas): `docs/specs/03-delivery/07-spec-agenda-citas-v0.1.md` (🟢 APROBADA Y EN PROD)
- Manual de usuario §Secciones (layout didáctico Terraza 6/Salón 10/VIP 4): `docs/manuales/manual-usuario.md`
- Credenciales por tenant: `docs/manuales/credenciales-por-tenant.md`
- Pipeline §CHECKPOINT DE PRODUCCIÓN (R1-R4): `docs/pipeline-orquestador.md`
- Deploy F6 + E2E 18/18: `docs/reports/deploy-f6-agenda-citas-2026-08-16.md`
- Backup disponible: `backups/iaas_ronsys_pre_f6_deploy_20260816.dump`
