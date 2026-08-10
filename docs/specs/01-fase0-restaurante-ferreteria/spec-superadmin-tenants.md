# SPEC — Superadmin y Gestión de Tenants (Empresas, Usuarios, Dashboard)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción, migración `0014`)
- **Proyecto**: IaaS-RonSys — ERP SaaS multi-tenant
- **Alcance**: rol `superadmin` (acceso a todos los tenants, bypass de aislamiento)
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

La plataforma SaaS necesita una consola de administración global: **crear empresas (tenants),
gestionar usuarios de todas las empresas, activar/desactivar cuentas y ver métricas
agregadas del dashboard**. El rol `superadmin` puede acceder a cualquier tenant sin la
validación cruzada de `X-Tenant-ID`.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Router superadmin | `app/routers/superadmin.py` (546 ln) | ✅ Desplegado |
| Role superadmin | `app/models/user.py` + migración `0014_superadmin_role` | ✅ Implementado |
| Bypass de tenant | `app/core/dependencies.py` `get_current_user` (superadmin salta validación) | ✅ Implementado |
| Frontend | `pages/superadmin/Companies.tsx`, `Users.tsx`, `Dashboard.tsx` + rutas `/superadmin*` | ✅ Desplegado |
| Tests | `test_settings.py` (relacionado), `test_caso7_investment.py` | ✅ Parcial |

### 2.2 Endpoints (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/superadmin/companies` | Crear empresa (tenant) (201) |
| GET | `/api/superadmin/companies` | Listar empresas |
| GET | `/api/superadmin/companies/{id}` | Detalle empresa |
| PUT | `/api/superadmin/companies/{id}` | Actualizar empresa |
| DELETE | `/api/superadmin/companies/{id}` | Eliminar empresa (204) |
| POST | `/api/superadmin/users` | Crear usuario (cualquier tenant) (201) |
| GET | `/api/superadmin/users` | Listar usuarios (todas las empresas) |
| PUT | `/api/superadmin/users/{id}` | Actualizar usuario |
| DELETE | `/api/superadmin/users/{id}` | Eliminar usuario |
| POST | `/api/superadmin/users/{id}/activate` | Activar/desactivar usuario |
| GET | `/api/superadmin/dashboard` | Métricas globales (empresas, usuarios, actividad) |

### 2.3 Reglas (verificadas)

- **R1**: solo rol `superadmin` accede a `/api/superadmin/*` (require_role).
- **R2**: superadmin no requiere `X-Tenant-ID` y puede operar en cualquier tenant.
- **R3**: creación de empresa habilita nuevo tenant (aislamiento automático).
- **R4**: `activate` conmuta `is_active` (bloqueo/desbloqueo de cuenta).

### 2.4 Criterios de aceptación (verificados)

- CA1: CRUD de empresas/usuarios solo con rol superadmin. ✅
- CA2: usuario superadmin accede a cualquier tenant sin 403. ✅
- CA3: dashboard devuelve métricas globales. ✅
- CA4: activar/desactivar usuario surte efecto inmediato (login 403 si inactivo). ✅

---

## 3. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Router | `app/routers/superadmin.py` | §2.2 |
| Bypass tenant | `app/core/dependencies.py` | §2.1 |
| Role + migración | `app/models/user.py`, `0014_superadmin_role` | §2.1 |
| Frontend | `pages/superadmin/*` | §2.1 |

> ⚠️ Si cambias permisos de superadmin, CRUD de empresas/usuarios o el dashboard, **actualiza esta spec** (Spec Anchor).
