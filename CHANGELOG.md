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

## [0.2.0] — 2026-05-26

### Added

#### 🍽️ Restaurante — Nombre del Mesero Autocompletado
- Al abrir una mesa en `TablesMap.tsx`, el campo "Nombre del Mesero" ahora es un **combobox** preseleccionado con el nombre completo (`full_name`) del usuario logueado
- El usuario se obtiene del `AuthContext` (JWT de sesión) a través del endpoint existente `GET /api/auth/me`
- Una opción **"Otro…"** permite al mesero escribir un nombre diferente manualmente si es necesario
- Mejora la velocidad de apertura de mesas al eliminar la escritura manual del nombre

---

## [0.3.0] — 2026-05-26

### Added

#### 🏢 Mantenimiento de Secciones (CRUD completo)
- Nuevo módulo de datos maestros para gestionar las secciones del restaurante
- `GET /api/sections` — listar secciones del tenant
- `POST /api/sections` — crear una nueva sección
- `PUT /api/sections/{id}` — actualizar datos de una sección
- `DELETE /api/sections/{id}` — eliminar sección (solo si no tiene mesas asociadas)
- Frontend: pantalla de administración de secciones con tabla editable
- Validación: nombre único por tenant, máximo 50 caracteres
- Protección: solo usuarios con rol `admin` pueden crear/editar/eliminar secciones

#### 🗺️ Filtro de Mesas por Sección en el Mapa
- El `TablesMap` del POS ahora incluye un filtro desplegable de secciones
- Al seleccionar una sección, el mapa muestra solo las mesas de esa sección
- Opción "Todas las secciones" para ver el mapa completo
- Mejora la navegación en restaurantes con muchas mesas distribuidas en zonas

#### 🧭 Onboarding Guiado para Configuración Inicial
- Wizard interactivo al primer login que guía paso a paso la configuración del negocio
- Selección de tipo de negocio (restaurante, ferretería, retail)
- Configuración de secciones y mesas (solo para restaurante)
- Creación del primer usuario operador
- Personalización inicial de marca (colores, logo)
- Skip disponible: el usuario puede saltar el onboarding y configurar manualmente

### Changed

#### 🍽️ Campo Sección en Mesas ahora es Dropdown del Listado de Secciones
- El campo `section` en el formulario de creación/edición de mesas pasó de campo libre a **dropdown**
- El dropdown se puebla dinámicamente desde `GET /api/sections`
- Si no hay secciones registradas, muestra un mensaje para crearlas desde Mantenimiento de Secciones
- Compatibilidad hacia atrás: mesas legacy con secciones escritas a mano se migran automáticamente

#### 🔄 Migración de Datos Legacy de Secciones a Nueva Tabla
- Script de migración único que escanea todas las mesas existentes
- Extrae valores únicos del campo `section` legacy y los inserta como registros en la nueva tabla `sections`
- Asigna cada mesa a su sección correspondiente mediante `section_id`
- Ejecutado automáticamente en el primer deploy post-migración
- Log detallado de migración disponible en `docker-compose logs backend`

### Fixed

#### 🗑️ Ruta Duplicada GET /orders/active Eliminada
- **Bug:** Dos routers definían `GET /api/orders/active` causando conflicto de ruta y error 500 al acceder
- **Causa raíz:** El router de orders legacy y el nuevo router de POS registraban la misma ruta
- **Fix:** Se unificó la lógica en un único router y se eliminó la definición duplicada

#### 🐛 Race Condition en Estado Vacío de Mesas
- **Bug:** Al cargar el mapa de mesas sin datos, ocurría un race condition entre la carga del listado de mesas y la inicialización del canvas
- **Síntoma:** El mapa se renderizaba vacío o con posiciones incorrectas hasta recargar manualmente
- **Fix:** Se agregó estado `isLoading` con spinner y se diferencia el renderizado del canvas hasta que `tables.length > 0`

