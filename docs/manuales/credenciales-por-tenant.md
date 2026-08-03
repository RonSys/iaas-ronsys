# 🔑 Credenciales por Tenant — IaaS-RonSys (Producción)

- **Fecha de verificación:** 2026-08-03 (consultado directo en BD de producción `iaas_ronsys`)
- **Producción:** https://www.ronsyserp.com · Login: https://www.ronsyserp.com/login
- **Landing delivery (pública):** https://www.ronsyserp.com/menu/el-segoviano
- **Panel delivery (staff):** https://www.ronsyserp.com/restaurante/delivery
- ⚠️ **Ojo:** `deploy.sh` resetea las passwords demo a los valores de abajo en cada deploy.

---

## 🏢 Tenants (tabla `companies`)

| ID | Nombre | Slug | Tipo | Nota |
|---|---|---|---|---|
| 1 | **Admin Tenant** | `el-segoviano` | restaurant | **Tenant activo del delivery** (landing pública, Zona 1) |
| 3 | El Segoviano | `NULL` | restaurant | Cevichería (sin slug aún) |
| 5 | Ferretería El Segoviano | `NULL` | hardware | Demo ferretería |

---

## 👤 Usuarios por tenant

### Tenant 1 — Admin Tenant (`el-segoviano`) ⭐ RECOMENDADO PARA PRUEBAS

| Email | Password | Rol | Uso |
|---|---|---|---|
| `admin@elsegoviano.pe` | `admin123` | admin | **Principal**: panel delivery, settings, POS, métricas, todo |
| `mesero@elsegoviano.pe` | `mesero123` | operator | Mesas / toma de pedidos |
| `cocinero@elsegoviano.pe` | `cocinero123` | operator | Kanban de cocina |
| `test@elsegoviano.pe` | *(seed test)* | operator | Usuario de prueba genérico |
| `testqa@elsegoviano.pe` | *(seed test)* | operator | QA |
| `operator@test.com` | *(seed test)* | operator | QA |
| `locktest@elsegoviano.pe` | *(seed test)* | viewer | QA bloqueo |
| `inactive_test@test.com` | *(seed test)* | viewer | QA inactivo |

### Tenant 3 — El Segoviano (cevichería)

| Email | Password | Rol |
|---|---|---|
| `admincevicheria@elsegoviano.pe` | *(seed tenant 3)* | admin |
| `mesero1@elsegoviano.pe` | `mesero123` | operator |
| `cocinero1@elsegoviano.pe` | `cocinero123` | operator |

### Tenant 5 — Ferretería El Segoviano (demo hardware)

| Email | Password | Rol |
|---|---|---|
| `ferretero@elsegoviano.pe` | `ferreteria123` | admin |

### Superadmin (gestión global)

| Email | Password | Rol |
|---|---|---|
| `admin@iaas.com` | `Admin2026!` | **superadmin** |
| `demo@iaas.com` | `Demo2026!` | demo (corregido por seed_superadmin) |

---

## 🧪 Datos de prueba del módulo delivery (tenant 1)

- **Zona 1 (única activa):** Montenegro / Motupe / Canto Grande — fee S/5.00 · min S/35.00 · ETA 35 min
- **Yape del negocio:** `912057784` (configurado en `settings.delivery.yape_phone`)
- **Horario delivery:** 19:00 – 23:59
- **Slug público:** `el-segoviano` → `/menu/el-segoviano`
- **Tracking de ejemplo (cancelado):** `DLV-9fc6268b79`

---

## 🔗 Endpoints útiles

| Endpoint | Auth | Descripción |
|---|---|---|
| `POST /api/auth/login` | — | Login (email+password → JWT) |
| `GET /api/public/el-segoviano/menu` | ❌ público | Menú delivery + branding + yape_phone |
| `GET /api/public/el-segoviano/zones` | ❌ público | Zonas activas |
| `POST /api/public/el-segoviano/orders` | ❌ público | Checkout delivery |
| `GET /api/public/orders/{tracking}/status` | ❌ público | Tracking |
| `/api/v1/delivery/*` | JWT | Panel staff (zonas, repartidores, campañas, pedidos, métricas) |

---

## ℹ️ Notas

- Las passwords `*(seed test)*` no se documentan aquí por higiene; se pueden re-consultar en BD o usar los usuarios principales.
- Fuente de verificación: `apps/backend/scripts/seed_db.py`, `seed_superadmin.py`, `docs/reports/qa-validation-seed-demo-users*.md`, consulta directa a BD prod.
- **No commitear este archivo al repo público si contiene secretos reales** — aquí solo hay credenciales demo del sistema (seguras para incluir en docs internos).
