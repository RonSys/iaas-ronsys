# 🗄️ Informe de Tablas y Esquemas Afectados — F1 WhatsApp en Vivo (lógica para el cliente)

- **Proyecto:** IaaS-RonSys — Cliente "El Segoviano"
- **Spec:** `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md` (F1)
- **Fecha:** 2026-08-13
- **Motivo:** el cliente quiere **entender la lógica** de qué tablas y esquemas se tocan con la Fase 1. Este documento lo explica en lenguaje claro + detalle técnico.

---

## 1. Resumen ejecutivo (para el cliente)

La F1 **no crea un sistema nuevo**: solo toca **4 piezas** del sistema que ya tiene:

1. **`delivery_orders`** (pedidos de delivery) → se le agrega **1 columna nueva** (el identificador que usa WhatsApp para reconocer al cliente).
2. **`companies`** (la ficha de su negocio) → dentro de su configuración (JSON) se guarda un **bloque nuevo "whatsapp"** con el número del negocio, el token y los nombres de las plantillas.
3. **`menu` público** (lo que ve el cliente en la web) → ahora **entrega también los datos de contacto** (link de WhatsApp y teléfono) para mostrar los botones.
4. **Cola de mensajes RabbitMQ** (el "cartero" interno) → los eventos de pedido ahora **llevan un dato extra** (el BSUID).

**Nada de lo existente se rompe o se borra**: son cambios **aditivos** (agregar, no reemplazar).

---

## 2. Tablas afectadas (detalle técnico)

### 2.1 `delivery_orders` — pedidos de delivery (+1 columna)

**Antes (Spec 03, ya en producción):**

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | serial PK | Identificador del pedido |
| `tenant_id` | int FK | A qué empresa pertenece (multi-tenant) |
| `sale_id` | int FK unique | La venta del motor contable (1 pedido = 1 venta) |
| `zone_id` | int FK | Zona de reparto (fee, mínimo, ETA) |
| `courier_id` | int FK | Repartidor asignado |
| `campaign_id` | int FK | Campaña publicitaria (atribución UTM) |
| `tracking_code` | varchar unique | Código público del pedido (DLV-XXXX) |
| `customer_name` / `customer_phone` / `customer_address` | varchar | Datos del cliente |
| `fee` | numeric | Costo de delivery |
| `status` | varchar | received → preparing → ready → out_for_delivery → delivered / cancelled |
| `received_at` … `cancelled_at` | timestamptz | Marca de tiempo de cada etapa |
| `utm` | jsonb | Datos de la campaña (source, medium, campaign) |
| `created_at` / `updated_at` | timestamptz | Auditoría |

**Nuevo en F1 (migración `0017_whatsapp_bsuid`):**

| Columna | Tipo | Para qué | Regla |
|---|---|---|---|
| `whatsapp_bsuid` | varchar(64) | **Identificador de usuario de WhatsApp (BSUID)** que Meta envía en lugar del número cuando el cliente usa username (cambio de Meta 2026) | **NULL por ahora** — se llena cuando llegue el webhook (Fase 3). Mientras tanto, la notificación se envía al `customer_phone` normal |

**SQL real de la migración:**
```sql
ALTER TABLE delivery_orders ADD COLUMN whatsapp_bsuid varchar(64);
-- nullable; BSUID/usernames Meta (D3): se persiste cuando el payload lo trae
```

**Por qué es importante:** Meta está migrando a "usernames" (los clientes ya no siempre comparten su número). Esta columna **prepara el sistema desde el día 1** para seguir notificando aunque el cliente no comparta su número — sin rehacer nada después (cambio de Meta del 31-mar-2026).

---

### 2.2 `companies` — la ficha del negocio (campo `settings` JSONB)

**Sin cambios de esquema** — la tabla `companies` ya tiene el campo `settings` como **JSONB** (documento flexible). F1 solo **agrega un bloque nuevo** dentro de ese JSON:

```jsonc
// companies.settings.whatsapp  ← BLOQUE NUEVO (dentro del JSON existente)
{
  "enabled": false,                // true = envía real · false = simulación (dry-run)
  "provider": "meta_cloud",        // proveedor (agnóstico: se puede cambiar)
  "phone_number_id": "1234567890", // identificador del número en Meta
  "token": "EAAG...",              // llave de acceso (NUNCA en código)
  "business_phone": "+51999999999",// número del negocio (remitente)
  "alert_phone": "+51999999998",   // celular del local (alertas)
  "templates": {                   // nombres de las 7 plantillas aprobadas en Meta
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

**Ventaja del diseño (JSONB):** no hace falta crear tablas nuevas ni migraciones para configurar WhatsApp — es un documento flexible que ya soporta multi-empresa (cada local de la franquicia puede tener SU config de WhatsApp sin mezclarse).

**Cómo se modifica:** `PATCH /api/settings` (con sesión de staff) — **solo configuración, sin deploy** (ver manual del servicio).

---

### 2.3 API pública del menú — respuesta `contact` (nuevo bloque opcional)

**Sin cambios de tabla.** El endpoint `GET /api/public/{slug}/menu` (menú público) ahora **incluye un bloque nuevo** cuando la config de WhatsApp está activa:

```jsonc
// Respuesta del menú público (adición)
{
  "sections": [...],          // menú (existente)
  "promotions": [...],        // promociones (existente)
  "delivery_window": {...},   // horario (existente)
  "contact": {                // ← NUEVO (F1)
    "whatsapp_link": "https://wa.me/51999999999?text=¡Hola%20El%20Segoviano!...",
    "phone": "tel:+51999999999",
    "whatsapp_message": "¡Hola El Segoviano! Quiero hacer un pedido..."
  }
  // "contact" es null si no hay config activa → los botones se ocultan
}
```

**Lógica:** el frontend (landing) lee este bloque y muestra los botones "Pedir por WhatsApp" y "Llamar". Si es `null`, no muestra botones. **Los sistemas que ya existen ignoran los campos nuevos** (retrocompatible — no se rompe nada).

---

### 2.4 Cola de mensajes RabbitMQ — payload de eventos (+1 campo opcional)

**Sin cambios de infraestructura.** La cola `iaas-tasks` ya existe y funciona. El **payload** de los eventos de pedido ahora incluye un campo opcional:

```jsonc
// Evento publicado en RabbitMQ (delivery.confirmed / status_changed / ...)
{
  "tenant_id": 1,
  "tracking_code": "DLV-9fc6268b79",
  "sale_id": 42,
  "customer_phone": "+51999999999",
  "bsuid": "PE.13491208655302741918",   // ← NUEVO (opcional, F1)
  "status": "received",
  "total": "58.50",
  "items_resumen": "2x Ceviche Clásico",
  "zone": "Montenegro / Motupe / Canto Grande",
  "timestamp": "..."
}
```

**Lógica:** el worker de notificaciones (`notify_worker`) lee el payload → si trae `bsuid`, lo guarda en `delivery_orders.whatsapp_bsuid` (la columna nueva de §2.1). El envío sigue usando `customer_phone` (el BSUID se usará en Fase 3 cuando llegue el webhook).

---

## 3. Diagrama de flujo (cómo se conecta todo)

```
CLIENTE PIDE (web)                    SISTEMA
───────────────                       ───────
Cliente llena carrito     →    POST /api/public/{slug}/orders
  y paga (Yape/Plin)             │
                                 ▼
                          delivery_orders  (se crea el pedido DLV-XXXX)
                          sales + kárdex + contabilidad (automático)
                          kitchen_orders (llega a cocina)
                                 │
                                 ▼
                    RabbitMQ: delivery.confirmed + new_order
                                 │
                                 ▼
                    notify_worker (lee companies.settings.whatsapp)
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        enabled=false (dry-run)     enabled=true (real)
        → solo logs                 → POST a Meta Cloud API
                    │                         │
                    ▼                         ▼
        (pedido cambia de estado:     WhatsApp Business API
        preparing → ready →           entrega el mensaje al
        out_for_delivery →            celular del cliente 📱
        delivered → eventos →
        notificación en cada paso)
```

---

## 4. ¿Qué NO se toca? (para tranquilidad del cliente)

| Módulo | Estado |
|---|---|
| Ventas / POS / caja | **Intacto** |
| Restaurante (mesas, cocina, takeaway, promociones) | **Intacto** |
| Inventario / kárdex / seriales | **Intacto** |
| Contabilidad / asientos / estados financieros | **Intacto** |
| Recetas / costeo | **Intacto** |
| Panel del dueño (V1+V2+PDF) | **Intacto** |
| Panel global multi-empresa | **Intacto** |
| Delivery online (zonas, repartidores, campañas, tracking) | **Intacto** (solo +1 columna opcional) |
| Motor WhatsApp existente (Spec 03 Fase B) | **Intacto** (se reutiliza; F1 solo activa y agrega BSUID) |

**Regla de oro:** todos los cambios de F1 son **aditivos y retrocompatibles** — nada existente se reemplaza ni se borra. Si se desactiva WhatsApp (`enabled: false`), el sistema queda exactamente como estaba antes de la F1.

---

## 5. Resumen de cambios por capa (tabla técnica)

| Capa | Cambio | Migración | Riesgo |
|---|---|---|---|
| **BD — `delivery_orders`** | + columna `whatsapp_bsuid varchar(64)` NULL | `0017_whatsapp_bsuid` (verificada upgrade/downgrade) | Nulo (columna opcional) |
| **BD — `companies.settings`** | + bloque `whatsapp` en JSONB | Ninguna (JSONB flexible) | Nulo |
| **API pública menú** | + bloque `contact` opcional en respuesta | Ninguna | Nulo (campos nuevos ignorados) |
| **RabbitMQ** | + campo `bsuid` opcional en payload | Ninguna | Nulo (campo opcional) |
| **Worker notificaciones** | Persiste BSUID si viene en payload | Ninguna | Nulo (fire-and-forget) |
| **Frontend landing/campañas** | Botones wa.me / tel (se ocultan si `contact=null`) | Ninguna | Nulo |

---

*Informe técnico-ejecutivo — Equipo IaaS-RonSys · 2026-08-13 · Para entendimiento del cliente sobre la lógica de datos de F1.*
