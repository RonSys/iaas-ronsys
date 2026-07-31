# 📋 Reporte QA — IaaS-RonSys (Recetas + Costos Variables) — 2026-07-31

- **Fecha**: 2026-07-31 · **Tenant**: 1 (Admin Tenant, restaurant) · **User**: admin@elsegoviano.pe
- **Script**: [`../scripts/qa/test_suite.py`](../scripts/qa/test_suite.py) — reutilizable (`python3 scripts/qa/test_suite.py`)
- **Cobertura**: Spec 01 (recetas + explosión + costeo) · Spec 02 (costos variables + kárdex DB-aware + POS search) · UI/UX (sidebar, RecipeModal, Kardex preview, auto-refresh token)

---

## Resultados: 10/10 PASS

| # | Test | Resultado | Evidencia clave |
|---|---|---|---|
| T1 | Login + auth | ✅ PASS | Token OK, JWT `company_id=1` |
| T2 | CRUD recetas + validación unidades | ✅ **PASS** | GET 200 (5 ing.) · PUT 200 (costo 4.58) · PUT con unidad inválida → **400** y la receta NO se sobrescribe (fix F1) |
| T3 | Explosión al vender | ✅ PASS | Venta OK → deltas exactos (pescado −0.15, limón −2, cebolla −0.05, camote −0.10, choclo −0.05) + kárdex "Consumo por receta" + stocks restaurados |
| T4 | Stock insuficiente | ✅ PASS | Venta de 200 ceviches → **409** "Stock insuficiente… 30.0 kg, disponible 19.7" + **0 movimientos parciales** |
| T5 | Costeo + COGS | ✅ PASS | Costo receta reportado **4.58 = Σ ingredientes** (recosteado con pescado @20.03) · asiento COGS **50:4.58** |
| T6 | Costos variables (entrada DB) | ✅ PASS | QA-TMP01: 0 → entrada 10@18 → entrada 10@22 → **balance 20.00 @ 20.00**, persistido en BD, cleanup OK |
| T7 | Multi-tenant | ✅ PASS | X-Tenant-ID=3 con token tenant 1 → **403 "Access denied to this tenant"** · menu 999 → 404 · /db/entry inexistente → 400 |
| T8 | POS search | ✅ PASS | inventory `?search=pescado` → 2 resultados con retail · kardex `?search=` → 2 resultados |
| T9 | UI bundle | ✅ PASS | Banner éxito, "Puesta en Marcha", "Nuevo promedio estimado", auto-refresh — presentes en assets desplegados |
| T10 | Salud general | ✅ PASS | **40/40 containers Up**, endpoints 200 (iaas, segoviano, eyfimport, stratify, smart, openclaw), `alembic_version=0015_recipes_sale_items` |

---

## Hallazgos

### F1 — (RESUELTO) `save_recipe` no validaba la unidad del ingrediente (D4)
- **Estado**: ✅ **CORREGIDO 2026-07-31** (aprobado por Ron). `RecipesService.save_recipe` ahora valida **antes de sobrescribir**: productos del tenant (404) y unidades **normalizadas** (D4) vía `normalize_unit()` compartido con el precheck de explosión. Unidad inválida → 400 con mensaje claro y la receta existente queda intacta; se guarda la unidad canónica del producto.
- **Verificación**: suite completa **10/10 PASS** (T2 ahora PASS: 400 + receta intacta + regresión 200 con unidades correctas).

### F2 — Observaciones del proceso QA (no son fallas del producto)
- Durante el desarrollo de la suite se corrigieron 4 bugs del propio script (orden de headers en el helper HTTP — simulaba mal otro tenant; restauración de la receta para idempotencia entre corridas; aserción de `reference_type` inexistente en el modelo de respuesta → se valida por `concept`; pre-cleanup del producto temporal). La suite final es idempotente.
- **Residuo trazable de las corridas**: ventas QA (sale_id 21-23, concepto "...(QA)") + movimientos de compensación ("Compensación QA") en kárdex; producto `QA-TMP01` desactivado (invisible). No se alteraron stocks ni promedios de los datos demo.

---

## Recomendaciones post-QA

1. ~~Fix F1~~ ✅ **RESUELTO** (validación de unidades en save_recipe, 10/10 PASS).
2. Revisión final de Ron de los cambios sin commitear (ciclo RPI #1 + spec 02 + UI/UX + QA + F1) y **commit** cuando apruebe.
3. Opcional: `searchKardexProducts` (hook `useSales.search`) quedó funcional pero sin consumidores — candidato a eliminar o a conectar el POS a él.

---

## Comandos de referencia

```bash
# Ejecutar la suite QA (idempotente, no destructiva)
cd /mnt/disco_ssd/projectos/IaaS-RonSys
python3 scripts/qa/test_suite.py

# Checklist manual para Ron
docs/manuales/checklist-qa-manual-2026-07-31.md
```
