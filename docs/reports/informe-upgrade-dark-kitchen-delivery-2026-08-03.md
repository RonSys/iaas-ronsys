# 📦 Informe: Upgrade Dark Kitchen / Delivery Nocturno — IaaS-RonSys (El Segoviano)

- **Fecha:** 2026-08-03
- **Proyecto:** IaaS-RonSys — ERP SaaS con Agentes de IA (El Segoviano)
- **Producción:** https://www.ronsyserp.com (HTTP 200 ✓)
- **Elaborado por:** Asistente (chatbot) + Jarvis (orquestador) — colaboración conjunta
- **Motivo:** El cliente ya inició operaciones en la cevichería y solicita un upgrade para aprovechar la **capacidad instalada del local (ocioso de noche)** montando un servicio de **Dark Kitchen / Delivery nocturno**, dirigido a un público objetivo **con capacidad de compra**, con **marketing digital dirigido (campañas digitales)**.

---

## 1. Resumen Ejecutivo

La Fase 0 dejó el terreno **80% listo** para delivery: el motor de ventas del ERP ya soporta `order_type="delivery"`, el método de pago **Yape ya existe**, la sesión POS no bloquea el checkout, la cocina ya recibe comandas por WebSocket, y el plan integral v3 ya tenía prevista la deuda técnica **D-06 (Delivery)** como parte de la Fase 2.

El trabajo real del upgrade es: **migración de BD (5 tablas nuevas), canal público con slug por tenant, máquina de estados de entrega + integración a cocina, notificaciones WhatsApp y panel de métricas de campañas**.

> ⏱️ **Estimación: MVP en 8–10 días-dev · Producto completo en 20–28 días-dev** (2–3 sprints).
> 💰 **Contexto del mercado (reporte "Top 10 negocios Perú 2026"):** dark kitchens = inversión desde ~S/35,000, margen 12–18%, probabilidad de éxito 50–55%, escalable a local físico.

---

## 2. Estado Actual del Proyecto (lo avanzado — verificado)

| Área | Estado | Evidencia |
|---|---|---|
| **Producción** | 🟢 Desplegado y operativo | https://www.ronsyserp.com responde HTTP 200 (nginx → frontend React + backend API) |
| **QA reciente** | 🟢 **10/10 PASS** (2026-07-31) | Suite reutilizable `scripts/qa/test_suite.py`: auth, recetas, explosión de kárdex, stock insuficiente (409), costeo/COGS, multi-tenant, POS search, UI bundle, salud general |
| **Infraestructura** | 🟢 **40/40 containers Up** | PostgreSQL 16 + pgvector, Redis, RabbitMQ (desplegado, sin uso), Prometheus/Grafana, alembic en `0015` |
| **Restaurante (Fase 0)** | 🟢 Operativo | Mesas (`TablesMap`), menú con modificadores (`MenuPage`), cocina Kanban con WebSocket realtime (`KitchenKanban`), **Take Away** (`TakeawayPage`), **Promociones** (`PromotionsPage`), secciones |
| **Ventas + Contabilidad** | 🟢 Operativo | POS + Kárdex (promedio ponderado), venta → explosión de recetas → asiento contable automático; ventas por mayor/detal (ferretería demo) |
| **Recetas + Costos** | 🟢 Operativo | Último commit: explosión de recetas con costos variables (2026-07-31) |
| **Multi-tenant** | 🟢 Operativo | Aislamiento por `X-Tenant-ID` (fallback JWT) en todos los módulos |
| **Simulador financiero** | 🟢 Operativo | `Simulator` / `InvestmentPage`, balance, flujo de caja, VAN/TIR, ratios |
| **IA / Agentes** | 🟡 Parcial | Sistema de skills IA (`core/agents`) y orquestación presente; uso por módulo |

**Últimos commits:** `93f6693 feat(recipes): recetas con explosión de kárdex y costos variables` · `4f36b2d ci: GitHub Actions lint backend` · `01f2107 docs: marcha blanca`.

