# 📋 Historias de Usuario — Sistema de Autenticación Multi-Tenant

> **Autor:** Product Owner Agent
> **Fecha:** 2026-05-10
> **Arquitectura de referencia:** `docs/architecture/auth-multi-tenant-design.md`
> **Arquitectura aprobada por:** Ron (2026-05-10)

---

## Resumen de Fases

| Fase | Historias | Alcance |
|------|-----------|---------|
| Fase 1 | US-01, US-02, US-03 | Core Security + Modelos |
| Fase 2 | US-04, US-05, US-06, US-07 | Auth Endpoints |
| Fase 3 | US-08, US-09 | Admin Users |
| Fase 4 | US-10, US-11, US-12 | Tenant Scoping |
| Fase 5 | US-13, US-14, US-15 | Rate Limiting Redis |
| Fase 6 | US-16, US-17, US-18, US-19 | Frontend |

---

## Fase 1 — Core Security + Modelos

---

### US-01: Configuración de Seguridad Base

**Como** desarrollador del backend,
**quiero** tener configuradas todas las variables de seguridad y el motor de hashing de contraseñas,
**para** que el sistema de autenticación tenga una base criptográfica sólida y configurable desde el día 1.

#### Criterios de Aceptación

```gherkin
Escenario: SECRET_KEY se genera y almacena de forma segura
  Given el archivo .env en la raíz del proyecto
  When se configura la variable SECRET_KEY
  Then la clave debe tener al menos 32 bytes (64 caracteres hexadecimales)
  And la clave NUNCA debe estar hardcodeada en archivos .py
  And el archivo .env debe ser ignorado por .gitignore

Escenario: Variables de configuración de auth se cargan correctamente
  Given el archivo config.py con el modelo Settings
  When la aplicación se inicia
  Then debe existir SECRET_KEY de tipo str
  And debe existir ACCESS_TOKEN_EXPIRE_MINUTES con valor por defecto 15
  And debe existir REFRESH_TOKEN_EXPIRE_DAYS con valor por defecto 7
  And debe existir LOGIN_MAX_ATTEMPTS con valor por defecto 10
  And debe existir LOGIN_LOCK_MINUTES con valor por defecto 15

Escenario: Hashing de contraseñas usa Argon2id
  Given el módulo core/security.py
  When se hashea una contraseña con hash_password("MiPassword123")
  Then el resultado debe ser un string de hash de Argon2id
  And el hash debe ser diferente cada vez (salt aleatorio)
  And la verificación con verify_password("MiPassword123", hash) debe retornar True
  And la verificación con verify_password("WrongPassword", hash) debe retornar False
  And la verificación debe ser constant-time (resistente a timing attacks)

Escenario: Email validation rechaza formatos inválidos
  Given el validador de email configurado con email-validator
  When se valida "notanemail"
  Then debe lanzar error de validación
  When se valida "user@example.com"
  Then debe ser aceptado como válido
```

#### Notas Técnicas

- **Archivos nuevos:** `config.py` (modificar, agregar 5 variables), `.env` (modificar)
- **Librerías:** `pyjwt[crypto]`, `pwdlib[argon2]`, `email-validator`
- **Función `hash_password`** en `core/security.py` usando `pwdlib.hash()` con Argon2id por defecto
- **Función `verify_password`** en `core/security.py` usando `pwdlib.verify()`
- **Generar SECRET_KEY:** `openssl rand -hex 32`

---

### US-02: Modelos de Datos User y RefreshToken

**Como** arquitecto de datos,
**quiero** tener los modelos ORM de `users` y `refresh_tokens` con su migración Alembic,
**para** que la capa de persistencia esté lista antes de implementar los endpoints de auth.

#### Criterios de Aceptación

```gherkin
Escenario: Migración crea tabla users con todas las columnas
  Given la migración Alembic 0002_users_auth ejecutada
  When consulto la tabla users en PostgreSQL
  Then debe tener columna id (SERIAL PK)
  And email VARCHAR(255) UNIQUE NOT NULL
  And hashed_password VARCHAR(255) NOT NULL
  And full_name VARCHAR(150) NOT NULL
  And role tipo ENUM ('admin','manager','operator','viewer') con default 'viewer'
  And company_id INTEGER NOT NULL con FK a companies(id) ON DELETE CASCADE
  And is_active BOOLEAN DEFAULT TRUE
  And is_verified BOOLEAN DEFAULT FALSE
  And failed_login_attempts INTEGER DEFAULT 0
  And locked_until TIMESTAMPTZ nullable
  And last_login_at TIMESTAMPTZ nullable
  And created_at TIMESTAMPTZ DEFAULT NOW()
  And updated_at TIMESTAMPTZ DEFAULT NOW()

Escenario: Migración crea tabla refresh_tokens con todas las columnas
  Given la migración Alembic 0002_users_auth ejecutada
  When consulto la tabla refresh_tokens en PostgreSQL
  Then debe tener columna id (SERIAL PK)
  And user_id INTEGER NOT NULL con FK a users(id) ON DELETE CASCADE
  And company_id INTEGER NOT NULL con FK a companies(id) ON DELETE CASCADE
  And token_hash VARCHAR(64) UNIQUE NOT NULL
  And expires_at TIMESTAMPTZ NOT NULL
  And revoked_at TIMESTAMPTZ nullable
  And created_at TIMESTAMPTZ DEFAULT NOW()
  And created_by_ip VARCHAR(45) nullable
  And user_agent VARCHAR(512) nullable
  And replaced_by_id INTEGER con FK a refresh_tokens(id) nullable

Escenario: Índices de rendimiento están creados
  Given la migración ejecutada
  When reviso los índices de la tabla users
  Then debe existir índice en email
  And debe existir índice en company_id
  When reviso los índices de la tabla refresh_tokens
  Then debe existir índice en user_id
  And debe existir índice en expires_at
  And debe existir índice en token_hash

Escenario: Migración crea seed de usuario admin inicial
  Given la migración ejecutada
  When consulto users WHERE email = 'admin@elsegoviano.pe'
  Then debe existir un usuario con role = 'admin'
  And company_id = 1
  And is_active = TRUE
  And hashed_password no debe ser nulo
  And la contraseña por defecto debe estar documentada para cambio inmediato

Escenario: Migración down elimina las tablas correctamente
  Given la migración 0002 aplicada
  When ejecuto alembic downgrade -1
  Then las tablas users y refresh_tokens deben ser eliminadas
  And las tablas existentes (companies, accounts, etc.) deben permanecer intactas
```

#### Notas Técnicas

- **Archivos nuevos:**
  - `apps/backend/app/models/__init__.py`
  - `apps/backend/app/models/user.py` (User, RefreshToken ORM models)
  - `apps/backend/app/adapters/alembic/versions/0002_users_auth.py`
- **Archivos existentes modificados:** Ninguno
- **Rol ENUM en PostgreSQL:** `CREATE TYPE user_role AS ENUM ('admin', 'manager', 'operator', 'viewer')`
- **NOTA para tests:** SQLite no soporta ENUM nativo. El modelo ORM debe usar `VARCHAR` con check constraint para ser portable. El ENUM se usa solo en la migración de PostgreSQL.
- **Seed admin:** Contraseña temporal generada con `secrets.token_urlsafe(16)`, impresa en logs de migración

---

### US-03: Motor de JWT y Dependencias de Autenticación

**Como** desarrollador del backend,
**quiero** tener las funciones de creación/validación de JWT y las dependencias FastAPI de autenticación,
**para** que cualquier endpoint futuro pueda protegerse con un simple `Depends(get_current_active_user)`.

#### Criterios de Aceptación

