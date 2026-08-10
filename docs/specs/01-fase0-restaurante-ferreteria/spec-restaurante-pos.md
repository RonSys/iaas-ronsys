# SPEC — Restaurante y POS (Mesas, Pedidos, Cocina, Takeaway, Promociones)

- **Estado**: 🟢 **IMPLEMENTADA Y DESPLEGADA** (producción; Fase 0 Real, migraciones `0005`, `0007`, `0011`)
- **Proyecto**: IaaS-RonSys — ERP SaaS (cliente: El Segoviano)
- **Alcance**: tenant restaurante; diseño multi-tenant por construcción
- **Fecha**: 2026-08-10 (spec generada por análisis del código)
- **Framework**: SDD / Spec Anchor — esta spec debe mantenerse sincronizada con el código

---

## 1. Contexto y objetivo

El módulo de restaurante cubre el flujo operativo completo: **mesas y secciones → tomar
pedido → cocina (kanban) → cierre/cobro → takeaway (para llevar)**. El POS registra la venta
en el motor de ventas (kárdex + asiento contable automático). Las promociones aplican
descuentos en el pedido.

---

## 2. Fase R — Hallazgos de la investigación (código verificado 2026-08-10)

### 2.1 Componentes reales

| Componente | Ubicación | Estado |
|---|---|---|
| Router restaurante | `app/routers/restaurant.py` (568 ln) | ✅ Desplegado |
| Service | `app/services/restaurant_service.py` (1,703 ln) | ✅ Implementado |
| Modelos | `app/adapters/db/models/restaurant.py`: RestaurantSection, Table, MenuItem, MenuModifier, KitchenOrder, TakeawayOrder, Promotion | ✅ Implementado |
| Modelos de venta | `app/adapters/db/models/sales.py`: PosSession, Sale, SaleItem, SalePayment, RestaurantSale, HardwareSale | ✅ Implementado |
| Migraciones | `0005` (ventas), `0007` (restaurante), `0011` (secciones), `2026-05-20` (session_id nullable) | ✅ Aplicadas en prod |
| Router ventas (POS) | `app/routers/sales.py` (260 ln) | ✅ Desplegado |
| Router inversión | `app/routers/investment.py` (97 ln) | ✅ Desplegado (spec propia) |
| Frontend | `TablesMap`, `MenuPage`, `KitchenKanban`, `TakeawayPage`, `PromotionsPage`, `SectionsManagement`, `Pos`, `SalesNew`, `SalesListPage` | ✅ Desplegado |
| E2E | `apps/web/e2e/dashboard.spec.ts` | ✅ Parcial |

### 2.2 Endpoints restaurante (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/restaurant/tables` | Crear mesa |
| GET | `/api/v1/restaurant/tables` | Listar mesas |
| PATCH | `/api/v1/restaurant/tables/{id}` | Editar mesa |
| DELETE | `/api/v1/restaurant/tables/{id}` | Eliminar mesa |
| POST | `/api/v1/restaurant/tables/{id}/reserve` | Reservar mesa |
| POST | `/api/v1/restaurant/tables/{id}/free` | Liberar mesa |
| POST | `/api/v1/restaurant/tables/{id}/open` | Ocupar mesa |
| POST | `/api/v1/restaurant/tables/{id}/order` | Tomar pedido en mesa |
| POST | `/api/v1/restaurant/tables/{id}/close-order` | Cerrar pedido |
| POST | `/api/v1/restaurant/tables/{id}/pay` | Cobrar mesa |
| GET | `/api/v1/restaurant/tables/{id}/orders/status` | Estado de pedidos de mesa |
| GET/POST | `/api/v1/restaurant/menu` | Listar/crear ítems de menú |
| PATCH | `/api/v1/restaurant/menu/{id}` | Editar ítem (precios, disponibilidad) |
| GET/PUT | `/api/v1/restaurant/menu/{id}/recipe` | Ver/editar receta del plato (Spec 01) |
| GET | `/api/v1/restaurant/products` | Productos vinculables (ingredientes) |
| GET | `/api/v1/restaurant/orders/active` | Pedidos activos |
| GET | `/api/v1/restaurant/orders/{id}` | Detalle de pedido |
| POST | `/api/v1/restaurant/orders/{id}/send-to-kitchen` | Enviar a cocina |
| PATCH | `/api/v1/restaurant/orders/{id}/status` | Actualizar estado pedido |
| DELETE | `/api/v1/restaurant/orders/{id}/items/{mid}` | Quitar ítem del pedido |
| POST | `/api/v1/restaurant/orders/{id}/apply-promotion/{promotion_id}` | Aplicar promoción |
| POST/GET | `/api/v1/restaurant/takeaway` | Crear/listar pedidos takeaway |
| PATCH | `/api/v1/restaurant/takeaway/{id}/status` | Cambiar estado takeaway |
| PATCH | `/api/v1/restaurant/takeaway/{id}/pickup` | Marcar recogido |
| POST/GET | `/api/v1/restaurant/promotions` | CRUD promociones |
| PATCH | `/api/v1/restaurant/promotions/{id}` | Editar promoción |
| CRUD | `/api/v1/restaurant/sections` | Secciones/zonas de mesas (mig. 0011) |
| WS | `/ws/kitchen/{tenant_id}` | WebSocket cocina — actualización en vivo del kanban (`restaurant.py:543`) |
| WS | `/ws/waiter/{tenant_id}` | WebSocket mozos — actualización en vivo de mesas/pedidos (`restaurant.py:557`) |

