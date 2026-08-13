# 📘 Manual Operativo — Servicio de Activación WhatsApp Business (F1) + Carga de Configuración

- **Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
- **Spec:** `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md` (F1 — WhatsApp en Vivo, 🟢 APROBADA)
- **Fecha:** 2026-08-13
- **Audiencia:** Equipo IaaS-RonSys (quien ejecuta el trámite y la configuración)
- **Tipo de servicio:** ⭐ **SERVICIO INCLUIDO EN LA F1** — el cliente nos da acceso a sus cuentas Meta (o las creamos desde cero con él) y nos entrega un **número de prepago**; nosotros ejecutamos todo el trámite + carga de configuración.

---

## 0. Alcance de este manual

Este manual cubre los 2 puntos del "cuello de botella externo" de la F1:

1. **Trámite de la cuenta Meta Cloud API del cliente** + aprobación de las **7 plantillas Utility** (§1–§5).
2. **Carga de la configuración** en `companies.settings.whatsapp` (JSONB) — **solo configuración, sin deploy** (§6).

No cubre: código (ya implementado y mergeado), deploy, ni QA en vivo (ver spec §3.9 y el doc de simulación).

**Modelo de servicio acordado con el cliente:**
- El cliente nos **otorga acceso** a sus cuentas Meta existentes, **o autoriza crear cuentas desde cero** con sus datos (RUC/titularidad).
- El cliente nos entrega un **número de prepago** (línea celular con WhatsApp Business) que será el número del negocio.
- Nosotros (equipo IaaS-RonSys) ejecutamos el trámite completo: Business Manager, verificación, app, System User, registro de número, plantillas y configuración final.

---

## 1. Definición del número del negocio (paso 0)

| Campo | Detalle |
|---|---|
| **Qué es** | Línea celular prepago con app **WhatsApp Business** instalada, **titular del local** (El Segoviano) |
| **Quién lo aporta** | Cliente (compra del chip prepago; costo mínimo ~S/ 5–10 + recargas) |
| **Importante** | El número **NO debe estar vinculado** a otra cuenta WhatsApp Business API. Debe poder recibir el **SMS/llamada de verificación** de Meta |
| **Resultado** | → se guarda en `settings.whatsapp.business_phone` (D4) |

**Regla dura (heredada de Spec 03 §7.3):** NUNCA usar el número del agente (+51 975 224 103) ni ningún número personal del equipo. El número del negocio es del cliente, siempre.

**Recomendación al cliente:** comprar el chip prepago **antes** de empezar el trámite (día 1), porque la portabilidad o activación de línea puede tomar 1–2 días.

---

## 2. Cuenta Meta Business Manager + verificación

### 2.1 ¿Cuenta existente o desde cero?

- Si el cliente ya tiene **cuenta personal Meta** (la de Ron con 2 fanpages): usamos **Business Manager dedicado al negocio** (recomendado, separación limpia — ver `plan-cuenta-meta-whatsapp.md`).
- Si no tiene nada: **creamos desde cero** en `business.facebook.com` con los datos del negocio (nombre legal "El Segoviano", RUC, país Perú, correo de contacto).

### 2.2 Pasos (quién: cliente acompañado por el equipo)

1. Ir a `https://business.facebook.com` → **Crear cuenta de empresa** (gratis).
2. Datos: nombre del negocio, nombre legal, país (**Perú**), correo de contacto (del cliente), número de teléfono.
3. **Añadir al equipo**: Ron + encargado del local como empleados/administradores + cuenta técnica del equipo (si aplica).
4. **Verificación del negocio** (Business Verification): subir documentación (RUC, representante legal). Puede tomar **días a semanas** — iniciar el día 1.
   - Se necesita: nombre legal, dirección, documentos (constancia RUC), dominio (ronsyserp.com) si se usa.
5. Resultado: acceso a Business Manager verificado.

> ⚠️ La verificación del negocio es **requisito** para usar Cloud API de forma estable. Sin verificación, Meta puede restringir el número.

---

## 3. App en Meta for Developers + producto WhatsApp Cloud API

**Quién:** equipo IaaS-RonSys (con acceso del cliente al Business Manager).

1. Ir a `https://developers.facebook.com` → **Mis Apps** → **Crear app**.
2. Tipo: **Business**. Nombre sugerido: `segoviano-whatsapp`.
3. Asociar la app al **Business Manager** del cliente (paso 2).
4. En la app → **Add products** → **WhatsApp** → configurar **WhatsApp Cloud API**.
5. Resultado: **App ID** y **App Secret** (guardar App Secret en el gestor de secretos del cliente, NUNCA en código).

---

## 4. System User + token de acceso (el `token` del settings)

**Quién:** equipo (o cliente con guía). Permisos **mínimos**.

