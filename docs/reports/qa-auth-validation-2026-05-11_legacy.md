# 🧪 QA Validation Report — Auth Multi-Tenant

> **Autor:** QA Automation Agent  
> **Fecha:** 2026-05-11  
> **Sprint:** Auth Multi-Tenant (19 US)  
> **Veredicto:** ✅ **LISTO** (con observaciones)

---

## 📊 Resumen Ejecutivo

| Métrica | Resultado |
|---------|:---------:|
| Backend unit tests | **66/66** ✅ (incluye 7 nuevos de rate limit) |
| Frontend unit tests | **43/43** ✅ (8 suites) |
| TypeScript check | ✅ Clean (`tsc --noEmit`) |
| Vite build | ✅ Clean (5.7s) |
| Endpoints curl tests | **31/31** ✅ |
| Cobertura backend | 48% (auth sin unit tests — pendiente) |
| Bugs encontrados | **2** (1 HIGH, 1 MEDIUM) |
| Observaciones | **3** |

---

## 🔬 Validación de Historias Gherkin (19 US)

### Fase 1 — Core Security + Modelos

| US | Descripción | Veredicto | Evidencia |
|----|------------|:---------:|-----------|
| US-01 | Configuración de Seguridad Base | ✅ PASS | SECRET_KEY 64 chars hex en .env.qa, Argon2id en security.py, constant-time verification, email-validator activo, .env en .gitignore |
| US-02 | Modelos User y RefreshToken | ✅ PASS | Modelos ORM completos (User + RefreshToken) con todas las columnas, índices en email/token_hash/expires_at, check constraint para roles, seed admin en migración 0002 |
| US-03 | Motor JWT y Dependencias | ✅ PASS | `create_access_token` con HS256, `decode_access_token` con validación completa, `get_current_user`, `get_current_active_user`, `require_role` factory |

### Fase 2 — Auth Endpoints

| US | Endpoint | Veredicto | Evidencia |
|----|----------|:---------:|-----------|
| US-04 | `POST /api/auth/login` | ✅ PASS | 200 con JWT + refresh + user data. Anti-enumeración: mismo mensaje "Invalid email or password" para email inexistente y password incorrecta. Resetea failed_login_attempts en login exitoso |
| US-05 | `POST /api/auth/refresh` | ✅ PASS | Rotación correcta (revoca viejo, crea nuevo). Family revocation: token reusado → 401 "Token revoked — all sessions invalidated". Nuevo RT emitido correctamente |
| US-06 | `POST /api/auth/logout` | ✅ PASS | 200 idempotente (siempre "Successfully logged out"). Revoca refresh token |
| US-07 | `GET /api/auth/me` | ✅ PASS | Retorna perfil sin campos sensibles. 401 sin token, 403 usuario inactivo |

### Fase 3 — Admin Users

| US | Endpoint | Veredicto | Evidencia |
|----|----------|:---------:|-----------|
| US-08 | `POST /api/admin/users` | ✅ PASS | 201 Created con datos del usuario. Password policy (8+ chars, 1 uppercase, 1 number) validada. Role validation (admin/manager/operator/viewer). 409 email duplicado |
| US-09 | `GET /api/admin/users` | ✅ PASS | Lista usuarios del tenant con filtros (role, is_active, search). Paginación (limit/offset) |

### Fase 4 — Tenant Scoping

| US | Descripción | Veredicto | Evidencia |
|----|------------|:---------:|-----------|
| US-10 | Middleware X-Tenant-ID | ✅ PASS | `get_tenant_id` como dependencia explícita (no middleware global). 400 si falta header. Validación numérica |
| US-11 | Repositorios con scoping | ✅ PASS | `UserRepository.__init__(session, company_id)` aplica scoping automático. `SQLAlchemyAccountingRepository` igual |
| US-12 | Proteger endpoints existentes | ✅ PASS | Todos los endpoints accounting, kardex, setup con `Depends(get_tenant_id)` + `Depends(get_current_active_user)`. Cross-tenant rechazado → 403 |

### Fase 5 — Rate Limiting

| US | Descripción | Veredicto | Evidencia |
|----|------------|:---------:|-----------|
| US-13 | Rate limiting login por IP | ✅ PASS | Redis sliding window con fallback en memoria. 5 req/min. Test: 429 tras exceder límite |
| US-14 | Rate limiting login por email | ✅ PASS | Misma implementación, key separada `login:email:{email}` |
| US-15 | Bloqueo de cuenta | ✅ PASS | 10 fallos consecutivos → locked_until +15 min → 423 "Account temporarily locked". Reset en login exitoso |

