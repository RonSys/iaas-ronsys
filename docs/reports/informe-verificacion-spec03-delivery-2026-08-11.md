# Informe de Verificación — Módulo Delivery / Dark Kitchen (Spec 03, Fase A)

- **Fecha**: 2026-08-11
- **Auditoría solicitada por**: Ron (a petición del cliente El Segoviano)
- **Alcance**: verificación punto por punto de la Fase A del Spec 03 (03-spec-delivery-dark-kitchen-v0.1.md) contra producción: código, BD y endpoints en vivo
- **Método**: pruebas reales en producción (pedido de auditoría creado y cancelado, sin efectos residuales), consultas a BD, revisión de código y de la bitácora Spec Anchor

---

## Resumen ejecutivo (para el cliente)

**La Fase A del Delivery Nocturno / Dark Kitchen está operativa en producción.** Se verificó en vivo el ciclo completo: el cliente ve el menú nocturno en la página pública, hace su pedido pagando por Yape (o Plin/contraentrega), el pedido entra a la cocina, avanza por estados con seguimiento, y el staff lo gestiona desde el panel (zonas, repartidores, campañas). La contabilidad del negocio se registra automáticamente (venta → inventario → asiento contable), tal como exige el diseño.

**Se encontró 1 detalle a corregir** (no bloquea la operación diaria): la sección de **métricas de campañas con filtro por fechas** (ej. "¿cuánto vendió mi campaña de Meta entre el 1 y el 10 de agosto?") devuelve error de servidor. Sin filtro de fechas funciona. Es un ajuste técnico pequeño con solución clara.

**Recomendación**: corregir el filtro de fechas de métricas (trabajo menor) y, con eso, la Fase A queda 100% completa. Las Fases B y C (WhatsApp, pagos online, integración con Rappi/PedidosYa) siguen disponibles como siguiente paso cuando el negocio lo decida.

---

## Verificación punto por punto (evidencia en vivo, prod)

| # | Ítem de la Fase A (objetivo del spec) | Estado | Evidencia verificada el 2026-08-11 |
|---|---|---|---|
| 1 | **Landing pública con menú nocturno** | ✅ **CUMPLIDO** | `GET /api/public/el-segoviano/menu` → **200**, 5 secciones / 10 productos, ventana de delivery 19:00–23:59, teléfono Yape del negocio (912057784) y branding (logo/colores) configurados. Página web `/menu/el-segoviano` → 200 |
| 2 | **Checkout con pago Yape / Plin / contraentrega** | ✅ **CUMPLIDO** | **Pedido real creado**: 2× Lomo Saltado (S/70) + fee zona (S/5) = **S/75 pagados por Yape con referencia**. Respuesta 201 con código de seguimiento `DLV-9feea235b2`. Validaciones verificadas: pedido mínimo de zona (S/35) rechaza montos menores con mensaje claro |
| 3 | **Pedido llega a cocina (kanban existente)** | ✅ **CUMPLIDO** | El pedido creó automáticamente su orden de cocina (`kitchen_orders`, estado pendiente) vinculada a la venta — misma cocina en tiempo real que usan las mesas del salón |
| 4 | **Máquina de estados con seguimiento** | ✅ **CUMPLIDO** | Transiciones validadas en vivo: `recibido → en cocina` (200 OK); salto inválido `recibido → entregado` → **400 con mensaje** de las transiciones permitidas. Seguimiento público por código: `GET /api/public/orders/DLV-…/status` → 200 con estado y marcas de tiempo |
| 5 | **Panel staff (zonas, repartidores, campañas)** | ✅ **CUMPLIDO** | Endpoints del panel todos 200 con sesión: zonas, repartidores, campañas, lista de pedidos (kanban). En vivo: se creó un repartidor de prueba, se asignó al pedido (quedó "en reparto"), y al cancelar el pedido el repartidor volvió a "disponible" — ciclo correcto. CRUD de campañas y zonas operativo. Página web del panel → 200 |
| 6 | **Atribución UTM / medición ROAS** | ⚠️ **PARCIAL** | **Captura de UTM ✅**: el pedido guardó su origen (`meta/cpc/campaña`) en la BD. **Métricas con rango de fechas ❌**: `GET /metrics/campaigns?from=&to=` y `GET /metrics/overview?from=&to=` → **error 500** (detalle técnico: las fechas se comparan como texto contra fechas de BD). Sin fechas, el resumen sí responde (0 entregados / 11 cancelados en el período reciente). **Causa raíz**: falta de conversión de fechas en el servicio + tests que no cubren el filtro por fechas |

