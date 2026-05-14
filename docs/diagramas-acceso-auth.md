# Diagramas de Estructura de Acceso — IaaS-RonSys

## 1. Flujo Completo de Autenticación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLUJO DE LOGIN END-TO-END                          │
└─────────────────────────────────────────────────────────────────────────────┘

  USUARIO                   FRONTEND                          BACKEND
    │                          │                                │
    │  1. Abre la app          │                                │
    │ ───────────────────────> │                                │
    │                          │  2. AuthProvider mount         │
    │                          │  ┌─────────────────────────┐   │
    │                          │  │ sessionStorage tiene     │   │
    │                          │  │ refresh_token?           │   │
    │                          │  └──────┬──────────┬────────┘   │
    │                          │         │ Sí       │ No         │
    │                          │         v          v            │
    │                          │  POST /auth/refresh  Muestra    │
    │                          │ ──────────────────>  /login     │
    │                          │ <──────────────────             │
    │                          │  Restaurar sesión              │
    │                          │                                 │
    │  3. Ingresa email+pass  │                                 │
    │ ───────────────────────> │                                 │
    │                          │  4. POST /api/auth/login        │
    │                          │ ──────────────────────────────> │
    │                          │                                 │
    │                          │                    ┌────────────────────────┐
    │                          │                    │ 5. Rate limit por IP  │
    │                          │                    │    (5/min Redis)      │
    │                          │                    │    ──> 429 si excede  │
    │                          │                    ├────────────────────────┤
    │                          │                    │ 6. Rate limit por     │
    │                          │                    │    email (5/min)      │
    │                          │                    │    ──> 429 si excede  │
    │                          │                    ├────────────────────────┤
    │                          │                    │ 7. Cuenta bloqueada?  │
    │                          │                    │    locked_until > now │
    │                          │                    │    ──> 423 Locked     │
    │                          │                    ├────────────────────────┤
    │                          │                    │ 8. verify_password    │
    │                          │                    │    (Argon2id)         │
    │                          │                    │    fail ──> 401       │
    │                          │                    │    + incrementar      │
    │                          │                    │      failed_attempts  │
    │                          │                    │    + si >=10: bloquear│
    │                          │                    │      15 min           │
    │                          │                    ├────────────────────────┤
    │                          │                    │ 9. is_active=False?   │
    │                          │                    │    ──> 403            │
    │                          │                    ├────────────────────────┤
    │                          │                    │ 10. ÉXITO:            │
    │                          │                    │  - Reset attempts     │
    │                          │                    │  - JWT HS256 (15min)  │
    │                          │                    │  - Refresh UUID v4    │
    │                          │                    │    SHA-256 → DB       │
    │                          │                    └────────────────────────┘
    │                          │                                 │
    │                          │  { access_token, refresh_token, │
    │                          │    expires_in, user }           │
    │                          │ <────────────────────────────── │
    │                          │                                 │
    │                          │  11. authStore.setTokens()      │
    │                          │  ┌───────────────────────────┐  │
    │                          │  │ access_token  → memoria   │  │
    │                          │  │ refresh_token → sessionSt │  │
    │                          │  └───────────────────────────┘  │
    │                          │                                 │
    │  12. Redirect a ruta    │                                 │
    │      solicitada o /     │                                 │
    │ <─────────────────────── │                                 │
```

---

## 2. Arquitectura de Tokens y Sesión

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     GESTIÓN DE TOKENS Y SESIÓN                           │
└──────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────┐                         ┌──────────────────────┐
  │  ACCESS TOKEN   │                         │   REFRESH TOKEN      │
  │  ─────────────  │                         │   ──────────────     │
  │  Tipo: JWT      │                         │   Tipo: UUID v4      │
  │  Algoritmo:HS256│                         │   Opaque             │
  │  Expira: 15 min │                         │   Expira: 7 días     │
  │  Almacén:RAM    │                         │   Almacén:sessionSt  │
  │                 │                         │   DB: SHA-256 hash   │
  │  Payload:       │                         │                      │
  │  {              │                         │   Rotación en cada   │
  │   sub: user_id, │                         │   /auth/refresh:     │
  │   company_id,   │                         │   old → revoked      │
  │   role,         │                         │   new → created      │
  │   email,        │                         │   linked por         │
  │   exp, iat, jti │                         │   replaced_by_id     │
  │  }              │                         │                      │
  └────────┬────────┘                         └──────────┬───────────┘
           │                                              │
           │  Se envía en cada request:                   │
           │  Authorization: Bearer <access_token>        │
           │  X-Tenant-ID: <company_id>                   │
           │                                              │
           v                                              v
  ┌─────────────────────────────────────────────────────────────────────┐
  │                      API CLIENT (api.ts)                             │
  │                                                                      │
  │  • Auto-inyecta Authorization + X-Tenant-ID                         │
  │  • En 401: lanza refresh automático (singleton promise)             │
  │  • Race-condition safe: requests concurrentes comparten             │
  │    el mismo refreshPromise                                          │
  │  • Skip auth:  ["/auth/", "/health"]                                │
  │  • Skip retry: ["/auth/login", "/auth/refresh", "/auth/logout"]     │
  └─────────────────────────────────────────────────────────────────────┘
```

