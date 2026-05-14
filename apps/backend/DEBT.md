# DEBT.md — Deudas Técnicas del Backend

> Generado: 2026-05-14 | Proyecto: IaaS-RonSys `apps/backend/`

---

## 🔴 Críticas (bloquean producción)

### AUTH-001: Sistema de Autenticación y Autorización

- **Estado:** 🟡 Parcial — Fases 1-5 implementadas (US-01 a US-15). Pendiente: despliegue con Python 3.12 + PostgreSQL + Redis, tests de integración HTTP.
- **Impacto:** Sin deployment, los endpoints siguen siendo públicos en memoria.
- **Qué se implementó:**
  - ✅ JWT HS256 + refresh tokens rotativos con family revocation
  - ✅ Password hashing con Argon2id (pwdlib)
  - ✅ User model + RefreshToken model + migración 0002_users_auth
  - ✅ Login, Refresh, Logout, Me endpoints
  - ✅ Admin endpoints (crear/lista usuarios)
  - ✅ Tenant scoping: X-Tenant-ID + repos con company_id
  - ✅ Bloqueo de cuenta por fallos
  - ✅ Rate limiting Redis sliding window (skeleton)
- **Qué falta:**
  - Deploy con PostgreSQL real (Python 3.12 requerido)
  - Tests de integración HTTP (pytest + httpx + TestClient)
  - Cambiar SECRET_KEY en .env por una generada con openssl rand -hex 32
  - Redis real para rate limiting (actualmente fallback in-memory)

### AUTH-002: Rate Limiting sin Redis (fallback en memoria)

- **Estado:** 🟡 Parcial — implementado con diccionario en memoria
- **Impacto:** El rate limiting no persiste entre reinicios. En producción con múltiples workers, cada worker tiene su propio contador.
- **Qué falta:**
  - Conectar `setup_rate_limiting()` a Redis real (el cliente Redis ya está en `requirements.txt`)
  - Implementar sliding window con `ZADD`/`ZREMRANGEBYSCORE` en Redis
- **Estimado:** 4 horas

---

## 🟡 Medias

### AGT-001: Skills de IA sin implementar

- **Estado:** 🟡 Puerto abstracto diseñado (`BaseSkill`, `SkillRegistry`), sin implementaciones concretas
- **Archivos:** `core/agents/base.py`, `core/agents/__init__.py`
- **Skills pendientes:**
  - `SalesSkill` — análisis de ventas, predicciones, alertas
  - `InventorySkill` — stock bajo, rotación, sugerencias de compra
  - `FinanceSkill` — proyecciones, alertas de flujo de caja
  - `ReportSkill` — generación de reportes financieros
- **Qué falta:**
  - Implementar skills concretas
  - `SkillLoader` que descubre skills por decorador/registro
  - Conexión con LLM provider (OpenAI/DeepSeek vía API key en `.env`)
  - Tests unitarios para cada skill
  - Posible extracción a servicio independiente si el consumo de CPU es alto
- **Estimado:** 5-7 días

### CF-001: Flujo de Caja como módulo separado

- **Estado:** 🟡 Documentado en `simulador-financiero/docs/05-flujo-caja.md`, lógica básica embebida en `statements.py`
- **Impacto:** El flujo de caja está documentado como un módulo completo con: proyectado, real, comparado. Solo se implementó el cálculo básico de flujos dentro de `FinancialStatementService.run_simulation()`.
- **Qué falta:**
  - Módulo `core/accounting/cashflow.py` independiente
  - Endpoint `GET /api/accounting/cashflow`
  - Integración con datos reales del ERP (ventas reales vs proyectadas)
  - Comparativa proyectado vs real
- **Estimado:** 1-2 días

### DB-001: SQLite in-memory para tests no implementado

- **Estado:** 🟡 `conftest.py` preparado pero tests usan el motor contable en memoria (sin DB)
- **Impacto:** Los tests de repositorios SQLAlchemy no se ejecutan. Solo se testea el dominio puro.
- **Qué falta:**
  - `conftest.py` con fixture que cree engine SQLite in-memory
  - Tests de integración para `SQLAlchemyAccountingRepository` y `SQLAlchemyInventoryRepository`
  - Marcar tests que requieren DB con `@pytest.mark.db`