1. En Business Manager → **Configuración** → **Usuarios del sistema** → **Agregar** → **Empleado del sistema**.
2. Nombre: `iaas-ronsys-whatsapp`. Rol: **Admin** (o Empleado con permisos específicos).
3. **Asignar activos**: la app (paso 3) y el número de teléfono (paso 5, cuando exista).
4. **Generar token**: con permisos exactos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. **Caducidad**: elegir token que **no expire** (o renovar por cron) — anotar fecha de renovación en el calendario del proyecto.
6. Resultado: `EAAG...` → **`settings.whatsapp.token`**

> 🔒 **Regla de oro:** el token se guarda SOLO en `companies.settings` (BD) y en el gestor de secretos del cliente. NUNCA en código, logs, READMEs, respaldos de código ni chats.

---

## 5. Registrar el número + Phone Number ID + 7 plantillas

### 5.1 Registrar el número en Cloud API

**Quién:** equipo.

1. En la app (paso 3) → **WhatsApp** → **Configuración de API** → **Números de teléfono** → **Agregar número de teléfono**.
2. Ingresar el **número prepago** (paso 1, formato `+51...`).
3. Meta envía **código de verificación por SMS/llamada** al número → ingresarlo.
4. Resultado: **Phone Number ID** (identificador numérico largo) → **`settings.whatsapp.phone_number_id`**

### 5.2 Crear y aprobar las 7 plantillas Utility (idioma `es`)

**Quién:** equipo (con acceso). Categoría: **Utility** (transaccional — aprobación más rápida y estable).

| Key del settings | Nombre en Meta | Variables | Cuerpo sugerido |
|---|---|---|---|
| `confirmed` | `segoviano_pedido_confirmado` | `{{1}}` código, `{{2}}` total | *¡Gracias por tu pedido, {{1}}!* ✅ Tu pedido *DLV-…* por **S/ {{2}}** fue confirmado. Te avisamos cuando esté en camino. — El Segoviano |
| `preparing` | `segoviano_pedido_preparando` | `{{1}}` código | Tu pedido *{{1}}* está **en cocina** 👨🍳. — El Segoviano |
| `ready` | `segoviano_pedido_listo` | `{{1}}` código, `{{2}}` tiempo | Tu pedido *{{1}}* está **listo** y sale en ~{{2}} min 🛵. — El Segoviano |
| `delivered` | `segoviano_pedido_entregado` | `{{1}}` código | ¡Tu pedido *{{1}}* fue **entregado**! 🙌 Gracias por pedir con El Segoviano. |
| `cancelled` | `segoviano_pedido_cancelado` | `{{1}}` código, `{{2}}` teléfono | Tu pedido *{{1}}* fue **cancelado**. Si fue un error, llámanos al {{2}} — El Segoviano |
| `new_order` | `segoviano_alerta_pedido_nuevo` | `{{1}}` código, `{{2}}` total, `{{3}}` zona | 🛎️ *Pedido nuevo* *{{1}}* — S/ {{2}} — Zona {{3}}. Revisa el panel. |
| `order_cancelled` | `segoviano_alerta_pedido_cancelado` | `{{1}}` código | ⚠️ *Pedido cancelado* *{{1}}*. Verifica en el panel. |

**Reglas Meta para aprobación rápida (D2):**
- Categoría **Utility** (nunca Marketing) → más baratas y estables.
- **Sin emojis excesivos de marketing** (usar solo los de contexto operativo ✅👨🍳🛵🙌⚠️🛎️ como arriba).
- **Sin links** en el cuerpo (los links van en botones de plantilla si aplica).
- Contenido dinámico SOLO en variables `{{n}}` (nunca texto libre variable).
- Idioma `es` (Español). Si Meta lo pide, agregar `es_PE` como variante regional.
- Formato estable → aprobación en **< 6 h a 24–48 h** (Meta anuncia <6h pero no confiar: enviar temprano).

**Resultado:** nombres aprobados → se copian EXACTOS en `settings.whatsapp.templates{}` (§6).

---

## 6. Carga de configuración — `companies.settings.whatsapp` (solo configuración, SIN deploy)

El código ya está en producción (mergeado en main). Esto es **configuración de datos**, no despliegue.

### 6.1 Contrato JSON (valores de ejemplo estructurales — reemplazar con los reales del cliente)

```json
{
  "enabled": false,
  "provider": "meta_cloud",
  "phone_number_id": "123456789012345",
  "token": "EAAG...",
  "business_phone": "+51999999999",
  "alert_phone": "+51999999998",
  "templates": {
    "confirmed": "segoviano_pedido_confirmado",
    "preparing": "segoviano_pedido_preparando",
    "ready": "segoviano_pedido_listo",
    "delivered": "segoviano_pedido_entregado",
    "cancelled": "segoviano_pedido_cancelado",
    "new_order": "segoviano_alerta_pedido_nuevo",
    "order_cancelled": "segoviano_alerta_pedido_cancelado"
  }
}
```

