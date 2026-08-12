# SPEC 04 — F1 "WhatsApp en Vivo" — Plan Integral de Canales (El Segoviano)

- **Estado**: 🟡 **PROPUESTA (2026-08-12)** — pendiente aprobación de Ron y decisiones D1–D7 (§0). Se apoya sobre infraestructura **ya desplegada y verificada en producción** (Spec 03 §7 — motor WhatsApp dry-run).
- **Proyecto**: IaaS-RonSys — Cliente "El Segoviano"
- **Alcance**: Fase 1 "WhatsApp en Vivo" del Plan Integral de Canales (llamadas/atención 2026-08-12); tenant 1 (El Segoviano); diseño multi-tenant por construcción
- **Fecha**: 2026-08-12
- **Framework**: SDD / Spec Anchor — esta spec está sincronizada con el código (Spec 03 §7 como base; cualquier cambio en uno debe reflejarse en el otro)

---

## 0. Decisiones (D1–D7 — PROPUESTAS, pendientes de aprobación)

Complementan la decisión D-B1 ya aprobada en Spec 03 §7.3 (Meta Cloud API oficial + interfaz `Notifier` agnóstica).

| # | Decisión | Acuerdo propuesto |
|---|---|---|
| D1 | Cuenta Meta Cloud API | **Número propio del negocio**, cuenta gestionada por el **cliente** (titular: verificación de negocio y número) con acompañamiento del equipo IaaS-RonSys. El equipo no crea la cuenta a nombre propio. Reafirma D-B1. |
| D2 | Categoría de plantillas | **TODAS las plantillas de F1 en categoría Utility (transaccionales)** — formato más estable y barato de la plataforma (pago por mensaje, sin recargo marketing). **Cero plantillas Marketing en F1.** |
| D3 | BSUID desde el día 1 | Guardar el identificador nuevo de Meta (`user_id` / BSUID) junto a `customer_phone` desde F1: columna `delivery_orders.whatsapp_bsuid` (varchar(64), nullable) + campo `bsuid` en el payload de eventos; el worker lo persiste cuando viene presente. Requisito de cumplimiento Meta (usernames/BSUID, en vigencia desde 31-mar-2026 en adelante). |
| D4 | Números en settings | `business_phone` = número **verificado del negocio** (remitente de todos los envíos); `alert_phone` = celular del local (alertas de pedido nuevo/cancelación). Ambos configurables en `companies.settings.whatsapp`. **Regla dura**: NUNCA usar el número wacli del agente (**+51 975 224 103**) — es canal del asistente, no del negocio. |
| D5 | Botones | "Pedir por WhatsApp" = enlace `https://wa.me/<business_phone>?text=<mensaje prefabricado>`; "Llamar" = `tel:<business_phone>`. Ubicaciones: landing pública `/menu/{slug}` (hero + pantalla de éxito de pedido) y pestaña **Campañas** del panel Delivery (junto al link UTM autogenerado). Solo se renderizan si hay configuración válida (`enabled=true` + `business_phone`). |
| D6 | Activación dry-run → real | **Solo configuración** (`enabled=true` + `token` + `phone_number_id` en settings), sin cambio de código ni deploy. El switch es reversible (volver a `false` = dry-run inmediato). |
| D7 | Límites de F1 | **NO** se declara webhook de recepción (chatbot bidireccional queda fuera; se prepara el campo BSUID para F3). **NO** se toca telefonía (F2: Asterisk/trunk SIP). F1 es envío unidireccional con plantillas aprobadas. |

---

## 1. Contexto y objetivo

El local de El Segoviano ya opera delivery nocturno online completo (landing `/menu/{slug}`, zonas, repartidores, campañas con ROAS, tracking DLV-, Spec 03 Fase A) y desde el 2026-08-11 cuenta con el **motor de notificaciones WhatsApp desplegado y verificado en producción en modo dry-run** (Spec 03 Fase B): los eventos ya se publican a RabbitMQ, el worker ya "envía" contra un notifier de demostración y el pedido nunca depende del envío. **Lo único que falta para el valor real es conectar la cuenta Meta y activar el envío** — eso, más los botones de contacto, es exactamente la F1 "WhatsApp en Vivo" del Plan Integral de Canales (1–2 semanas · S/ 1,500 – 2,500, propuesta comercial 2026-08-12).

