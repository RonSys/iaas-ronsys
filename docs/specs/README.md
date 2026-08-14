# 📚 IaaS-RonSys — Specs por Fase (SDD / Spec Anchor)

> **Framework**: SDD — **Spec Anchor**: la especificación está sincronizada con el código;
> cualquier cambio en uno debe reflejarse en el otro.
> **Guía base**: `~/investigacion/02-desarrollo-herramientas/20260730_Que-es-SDD-Spec-Driven-Development.md`
> **Fecha de generación**: 2026-08-10 (última verificación 2026-08-14) · Verificadas contra código + BD prod (head `0020_assistant`)

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
| [03-spec-delivery-dark-kitchen-v0.1.md](03-delivery/03-spec-delivery-dark-kitchen-v0.1.md) — Delivery nocturno, zonas, repartidores, campañas, menú público + **Fase B WhatsApp** (§7, motor dry-run desplegado 2026-08-11) | 🟢 APROBADA/IMPLEMENTADA (Fase A + motor Fase B dry-run) | 0016 (+companies.slug) | `/api/v1/delivery`, `/api/public`, `/api/settings` |
| [04-spec-whatsapp-en-vivo-v0.1.md](03-delivery/04-spec-whatsapp-en-vivo-v0.1.md) — **F1 "WhatsApp en Vivo"**: botones wa.me/tel en landing y campañas, BSUID, `contact` público — APROBADA y DEPLOYADA (2026-08-13) | 🟢 APROBADA/IMPLEMENTADA (2026-08-13) | 0017 (whatsapp_bsuid) | `GET /api/public/{slug}/menu` (contact) |
| [05-spec-central-telefonica-v0.1.md](03-delivery/05-spec-central-telefonica-v0.1.md) — **F2 "Central que No Pierde Llamadas"**: Asterisk (Docker host, trunk SIP 4 canales G.711), call-bridge AMI/ARI, CallRecord, panel en vivo WS, convertir llamada→pedido — APROBADA, IMPLEMENTADA y DEPLOYADA (2026-08-13) | 🟢 APROBADA/IMPLEMENTADA (2026-08-13) | 0018 (call_records) | `/api/v1/calls*`, WS `/api/v1/calls/ws/{tenant}` |
| [06-spec-recepcionista-ia-v0.1.md](03-delivery/06-spec-recepcionista-ia-v0.1.md) — **F3 "Recepcionista IA"** (por voz, agente task-bound Meta) — IMPLEMENTADA Y DEPLOYADA (2026-08-13) | 🟢 APROBADA/IMPLEMENTADA | 0019 (voice_ai) | `/api/v1/calls*` (IA) + `/api/v1/ai-calls*` |

### Fase 05 — Franquicia Conectada (multi-sucursal / F4)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [07-spec-franquicia-conectada-v0.1.md](05-franquicia-conectada/07-spec-franquicia-conectada-v0.1.md) — **F4 "Franquicia Conectada"**: tablets por sucursal, monitoreo central, enrutamiento de llamadas por local | 🟡 PROPUESTA (pendiente análisis) | — | — |

### Fase 06 — Asistente IA (consultas en lenguaje natural / F5)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [08-spec-preguntale-al-sistema-v0.1.md](06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md) — **F5 "Pregúntale al Sistema"**: NL2SQL controlado (tool calling sobre catálogo SQL seguro, delivery primero → todo el ERP). **IMPLEMENTADA Y DEPLOYADA (2026-08-14) + OBSERVABILIDAD IA**: chat flotante en Panel del Dueño, 10 consultas delivery, E2E 6/6, + LangSmith (trazas/costo por run), Grafana/Prometheus (dashboard IA Infra) y API de costos `/assistant/costs` | 🟢 APROBADA/IMPLEMENTADA | 0020 (assistant) | `/api/v1/assistant/*` |

### Fase 04 — Panel del Dueño (dashboard ejecutivo)

| Spec | Estado | Migraciones | Routers |
|---|---|---|---|
| [spec-panel-dueño.md](04-panel-indicadores/spec-panel-dueño.md) — KPIs del día, canales, top platos, ROAS, zonas, embudo delivery (V1) + V2: heatmap hora×día por canal, márgenes por canal con costeo, comparativa semana vs semana, reporte descargable CSV + PDF (dropdown), alertas vs 7 días | 🟢 IMPLEMENTADA Y DESPLEGADA (V1 + V2 + PDF, 2026-08-11) | — (usa data existente) | `/api/v1/dashboard/owner` · `/api/v1/dashboard/owner/export` |