#### ⚡ Selectinload Lazy Loading en list_tables
- **Bug:** El endpoint `GET /api/tables` disparaba N+1 queries por cada mesa al cargar relaciones (section, orders)
- **Causa raíz:** Falta de `selectinload` explícito en la query SQLAlchemy
- **Fix:** Se agregó `selectinload(Table.section)` y `selectinload(Table.active_order)` para eager loading
- **Impacto:** Reducción de ~20 queries a 3 en un restaurante con 15 mesas

---

## [0.4.0] — 2026-05-26

### Added

- Gestión de modificadores en el formulario del menú (CRUD: nombre, precio, grupo, máx selección)
- Campo "Observaciones para cocina" en el modal de personalización de pedidos
- Precio base del plato visible en el selector de modificadores
- Desglose de costo de modificadores en el resumen del pedido (+S/ X.XX mods)
- Validación backend: price_adjustment debe ser >= 0, max_select entre 1-100
- Validación backend: modifiers solo pueden usarse con su plato correspondiente

### Changed

- Reemplazado modal de modificadores antiguo por ModifierBottomSheet (checkboxes, contadores, radios)
- Área de pedido ampliada (max-h-32 → max-h-64)
- modifier_group_id se envía como null en vez de string vacío

### Fixed

- update_item ahora soporta modificación completa de modifiers (reemplazo)

---

## [0.6.0] — 2026-05-27

### Added

#### 💰 Módulo de Inversión — Puesta en Marcha (Caso 7)
- **Nuevo modelo ORM:** `InvestmentItem` con tabla `investment_items`
  - Validaciones a nivel BD: `estimated_cost >= 0`, `actual_cost >= 0`, `status IN ('pending','acquired')`, categorías fijas
  - Índices compuestos: `(tenant_id, category)` y `(tenant_id, status)`
- **9 categorías predefinidas:** Infraestructura 🏗️, Mobiliario 🪑, Equipamiento Cocina 🔥, Instalaciones 🛠️, Vestimenta 👕, DyL 📋, Tecnología 📱, Marketing 📣, Gastos Operativos 💰
- **6 endpoints REST** bajo `/api/v1/restaurant/investment`:
  - `GET /investment` — listar bienes (filtros por categoría y estado)
  - `POST /investment` — crear bien (con Pydantic `InvestmentCreate`)
  - `GET /investment/summary` — resumen de totales (estimado vs real, conteos)
  - `GET /investment/{id}` — obtener detalle de un bien
  - `PUT /investment/{id}` — actualizar bien (con Pydantic `InvestmentUpdate`)
  - `DELETE /investment/{id}` — eliminar bien (204 No Content)
- **Pydantic schemas dedicados:** `InvestmentCreate`, `InvestmentUpdate`, `InvestmentResponse`, `InvestmentSummary` — validación automática de campos
- **🔒 Seguridad:** todos los endpoints protegidos con `require_role("admin")`
- **Frontend:**
  - `InvestmentPage.tsx` — Dashboard con 4 tarjetas de resumen (estimado, real, diferencia, adquiridos) + lista agrupada por categoría
  - `InvestmentModal.tsx` — Modal crear/editar con validación inline, keyboard handlers (Enter/Escape), notas opcionales
  - `InvestmentDetail.tsx` — Vista detalle overlay con ahorro/exceso, recibo, notas

#### 🗑️ Confirmación de eliminación y keyboard handlers
- Diálogo de confirmación antes de eliminar un bien (con soporte Enter/Escape)
- Toasts de feedback con auto-dismiss (3.5s)
- Loading states con Skeleton mientras se cargan datos
- Botón "Agregar Primer Bien" en estado vacío
- Formato moneda en soles peruanos (S/ X,XXX.XX)
- Ruteo protegido: solo visible en sidebar para admin, ruta `/restaurante/inversion`
- **Tests:** `test_caso7_investment.py` — 18 tests (523 líneas) cubriendo:
  - CRUD completo del service layer
  - Validaciones (categoría inválida, costo negativo, status inválido)
  - Summary con y sin datos (Escenario 6 del Gherkin)
  - Todas las 9 categorías válidas parametrizadas
  - NotFound en get/update/delete