### Ciclo de vida del Refresh Token (Rotación + Detección de robo)

```
  LOGIN                    REFRESH #1               REFRESH #2
  ─────                    ──────────               ──────────

  Token A ──creado──>     Token A ──revocado──>    Token A (ya revocado)
                           │                        │
                           v                        v
                         Token B ──creado──>      Token B ──revocado──>
                                                   │         │
                                                   v         v
                                                 Token C   Token C
                                                 (creado)  (válido)

  ⚠️  Si se reusa Token A (ya revocado):
  ┌──────────────────────────────────────────────────────┐
  │  DETECCIÓN DE ROBO → Revocar TODOS los tokens       │
  │  del usuario (family revocation)                     │
  │  → 401 "Token revoked — all sessions invalidated"   │
  └──────────────────────────────────────────────────────┘
```

---

## 3. Modelo de Roles y Permisos (RBAC)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          SISTEMA DE ROLES                                │
└──────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  ADMIN   │     │ MANAGER  │     │ OPERATOR │     │  VIEWER  │
  │ ──────── │     │ ──────── │     │ ──────── │     │ ──────── │
  │Acceso    │     │Acceso    │     │Acceso    │     │Solo      │
  │completo  │     │alto      │     │medio     │     │lectura   │
  └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
       │                │                │                │
       v                v                v                v
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        PERMISOS POR RUTA                            │
  ├─────────────────────┬───────────────────────────────────────────────┤
  │  Ruta               │  Roles permitidos                            │
  ├─────────────────────┼───────────────────────────────────────────────┤
  │  / (Dashboard)      │  admin, manager, operator, viewer            │
  │  /setup             │  admin, manager, operator, viewer            │
  │  /simulador         │  admin, manager, operator, viewer            │
  │  /reportes          │  admin, manager, operator, viewer            │
  │  /kardex            │  admin, manager, operator, viewer            │
  │  /cashflow          │  admin, manager, operator, viewer            │
  │  /ventas            │  admin, manager, operator, viewer            │
  │  /settings          │  admin, manager                  ← Restringido│
  │  /caja (POS)        │  admin, manager, operator        ← Restringido│
  │  /ventas/nueva      │  admin, manager, operator        ← Restringido│
  ├─────────────────────┼───────────────────────────────────────────────┤
  │  POST /admin/users  │  admin                           ← Solo admin │
  │  GET  /admin/users  │  admin                           ← Solo admin │
  │  PUT  /admin/co.    │  admin                           ← Solo admin │
  │  GET  /admin/co.    │  admin, manager, operator, viewer              │
  └─────────────────────┴───────────────────────────────────────────────┘
```

### Matriz de acceso visual

```
  ┌────────────────┬───────┬───────┬───────┬───────┐
  │   Recurso      │ ADMIN │MNGR   │OPRTR  │VIEWER │
  ├────────────────┼───────┼───────┼───────┼───────┤
  │ Dashboard      │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Setup          │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Simulador      │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Reportes       │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Kardex         │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Cashflow       │  ✅   │  ✅   │  ✅   │  ✅   │
  │ Ventas (lista) │  ✅   │  ✅   │  ✅   │  ✅   │
  ├────────────────┼───────┼───────┼───────┼───────┤
  │ Settings       │  ✅   │  ✅   │  ❌   │  ❌   │
  │ Caja (POS)     │  ✅   │  ✅   │  ✅   │  ❌   │
  │ Nueva Venta    │  ✅   │  ✅   │  ✅   │  ❌   │
  ├────────────────┼───────┼───────┼───────┼───────┤
  │ Crear usuarios │  ✅   │  ❌   │  ❌   │  ❌   │
  │ Listar usuarios│  ✅   │  ❌   │  ❌   │  ❌   │
  │ Config empresa │  ✅   │  ❌   │  ❌   │  ❌   │
  └────────────────┴───────┴───────┴───────┴───────┘
