# 📅 Avance Diario — 2026-08-03 (Día 1: Pipeline Fase A Delivery completo)

> **Proyecto:** IaaS-RonSys — Upgrade Dark Kitchen / Delivery nocturno (El Segoviano)
> **Estado general:** 🟢 **Fase A (MVP Delivery) IMPLEMENTADA, DESPLEGADA EN PROD y con E2E 11/11 PASS**
> **Patrón diario:** cada día se crea `docs/reports/avance-diario-YYYY-MM-DD.md` (mañana: `avance-diario-2026-08-04.md`)

---

## 1. Resumen ejecutivo

En un solo día se completó el **pipeline completo de la Fase A**: especificación (Spec 03 aprobada por Ron con decisiones D1-D6) → migración → backend → frontend → manuales → deploy a producción → smoke tests → E2E automatizados. El delivery nocturno **ya está operativo en https://www.ronsyserp.com/menu/el-segoviano**.

**Lo más relevante de hoy:**
- 🚀 **Fase A en producción**: landing pública funcional, checkout con Yape/Plin/contraentrega, cocina integrada (kanban), panel staff completo, campañas con ROAS.
- ✅ **QA: 10/10** (suite specs 01/02) + **E2E: 11/11** contra prod.
- 🐛 **3 bugs reales encontrados y corregidos** en el camino (yape_phone no configurable, PATCH parcial 422, timezone UTC vs Lima).

---

## 2. Avanzado hoy (en orden)

| # | Hito | Detalle | Evidencia |
|---|---|---|---|
| 1 | **Análisis técnico + plan** | Revisión del repo: motor de ventas ya soportaba delivery (`order_type=delivery`), Yape ya existía, sesión POS opcional → 80% reutilizable | Análisis entregado al dashboard |
| 2 | **Spec 03 aprobada** | `docs/specs/03-spec-delivery-dark-kitchen-v0.1.md` — D1-D6 resueltas por Ron | D1 fee→cuenta 40 · D2 Zona 1 (Montenegro/Motupe/Canto Grande, S/5, mín. S/35, ETA 35) · D3 repartidores internos · D4 Yape configurable · D5 19:00–24:00 · D6 campaign_id solo en delivery_orders |
| 3 | **Migración 0016** | 4 tablas nuevas (delivery_zones, couriers, marketing_campaigns, delivery_orders) + columnas menu_items/companies + seed Zona 1 + slug `el-segoviano` | Validada: upgrade/downgrade/upgrade en PG16 desechable |
| 4 | **Backend Fase A** | 18 rutas: públicas (menú/zones/checkout/tracking, rate-limit, slug) + staff (CRUD zonas/repartidores/campañas, máquina de estados, assign-courier, métricas ROAS) + fix D-03 (settings persistente) | Smoke E2E: checkout 201, asiento contable balanceado |
| 5 | **Frontend Fase 5** | Panel staff (5 pestañas) + landing pública con branding del tenant, carrito, checkout UTM, tracking | Build OK (tsc 0 errores) |
| 6 | **Manuales** | Manual delivery nuevo + admin §5.3/5.4/10.5 + puntero en manual Fase 0 | `docs/manuales/` |
| 7 | **Deploy PROD (Fase 6)** | Backup imágenes `.bak-2026-08-03` + pg_dump → `./deploy.sh --env prod` → alembic `0016_delivery` en prod → QA 10/10 post-deploy | Prod en 0016, contenedores healthy |
| 8 | **Config prod** | Yape **912057784** configurado (settings.delivery.yape_phone) → visible en landing | Verificado en menú público |
| 9 | **Fixes post-deploy** | (a) yape_phone no persistía (schema sin campo delivery) · (b) PATCH parcial 422 en panel (toggle Pausar roto) · (c) timezone America/Lima | Desplegados y verificados |
| 10 | **E2E Camino C** | Playwright contra prod con Chrome for Testing 151: 6 tests landing + 5 staff | **11/11 PASS** (41.6s) |
| 11 | **Monitor físico (.35)** | Plan completo entregado (Xorg+openbox+lightdm, CfT listo, config OpenClaw) | ⏳ Pendiente de Ron (paso 0 y 1) |

---

## 3. Estado actual en producción (https://www.ronsyserp.com)

