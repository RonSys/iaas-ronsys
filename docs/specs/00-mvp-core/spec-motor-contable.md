# SPEC — Motor Contable y Estados Financieros (MVP Core)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción, migraciones `0001` + `0004`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: todos los tenants; motor de dominio puro (hexagonal)
- **Fecha**: 2026-08-10 (spec generada por análisis del código; funcionalidad desde MVP)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

El ERP necesita contabilizar automáticamente todas las operaciones (ventas, compras, recetas,
delivery) con partida doble, generar estados financieros (PyG, Balance, BCSS), ratios con
semáforo, y proyecciones de caja. El motor vive en dominio puro (`core/accounting/`) sin
dependencias de infraestructura (patrón hexagonal: `ports.py` define contratos).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Motor de asientos (partida doble, validación balance) | `app/core/accounting/engine.py` (1,053 ln) | ✅ Implementado |
| Kárdex (motor puro, promedio ponderado) | `app/core/accounting/kardex.py` | ✅ Implementado (spec propia) |
| Proyección de flujo de caja | `app/core/accounting/cashflow.py` | ✅ Implementado |
| Ratios financieros con semáforo 🟢🟡🔴 | `app/core/accounting/ratios.py` | ✅ Implementado |
| Estados financieros (BCSS/PyG/Balance) | `app/core/accounting/statements.py` | ✅ Implementado |
| Puertos (interfaces abstractas) | `app/core/accounting/ports.py` | ✅ Implementado |
| Entidades de BD | `app/adapters/db/models/accounting.py` (Company, Account, JournalEntry(+Line), Product, KardexMovement, CashflowProjection) | ✅ Implementado |
| Migraciones | `0001_initial_setup.py` + `0004_cashflow_projections.py` | ✅ Aplicadas en prod |
| Endpoints `/api/accounting/*` + kárdex | `app/routers/accounting.py` (1,031 ln) | ✅ Desplegados |
| Asiento automático en venta | `app/services/sales_service.py` `_generate_journal_entry` (L720) | ✅ Desplegado |

### 2.2 Motor contable (engine.py) — capacidades verificadas

- **Enums**: `AccountNature` (deudora/acreedora), `AccountCategory`, `EntryType`, `MovementType`.
- **`JournalEntry`**: líneas con partida doble, `is_balanced()` (debe == haber).
- **`generate_opening_entries`** (L377): asientos de apertura desde variables de inversión (activos, pasivos, patrimonio, capital).
- **`generate_monthly_entries`** (L516): asientos mensuales por 12 meses (ventas, compras, sueldos, servicios, depreciación, intereses, impuesto a la renta 29.5%).
- **`_generate_depreciation_entry`** (L687): depreciación de activos fijos.
- **`generate_closing_entry`** (L751): cierre de ejercicio (resultado → patrimonio).
- **`build_general_ledger`** (L816): mayor general desde asientos.
- **Estados financieros** (`statements.py`): `FinancialStatementService.run_simulation` → PyG (ingresos/gastos/resultado), Balance (Activo = Pasivo + Patrimonio, `is_balanced()`), BCSS (sumas y saldos, `is_balanced()`).
- **Ratios** (`ratios.py`): 9 ratios — Liquidez, Prueba Ácida, Endeudamiento, Margen Neto, ROE, ROA, Cobertura de Intereses, Rotación de Inventario, Payback; cada uno con rango objetivo y semáforo.
- **Cashflow** (`cashflow.py`): `CashflowService.generate_projection` (12 meses), `calculate_real` (vs. real desde kárdex/caja), `compare` (desviaciones %), alertas.

### 2.3 Endpoints (verificados en `accounting.py`)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/accounting/setup` | Correr simulación completa (InvestmentInput → FinancialReportResponse) |
| GET | `/api/accounting/bcss` | Balance de Comprobación de Sumas y Saldos |
| GET | `/api/accounting/pyg` | Estado de Resultados |
| GET | `/api/accounting/balance` | Balance General |
| GET | `/api/accounting/ratios` | Ratios con semáforo |
| POST | `/api/accounting/transaction` | Registrar transacción contable manual |
| POST | `/api/accounting/validate` | Validar consistencia contable |
| GET | `/api/accounting/cashflow` | Proyección/flujo de caja |
| POST | `/api/accounting/kardex/products` | Registrar producto (kárdex) |
| POST | `/api/accounting/kardex/entry` | Entrada (compra) → recalcula promedio |
| POST | `/api/accounting/kardex/exit` | Salida (venta/merma) |
| GET | `/api/accounting/kardex/products` | Listar productos + valorización |
| GET | `/api/accounting/kardex/inventory/summary` | Resumen de inventario valorizado |
| POST | `/api/accounting/kardex/warehouse-close` | Cierre de almacén |

---

## 3. Fase P — Contratos y modelo de datos

### 3.1 Tablas principales (migraciones 0001 + 0004)

```sql
accounts (id, company_id, code, name, nature, category, is_active)
journal_entries (id, company_id, entry_number, date, description, total_debit, total_credit, status)
journal_entry_lines (id, journal_entry_id, account_id, debit, credit)
cashflow_projections (id, company_id, month, income, expenses, net, ...)
```

### 3.2 Flujo de asiento automático de venta (verificado en sales_service)

```
SaleService.create_sale → _generate_journal_entry:
  1. Determina cuenta de ingreso (según business_type: restaurant/ferretería)
  2. Crea líneas: debe (caja/banco) = total con IGV; haber (ventas) = base; haber (IGV) = impuesto
  3. Persiste JournalEntry + JournalEntryLines; linkea sale.journal_entry_id
```

### 3.3 Criterios de aceptación (verificados)

- CA1: todo asiento generado cumple partida doble (debe == haber). ✅
- CA2: Balance General balancea (Activo = Pasivo + Patrimonio). ✅
- CA3: BCSS balancea (sumas deudoras == sumas acreedoras). ✅
- CA4: simulación de 12 meses genera asientos de apertura, mensuales y cierre. ✅
- CA5: ratios calculan con semáforo y rangos configurables. ✅
- CA6: cashflow proyectado vs. real con alertas de desviación. ✅
- CA7: venta genera asiento automático (HU-F2-006). ✅

---

## 4. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Motor de asientos | `app/core/accounting/engine.py` | §2.2 |
| Estados financieros | `app/core/accounting/statements.py` | §2.2 |
| Ratios | `app/core/accounting/ratios.py` | §2.2 |
| Cashflow | `app/core/accounting/cashflow.py` | §2.2 |
| Puertos | `app/core/accounting/ports.py` | §2.1 |
| Endpoints | `app/routers/accounting.py` | §2.3 |
| Asiento de venta | `app/services/sales_service.py` `_generate_journal_entry` | §3.2 |
| Modelos | `app/adapters/db/models/accounting.py` | §3.1 |
| Migraciones | `0001`, `0004` | §3.1 |

> ⚠️ Si cambias el plan de cuentas, la generación de asientos, ratios o estados financieros, **actualiza esta spec** (Spec Anchor).
