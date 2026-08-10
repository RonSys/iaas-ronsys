# SPEC 04 — Panel de Indicadores para el Dueño (Dashboard Ejecutivo)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA (V1, 2026-08-10)** — endpoint `/api/v1/dashboard/owner` + página `/panel` en producción (verificado: S/638, 11 pedidos, 90.9% delivery). V2 pendiente.
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

**Frontend** — nueva página `/panel` (o `/dashboard/dueño`):
- Fila 1: tarjetas KPI (ventas del día, pedidos, ticket promedio, % delivery, cocina en vivo, en ruta).
- Fila 2: **Ventas por hora** (línea doble salón vs delivery) + **Ventas por día de la semana** (barras).
- Fila 3: **Canales** (dona) + **Top 10 platos** (barras horizontales) + **Pagos** (pie).
- Fila 4: **ROAS por campaña** (barras) + **Pedidos por zona** (barras) + **Embudo delivery** (funnel).
- Selector de rango de fechas (hoy / 7 días / 30 días / personalizado) + refresh.
- Acceso: admin/manager/viewer (solo lectura).

### 3.2 V2 — Analítica avanzada (alcance)

- **Heatmap hora × día** (salón y delivery por separado): patrón de demanda completo.
- **Márgenes por canal**: costo de venta (recetas/kárdex) vs ingresos por canal → margen real por canal (B3).
- **Comparativas semana vs semana / mes vs mes**: % de cambio en KPIs.
- **Ticket promedio por canal** y por turno (mañana/tarde/noche).
- **Reporte descargable** (PDF/CSV) del resumen del período (B4).
- **Top meseros** y **rate de anulación** (ventas anuladas vs totales).
- **Pedidos delivery por campaña vs sin campaña** (medir efectividad del marketing).
- Alertas simples (ej: "hoy 20% menos que el promedio de los últimos 7 días").

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

### V2
- CA10: heatmap hora×día por canal. 
- CA11: margen por canal con costeo (recetas/kárdex). 
- CA12: comparativa semana vs semana con % de cambio. 
- CA13: reporte descargable (PDF/CSV) con los bloques del resumen. 
- CA14: alertas de desviación vs promedio 7 días. 

---

## 5. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código (propuesta) | Spec |
|---|---|---|
| Endpoint dueño | `app/routers/dashboard.py` (nuevo, prefix `/api/v1/dashboard`) | §3.1 |
| Service de métricas | `app/services/owner_dashboard_service.py` (nuevo) | §3.1 |
| Pool solo-lectura | `dashboard_ro` (panel es solo lectura — no usa pool de escritura) | §3.1 |
| Reuso delivery metrics | `app/services/delivery_service.py` (`metrics_overview`, `metrics_campaigns`) | §2.2 |
| Página panel | `apps/web/src/pages/DashboardOwner.tsx` + ruta `/panel` en `App.tsx` | §3.1 |
| Charts | `apps/web/src/components/dashboard/*` (recharts) | §3.1 |
| Tests | `apps/backend/tests/test_owner_dashboard.py`, `apps/web/e2e/panel.spec.ts` | §4 |
| Registro requerimiento | `docs/reports/informe-ejecutivo-cliente-2026-08-10.md` §5.3 (#1) | — |

> ⚠️ Si cambias los gráficos, KPIs o el contrato del endpoint, **actualiza esta spec** (Spec Anchor) y el registro en el informe ejecutivo.