### Controles de seguridad verificados

| Control | Resultado |
|---|---|
| Aislamiento entre empresas (multi-tenant) | ✅ Página pública de un tenant inexistente → 404; datos nunca se cruzan |
| Acceso staff sin sesión | ✅ 401 (rechazado) |
| Rate-limit en endpoints públicos | ✅ Operativo (límite Redis; el menú responde normal en ráfagas de prueba) |
| Cancelación/limpieza | ✅ El pedido de auditoría quedó cancelado; repartidor y campaña de prueba eliminados — sin datos residuales |

### Cadena contable verificada (BD producción)

El pedido de auditoría generó en una sola transacción: **venta S/75** (tipo delivery) → **pago Yape S/75 con referencia** → **asiento contable AS-2026-00174** ("Venta VEN-2026-00029-035 — restaurant") → **orden de cocina** → **pedido delivery con UTM y fee S/5**. Confirma que el delivery nocturno usa el mismo motor contable que el salón (no es un flujo paralelo), tal como exige el diseño.

---

## Qué falta / pendiente

1. **Fix del filtro de fechas en métricas** (único hallazgo): convertir las fechas a formato correcto antes de consultar BD + agregar pruebas automatizadas con rango de fechas. Trabajo acotado (patrón ya existe en otro módulo del sistema: Panel del Dueño). **Estimación: horas, no días.**
2. Fuera de alcance Fase A (documentado, no pendiente): WhatsApp (Fase B), pagos online PSP (Fase C), integración Rappi/PedidosYa (Fase C), seguimiento en mapa (Fase C).

---

## Recomendación

- **Corregir el filtro de fechas de métricas** (fix pequeño + tests) → con eso la Fase A queda cerrada al 100% verificada.
- **Decidir siguiente fase**: Fase B (notificaciones WhatsApp a clientes — valor inmediato para confirmar pedidos y entregas) o Fase C (pago online PSP / integración con plataformas de delivery). Sugerencia de prioridad: **Fase B** si el objetivo es fidelizar al cliente nocturno; **Fase C** si el objetivo es volumen vía plataformas.

---

## Anexo técnico (para el equipo)

- **Archivos con el hallazgo**: `apps/backend/app/services/delivery_service.py` — `metrics_overview` (L708) y `metrics_campaigns` (L666) reciben `date_from/date_to` como `str` y los comparan contra `DeliveryOrder.created_at` (timestamptz) → `asyncpg ProgrammingError: operator does not exist: timestamp with time zone >= character varying`.
- **Patrón correcto ya existente**: `owner_dashboard_service.py` `_parse_date()` + `_resolve_dates()` (L77-105) — mismo bug clase que el de `Decimal` en agregaciones (lección 2026-08-10).
- **Tests que no cubren el caso**: `tests/test_delivery.py` (19 tests) no ejercita `metrics_*` con fechas.
- **Verificaciones en vivo realizadas**: 6 llamadas públicas + 12 staff + 4 consultas BD + 1 pedido real cancelado. Todas limpias.
- **E2E existentes**: `delivery-landing.spec.ts` (6) + `delivery-staff.spec.ts` (5) — 11/11 PASS contra prod (2026-08-03, bitácora spec).
- **Manual del usuario**: `docs/manuales/manual-delivery-dark-kitchen.md` (flujo cliente + staff + FAQ) — actualizado.