### 6.2 Cómo cargarla

**Opción A — PATCH `/api/settings` (recomendada, patrón D-03):**

```bash
# Con sesión de staff autenticada + X-Tenant-ID del tenant El Segoviano (1)
curl -X PATCH https://www.ronsyserp.com/api/settings \
  -H "Authorization: Bearer <token_staff>" \
  -H "X-Tenant-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "whatsapp": {
      "enabled": false,
      "provider": "meta_cloud",
      "phone_number_id": "<REAL>",
      "token": "<REAL>",
      "business_phone": "+51...",
      "alert_phone": "+51...",
      "templates": { ... }
    }
  }'
```

**Opción B — SQL directo (solo si no hay acceso por API; con precaución):**

```sql
UPDATE companies
SET settings = jsonb_set(
  settings,
  '{whatsapp}',
  '{"enabled": false, "provider": "meta_cloud", ...}'::jsonb
)
WHERE id = 1;  -- tenant El Segoviano
```

### 6.3 Secuencia de activación (importante — orden seguro)

1. Cargar la config con **`enabled: false`** → el sistema sigue en **dry-run** (no envía nada, solo loguea) aunque el token sea real. **Verificar** con un pedido de prueba: eventos publicados, worker consume, `DryRunNotifier` loguea, cero HTTP (CA-B7).
2. **QA en vivo dry-run** con las plantillas reales aprobadas (nombres existen en Meta).
3. Recién cuando todo verifique: `enabled: true` → **1 pedido real de prueba** → confirmar entrega en el celular del cliente.
4. **Rollback probado**: `enabled: false` devuelve al dry-run al instante (switch reversible D6). Documentar el procedimiento.

### 6.4 Verificación post-carga

- `GET /api/public/{slug}/menu` → `contact` con `whatsapp_link` y `phone` (solo si `enabled=true` y hay `business_phone`) — CA-F1.14.
- Botones visibles en landing `/menu/el-segoviano` y pestaña Campañas.
- `delivery_orders.whatsapp_bsuid` acepta el campo (migración 0017 aplicada).

---

## 7. Checklist de entrega del servicio (para reportar al cliente)

| # | Ítem | Estado |
|---|---|---|
| 1 | Número prepago del cliente recibido y verificado (WhatsApp Business) | ☐ |
| 2 | Business Manager creado/vinculado + verificación enviada/aprobada | ☐ |
| 3 | App creada + producto WhatsApp Cloud API configurado | ☐ |
| 4 | System User + token (permisos mínimos) generado y guardado en secreto | ☐ |
| 5 | Número registrado en Cloud API + Phone Number ID obtenido | ☐ |
| 6 | 7 plantillas Utility creadas y **APROBADAS** por Meta | ☐ |
| 7 | Config cargada en `companies.settings.whatsapp` (`enabled: false`) | ☐ |
| 8 | QA dry-run con plantillas reales (CA-F1.5/6) | ☐ |
| 9 | Activación `enabled: true` + prueba real (CA-F1.1–1.4) | ☐ |
| 10 | Rollback probado y documentado | ☐ |
| 11 | Botones visibles en landing y campañas (CA-F1.7/8/9) | ☐ |
| 12 | BSUID persistido en `delivery_orders.whatsapp_bsuid` (CA-F1.10) | ☐ |

---

## 8. Tiempos estimados y cuello de botella

| Paso | Tiempo típico |
|---|---|
| Chip prepago + WhatsApp Business | 1 día (cliente) |
| Business Manager + verificación | **3–15 días** (Meta) ⚠️ |
| App + Cloud API + System User | 1–2 h (equipo) |
| Registro del número (SMS) | 10 min |
| Plantillas Utility (aprobación) | **<6 h – 48 h** (Meta) ⚠️ |
| Config + QA dry-run | 2–4 h (equipo) |
| Activación real + rollback | 1–2 h (equipo) |

> **Conclusión:** el cuello de botella es la **verificación del negocio** y la **aprobación de plantillas** (ambos de Meta). Por eso el trámite debe iniciarse el **día 1**, en paralelo a cualquier otra actividad.

---

## 9. Costos recurrentes (los asume el cliente)

| Concepto | Estimado |
|---|---|
| WhatsApp Business API (plantillas Utility) | ~S/ 30–150/mes según volumen |
| Respuestas dentro de ventana de servicio 24h (cliente escribe primero) | **Gratis** |
| Chip prepago | ~S/ 5–10 + recargas |

> Estrategia de costo: alentamos a que el cliente **responda dentro de la ventana de servicio** (24h desde que el cliente escribe) — las respuestas libres y plantillas Utility dentro de la ventana son gratis.

---

*Manual operativo — Equipo IaaS-RonSys · 2026-08-13 · Vinculado a Spec 04 (F1) y `plan-cuenta-meta-whatsapp.md`.*