```gherkin
Escenario: Creación de access token JWT con payload completo
  Given un usuario con id=42, company_id=1, role="admin", email="admin@test.com"
  When se llama a create_access_token(user)
  Then el token debe ser un JWT válido firmado con HS256
  And el payload debe contener "sub": "42" (como string)
  And el payload debe contener "company_id": 1
  And el payload debe contener "role": "admin"
  And el payload debe contener "email": "admin@test.com"
  And el payload debe contener "exp" (expiration) = ahora + 15 minutos
  And el payload debe contener "iat" (issued at)
  And el payload debe contener "jti" (JWT ID único)

Escenario: Creación de refresh token opaco
  Given un usuario con id=42 y company_id=1
  When se llama a create_refresh_token(user, db, ip, user_agent)
  Then debe retornar un string UUID v4
  And debe guardar SHA-256 del token en refresh_tokens.token_hash
  And el registro debe tener user_id=42 y company_id=1
  And expires_at debe ser ahora + 7 días
  And revoked_at debe ser NULL
  And created_by_ip y user_agent deben coincidir con los parámetros

Escenario: Validación de access token exitosa
  Given un access token válido y no expirado
  When se llama a decode_access_token(token)
  Then debe retornar el payload decodificado con sub, company_id, role
  And no debe lanzar excepción

Escenario: Validación de access token expirado
  Given un access token con exp en el pasado
  When se llama a decode_access_token(token)
  Then debe lanzar excepción de token expirado

Escenario: Validación de access token con firma inválida
  Given un JWT firmado con una SECRET_KEY diferente
  When se llama a decode_access_token(token)
  Then debe lanzar excepción de firma inválida

Escenario: Dependencia get_current_user extrae usuario del token
  Given un request con header Authorization: Bearer <access_token_válido>
  When el endpoint usa Depends(get_current_user)
  Then debe retornar el objeto User ORM correspondiente al sub del token
  And el usuario debe estar attached a la sesión de BD

Escenario: Dependencia get_current_user rechaza token ausente
  Given un request SIN header Authorization
  When el endpoint usa Depends(get_current_user)
  Then debe retornar HTTP 401 Unauthorized
  And el mensaje debe ser "Not authenticated"

Escenario: Dependencia get_current_user rechaza token malformado
  Given un request con header Authorization: Bearer not_a_valid_jwt
  When el endpoint usa Depends(get_current_user)
  Then debe retornar HTTP 401 Unauthorized
  And el mensaje debe indicar credenciales inválidas

Escenario: Dependencia get_current_active_user rechaza usuario inactivo
  Given un usuario con is_active=False
  And un access token válido para ese usuario
  When el endpoint usa Depends(get_current_active_user)
  Then debe retornar HTTP 403 Forbidden
  And el mensaje debe ser "Inactive user"

Escenario: Dependencia require_role restringe por rol
  Given un usuario con role="viewer"
  And un access token válido
  When el endpoint usa Depends(require_role("admin"))
  Then debe retornar HTTP 403 Forbidden
  And el mensaje debe indicar que el rol no tiene permisos suficientes

Escenario: require_role permite acceso con rol suficiente
  Given un usuario con role="admin"
  When el endpoint usa Depends(require_role("admin"))
  Then el acceso debe ser permitido
  And el endpoint debe ejecutarse normalmente
```

#### Notas Técnicas

- **Archivos nuevos:**
  - `apps/backend/app/core/security.py` (create_access_token, create_refresh_token, decode_access_token, hash_password, verify_password, verify_and_update_password)
  - `apps/backend/app/core/dependencies.py` (get_current_user, get_current_active_user, require_role)
- **Excepciones a usar:** `HTTPException(status_code=401)` y `HTTPException(status_code=403)` de FastAPI
- **OAuth2PasswordBearer:** Usar `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` como transporte del token desde el header Authorization
- **Función `create_refresh_token`**: Debe tener `company_id` como parámetro (schema preparado para multi-empresa en V2)

---

## Fase 2 — Auth Endpoints

---

### US-04: Login (POST /api/auth/login)

**Como** usuario del sistema,
**quiero** poder autenticarme con mi email y contraseña,
**para** obtener un access token y refresh token que me permitan usar la aplicación.

#### Criterios de Aceptación

```gherkin
Escenario: Login exitoso con credenciales válidas
  Given un usuario activo con email "admin@elsegoviano.pe" y contraseña correcta
  And la cuenta no está bloqueada
  When hago POST /api/auth/login con {"email": "admin@elsegoviano.pe", "password": "CorrectPass1"}
  Then la respuesta debe ser HTTP 200
  And el body debe contener "access_token" (string JWT)
  And "refresh_token" (string UUID)
  And "token_type": "bearer"
  And "expires_in": 900 (15 minutos en segundos)
  And "user" con id, email, full_name, role, company_id
  And failed_login_attempts del usuario debe resetearse a 0
  And last_login_at del usuario debe actualizarse a la fecha/hora actual
  And debe crearse un registro en refresh_tokens con token_hash, user_id, company_id

Escenario: Login fallido por contraseña incorrecta
  Given un usuario activo con email "admin@elsegoviano.pe"
  When hago POST /api/auth/login con {"email": "admin@elsegoviano.pe", "password": "WrongPass"}
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe ser "Invalid email or password" (genérico, no revela cuál falló)
  And failed_login_attempts debe incrementarse en 1

Escenario: Login fallido por email inexistente
  Given no existe usuario con email "noexiste@test.com"
  When hago POST /api/auth/login con {"email": "noexiste@test.com", "password": "AnyPass"}
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe ser "Invalid email or password" (mismo mensaje genérico)
  And el tiempo de respuesta debe ser similar al de contraseña incorrecta (sin timing leak)

Escenario: Login fallido — cuenta bloqueada
  Given un usuario con locked_until = ahora + 10 minutos
  When hago POST /api/auth/login con credenciales correctas
  Then la respuesta debe ser HTTP 423 Locked
  And el mensaje debe indicar que la cuenta está bloqueada temporalmente
  And NO debe validar la contraseña (evitar timing leak adicional)

Escenario: Login fallido — cuenta inactiva
  Given un usuario con is_active = False
  When hago POST /api/auth/login con credenciales correctas
  Then la respuesta debe ser HTTP 403 Forbidden
  And el mensaje debe indicar que la cuenta está desactivada

Escenario: Login fallido — validación de campos requeridos
  Given el endpoint POST /api/auth/login
  When envío un request sin campo "email"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And debe indicar que "email" es requerido
  When envío un request sin campo "password"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And debe indicar que "password" es requerido

Escenario: Login fallido — email con formato inválido
  Given el endpoint POST /api/auth/login
  When envío {"email": "not-an-email", "password": "SomePass1"}
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And debe indicar que el email no tiene formato válido

Escenario: Login registra IP y User-Agent en refresh token
  Given credenciales válidas
  When hago POST /api/auth/login desde IP 192.168.1.100 con User-Agent "Mozilla/5.0..."
  Then el refresh token creado debe tener created_by_ip = "192.168.1.100"
  And user_agent debe contener "Mozilla/5.0..."

Escenario: Bloqueo de cuenta tras 10 fallos consecutivos
  Given un usuario con 9 failed_login_attempts
  When falla el login por décima vez consecutiva
  Then locked_until debe ser ahora + 15 minutos
  And failed_login_attempts debe ser 10
  And la respuesta debe ser HTTP 423 Locked

Escenario: Rate limiting de login — más de 5 intentos por minuto por IP
  Given el rate limiting de login está activo
  When hago 5 intentos de login fallidos desde la misma IP en menos de 1 minuto
  And intento un sexto login
  Then la respuesta debe ser HTTP 429 Too Many Requests

Escenario: Login exitoso descongela cuenta tras lock expirado
  Given un usuario con locked_until = hace 1 minuto (ya expirado)
  When hago login con credenciales correctas
  Then el login debe ser exitoso (HTTP 200)
  And failed_login_attempts debe resetearse a 0
  And locked_until debe ser NULL
```

