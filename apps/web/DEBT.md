# DEBT.md — Deudas Técnicas del Frontend

> **Proyecto**: IaaS-RonSys Web  
> **Actualizado**: 2026-05-10

---

## 🔴 Críticas (bloquean producción)

### AUTH-001: Sistema de Autenticación
- **Estado**: No implementado
- **Impacto**: La app asume sesión abierta. Sin login no hay protección de rutas ni multi-tenant real.
- **Qué falta**:
  - [ ] Página de Login (`/login`) — email + password
  - [ ] Página de Registro (`/register`)
  - [ ] `AuthContext` o `useAuth` hook (almacenar JWT, user, tenant)
  - [ ] Protección de rutas (`PrivateRoute` / wrapper)
  - [ ] Inyección de `Authorization: Bearer <token>` en `api.ts`
  - [ ] Inyección de `X-Tenant-ID` en `api.ts`
  - [ ] Refresh token flow (silent refresh antes de que expire)
  - [ ] Logout (limpiar token, redirigir a /login)
  - [ ] Manejo de 401 → redirigir a login
- **Endpoints del backend**: `POST /api/v1/auth/login`, `POST /api/v1/auth/register`
- **Estimado**: 2-3 días

### AUTH-002: Multi-tenant
- **Estado**: No implementado
- **Impacto**: Los datos se comparten entre tenants. Cada empresa debe ver solo sus datos.
- **Qué falta**:
  - [ ] Selector de tenant en el header
  - [ ] `X-Tenant-ID` header en todas las requests
  - [ ] Manejo de tenant en `usePalette` (paleta por tenant, no global)
- **Estimado**: 1-2 días

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
| 🔴 Críticas | 2 | 3-5 |
| 🟡 Medias | 5 | 5-8.5 |
| 🟢 Bajas | 5 | 3.5-5.5 |
| **Total** | **12** | **11.5-19** |
