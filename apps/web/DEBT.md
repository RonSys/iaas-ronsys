# DEBT.md — Deudas Técnicas del Frontend

> **Proyecto**: IaaS-RonSys Web  
> **Actualizado**: 2026-05-14

---

## ✅ Fase 0 Implementada (2026-05-14)

### HU-F0-011: Sidebar jerárquico con botón Salir siempre visible
- **Estado**: Implementado ✅
- **Cambios**:
  - Nuevos componentes: `Sidebar.tsx`, `SidebarSection.tsx`, `SidebarItem.tsx` en `components/layout/`
  - Sidebar jerárquico colapsable con persistencia en sessionStorage
  - Botón "Cerrar Sesión" en la parte inferior izquierda, SIEMPRE visible
  - Secciones: PROYECTO DE INVERSIÓN, ERP (Ventas, Restaurante, Inventario, Finanzas), CONFIGURACIÓN
  - Responsive: desktop sidebar fijo + mobile overlay con hamburguesa
  - Sección Restaurante oculta según feature flag `tables_enabled` o `businessType === 'restaurant'`

### HU-F0-012: Rutas frontend organizadas por dominio
- **Estado**: Implementado ✅
- **Cambios**:
  - `App.tsx` reorganizado con rutas agrupadas:
    - `/` → Dashboard
    - `/inversiones/reportes` → Reports
    - `/ventas/pos` → PosPage
    - `/ventas/nueva` → SalesNewPage
    - `/ventas/historial` → SalesListPage
    - `/restaurante/mesas` → TablesPage
    - `/restaurante/menu` → MenuPage
    - `/restaurante/comandas` → KitchenOrdersPage
    - `/restaurante/takeaway` → TakeAwayPage
    - `/restaurante/promociones` → PromotionsPage
    - `/inventario/kardex` → KardexPage
    - `/inventario/categorias` → CategoriesPage
    - `/finanzas/cashflow` → CashflowPage
    - `/config/marca` → Settings
  - Redirects 301 para rutas antiguas: `/kardex`→`/inventario/kardex`, `/reportes`→`/inversiones/reportes`, etc.
  - 404 catch-all
  - Code-splitting con React.lazy mantenido

### HU-F0-014: Páginas frontend para Restaurante
- **Estado**: Implementado ✅
- **Páginas creadas**:
  - `pages/restaurant/TablesPage.tsx` — Mapa visual de mesas con estados y modales
  - `pages/restaurant/MenuPage.tsx` — CRUD de ítems del menú con toggle disponibilidad
  - `pages/restaurant/KitchenOrdersPage.tsx` — Tablero Kanban (Pendiente→Preparando→Listo) con WebSocket + polling fallback
  - `pages/restaurant/TakeAwayPage.tsx` — Gestión de pedidos takeaway con alertas de atraso
  - `pages/restaurant/PromotionsPage.tsx` — CRUD de promociones con toggle activo
- **Cada página maneja 4 estados**: loading (Skeleton), empty (mensaje amigable), error (banner + retry), data

### HU-F0-015: Frontend Ferretería
- **Estado**: Implementado (parcial - depende de backend) ✅
- **Cambios**:
  - `types/accounting.ts`: `KardexProduct` extendido con `unit_price`, `wholesale_price`, `wholesale_min_qty`, `category_id`, `category_name`
  - `components/sales/ProductSearch.tsx`: Filtro de productos por categoría + muestra precios mayoristas/menoristas
  - `components/sales/SaleForm.tsx`: Lógica de `getEffectivePrice()` para aplicar precio mayorista según cantidad
  - `pages/inventario/CategoriesPage.tsx`: CRUD de categorías
  - `components/sales/SaleItemsList.tsx`: Indicador de precio mayorista en ítems

### Deudas resueltas:
- D-08 (sidebar jerárquico) — ✅ Resuelto
- D-09 (botón Salir siempre visible) — ✅ Resuelto
- D-07 (rutas por dominio) — ✅ Resuelto (parcial: estructura de frontend, backend routers pendientes)