#### Notas Técnicas

- **Endpoint:** `POST /api/auth/login`
- **Request body:** `LoginRequest { email: EmailStr, password: str }`
- **Response body:** `TokenResponse { access_token, refresh_token, token_type, expires_in, user: UserResponse }`
- **Dependencias:** Ninguna (público)
- **Funciones usadas:** `verify_password()`, `create_access_token()`, `create_refresh_token()`
- **Archivos:** `routers/auth.py`, `schemas/auth.py`
- **Mensaje genérico:** No diferenciar entre "email no encontrado" y "contraseña incorrecta" para evitar enumeración de usuarios
- **Timing:** La validación de contraseña debe ejecutarse incluso si el email no existe (usar hash falso o dummy verify) para evitar timing attack que revele existencia de cuenta

---

### US-05: Refresh Token (POST /api/auth/refresh)

**Como** usuario con sesión activa,
**quiero** poder renovar mi access token expirado usando mi refresh token,
**para** no tener que volver a hacer login cada 15 minutos.

#### Criterios de Aceptación

```gherkin
Escenario: Refresh exitoso — rotación de tokens
  Given un refresh token válido, no expirado y no revocado en la BD
  When hago POST /api/auth/refresh con {"refresh_token": "<token_válido>"}
  Then la respuesta debe ser HTTP 200
  And debe contener un NUEVO access_token
  And debe contener un NUEVO refresh_token
  And el refresh_token viejo debe marcarse como revoked_at = now()
  And el refresh_token viejo debe tener replaced_by_id apuntando al nuevo token

Escenario: Refresh fallido — token revocado (detección de reuso)
  Given un refresh_token que YA fue revocado (revoked_at NO es NULL)
  When hago POST /api/auth/refresh con ese token
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe indicar "Token revoked"
  And TODOS los refresh tokens del usuario deben ser revocados (family revocation)
  And el usuario debe ser forzado a hacer login de nuevo

Escenario: Refresh fallido — token expirado
  Given un refresh token con expires_at en el pasado
  When hago POST /api/auth/refresh con ese token
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe indicar "Token expired"

Escenario: Refresh fallido — token no existe en BD
  Given un UUID aleatorio que no está en refresh_tokens
  When hago POST /api/auth/refresh con {"refresh_token": "<uuid_inválido>"}
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe ser genérico "Invalid token"

Escenario: Refresh fallido — campo requerido ausente
  Given el endpoint POST /api/auth/refresh
  When envío un request sin "refresh_token"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity

Escenario: Refresh exitoso — el nuevo access token hereda datos del usuario
  Given refresh exitoso para usuario con company_id=1, role="manager"
  When decodifico el nuevo access_token
  Then el payload debe contener el mismo sub, company_id, role que el usuario original
  And exp debe ser ahora + 15 minutos
```

#### Notas Técnicas

- **Endpoint:** `POST /api/auth/refresh`
- **Request body:** `RefreshRequest { refresh_token: str }`
- **Response body:** `TokenResponse` (igual que login, sin "user")
- **Dependencias:** Ninguna (público)
- **Rotación con family revocation:** Si se detecta reuso de un token ya revocado, se revocan TODOS los tokens del usuario. Esto es el estándar de Auth0 para refresh token rotation.
- **Token hash:** El refresh token recibido se hashea con SHA-256 y se busca en `refresh_tokens.token_hash`

---

### US-06: Logout (POST /api/auth/logout)

**Como** usuario autenticado,
**quiero** poder cerrar mi sesión de forma segura,
**para** que mi refresh token sea invalidado y nadie pueda usarlo después.

#### Criterios de Aceptación

```gherkin
Escenario: Logout exitoso revoca refresh token
  Given un refresh token válido y activo en la BD
  When hago POST /api/auth/logout con {"refresh_token": "<token_válido>"}
  Then la respuesta debe ser HTTP 200
  And el mensaje debe confirmar "Successfully logged out"
  And el refresh_token en BD debe tener revoked_at = now()
  And el access token NO se invalida en el servidor (sigue siendo válido hasta que expire)

Escenario: Logout con token ya revocado — idempotente
  Given un refresh token que ya tiene revoked_at seteado
  When hago POST /api/auth/logout con ese token
  Then la respuesta debe ser HTTP 200 (idempotente, no error)
  And el mensaje debe confirmar "Successfully logged out"

Escenario: Logout con token inexistente — no revela información
  Given un UUID que no existe en refresh_tokens
  When hago POST /api/auth/logout con ese token
  Then la respuesta debe ser HTTP 200
  And el mensaje debe ser "Successfully logged out"
  And no debe revelar que el token no existía
```

#### Notas Técnicas

- **Endpoint:** `POST /api/auth/logout`
- **Request body:** `LogoutRequest { refresh_token: str }`
- **Dependencias:** Ninguna (no requiere autenticación — el refresh token ES la prueba de sesión)
- **Idempotente:** No debe fallar si el token ya estaba revocado

---

### US-07: Perfil de Usuario Actual (GET /api/auth/me)

**Como** usuario autenticado,
**quiero** consultar mis datos de perfil,
**para** que el frontend pueda mostrar mi nombre, rol y empresa actual.

#### Criterios de Aceptación

```gherkin
Escenario: Obtener perfil con token válido
  Given un access token válido para el usuario id=42
  When hago GET /api/auth/me con header Authorization: Bearer <token>
  Then la respuesta debe ser HTTP 200
  And debe contener "id": 42
  And "email": "admin@elsegoviano.pe"
  And "full_name": "Admin Principal"
  And "role": "admin"
  And "company_id": 1
  And NO debe contener "hashed_password"
  And NO debe contener "failed_login_attempts"
  And NO debe contener "locked_until"

Escenario: GET /me sin token — rechazado
  Given un request sin header Authorization
  When hago GET /api/auth/me
  Then la respuesta debe ser HTTP 401 Unauthorized

Escenario: GET /me con token expirado — rechazado
  Given un access token expirado
  When hago GET /api/auth/me con ese token
  Then la respuesta debe ser HTTP 401 Unauthorized
  And el mensaje debe indicar token expirado

Escenario: GET /me — usuario inactivo
  Given un access token válido para un usuario con is_active=False
  When hago GET /api/auth/me
  Then la respuesta debe ser HTTP 403 Forbidden
```

#### Notas Técnicas

- **Endpoint:** `GET /api/auth/me`
- **Dependencias:** `Depends(get_current_active_user)`
- **Response:** `UserResponse` (mismo schema que el campo "user" del login)
- **Schema seguro:** El Pydantic schema `UserResponse` no debe incluir campos sensibles

---

## Fase 3 — Admin Users

---

### US-08: Crear Usuario (POST /api/admin/users)

**Como** administrador del tenant,
**quiero** crear nuevos usuarios para mi empresa,
**para** que otros empleados puedan acceder al sistema con sus propias credenciales.

#### Criterios de Aceptación