**Objetivo de negocio (en lenguaje cliente):** el cliente que pide por el menú nocturno recibe en su WhatsApp la **confirmación del pedido y los avisos automáticos** (en cocina, en camino, entregado, cancelado) sin que nadie le escriba; el local recibe **alerta automática** de pedido nuevo y cancelaciones; y desde el menú público y las campañas el cliente puede **"Pedir por WhatsApp"** (con el pedido ya armado) o **"Llamar"** con un toque.

**Qué resuelve:** hoy los avisos funcionan en modo demostración — el cliente no recibe el mensaje real. Con F1 el delivery nocturno se convierte en un canal con **comunicación automática y confiable**: menos llamadas de "¿cómo va mi pedido?", más confianza y más pedidos repetidos (benchmark reel 1: confirmación y seguimiento por WhatsApp).

**Fuera de alcance F1:** chatbot bidireccional / atención conversacional por WhatsApp (webhook de recepción), telefonía (F2 — Asterisk/trunk SIP, click-to-call solo como botón `tel:`), IA por voz (F3), multi-sucursal (F4), consultas IA (F5).

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-12)

### 2.1 El motor WhatsApp YA está desplegado y verificado en prod (dry-run) — reutilización directa

| Componente | Ubicación | Estado |
|---|---|---|
| Publicador de eventos (fire-and-forget) | `app/services/notify_events.py` | ✅ Desplegado |
| Worker consumidor + reintentos + DLQ | `app/services/notify_worker.py` | ✅ Desplegado (`iaas-worker-prod` en compose) |
| Interfaz `Notifier` agnóstica (MetaCloud/DryRun) | `app/services/whatsapp_notifier.py` | ✅ Desplegado |
| Schema `WhatsAppSettings` + `CompanySettings.whatsapp` | `app/schemas/__init__.py` (L249, L271–282) | ✅ Desplegado |
| Persistencia en `companies.settings.whatsapp` (JSONB, patrón D-03) | setup.py / settings router | ✅ Desplegado |
| Cola RabbitMQ `iaas-tasks` + `RABBITMQ_URL` al backend | compose (fix `c60227e`) | ✅ Desplegado |
| Fix `a2287fb` — routing_key = nombre de cola | `notify_events.py` L109 | ✅ Verificado en vivo (bug real: default exchange no ruteaba `delivery.*`) |

**Detalle verificado en código (2026-08-12):**
- **Eventos publicados** a la cola `iaas-tasks`: `delivery.confirmed` + `delivery.new_order` (checkout 201 — cliente y local), `delivery.status_changed` (cada transición válida), `delivery.cancelled` (alerta local, plantilla `order_cancelled`). `LOCAL_ALERT_EVENTS = {"new_order", "cancelled"}`.
- **Worker**: reintentos **3× (0s/60s/300s)** → agotados → dead-letter **`iaas-tasks-dlq`**; errores de CONFIG (sin plantilla/destinatario) se loguean y se hace ack sin reintentar (dry-run CA-B5/B7, cero HTTP); fallos del proveedor sí reintentan.
- **Notifier**: `Notifier` (Protocol) → `MetaCloudNotifier` (HTTP real) y `DryRunNotifier` (solo logs). `build_notifier` decide por config del tenant.
- **Schema**: `WhatsAppSettings` con `enabled / provider / phone_number_id / token / business_phone / alert_phone / templates{confirmed, preparing, ready, delivered, cancelled, new_order, order_cancelled}`; anidado en `CompanySettings.whatsapp` junto a `delivery` (mismo patrón D-03 que `yape_phone`).
- **Verificación en vivo (2026-08-11)**: checkout → `confirmed`+`new_order`; transición → `status_changed`; cancelación → `cancelled` — todo dry-run (cero HTTP); QA 8/8 CA-B1..B8; 22 tests.