### 2.3 Endpoints POS / ventas (verificados)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/sales/sessions/open` | Abrir caja (POS session) |
| GET | `/api/sales/sessions/current` | Sesión actual |
| POST | `/api/sales/sessions/{id}/close` | Cerrar caja |
| POST | `/api/sales/sale` | Registrar venta (create_sale) |
| GET | `/api/sales/sales` | Historial de ventas |
| GET | `/api/sales/sale/{id}` | Detalle venta |
| POST | `/api/sales/sale/{id}/void` | Anular venta |
| GET | `/api/sales/sale/{id}/ticket` | Ticket/boleta |
| GET | `/api/sales/payment-methods` | Métodos de pago (yape/plin/cash/card/transfer) |

### 2.4 Flujo de venta de restaurante (verificado en `sales_service.create_sale` L267)

```
POST /api/sales/sale
  1. Valida sesión POS abierta (session_id nullable → permite venta sin caja, mig. 2026-05-20)
  2. Carga company → business_type (restaurant/ferretería)
  3. Explosión de recetas pre-check atómico si recipe_explosion (Spec 01)
  4. Calcula totales con IGV incluido/excluido (QA-F2-01: igv_included)
  5. Valida stock (kárdex): seriales disponibles si is_serialized, si no stock numérico
  6. Crea Sale + SaleItems (+menu_item_id, mig. 0015) + SalePayments
  7. _generate_journal_entry → asiento contable automático (HU-F2-006)
  8. Kárdex: salida por producto vendido (o explosión de ingredientes)
  9. Aplica promoción si corresponde
```

---

## 3. Fase P — Modelo de datos clave

```sql
tables (id, tenant_id, section_id, name, capacity, status[libre|ocupada|reservada])
restaurant_sections (id, tenant_id, name, sort_order)
menu_items (id, tenant_id, name, price, category_id, preparation_area[cocina|bar], is_available, available_from/to)
menu_modifiers (id, tenant_id, menu_item_id, name, price)
kitchen_orders (id, tenant_id, table_id, status, items jsonb, sent_at)
takeaway_orders (id, tenant_id, status, customer_name, phone, items, pickup_at)
promotions (id, tenant_id, name, type, value, active, date_range)
pos_sessions (id, tenant_id, opened_by, opened_at, closed_at, opening_cash, closing_cash)
sales (id, tenant_id, session_id, total, igv, status, journal_entry_id, restaurant_data jsonb)
sale_items (id, sale_id, product_id, menu_item_id, item_name, quantity, unit_price, modifiers)
sale_payments (id, sale_id, method[yape|plin|cash|card|transfer], amount, reference)
```

### 3.1 Criterios de aceptación (verificados)

- CA1: ciclo mesa completo: libre → reservada/ocupada → pedido → cocina → cobro → libre. ✅
- CA2: venta con kárdex + asiento contable automático (HU-F2-004/005/006). ✅
- CA3: modificadores por plato al tomar pedido (Fase 0 Real). ✅
- CA4: takeaway con estados y pickup. ✅
- CA5: promociones aplicables al pedido. ✅
- CA6: sesión POS opcional (venta sin caja permitida). ✅
- CA7: IGV incluido/excluido por ítem (QA-F2-01). ✅

---

## 4. Matriz Spec Anchor (sincronización spec ↔ código)

| Artefacto | Ubicación en código | Spec |
|---|---|---|
| Router restaurante | `app/routers/restaurant.py` | §2.2 |
| Router ventas | `app/routers/sales.py` | §2.3 |
| Services | `restaurant_service.py`, `sales_service.py` | §2.4 |
| Modelos | `models/restaurant.py`, `models/sales.py` | §3 |
| Migraciones | `0005`, `0007`, `0011`, `0015`, `2026-05-20` | §3 |
| Frontend | `pages/restaurante/*`, `pages/ventas/*`, `Pos.tsx` | §2.1 |
| E2E | `e2e/dashboard.spec.ts` | §2.1 |

> ⚠️ Si cambias flujos de mesas/pedidos/cocina/takeaway/promociones o el POS, **actualiza esta spec** (Spec Anchor).