- **Estimado:** 1-2 días

### REST-001: Tests de integración para nuevos módulos Restaurante

- **Estado:** 🟢 Pendiente — modelos y servicios implementados en Fase 0
- **Qué falta:**
  - Tests unitarios para servicios de Restaurante (TablesService, KitchenOrdersService, etc.)
  - Tests de integración HTTP para nuevos endpoints de Restaurante y Ferretería
  - Tests de WebSocket para comunicación cocina
- **Estimado:** 1-2 días

### FERR-001: Precios mayoristas solo afectan endpoint POST /api/sales/sale

- **Estado:** 🟢 Funcional — HU-F0-010 implementado en `sales_service.py`
- **Qué falta:**
  - Los endpoints de Restaurante que crean ventas (close-order + pay) NO aplican wholesale pricing automáticamente (son items del menú)
  - Confirmar que wholesale pricing se aplique también en ventas directas por API
- **Estimado:** 0.5 día

---

## 🟢 Bajas

### TST-001: Cobertura de tests HTTP (routers)

- **Estado:** 🟢 Tests del dominio existen (140 tests ✅), pero no hay tests de integración HTTP para nuevos endpoints de Fase 0
- **Qué falta:**
  - Tests para cada endpoint del Restaurante
  - Tests de validación de schemas (request/response)
  - Tests de WebSocket
- **Estimado:** 1-2 días

### DOC-001: Documentación de API (OpenAPI/Swagger)

- **Estado:** 🟢 Swagger UI funciona en `/docs`, pero algunas descripciones podrían mejorarse
- **Qué falta:**
  - Ejemplos `response_model_example` en los endpoints principales
  - `docs/api.md` con ejemplos curl
  - `docs/architecture.md` con diagrama de capas hexagonal
- **Estimado:** 2-4 horas

### CFG-001: Tests asyncio_mode en pyproject.toml

- **Estado:** 🟢 `asyncio_mode = "auto"` configurado pero genera warning en pytest 9.x
- **Qué falta:** Actualizar configuración a formato pytest 9.x
- **Estimado:** 15 minutos

### MULTITENANT-001: tenant_id unificado — company_id eliminado (✅ Resuelto)

- **Estado:** 🟢 QA Fase 0 — migración `0010_drop_company_id` elimina `company_id` de todas las tablas.
  Todos los modelos ORM, repositorios, servicios y core usan `tenant_id`.
  Schemas Pydantic mantienen `company_id` como nombre de campo para backward compat de API.
- **Plan:** Fase 1 — cambiar schemas Pydantic de `company_id` → `tenant_id` (breaking API change).
- **Estimado:** 0.5 día

### MULTITENANT-002: Schemas Pydantic con campo company_id (deuda API)

- **Estado:** 🟢 Los schemas de respuesta (AuthResponse, SaleResponse, etc.) exponen `company_id`
  en JSON pero internamente usan `tenant_id`. Cambiar en Fase 1 con versionado de API.
- **Plan:** Agregar `serialization_alias="company_id"` o cambiar a `tenant_id` en v2.
- **Estimado:** 0.5 día

### RBAC-001: Sistema de permisos sin consumir

- **Estado:** 🟢 Migración `0011_role_permissions` crea tabla con seed de permisos básicos.
  No hay middleware/guards que consulten la tabla — los permisos se validan por rol hardcodeado.
- **Plan:** Implementar `require_permission("sales:write")` que consulte `role_permissions`.
- **Estimado:** 1 día

---

## 📊 Resumen

| Severidad | Cantidad | Días estimados |
|-----------|:--------:|:--------------:|
| 🔴 Crítica | 2 | 4-5 días |
| 🟡 Media | 5 | 9-15 días |
| 🟢 Baja | 6 | 3-4 días |
| **Total** | **13** | **16-24 días** |