---

## 3. La Oportunidad de Negocio (por qué delivery nocturno)

Contexto del reporte de investigación **"Top 10 negocios con mayor probabilidad de éxito en Perú 2026"**:

- **Dark Kitchens Delivery:** negocio de bajo riesgo, inversión inicial ~S/35,000, margen de utilidad 12–18%, probabilidad de éxito 50–55%, y eventualmente convertible en local físico.
- **Ventaja única del cliente:** la inversión de capital ya está hecha (local + cocina + ERP). El costo marginal de operar de noche es **solo insumos + personal + delivery** → el 12–18% de margen típico de dark kitchen se protege mejor porque **no hay inversión adicional de infraestructura**.
- **Capacidad instalada ociosa:** el local no se usa de noche → la cocina, el ERP y el personal base pueden absorber pedidos delivery sin costo fijo extra significativo.
- **Público objetivo con capacidad de compra (SJL):** distrito más poblado del Perú, con **capacidad de compra creciente** en zonas como Montenegro, Motupe, Canto Grande, Zárate y Campoy, y **poca oferta de delivery nocturno de calidad** → menos competencia. Ticket promedio objetivo S/45–90 por pedido.

---

## 4. Lo que YA Existe y se Reutiliza (verificado en código por Jarvis)

### Backend — reutilización directa (cero código nuevo)

| Componente | Ubicación | Estado |
|---|---|---|
| **Motor de venta completo** (Sale + SaleItem + SalePayment → kárdex → asiento contable automático) | `services/sales_service.py` (`create_sale`, ~L280) | ✅ **Ya acepta `order_type="delivery"`** vía `restaurant_data` |
| `RestaurantSale.order_type` | `models/sales.py` | ✅ Enum ya incluye `delivery` (default `dine_in`) |
| `delivery_address` en schemas | `schemas/sales.py` | ✅ Ya existe en `restaurant_data` |
| **Métodos de pago** | `models/sales.py` `SalePayment` | ✅ `cash \| card \| yape \| plin \| transfer` — **Yape ya soportado** con campo `reference` |
| **Sesión POS opcional** | `sales_service.py` ~L285 | ✅ `session_id` nullable — **no bloquea checkout sin caja abierta** (migración `2026-05-20`) |
| **Comandas a cocina + Kanban realtime** | `KitchenOrder` + `ws_manager.py` (`broadcast_to_kitchen`) + WS `/api/v1/restaurant/ws/kitchen/{tenant_id}` | ✅ Los pedidos delivery se inyectan a esta misma cola |
| **Motor de promociones** | `Promotion` + `PromotionsService.apply_promotion` | ✅ Reusable para delivery (combo, discount_pct, discount_fixed, bogof) |
| **Multi-tenant** | `core/tenant.py` | ✅ Todos los modelos tenant-scoped |

### Frontend
- `pages/restaurante/`: `KitchenKanban`, `MenuPage`, `PromotionsPage`, `TakeawayPage`, `TablesMap`, `SectionsManagement` — reutilizables (Kanban ya recibe eventos WS; **TakeawayPage es la plantilla del panel delivery**).
- `services/restaurantApi.ts` — patrón de cliente API a seguir.

### Infra
- **Redis** (rate limiting sliding-window), **RabbitMQ desplegado pero sin producer/consumer** → oportunidad: cola para WhatsApp async y procesamiento de pedidos, **Prometheus/Grafana**, alembic hasta `0015`.

> ⚠️ **No copiar como patrón:** `TakeawayOrder` NO crea Sale (queda fuera de kárdex/contabilidad). Para delivery el cobro es al ordenar → **el pedido delivery debe crear un `Sale` directamente** (`order_type="delivery"`) para que la explosión de recetas y el asiento contable se generen solos. Takeaway sirve solo como referencia de UX/estados.

---

## 5. Gaps — Lo que NO Existe y Hay que Construir