```gherkin
Escenario: Admin crea usuario exitosamente
  Given un admin autenticado del tenant company_id=1
  When hago POST /api/admin/users con {
    "email": "nuevo@elsegoviano.pe",
    "full_name": "Nuevo Usuario",
    "role": "operator",
    "password": "TempPass1"
  }
  Then la respuesta debe ser HTTP 201 Created
  And el body debe contener "id", "email", "full_name", "role", "company_id"
  And company_id debe ser 1 (el tenant del admin que crea)
  And NO debe contener "hashed_password"
  And el usuario creado debe tener is_active=True
  And is_verified=False (MVP: no email verification)
  And failed_login_attempts=0

Escenario: Admin crea usuario — email duplicado
  Given ya existe un usuario con email "existe@test.com"
  When un admin intenta crear otro usuario con el mismo email
  Then la respuesta debe ser HTTP 409 Conflict
  And el mensaje debe indicar que el email ya está en uso

Escenario: Admin crea usuario — email con formato inválido
  Given un admin autenticado
  When intento crear usuario con email "no-es-email"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity

Escenario: Admin crea usuario — contraseña débil rechazada
  Given un admin autenticado
  When intento crear usuario con password "123" (menos de 8 caracteres)
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And el mensaje debe indicar la política de contraseñas

Escenario: Admin crea usuario — contraseña sin mayúscula
  Given un admin autenticado
  When intento crear usuario con password "todominusculas1"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And el mensaje debe indicar que requiere al menos 1 mayúscula

Escenario: Admin crea usuario — contraseña sin número
  Given un admin autenticado
  When intento crear usuario con password "SoloLetrasMayus"
  Then la respuesta debe ser HTTP 422 Unprocessable Entity
  And el mensaje debe indicar que requiere al menos 1 número

Escenario: Admin crea usuario — role inválido
  Given un admin autenticado
  When intento crear usuario con role "superadmin" (no existe en el ENUM)
  Then la respuesta debe ser HTTP 422 Unprocessable Entity

Escenario: No-admin intenta crear usuario — rechazado
  Given un usuario autenticado con role="operator"
  When intenta hacer POST /api/admin/users
  Then la respuesta debe ser HTTP 403 Forbidden

Escenario: Usuario no autenticado intenta crear usuario
  Given un request sin token de autenticación
  When hago POST /api/admin/users
  Then la respuesta debe ser HTTP 401 Unauthorized

Escenario: Admin NO puede crear usuario en otro tenant
  Given admin de company_id=1 autenticado con header X-Tenant-ID: 1
  When intenta crear usuario especificando company_id=2 en el body
  Then la respuesta debe ser HTTP 403 Forbidden o 422 Unprocessable Entity
  And el company_id del usuario creado SIEMPRE debe ser el del admin autenticado
```

#### Notas Técnicas

- **Endpoint:** `POST /api/admin/users`
- **Dependencias:** `Depends(get_current_active_user)`, `Depends(require_role("admin"))`, `Depends(get_tenant_id)`
- **Request body:** `CreateUserRequest { email: EmailStr, full_name: str, role: UserRole, password: str }`
- **Response:** `UserResponse` (status 201)
- **Password policy enforcement:** Validación en el Pydantic schema con `@field_validator` o `@model_validator`
- **company_id implícito:** El endpoint toma el `company_id` del admin autenticado (`current_user.company_id`), NO del body
- **Password validation regex:** mínimo 8 caracteres, al menos 1 mayúscula (`[A-Z]`), al menos 1 número (`[0-9]`)

---

### US-09: Listar Usuarios (GET /api/admin/users)

**Como** administrador del tenant,
**quiero** ver la lista de todos los usuarios de mi empresa,
**para** gestionar quién tiene acceso al sistema.

#### Criterios de Aceptación

```gherkin
Escenario: Admin lista usuarios de su tenant
  Given un admin de company_id=1 autenticado
  And existen 3 usuarios en company_id=1
  And existen 2 usuarios en company_id=2 (otro tenant)
  When hago GET /api/admin/users con header X-Tenant-ID: 1
  Then la respuesta debe ser HTTP 200
  And debe retornar exactamente 3 usuarios
  And ningún usuario retornado debe tener company_id != 1
  And cada usuario debe incluir id, email, full_name, role, is_active, is_verified, created_at
  And NO debe incluir hashed_password ni failed_login_attempts

Escenario: Admin lista usuarios — tenant vacío
  Given un admin de company_id=99 autenticado
  And no existen usuarios en company_id=99 excepto el admin
  When hago GET /api/admin/users con X-Tenant-ID: 99
  Then la respuesta debe ser HTTP 200
  And debe retornar solo al admin (lista con 1 elemento)

Escenario: No-admin intenta listar usuarios — rechazado
  Given un usuario con role="operator" autenticado
  When intenta hacer GET /api/admin/users
  Then la respuesta debe ser HTTP 403 Forbidden

Escenario: Listar usuarios sin X-Tenant-ID
  Given un admin autenticado
  When hago GET /api/admin/users sin header X-Tenant-ID
  Then la respuesta debe ser HTTP 400 Bad Request
  And el mensaje debe ser "X-Tenant-ID header required"

Escenario: Admin ve metadata de seguridad de cada usuario
  Given un admin autenticado
  When hago GET /api/admin/users
  Then cada usuario en la lista debe mostrar is_active (boolean)
  And debe mostrar is_verified (boolean)
  And debe mostrar created_at
  And NO debe exponer failed_login_attempts ni locked_until

Escenario: Listar usuarios con filtro por rol (opcional V1)
  Given un admin autenticado y el query param ?role=viewer
  When hago GET /api/admin/users?role=viewer
  Then solo deben retornarse usuarios con role="viewer" del tenant
```

#### Notas Técnicas

- **Endpoint:** `GET /api/admin/users`
- **Dependencias:** `Depends(get_current_active_user)`, `Depends(require_role("admin"))`, `Depends(get_tenant_id)`
- **Query params opcionales:** `role: Optional[UserRole] = None`, `is_active: Optional[bool] = None`, `search: Optional[str] = None`
- **Scoping:** Filtrar por `company_id` del admin, NO aceptar company_id del request
- **Paginación futura:** Dejar preparado con `limit` y `offset` aunque en MVP retorne todos

---

## Fase 4 — Tenant Scoping

---

### US-10: Middleware X-Tenant-ID

**Como** arquitecto del sistema,
**quiero** que cada request incluya obligatoriamente el header X-Tenant-ID y que se valide contra el usuario autenticado,
**para** garantizar que los datos de un tenant nunca se filtren a otro.

#### Criterios de Aceptación

```gherkin
Escenario: X-Tenant-ID válido se almacena en request.state
  Given un request con header X-Tenant-ID: 1
  When el middleware de tenant procesa el request
  Then request.state.tenant_id debe ser 1 (int)

Escenario: X-Tenant-ID ausente en endpoint protegido
  Given un endpoint que usa Depends(get_tenant_id)
  When hago un request SIN el header X-Tenant-ID
  Then la respuesta debe ser HTTP 400 Bad Request
  And el mensaje debe ser "X-Tenant-ID header required"

Escenario: X-Tenant-ID no numérico
  Given un request con header X-Tenant-ID: "abc"
  When el middleware procesa el request
  Then la respuesta debe ser HTTP 400 Bad Request
  And el mensaje debe indicar que X-Tenant-ID debe ser un entero

Escenario: Validación cruzada — user.company_id coincide con tenant_id
  Given un usuario con company_id=1 autenticado
  And el request tiene header X-Tenant-ID: 1
  When get_current_active_user procesa la dependencia
  Then la validación user.company_id == tenant_id debe pasar
  And el request debe continuar normalmente

Escenario: Validación cruzada — user.company_id NO coincide con tenant_id
  Given un usuario con company_id=1 autenticado
  And el request tiene header X-Tenant-ID: 2
  When get_current_active_user procesa la dependencia
  Then la respuesta debe ser HTTP 403 Forbidden
  And el mensaje debe ser "Access denied to this tenant"

Escenario: Endpoints públicos no requieren X-Tenant-ID
  Given los endpoints /api/auth/login, /api/auth/refresh, /api/auth/logout, /docs, /redoc, /
  When hago un request sin X-Tenant-ID a cualquiera de ellos
  Then NO deben fallar por falta de X-Tenant-ID
  And deben funcionar normalmente
```