### Fase 6 — Frontend

| US | Descripción | Veredicto | Evidencia |
|----|------------|:---------:|-----------|
| US-16 | AuthContext | ✅ PASS | Estado global con login/logout/refreshSession. Restaura sesión de sessionStorage al montar. Derive tenant de JWT |
| US-17 | LoginPage | ✅ PASS | Formulario con validación cliente, manejo errores 401/423/429, redirección post-login, auto-login si sesión activa |
| US-18 | PrivateRoute | ✅ PASS | Redirect a /login si no autenticado. Soporte allowedRoles (ej: /settings solo admin/manager). Loading spinner mientras verifica |
| US-19 | API Interceptor 401 | ✅ PASS | Inyecta Authorization + X-Tenant-ID. Refresh automático con cola (solo 1 refresh en vuelo). Excluye /auth/* y /health |

---

## 🧪 Resultados de 31 Pruebas End-to-End (curl)

| # | Test | Esperado | Obtenido |
|---|------|----------|----------|
| 1 | Login exitoso | 200 + tokens | ✅ 200, JWT 277B, RT 32 chars |
| 2 | GET /me con token | 200 + perfil | ✅ 200, datos completos |
| 3 | GET /me sin token | 401 | ✅ "Not authenticated" |
| 4 | Password incorrecta | 401 genérico | ✅ "Invalid email or password" |
| 5 | Email inexistente | 401 mismo msg | ✅ "Invalid email or password" |
| 6 | Refresh exitoso | 200 + nuevos tokens | ✅ 200, rotación correcta |
| 7 | Reuso refresh rotado | 401 family revocation | ✅ "Token revoked — all sessions invalidated" |
| 8 | Token post-revocation | 401 | ✅ 401, family revocada |
| 9 | Logout | 200 | ✅ "Successfully logged out" |
| 10 | Refresh post-logout | 401 | ✅ Revocado |
| 11 | Crear usuario admin | 201 | ✅ 201, datos completos |
| 12 | Listar usuarios | 200 | ✅ 4 usuarios listados |
| 13 | Admin sin X-Tenant-ID | 400 | ✅ "X-Tenant-ID header required" |
| 14 | Password muy corta | 422 | ✅ "at least 8 characters" |
| 15 | Password sin mayúscula | 422 | ✅ "at least 1 uppercase letter" |
| 16 | Password sin número | 422 | ✅ "at least 1 number" |
| 17 | Email duplicado | 409 | ✅ "Email already in use" |
| 18 | Endpoint sin auth | 400/401 | ✅ 400 tenant missing, 401 no auth |
| 19 | Rate limiting IP | 429 | ✅ 429 "Too many login attempts" |
| 20 | Cuenta bloqueada | 423 | ✅ "Account temporarily locked. Try again in 15 minutes." |
| 21 | Health público | 200 | ✅ Sin auth requerida |
| 22 | Viewer crea usuario | 403 | ✅ "Role 'viewer' does not have sufficient permissions" |
| 23 | Viewer lista usuarios | 403 | ✅ 403 |
| 24 | Cross-tenant access | 403 | ✅ "Access denied to this tenant" |
| 25 | Token expirado | 401 | ✅ "Invalid credentials" |
| 26 | Usuario inactivo login | 403 | ✅ "Account is deactivated" |
| 27 | Usuario inactivo /me | 403 | ✅ "Inactive user" |
| 28 | JWT firma inválida | 401 | ✅ "Invalid credentials" |
| 29 | Rol inválido | 422 | ✅ "Role must be one of..." |
| 30 | Logout idempotente | 200 | ✅ Siempre 200 |
| 31 | Refresh token inexistente | 401 | ✅ "Invalid token" |

---

## 🐛 Bugs Encontrados

### BUG-01: `pyproject.toml` no incluye dependencias de auth

- **Severidad:** MEDIUM  
- **Ubicación:** `apps/backend/pyproject.toml`  
- **Descripción:** Las dependencias `pyjwt[crypto]`, `pwdlib[argon2]` y `email-validator` están en `requirements.txt` pero NO en `pyproject.toml`. Si alguien instala con `pip install -e .` o `poetry install`, el backend fallará al importar `jwt` y `pwdlib`.  
- **Fix:** Agregar a `pyproject.toml` → `dependencies`
  ```toml
  "pyjwt[crypto]>=2.10",
  "pwdlib[argon2]>=0.3",
  "email-validator>=2.2",
  ```

### BUG-02: QA environment usa la base de datos de producción

- **Severidad:** HIGH  
- **Ubicación:** `.env.qa` → `DATABASE_URL`  
- **Descripción:** `DATABASE_URL=postgresql+asyncpg://ron:ron123@postgres:5432/iaas_ronsys` apunta a la BD de producción. `DATABASE_URL_DOCKER` sí apunta a `iaas_ronsys_qa`, pero el backend lee `DATABASE_URL`. Esto significa que QA y Prod comparten la misma BD — **cualquier prueba escribe en datos reales**.  
- **Evidencia:** `docker exec iaas-backend-qa env | grep DATABASE_URL` muestra `iaas_ronsys`  
- **Fix:** Cambiar `DATABASE_URL` en `.env.qa` a: `postgresql+asyncpg://ron:ron123@postgres:5432/iaas_ronsys_qa`

---

## ⚠️ Observaciones

### OBS-01: Cobertura de auth sin tests unitarios (48% global)
Ninguno de los archivos nuevos de auth (`routers/auth.py`, `routers/admin.py`, `core/security.py`, `core/dependencies.py`, `core/tenant.py`, `models/user.py`, `schemas/auth.py`) tiene tests unitarios. La validación E2E vía curl cubre los flujos, pero no hay tests automatizados para regresiones. Esto ya estaba identificado como deuda técnica.

### OBS-02: QA port mapping usa 8000 en vez de 8001
`docker-compose.qa.yml` no sobrescribe el puerto del backend. QA expone `0.0.0.0:8000` igual que Prod, impidiendo que ambos entornos coexistan simultáneamente. El diseño original especificaba QA en :8001.

### OBS-03: LoginPage espera códigos de error en el mensaje (parsing frágil)
`LoginPage.tsx` parsea el string del error con regex `/^(\d{3})/` para mapear códigos HTTP a mensajes amigables. Si el backend cambia ligeramente el formato de error, este mapeo fallará silenciosamente. Recomendación: devolver `{status: 401, detail: "..."}` o usar headers de respuesta.

---

## 📋 Checklist de Validación Pre-Implementación (del PO)

| Criterio | Estado |
|----------|:------:|
| ¿Cada endpoint tiene definidos todos los códigos HTTP? | ✅ |
| ¿Mensajes de error de login genéricos? | ✅ |
| ¿Schemas Pydantic excluyen hashed_password? | ✅ |
| ¿Middleware de tenant es dependencia explícita, no global? | ✅ |
| ¿Endpoints públicos no requieren X-Tenant-ID? | ✅ |
| ¿Refresh token rota en cada uso? | ✅ |
| ¿Detección de reuso revoca TODA la familia? | ✅ |
| ¿Bloqueo por fallos consecutivos? | ✅ |
| ¿Rate limiting con fallback in-memory? | ✅ |
| ¿Frontend persiste sesión al recargar? | ✅ |
| ¿Interceptor 401 maneja requests concurrentes? | ✅ |
| ¿Seed de migración crea admin funcional? | ✅ |

---

## 🎯 Veredicto Final

### ✅ LISTO para Demo

**Fortalezas:**
- Auth completo y bien implementado siguiendo las 19 historias al pie de la letra
- 66 tests unitarios backend + 43 frontend + 31 smoke tests E2E manuales = **140 verificaciones**
- Familia de refresh tokens con revocación en cascada (gold standard)
- Rate limiting con Redis + fallback en memoria (resiliente)
- Cross-tenant isolation probado y funcionando
- Anti-enumeración de usuarios implementado

**Riesgos para producción:**
- 🔴 BUG-02 (HIGH): QA comparte BD con Producción — **debe resolverse antes del próximo despliegue**
- 🟡 BUG-01 (MEDIUM): pyproject.toml sin deps de auth — corregir en este sprint
- 🟡 OBS-01: Sin tests automatizados de integración HTTP para auth

**Recomendación:** ✅ Aprobar para demo con la condición de resolver BUG-02 (HIGH) en este sprint.

---

> **QA Agent** 🧪 | 2026-05-11 | IaaS-RonSys Auth Multi-Tenant v1.0