1. **Sin resolución pública de tenant:** `get_tenant_id` exige X-Tenant-ID o JWT. La landing pública necesita resolver tenant por **slug/subdominio** (ej. `/menu/el-segoviano`). `Company` no tiene columna `slug` → migración.
2. **Sin disponibilidad horaria en menú:** `MenuItem.active` es booleano simple. No hay "menú nocturno" (ej. 7pm–12am).
3. **Sin zonas de delivery, repartidores, tracking:** no existen modelos.
4. **Sin infraestructura de notificaciones:** cero WhatsApp/SMTP/Twilio en el repo.
5. **Sin campañas/UTMs:** no hay tabla de campañas ni atribución de ventas.
6. **Sin endpoints públicos:** todos los routers exigen `get_current_active_user`.
7. **Branding en memoria (D-03):** `setup.py` guarda `_current_settings` en RAM global, no multi-tenant ni persistente → afecta a la landing (logo/colores por tenant). Conviene resolverlo (0.5 día) o usar `Company.settings` (JSONB).
8. **Pago online real:** Yape manual con referencia + contraentrega para el MVP; integración PSP (Izipay/Culqui/MercadoPago) es trabajo aparte (Fase C).

---

## 6. Arquitectura Propuesta (fiel a la hexagonal del repo)

```
core/delivery/               ← dominio puro (políticas: tarifas, máquina de estados)
adapters/db/models/delivery.py
adapters/alembic/versions/0016_delivery.py
routers/delivery.py          ← staff autenticado (/api/v1/delivery/*)
routers/public.py            ← canal público sin auth (/api/public/{slug}/*)
schemas/delivery.py
services/delivery_service.py ← orquestación (usa SaleService + PromotionsService + KitchenOrder)
```

### Migración `0016_delivery` (tablas nuevas)
- `delivery_zones`: tenant, nombre, radio/zonas (geo JSONB o simple), `fee`, `min_order`, `eta_min`, `active`
- `delivery_orders`: tenant, `sale_id` FK (única), cliente (nombre/teléfono/dirección/lat/lng), `zone_id`, `courier_id` nullable, `status`, `fee`, `eta`, `campaign_id` nullable, `utm` JSONB, `tracking_code` único, timestamps
- `couriers`: tenant, `user_id` FK nullable (rol `courier`), nombre, teléfono, vehículo, `status` (available/on_delivery/offline)
- `marketing_campaigns`: tenant, nombre, canal (meta/google), presupuesto/gasto real, fechas, `utm_source/medium/campaign`, `active`
- `MenuItem`: + `delivery_enabled` bool, `available_from`/`available_to` time (ventana nocturna), `delivery_surcharge` opcional
- `Sale`: + `campaign_id` FK nullable (atribución directa) — alternativa: solo en `delivery_orders`

### Máquina de estados (entrega)
`received → preparing (cocina, = KitchenOrder) → ready → out_for_delivery → delivered | cancelled`

### Endpoints nuevos
- **Públicos** (rate-limited, resolución por slug, sin JWT):
  - `GET /api/public/{slug}/menu`
  - `GET /api/public/{slug}/zones`
  - `POST /api/public/{slug}/orders` (checkout)
  - `GET /api/public/orders/{tracking_code}/status`
- **Staff:** CRUD zonas/repartidores/campañas, `GET/PATCH /api/v1/delivery/orders` (transiciones), `POST /orders/{id}/assign-courier`, `GET /api/v1/delivery/metrics/campaigns` (pedidos, GMV, ticket promedio, **ROAS**)

### Flujo del checkout (MVP)
Landing pública → menú nocturno (filtrado por ventana horaria + `delivery_enabled`) → carrito → datos de entrega + zona (calcula fee/ETA) → promo aplicable → pago **Yape manual (referencia) o contraentrega** → crea `Sale` (order_type=delivery) → explota recetas/kárdex + asiento contable → crea `DeliveryOrder` + `tracking_code` → evento WS a cocina → notificación WhatsApp.

