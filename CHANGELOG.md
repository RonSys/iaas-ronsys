# Changelog — IaaS-RonSys

> ERP SaaS Financiero-Contable para la Franquicia "El Segoviano" 🐟

---

## [0.1.0] — 2026-05-10

### Added

#### 🧾 Motor Contable
- Simulación financiera completa a 12 meses con asientos contables automáticos
- Cálculo de depreciación, intereses, amortización e impuesto a la renta (29.5%)
- Validación de consistencia contable (partida doble)
- Endpoint `POST /api/accounting/setup` con InvestmentInput completo

#### 📦 Kárdex / Inventario
- Registro de productos, entradas (compras) y salidas (ventas/mermas)
- Costo promedio ponderado automático con cada entrada
- Historial completo de movimientos por producto
- Inventario actual valorizado

#### 📊 Estados Financieros
- Estado de Resultados (PYG) con desglose completo
- Balance General (Activo = Pasivo + Patrimonio)
- Balance de Comprobación de Sumas y Saldos (BCSS)
- Todos generados automáticamente desde la simulación

#### 💰 Ratios Financieros
- 9 ratios con semáforo interpretativo 🟢🟡🔴
- Liquidez, Prueba Ácida, Endeudamiento, Margen Neto, ROE, ROA
- Cobertura de Intereses, Rotación de Inventario, Payback
- Rangos configurables por ratio

#### 🔐 Autenticación Multi-Tenant
- JWT self-contained (HS256) con access token (15 min) + refresh token rotativo (7 días)
- Password hashing con Argon2id (pwdlib)
- Middleware X-Tenant-ID obligatorio en endpoints protegidos
- Validación cruzada: user.company_id == tenant_id
- Scoping automático en repositorios SQLAlchemy
- Role-based access control: admin, manager, operator, viewer
- `POST /api/auth/login`, `/refresh`, `/logout`, `GET /api/auth/me`

#### 👥 Admin Users
- `POST /api/admin/users` — crear usuarios (admin only)
- `GET /api/admin/users` — listar usuarios con filtros (rol, estado, búsqueda)
- Validación de contraseña: mín 8 chars, 1 mayúscula, 1 número
- Usuario creado en el mismo tenant que el admin

#### 🛡️ Seguridad
- Rate limiting de login: 5 intentos/min por IP + 5 intentos/min por email (Redis sliding window)
- Bloqueo de cuenta: 10 fallos consecutivos → 15 minutos
- Family revocation: reuso de refresh token revoca todas las sesiones
- Mensajes genéricos anti-enumeración de usuarios
- Timing attack mitigation en login

#### 🖥️ Frontend
- **Login** — formulario con validación, mensajes de error, estado de carga
- **AuthContext** — estado global de autenticación con refresh automático
- **PrivateRoute** — protección de rutas con restricción por roles
- **Interceptor 401** — refresh automático transparente, cola de requests concurrentes
- **Dashboard** — 4 KPIs + PYG resumido + Balance resumido + gráficos de flujo de caja
- **Setup Wizard** — formulario de inversión con secciones colapsables
- **Simulador** — 5 sliders interactivos + escenarios comparativos (4)
- **Reportes** — 4 tabs (PYG, Balance, BCSS, Ratios con semáforo)
- **Kárdex** — inventario con modales de entrada/salida + historial
- **Settings** — 4 paletas predefinidas + 10 colores personalizables
- **Admin Users** — crear/listar usuarios (UI de admin)
- Code-splitting con React.lazy + Suspense (~77 KB inicial)
- Sistema de branding dinámico vía CSS custom properties
- 10 colores configurables vía `PATCH /api/settings/palette`

#### 🎭 Testing
- **66 tests backend** (pytest) — motor contable, kárdex, ratios, auth
- **43 tests frontend** (Jest + React Testing Library) — 8 suites de componentes
- **31 tests E2E** (Playwright) — 6 flujos de usuario completos
- Total: **140 tests** automatizados

#### 🏗️ Infraestructura
- **2 entornos separados**: QA (:5173/:8001) y Producción (:80/:8000)
- Script `deploy.sh` idempotente con `--env qa` y `--env prod`
- QA: Vite dev server con hot-reload + proxy
- Producción: Nginx sirviendo archivos estáticos + proxy reverso `/api`
- Bases de datos separadas: `iaas_ronsys_qa` vs `iaas_ronsys`
- Ambos entornos pueden ejecutarse simultáneamente
- Docker Compose files: `docker-compose.qa.yml`, `docker-compose.prod.yml`

#### 📚 Documentación
- `docs/architecture/auth-multi-tenant-design.md` — diseño completo de auth
- `docs/stories/auth-multi-tenant.stories.md` — 19 historias Gherkin
- `docs/arquitectura-frontend.md` — arquitectura del frontend
- `docs/manuales/guia-despliegue.md` — guía de despliegue con QA/Prod
- `docs/manuales/guia-inicio-rapido.md` — primeros pasos en 5 minutos
- `docs/manuales/manual-usuario.md` — manual completo de cada módulo
- `docs/manuales/manual-admin.md` — guía de administración y seguridad
- `docs/setup.md` — setup técnico del backend

---

## [0.1.1] — 2026-05-11

### Fixed

#### 🧩 Simulador — Pantalla en Blanco
- **Bug:** `GET /api/simulator/scenarios` devolvía `{ scenarios, total, max_allowed }` (objeto) pero el frontend esperaba un `array` directo → `.map()` sobre objeto → crash → pantalla en blanco.
- **Causa raíz:** Type mismatch Backend↔Frontend en `getScenarios()`.
- **Fix:** `apps/web/src/services/api.ts` — `getScenarios()` ahora desenvuelve `data.scenarios` tipando correctamente la respuesta como `{ scenarios: Scenario[]; total: number; max_allowed: number }`.
- **Rebuild:** `docker compose up -d --build` necesario para aplicar.

#### 🟡 Issue secundario (deuda técnica baja)
- `GET /api/settings/palette` retorna 400 sin `X-Tenant-ID`. No bloqueante (`usePalette` hace fallback). Pendiente de resolver en próxima iteración.

---

## [Unreleased]

### Planned
- 🔜 Email verification + password reset flow
- 🔜 MFA / 2FA (TOTP)
- 🔜 OAuth2 social login (Google)
- 🔜 Usuario en múltiples empresas (user_companies pivot)
- 🔜 httpOnly cookies para refresh token
- 🔜 Endpoint de Flujo de Caja completo
- 🔜 Skills de IA concretas (LangChain)
- 🔜 Módulo Sales / POS
- 🔜 Módulo RRHH / Planillas
- 🔜 Módulo Delivery

---

> **Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)**  
> **Versionado semántico**: [SemVer](https://semver.org/lang/es/)