#### 🗄️ Migración
- Alembic migration `0013_investment_items.py`
  - Crea tabla `investment_items` con FK → `companies.id` (CASCADE)
  - Índices en `(tenant_id, category)` y `(tenant_id, status)`
  - Check constraints a nivel BD: costos >= 0, status válido, categorías válidas

### Fixed

#### 🔧 Seguridad — Pydantic schemas en router
- `POST /investment` y `PUT /investment/{id}` ahora reciben `InvestmentCreate`/`InvestmentUpdate` tipados en lugar de `body: dict`
- Validación automática de tipos y rangos vía Pydantic
- Eliminado riesgo de inyección de campos no esperados

#### 🔧 UX — formato moneda consistente
- Unificado formato `S/ X,XXX.XX` en InvestmentPage, InvestmentModal e InvestmentDetail
- Manejo correcto de valores negativos (ahorro/exceso)

---

## [0.5.0] — 2026-05-27

### Added

#### 📋 Recetas e Insumos por Plato (Caso 6)
- Nuevos modelos ORM: `Recipe` (PK, FK → menu_items, unique) y `RecipeIngredient`
- `GET /api/v1/restaurant/menu/{id}/recipe` — Obtener receta completa: ingredientes, costo total estimado y margen
- `PUT /api/v1/restaurant/menu/{id}/recipe` — Guardar/actualizar receta (reemplazo completo de ingredientes)
- `GET /api/v1/restaurant/products` — Listar productos del inventario para selector de insumos
- ✅ **Validación:** solo platos con `preparation_area="cocina"` pueden tener receta
- **Costo estimado:** suma de quantity × product.average_cost por ingrediente
- **Margen calculado:** precio_venta - costo_receta (valor absoluto y porcentaje)
- Botón "📋 Receta" en MenuPage.tsx — visible solo en platos de cocina
- **RecipeModal.tsx** — modal completo con:
  - Selector de productos del inventario con búsqueda
  - Asignación de cantidades y unidad de medida
  - Cálculo de costo estimado en tiempo real
- Vista de detalle del plato con ingredientes, costo total y margen

### Fixed

#### 🔧 Normalización preparation_area
- Validación backend ahora usa `"cocina"` (sin emoji) consistente con frontend y schemas
- Eliminada inconsistencia que causaba que items con receta fueran incorrectamente rechazados

### Technical Debt

| ID | Descripción |
|----|-------------|
| **TD-004** | Descuento automático de kardex al confirmar venta (recipe_explosion) — integración futura al confirmar pedidos |

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

## v0.4.1 — 2026-05-26

### Added
- **Área de preparación**: nuevo campo `preparation_area` en MenuItem (cocina | barra | none)
- Select "Área de preparación" en el formulario del menú (MenuPage.tsx)
- Filtro en cocina por `preparation_area === "cocina"` — solo se muestran platos marcados para cocina
- Columna `preparation_area` con default "cocina" — legacy items compatibles
- Items de pedido incluyen `preparation_area` para filtrado en cocina

### Changed
- "Bebida" renombrado a "Producto" en el formulario del menú
- Menú del kanban de cocina filtra por `preparation_area` (fallback legacy: `item_type !== "beverage"`)
- Esquemas Pydantic: MenuItemBase, MenuItemCreate, MenuItemUpdate incluyen `preparation_area`
- `update_item` ahora acepta y actualiza `preparation_area`

### Fixed
- Items sin `item_type` legacy se muestran igual (seguro por compatibilidad)

### Technical Debt
- **TD-001**: Modelo Recipe + integración kardex (MP consumption tracking)
- **TD-002**: Gestión separada de "Productos" (compra-venta sin receta)