#### Notas Técnicas

- **Archivo nuevo:** `apps/backend/app/core/tenant.py`
- **Función:** `get_tenant_id(request: Request) -> int`
- **Dependencia FastAPI:** Se inyecta con `Depends(get_tenant_id)` en cada endpoint protegido
- **No es middleware global:** Es una dependencia explícita, no un `@app.middleware("http")`, para permitir endpoints públicos sin el header
- **Validación cruzada:** Se hace dentro de `get_current_active_user` (en `dependencies.py`), validando `user.company_id == request.state.tenant_id`

---

### US-11: Scoping Automático en Repositorios

**Como** desarrollador del backend,
**quiero** que todos los repositorios reciban `company_id` en su constructor y filtren automáticamente,
**para** eliminar el riesgo de que una query olvide el filtro de tenant.

#### Criterios de Aceptación

```gherkin
Escenario: Repositorio contable con scoping
  Given SQLAlchemyAccountingRepository(db, company_id=1)
  When llamo a get_journal_entries() sin pasar company_id
  Then la query SQL debe incluir WHERE company_id = 1
  And solo debe retornar asientos del tenant 1

Escenario: Repositorio de inventario con scoping
  Given SQLAlchemyInventoryRepository(db, company_id=2)
  When llamo a get_products()
  Then la query SQL debe incluir WHERE company_id = 2
  And solo debe retornar productos del tenant 2

Escenario: Repositorio sin company_id lanza error en init
  Given que intento instanciar SQLAlchemyAccountingRepository(db) sin company_id
  Then debe lanzar TypeError indicando que company_id es requerido

Escenario: UserRepository implementa scoping
  Given UserRepository(db, company_id=1)
  When llamo a get_all_users()
  Then la query SQL debe incluir WHERE company_id = 1

Escenario: Dos repositorios con distinto company_id no comparten datos
  Given repo_tenant1 = SQLAlchemyAccountingRepository(db, company_id=1)
  And repo_tenant2 = SQLAlchemyAccountingRepository(db, company_id=2)
  And existen datos en ambos tenants
  When consulto get_journal_entries() en repo_tenant1
  Then los resultados solo deben ser del tenant 1
  When consulto get_journal_entries() en repo_tenant2
  Then los resultados solo deben ser del tenant 2
```

#### Notas Técnicas

- **Archivos modificados:**
  - `apps/backend/app/adapters/db/repositories/accounting.py` — agregar `company_id` al constructor de `SQLAlchemyAccountingRepository` y `SQLAlchemyInventoryRepository`
  - `apps/backend/app/adapters/db/repositories/user.py` — NUEVO archivo con `UserRepository`
- **Cambio mínimo:** Solo agregar `company_id` como parámetro requerido del `__init__` y usarlo en cada query `WHERE`
- **Constructor actual:** `def __init__(self, session: AsyncSession)` → `def __init__(self, session: AsyncSession, company_id: int)`
- **Queries existentes que ya filtran por company_id:** `get_journal_entries` y `clear_journal` — actualizar para usar `self.company_id` en vez del parámetro

---

### US-12: Proteger Endpoints Existentes con Auth + Tenant

**Como** administrador del sistema,
**quiero** que todos los endpoints contables y de configuración requieran autenticación y validación de tenant,
**para** que ningún dato sea accesible sin credenciales ni se cruce entre tenants.

#### Criterios de Aceptación

```gherkin
Escenario: Endpoint contable requiere auth y tenant
  Given un usuario autenticado con token válido y X-Tenant-ID correcto
  When hago GET /api/accounting/bcss
  Then la respuesta debe ser HTTP 200
  And los datos deben ser del tenant del usuario

Escenario: Endpoint contable sin token — rechazado
  Given un request sin header Authorization
  When hago GET /api/accounting/pyg
  Then la respuesta debe ser HTTP 401 Unauthorized

Escenario: Endpoint de setup requiere auth y tenant
  Given un usuario autenticado
  When hago POST /api/accounting/setup
  Then la respuesta debe procesarse normalmente (o error de negocio, no de auth)

Escenario: Endpoint de kárdex requiere auth y tenant
  Given un usuario autenticado con X-Tenant-ID válido
  When hago GET /api/accounting/kardex/P001
  Then la respuesta debe ser HTTP 200 (o 404 si no existe el producto)
  And no debe ser error de autenticación

Escenario: Health check sigue siendo público
  Given un request sin autenticación
  When hago GET /api/health
  Then la respuesta debe ser HTTP 200
  And debe retornar el estado del servicio

Escenario: Documentación OpenAPI sigue accesible
  Given un request sin autenticación
  When visito /docs o /redoc
  Then deben cargar correctamente
  And deben mostrar el esquema de seguridad con lock icon (Authorize button)

Escenario: Scoping consistente en todos los endpoints contables
  Given usuario company_id=1 autenticado con X-Tenant-ID: 1
  And usuario company_id=2 autenticado con X-Tenant-ID: 2
  When ambos consultan GET /api/accounting/bcss
  Then el usuario 1 solo ve datos de company_id=1
  And el usuario 2 solo ve datos de company_id=2
  And los resultados deben ser diferentes

Escenario: Todos los endpoints protegidos tienen el mismo patrón de dependencias
  Given cualquier endpoint contable en routers/accounting.py
  When reviso la firma de la función
  Then debe incluir tenant_id: int = Depends(get_tenant_id)
  And debe incluir current_user: User = Depends(get_current_active_user)
  And el repositorio debe instanciarse con company_id=tenant_id
```

#### Notas Técnicas