### 2.2 Lo que FALTA para F1 (gaps)

| Gap | Tipo | Detalle |
|---|---|---|
| Cuenta Meta Cloud API real | **Externa** (cliente + acompañamiento) | `phone_number_id` + token System User + número del negocio **verificado** |
| 7 plantillas aprobadas por Meta | **Externa** | `confirmed / preparing / ready / delivered / cancelled / new_order / order_cancelled` (categoría Utility, D2) |
| Activación del envío real | Config | `enabled=true` + token + phone_number_id en `companies.settings.whatsapp` (D6) |
| Botones "Pedir por WhatsApp" (wa.me) y "Llamar" (tel:) | **Frontend** | **Verificado: 0 ocurrencias de `wa.me`/`tel:` en `apps/web/src/`** — no existen hoy; faltan en `PublicMenuPage.tsx` (landing `/menu/:slug`), pantalla de éxito del checkout y pestaña Campañas (`DeliveryPage.tsx`) |
| Campo BSUID | Backend menor | No existe columna `whatsapp_bsuid` ni campo `bsuid` en el payload (D3) |
| Contacto en respuesta pública | Backend menor | `PublicMenuResponse` expone `branding` y `yape_phone` pero **no** datos de WhatsApp/teléfono para los botones |

### 2.3 Regla dura y cumplimiento Meta 2026

- **Regla dura (D-B1/D4)**: NO usar el número wacli del agente **+51 975 224 103** en ninguna configuración, plantilla, enlace o log de F1 — es el canal del asistente, no del negocio.
- **Cumplimiento Meta 2026** (verificado en plan-fases §6): plantillas **transaccionales/Utility** (formato más estable; el código no quedará obsoleto — los cambios Meta afectan precios/reglas, no la tecnología base); **BSUID registrado desde el día 1** (D3); la IA (F3, fuera de alcance) se diseñará como agente de dominio acotado — requisito de Meta desde 15-ene-2026.

### 2.4 Dependencias externas (fuera de nuestro control — mitigar con trámite en paralelo)

| Dependencia | Riesgo | Mitigación |
|---|---|---|
| Verificación de la cuenta/número en Meta | Días (puede requerir documentación del titular) | Iniciar el día 1 del proyecto; el equipo acompaña, el cliente ejecuta |
| Aprobación de las 7 plantillas | Días a semanas según backlog de Meta | Plantillas estándar de pedido (se aprueban rápido); formato fijo y categoría Utility |
| Costo por conversación/mensaje | Recurrente del cliente (~S/ 30–70/mes base, 300 pedidos) | Informado en la propuesta comercial §6; mensajes dentro de ventana de servicio 24h son gratis |

---

## 3. Fase P — Propuesta

### 3.1 Alcance

**INCLUYE (F1):**
- Activación de la cuenta Meta Cloud API real (checklist §3.4) y configuración en `companies.settings.whatsapp` (§3.2).
- 7 plantillas aprobadas por Meta (categoría Utility, §3.3) cableadas al mapa `templates` del settings.
- Switch dry-run → real por configuración (D6), con verificación en vivo.
- Botones "Pedir por WhatsApp" (wa.me con mensaje prefabricado) y "Llamar" (tel:) en la landing pública `/menu/{slug}`, pantalla de éxito del checkout y pestaña Campañas (D5).
- Campo BSUID desde el día 1 (columna + payload + persistencia, D3).
- Exposición de datos de contacto en la respuesta pública del menú (para los botones).

**NO INCLUYE (límites F1):**
- Chatbot bidireccional / webhook de mensajes entrantes (D7; se prepara solo la columna BSUID).
- Telefonía / central Asterisk / trunk SIP (F2 — el botón "Llamar" es solo un enlace `tel:`).
- IA por voz / recepcionista IA (F3), multi-sucursal (F4), consultas IA (F5).
- Plantillas Marketing (promociones por WhatsApp) — se evalúa en fases futuras.

### 3.2 Configuración — `companies.settings.whatsapp` (JSONB, patrón D-03)