- 🌙 **Landing delivery:** `/menu/el-segoviano` — menú nocturno, horario 19:00–23:59, Yape 912057784 visible, promos, checkout con UTM, seguimiento por código.
- 🛵 **Panel staff:** Restaurante → Delivery Nocturno — kanban de pedidos (recibido→cocina→listo→en ruta→entregado/cancelado), zonas, repartidores, campañas (link UTM autogenerado), métricas ROAS/AOV.
- 🧾 **Contabilidad automática:** cada pedido genera venta (order_type=delivery) + kárdex (explosión de recetas) + asiento contable (fee en cuenta 40).
- 🗄️ **BD prod:** alembic `0016_delivery` · Zona 1 sembrada · slug `el-segoviano` · Yape configurado.
- 🔑 **Credenciales demo (el deploy las resetea):** `admin@elsegoviano.pe` / `admin123` · tenant 1 = "Admin Tenant" (operación real de El Segoviano).

---

## 4. Pendiente / sugerencias para mañana (2026-08-04)

**Bloqueante para el demo visual en el monitor:**
1. 🖥️ Ron conecta el monitor al **HDMI-A-1** del .35 y lo enciende → verificar `cat /sys/class/drm/card0-HDMI-A-1/status` = `connected`.
2. Ron corre el apt del plan (xserver-xorg, xinit, openbox, lightdm + deps + autologin) y reinicia.
3. Configurar OpenClaw (plugins.allow + bloque `browser`: headless:false, noSandbox:true, executablePath `/home/ron/.local/share/chrome-linux64/chrome`) y **relanzar el gateway con `DISPLAY=:0`** (⚠️ reiniciar el gateway mata las sesiones activas — coordinar horario).
4. **Demo en vivo con Ron**: navegador visible en el monitor abriendo la landing y el panel.

**Cierre operativo del negocio:**
5. 🛵 Registrar a **Nilton y repartidores reales** en el panel (Delivery Nocturno → Repartidores).
6. 📢 Crear las **campañas reales** (Meta/Google) con sus links UTM y registrar el gasto → ROAS real.
7. 📱 Confirmar el número Yape mostrado y probar un pedido real nocturno (19:00–24:00).

**Opcional (Fase B — no aprobada aún):**
8. Notificaciones WhatsApp (Meta Cloud API + RabbitMQ ya desplegado), pago online PSP (Izipay/Culqui), integración Rappi/PedidosYa.

---

## 5. Commits del día

```
5490174  feat(e2e): Camino C — Playwright E2E delivery contra prod (11/11) + fix PATCH parcial
6a4e210  feat(delivery): Spec 03 Fase 5 — frontend (panel staff + landing pública) + manuales
7787a70  fix(delivery): yape_phone configurable vía PATCH /api/settings (Spec 03 D4)
7f93642  feat(delivery): Spec 03 Fase A — backend público + staff + fix D-03
0f13728  feat(delivery): Spec 03 Fase A — migración 0016 delivery + seed Zona 1
```

## 6. Archivos clave (rutas)

| Qué | Ruta |
|---|---|
| **Spec 03 (viva)** | `docs/specs/03-spec-delivery-dark-kitchen-v0.1.md` |
| Migración | `apps/backend/app/adapters/alembic/versions/0016_delivery.py` |
| Backend delivery | `apps/backend/app/services/delivery_service.py` + `routers/public.py` + `routers/delivery.py` |
| Frontend staff | `apps/web/src/pages/restaurante/DeliveryPage.tsx` |
| Landing pública | `apps/web/src/pages/public/PublicMenuPage.tsx` |
| E2E prod | `apps/web/e2e/playwright.config.prod.ts` + `delivery-landing.spec.ts` + `delivery-staff.spec.ts` |
| Manual delivery | `docs/manuales/manual-delivery-dark-kitchen.md` |
| Manual admin (delivery) | `docs/manuales/manual-admin.md` §5.3/§5.4/§10.5 |
| Informe de upgrade | `docs/reports/informe-upgrade-dark-kitchen-delivery-2026-08-03.md` |

## 7. Comandos útiles

```bash
# E2E contra prod + reporte (visible desde la laptop .39)
cd apps/web && npm run test:e2e:prod && npm run test:e2e:prod:report   # → http://192.168.1.35:9323

# QA suite specs 01/02 (idempotente)
python3 scripts/qa/test_suite.py

# Deploy (patrón: backup previo de imágenes .bak-<fecha>)
./deploy.sh --env prod
```

---

> **Nota para mañana:** continuar con este archivo como referencia; crear `avance-diario-2026-08-04.md` al cierre del día 2. Toda la Fase A quedó sync según Spec Anchor (spec ↔ código ↔ bitácora en `docs/specs/03-...` §5).
