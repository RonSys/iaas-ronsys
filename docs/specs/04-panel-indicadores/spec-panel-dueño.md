# SPEC 04 — Panel de Indicadores para el Dueño (Dashboard Ejecutivo)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA (V1 + V2 + PDF, 2026-08-11)** — V1 verificado en producción (S/638, 11 pedidos, 90.9% delivery); V2 desplegada: heatmap hora×día por canal, márgenes por canal con costeo, comparativa semana vs semana, reporte descargable **CSV + PDF**, alertas de desviación vs 7 días. **PDF del reporte (CA13-b, iteración 2) desplegado 2026-08-11**: `format=pdf` reportlab platypus, verificado 200 application/pdf en prod.
- **Proyecto**: IaaS-RonSys — ERP SaaS (cliente: El Segoviano)
- **Alcance**: tenant restaurante + delivery/dark kitchen (fase inicial); multi-tenant por construcción
- **Fecha**: 2026-08-10
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código
- **Requerimiento registrado**: informe ejecutivo cliente §5.3 (#1) — `docs/reports/informe-ejecutivo-cliente-2026-08-10.md`

---

## 0. Decisiones aprobadas (Ron, 2026-08-10)

| Decisión | Acuerdo |
|---|---|
| D1 | Alcance: **V1 (panel inicial)** + **V2 (analítica avanzada)** — ambas aprobadas |
| D2 | Enfoque inicial: **restaurante (salón + takeaway) + delivery/dark kitchen** |
| D3 | V1 usa SOLO data ya registrada (sin cambios en el modelo de datos) — endpoint de resumen + frontend |
| D4 | V2 agrega: heatmaps, márgenes por canal (costeo vía recetas), comparativas semana vs semana, reporte descargable |
| D5 | El panel es de **solo lectura** (vista ejecutiva); el dueño NO edita data desde aquí |
| D6 | Acceso: rol `admin`/`manager` (dueño); los `viewer` (inversionista/auditor) también pueden verlo (solo lectura) |
| D7 | GMV del panel = pedidos delivery **entregados** (consistente con `metrics_overview`); no incluye no-entregados |
| R2 | Costeabilidad V2: margen solo sobre ítems con receta (`average_cost`); ventas sin receta no aportan costo → margen parcial con nota |
| R3 | Reporte V2: **CSV primero**; PDF (reportlab) implementado en iteración 2 (2026-08-10) — mismo endpoint, `format=pdf` |
| R4 | Heatmap V2: render con **CSS grid coloreado** (sin librería extra de heatmaps) |

---

## 1. Contexto y objetivo

El dueño de la franquicia necesita una **sola pantalla** que le responda, sin hojas de cálculo:
"¿cómo va el negocio hoy?". El sistema ya registra toda la data (ventas, canales, platos,
pagos, delivery, campañas), pero no existe una vista ejecutiva que la consolide. Este panel
la entrega en KPIs y gráficos, empezando por restaurante + delivery (los canales que el
cliente opera hoy).

---

## 2. Fase R — Hallazgos de la investigación (data verificada 2026-08-10)

### 2.1 Data real disponible (fuentes verificadas en código)

| Fuente | Campos clave | Uso en el panel |
|---|---|---|
| `sales` (models/sales.py) | `sale_date`, `sale_time`, `total`, `subtotal`, `tax_total`, `discount_total`, `business_type`, `is_voided` | KPIs de ventas, series por hora/día |
| `restaurant_sales` (models/sales.py) | `order_type` (dine_in/takeout/delivery), `table_number`, `guests`, `waiter_name`, `tip_amount` | Canal más rentable, top meseros, ticket por canal |
| `sale_items` (models/sales.py) | `item_name`, `menu_item_id`, `quantity`, `unit_price`, `total`, `item_type` | Top 10 platos (cantidad y soles) |
| `sale_payments` (models/sales.py) | `payment_method` (yape/plin/cash/card/transfer), `amount` | Ingresos por método de pago |
| `delivery_orders` (models/delivery.py) | `status` (CHECK: received/preparing/ready/out_for_delivery/delivered/cancelled), `zone_id`, `courier_id`, `campaign_id`, `received_at`, `delivered_at`, `created_at`, `fee` | Embudo, zonas, SLA, GMV delivery |
| `delivery_zones` (models/delivery.py) | `name`, `districts`, `fee`, `min_order` | Pedidos por zona |
| `marketing_campaigns` (models/delivery.py) | `channel` (meta/google/tiktok), `spend`, `utm_*` | ROAS por campaña |
| `kitchen_orders` (models/restaurant.py) | `status` (CHECK: pending/preparing/ready/delivered/cancelled) | Pedidos en cocina ahora (KPI en vivo) |
| `couriers` (models/delivery.py) | `status`, `vehicle` | Órdenes en ruta (KPI en vivo) |

### 2.2 Métricas YA implementadas (reutilizar, no duplicar)

| Endpoint existente | Qué devuelve | Reuso |
|---|---|---|
| `GET /api/v1/delivery/metrics/overview` | orders, gmv, fee_total, avg_delivery_min, cancelled (filtro fechas) | KPIs delivery + SLA |
| `GET /api/v1/delivery/metrics/campaigns` | por campaña: spend, orders, gmv, aov, roas (filtro fechas/canal) | Gráfico ROAS por campaña |
| `GET /api/superadmin/dashboard` | global empresas/usuarios (superadmin) | NO aplica al dueño de tenant (referencia) |

### 2.3 Bloqueantes / brechas detectadas

- **B1 — No existe endpoint de métricas del dueño por tenant**: hay delivery metrics y superadmin
  dashboard, pero no un consolidado ventas+canales+platos+pagos por tenant con rango de fechas.
- **B2 — No hay página frontend de panel ejecutivo**: la ruta `/` hoy muestra Dashboard genérico.
- **B3 — Márgenes por canal (V2)**: requiere costeo por canal (recetas/costo de venta) — no calculado hoy.
- **B4 — Reporte descargable (V2)**: no existe generación de PDF/CSV del resumen.

---

## 3. Fase P — Propuesta

### 3.1 V1 — Panel inicial (alcance)

**Backend** — nuevo endpoint consolidado por tenant:

```
GET /api/v1/dashboard/owner?date_from=&date_to=
  → 200 OwnerDashboardResponse
```

Response (JSON) agrupado:

```jsonc
{
  "period": { "date_from": "2026-07-12", "date_to": "2026-08-10" },  // rango efectivo aplicado (default: últimos 30 días)
  "kpis": {
    "sales_total": 1250.50,        // ventas del período (sin anuladas)
    "orders_count": 42,            // # pedidos (sales)
    "avg_ticket": 29.77,
    "orders_delivery": 18,         // order_type=delivery
    "orders_dine_in": 20,
    "orders_takeout": 4,
    "delivery_pct": 42.9,
    "kitchen_open": 3,             // en vivo: kitchen_orders status IN ('pending','preparing')
    "delivery_in_route": 2         // en vivo: delivery_orders status='out_for_delivery'
  },
  "sales_by_hour": [ {"hour": 12, "dine_in": 320.0, "delivery": 0}, ... ],   // 0-23
  "sales_by_weekday": [ {"weekday": 1, "total": 850.0}, ... ],               // 1=Mon..7=Sun
  "channels": { "dine_in": 680.0, "takeout": 120.0, "delivery": 450.5 },     // S/ por canal
  "top_platos": [ {"name": "Ceviche Clásico", "qty": 15, "total": 375.0}, ... ],  // top 10
  "payments": { "yape": 500.0, "plin": 200.0, "cash": 400.0, "card": 120.0, "transfer": 30.5 },
  "delivery": {
    "orders_by_zone": [ {"zone": "Zona 1", "orders": 12}, ... ],
    "funnel": { "received": 18, "preparing": 3, "ready": 2, "out_for_delivery": 2, "delivered": 9, "cancelled": 2 },
    "avg_delivery_min": 32.4,
    "gmv": 450.5,
    "fee_total": 90.0
  },
  "campaigns": [ {"name": "Meta Jul", "channel": "meta", "spend": 100, "orders": 8, "gmv": 240, "aov": 30, "roas": 2.4}, ... ]
}
```

**Nota GMV (D7)**: el GMV del panel = pedidos delivery **entregados** (consistente con `metrics_overview` existente, que solo cuenta `status='delivered'`); no incluye no-entregados.

**Nota `period`**: el endpoint devuelve `period.date_from/date_to` con el rango efectivamente aplicado (si no se pasan fechas, default = últimos 30 días incluyendo hoy). El frontend lo usa para reflejar el rango activo en el selector.

**Frontend** — nueva página `/panel` (o `/dashboard/dueño`):
- Fila 1: tarjetas KPI (ventas del día, pedidos, ticket promedio, % delivery, cocina en vivo, en ruta).
- Fila 2: **Ventas por hora** (línea doble salón vs delivery) + **Ventas por día de la semana** (barras).
- Fila 3: **Canales** (dona) + **Top 10 platos** (barras horizontales) + **Pagos** (pie).
- Fila 4: **ROAS por campaña** (barras) + **Pedidos por zona** (barras) + **Embudo delivery** (funnel).
- Selector de rango de fechas (hoy / 7 días / 30 días / personalizado) + refresh.
- Acceso: admin/manager/viewer (solo lectura).

### 3.1-V2 — Contrato V2 (analítica avanzada)

Contrato detallado de los bloques V2 aprobados por Ron (2026-08-10; decisiones D1/D4 de §0 y R2/R3/R4).
Esta sección es el **Spec Anchor de la iteración V2**: backend-dev implementa contra estos JSON;
cualquier cambio de contrato se documenta aquí ANTES de tocar código (Spec Anchor).

#### CA10 — Heatmap hora×día por canal

**Bloque**: `heatmap` (nuevo en el response de `GET /api/v1/dashboard/owner`).

**Definición**: serie de ventas (S/) por **hora (0-23)** × **día de semana (1=Lun..7=Dom)** separada por canal.
Canales: `dine_in` y `delivery`; **takeout se suma a `dine_in`** (misma convención que `sales_by_hour` de V1:
dine_in y takeout suman al salón — verificado en `_sales_by_hour`).

**Contrato JSON**:

```jsonc
{
  "heatmap": {
    "dine_in":  { "rows": [{ "hour": 12, "weekday": 1, "total": 320.5 }, ...] },
    "delivery": { "rows": [...] }
  }
}
```

**Reglas**:
- `hour` ∈ 0..23; `weekday` ∈ 1..7 (1=Lun, 7=Dom).
- `total` = S/ vendidos sin anuladas (`is_voided=False`), consistente con CA2.
- Rows **completos**: hasta 24×7 = 168 rows por canal; celdas sin ventas con `total: 0` (sin agujeros, consistente con CA3).

**DoD**: backend devuelve rows completos (hasta 24×7 por canal, huecos con 0); frontend renderiza
heatmap con **CSS grid coloreado** (decisión R4: sin librería extra; intensidad relativa al máximo del canal).

#### CA11 — Margen por canal con costeo

**Bloque**: `margins`.

**Definición**: costo de venta = Σ (cantidad vendida × `average_cost` del ingrediente) vía recetas —
**reuso de `recipe_explosion`** existente. Margen = (revenue − cost) / revenue × 100.

**Decisión R2 (costeabilidad)**: solo los ítems con receta (`average_cost`) aportan costo; ventas sin
receta no aportan costo. El margen resultante es **parcial** y se declara explícitamente en `costable_note`.

**Contrato JSON**:

```jsonc
{
  "margins": {
    "by_channel": [
      { "channel": "dine_in", "revenue": 2450.0, "cost": 980.0, "margin_pct": 60.0 },
      { "channel": "takeout", "revenue": 620.0, "cost": 310.0, "margin_pct": 50.0 },
      { "channel": "delivery", "revenue": 1780.5, "cost": 890.25, "margin_pct": 50.0 }
    ],
    "costable_note": "Margen calculado solo sobre ítems con receta (average_cost); ventas sin receta no aportan costo (decisión R2)"
  }
}
```

**Reglas**:
- `channel` ∈ {dine_in, takeout, delivery} — aquí takeout SÍ es canal propio (a diferencia del
  heatmap CA10, que lo suma a dine_in); el margen se reporta por los 3 `order_type` de `restaurant_sales`.
- `margin_pct` redondeado a 1 decimal; si `revenue == 0` → `cost: 0.0`, `margin_pct: 0.0`.
- `costable_note` = texto fijo (constante backend) que el frontend muestra como nota/tooltip.

**DoD**: backend computa costeo por canal vía recetas (reuso `recipe_explosion`); frontend muestra
margen por canal con la nota de costeabilidad visible.

#### CA12 — Comparativa semana vs semana

**Bloque**: `comparison`.

**Definición**: período actual (`date_from..date_to`) vs **período previo de igual longitud
inmediatamente anterior** (previous = [date_from − longitud, date_from − 1 día]). Devuelve KPIs de
ambos períodos + deltas.

**Contrato JSON**:

```jsonc
{
  "comparison": {
    "current": { "sales_total": 4850.5, "orders_count": 42, "avg_ticket": 115.5, "delivery_pct": 35.7 },
    "previous": { "sales_total": 4100.0, "orders_count": 38, "avg_ticket": 107.9, "delivery_pct": 31.2 },
    "deltas": { "sales_total_pct": 18.3, "orders_count_pct": 10.5, "avg_ticket_pct": 7.0, "delivery_pct_delta": 4.5 }
  }
}
```

**Reglas**:
- Métricas base = las de `kpis` V1 (sales_total, orders_count, avg_ticket, delivery_pct).
- `*_pct` = ((current − previous) / previous) × 100, redondeado a 1 decimal; si previous = 0 → `null`.
- `delivery_pct_delta` = diferencia **absoluta en puntos porcentuales** (current − previous).
- Ventas sin anuladas (CA2).

**DoD**: backend calcula ambos períodos y deltas; frontend muestra % de cambio con ▲/▼ verde/rojo según signo.

#### CA13 — Reporte descargable CSV

**Endpoint nuevo**: `GET /api/v1/dashboard/owner/export?format=csv&date_from=&date_to=`

**Respuesta**: `Content-Type: text/csv` (attachment) con los bloques del resumen del período:
`kpis`, `sales_by_hour`, `sales_by_weekday`, `channels`, `top_platos`, `payments`, `delivery`,
`campaigns`, `comparison`, `margins`, `alerts`.

**Formato**: CSV plano con secciones — cada bloque abre con `# <nombre_bloque>`, luego fila de
cabecera y filas de datos (UTF-8, separador `,`, decimales `.`).

```csv
# kpis
metric,value
sales_total,4850.50
orders_count,42
# sales_by_hour
hour,weekday,channel,total
12,1,dine_in,320.5
```

**Decisión R3**: **CSV primero**; el **PDF** (reportlab platypus) se implementó en la **iteración 2** (2026-08-10) sobre el mismo contrato de datos — ver §3.1-V2 CA13-b.

**DoD**: endpoint devuelve CSV descargable con TODOS los bloques listados; frontend añade botón
"Exportar CSV" que descarga el archivo para el rango seleccionado.

#### CA13-b — Reporte descargable PDF (iteración 2, implementado 2026-08-10)

**Endpoint**: `GET /api/v1/dashboard/owner/export?format=pdf&date_from=&date_to=` (mismo endpoint del CSV; `format` acepta `csv` | `pdf`; otro valor → 422).

**Respuesta**: `Content-Type: application/pdf` (attachment) generado con **reportlab platypus** (dependencia pura Python — sin cambios de Dockerfile).

**Secciones del PDF** (en español, misma data de `get_owner_dashboard` — una sola llamada):
1. **Encabezado**: "Panel del Dueño — El Segoviano" + período (`date_from` — `date_to`) + fecha de generación
2. **KPIs**: ventas, pedidos, ticket promedio, % delivery
3. **Comparativa semana vs semana**: current/previous/deltas con ▲▼ (solo si hay deltas no nulos)
4. **Márgenes por canal**: revenue/cost/margin_pct por canal + `costable_note`
5. **Top platos** (top 10 por total)
6. **Canales + Pagos**: resumen de canales (salón/para llevar/delivery) y métodos de pago
7. **Ventas por hora**: tabla 0-23 con salón vs delivery (misma forma que el CSV)
8. **Delivery + Campañas**: pedidos por zona, embudo, GMV; ROAS por campaña
9. **Alertas**: rojas/ámbar con ⚠️ (severidad, métrica, mensaje); "Sin alertas en el período" si `[]`

**Filename**: `panel_dueño_YYYYMMDD.pdf` (misma convención ñ/RFC 5987 que el CSV).

**DoD**: endpoint devuelve PDF descargable con las 9 secciones; frontend añade dropdown "Descargar CSV / Descargar PDF" (mismo rango seleccionado).

#### CA14 — Alertas de desviación vs promedio 7 días

**Bloque**: `alerts` (nuevo; V1 no incluye este bloque).

**Definición**: compara el período actual — o el **último día** si `date_from == date_to` — contra
el **promedio de los 7 días previos** (los 7 días calendario inmediatamente anteriores al inicio del
período). Desviación = (actual − promedio_7d) / promedio_7d × 100. Alerta si la desviación supera el umbral.

**Umbrales**: 🔴 `red` si desviación ≤ −20%; 🟡 `yellow` si desviación ≤ −10% (y > −20%).
Desviación negativa = ventas por debajo del promedio.

**Contrato JSON**:

```jsonc
{
  "alerts": [
    { "severity": "red" | "yellow", "metric": "sales_total", "message": "Hoy -20% vs promedio últimos 7 días" }
  ]
}
```

**Reglas**:
- `severity` ∈ {red, yellow}; `metric` = nombre del KPI (sales_total, orders_count, avg_ticket, ...).
- `message` = texto legible generado por backend con el % real redondeado.
- Sin desviación relevante → `alerts: []` (array vacío, nunca null).

**DoD**: backend computa promedio 7 días previos y emite alertas por umbral; frontend renderiza
lista coloreada por severidad (rojo/amarillo).

### 3.2 V2 — Analítica avanzada (alcance)

- **Heatmap hora × día** (salón y delivery por separado): patrón de demanda completo.
- **Márgenes por canal**: costo de venta (recetas/kárdex) vs ingresos por canal → margen real por canal (B3).
- **Comparativas semana vs semana / mes vs mes**: % de cambio en KPIs.
- **Ticket promedio por canal** y por turno (mañana/tarde/noche).
- **Reporte descargable** (PDF/CSV) del resumen del período (B4).
- **Top meseros** y **rate de anulación** (ventas anuladas vs totales).
- **Pedidos delivery por campaña vs sin campaña** (medir efectividad del marketing).
- Alertas simples (ej: "hoy 20% menos que el promedio de los últimos 7 días").

> **Nota V2 contratada**: los bloques **CA10-CA14** (heatmap, márgenes, comparativa, export CSV, alertas) tienen contrato detallado en §3.1-V2 y DoD en §4. Top meseros, rate de anulación, ticket por canal/turno y pedidos delivery campaña vs sin campaña quedaron **sin contrato** hasta la **iteración 3 (2026-08-11)** — ahora contratados en §3.2-V2 (CA-M1..M8, aprobados por Ron).

### 3.2-V2 — Contrato iteración 3: Top meseros, anulaciones, ticket por canal/turno, campaña vs sin campaña (aprobado Ron 2026-08-11)

Contrato detallado de los 4 bloques pendientes de §3.2 (iteración futura). Aditivos al response de
`GET /api/v1/dashboard/owner` (keys nuevas; no rompen el contrato V1/V2 — Spec Anchor).
Esta sección es el Spec Anchor de la iteración 3: backend-dev implementa contra estos JSON.

#### CA-M1 — Top meseros (`top_waiters`)

**Definición**: ventas por usuario del POS (mesero/cajero) en el rango, sin anuladas.
Fuente: `sales.user_id` → `users.full_name` (verificado en prod: user_id poblado 41/41).

```jsonc
{
  "top_waiters": {
    "rows": [
      { "user_id": 3, "name": "Lock Test", "sales_count": 24, "total": 1380.00, "avg_ticket": 57.50 }
    ],
    "total_sales": 42
  }
}
```

**Reglas**: orden por `total` desc; límite 5 (constante); `avg_ticket` = total/sales_count 2 decimales;
`total_sales` = ventas sin anuladas del rango (contexto). Usuarios sin ventas no aparecen.

#### CA-M2 — Rate de anulación (`cancellation_rate`)

**Definición**: % de ventas anuladas + motivos. Fuente: `sales.is_voided` + `sales.void_reason`.

```jsonc
{
  "cancellation_rate": {
    "voided_count": 1, "total_count": 42, "rate_pct": 2.4,
    "top_reasons": [ { "reason": "Cliente no asistió", "count": 1 } ]
  }
}
```

**Reglas**: `rate_pct` = voided/total×100 (1 decimal; 0 si total=0); `top_reasons` agrupa `void_reason`
top 5 por count desc (si vacío → `[]`).

#### CA-M3 — Ticket promedio por canal y turno (`avg_ticket_by`)

**Definición**: ticket promedio por canal (convención V1: dine_in incluye takeout) y por turno.
Fuente: `sales.business_type` + `sales.sale_time` (hora).

```jsonc
{
  "avg_ticket_by": {
    "channel": [ { "channel": "dine_in", "ticket": 46.20 }, { "channel": "delivery", "ticket": 52.10 } ],
    "shift": [
      { "shift": "morning", "ticket": 38.00, "orders": 10 },
      { "shift": "afternoon", "ticket": 48.50, "orders": 18 },
      { "shift": "evening", "ticket": 61.30, "orders": 14 }
    ]
  }
}
```

**Reglas**: turnos **morning** 06:00–11:59 · **afternoon** 12:00–17:59 · **evening** 18:00–23:59
(decisión D-M1; fronteras constantes ajustables sin cambiar contrato); huecos sin ventas con
`ticket: 0, orders: 0` (consistente con CA3). Sin anuladas.

#### CA-M4 — Delivery: campaña vs sin campaña (`delivery_campaign_effect`)

**Definición**: efectividad del marketing en delivery — doble sub-vista. Fuente:
`delivery_orders.campaign_id` (→ `marketing_campaigns.name`) y `delivery_orders.utm->>'source'`.
Solo pedidos **no cancelados** (GMV real). Hallazgo verificado en prod: `campaign_id` vacío 0/24,
pero `utm.source` poblado (meta 13 / e2e 11) → `by_channel` es la vista principal real hoy.

```jsonc
{
  "delivery_campaign_effect": {
    "by_campaign": [
      { "campaign_id": null, "campaign_name": "Sin campaña", "orders": 24, "gmv": 960.00, "aov": 40.00 }
    ],
    "by_channel": [
      { "source": "meta", "orders": 13, "gmv": 520.00, "aov": 40.00 },
      { "source": "directo", "orders": 11, "gmv": 440.00, "aov": 40.00 }
    ]
  }
}
```

**Reglas**: `by_campaign` agrupa campaign_id (null → name "Sin campaña"); `by_channel` agrupa
`utm->>'source'` (null/vacío → "directo"); `aov` = gmv/orders 2 decimales; orden por gmv desc.

### 3.3 Fuera de alcance

- Edición de data desde el panel (es solo lectura, D5).
- App móvil del panel (fase futura independiente).
- Facturación/impuestos (módulo futuro).
- Panel multi-empresa global (eso es superadmin, ya existe).

---

## 4. Criterios de aceptación

### V1
- CA1: `GET /api/v1/dashboard/owner` devuelve todos los bloques del contrato §3.1 con fechas válidas. 
- CA2: KPIs excluyen ventas anuladas (`is_voided=True`). 
- CA3: serie por hora cubre 0-23 (sin agujeros). 
- CA4: top platos ordenado por cantidad (top 10) con total en soles. 
- CA5: canal delivery usa `restaurant_sales.order_type='delivery'` y cruza con `delivery_orders`. 
- CA6: embudo delivery = conteo por `delivery_orders.status` del período. 
- CA7: ROAS = gmv/spend por campaña (consistente con endpoint existente). 
- CA8: frontend `/panel` renderiza KPIs + 7 gráficos + selector de fechas; accesible con admin/manager/viewer. 
- CA9: tests: unit (cálculos) + e2e básico del panel. 

### V2 (contrato detallado: §3.1-V2)
- **CA10 — Heatmap hora×día por canal**: bloque `heatmap` con serie de ventas (S/) por hora (0-23) × día de semana (1=Lun..7=Dom) separada por canal (dine_in/delivery; takeout suma a dine_in como en V1).
  Contrato: `{ "heatmap": { "dine_in": { "rows": [{ "hour": 12, "weekday": 1, "total": 320.5 }, ...] }, "delivery": { "rows": [...] } } }`
  DoD: backend devuelve rows completos (hasta 24×7 por canal, huecos con `total: 0`); frontend renderiza heatmap con CSS grid coloreado (R4: sin lib extra).
- **CA11 — Margen por canal con costeo**: bloque `margins`; costo de venta = Σ (cantidad × `average_cost`) vía recetas (reuso `recipe_explosion`); margen = (revenue − cost) / revenue × 100.
  Contrato: `{ "margins": { "by_channel": [ { "channel": "dine_in", "revenue": 2450.0, "cost": 980.0, "margin_pct": 60.0 }, { "channel": "takeout", "revenue": 620.0, "cost": 310.0, "margin_pct": 50.0 }, { "channel": "delivery", "revenue": 1780.5, "cost": 890.25, "margin_pct": 50.0 } ], "costable_note": "Margen calculado solo sobre ítems con receta (average_cost); ventas sin receta no aportan costo (decisión R2)" } }`
  DoD: solo ítems costeables aportan costo (R2: margen parcial con nota); `margin_pct` a 1 decimal; revenue=0 → `margin_pct: 0.0`.
- **CA12 — Comparativa semana vs semana**: bloque `comparison`; período actual vs previo de igual longitud inmediatamente anterior, con % de cambio.
  Contrato: `{ "comparison": { "current": { "sales_total": 4850.5, "orders_count": 42, "avg_ticket": 115.5, "delivery_pct": 35.7 }, "previous": { "sales_total": 4100.0, "orders_count": 38, "avg_ticket": 107.9, "delivery_pct": 31.2 }, "deltas": { "sales_total_pct": 18.3, "orders_count_pct": 10.5, "avg_ticket_pct": 7.0, "delivery_pct_delta": 4.5 } } }`
  DoD: deltas `*_pct` a 1 decimal; previous=0 → `null`; `delivery_pct_delta` en puntos porcentuales; ventas sin anuladas.
- **CA13 — Reporte descargable CSV + PDF**: `GET /api/v1/dashboard/owner/export?format=csv|pdf&date_from=&date_to=` → `text/csv` (12 secciones `# bloque`) o `application/pdf` (9 secciones platypus, CA13-b). Frontend: dropdown "Descargar CSV / Descargar PDF".
  Formato: CSV plano con secciones `# <bloque>` + cabecera + filas (UTF-8, `,`, decimales `.`).
  DoD: archivo descargable con TODOS los bloques listados; botón "Exportar CSV" en frontend; PDF documentado como iteración 2 (reportlab/weasyprint).
- **CA14 — Alertas de desviación vs promedio 7 días**: bloque `alerts`; compara período actual (o último día si `date_from == date_to`) vs promedio de los 7 días previos.
  Contrato: `{ "alerts": [ { "severity": "red" | "yellow", "metric": "sales_total", "message": "Hoy -20% vs promedio últimos 7 días" } ] }`
  DoD: umbrales red ≤ −20%, yellow ≤ −10% (y > −20%); sin desviación → `alerts: []` (nunca null); frontend colorea por severidad.

### Iteración 3 (aprobada Ron 2026-08-11 — contrato en §3.2-V2)

- **CA-M1 — Top meseros**: bloque `top_waiters`; ventas por `sales.user_id` (join `users.full_name`), sin anuladas, en rango. DoD: rows ordenadas por total desc (límite 5), `avg_ticket` 2 decimales, `total_sales` = contexto del rango.
- **CA-M2 — Rate de anulación**: bloque `cancellation_rate`; `rate_pct` = voided/total×100 (1 decimal; 0 si total=0); `top_reasons` top 5 por void_reason ([] si vacío).
- **CA-M3 — Ticket por canal/turno**: bloque `avg_ticket_by`; `channel` (convención V1: dine_in incluye takeout) + `shift` (morning 06-11:59, afternoon 12-17:59, evening 18-23:59 — D-M1); huecos con `ticket: 0, orders: 0`. Sin anuladas.
- **CA-M4 — Delivery campaña vs sin**: bloque `delivery_campaign_effect`; doble sub-vista `by_campaign` (campaign_id → name, null = "Sin campaña") + `by_channel` (utm.source, null/vacío = "directo"); solo no-cancelados; `aov` = gmv/orders; orden por gmv desc.
- **CA-M5 — CSV ampliado**: el export CSV incluye las 4 secciones nuevas (`# top_waiters`, `# cancellation_rate`, `# avg_ticket_by`, `# delivery_campaign_effect`) sin romper las 12 existentes.
- **CA-M6 — PDF ampliado**: el PDF incluye las secciones nuevas (Top Meseros, Anulaciones, Ticket por turno; campaña vs sin amplía la sección Delivery) — sin romper las 9 existentes.
- **CA-M7 — Regresión**: suite backend completa verde (48 panel + 22 whatsapp + resto; 2 fallos pre-existentes test_caso6_recipes ajenos), E2E panel 13/13.
- **CA-M8 — Verificación en vivo**: `GET /api/v1/dashboard/owner` devuelve los 4 bloques con data real de prod (top_waiters con usuarios reales; rate real; turnos; campaña vs directo).

---

## 5. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código (propuesta) | Spec |
|---|---|---|
| Endpoint dueño | `app/routers/dashboard.py` (nuevo, prefix `/api/v1/dashboard`) | §3.1 |
| Service de métricas | `app/services/owner_dashboard_service.py` (nuevo) | §3.1 |
| Pool solo-lectura | `dashboard_ro` (panel es solo lectura — no usa pool de escritura) | §3.1 |
| Reuso delivery metrics | `app/services/delivery_service.py` (`metrics_overview`, `metrics_campaigns`) | §2.2 |
| Página panel | `apps/web/src/pages/DashboardOwner.tsx` + ruta `/panel` en `App.tsx` | §3.1 |
| API client + tipos | `apps/web/src/services/dashboardApi.ts`, `apps/web/src/types/dashboard.ts` | §3.1 |
| Charts | `apps/web/src/components/dashboard/*` (recharts) | §3.1 |
| Tests | `apps/backend/tests/test_owner_dashboard.py`, `apps/web/e2e/panel.spec.ts` | §4 |
| Registro requerimiento | `docs/reports/informe-ejecutivo-cliente-2026-08-10.md` §5.3 (#1) | — |
| V2: bloques heatmap/margins/comparison/alerts | `app/services/owner_dashboard_service.py` (ampliar con CA10-12, CA14) | §3.1-V2 |
| V2: export CSV | `app/routers/dashboard.py` (ampliar con `GET /export`) | §3.1-V2 (CA13) |
| V2: frontend | `apps/web/src/pages/DashboardOwner.tsx` (ampliar: heatmap CSS grid, márgenes, comparativa, alertas, botón export) | §3.1-V2 |
| Iteración 3: bloques top_waiters/cancellation_rate/avg_ticket_by/delivery_campaign_effect | `app/services/owner_dashboard_service.py` (ampliar con CA-M1..M4) | §3.2-V2 (CA-M1..M4) |
| Iteración 3: CSV/PDF ampliados | `app/routers/dashboard.py` (export) + `render_owner_pdf` | §3.2-V2 (CA-M5..M6) |
| Iteración 3: frontend | `apps/web/src/pages/DashboardOwner.tsx` (secciones nuevas) | §3.2-V2 |
| V2: tests | `apps/backend/tests/test_owner_dashboard.py`, `apps/web/e2e/panel.spec.ts` (ampliar CA10-14) | §4 |

> ⚠️ Si cambias los gráficos, KPIs o el contrato del endpoint, **actualiza esta spec** (Spec Anchor) y el registro en el informe ejecutivo.