```json
// companies.settings.whatsapp — F1 activada (ejemplo estructural; valores reales del cliente)
{
  "enabled": true,
  "provider": "meta_cloud",
  "phone_number_id": "123456789012345",   // Meta: Phone Number ID (D1)
  "token": "EAAG...",                     // System User token — SOLO settings, NUNCA código/logs
  "business_phone": "+51999999999",       // número VERIFICADO del negocio (remitente, D4)
  "alert_phone": "+51999999998",          // celular del local (alertas new_order/order_cancelled, D4)
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

- Mismo mecanismo de persistencia que `yape_phone` (PATCH `/api/settings`, patrón D-03 — verificado en Spec 03: copia nueva del dict al persistir para marcar dirty).
- **Token nunca en código, logs, READMEs ni respaldos de código** — solo en `companies.settings` (BD) y en el gestor de secretos del cliente.
- Tenant sin config completa → sigue **dry-run** (CA-B5/B7 ya probados); `enabled=false` → dry-run aunque haya token (switch reversible, D6).

### 3.3 Plantillas Meta (7, categoría Utility, idioma `es`)

| Plantilla (key del settings) | Nombre sugerido en Meta | Variables | Ejemplo de contenido (cuerpo) |
|---|---|---|---|
| `confirmed` | `segoviano_pedido_confirmado` | `{{1}} código, {{2}} total | *¡Gracias por tu pedido, {{1}}!* ✅ Tu pedido *DLV-…* por **S/ {{2}}** fue confirmado. Te avisamos cuando esté en camino. — El Segoviano |
| `preparing` | `segoviano_pedido_preparando` | `{{1}} código | Tu pedido *{{1}}* está **en cocina** 👨🍳. — El Segoviano |
| `ready` | `segoviano_pedido_listo` | `{{1}} código, {{2}} tiempo | Tu pedido *{{1}}* está **listo** y sale en ~{{2}} min 🛵. — El Segoviano |
| `delivered` | `segoviano_pedido_entregado` | `{{1}} código | ¡Tu pedido *{{1}}* fue **entregado**! 🙌 Gracias por pedir con El Segoviano. |
| `cancelled` | `segoviano_pedido_cancelado` | `{{1}} código | Tu pedido *{{1}}* fue **cancelado**. Si fue un error, llámanos al {{2}} — El Segoviano |
| `new_order` | `segoviano_alerta_pedido_nuevo` | `{{1}} código, {{2}} total, {{3}} zona | 🛎️ *Pedido nuevo* *{{1}}* — S/ {{2}} — Zona {{3}}. Revisa el panel. |
| `order_cancelled` | `segoviano_alerta_pedido_cancelado` | `{{1}} código | ⚠️ *Pedido cancelado* *{{1}}*. Verifica en el panel. |

- El **nombre real en Meta** de cada plantilla se guarda en `settings.whatsapp.templates` (mapa key→nombre aprobado).
- Reglas Meta: sin emojis "de marketing" excesivos, sin links en el cuerpo (los links van en botones de plantilla si aplica), sin contenido dinámico fuera de variables `{{n}}`. Formato estable → aprobación rápida (D2).
- El worker ya resuelve `_recipient_and_template(event_type, payload, whatsapp)` → el trabajo es **config**, no código.

### 3.4 Activación de la cuenta Meta — checklist (dependencias externas, trámite en paralelo)

| # | Paso | Quién | Resultado → campo del settings |
|---|---|---|---|
| 1 | Definir el **número del negocio** (línea celular con WhatsApp Business, titular del local) | Cliente | → `business_phone` (D4) |
| 2 | Crear cuenta **Meta Business Manager** + **verificación de negocio** (dominio/documentos) | Cliente (acompañado) | Acceso a Business Manager |
| 3 | Crear **app** en Meta for Developers → producto **WhatsApp Cloud API** | Equipo (con acceso del cliente) | App ID |
| 4 | Crear **System User** con token (permisos mínimos: `whatsapp_business_messaging`, `whatsapp_business_management`) | Cliente/equipo | → `token` |
| 5 | **Registrar el número** en Cloud API → obtener **Phone Number ID** | Equipo | → `phone_number_id` |
| 6 | Crear y enviar a aprobación las **7 plantillas** (Utility, §3.3) | Equipo | Aprobación Meta → nombres → `templates{}` |
| 7 | (F3, NO en F1) declarar **webhook** de recepción + registrar `user_id`/BSUID entrante | — | Preparado por la columna `whatsapp_bsuid` (D3) |
| 8 | Cargar config → **QA en vivo**: dry-run con plantillas reales → `enabled=true` → envío real de prueba | Equipo | CA-F1.1..CA-F1.6 |