### Deudas nuevas identificadas:
- **F0-IMP-001**: Páginas de Restaurante dependen de endpoints backend (`/api/v1/restaurant/*`) que aún no existen
- **F0-IMP-002**: ProductSearch usa `fetch()` directo para categorías — necesita mock global en tests

---

## 🔴 Críticas (bloquean producción)

### AUTH-001: Sistema de Autenticación
- **Estado**: Implementado ✅
- **Nota**: Login, AuthContext, PrivateRoute y authStore existen y están funcionales.
  - ✅ `LoginPage` (`/login`) — email + contraseña
  - ✅ `AuthContext` — estado global (user, tenant, tokens)
  - ✅ `PrivateRoute` — protección de rutas con redirect a /login
  - ✅ `authStore` — bridge entre AuthContext y api.ts
  - ✅ `api.ts` — inyección automática de `Authorization: Bearer` y `X-Tenant-ID`
  - ✅ Refresh token con cola (evita race condition)
  - ✅ Logout (limpia token, sessionStorage)
  - ✅ Manejo de 401 → refresh automático o logout

### AUTH-002: Multi-tenant
- **Estado**: Implementado parcialmente ✅
- **Nota**: `X-Tenant-ID` se inyecta automáticamente desde el JWT decodificado (company_id).
  - ✅ `X-Tenant-ID` header en todas las requests vía `api.ts`
  - ⚠️ Selector de tenant en el header (pendiente para multi-tenant real)
  - ⚠️ Paleta por tenant (actualmente usa configuración global)

---

## 🟡 Medias

### UX-001: Manejo de errores global
- **Estado**: Básico — cada página muestra errores inline
- **Qué falta**:
  - [ ] `ErrorBoundary` global (React error boundary)
  - [ ] Toast / snackbar de notificaciones (éxito, error, warning)
  - [ ] Manejo uniforme de errores de red (offline, timeout, 500)
- **Estimado**: 1-2 días

### UX-002: Responsive design completo
- **Estado**: Desktop-first con navbar mobile básico. No probado exhaustivamente en tablet/phone.
- **Qué falta**:
  - [ ] Probar y ajustar todas las páginas en breakpoints sm/md
  - [ ] Tablas con scroll horizontal en mobile
  - [ ] Gráficos Recharts responsive en pantallas pequeñas
  - [ ] Modales full-screen en mobile
- **Estimado**: 2-3 días

### UX-003: Estados de carga (skeletons)
- **Estado**: Implementado en Dashboard, parcial en otras páginas
- **Qué falta**:
  - [ ] Skeletons en SetupWizard (mientras simula)
  - [ ] Skeletons en Reports (mientras cambia de tab)
  - [ ] Skeletons en Settings (mientras carga paleta)
- **Estimado**: 0.5 día

### DOC-001: Storybook / Catálogo de componentes
- **Estado**: No implementado
- **Qué falta**:
  - [ ] Instalar y configurar Storybook
  - [ ] Stories para: KPICard, TrafficLight, Skeleton, CashflowChart, SliderField, FormField, modals
- **Estimado**: 1-2 días

### PERF-001: Tamaño de bundle (Recharts)
- **Estado**: Recharts son 110 KB gzip, solo en el chunk del Dashboard
- **Mitigación actual**: Code-splitting con React.lazy
- **Opciones futuras**:
  - [ ] Evaluar alternativas más ligeras (Nivo, visx)
  - [ ] Lazy load Recharts solo cuando la sección de gráficos es visible (IntersectionObserver)
- **Estimado**: 1 día (si se cambia de librería)

---

## 🟢 Bajas

### TST-001: Cobertura de tests
- **Estado**: 43 tests en 8 suites. Solo componentes y páginas principales.
- **Qué falta**:
  - [ ] Tests de `usePalette` y `useAccounting` hooks (con mock de fetch)
  - [ ] Tests de `api.ts` funciones (con mock de fetch)
  - [ ] Tests de flujo: Setup → Simulador → Dashboard (integración)
  - [ ] Tests de accesibilidad (axe-core)