```

---

## 4. Protección de Rutas — Frontend

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ROUTE GUARDS — FRONTEND                               │
└──────────────────────────────────────────────────────────────────────────┘

  Navegador
      │
      v
  ┌──────────────────────┐
  │  <AuthProvider>      │  ← React Context global
  │  (AuthContext.tsx)   │
  │                      │
  │  Provee:             │
  │  • user              │
  │  • tenant            │
  │  • isAuthenticated   │
  │  • isLoading         │
  │  • login()           │
  │  • logout()          │
  │  • refreshSession()  │
  └──────────┬───────────┘
             │
             v
  ┌──────────────────────────────────────────────────────┐
  │               <PrivateRoute>                         │
  │            (PrivateRoute.tsx)                        │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐  │
  │  │  1. isLoading?  → Spinner ("Verificando...")  │  │
  │  │  2. !isAuthenticated? → Redirect /login       │  │
  │  │     + guarda ruta original en location.state   │  │
  │  │  3. allowedRoles && role ∉ allowedRoles?      │  │
  │  │     → "Acceso Denegado" + link a dashboard    │  │
  │  │  4. OK → renderizar children                  │  │
  │  └────────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────────┘
             │
             v
  ┌──────────────────────────────────────────────────────┐
  │              App.tsx — Rutas                         │
  │                                                      │
  │  PÚBLICAS (sin PrivateRoute):                        │
  │  ├── /login                                          │
  │                                                      │
  │  PROTEGIDAS (cualquier rol autenticado):             │
  │  ├── /  (Dashboard)     <PrivateRoute>              │
  │  ├── /setup             <PrivateRoute>              │
  │  ├── /simulador         <PrivateRoute>              │
  │  ├── /reportes          <PrivateRoute>              │
  │  ├── /kardex            <PrivateRoute>              │
  │  ├── /cashflow          <PrivateRoute>              │
  │  ├── /ventas            <PrivateRoute>              │
  │                                                      │
  │  RESTRINGIDAS (roles específicos):                   │
  │  ├── /settings          <PrivateRoute ["admin",     │
  │  │                          "manager"]>             │
  │  ├── /caja              <PrivateRoute ["admin",     │
  │  │                          "manager","operator"]>  │
  │  └── /ventas/nueva      <PrivateRoute ["admin",     │
  │                              "manager","operator"]>  │
  └──────────────────────────────────────────────────────┘
```

---

## 5. Protección de Endpoints — Backend

```
┌──────────────────────────────────────────────────────────────────────────┐
│              DEPENDENCIAS DE AUTENTICACIÓN — BACKEND                      │
│              (FastAPI Depends chain)                                      │
└──────────────────────────────────────────────────────────────────────────┘

  Request HTTP
      │
      v
  ┌─────────────────────────────────────────────────────────────┐
  │  Middleware (orden de ejecución)                             │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ 1. CORS           → Orígenes permitidos               │  │
  │  │ 2. Security Headers → CSP, HSTS, X-Frame-Options     │  │
  │  │ 3. Logging         → method, path, status, duration   │  │
  │  │ 4. Rate Limit      → 100/h por IP+path (in-memory)   │  │
  │  └───────────────────────────────────────────────────────┘  │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               v
  ┌─────────────────────────────────────────────────────────────┐
  │  OAuth2PasswordBearer                                      │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ Extrae token del header:                              │  │
  │  │ Authorization: Bearer <jwt>                           │  │
  │  │ auto_error=False (permite endpoints públicos)         │  │
  │  └───────────────────────────────────────────────────────┘  │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               v
  ┌─────────────────────────────────────────────────────────────┐
  │  get_current_user                                          │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ 1. decode_access_token(jwt) → payload                 │  │
  │  │ 2. Buscar user por payload["sub"] en DB               │  │
  │  │ 3. Si X-Tenant-ID presente:                          │  │
  │  │    user.company_id == X-Tenant-ID?                    │  │
  │  │    ❌ No → 403 "Access denied to this tenant"         │  │
  │  │    ✅ Sí → retornar user                              │  │
  │  └───────────────────────────────────────────────────────┘  │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               v
  ┌─────────────────────────────────────────────────────────────┐
  │  get_current_active_user                                   │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ Depende de: get_current_user                          │  │
  │  │ user.is_active == True?                               │  │
  │  │ ❌ No → 403 "Account is deactivated"                  │  │
  │  │ ✅ Sí → retornar user                                 │  │
  │  └───────────────────────────────────────────────────────┘  │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               v
  ┌─────────────────────────────────────────────────────────────┐
  │  require_role(*allowed_roles)                              │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ Depende de: get_current_active_user                   │  │
  │  │ user.role in allowed_roles?                           │  │
  │  │ ❌ No → 403 "Role 'x' insufficient permissions"      │  │
  │  │ ✅ Sí → retornar user                                 │  │
  │  │                                                       │  │
  │  │ Uso:                                                  │  │
  │  │  require_role("admin")              → solo admin      │  │
  │  │  require_role("admin","manager")    → admin + manager │  │
  │  └───────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
```