---

## 7. Plan de Implementación por Fases

| Fase | Alcance | Estimación |
|---|---|---|
| **A — MVP Delivery** 🚀 | Migración 0016 (zonas, delivery_orders, couriers, campañas, disponibilidad horaria) + endpoints públicos (menú/zones/checkout/tracking) + panel staff con estados + integración cocina (KitchenOrder+WS) + captura UTM + CRUD campañas + fix D-03 (branding por tenant) | **8–10 dd** |
| **B — Notificaciones + Métricas** | Worker WhatsApp (Meta Cloud API + cola RabbitMQ) + panel de métricas de campañas (pedidos, GMV, ticket promedio, ROAS por campaña y canal) + gestión de menú nocturno en UI + asignación de repartidores con vista de rutas | **6–8 dd** |
| **C — Opcional / Fase 2 plan v3** | PSP pago online real (Izipay/Culqui payment link), integración Rappi/PedidosYa (APIs partner, requieren contrato comercial), página pública de seguimiento de pedido, autocompletado de direcciones (Google Places) | **6–10 dd** |
| **QA + deploy** | ~15% adicional; pipeline ya existe (docker-compose prod/qa, deploy.sh) | **3–4 dd** |

> **Total: ~20–28 dd** (2–3 sprints de 2 semanas). **El MVP (Fase A) es el punto de corte recomendado para el primer despliegue** y ya genera valor de negocio.

---

## 8. Plan de Marketing Digital Dirigido (campañas digitales)

El cliente aplicará **mkt digital dirigido** sobre el canal público del MVP. Requisito técnico habilitante: **URLs estables por campaña** (ej. `ronsyserp.com/menu/el-segoviano?utm_source=meta&utm_campaign=lanza_segoviano`) con captura de UTM en el primer clic y persistencia en `delivery_orders.utm`. El ROAS requiere registrar el **gasto real por campaña** (campo `spend` en `marketing_campaigns`).