### Fase 99 — Infraestructura / DevOps

| Spec | Estado | Migraciones | Artefactos |
|---|---|---|---|
| [spec-infra-cicd.md](99-infra-devops/spec-infra-cicd.md) — Docker, deploy, GH Actions, monitoreo, e2e | 🟢 IMPLEMENTADA | — | compose, deploy.sh, workflows, e2e |

---

## 🔗 Matriz Spec Anchor (spec ↔ código ↔ migración ↔ frontend)

> **Regla**: si modificas código de un módulo, actualiza su spec; si modificas la spec, ajusta el código.
> Estado verificado 2026-08-14 contra `main` + BD prod (head `0020_assistant`).

| Dominio | Spec | Backend | Migración | Frontend | E2E |
|---|---|---|---|---|---|
| Auth/tenant | 00-auth | `routers/auth.py`, `routers/admin.py`, `core/security.py`, `core/dependencies.py` | 0002 | Login, SetupWizard | login |
| Contabilidad | 00-contable | `routers/accounting.py`, `core/accounting/*` | 0001, 0004 | Cashflow, Reports | reportes |
| Kárdex | 00-kardex | `routers/accounting.py:386`, `services/kardex_service.py`, `core/accounting/kardex.py` | 0001, 0008-0010 | Kardex, ProductsPage | kardex |
| Simulador | 00-simulador | `routers/simulator.py`, `services/simulator_service.py` | 0006 | Simulator | simulador |
| Restaurante/POS | 01-restaurante | `routers/restaurant.py`, `routers/sales.py`, `services/restaurant_service.py`, `services/sales_service.py` + WS `/ws/kitchen`, `/ws/waiter` | 0005, 0007, 0011, 0015 | TablesMap, MenuPage, KitchenKanban, Takeaway, Pos, SalesNew/List | dashboard ⚠️ sin e2e POS/mesas |
| Inventario ferretería | 01-inventario | `routers/inventory.py`, `services/inventory_service.py` | 0008-0010 | ProductsPage, CategoriesPage | ⚠️ sin e2e inventario |
| Superadmin | 01-superadmin | `routers/superadmin.py` | 0014 | superadmin/* | ⚠️ sin e2e |
| Inversiones | 01-inversiones | `routers/investment.py`, `services/investment_service.py` | 0013 | InvestmentPage, Reports | — |
| Recetas | 02-recetas | `services/recipe_explosion.py`, `restaurant_service.py:1377` | 0012, 0015 | RecipeModal (MenuPage) | — |
| Delivery | 03-delivery | `routers/delivery.py`, `routers/public.py`, `services/delivery_service.py`, `services/whatsapp_notifier.py`, `services/notify_events.py`, `services/notify_worker.py` (worker `iaas-worker-prod`) | 0016 | DeliveryPage, PublicMenuPage | delivery-landing, delivery-staff, e2e-demo-delivery-whatsapp.cjs |
| Recepcionista IA (F3) | 06 | `routers/ai_calls.py`, `services/voice_ai_service.py`, `services/voice_bridge.py` | 0019 | CallCenterPage (tab IA) | e2e-hot-f3-recepcionista.cjs |
| Panel Dueño | 04-panel | `routers/dashboard.py`, `services/owner_dashboard_service.py` | — | DashboardOwner (`/panel`) | panel (13 tests, e2e — incl. dropdown CSV/PDF) |
| Asistente IA (F5) | 08 | `routers/assistant.py`, `services/assistant_service.py` | 0020 | AssistantChat (DashboardOwner) | e2e-hot-f5-asistente.cjs + observabilidad (LangSmith/Grafana/costs) |

> **Fase B (Spec 03 §7, 2026-08-11)**: notificaciones WhatsApp — motor de eventos desplegado en prod en modo dry-run (Notifier MetaCloud/DryRun + cola RabbitMQ `iaas-tasks` + worker con reintentos/DLQ; verificado en vivo: confirmed/new_order/status_changed/cancelled, cero HTTP). Fix métricas delivery con rango de fechas también desplegado (2026-08-11, antes 500 → 200).
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