> **Nota comercial (ya comunicada al cliente):** la activación en sí **no es desarrollo**, es configuración + QA en vivo + acompañamiento de aprobación — eso es lo que cubre la F1 (S/ 1,500 – 2,500). El trámite de Meta se inicia el día 1 porque es el cuello de botella (aprobación de plantillas: días).

### 3.5 Backend — cambios menores (Spec Anchor)

**Migración `0017_whatsapp_bsuid`** (única migración de F1):

```sql
ALTER TABLE delivery_orders ADD COLUMN whatsapp_bsuid varchar(64);
-- nullable; BSUID/usernames Meta (D3): se persiste cuando el payload lo trae
```

- **Payload de evento** (amplía el de Spec 03 §7.4): `tenant_id, tracking_code, sale_id, customer_phone, bsuid (opcional), status, total, items_resumen, zone, timestamp`.
- **Worker** (`notify_worker.py`): si `payload.bsuid` viene presente y no está en `delivery_orders.whatsapp_bsuid`, lo persiste (update ligero, sin bloquear el envío).
- **`PublicMenuResponse`** (+serializador del menú público): campos **nuevos opcionales** `contact: {whatsapp_link, phone, whatsapp_message} | null` — sin romper contrato (el frontend existente ignora campos nuevos). `whatsapp_link` = `https://wa.me/<business_phone>?text=<mensaje prefabricado>`; `phone` = `tel:<business_phone>`; ambos `null` si `enabled=false` o sin `business_phone` (los botones se ocultan).

### 3.6 Frontend — botones (D5)

**Landing pública `/menu/:slug` (`PublicMenuPage.tsx`):**
- Hero: botón primario **"Pedir por WhatsApp"** → `wa.me/<business_phone>?text=` + mensaje prefabricado (URL-encoded): *"¡Hola El Segoviano! Quiero hacer un pedido: [items del carrito] — Total aprox: S/ X"*; y botón secundario **"Llamar"** → `tel:<business_phone>`.
- Pantalla de éxito del checkout (tras tracking DLV-): botón **"Ver mi pedido por WhatsApp"** → `wa.me/<business_phone>?text=` con código de tracking: *"Hola, mi pedido es *DLV-…*. ¿En qué estado está?"* (mensaje de servicio; respuesta dentro de la ventana de 24h es gratis en Meta).
- Fuente de datos: `contact` de `GET /api/public/{slug}/menu` (§3.5). Si `contact` es `null` → botones ocultos.

**Panel Delivery — pestaña Campañas (`DeliveryPage.tsx`):**
- Junto al link UTM autogenerado de cada campaña, dos botones de preview: **"Abrir en WhatsApp"** (link `wa.me` con mensaje de la campaña + UTM de la campaña) y **"Llamar"** (`tel:`). La URL de campaña resultante combina la landing `/menu/{slug}?utm_*` con el número del negocio.
- `services/publicMenuApi.ts` / `deliveryApi.ts`: tipado de `contact` y de los nuevos campos.

### 3.7 Reglas de negocio (resumen)

