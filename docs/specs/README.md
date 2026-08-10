# 📚 IaaS-RonSys — Specs por Fase (SDD / Spec Anchor)

> **Framework**: SDD — **Spec Anchor**: la especificación está sincronizada con el código;
> cualquier cambio en uno debe reflejarse en el otro.
> **Guía base**: `~/investigacion/02-desarrollo-herramientas/20260730_Que-es-SDD-Spec-Driven-Development.md`
> **Fecha de generación**: 2026-08-10 · Verificadas contra código + BD prod (migración `0016_delivery`)

---

## 🗂️ Índice por Fase

### Fase 00 — MVP Core (núcleo del ERP)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [spec-auth-multitenant.md](00-mvp-core/spec-auth-multitenant.md) — Auth JWT + roles + tenant + seguridad | 🟢 IMPLEMENTADA | 0002, 0014 (rol superadmin) | `/api/auth`, `/api/admin` |
| [spec-motor-contable.md](00-mvp-core/spec-motor-contable.md) — Motor contable, estados financieros, ratios, cashflow | 🟢 IMPLEMENTADA | 0001, 0004 | `/api/accounting` |
| [spec-kardex-inventario.md](00-mvp-core/spec-kardex-inventario.md) — Kárdex promedio ponderado + seriales | 🟢 IMPLEMENTADA | 0001, 0008-0010 | `/api/accounting/kardex` |
| [spec-simulador-financiero.md](00-mvp-core/spec-simulador-financiero.md) — Simulador y escenarios | 🟢 IMPLEMENTADA | 0006 | `/api/simulator` |

### Fase 01 — Restaurante + Ferretería (Fase 0 Real)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [spec-restaurante-pos.md](01-fase0-restaurante-ferreteria/spec-restaurante-pos.md) — Mesas, pedidos, cocina, takeaway, promociones, POS | 🟢 IMPLEMENTADA | 0005, 0007, 0011, 0015 | `/api/v1/restaurant`, `/api/sales` |
| [spec-inventario-ferreteria.md](01-fase0-restaurante-ferreteria/spec-inventario-ferreteria.md) — Categorías, productos, seriales, garantías | 🟢 IMPLEMENTADA | 0008, 0009, 0010 | `/api/v1/inventory` |
| [spec-superadmin-tenants.md](01-fase0-restaurante-ferreteria/spec-superadmin-tenants.md) — Consola global empresas/usuarios/dashboard | 🟢 IMPLEMENTADA | 0014 | `/api/superadmin` |
| [spec-inversiones.md](01-fase0-restaurante-ferreteria/spec-inversiones.md) — Items de inversión y reportes | 🟢 IMPLEMENTADA | 0013 | `/api/v1/restaurant/investment` |

### Fase 02 — Recetas y Costos Variables (Specs 01/02 históricas)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [01-spec-recetas-productos-v0.2.md](02-recetas-costos/01-spec-recetas-productos-v0.2.md) — Recetas por plato + explosión kárdex | 🟢 APROBADA/IMPLEMENTADA | 0012, 0015 | `/api/v1/restaurant/menu/{id}/recipe` |
| [02-spec-costos-variables-v0.1.md](02-recetas-costos/02-spec-costos-variables-v0.1.md) — Costos variables (promedio ponderado) | 🟢 IMPLEMENTADA | — (usa kárdex) | `/api/accounting/kardex/*` |

### Fase 03 — Delivery / Dark Kitchen (Spec 03)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [03-spec-delivery-dark-kitchen-v0.1.md](03-delivery/03-spec-delivery-dark-kitchen-v0.1.md) — Delivery nocturno, zonas, repartidores, campañas, menú público | 🟢 APROBADA/IMPLEMENTADA | 0016 (+companies.slug) | `/api/v1/delivery`, `/api/public`, `/api/settings` |

### Fase 99 — Infraestructura / DevOps

