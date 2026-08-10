# SPEC — Autenticación Multi-Tenant y Seguridad (MVP Core)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción, migración `0002`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: toda la plataforma (todos los tenants); superadmin con bypass de tenant
- **Fecha**: 2026-08-10 (spec generada por análisis del código; funcionalidad desde MVP)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

IaaS-RonSys es un ERP SaaS para la franquicia "El Segoviano" y otros tenants. Cada tenant
(empresa) debe tener aislamiento total de datos y usuarios, con roles y control de acceso,
sin exponer información de otros tenants. Objetivo de esta spec: documentar el mecanismo
completo de autenticación, autorización y seguridad que protege todos los módulos.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| JWT HS256 access (15 min) + refresh rotativo (7 días) | `app/core/security.py` | ✅ Implementado |
| Password Argon2id (pwdlib, no passlib) | `app/core/security.py` | ✅ Implementado |
| Dependencias inyectables (`get_current_user`, `get_current_active_user`, `require_role`) | `app/core/dependencies.py` | ✅ Implementado |
| Middleware tenant `X-Tenant-ID` + fallback JWT `company_id` | `app/core/dependencies.py` `_get_tenant_from_request` | ✅ Implementado |
| Rate limiting login (Redis sliding window): 5/min por IP + 5/min por email | `app/core/rate_limit.py` + `app/routers/auth.py:63-78` | ✅ Implementado |
| Bloqueo de cuenta: 10 fallos → `locked_until` 15 min (HTTP **423** con `Retry-After`) | `app/routers/auth.py:87-106` | ✅ Implementado |
| Family revocation (refresh reuse revoca todas las sesiones) | `app/routers/auth.py:226` | ✅ Implementado |
| Modelos `User` + `RefreshToken` | `app/models/user.py` | ✅ Implementado |
| Migración `0002_users_auth` | `app/adapters/alembic/versions/0002_users_auth.py` | ✅ Aplicada en prod |
| Endpoints `/api/auth/*` y `/api/admin/*` | `app/routers/auth.py`, `app/routers/admin.py` | ✅ Desplegados |

### 2.2 Flujo de login (verificado)

```
POST /api/auth/login
  → rate limiter (IP + email, Redis)
  → verificar_password (Argon2id, constant-time)
  → si falla: failed_login_attempts += 1; si >= 10 → `locked_until = now + 15 min` (login devuelve 423 Retry-After)
  → si ok: reset failed_login_attempts, generar access_token (15 min) + refresh_token (7 días)
  → responde LoginResponse (token + usuario sin campos sensibles)
```

- **Refresh**: POST `/api/auth/refresh` — valida refresh token, family revocation (reuso revoca toda la familia), emite nuevo par.
- **Logout**: POST `/api/auth/logout` — revoca el refresh token.
- **Me**: GET `/api/auth/me` — devuelve usuario actual (sin `hashed_password`, `failed_login_attempts`).

### 2.3 Autorización por roles

- Roles: `admin`, `manager`, `operator`, `viewer` + `superadmin` (bypass total, migración 0014).
- `require_role(*roles)` valida contra `current_user.role`; superadmin siempre pasa.
- Validación cruzada de tenant: si `user.role != "superadmin"` y `X-Tenant-ID != user.company_id` → 403.
- Endpoints públicos (`/api/public/*`) no requieren JWT, con rate limit por slug (60 req/min).

---

## 3. Fase P — Propuesta y contratos

### 3.1 Modelo de datos (migración 0002)

```sql
users (
  id serial PK,
  company_id int NOT NULL REFERENCES companies(id),   -- tenant
  email varchar UNIQUE NOT NULL,
  hashed_password varchar NOT NULL,                    -- Argon2id
  full_name varchar,
  role varchar NOT NULL DEFAULT 'viewer',              -- admin|manager|operator|viewer|superadmin
  is_active bool DEFAULT true,
  failed_login_attempts int DEFAULT 0,
  created_at, updated_at
)

refresh_tokens (
  id serial PK,
  user_id int NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash varchar UNIQUE NOT NULL,                  -- hash del token, nunca el valor crudo
  family_id uuid NOT NULL,                             -- familia de rotación
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz NULL,
  replaced_by int NULL,
  created_at
)
```

### 3.2 Endpoints

| Método | Ruta | Descripción | Protección |
|---|---|---|---|
| POST | `/api/auth/login` | Login con email+password, rate limit | Público (rate-limited) |
| POST | `/api/auth/refresh` | Rotar refresh token (family) | Refresh token |
| POST | `/api/auth/logout` | Revocar refresh token | Bearer |
| GET | `/api/auth/me` | Usuario actual | Bearer |
| POST | `/api/admin/users` | Crear usuario en tenant del admin | Admin |
| GET | `/api/admin/users` | Listar usuarios con filtros | Admin |
| GET/PUT | `/api/admin/company/settings` | Settings de la empresa | Admin/Manager |

### 3.3 Criterios de aceptación (verificados)

- CA1: login exitoso devuelve access (15 min) + refresh (7 días). ✅
- CA2: 5 intentos fallidos/min por IP → 429 "Too many login attempts from this IP". ✅
- CA3: 10 fallos consecutivos → cuenta bloqueada 15 min (HTTP 423 con `Retry-After`). ✅
- CA4: usuario de tenant A con `X-Tenant-ID=B` → 403. ✅
- CA5: refresh token reusado → revoca toda la familia (nuevos intentos 401). ✅
- CA6: passwords con Argon2id (verificado en hash `$argon2id$...`). ✅

---

## 4. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| JWT + hashing | `app/core/security.py` | §2.1, §3.1 |
| Dependencias | `app/core/dependencies.py` | §2.3 |
| Login/refresh/logout/me | `app/routers/auth.py` | §2.2, §3.2 |
| Admin users | `app/routers/admin.py` | §3.2 |
| Rate limit | `app/core/rate_limit.py` | §2.1 |
| Modelos | `app/models/user.py` | §3.1 |
| Migración | `0002_users_auth.py` | §3.1 |

> ⚠️ Si cambias el flujo de auth (roles, expiración, rate limit, modelo User), **actualiza esta spec** (Spec Anchor).