### 8.1 Público objetivo (capacidad de compra — SJL)
- **Geográfico:** San Juan de Lurigancho — arranque con **Zona 1: Montenegro, Motupe, Canto Grande** (radio cercano al local, 11°56'25.6"S 76°58'32.0"W, límite Montenegro–Motupe). Expansión posterior a Zárate, Campoy, Los Jardines vía CRUD de zonas.
- **Demográfico:** 22–55 años, profesionales, jóvenes y familias de SJL con capacidad de compra; ticket promedio objetivo S/45–90.
- **Conductual:** consumidores nocturnos de delivery (ceviches, arroces, jaleas, parrillas de mariscos), pedidos recurrentes entre 7pm–12am, usuarios de Yape/contraentrega.
- **Lookalikes:** audiencias similares a clientes actuales del local + data de pedidos (cuando haya volumen).
- **Ventaja competitiva:** poca oferta de delivery nocturno de calidad en la zona → el mensaje debe destacar "cocina marina nocturna cerca de ti".

### 8.2 Canales y estructura de campañas
| Canal | Objetivo | Formato |
|---|---|---|
| **Meta (Instagram + Facebook Ads)** | Pedidos de lanzamiento y consideración | Carousel del menú nocturno, Reels de cocina en vivo, ofertas con cupón, remarketing a visitantes del menú |
| **Google (Search + Performance Max)** | Captura de demanda activa ("cevichería delivery SJL", "cevichería a domicilio Canto Grande", "comida marina a domicilio Montenegro") | Search Ads con extensión de llamada; PMax para conversiones |
| **WhatsApp Business** | Canal de pedidos directo + soporte | Catálogo, mensajes de seguimiento de pedido (Fase B), promos segmentadas |
| **Contenido orgánico (refuerzo)** | Confianza y comunidad | UGC (clientes filmando el unboxing), historias de repartidores, contenido de "cocina de noche" |

### 8.3 Calendario sugerido (primeras 6 semanas post-MVP)
1. **Semana 1–2 — Pre-lanzamiento (teaser):** contenido de cocina nocturna + "pronto delivery" + captura de leads (lista de WhatsApp). Meta: construir expectativa y audiencia de remarketing.
2. **Semana 3 — Lanzamiento:** campaña agresiva 7 días con **descuento 20–30%** en primeras órdenes (cupón por UTM), prioridad zonas A/B. Meta: primeras 200–300 órdenes para alimentar la data.
3. **Semana 4–5 — Estabilización:** remarketing a no-conversores, campaña de combos familiares (ticket alto), horario pico 7–10pm.
4. **Semana 6+ — Optimización:** escalar canales según ROAS, pausar lo que no rinda, lanzar suscripción/lealtad ("El Segoviano Club") si el ticket lo soporta.

### 8.4 KPIs
- **ROAS ≥ 2.5–3.0** (objetivo por campaña)
- **CPA por pedido** vs. margen por ticket (12–18% del plan de negocio)
- **Ticket promedio** y frecuencia de recompra (meta: ≥2 pedidos/mes)
- **% pedidos con UTM atribuida** (sanity check de tracking)
- **Tasa de conversión** landing → checkout (benchmark: 2–5%)

---

## 9. Riesgos y Recomendaciones

1. **Seguridad del canal público:** endpoints sin auth + multi-tenant = riesgo de fuga de datos entre tenants. Todo query debe filtrar por el tenant resuelto del slug. Aplicar rate-limiter Redis agresivamente en `/api/public/*`.
2. **Concurrencia en `sale_number` (VEN-YYYY-NNNNN único):** picos nocturnos requieren generación atómica o reintentos — revisar antes de Fase A.
3. **Contabilidad del fee de delivery:** definir cuenta de ingresos del fee (705/706 PCGE) para que los reportes no mezclen delivery con venta de comida.
4. **Kárdex nocturno:** la explosión de recetas corre al crear el Sale (funciona igual para delivery), pero validar **stock real de noche** (no se repone en ese turno) y política de "agotado" en el catálogo público.
5. **Rappi/PedidosYa:** APIs outbound (el pedido entra por su app) + contrato comercial. **Empezar con repartidores internos + WhatsApp**; integración en Fase C.
6. **WhatsApp (Fase B):** Meta exige verificación del número de negocio y plantillas aprobadas → **iniciar el trámite en paralelo a la Fase A** (no bloquea el MVP: los estados se ven en la app).
7. **Mano de obra nocturna:** validar con Nilton (operaciones) disponibilidad de cocina/repartidor en horario nocturno antes de prometer ETAs.

---

## 10. Próximos Pasos

1. ✅ Ron revisa y aprueba este plan (alcance Fase A como primer entregable).
2. Generar migración `0016_delivery` (modelos SQLAlchemy + alembic) — Jarvis puede preparar el borrador.
3. Sprint A (8–10 dd): canal público + checkout delivery + cocina + panel staff + campañas/UTM.
4. En paralelo: trámite WhatsApp Business API + definición de zonas/ETAs con Nilton + presupuesto de campañas de lanzamiento.
5. Deploy del MVP con `./deploy.sh --env prod` + QA suite extendida (script `scripts/qa/`).
6. Lanzamiento de campañas digitales (calendario Semana 1–6) con tracking UTM desde el día 1.

---

## Anexo — Referencias

- Repo: `~/projectos/IaaS-RonSys` · Producción: https://www.ronsyserp.com
- Reporte de investigación: `~/investigacion/07-varios/20260802_Top-10-negocios-con-mayor-probabilidad-de-exito-en.md`
- QA más reciente: `docs/reports/reporte-qa-2026-07-31.md` (10/10 PASS)
- Plan integral: `Plan-Integral-de-Integración-de-Módulos-ERP-v3.md` (deuda D-06 = Delivery, Fase 2)
- Manuales: `docs/manuales/` (guía despliegue, marcha blanca, usuario Fase 0)