| # | Regla |
|---|---|
| R-F1.1 | Envío real **solo** si `settings.whatsapp.enabled=true` AND `token` AND `phone_number_id` AND plantilla aprobada configurada; cualquier otra combinación → **dry-run** (logueado, cero HTTP) |
| R-F1.2 | Remitente SIEMPRE `business_phone` (número verificado del negocio, D4); alertas del local SIEMPRE a `alert_phone`; cliente SIEMPRE a `customer_phone` |
| R-F1.3 | **Regla dura wacli**: el número +51 975 224 103 está prohibido en settings/plantillas/enlaces/logs de F1 (D-B1, D4) |
| R-F1.4 | El pedido **nunca** depende del envío: fallo del proveedor → 3 reintentos (0/60/300s) → DLQ `iaas-tasks-dlq`; fallo de config → ack + log (sin reintento) |
| R-F1.5 | Plantillas: categoría Utility, formato fijo, solo variables `{{n}}`; el nombre real en Meta vive en `settings.whatsapp.templates` (D2) |
| R-F1.6 | BSUID: se persiste en `delivery_orders.whatsapp_bsuid` cuando el payload lo trae; nunca reemplaza a `customer_phone` (D3) |
| R-F1.7 | Botones wa.me/tel: se renderizan solo con `contact` válido en la respuesta pública (config activa); mensajes prefabricados URL-encoded |
| R-F1.8 | Token nunca en código/logs/respuestas de API; solo en `companies.settings` (BD) — patrón D-03 (persistir copia nueva del dict) |
| R-F1.9 | Multi-tenant: tenant sin config sigue en dry-run; la config de El Segoviano no afecta a otros tenants |
| R-F1.10 | Sin webhook de recepción en F1 (D7): no se declara URL de callback en Meta; la columna BSUID queda lista para F3 |

### 3.8 Criterios de aceptación (F1)

| # | Caso | Resultado esperado |
|---|---|---|
| CA-F1.1 | Checkout 201 con config real activa (`enabled=true`, token, plantilla `confirmed` aprobada) | El cliente recibe el **WhatsApp real** "pedido confirmado" (verificado en el teléfono del cliente y en logs del worker sin dry-run) |
| CA-F1.2 | Transición de estado válida (preparing/ready/out_for_delivery/delivered) | El cliente recibe la plantilla correcta por cada transición (CA-B2 en real) |
| CA-F1.3 | Cancelación de pedido | Cliente recibe `cancelled` y el local recibe `order_cancelled` en `alert_phone` |
| CA-F1.4 | Checkout 201 | El local recibe `new_order` en `alert_phone` |
| CA-F1.5 | Switch dry-run → real (solo settings) | Con `enabled=false` o sin token: cero HTTP (dry-run, CA-B7). Con `enabled=true`+token: envío real. Sin rebuild/deploy. Reversible |
| CA-F1.6 | Plantilla faltante o no aprobada | No reintenta (error de config): log claro + ack; pedido intacto. Fallo del proveedor: 3 reintentos → DLQ (CA-B4) |
| CA-F1.7 | Botón "Pedir por WhatsApp" en landing `/menu/{slug}` | Abre `wa.me/<business_phone>?text=<mensaje prefabricado>` con los items del carrito (URL-encoded) |
| CA-F1.8 | Botón "Llamar" en landing | Abre `tel:<business_phone>` |
| CA-F1.9 | Pestaña Campañas del panel | Cada campaña muestra link "Abrir en WhatsApp" (wa.me + mensaje + UTM) y "Llamar" (tel:) |
| CA-F1.10 | Evento con `bsuid` en payload | Se persiste en `delivery_orders.whatsapp_bsuid`; sin BSUID → columna NULL; `customer_phone` intacto (D3) |
| CA-F1.11 | **Regla wacli** | En settings, plantillas, enlaces y logs de F1 no aparece **+51 975 224 103**; remitente = `business_phone` |
| CA-F1.12 | PATCH `/api/settings` con config whatsapp (token, plantillas, enabled) | Persiste en `companies.settings` JSONB (D-03); sobrevive reinicio; token no se expone en respuestas/logs |
| CA-F1.13 | Aislamiento multi-tenant | Tenant sin config → dry-run; la activación de El Segoviano no altera otros tenants |
| CA-F1.14 | Menú público sin config activa | `contact` = `null` → la landing NO muestra botones wa.me/tel: (sin enlaces rotos) |
| CA-F1.15 | Suite de regresión | Tests previos (Spec 03: 300+ passed, Fase B: 22) siguen verdes; +tests de BSUID, contact público y botones |