- **Cobertura actual**: ~40% (estimada)
- **Meta**: 80%+
- **Estimado**: 2-3 días

### TST-002: Tests E2E
- **Estado**: No implementado
- **Qué falta**:
  - [ ] Playwright o Cypress para tests end-to-end
  - [ ] Flujo: Login → Setup → Dashboard → Simulador → Reportes
- **Estimado**: 2-3 días

### CFG-001: Variables de entorno
- **Estado**: Solo proxy de Vite hardcodeado
- **Qué falta**:
  - [ ] `.env.production` con `VITE_API_BASE_URL`
  - [ ] `.env.development` con `VITE_API_BASE_URL=/api`
  - [ ] Usar `import.meta.env.VITE_API_BASE_URL` en `api.ts`
- **Estimado**: 0.5 día

### IMPL-001: Endpoints de backend pendientes para Fase 1-2
- **Estado**: Pendiente (dependencia externa)
- **Impacto**: Las nuevas páginas (Cashflow, POS, Ventas) no recibirán datos reales hasta que el backend implemente los endpoints.
- **Endpoints requeridos**:
  - `GET /api/admin/company/settings` — HU-F1-002 (backend)
  - `GET /api/accounting/cashflow` — HU-F1-004/005/006 (backend)
  - `POST /api/sales/sessions/open` — HU-F2-003 (backend)
  - `GET /api/sales/sessions/current` — HU-F2-003 (backend)
  - `POST /api/sales/sessions/{id}/close` — HU-F2-003 (backend)
  - `POST /api/sales/sale` — HU-F2-004 (backend)
  - `GET /api/sales/sales` — HU-F2-004 (backend)
  - `GET /api/sales/sale/{id}` — HU-F2-004 (backend)
  - `GET /api/sales/sale/{id}/ticket` — HU-F2-007 (backend)
  - `POST /api/sales/sale/{id}/void` — HU-F2-004 (backend)
  - `GET /api/sales/payment-methods` — HU-F2-004 (backend)
  - `GET /api/accounting/kardex/products?search=` — HU-F2-005 (backend)
- **Mitigación**: Todos los componentes y hooks tienen mocks completos para desarrollo y tests.
- **Estimado**: 0 (frontend completo, depende de backend)

### IMPL-002: Cobertura de tests para nuevos componentes
- **Estado**: Parcial
- **Cubierto**: useCompanySettings (5 tests), CashflowPage (3 tests), PosSession (13 tests), SalesComponents (11 tests), SalesList (9 tests) — Total: 49 nuevos tests
- **Pendiente**: Tests de integración para flujo completo de venta, tests E2E con Playwright
- **Estimado**: 1-2 días

### CFG-002: ESLint + Prettier
- **Estado**: No instalados (están en package.json como scripts pero sin dependencias)
- **Qué falta**:
  - [ ] Instalar y configurar ESLint con reglas React + TypeScript
  - [ ] Instalar y configurar Prettier
  - [ ] Agregar lint-staged + husky (pre-commit hooks)
- **Estimado**: 0.5 día

### DOC-002: Changelog
- **Estado**: No existe
- **Qué falta**:
  - [ ] `CHANGELOG.md` con historial de versiones
  - [ ] Convención de versionado semántico
- **Estimado**: 0.25 día

---

## 📊 Resumen

| Prioridad | Count | Días estimados |
|-----------|:-----:|:--------------:|
| 🔴 Críticas | 0 | 0 (Auth implementado) |
| 🟡 Medias | 5 | 5-8.5 |
| 🟢 Bajas | 5 | 3.5-5.5 |
| ⏳ Dependencias Backend | 1 | 0 |
| 🟡 Nuevas (Fase 1-2) | 2 | 1-2 |
| **Total** | **13** | **9.5-16** |

> **Nota Fase 1-2 (2026-05)**: Implementados 6 HU frontend con 49 nuevos tests.
> Auth (AUTH-001) ya estaba implementado — actualizado DEBT.md para reflejar realidad.
