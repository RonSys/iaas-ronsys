# 🛡️ Manual de Administrador — IaaS-RonSys

> **Versión:** 2.0  
> **Fecha:** 2026-05-12  
> **Sistema:** IaaS-RonSys v0.2.0 — ERP SaaS + POS + Cashflow + Kárdex Persistente  
> **Audiencia:** Administradores del sistema (rol `admin`)  
> **Franquicia:** El Segoviano 🐟

---

## 📑 Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Arquitectura de Seguridad](#2-arquitectura-de-seguridad)
3. [Gestión de Usuarios](#3-gestión-de-usuarios)
4. [Roles y Permisos](#4-roles-y-permisos)
5. [Configuración de Empresa](#5-configuración-de-empresa)
6. [Interpretación de Ratios Financieros](#6-interpretación-de-ratios-financieros)
7. [Rate Limiting y Bloqueos](#7-rate-limiting-y-bloqueos)
8. [Troubleshooting](#8-troubleshooting)
9. [Comandos de Infraestructura](#9-comandos-de-infraestructura)
10. [Referencia de Endpoints (Admin)](#10-referencia-de-endpoints-admin)

---

## 1. Introducción

Este manual es para **administradores del sistema** (rol `admin`). Cubre tareas que requieren privilegios elevados: creación de usuarios, interpretación de seguridad, troubleshooting de infraestructura y configuración avanzada.

### El Rol de Admin

Como admin, eres responsable de:

- 👥 **Gestionar usuarios**: crear cuentas, asignar roles, desactivar accesos
- 🔒 **Seguridad**: entender el modelo de autenticación y actuar ante incidentes
- 📊 **Supervisar**: interpretar los ratios financieros generados por el sistema
- 🏢 **Configurar la empresa**: definir parámetros base del tenant
- 🩺 **Diagnosticar**: resolver problemas técnicos de primer nivel

> ⚠️ El admin tiene acceso **total** al tenant. Protege tus credenciales y usa el principio de mínimo privilegio al crear otros usuarios.

---

## 2. Arquitectura de Seguridad

### 2.1 Modelo de Autenticación

IaaS-RonSys usa **JWT (JSON Web Tokens)** con refresh tokens rotativos:

```
┌──────────────────────────────────────────────────────┐
│                 FLUJO DE AUTENTICACIÓN                │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. LOGIN                                            │
│     Email + Password ──▶ Backend                     │
│                          │                           │
│                          ├─ Valida credenciales       │
│                          ├─ Verifica bloqueo          │
│                          ├─ Genera Access Token (15m) │
│                          └─ Genera Refresh Token (7d) │
│                                                      │
│  2. CADA REQUEST                                     │
│     Authorization: Bearer <access_token>             │
│     X-Tenant-ID: <company_id>                        │
│                                                      │
│  3. REFRESH (cuando access token expira)             │
│     Refresh Token ──▶ Backend                        │
│                       ├─ Valida refresh token         │
│                       ├─ Revoca token viejo           │
│                       ├─ Genera nuevo refresh token   │
│                       └─ Genera nuevo access token    │
│                                                      │
│  4. LOGOUT                                           │
│     Refresh Token ──▶ Backend                        │
│                       └─ Revoca refresh token         │
└──────────────────────────────────────────────────────┘
```

### 2.2 Características de Seguridad

| Característica | Implementación | Detalle |
|---------------|---------------|---------|
| **Hashing de contraseñas** | Argon2id | Algoritmo ganador del Password Hashing Competition. Resistente a GPU/ASIC |
| **Access Token** | JWT HS256, 15 minutos | Self-contained, no requiere consulta a BD por request |
| **Refresh Token** | UUID opaco, 7 días, rotativo | Se revoca y reemplaza en cada uso |
| **Family Revocation** | Revocación en cascada | Si se detecta reuso de un refresh token revocado, se invalidan TODOS los tokens del usuario |
| **Rate Limiting** | Redis sliding window | 5 intentos/minuto por IP, 5 intentos/minuto por email |
| **Account Lockout** | 10 fallos consecutivos → 15 min | Bloqueo temporal, no permanente |
| **Tenant Scoping** | Header X-Tenant-ID | Cada request se valida contra el company_id del usuario |
| **Anti-enumeración** | Mensajes genéricos | "Email o contraseña inválidos" — no revela si el email existe |

### 2.3 Política de Contraseñas

| Regla | Valor |
|-------|-------|
| Longitud mínima | 8 caracteres |
| Mayúsculas | Al menos 1 (`A-Z`) |
| Números | Al menos 1 (`0-9`) |
| Caracteres especiales | No requeridos (favorece frases largas) |
| Rotación forzada | No (siguiendo NIST SP 800-63B) |
| Historial | No se reutilizan (por Argon2id salt aleatorio) |

> 💡 Siguiendo lineamientos modernos (NIST, OWASP), **no** forzamos composición compleja ni rotación periódica. Una frase larga es más segura que `P@ssw0rd!`.

---

## 3. Gestión de Usuarios

### 3.1 Crear un Usuario

**Endpoint:** `POST /api/admin/users`  
**Rol requerido:** admin

Para crear un usuario, envía una solicitud con los siguientes campos:

| Campo | Tipo | Requerido | Validación |
|-------|------|:---:|------------|
| `email` | string (email) | ✅ | Formato RFC 5322, único en el tenant |
| `full_name` | string | ✅ | Mínimo 1 caracter |
| `role` | string (enum) | ✅ | `admin`, `manager`, `operator`, `viewer` |
| `password` | string | ✅ | Mín 8 caracteres, 1 mayúscula, 1 número |

**Ejemplo de solicitud (cURL):**

```bash
curl -X POST http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer <tu_access_token>" \
  -H "X-Tenant-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo.gerente@elsegoviano.pe",
    "full_name": "Carlos Mendoza",
    "role": "manager",
    "password": "Bienvenido1"
  }'
```

**Respuesta (201 Created):**

```json
{
  "id": 5,
  "email": "nuevo.gerente@elsegoviano.pe",
  "full_name": "Carlos Mendoza",
  "role": "manager",
  "company_id": 1,
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-05-10T15:30:00Z"
}
```

> ⚠️ El `company_id` del nuevo usuario **siempre es el mismo** que el del admin que lo crea. No se puede crear usuarios en otro tenant.

### 3.2 Listar Usuarios

**Endpoint:** `GET /api/admin/users`  
**Rol requerido:** admin

Parámetros opcionales (query string):

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `role` | string | Filtrar por rol (`admin`, `manager`, `operator`, `viewer`) |
| `is_active` | boolean | Filtrar por estado de cuenta |
| `search` | string | Buscar en email y nombre |
| `limit` | integer | Máximo de resultados (default 100) |
| `offset` | integer | Paginación (default 0) |

**Ejemplo:**

```bash
curl "http://localhost:8000/api/admin/users?role=operator&is_active=true" \
  -H "Authorization: Bearer <tu_access_token>" \
  -H "X-Tenant-ID: 1"
```

### 3.3 Buenas Prácticas

| Práctica | Recomendación |
|----------|---------------|
| **Principio de mínimo privilegio** | Asigna el rol más bajo que el usuario necesite. No todos necesitan ser admin |
| **Una persona = una cuenta** | No compartas credenciales. Crea una cuenta por persona |
| **Cuentas de servicio** | Para integraciones futuras, usa rol `operator` con contraseñas generadas (`openssl rand -hex 16`) |
| **Revisión periódica** | Cada 3 meses, revisa la lista de usuarios. Desactiva cuentas inactivas |
| **Contraseñas temporales** | Comunica la contraseña por canal seguro (teléfono, WhatsApp, en persona). No por email sin cifrar |

---

## 4. Roles y Permisos

### 4.1 Matriz de Permisos

| Acción | admin | manager | operator | viewer |
|--------|:---:|:---:|:---:|:---:|
| Ver Dashboard | ✅ | ✅ | ✅ | ✅ |
| Ver Reportes | ✅ | ✅ | ✅ | ✅ |
| Ejecutar Setup/Simulación | ✅ | ✅ | ✅ | ❌ |
| Registrar Kárdex (entradas/salidas) | ✅ | ✅ | ✅ | ❌ |
| Cambiar Branding (Ajustes) | ✅ | ✅ | ❌ | ❌ |
| Crear usuarios | ✅ | ❌ | ❌ | ❌ |
| Listar usuarios | ✅ | ❌ | ❌ | ❌ |
| Ver info sensible de usuarios | ✅ | ❌ | ❌ | ❌ |

### 4.2 Descripción de Roles

#### 👑 Admin
- **Propósito:** Dueño del tenant, responsable de la configuración y seguridad
- **Perfil típico:** Dueño de la franquicia, gerente general, TI
- **Puede hacer todo** dentro de su tenant
- **No puede** acceder a otros tenants

#### 🧑‍💼 Manager
- **Propósito:** Gerencia operativa y financiera
- **Perfil típico:** Gerente de tienda, administrador, contador
- Puede operar el sistema completo, cambiar branding
- **No puede** crear o gestionar usuarios

#### 👨‍🍳 Operator
- **Propósito:** Operación diaria
- **Perfil típico:** Jefe de cocina, encargado de almacén, cajero
- Puede registrar operaciones de kárdex y ejecutar simulaciones
- **No puede** cambiar configuración ni branding

#### 👀 Viewer
- **Propósito:** Solo consulta
- **Perfil típico:** Inversionista, auditor externo, franquiciador
- Solo ve dashboard y reportes
- **No puede** modificar nada

### 4.3 Cuándo Usar Cada Rol

| Situación | Rol recomendado |
|-----------|----------------|
| Dueño de la cevichería | admin |
| Administrador de tienda | manager |
| Cocinero / almacenero | operator |
| Contador externo | viewer (o operator si registra asientos) |
| Inversionista | viewer |
| Auditor | viewer |

---

## 5. Configuración de Empresa

### 5.1 Setup Wizard — Qué Sucede Técnicamente

Cuando se ejecuta el Setup Wizard (`POST /api/accounting/setup`), el sistema:

1. **Registra la inversión inicial** como asientos contables:
   - Capital → cuenta de Patrimonio
   - Préstamo → cuenta de Pasivo
   - Equipos/muebles → cuentas de Activo No Corriente

2. **Simula 12 meses** de operación generando asientos automáticos:
   - Ventas mensuales → Ingresos
   - Costo de insumos → Egresos
   - Gastos fijos mensuales → Egresos
   - Depreciación mensual → Egresos (sin salida de caja)
   - Intereses del préstamo → Egresos financieros
   - Amortización del préstamo → Reducción de pasivo

3. **Calcula estados financieros:**
   - PYG acumulado de 12 meses
   - Balance General al cierre
   - BCSS con todas las cuentas

4. **Calcula ratios financieros** con semáforo

### 5.2 Variables Clave y su Impacto

| Variable | Impacto principal | Rango típico para cevichería |
|----------|-------------------|------------------------------|
| Capital propio | Determina cuánto necesitas de préstamo | S/ 30,000 – S/ 80,000 |
| Precio del plato | Ingresos directos | S/ 18 – S/ 45 |
| Platos por día | Volumen de ventas | 30 – 150 |
| Costo de insumos (%) | Margen bruto | 35% – 45% |
| Alquiler | Segundo gasto más grande | S/ 1,500 – S/ 5,000 |
| Sueldos | Mayor gasto operativo | S/ 3,000 – S/ 10,000 |

> 💡 El costo de insumos en cevichería suele ser 35-40%. Si tu simulación muestra >45%, revisa precios de proveedores o ajusta el precio del plato.

---

## 6. Interpretación de Ratios Financieros

### 6.1 Liquidez

| Ratio | Fórmula | 🟢 Saludable | 🟡 Precaución | 🔴 Crítico |
|-------|---------|:---:|:---:|:---:|
| **Liquidez Corriente** | Activo Cte / Pasivo Cte | > 1.5 | 1.0 – 1.5 | < 1.0 |
| **Prueba Ácida** | (Activo Cte − Inventario) / Pasivo Cte | > 1.0 | 0.7 – 1.0 | < 0.7 |

**Interpretación:**
- 🟢 **Liquidez > 1.5**: La empresa puede pagar sus deudas de corto plazo holgadamente
- 🟡 **Liquidez 1.0 – 1.5**: Cubre justo. Cualquier imprevisto puede causar problemas
- 🔴 **Liquidez < 1.0**: No alcanza a cubrir deudas de corto plazo. Peligro de insolvencia

### 6.2 Endeudamiento

| Ratio | Fórmula | 🟢 Saludable | 🟡 Precaución | 🔴 Crítico |
|-------|---------|:---:|:---:|:---:|
| **Endeudamiento Total** | Pasivo Total / Activo Total | < 40% | 40% – 60% | > 60% |

**Interpretación:**
- 🟢 **< 40%**: Mayoría del negocio es capital propio. Bajo riesgo
- 🟡 **40% – 60%**: Apalancamiento moderado. Vigila los intereses
- 🔴 **> 60%**: Altamente endeudado. Los intereses pueden comerse las ganancias

### 6.3 Rentabilidad

| Ratio | Fórmula | 🟢 Saludable | 🟡 Precaución | 🔴 Crítico |
|-------|---------|:---:|:---:|:---:|
| **Margen Neto** | Utilidad Neta / Ventas | > 15% | 8% – 15% | < 8% |
| **ROE** | Utilidad Neta / Patrimonio | > 20% | 10% – 20% | < 10% |
| **ROA** | Utilidad Neta / Activo Total | > 10% | 5% – 10% | < 5% |

**Interpretación:**
- 🟢 **Margen Neto > 15%**: Rentabilidad excelente para el sector alimentos
- 🟡 **Margen Neto 8-15%**: Rentabilidad aceptable pero ajustada
- 🔴 **Margen Neto < 8%**: Márgenes muy bajos. Revisa costos o precios
- **ROE > 20%**: El retorno sobre tu inversión es atractivo. Rinde más que un depósito a plazo
- **ROA > 10%**: Uso eficiente de los activos para generar ganancias

### 6.4 Payback (Recuperación de Inversión)

| Ratio | 🟢 Saludable | 🟡 Precaución | 🔴 Crítico |
|-------|:---:|:---:|:---:|
| **Payback (meses)** | < 18 | 18 – 30 | > 30 |

**Interpretación:**
- 🟢 **< 18 meses**: Recuperas tu inversión en menos de año y medio
- 🟡 **18 – 30 meses**: Retorno aceptable pero lento
- 🔴 **> 30 meses**: Inversión difícil de justificar. Revisa el modelo

### 6.5 Cobertura de Intereses

| Ratio | 🟢 Saludable | 🟡 Precaución | 🔴 Crítico |
|-------|:---:|:---:|:---:|
| **Cobertura de Intereses** | > 4.0 | 2.0 – 4.0 | < 2.0 |

**Interpretación:**
- 🟢 **> 4**: La utilidad operativa cubre los intereses 4 veces. Muy holgado
- 🟡 **2 – 4**: Cubre pero con poco margen
- 🔴 **< 2**: La operación apenas cubre los intereses. Si bajan las ventas, no podrás pagar el préstamo

---

## 7. Rate Limiting y Bloqueos

### 7.1 Capas de Protección

IaaS-RonSys implementa **3 capas** de protección contra ataques de fuerza bruta:

| Capa | Límite | Ventana | Implementación |
|------|--------|--------|----------------|
| **Rate Limit por IP** | 5 intentos | 1 minuto | Redis SORTED SET |
| **Rate Limit por Email** | 5 intentos | 1 minuto | Redis SORTED SET (email hasheado) |
| **Bloqueo de Cuenta** | 10 fallos consecutivos | 15 minutos | Campo `locked_until` en DB |

### 7.2 Cómo Funciona el Bloqueo de Cuenta

1. Un usuario falla el login → `failed_login_attempts` se incrementa en 1
2. Al llegar a 10 fallos consecutivos → `locked_until` se establece a `ahora + 15 minutos`
3. Durante el bloqueo, **cualquier intento de login es rechazado** (incluso con contraseña correcta)
4. Tras 15 minutos, el bloqueo expira automáticamente
5. Un login exitoso en cualquier momento **resetea** el contador a 0

### 7.3 ¿Qué Hacer si un Usuario Está Bloqueado?

**Opción 1: Esperar** (recomendado para bloqueos por error del usuario)
- El usuario debe esperar 15 minutos desde el último intento fallido
- El sistema muestra el tiempo restante en el mensaje de error

**Opción 2: Desbloqueo manual** (si es urgente, vía base de datos)

```sql
-- Desbloquear un usuario específico
UPDATE users
SET failed_login_attempts = 0,
    locked_until = NULL,
    updated_at = NOW()
WHERE email = 'usuario@elsegoviano.pe';
```

> ⚠️ Solo haz esto si estás **seguro** de que no es un ataque. Si ves múltiples bloqueos en poco tiempo, investiga.

### 7.4 Rate Limiting — Diagnóstico

Si un usuario reporta "Demasiados intentos" (HTTP 429):

- El rate limiting es por **IP + email simultáneamente**
- 5 intentos por minuto desde la misma IP **o** contra el mismo email
- Se resetea automáticamente tras 60 segundos
- **No afecta a otros usuarios** en la misma IP (el límite de email es independiente)

---

## 8. Troubleshooting

### 8.1 Problemas de Login

| Síntoma | Causa probable | Acción |
|---------|---------------|--------|
| "Email o contraseña inválidos" con credenciales correctas | Usuario inactivo (`is_active = false`) | Verificar estado en BD |
| "Cuenta bloqueada" con solo 3 intentos | El usuario (u otra persona) intentó más veces de las que reporta | Revisar `failed_login_attempts` en BD |
| Múltiples usuarios bloqueados en poco tiempo | Posible ataque de fuerza bruta | Revisar logs del backend, verificar IPs |
| Login lento (> 2 segundos) | Redis caído — rate limiting en fallback in-memory | Verificar Redis: `docker-compose ps redis` |
| Error 500 en login | Error interno del backend | Revisar logs: `docker-compose logs backend` |

### 8.2 Problemas de Datos

| Síntoma | Causa probable | Acción |
|---------|---------------|--------|
| Dashboard sin datos para un tenant | No se ha ejecutado simulación | Ejecutar Setup Wizard |
| Dos tenants ven los mismos datos | Error de scoping (grave) | Reportar inmediatamente al equipo técnico |
| Datos inconsistentes entre PYG y Balance | Error en motor contable | Revisar BCSS — el Debe debe igualar al Haber |
| Productos duplicados en Kárdex | Código de producto repetido | Usar códigos únicos. Eliminar duplicado vía BD si es necesario |

### 8.3 Problemas de Infraestructura

| Síntoma | Verificación | Acción |
|---------|-------------|--------|
| Frontend no carga (conexión rechazada) | `curl http://localhost:5173` | `docker-compose up -d web` |
| Backend no responde | `curl http://localhost:8000/api/health` | `docker-compose up -d backend` |
| Base de datos no accesible | `docker-compose exec db pg_isready -U postgres` | `docker-compose restart db` |
| Redis no disponible | `docker-compose exec redis redis-cli PING` | `docker-compose restart redis` |

### 8.4 Logs

```bash
# Ver logs del backend en tiempo real
docker-compose logs -f backend

# Ver últimas 100 líneas
docker-compose logs --tail=100 backend

# Ver logs de todos los servicios
docker-compose logs -f

# Buscar errores específicos
docker-compose logs backend | grep -i error
```

---

## 9. Comandos de Infraestructura

### 9.1 Servicios Docker

```bash
# Ver estado de todos los servicios
docker-compose ps

# Levantar todo
docker-compose up -d

# Detener todo
docker-compose down

# Reiniciar un servicio específico
docker-compose restart backend

# Reconstruir y levantar (tras cambios de código)
docker-compose up -d --build backend
```

### 9.2 Base de Datos

```bash
# Acceder a la consola de PostgreSQL
docker-compose exec db psql -U postgres -d iaas_ronsys

# Ejecutar migraciones pendientes
docker-compose exec backend alembic upgrade head

# Ver estado de migraciones
docker-compose exec backend alembic current

# Revertir última migración (¡cuidado!)
docker-compose exec backend alembic downgrade -1
```

### 9.3 Consultas Útiles en BD

```sql
-- Ver todos los usuarios de un tenant
SELECT id, email, full_name, role, is_active, created_at
FROM users WHERE company_id = 1;

-- Ver intentos fallidos de login
SELECT email, failed_login_attempts, locked_until, last_login_at
FROM users WHERE failed_login_attempts > 0;

-- Ver sesiones activas (refresh tokens no revocados ni expirados)
SELECT u.email, rt.created_at, rt.created_by_ip, rt.expires_at
FROM refresh_tokens rt
JOIN users u ON u.id = rt.user_id
WHERE rt.revoked_at IS NULL AND rt.expires_at > NOW();

-- Revocar todas las sesiones de un usuario
UPDATE refresh_tokens
SET revoked_at = NOW()
WHERE user_id = (SELECT id FROM users WHERE email = 'usuario@email.com')
  AND revoked_at IS NULL;

-- Desbloquear un usuario
UPDATE users
SET failed_login_attempts = 0, locked_until = NULL
WHERE email = 'usuario@email.com';
```

---

## 10. Referencia de Endpoints (Admin)

### 10.1 Auth Endpoints

| Método | Endpoint | Auth Requerida | Propósito |
|--------|----------|:---:|---|
| `POST` | `/api/auth/login` | ❌ No | Iniciar sesión |
| `POST` | `/api/auth/refresh` | ❌ No | Renovar access token |
| `POST` | `/api/auth/logout` | ❌ No | Cerrar sesión |
| `GET` | `/api/auth/me` | ✅ Sí | Perfil del usuario actual |

### 10.2 Admin Endpoints

| Método | Endpoint | Rol | Propósito |
|--------|----------|:---:|---|
| `POST` | `/api/admin/users` | admin | Crear usuario en el tenant |
| `GET` | `/api/admin/users` | admin | Listar usuarios del tenant |

### 10.3 Accounting Endpoints (Protegidos)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/accounting/setup` | Simulación financiera completa |
| `GET` | `/api/accounting/bcss` | Balance de Comprobación |
| `GET` | `/api/accounting/pyg` | Estado de Resultados |
| `GET` | `/api/accounting/balance` | Balance General |
| `GET` | `/api/accounting/ratios` | Ratios con semáforo |
| `POST` | `/api/accounting/transaction` | Registrar transacción manual |
| `POST` | `/api/accounting/kardex/products` | Registrar producto |
| `POST` | `/api/accounting/kardex/entry` | Entrada (compra) |
| `POST` | `/api/accounting/kardex/exit` | Salida (venta/merma) |
| `GET` | `/api/accounting/kardex/{code}` | Consultar kárdex de producto |
| `GET` | `/api/accounting/kardex/inventory/summary` | Inventario actual |

### 10.4 Settings Endpoints

| Método | Endpoint | Roles | Propósito |
|--------|----------|:---:|---|
| `GET` | `/api/settings` | Todos | Obtener configuración |
| `PATCH` | `/api/settings` | admin, manager | Modificar configuración |
| `GET` | `/api/settings/palette` | Todos | Obtener paleta de colores |
| `PATCH` | `/api/settings/palette` | admin, manager | Cambiar paleta |

---

## 📋 Checklist de Administración Periódica

### Semanal
- [ ] Revisar que el Dashboard muestre datos actualizados
- [ ] Verificar que no haya usuarios bloqueados sin motivo

### Mensual
- [ ] Respaldar la base de datos
- [ ] Revisar ratios financieros, especialmente Liquidez y Endeudamiento

### Trimestral
- [ ] Auditar lista de usuarios: ¿hay cuentas inactivas que desactivar?
- [ ] Revisar logs de login en busca de patrones sospechosos
- [ ] Actualizar contraseña del admin principal

### Ante Incidentes
- [ ] Usuario bloqueado → verificar si fue error o ataque
- [ ] Múltiples 429 → posible fuerza bruta. Revisar IPs en logs
- [ ] Datos inconsistentes → verificar BCSS, reportar al equipo técnico

---

> 📞 **Escalamiento:** Si encuentras un problema que no puedes resolver con este manual, contacta al equipo técnico con los logs relevantes (`docker-compose logs backend --tail=200`).

---

> IaaS-RonSys · El Segoviano · v0.1.0  
> *"Con poder viene responsabilidad. Administra con criterio."*