### Mapa de endpoints por nivel de protección

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  PÚBLICOS (sin auth)                                            │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │ POST /api/auth/login      → Login                        │  │
  │  │ POST /api/auth/refresh    → Renovar tokens               │  │
  │  │ POST /api/auth/logout     → Cerrar sesión (idempotente)  │  │
  │  │ GET  /health              → Health check                 │  │
  │  └───────────────────────────────────────────────────────────┘  │
  ├─────────────────────────────────────────────────────────────────┤
  │  AUTENTICADO (cualquier rol activo)                             │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │ GET  /api/auth/me         → Perfil del usuario           │  │
  │  │ GET  /api/admin/company   → Config de empresa            │  │
  │  │ ALL  /api/accounting/*    → 20+ endpoints contables      │  │
  │  │ ALL  /api/sales/*         → 9 endpoints de ventas        │  │
  │  │ ALL  /api/simulator/*     → 5 endpoints simulador        │  │
  │  │ ALL  /api/setup/*         → 4 endpoints configuración    │  │
  │  └───────────────────────────────────────────────────────────┘  │
  ├─────────────────────────────────────────────────────────────────┤
  │  SOLO ADMIN                                                     │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │ POST /api/admin/users     → Crear usuario                │  │
  │  │ GET  /api/admin/users     → Listar usuarios              │  │
  │  │ PUT  /api/admin/company   → Modificar config empresa     │  │
  │  └───────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 6. Multi-Tenancy — Aislamiento por Empresa

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MODELO MULTI-TENANT                                  │
└──────────────────────────────────────────────────────────────────────────┘

  Request con JWT + X-Tenant-ID
      │
      v
  ┌──────────────────────────────────────────────────────┐
  │  1. JWT contiene company_id                          │
  │  2. Header X-Tenant-ID enviado por frontend          │
  │  3. get_current_user:                                │
  │     JWT.company_id == X-Tenant-ID ?                  │
  │     ❌ → 403 "Access denied to this tenant"          │
  │     ✅ → Continúa                                    │
  └───────────────────┬──────────────────────────────────┘
                      │
                      v
  ┌──────────────────────────────────────────────────────┐
  │  4. get_tenant_id (dependencia explícita)            │
  │     Extrae y valida X-Tenant-ID del header           │
  │     ❌ → 400 si falta o no es numérico               │
  └───────────────────┬──────────────────────────────────┘
                      │
                      v
  ┌──────────────────────────────────────────────────────┐
  │  5. UserRepository._scope()                          │
  │     Todas las queries agregan:                       │
  │     WHERE company_id = :tenant_id                    │
  │                                                      │
  │     Aislamiento a nivel de datos:                    │
  │     Usuario de company=1 NUNCA ve datos de           │
  │     company=2                                        │
  └──────────────────────────────────────────────────────┘


  ┌────────────────┐          ┌────────────────┐
  │   Company 1    │          │   Company 2    │
  │  ┌──────────┐  │          │  ┌──────────┐  │
  │  │ User A   │  │          │  │ User X   │  │
  │  │ admin    │  │          │  │ manager  │  │
  │  ├──────────┤  │          │  ├──────────┤  │
  │  │ User B   │  │          │  │ User Y   │  │
  │  │ viewer   │  │          │  │ operator │  │
  │  └──────────┘  │          │  └──────────┘  │
  │                │          │                │
  │  Datos aislados│          │  Datos aislados│
  │  (scoped por   │          │  (scoped por   │
  │   company_id)  │          │   company_id)  │
  └────────────────┘          └────────────────┘
         │                           │
         └───────────┬───────────────┘
                     │
                     v
        ┌──────────────────────┐
        │    Base de Datos     │
        │  Tabla: users        │
        │  WHERE company_id=N  │
        └──────────────────────┘
```

---

## 7. Modelo de Datos — User y RefreshToken

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MODELO DE DATOS — AUTH                               │
└──────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────┐         ┌──────────────────────────────┐
  │          users              │         │       refresh_tokens         │
  ├─────────────────────────────┤         ├──────────────────────────────┤
  │ id            PK (autoinc)  │    ┌───>│ id             PK (autoinc)  │
  │ email         VARCHAR UNIQUE│    │    │ user_id        FK ───────────┤──┐
  │ hashed_pass   VARCHAR(255)  │    │    │ company_id     FK ──┐       │  │
  │ full_name     VARCHAR(150)  │    │    │ token_hash     VARCHAR(64)  │  │
  │ role          VARCHAR(20)   │    │    │                UNIQUE        │  │
  │   CHECK IN                   │    │    │ expires_at     DATETIME     │  │
  │   ('admin','manager',       │    │    │ revoked_at     DATETIME NULL│  │
  │    'operator','viewer')     │    │    │ created_at     DATETIME     │  │
  │ company_id    FK → companies│    │    │ created_by_ip  VARCHAR(45)  │  │
  │ is_active     BOOL (def:T) │    │    │ user_agent     VARCHAR(512) │  │
  │ is_verified   BOOL (def:F) │    │    │ replaced_by_id FK → self    │─┐│
  │ failed_login  INT (def:0)  │    │    └──────────────────────────────┘││
  │ locked_until  DATETIME NULL│    │                                    ││
  │ last_login_at DATETIME NULL│    │                                    ││
  │ created_at    DATETIME     │    │         ┌──────────────────┐       ││
  │ updated_at    DATETIME     │    │         │  Rotación chain  │       ││
  └─────────────────────────────┘    │         │                  │       ││
                                     │         │  Token A         │       ││
  ┌─────────────────────────────┐    │         │  replaced_by ────┼──┐    ││
  │        companies            │    │         │                  │  │    ││
  ├─────────────────────────────┤    │         │  Token B         │  │    ││
  │ id            PK            │◄───┤         │  replaced_by ────┼──┼──┐ ││
  │ name          VARCHAR       │    │         │                  │  │  │ ││
  │ settings      JSON          │    │         │  Token C (activo)│  │  │ ││
  └─────────────────────────────┘    │         │  replaced_by=NULL│  │  │ ││
                                     │         └──────────────────┘  │  │ ││
                                     │                               │  │ ││
                                     └───────────────────────────────┘  │ ││
                                                                        │ ││
                                     ┌──────────────────────────────────┘ ││
                                     │  replaced_by_id apunta al token   ││
                                     │  que lo reemplazó (cadena)        ││
                                     └────────────────────────────────────┘│
                                                                            │
                                     ┌─────────────────────────────────────┘
                                     │  user_id CASCADE: si se borra un user
                                     │  se borran todos sus refresh_tokens
                                     └────────────────────────────────────
```

---

## 8. Seguridad — Capas de Defensa

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     CAPAS DE SEGURIDAD                                   │
└──────────────────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │  CAPA 1: RED                                                 │
  │  • CORS: solo orígenes permitidos                            │
  │  • Security Headers: CSP, HSTS, X-Frame-Options, XSS,       │
  │    Referrer-Policy                                            │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────v───────────────────────────────────┐
  │  CAPA 2: RATE LIMITING                                       │
  │  • Global: 100 req/h por IP+path (middleware)                │
  │  • Login por IP: 5 req/min (Redis sliding window)           │
  │  • Login por email: 5 req/min (Redis sliding window)        │
  │  • Respuestas: 429 Too Many Requests                        │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────v───────────────────────────────────┐
  │  CAPA 3: PROTECCIÓN DE CUENTA                                │
  │  • Anti-enumeración: mismo error para email inexistente      │
  │    y contraseña incorrecta (401 genérico)                    │
  │  • Bloqueo automático tras 10 intentos fallidos (15 min)    │
  │  • Argon2id: hash resistente a timing attacks y GPU         │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────v───────────────────────────────────┐
  │  CAPA 4: TOKEN SECURITY                                      │
  │  • Access token: JWT corto (15 min) → menor ventana de robo │
  │  • Refresh token: opaque (UUID) → no revela payload         │
  │  • Refresh token: hasheado en DB (SHA-256) → nunca en claro │
  │  • Rotación: nuevo refresh en cada refresh → 1-use token    │
  │  • Detección de robo: reuso de token revocado →             │
  │    revocar TODOS los tokens del usuario                      │
  │  • JTI en JWT: permite futura lista negra de JWT            │
  └───────────────────────────┬───────────────────────────────────┘
                              │
  ┌───────────────────────────v───────────────────────────────────┐
  │  CAPA 5: AUTORIZACIÓN                                        │
  │  • RBAC: 4 roles (admin, manager, operator, viewer)         │
  │  • Multi-tenant: aislamiento por company_id                 │
  │  • Validación cruzada: JWT.company_id == X-Tenant-ID        │
  │  • Scoping en repositorios: WHERE company_id = :tenant_id   │
  │  • is_active check: usuarios inactivos → 403                │
  └───────────────────────────────────────────────────────────────┘
```

---

## 9. Archivos Clave del Sistema de Autenticación

| Capa | Archivo | Función |
|------|---------|---------|
| **Frontend — Página** | `apps/web/src/pages/Login.tsx` | Formulario de login |
| **Frontend — Context** | `apps/web/src/contexts/AuthContext.tsx` | Estado global de auth |
| **Frontend — Guard** | `apps/web/src/components/auth/PrivateRoute.tsx` | Protección de rutas |
| **Frontend — Store** | `apps/web/src/services/authStore.ts` | Almacenamiento de tokens |
| **Frontend — API** | `apps/web/src/services/api.ts` | Cliente HTTP con interceptores |
| **Frontend — Tipos** | `apps/web/src/types/auth.ts` | Interfaces User, Tenant, Tokens |
| **Frontend — Rutas** | `apps/web/src/App.tsx` | Definición de rutas protegidas |
| **Backend — Router** | `apps/backend/app/routers/auth.py` | Endpoints login/refresh/logout/me |
| **Backend — Admin** | `apps/backend/app/routers/admin.py` | CRUD usuarios (solo admin) |
| **Backend — Security** | `apps/backend/app/core/security.py` | JWT + Argon2id |
| **Backend — Dependencies** | `apps/backend/app/core/dependencies.py` | get_current_user, require_role |
| **Backend — Tenant** | `apps/backend/app/core/tenant.py` | get_tenant_id |
| **Backend — Rate Limit** | `apps/backend/app/core/rate_limit.py` | Redis sliding window |
| **Backend — Model** | `apps/backend/app/models/user.py` | User + RefreshToken ORM |
| **Backend — Schema** | `apps/backend/app/schemas/auth.py` | Pydantic request/response |
| **Backend — Repo** | `apps/backend/app/adapters/db/repositories/user.py` | Queries con tenant scoping |
| **Backend — Config** | `apps/backend/app/config.py` | secret_key, expiraciones, lockout |
| **Backend — Middleware** | `apps/backend/app/monitoring/middleware.py` | Logging, rate limit, headers |

---

## 10. Funcionalidades Pendientes

| Feature | Estado | Referencia |
|---------|--------|------------|
| Registro público | No implementado | No existe endpoint |
| Reset/Recuperar contraseña | Planificado | CHANGELOG: "🔜 Email verification + password reset" |
| OAuth2 / Social login (Google) | Planificado | CHANGELOG: "🔜 OAuth2 social login (Google)" |
| httpOnly cookies para refresh token | Planificado | CHANGELOG: "🔜 httpOnly cookies para refresh token" |
| RBAC con tabla de permisos separada | No implementado | Roles son strings planos |
| Verificación de email | Campo existe (`is_verified`) pero no se valida en login | |
| Refresh tokens en Redis | Parcial | Rate limiter usa Redis; tokens usan PostgreSQL |