| Spec | Estado | Migraciones | Artefactos |
|---|---|---|---|
| [spec-infra-cicd.md](99-infra-devops/spec-infra-cicd.md) — Docker, deploy, GH Actions, monitoreo, e2e | 🟢 IMPLEMENTADA | — | compose, deploy.sh, workflows, e2e |

---

## 🔗 Matriz Spec Anchor (spec ↔ código ↔ migración ↔ frontend)

> **Regla**: si modificas código de un módulo, actualiza su spec; si modificas la spec, ajusta el código.
> Estado verificado 2026-08-10 contra `main` + BD prod (head `0016_delivery`).

| Dominio | Spec | Backend | Migración | Frontend | E2E |
|---|---|---|---|---|---|
| Auth/tenant | 00-auth | `routers/auth.py`, `routers/admin.py`, `core/security.py`, `core/dependencies.py` | 0002 | Login, SetupWizard | login |
| Contabilidad | 00-contable | `routers/accounting.py`, `core/accounting/*` | 0001, 0004 | Cashflow, Reports | reportes |
| Kárdex | 00-kardex | `routers/accounting.py:386`, `services/kardex_service.py`, `core/accounting/kardex.py` | 0001, 0008-0010 | Kardex, ProductsPage | kardex |
| Simulador | 00-simulador | `routers/simulator.py`, `services/simulator_service.py` | 0006 | Simulator | simulador |
| Restaurante/POS | 01-restaurante | `routers/restaurant.py`, `routers/sales.py`, `services/restaurant_service.py`, `services/sales_service.py` | 0005, 0007, 0011, 0015 | TablesMap, MenuPage, KitchenKanban, Takeaway, Pos, SalesNew/List | dashboard ⚠️ sin e2e POS/mesas |
| Inventario ferretería | 01-inventario | `routers/inventory.py`, `services/inventory_service.py` | 0008-0010 | ProductsPage, CategoriesPage | ⚠️ sin e2e inventario |
| Superadmin | 01-superadmin | `routers/superadmin.py` | 0014 | superadmin/* | ⚠️ sin e2e |
| Inversiones | 01-inversiones | `routers/investment.py`, `services/investment_service.py` | 0013 | InvestmentPage, Reports | — |
| Recetas | 02-recetas | `services/recipe_explosion.py`, `restaurant_service.py:1377` | 0012, 0015 | RecipeModal (MenuPage) | — |
| Delivery | 03-delivery | `routers/delivery.py`, `routers/public.py`, `services/delivery_service.py` | 0016 | DeliveryPage, PublicMenuPage | delivery-landing, delivery-staff |
| Infra/CI | 99-infra | compose, deploy.sh, `.github/workflows/`, `routers/health.py` | — | — | configs prod |

---

## ⚠️ Estado de Código No Operativo / No Desplegado (verificado 2026-08-10)

| Artefacto | Estado | Nota |
|---|---|---|
| `apps/backend/app/core/agents/` | ☠️ Código muerto | 0 imports en `app/` — NO operativo, excluido de specs |
| `apps/mobile/` | 🕳️ Vacío | Solo `.gitkeep` — no existe app móvil |
| Rama `ron/simulador-financiero` | 🧊 Legacy | 2 commits sin mergear (`780e740`, `7eb49ca` "Fase 1/2 deploy") — no desplegados |
| Worktrees `faint-haze`, `unique-thumb` | 🧊 Inactivos | En commit `6bfd61a` — sin commits propios sobre main |

---

## ✅ Cómo mantener el Spec Anchor (checklist)

1. **Antes de implementar** un cambio → lee la spec del módulo; si el cambio altera contrato, actualiza la spec **en el mismo PR/commit**.
2. **Después de implementar** → verifica que la spec refleja el código real (endpoints, modelo de datos, flujos).
3. **Migraciones nuevas** → actualizar la sección "Migraciones" de la spec correspondiente.
4. **E2E nuevos** → actualizar la columna E2E de la matriz de este README.
5. **Features nuevas que cruzan módulos** → crear spec nueva numerada por fase (04-, 05-, ...) siguiendo el formato de las existentes (Estado / Decisiones / Fase R / Fase P / Matriz).