### 3.9 QA en vivo (verificación real, patrón Spec 03 Fase B)

1. **Dry-run con plantillas reales**: cargar config sin `enabled` → pedido de prueba → confirmar en logs del worker que resuelve plantilla y destinatario correctos (cero HTTP).
2. **Switch real en QA**: `enabled=true` → pedido de prueba al número de un teléfono de prueba del equipo → verificar recepción, formato y variables de `confirmed`/`status_changed`.
3. **Prueba con el cliente**: un pedido real del negocio al celular del dueño (alerta `new_order` + confirmación al cliente).
4. **Rollback probado**: `enabled=false` → vuelve a dry-run sin cambios de código.
5. Documentar en `docs/reports/` con capturas (patrón `informe-verificacion-spec03-delivery-2026-08-11.md`).

---

## 4. Plan de implementación sugerido (1–2 semanas, solo cuando la spec esté aprobada)

- **Día 1 — en paralelo**: iniciar el trámite de la cuenta Meta con el cliente (§3.4 pasos 1–6: verificación de negocio + app + System User + registro de número + envío de las 7 plantillas a aprobación). **Este es el cuello de botella (dependencia externa).**
- **Fase 1 — Backend menor (2–3 días)**: migración `0017_whatsapp_bsuid` + campo `bsuid` en payload + persistencia en worker + `contact` en `PublicMenuResponse`; tests (BSUID, contact null/activo, regresión).
- **Fase 2 — Frontend botones (2–3 días)**: `PublicMenuPage` (hero + éxito de pedido) y `DeliveryPage` pestaña Campañas; tipado en `publicMenuApi.ts`/`deliveryApi.ts`; build `tsc -b` + `vite build`.
- **Fase 3 — QA + activación (depende de Meta)**: dry-run con plantillas reales → QA §3.9 en QA → deploy (`./deploy.sh --env prod`, backup imágenes `.bak-<fecha>` + `pg_dump`) → activar `enabled=true` en prod → verificación en vivo con el cliente → CA-F1.1..CA-F1.15.
- **Entregable visible**: el cliente recibe su **primer WhatsApp real de pedido** y el local sus alertas; botones operativos en el menú público y campañas.

---

## 5. Bitácora Spec Anchor (sync spec ↔ código)

- **2026-08-12 (v0.1)**: spec creada como F1 del Plan Integral de Canales. Fase R verificada en código (2026-08-12): motor WhatsApp desplegado en prod en modo dry-run (Spec 03 §7 — commits `415da23`→`8f3d5a9`, fix `a2287fb` routing_key, worker `iaas-worker-prod` + DLQ `iaas-tasks-dlq`, `WhatsAppSettings` en `CompanySettings.whatsapp` JSONB); gaps confirmados: 0 ocurrencias `wa.me`/`tel:` en `apps/web/src/`, sin columna BSUID, sin `contact` en `PublicMenuResponse`. D1–D7 **propuestas** — pendientes de aprobación de Ron. **Sin código implementado en esta iteración** (Spec Anchor: spec primero).

---

## 6. Referencias

- Spec 03 — Delivery / Dark Kitchen (Fase A + Fase B WhatsApp, §7): `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md`
- Plan Integral de Canales (5 fases, detalle F1): `plan-fases-cliente-llamadas-20260812.md` (workspace del agente)
- Propuesta comercial (2026-08-12, precios y costos mensuales): `propuesta-comercial-cliente-20260812.md` (workspace del agente)
- Informe ejecutivo del cliente §8 (Plan Integral) y §7 (registro requerimiento #2): `docs/reports/informe-ejecutivo-cliente-2026-08-10.md`
- Verificación Fase B en vivo (dry-run): `docs/reports/informe-verificacion-spec03-delivery-2026-08-11.md`
- Manual de usuario delivery: `docs/manuales/manual-delivery-dark-kitchen.md` (se actualizará en F1 con los botones)
- Índice de specs: `docs/specs/README.md` (se actualizará al aprobar)