- **Archivos modificados:**
  - `apps/backend/app/routers/accounting.py` — agregar `Depends(get_tenant_id)` y `Depends(get_current_active_user)` a los 10 endpoints (bcss, pyg, balance, ratios, transaction, kardex/*)
  - `apps/backend/app/routers/setup.py` — agregar dependencias de auth
  - `apps/backend/app/main.py` — conectar `auth_router`
- **Endpoints públicos que NO cambian:** `/api/health`, `/`, `/docs`, `/redoc`
- **Patrón de dependencias:**
  ```python
  tenant_id: int = Depends(get_tenant_id),
  current_user: User = Depends(get_current_active_user),
  db: AsyncSession = Depends(get_db),
  ```
- **Instanciación de repositorio:** `repo = SQLAlchemyAccountingRepository(db, company_id=tenant_id)`

---

## Fase 5 — Rate Limiting Redis

---

### US-13: Rate Limiting de Login por IP

**Como** administrador de seguridad,
**quiero** limitar los intentos de login a 5 por minuto por dirección IP,
**para** prevenir ataques de fuerza bruta desde una misma máquina.

#### Criterios de Aceptación

```gherkin
Escenario: Hasta 5 intentos de login desde misma IP son permitidos
  Given el rate limiting está activo (Redis disponible)
  When hago 5 POST /api/auth/login desde IP 10.0.0.1 en 60 segundos
  Then todos deben ser aceptados (HTTP 200 o 401 según credenciales)
  And ninguno debe ser HTTP 429

Escenario: El sexto intento desde misma IP es bloqueado
  Given 5 intentos de login desde IP 10.0.0.1 en el último minuto
  When hago un sexto POST /api/auth/login desde la misma IP
  Then la respuesta debe ser HTTP 429 Too Many Requests
  And el body debe contener "detail" explicando el rate limit
  And debe incluir header "Retry-After" con los segundos restantes

Escenario: El rate limiting por IP se resetea tras la ventana
  Given 5 intentos de login desde IP 10.0.0.1 hace más de 1 minuto
  When hago un nuevo POST /api/auth/login desde la misma IP
  Then la respuesta NO debe ser 429
  And el contador debe empezar de nuevo

Escenario: Dos IPs diferentes tienen límites independientes
  Given 5 intentos de login desde IP 10.0.0.1 en el último minuto
  When hago POST /api/auth/login desde IP 10.0.0.2
  Then la respuesta NO debe ser 429
  And la IP 10.0.0.2 tiene su propio contador

Escenario: Login exitoso cuenta igual para rate limiting
  Given 4 intentos fallidos y 1 exitoso desde la misma IP en 1 minuto
  When intento un sexto login desde esa IP
  Then debe ser HTTP 429 (todos los intentos cuentan, exitosos o no)

Escenario: Rate limiting funciona con Redis SORTED SET
  Given el cliente Redis está conectado
  When se registra un intento de login
  Then debe usar ZADD en una key tipo "login_rate:{ip}"
  And debe usar ZREMRANGEBYSCORE para limpiar timestamps viejos
  And ZCARD para contar los intentos en la ventana

Escenario: Fallback a in-memory si Redis no está disponible
  Given Redis no responde (connection error)
  When hago un intento de login
  Then el rate limiting debe usar diccionario en memoria como fallback
  And debe loguearse un WARNING "Redis unavailable, using in-memory rate limiting"
  And el login debe seguir funcionando (no bloquear por falta de Redis)
```

#### Notas Técnicas

- **Archivos modificados:** `apps/backend/app/monitoring/middleware.py` — reemplazar implementación in-memory actual
- **Redis key pattern:** `ratelimit:login:ip:{ip_address}`
- **Algoritmo:** Sliding window log con Redis SORTED SET
  - `ZADD key timestamp unique_id`
  - `ZREMRANGEBYSCORE key 0 {now - window_seconds}`
  - `ZCARD key` → si >= max_requests → 429
- **Configuración:** `LOGIN_RATE_LIMIT_PER_IP = "5/minute"` en config.py
- **Redis client:** Ya existe `redis_url` en config.py; verificar que redis está en docker-compose.yml

---

### US-14: Rate Limiting de Login por Email

**Como** administrador de seguridad,
**quiero** limitar los intentos de login a 5 por minuto por email,
**para** prevenir ataques de fuerza bruta distribuidos (múltiples IPs contra una misma cuenta).

#### Criterios de Aceptación

```gherkin
Escenario: Rate limiting por email — 5 intentos máximo
  Given un usuario con email "victima@test.com"
  When se intenta login con ese email 5 veces desde diferentes IPs en 1 minuto
  Then todos deben ser aceptados (no 429)
  When se intenta un sexto login con el mismo email
  Then debe ser HTTP 429 Too Many Requests

Escenario: Rate limiting por email independiente del resultado
  Given credenciales correctas para "admin@test.com"
  When hago 5 logins exitosos en 1 minuto desde diferentes IPs
  And intento un sexto login
  Then debe ser HTTP 429 (el rate limit aplica a intentos, no solo fallos)

Escenario: Rate limiting por email es independiente del rate limiting por IP
  Given 5 intentos contra "user1@test.com" desde IP-A (llena el límite por email)
  When intento login con "user2@test.com" desde IP-A
  Then el rate limit por IP de IP-A debe estar lleno (5 intentos)
  And debe ser HTTP 429
  When intento login con "user1@test.com" desde IP-B (nueva IP)
  Then debe ser HTTP 429 por rate limit de email

Escenario: El contador de email se limpia tras la ventana
  Given 5 intentos contra "user@test.com" hace más de 1 minuto
  When intento un nuevo login con "user@test.com"
  Then NO debe ser 429
```

#### Notas Técnicas

- **Redis key pattern:** `ratelimit:login:email:{sha256(email)}`
- Se hashea el email para no almacenar PII en Redis
- Misma lógica de SORTED SET que el rate limiting por IP
- Se ejecutan AMBAS validaciones en el endpoint de login: IP + email
- La primera que falle (IP o email) retorna 429

---

### US-15: Bloqueo de Cuenta por Fallos Consecutivos

**Como** administrador de seguridad,
**quiero** que las cuentas se bloqueen temporalmente tras 10 fallos consecutivos de login,
**para** mitigar ataques de diccionario contra una cuenta específica.

#### Criterios de Aceptación

```gherkin
Escenario: Cuenta se bloquea tras 10 fallos consecutivos
  Given un usuario con 9 failed_login_attempts
  When falla el login por décima vez
  Then locked_until debe establecerse a now() + 15 minutos
  And la respuesta debe ser HTTP 423 Locked
  And el mensaje debe indicar "Account temporarily locked. Try again in X minutes."

Escenario: Login rechazado durante el período de bloqueo
  Given un usuario con locked_until = now() + 10 minutos
  When intento login con credenciales CORRECTAS
  Then debe ser HTTP 423 Locked
  And NO debe validar la contraseña (evitar timing leak)
  And failed_login_attempts NO debe cambiar

Escenario: Login exitoso después del bloqueo
  Given un usuario con locked_until = now() - 1 minuto (bloqueo expirado)
  When hago login con credenciales correctas
  Then debe ser HTTP 200
  And failed_login_attempts debe ser 0
  And locked_until debe ser NULL

Escenario: Login exitoso antes de llegar a 10 fallos resetea el contador
  Given un usuario con 5 failed_login_attempts
  When hago login exitoso
  Then failed_login_attempts debe ser 0
  And locked_until debe permanecer NULL

Escenario: Bloqueo es por cuenta, no por IP
  Given cuenta A bloqueada (10 fallos)
  When intento login con cuenta B (diferente) desde la misma IP
  Then la cuenta B debe poder hacer login normalmente
  And el bloqueo de A no afecta a B

Escenario: El tiempo de bloqueo es configurable
  Given la variable LOGIN_LOCK_MINUTES = 30 en config
  When una cuenta alcanza 10 fallos
  Then locked_until debe ser now() + 30 minutos

Escenario: Detalle del tiempo restante en respuesta 423
  Given un usuario bloqueado con locked_until = now() + 8 minutos
  When intento login
  Then la respuesta 423 debe incluir "retry_after_seconds" ≈ 480
  And el mensaje debe ser legible: "Account locked. Try again in 8 minutes."
```

#### Notas Técnicas

- **Campos en DB:** `users.failed_login_attempts` (INT) y `users.locked_until` (TIMESTAMPTZ)
- **Lógica en login endpoint:**
  1. Buscar usuario por email
  2. Si `locked_until > now()` → 423
  3. Si contraseña incorrecta → incrementar `failed_login_attempts`
  4. Si `failed_login_attempts >= LOGIN_MAX_ATTEMPTS` → set `locked_until = now() + LOGIN_LOCK_MINUTES`
  5. Si contraseña correcta → reset `failed_login_attempts = 0`, `locked_until = NULL`
- **Variables de configuración:** `LOGIN_MAX_ATTEMPTS=10`, `LOGIN_LOCK_MINUTES=15`

---

## Fase 6 — Frontend

---

### US-16: AuthContext — Estado Global de Autenticación

**Como** desarrollador frontend,
**quiero** tener un AuthContext de React que gestione el estado de autenticación globalmente,
**para** que cualquier componente pueda acceder al usuario, token y funciones de login/logout.

#### Criterios de Aceptación

```gherkin
Escenario: AuthProvider envuelve la aplicación
  Given la aplicación React inicia
  When App.tsx renderiza <AuthProvider>
  Then todos los componentes hijos deben poder usar useAuth()

Escenario: Estado inicial — sin sesión
  Given que no hay token en sessionStorage
  When la aplicación carga
  Then useAuth() debe retornar user = null
  And isAuthenticated = false
  And isLoading = false (no está cargando)

Escenario: Login exitoso actualiza el estado global
  Given el AuthContext montado
  When se llama a login("admin@test.com", "CorrectPass1")
  Then debe hacer POST /api/auth/login
  And al recibir 200, debe guardar access_token en memoria (variable JS)
  And guardar refresh_token en sessionStorage (o variable JS)
  And setear user con los datos de la respuesta
  And isAuthenticated debe ser true

Escenario: Login fallido NO actualiza el estado
  Given el AuthContext montado
  When se llama a login("admin@test.com", "WrongPass")
  Then debe hacer POST y recibir 401
  And user debe seguir siendo null
  And isAuthenticated debe ser false
  And debe lanzar error con el mensaje del servidor

Escenario: Logout limpia el estado global
  Given un usuario autenticado (isAuthenticated = true)
  When se llama a logout()
  Then debe hacer POST /api/auth/logout con el refresh_token
  And access_token debe eliminarse de memoria
  And refresh_token debe eliminarse de sessionStorage
  And user debe ser null
  And isAuthenticated debe ser false

Escenario: refreshToken se llama automáticamente al recibir 401
  Given un usuario autenticado con refresh_token válido
  And el access_token está expirado
  When el interceptor de API detecta un 401
  Then debe llamar a POST /api/auth/refresh con el refresh_token
  And al recibir nuevo access_token + refresh_token
  Then debe actualizar ambos en el estado
  And reintentar el request original
  And el usuario NO debe notar la interrupción

Escenario: Refresh fallido fuerza logout
  Given el refresh_token está expirado o revocado
  When el interceptor intenta refrescar y recibe 401
  Then debe ejecutar logout() automáticamente
  And redirigir al usuario a /login

Escenario: Múltiples 401 concurrentes hacen solo un refresh
  Given el access_token expirado
  When 3 requests simultáneos reciben 401
  Then solo debe ejecutarse UNA llamada a /api/auth/refresh
  And los 3 requests deben esperar y usar el nuevo token
  And no debe haber race condition

Escenario: AuthContext expone datos del tenant
  Given un usuario autenticado con company_id=1
  When un componente lee useAuth().tenant
  Then debe retornar { id: 1 } (o el company_id del JWT)
  And este valor debe usarse para el header X-Tenant-ID

Escenario: Persistencia de sesión al recargar la página
  Given un refresh_token en sessionStorage de una sesión previa
  When la aplicación se carga
  Then AuthContext debe intentar POST /api/auth/refresh automáticamente
  And si es exitoso, restaurar la sesión sin pedir login
  And si falla, limpiar storage y mostrar /login
```

#### Notas Técnicas

- **Archivo nuevo:** `apps/web/src/contexts/AuthContext.tsx`
- **Tecnologías:** React Context API + useReducer (o useState para MVP)
- **Interface del contexto:**
  ```typescript
  interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    tenant: Tenant | null;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<string | null>;
  }
  ```
- **Almacenamiento de tokens:** Access token en variable JS (memoria). Refresh token en sessionStorage (sobrevive refrescos de página pero no cierre de pestaña).
- **Interceptor de 401:** Implementar en `services/api.ts` como wrapper de fetch/axios que detecta 401, llama a refreshToken(), y reintenta.

---

### US-17: Página de Login

**Como** usuario del sistema,
**quiero** una página de login limpia y funcional con validación,
**para** poder autenticarme y acceder al sistema.

#### Criterios de Aceptación

```gherkin
Escenario: Login page renderiza formulario
  Given que no hay sesión activa
  When navego a /login
  Then debe mostrarse un formulario con campos Email y Password
  And un botón "Iniciar Sesión"
  And el logo o nombre de la aplicación "IaaS-RonSys" o "El Segoviano"

Escenario: Login exitoso redirige al dashboard
  Given credenciales válidas ingresadas
  When hago clic en "Iniciar Sesión"
  Then el botón debe mostrar estado de carga (spinner, deshabilitado)
  And al recibir respuesta 200, debe redirigir a / (dashboard)
  And el usuario debe ver la interfaz principal

Escenario: Login fallido muestra mensaje de error
  Given credenciales inválidas ingresadas
  When hago clic en "Iniciar Sesión"
  Then debe mostrarse un mensaje de error debajo del formulario
  And el mensaje debe ser el que devuelve el servidor
  And el formulario NO debe limpiarse
  And el botón debe volver a habilitarse

Escenario: Validación de email en el frontend
  Given el campo de email
  When escribo "no-es-email" y hago blur del campo
  Then debe mostrarse error de validación "Ingrese un email válido"
  And el botón de submit debe deshabilitarse

Escenario: Validación de campo requerido
  Given el formulario con campos vacíos
  When hago clic en "Iniciar Sesión"
  Then debe mostrarse "El email es requerido" y "La contraseña es requerida"
  And NO debe enviarse el request al servidor

Escenario: Cuenta bloqueada muestra mensaje específico
  Given una cuenta bloqueada (HTTP 423)
  When intento hacer login
  Then debe mostrarse mensaje "Cuenta bloqueada temporalmente. Intente de nuevo en X minutos."
  And el campo de password debe limpiarse

Escenario: Rate limiting muestra mensaje de espera
  Given rate limiting activo (HTTP 429)
  When intento hacer login
  Then debe mostrarse "Demasiados intentos. Espere X segundos."
  And el botón debe deshabilitarse por el tiempo indicado

Escenario: Tecla Enter envía el formulario
  Given el formulario completado con datos válidos
  When presiono Enter en el campo de password
  Then debe enviarse el formulario (mismo comportamiento que clic en botón)

Escenario: Toggle de visibilidad de contraseña
  Given el campo de password
  When hago clic en el ícono de ojo 👁
  Then el campo debe cambiar de type="password" a type="text"
  And al hacer clic de nuevo debe volver a type="password"
```

#### Notas Técnicas

- **Archivo nuevo:** `apps/web/src/components/auth/LoginPage.tsx`
- **Ruta:** `/login`
- **Estado del formulario:** `email`, `password`, `error`, `isLoading`, `showPassword`
- **Redirección post-login:** Usar `window.location` o React Router `navigate` a `/` o a la ruta que intentó acceder originalmente (guardada en state)
- **Manejo de errores:** Mapear códigos HTTP a mensajes en español:
  - 401 → "Email o contraseña inválidos"
  - 423 → "Cuenta bloqueada. Intente de nuevo en X minutos"
  - 429 → "Demasiados intentos. Espere X segundos"
- **Estilos:** TailwindCSS, consistente con el diseño existente

---

### US-18: PrivateRoute — Protección de Rutas

**Como** desarrollador frontend,
**quiero** un componente PrivateRoute que proteja las rutas que requieren autenticación,
**para** que usuarios no autenticados sean redirigidos al login automáticamente.

#### Criterios de Aceptación

```gherkin
Escenario: Usuario autenticado accede a ruta protegida
  Given un usuario con isAuthenticated = true
  When navega a /dashboard (ruta protegida por PrivateRoute)
  Then debe renderizar el componente Dashboard normalmente

Escenario: Usuario no autenticado es redirigido a /login
  Given un usuario con isAuthenticated = false
  When navega a /dashboard
  Then debe ser redirigido a /login
  And la URL original /dashboard debe guardarse para redirigir post-login

Escenario: Usuario no autenticado accede a /login
  Given isAuthenticated = false
  When navega a /login
  Then debe mostrarse la página de login normalmente
  And NO debe redirigir (evitar bucle infinito)

Escenario: Usuario YA autenticado accede a /login
  Given isAuthenticated = true
  When navega a /login
  Then debe ser redirigido a / (dashboard)
  And NO debe mostrar la página de login

Escenario: PrivateRoute con restricción de rol
  Given PrivateRoute con allowedRoles={["admin"]}
  And un usuario autenticado con role="viewer"
  When navega a esa ruta
  Then debe mostrarse una página 403 "No tienes permisos para acceder"
  And NO debe redirigir a /login

Escenario: PrivateRoute muestra loading mientras valida sesión
  Given la aplicación está cargando (verificando refresh_token en sessionStorage)
  When navego a una ruta protegida
  Then debe mostrarse un spinner o skeleton
  And al terminar la validación, redirigir a /login o mostrar la ruta

Escenario: Todas las rutas de la app están protegidas excepto /login
  Given la configuración de rutas en App.tsx
  When reviso el árbol de rutas
  Then /, /dashboard, /accounting/*, /admin/* deben estar envueltas en PrivateRoute
  And /login NO debe tener PrivateRoute
```

#### Notas Técnicas

- **Archivo nuevo:** `apps/web/src/components/auth/PrivateRoute.tsx`
- **Props:** `{ children: ReactNode, allowedRoles?: UserRole[] }`
- **Implementación:**
  ```tsx
  function PrivateRoute({ children, allowedRoles }: Props) {
    const { isAuthenticated, user, isLoading } = useAuth();
    const location = useLocation();

    if (isLoading) return <LoadingSpinner />;
    if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
    if (allowedRoles && !allowedRoles.includes(user.role)) return <ForbiddenPage />;
    return <>{children}</>;
  }
  ```
- **Archivos modificados:** `apps/web/src/App.tsx` — envolver rutas protegidas

---

### US-19: Interceptor 401 con Refresh Automático

**Como** desarrollador frontend,
**quiero** que todas las llamadas a la API incluyan automáticamente el token de autorización y el header de tenant,
**para** que ningún componente tenga que preocuparse por adjuntar credenciales manualmente.

#### Criterios de Aceptación

```gherkin
Escenario: Toda request incluye Authorization header
  Given un usuario autenticado con access_token
  When cualquier componente hace una llamada a la API
  Then el request debe incluir header "Authorization: Bearer <access_token>"
  And debe incluir header "X-Tenant-ID: <company_id>"

Escenario: Request sin sesión no incluye headers de auth
  Given isAuthenticated = false
  When se hace una llamada a endpoint público (ej. /api/health)
  Then NO debe incluir Authorization header
  And NO debe incluir X-Tenant-ID

Escenario: Interceptor detecta 401 y refresca automáticamente
  Given un access_token expirado
  When se hace una llamada a GET /api/accounting/bcss
  Then el servidor responde 401
  And el interceptor llama a POST /api/auth/refresh
  And al obtener nuevo token, reintenta GET /api/accounting/bcss
  And el componente que hizo la llamada recibe los datos normalmente

Escenario: Refresh fallido redirige a login
  Given un refresh_token expirado
  When el interceptor intenta refrescar y recibe 401
  Then debe ejecutar logout()
  And redirigir a /login

Escenario: Cola de requests durante refresh
  Given access_token expirado
  When se disparan 3 requests simultáneos (A, B, C)
  Then el primero que recibe 401 dispara el refresh
  And los otros dos esperan en cola
  And cuando el refresh termina, los 3 se reintentan con el nuevo token
  And solo se hizo UNA llamada a /api/auth/refresh

Escenario: Interceptor no intercepta requests a /api/auth/*
  Given el interceptor configurado
  When se hace POST /api/auth/login
  Then NO debe adjuntar Authorization (no hay sesión aún)
  When se hace POST /api/auth/refresh
  Then el interceptor NO debe intentar refrescar si recibe 401 (bucle infinito)

Escenario: Errores no-401 pasan sin modificar
  Given un request que recibe HTTP 422 o 500
  When el interceptor procesa la respuesta
  Then debe propagar el error normalmente
  And NO debe intentar refresh
```

#### Notas Técnicas

- **Archivo modificado:** `apps/web/src/services/api.ts` (si ya existe) o crear nuevo
- **Estrategia:** Wrapper alrededor de `fetch` o usar axios con interceptors
- **Con axios (recomendado):**
  ```typescript
  // Request interceptor
  axiosInstance.interceptors.request.use(config => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    if (tenantId) config.headers['X-Tenant-ID'] = tenantId;
    return config;
  });

  // Response interceptor
  axiosInstance.interceptors.response.use(
    response => response,
    async error => {
      if (error.response?.status === 401 && !error.config._retry) {
        error.config._retry = true;
        const newToken = await refreshToken();
        if (newToken) {
          error.config.headers.Authorization = `Bearer ${newToken}`;
          return axiosInstance(error.config);
        }
      }
      return Promise.reject(error);
    }
  );
  ```
- **Cola de refresh:** Implementar con una promesa compartida. Si ya hay un refresh en curso, los requests subsecuentes esperan esa misma promesa.
- **Exclusiones:** No interceptar rutas `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/health`

---

## 📊 Matriz de Trazabilidad

| US | Endpoint / Componente | Dependencia de US |
|----|----------------------|-------------------|
| US-01 | `core/security.py`, `config.py` | — |
| US-02 | `models/user.py`, migración 0002 | US-01 |
| US-03 | `core/dependencies.py` | US-01, US-02 |
| US-04 | `POST /api/auth/login` | US-01, US-02, US-03 |
| US-05 | `POST /api/auth/refresh` | US-01, US-02, US-03 |
| US-06 | `POST /api/auth/logout` | US-01, US-02 |
| US-07 | `GET /api/auth/me` | US-03 |
| US-08 | `POST /api/admin/users` | US-03, US-10 |
| US-09 | `GET /api/admin/users` | US-03, US-10 |
| US-10 | `core/tenant.py` | — |
| US-11 | Repositorios con scoping | US-10 |
| US-12 | Proteger endpoints existentes | US-03, US-10, US-11 |
| US-13 | Rate limiting login por IP | — (Redis) |
| US-14 | Rate limiting login por email | US-13 |
| US-15 | Bloqueo de cuenta | US-01, US-02 |
| US-16 | AuthContext | US-04, US-05, US-06 |
| US-17 | LoginPage | US-16 |
| US-18 | PrivateRoute | US-16 |
| US-19 | API Interceptor 401 | US-16, US-05 |

---

## ✅ Checklist de Validación Pre-Implementación

- [ ] ¿Cada endpoint tiene definidos todos los códigos HTTP posibles? (200, 201, 400, 401, 403, 409, 422, 423, 429)
- [ ] ¿Los mensajes de error de login son genéricos? (no diferencian email vs password)
- [ ] ¿Los schemas Pydantic de respuesta excluyen `hashed_password` y `failed_login_attempts`?
- [ ] ¿El middleware de tenant es una dependencia explícita, no un middleware global?
- [ ] ¿Los endpoints públicos (login, refresh, logout, health, docs) no requieren X-Tenant-ID?
- [ ] ¿El refresh token se rota en cada uso (revocar viejo, crear nuevo)?
- [ ] ¿La detección de reuso de refresh token revoca TODA la familia?
- [ ] ¿El bloqueo de cuenta es por fallos consecutivos, no acumulados históricos?
- [ ] ¿El rate limiting tiene fallback a in-memory si Redis no está disponible?
- [ ] ¿El frontend persiste sesión al recargar la página (refresh automático)?
- [ ] ¿El interceptor 401 maneja requests concurrentes sin race condition?
- [ ] ¿El seed de migración crea un admin inicial funcional?

---

> **Próximo paso:** Revisión de Jarvis → Asignación a Backend Agent y Frontend Agent para implementación paralela.
