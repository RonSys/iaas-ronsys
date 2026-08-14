# 📊 Informe Ejecutivo — Sistema de Gestión El Segoviano

- **Fecha:** 10 de agosto de 2026 *(última actualización: 12 de agosto de 2026)*
- **Producto:** Sistema de gestión integral (ERP) para la franquicia **El Segoviano**
- **Estado general:** 🟢 **OPERATIVO EN PRODUCCIÓN** — el sistema está instalado y funcionando en el servidor del negocio (www.ronsyserp.com), con pedidos reales ya registrados.
- **Audiencia:** Cliente final / dueños de la franquicia

---

## 1. Resumen Ejecutivo

El Segoviano cuenta hoy con un **sistema de gestión completo y funcionando en producción**, muy por encima de lo que se comprometió originalmente. Lo que empezó como una herramienta de control contable y de inventario ha crecido hasta convertirse en una **plataforma que maneja todo el negocio**: la atención en el salón, las ventas, la cocina, el inventario, la contabilidad, las recetas de los platos y —desde agosto— el **delivery nocturno con pedidos por internet**.

El sistema ya no es un proyecto: **es una herramienta de trabajo diario**. Está en producción (no en pruebas), el menú público de delivery responde correctamente, ya hay **pedidos reales entregados** en la zona de San Juan de Lurigancho, y los módulos están verificados contra los datos reales del negocio.

**En una frase:** el negocio puede operar hoy —salón, para llevar, ferretería y delivery nocturno— con un solo sistema que además lleva la contabilidad y el inventario solos.

---

## 2. Módulos Avanzados y Funcionales

### 2.1 Administración y Seguridad 🔐

| Qué hace | Estado |
|---|---|
| Ingreso al sistema con correo y contraseña, con protección contra intentos de acceso no autorizados (bloqueos automáticos tras varios intentos fallidos) | 🟢 Operativo |
| **Usuarios con roles**: administrador (dueño), gerente, operador (cocina/caja/almacén) y solo-consulta (inversionista, auditor) | 🟢 Operativo |
| **Multi-empresa**: cada negocio de la franquicia (cevichería, ferretería, etc.) tiene sus datos completamente separados; nadie ve información de otra empresa | 🟢 Operativo |
| Personalización de la imagen del sistema (colores y marca del local) | 🟢 Operativo |

### 2.2 Ventas / Punto de Venta (POS) 💳

| Qué hace | Estado |
|---|---|
| **Caja**: apertura de caja y registro de ventas del día | 🟢 Operativo |
| **Venta con ticket**: registro de la venta, cálculo de totales y comprobante | 🟢 Operativo |
| **Métodos de pago**: efectivo, tarjeta, Yape, Plin y transferencia (con número de referencia) | 🟢 Operativo |
| **Historial de ventas**: todas las ventas registradas, consultables por fecha | 🟢 Operativo |
| Ventas con **precio mayorista y minorista** (para la ferretería: el sistema elige el precio según la cantidad comprada) | 🟢 Operativo |
| Cada venta **descuenta el inventario y genera su contabilidad automáticamente** (sin trabajo extra) | 🟢 Operativo |

### 2.3 Restaurante 🍽️

| Qué hace | Estado |
|---|---|
| **Mesas y secciones**: mapa del salón con mesas libres, ocupadas, reservadas y en limpieza; secciones (Terraza, Salón, VIP); el mesero se identifica solo | 🟢 Operativo |
| **Toma de pedidos**: desde la mesa o para llevar, con menú digital por categorías | 🟢 Operativo |
| **Personalización de platos (modificadores)**: "sin cebolla", "huevo frito +S/3", "término de cocción" — el precio se recalcula solo | 🟢 Operativo |
| **Cocina en tiempo real**: las comandas llegan solas a la pantalla del cocinero (pendiente → preparando → listo → entregado), con aviso de demoras | 🟢 Operativo |
| **Para llevar (take away)**: pedidos con nombre, teléfono y hora de recojo | 🟢 Operativo |
| **Promociones automáticas**: combos, descuento por porcentaje, descuento fijo y 2x1 — el sistema aplica la mejor opción al cerrar la cuenta | 🟢 Operativo |

### 2.4 Inventario y Kárdex 📦

| Qué hace | Estado |
|---|---|
| **Control de stock** por producto, con historial completo de entradas (compras) y salidas (ventas) | 🟢 Operativo |
| **Costo promedio ponderado**: cuando el precio de compra cambia, el sistema recalcula el costo promedio automáticamente | 🟢 Operativo |
| **Valorización del inventario**: cuánto vale lo que hay en el almacén, en soles | 🟢 Operativo |
| **Productos con serial y garantía** (ferretería): control unitario — se sabe exactamente qué unidad se vendió, a quién y hasta cuándo tiene garantía; si se anula la venta, el serial vuelve al almacén solo | 🟢 Operativo |
| Categorías de productos y búsqueda por nombre o código | 🟢 Operativo |

### 2.5 Contabilidad y Finanzas 💰

| Qué hace | Estado |
|---|---|
| **Asientos contables automáticos**: cada venta genera su registro contable solo (partida doble verificada) | 🟢 Operativo |
| **Estados financieros**: Estado de Resultados (ganancias/pérdidas), Balance General y Balance de Comprobación — generados automáticamente | 🟢 Operativo |
| **9 indicadores financieros con semáforo** 🟢🟡🔴: liquidez, endeudamiento, margen, rentabilidad, recuperación de la inversión, etc., con interpretación incluida | 🟢 Operativo |
| **Flujo de caja**: seguimiento de ingresos y egresos | 🟢 Operativo |
| **Simulador de inversión**: proyección del negocio a 12 meses (ventas, costos, sueldos, alquiler, préstamo, depreciación) con resultados financieros y evaluación de rentabilidad — ideal para decidir inversiones o pedir financiamiento | 🟢 Operativo |

### 2.6 Recetas de Platos 🍛

| Qué hace | Estado |
|---|---|
| **Receta por plato**: cada plato de cocina tiene su lista de ingredientes con cantidades y unidades | 🟢 Operativo (3 recetas cargadas, con 15 ingredientes) |
| **Descuento automático de ingredientes al vender**: al vender un plato, los ingredientes salen del inventario solos ("consumo por receta") | 🟢 Operativo |
| **Costeo y margen del plato**: el sistema muestra el costo de cada plato y su margen en vivo; si sube el precio de un insumo, el costo del plato se recalcula solo | 🟢 Operativo |
| Protección ante faltante: si no hay ingredientes suficientes, la venta se rechaza con aviso claro (sin descuentos parciales) | 🟢 Operativo |

### 2.7 Delivery / Dark Kitchen 🛵 (lo más reciente)

| Qué hace | Estado |
|---|---|
| **Pedidos online por menú público**: los clientes piden desde su celular en el enlace del local (menu/el-segoviano), con horario nocturno configurable (19:00–24:00) | 🟢 Operativo — verificado en producción |
| **Pago**: Yape, Plin (con código de referencia) o contraentrega | 🟢 Operativo |
| **Zonas de reparto**: cada zona con su costo de delivery, pedido mínimo y tiempo estimado. La Zona 1 (Montenegro / Motupe / Canto Grande — SJL, S/5, mínimo S/35, ~35 min) ya está configurada; se pueden agregar más | 🟢 Operativo |
| **Repartidores**: registro de repartidores con teléfono y vehículo; estados disponible / en entrega / descanso; asignación de pedidos | 🟢 Operativo |
| **Seguimiento del pedido**: el cliente ve el avance con su código: recibido → en cocina → listo → en camino → entregado | 🟢 Operativo |
| **Campañas publicitarias con medición**: cada campaña (Meta/Instagram, Google, TikTok) tiene su enlace de anuncio; el sistema atribuye los pedidos a la campaña y muestra ventas y **retorno de la inversión publicitaria (ROAS)** | 🟢 Operativo |
| Los pedidos online entran a cocina, descuentan inventario y generan contabilidad solos — **sin necesidad de abrir caja** | 🟢 Operativo |
| **Producción real**: más de 8 pedidos reales registrados desde la puesta en marcha | 🟢 Verificado |
| **Notificaciones WhatsApp (Fase B)**: avisos automáticos al cliente (pedido confirmado, en cocina, en camino, entregado, cancelado) y alertas al local (pedido nuevo, cancelación). Motor de eventos desplegado y verificado en producción (modo dry-run: funciona sin costo ni cuenta Meta; se activa el envío real al conectar la cuenta WhatsApp Business) | 🟢 Motor desplegado — envío real pendiente de cuenta Meta (ver plan) |

### 2.8 Panel Administrativo Global (Dueño de la Franquicia) 🏢

| Qué hace | Estado |
|---|---|
| Consola central para **crear y gestionar empresas** (locales de la franquicia) y **usuarios de todas las empresas**, activar/desactivar accesos y ver indicadores agregados | 🟢 Operativo |
| Permite vender el sistema como servicio a otros negocios: cada empresa con sus datos, su marca y su propio enlace público | 🟢 Operativo |

### 2.9 Panel del Dueño (Dashboard Ejecutivo) 📊 *(lo más reciente)*

| Qué hace | Estado |
|---|---|
| **Vista ejecutiva de una sola pantalla**: el dueño ve cómo va el negocio hoy sin hojas de cálculo — ventas del día, ticket promedio, % de delivery, pedidos en cocina y en ruta en vivo | 🟢 Operativo — verificado en producción |
| **Ventas por hora (salón vs delivery)** y **por día de la semana** en gráficos | 🟢 Operativo |
| **Canales de venta** (salón / para llevar / delivery), **top platos vendidos** y **métodos de pago** (Yape, Plin, efectivo, tarjeta, transferencia) | 🟢 Operativo |
| **Delivery**: pedidos por zona, embudo (recibido → cocina → listo → en ruta → entregado) y **GMV solo de pedidos entregados** | 🟢 Operativo |
| **ROAS por campaña publicitaria**: cuánto retorna cada campaña (Meta, Google, TikTok) frente a lo invertido | 🟢 Operativo |
| **Selector de rango**: hoy / 7 días / 30 días, actualizable con un clic; acceso con rol admin/manager/viewer (solo lectura) | 🟢 Operativo |
| **V2 — Heatmap de demanda** hora×día separado por canal (Salón / Delivery), intensidad de color relativa | 🟢 Operativo (V2, 2026-08-10) |
| **V2 — Margen por canal con costeo**: ingresos vs costo de recetas/kárdex → margen real por canal (salón / para llevar / delivery), con nota de costeabilidad | 🟢 Operativo (V2, 2026-08-10) |
| **V2 — Comparativa semana vs semana** con % de cambio en KPIs (ventas, pedidos, ticket, % delivery) | 🟢 Operativo (V2, 2026-08-10) |
| **V2 — Reporte descargable CSV + PDF** del resumen del período (dropdown "Descargar ▾" con CSV/PDF, PDF: 9 secciones platypus, filename `panel_dueño_YYYYMMDD.pdf`) | 🟢 Operativo (V2, 2026-08-10) + **PDF desplegado (2026-08-11)** |
| **V2 — Alertas de desviación** vs promedio de los últimos 7 días (umbrales: roja ≤ −20%, ámbar ≤ −10%) | 🟢 Operativo (V2, 2026-08-10) |

---

## 3. Evolución del Desarrollo (cómo creció el sistema)

El sistema se construyó por etapas, y **cada etapa se probó con datos reales antes de continuar**:

1. **Punto de partida — núcleo contable (MVP):** el sistema nació como una herramienta financiera: control de inventario (kárdex), contabilidad automática, estados financieros, indicadores y un simulador para evaluar la inversión del negocio. También se construyó la base de seguridad (usuarios con roles, empresas separadas).
2. **Fase Restaurante + Ferretería:** se sumó la operación del día a día: mapa de mesas, menú digital con personalización de platos, cocina en tiempo real, pedidos para llevar, promociones, caja/ventas con todos los métodos de pago, y para la ferretería: ventas por mayor/detal y productos con serial y garantía. Se estrenó en marcha blanca con datos reales del local.
3. **Fase Recetas y Costos:** se conectó el menú con el inventario: recetas por plato, descuento automático de ingredientes al vender, y costeo en vivo del plato (costo variable con promedio ponderado).
4. **Fase Delivery / Dark Kitchen (agosto 2026):** aprovechando que el local está libre de noche, se lanzó el **delivery nocturno**: menú público por internet, zonas de reparto, repartidores, campañas publicitarias medibles y seguimiento del pedido para el cliente. Hoy está **en producción con pedidos reales**.

**Conclusión de la evolución:** el plan original era un sistema contable; el sistema actual es una **plataforma completa de gestión y venta por canales** (salón, para llevar, mostrador y delivery online), que además lleva la contabilidad sola. Es sustancialmente más completo de lo comprometido.

---

## 4. En Producción Hoy vs. Pendiente / Futuro

### ✅ Verificado en producción (2026-08-10)

- Sistema desplegado y operativo en el servidor del negocio (www.ronsyserp.com).
- Delivery operativo: menú público respondiendo, **Zona 1 (SJL)** activa, **más de 8 pedidos reales** registrados.
- Recetas operativas: **3 recetas cargadas** (Ceviche Clásico, Ceviche Mixto, Arroz con Mariscos) con **15 ingredientes** en el kárdex.
- Los módulos de administración, ventas, restaurante, inventario, contabilidad, recetas, delivery y consola global verificados contra los datos reales.

### ⏳ Pendiente / futuro (no está desarrollado aún)

- **No existe aplicación móvil** para clientes ni para el personal (el sistema se usa desde el navegador del celular o computadora).
- **No hay integración con Rappi / PedidosYa / Didi Food** (los pedidos llegan por el menú propio del local).
- **No hay pago online directo** (tarjeta en línea): el pago es Yape/Plin con referencia o contraentrega.
- **No hay notificaciones automáticas por WhatsApp en envío real** (el motor de eventos está desplegado y verificado en modo demo/dry-run desde 2026-08-11 — Fase B: avisos de pedido confirmado, en cocina, en camino, entregado y cancelado; el envío real se activa al conectar la cuenta WhatsApp Business de Meta, ver §2.7 y plan de cuenta Meta).
- **No hay facturación electrónica (SUNAT)**: las ventas se registran internamente; la emisión de comprobantes electrónicos es una fase futura.
- **No hay escáner de código de barras** en la caja (el código se puede ingresar manualmente).
- Detalles finos por automatizar: factor de merma/desperdicio en recetas, venta visual de platos con receta desde el punto de venta, y la pantalla de cocina aún no se integra con el POS de platos en todas las variantes.
- ~~La funcionalidad de "asistentes inteligentes" dentro del sistema está diseñada pero no operativa~~ → **CERRADO (2026-08-13/14)**: F3 Recepcionista IA y F5 Pregúntale al Sistema implementadas y desplegadas en producción (ver §5.3 filas 4 y 6).
- ~~Panel del Dueño: reporte descargable en PDF (iteración 2)~~ → **CERRADO (2026-08-11)**: PDF desplegado en producción — `GET /api/v1/dashboard/owner/export?format=pdf` (reportlab platypus, 9 secciones), dropdown CSV/PDF en el panel (spec 04 §CA13-b).

---

## 5. Mapa de Requerimientos ↔ Specs (documento vivo — Spec Anchor) 🗺️

> Este informe es el **mapa maestro**: cada funcionalidad desarrollada está registrada aquí y alineada con su **Spec** (especificación técnica SDD) en `docs/specs/`. La regla **Spec Anchor** garantiza que spec y código están sincronizados: cuando se desarrolla un requerimiento nuevo, primero se registra aquí, se crea/actualiza su spec y recién se codea (con la ayuda de JARVIS). El cliente siempre puede ver aquí qué hay, en qué etapa está y a qué spec corresponde.

### 5.1 Lo desarrollado y sus etapas (requerimiento ↔ spec)

| Fase | Requerimiento del cliente (sección del informe) | Spec asociada | Ubicación de la spec | Estado |
|---|---|---|---|---|
| **00 — MVP Core** | Administración y seguridad: login, roles, multi-empresa (§2.1) | SPEC — Auth Multi-Tenant | `docs/specs/00-mvp-core/spec-auth-multitenant.md` | 🟢 Implementada |
| **00 — MVP Core** | Contabilidad: asientos automáticos, estados financieros, indicadores, flujo de caja (§2.5) | SPEC — Motor Contable | `docs/specs/00-mvp-core/spec-motor-contable.md` | 🟢 Implementada |
| **00 — MVP Core** | Inventario y kárdex: stock, costos promedio, valorización (§2.4) | SPEC — Kárdex de Inventario | `docs/specs/00-mvp-core/spec-kardex-inventario.md` | 🟢 Implementada |
| **00 — MVP Core** | Simulador de inversión a 12 meses (§2.5) | SPEC — Simulador Financiero | `docs/specs/00-mvp-core/spec-simulador-financiero.md` | 🟢 Implementada |
| **01 — Restaurante + Ferretería** | Restaurante y POS: mesas, cocina en vivo, takeaway, promociones, ventas/caja (§2.2, §2.3) | SPEC — Restaurante y POS | `docs/specs/01-fase0-restaurante-ferreteria/spec-restaurante-pos.md` | 🟢 Implementada |
| **01 — Restaurante + Ferretería** | Inventario ferretería: categorías, seriales con garantía (§2.4) | SPEC — Inventario Ferretería | `docs/specs/01-fase0-restaurante-ferreteria/spec-inventario-ferreteria.md` | 🟢 Implementada |
| **01 — Restaurante + Ferretería** | Panel global del dueño: empresas y usuarios (§2.8) | SPEC — Superadmin y Tenants | `docs/specs/01-fase0-restaurante-ferreteria/spec-superadmin-tenants.md` | 🟢 Implementada |
| **01 — Restaurante + Ferretería** | Registro de inversiones y reportes | SPEC — Inversiones | `docs/specs/01-fase0-restaurante-ferreteria/spec-inversiones.md` | 🟢 Implementada |
| **02 — Recetas y Costos** | Recetas por plato con descuento automático y costeo (§2.6) | SPEC 01 — Recetas por Producto | `docs/specs/02-recetas-costos/01-spec-recetas-productos-v0.2.md` | 🟢 Implementada |
| **02 — Recetas y Costos** | Costos variables: promedio ponderado en compras (§2.6) | SPEC 02 — Costos Variables | `docs/specs/02-recetas-costos/02-spec-costos-variables-v0.1.md` | 🟢 Implementada |
| **03 — Delivery** | Delivery / Dark Kitchen: menú público, zonas, repartidores, campañas, seguimiento (§2.7) | SPEC 03 — Delivery Dark Kitchen | `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md` | 🟢 Implementada |
| **04 — Panel Dueño** | Panel de indicadores para el dueño: KPIs del día, canales, top platos, ROAS, zonas, embudo delivery (V1 completa) + V2: heatmap hora×día por canal, márgenes por canal con costeo, comparativa semana vs semana, reporte descargable CSV + PDF (dropdown), alertas de desviación vs 7 días | SPEC — Panel del Dueño | `docs/specs/04-panel-indicadores/spec-panel-dueño.md` | 🟢 IMPLEMENTADA Y DESPLEGADA (V1 + V2 + PDF, 2026-08-11) |
| **99 — Infraestructura** | Servidor, despliegue, respaldos, monitoreo y pruebas (soporte de todo lo anterior) | SPEC — Infra y CI/CD | `docs/specs/99-infra-devops/spec-infra-cicd.md` | 🟢 Implementada |

### 5.2 Cómo se incorpora un requerimiento nuevo (proceso obligatorio)

```
Nuevo requerimiento del cliente
        │
        ▼
1. Se REGISTRA en este informe (tabla §5.3) con fecha, descripción y prioridad
        │
        ▼
2. Se crea/actualiza su SPEC SDD en docs/specs/<fase>/ (formato estándar:
   estado, decisiones, fase R hallazgos, contratos, criterios de aceptación)
        │
        ▼
3. Se desarrolla con JARVIS: código + pruebas + migración (si aplica),
   siempre alineado a la spec (Spec Anchor: cambio en spec → cambio en código)
        │
        ▼
4. Se verifica: la spec refleja el código real y el código cumple la spec
        │
        ▼
5. Se actualiza este informe: estado del requerimiento, sección del módulo
   (si es nuevo) y fila de la matriz §5.1
```

> **Regla de oro:** ningún requerimiento se codea sin estar registrado en este informe y sin su spec actualizada. Así, el cliente siempre tiene el mapa completo de lo desarrollado y en curso.

### 5.3 Registro de nuevos requerimientos (se completa a medida que llegan)

| # | Requerimiento | Prioridad | Spec asociada | Estado | Fecha registro |
|---|---|---|---|---|---|
| 1 | **📊 Panel de indicadores para el dueño** — resumen ejecutivo (ventas del día, canal más rentable, platos más vendidos, ROAS campañas, pedidos por zona, embudo delivery) en una sola pantalla. Alcance: V1 (panel inicial) + V2 (analítica avanzada: heatmaps, márgenes por canal, comparativas semanales, reporte descargable). Enfoque inicial: restaurante + delivery/dark kitchen | 🔴 Alta | `docs/specs/04-panel-indicadores/spec-panel-dueño.md` | 🟢 **IMPLEMENTADO Y DESPLEGADO (V1 + V2 + PDF, 2026-08-11)** — V1: endpoint `/api/v1/dashboard/owner` + página `/panel` en producción (verificado: S/638, 11 pedidos, 90.9% delivery). V2 desplegada: heatmap hora×día por canal, márgenes por canal con costeo, comparativa semana vs semana, reporte descargable CSV, alertas vs promedio 7 días. **PDF del reporte (iteración 2) DESPLEGADO (2026-08-11)**: `GET /api/v1/dashboard/owner/export?format=pdf` — reportlab platypus 9 secciones, verificado 200 application/pdf en prod; dropdown CSV/PDF en el panel | 2026-08-10 |
| 2 | **💬 Notificaciones WhatsApp (Fase B del Delivery)** — avisos automáticos al cliente (confirmado, en cocina, en camino, entregado, cancelado) y alertas al local. Motor de eventos (colas RabbitMQ) desplegado en producción y verificado en vivo el 2026-08-11; envío real requiere cuenta WhatsApp Business API (Meta) — plan en `plan-cuenta-meta-whatsapp.md` | 🟠 Media | `docs/specs/03-delivery/04-spec-whatsapp-en-vivo-v0.1.md` (F1) + `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md` §7 | 🟢 **F1 "WHATSAPP EN VIVO" IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — botones "Pedir por WhatsApp"/"Llamar" en landing y campañas, migración BSUID (0017), `contact` público, 16 tests + E2E en caliente en prod. **Pendiente solo el trámite Meta del cliente** (cuenta Cloud API + 7 plantillas Utility — manual en `docs/manuales/manual-servicio-meta-whatsapp-f1.md`); sin cuenta Meta el sistema sigue en dry-run (simulación validada, ver `docs/reports/simulacion-f1-datos-ficticios-2026-08-13.md`) | 2026-08-11 |
| 3 | **📞 Central telefónica "que no pierde llamadas" (canal delivery por teléfono)** — Asterisk en el servidor: varias llamadas simultáneas sin buzón (concurrencia), click-to-call, registro + grabación de llamadas, conversión llamada → pedido delivery al mismo flujo (cocina, kárdex, contabilidad, DLV-). Requiere trunk SIP (4 canales recomendados) | 🟠 Media | `docs/specs/03-delivery/05-spec-central-telefonica-v0.1.md` | 🟢 **F2 "CENTRAL QUE NO PIERDE LLAMADAS" IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — Asterisk (Docker host, `mlan/asterisk:20.15.2`), call-bridge AMI/ARI, CallRecords (migración 0018), panel Central Telefónica `/restaurante/central` (WS en vivo + historial + click-to-call + convertir llamada→pedido con kárdex/contabilidad), 20 tests + E2E en caliente en prod verificada con **descuento real de insumos en kárdex**. **Pendiente solo lo externo**: trunk SIP real del cliente + port-forward UDP 5060/10000-10100 + +8GB RAM recomendados para go-live | 2026-08-12 |
| 4 | **🤖 Recepcionista IA por voz** — IA contesta el teléfono, toma el pedido (notas + dirección), confirma por WhatsApp, graba y transcribe, transfiere a humano con contexto; el pedido entra solo al sistema. Agente de dominio acotado (solo pedidos/menú/estado — requisito de cumplimiento Meta 15-ene-2026). Requiere Fase 2 + proveedor de voz IA | 🟠 Media | `docs/specs/03-delivery/06-spec-recepcionista-ia-v0.1.md` (spec 06 — F3) | 🟢 **F3 "RECEPCIONISTA IA" IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — agente por voz sobre la Central Telefónica (F2): migración `0019_voice_ai` (call_transcriptions + columnas IA en call_records), `voice_ai_service` (máquina de estados), `voice_bridge` (Stasis app + External Media RTP→WS), endpoints `/api/v1/calls/{id}/transcript|ai-state|ai-context|transfer|complete` + alias `/api/v1/ai-calls/*`, panel IA en Central Telefónica; suite 516 passed + E2E en caliente en prod (transcripción + transferencia con contexto). **Pendiente solo lo externo**: proveedor de voz IA (STT/TTS) y llamadas reales en PoC de 2 semanas | 2026-08-12 |
| 5 | **🏢 Franquicia conectada (multi-sucursal)** — tablets/pantallas por sucursal con pedidos en tiempo real, monitoreo central del dueño, enrutamiento de llamadas por local ("house service" por sucursal, referencia S/ 2,000 del benchmark). Explota el multi-tenant existente | 🟢 Alta (visión de crecimiento) | `docs/specs/01-fase0-restaurante-ferreteria/spec-superadmin-tenants.md` + extensión | 🟡 **PROPUESTA (2026-08-12)** — dentro del plan integral de canales; se activa cuando el modelo funcione en 1 local | 2026-08-12 |
| 6 | **🤖📊 "Pregúntale al Sistema" (consultas IA en lenguaje natural)** — el dueño consulta datos reales en tiempo real: "¿qué producto se vendió más hoy por delivery?". La IA decide qué función SQL del catálogo llamar (tool calling / NL2SQL controlado, sin SQL libre), responde en lenguaje natural; replicable a todo el ERP (ventas, inventario, contabilidad, recetas). Base: `app/core/agents/` (puerto hexagonal `BaseSkill` ya diseñado) | 🟠 Media | `docs/specs/06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md` (spec 08 — F5) | 🟢 **F5 "PREGÚNTALE AL SISTEMA" IMPLEMENTADA Y DEPLOYADA (2026-08-14)** — NL2SQL controlado: catálogo SQL seguro (10 consultas delivery, migración `0020_assistant`), `assistant_service` (pipeline 8 pasos: LLM elige query_catalog_id + params tipados, NUNCA escribe SQL; fallback determinista 35-44ms; anti-inyección; fechas relativas; R9), router `/api/v1/assistant/{ask,catalog,logs}` (rate limit 10 req/min), chat flotante 🤖 en el Panel del Dueño; 46 tests → suite 517 passed; QA real destapó y corrigió 3 bugs de ejecución; E2E en caliente en prod **6/6** (respuesta con datos reales: ticket promedio S/ 47.92 en 38 pedidos) + smoke 10/10 consultas | 2026-08-12 |

---

## 6. Inversión vs. Beneficios (Costos / Beneficios)

### 6.1 Beneficios del sistema (valor para el negocio)

| Beneficio | Qué significa en el día a día |
|---|---|
| ⏱️ **Ahorro de tiempo en caja e inventario** | La venta se registra en segundos; el stock se descuenta solo (ventas y recetas). Se elimina el cuadre manual de kárdex y las hojas de cálculo |
| 🍽️ **Control de costos y mermas** | Al vender un plato, los ingredientes salen del inventario automáticamente; se sabe el costo real de cada plato y su margen. Lo que se pierde o desperdicia se ve en el kárdex |
| 📊 **Decisiones con datos** | Reportes financieros, indicadores con semáforo, flujo de caja y simulador: el dueño decide precios, compras e inversiones con números, no con intuición |
| 🛵 **Nueva fuente de ingreso: delivery nocturno** | El local (que de noche estaba cerrado) ahora vende y reparte: el delivery aprovecha la capacidad instalada sin inversión adicional en infraestructura |
| 📢 **Marketing medible** | Cada campaña publicitaria tiene su enlace; el sistema muestra cuánto vendió cada campaña y el retorno de la inversión (ROAS): se sabe en qué anuncios conviene seguir invirtiendo |
| 🧾 **Menos errores contables** | Los asientos contables se generan solos con cada venta (partida doble verificada); la contabilidad cuadra sin depender de la memoria o de apuntes sueltos |
| 🏢 **Plataforma para crecer** | El panel global permite incorporar más locales o negocios de la franquicia, cada uno con sus datos y su marca separados |

### 6.2 Costos y consideraciones (honestos)

| Consideración | Detalle |
|---|---|
| 💻 **Inversión en el sistema y su mantenimiento** | El desarrollo, la instalación y el soporte continuo (servidor, actualizaciones, respaldos de información) tienen un costo; el sistema requiere mantenimiento periódico para seguir operando y protegido |
| 📥 **Tiempo de carga de datos inicial** | Antes de operar al 100% hay que cargar en el sistema: productos del almacén, recetas de los platos, mesas, promociones y usuarios. Es un trabajo de puesta en marcha que toma días (se hace una vez) |
| 🧑‍🍳 **Curva de aprendizaje del personal** | Meseros, cocineros y cajeros deben aprender a usar las pantallas (mesas, cocina, caja, delivery). Con el personal adecuado se domina en pocos días, pero exige capacitación y algo de paciencia al inicio |
| 🛵 **Costos operativos del delivery** | El canal de ventas nocturno genera costos reales: pago a repartidores, empaque de los pedidos y teléfono/datos. Estos costos deben cubrirse con el margen de cada pedido |
| 🤝 **Comisiones futuras si se integran plataformas** | Si más adelante se conecta Rappi / PedidosYa, esas plataformas cobran comisión por pedido; la integración en sí también implica desarrollo e inversión adicional |
| 🔧 **Desarrollo continuo = inversión adicional** | Las fases futuras (app móvil, facturación electrónica SUNAT, notificaciones WhatsApp, pago online) son mejoras nuevas y se cotizan por separado; no están incluidas en lo ya construido |

> **Lectura ejecutiva:** el sistema ya entrega valor operativo (ahorro de tiempo, control, menos errores) y abre ingresos nuevos (delivery). Los costos principales son la inversión inicial + mantenimiento, la carga de datos inicial y la operación del delivery; las fases futuras se financian por proyecto, según prioridad.

---

## 6bis. Mejoras V2 del Panel del Dueño (desplegado 11/08/2026) 🆕

La vista ejecutiva **Panel del Dueño** (sección 2.8 / ruta `/panel`) incorporó 4 indicadores nuevos, calculados con datos reales del negocio:

| Indicador | Qué responde | Detalle |
|---|---|---|
| **Top meseros** | ¿Quién vende más en el salón? | Ranking de los 5 meseros con más ventas (sin anuladas): total vendido y ticket promedio por mesero |
| **Rate de anulación** | ¿Cuántas ventas se están anulando? | % de anulaciones con semáforo (verde < 5% · ámbar 5-10% · roja ≥ 10%) + los 5 motivos más frecuentes |
| **Ticket promedio por turno y canal** | ¿Cuándo y dónde se gasta más por pedido? | Ticket por turno (Mañana 06-11:59 / Tarde 12-17:59 / Noche 18-23:59) y por canal (Salón / Delivery) |
| **Delivery: campaña vs sin campaña** | ¿La publicidad paga? | Pedidos, GMV y ticket promedio de pedidos con campaña publicitaria vs sin campaña + desglose por canal (Meta, directo, Google…) |

Todo desplegado y verificado en producción (API + pantalla), con descargas CSV y PDF ampliadas y pruebas automatizadas (17/17 E2E del panel).

---

## 7. Próximos Pasos Sugeridos (opciones de crecimiento)

El sistema ya rinde; estas son opciones de crecimiento para decidir juntos, según prioridad del negocio:

1. **📱 Aplicación móvil** — para que clientes pidan delivery desde una app con su marca (o para que meseros/cocina usen el sistema desde tablet).
2. **🗺️ Más zonas de delivery** — ampliar el radio de reparto (Zárate, Campoy, más distritos) desde el panel, sin desarrollo adicional.
3. **🧾 Facturación electrónica (SUNAT)** — emitir boletas y facturas electrónicas desde el sistema, cumpliendo con la tributación.
4. **💬 Notificaciones por WhatsApp** — avisos automáticos al cliente (pedido confirmado, en camino, entregado) y alertas al local. **⚠️ Ya está desplegado el motor completo (dry-run, 2026-08-11)** — pendiente solo conectar la cuenta Meta (Fase 1 del Plan Integral, ver §8).
5. **🤝 Integraciones con Rappi / PedidosYa** — recibir pedidos de las plataformas directamente en la cocina del sistema.
6. **💳 Pago online directo** — que el cliente pague con tarjeta al momento de ordenar (no solo Yape/Plin/contraentrega).
7. **📊 Panel de indicadores para el dueño** — un resumen ejecutivo (ventas del día, canal más rentable, platos más vendidos) en una sola pantalla.
8. **🏢 Nuevas empresas en la plataforma** — aprovechar el panel global para incorporar otros negocios de la franquicia o terceros, cada uno con sus datos, marca y enlace público propios.

> Todas las opciones se pueden priorizar por **impacto en ventas** y **costo de implementación**. El equipo puede preparar una propuesta con alcance y tiempos para las que el cliente elija.

---

## 8. Plan Integral de Canales — Fases y Cronograma (2026-08-12) 🗓️

> **Requerimiento del cliente (2026-08-12):** sumar el canal telefónico (llamadas de delivery) y consultas con IA, inspirado en soluciones del mercado (benchmark @keno.rdz). Se propone **adopción gradual en 5 fases** — valor rápido primero, lo complejo después — con pago por fase. Detalle completo en `plan-fases-cliente-llamadas-20260812.md` (workspace del agente).

### 8.1 Las 5 fases (qué recibe el cliente y cuándo)

| Fase | Nombre comercial | Qué recibe el cliente | Esfuerzo | Precio (desarrollo único) |
|---|---|---|---|---|
| **F1** | **"WhatsApp en Vivo"** 💬 | Mensajes reales de pedido al cliente (confirmado, en cocina, en camino, entregado, cancelado) + alertas al local + botones "Pedir por WhatsApp"/"Llamar" en el menú y campañas. **🟢 IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — botones en landing/campañas, migración BSUID (0017), 16 tests + E2E en caliente en prod. **Pendiente solo el trámite Meta del cliente** (cuenta Cloud API + 7 plantillas Utility) | 1–2 sem | S/ 1,500 – 2,500 |
| **F2** | **"Central que No Pierde Llamadas"** 📞 | El número del negocio conectado a una central digital: **varias llamadas a la vez sin buzón**, click-to-call, registro y **grabación** de llamadas, y el operador **convierte la llamada en pedido delivery** (mismo flujo: cocina, repartidor, contabilidad, tracking). **🟢 IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — Asterisk en servidor, call-bridge AMI/ARI, panel `/restaurante/central` (WS en vivo + historial + click-to-call + convertir→pedido), 20 tests + E2E en caliente con **descuento real de insumos en kárdex**. **Pendiente solo lo externo del cliente**: trunk SIP real + port-forward UDP 5060/10000-10100 en el router del local | 3–4 sem | S/ 4,000 – 6,500 |
| **F3** | **"Recepcionista IA"** 🤖 | **Una IA contesta el teléfono**, toma el pedido (notas + dirección), **confirma por WhatsApp**, graba y transcribe la llamada, y **transfiere a un humano** si hace falta — el pedido entra solo al sistema. Nunca se pierde una llamada **🟢 IMPLEMENTADA Y DEPLOYADA (2026-08-13)** — agente por voz sobre la Central (F2): transcripción, transferencia con contexto, panel IA; PoC de 2 semanas con llamadas reales pendiente (proveedor de voz IA externo) | 6–8 sem | S/ 8,000 – 12,000 |
| **F4** | **"Franquicia Conectada"** 🏢 | **Cada sucursal con su pantalla** (pedidos en tiempo real) y su atención; el dueño monitorea todo desde un panel. Enrutamiento de llamadas por local | 3–5 sem | S/ 4,000 – 7,000 |
| **F5** | **"Pregúntale al Sistema"** 🤖📊 | El dueño **le pregunta al sistema en lenguaje natural** ("¿qué producto se vendió más hoy por delivery?") y obtiene la respuesta al instante con datos reales. La IA elige la consulta correcta de un catálogo seguro (tool calling); **replicable a todo el ERP** **🟢 IMPLEMENTADA Y DEPLOYADA (2026-08-14)** — chat flotante en el Panel del Dueño con 10 consultas delivery y datos reales | 3–5 sem | S/ 5,000 – 8,000 |
| | **Total** | | **16–24 sem** | **S/ 22,500 – 36,000** |

> **Precios orientativos** (mercado peruano SMB, desarrollo único). No incluyen costos mensuales (WhatsApp Meta, trunk SIP, voz IA — ~S/ 200–600/mes según fases activas) ni hardware (tablets, teléfonos). Pago por fase (hitos), 50% inicio / 50% entrega recomendado.

### 8.2 Cronograma estimado (referencial, desde aprobación del cliente)

| Período (semanas desde aprobación) | Fase en curso | Entregable visible para el cliente |
|---|---|---|
| Semanas 1–2 | **F1 — WhatsApp en Vivo** ✅ **EJECUTADA (2026-08-13)** | El cliente recibe su primer WhatsApp real de pedido (confirmado/en camino/entregado) y el local sus alertas — **motor desplegado y verificado; pendiente solo conectar la cuenta Meta del cliente** |
| Semanas 3–6 | **F2 — Central telefónica** ✅ **EJECUTADA (2026-08-13)** | El número del negocio contesta siempre (sin buzón), las llamadas quedan grabadas y los pedidos telefónicos entran al sistema con tracking — **central desplegada y verificada con llamadas simuladas + conversión a pedido con kárdex; pendiente solo trunk SIP real + port-forward del cliente** |
| Semanas 7–14 | **F3 — Recepcionista IA** ✅ **EJECUTADA (2026-08-13)** | La IA contesta, toma pedidos completos, confirma por WhatsApp y transfiere a humano si es necesario (PoC con llamadas reales en las primeras 2 semanas) — **desplegada en prod; pendiente solo proveedor de voz IA externo (PoC 2 sem con llamadas reales)** |
| Semanas 15–19 | **F4 — Franquicia Conectada** *(si aplica)* | Segunda sucursal (o más) operando con su pantalla, su número y monitoreo central del dueño |
| Semanas 15–19 | **F5 — Pregúntale al Sistema** ✅ **EJECUTADA (2026-08-14)** *(puede ir en paralelo con F4)* | El dueño consulta ventas delivery por chat y recibe respuestas con datos reales; luego se extiende a salón, inventario y contabilidad — **desplegada en prod; pendiente extensión a salón, inventario y contabilidad** |

**Horizonte total:** ~4–6 meses desde la aprobación (según fases contratadas). **Cada fase se entrega, prueba y cobra por separado** — el cliente ve valor desde la semana 1 y decide fase a fase si continúa.

### 8.3 Lo que el cliente ya tiene (no se paga de nuevo) 🎁

Todo el ERP operativo (POS, restaurante, inventario, contabilidad, recetas, delivery online con ROAS, panel del dueño V1+V2+PDF, panel global) **+ el motor WhatsApp desplegado y verificado** (F1) **+ la Central Telefónica desplegada y verificada** (F2: panel en vivo, click-to-call, grabación y conversión llamada→pedido con kárdex). Fases 1, 2, 3 y 5 del plan ya están **implementadas y probadas en producción** — F3 Recepcionista IA (agente por voz, 2026-08-13) y F5 Pregúntale al Sistema (chat IA con datos reales, 2026-08-14) **sin costo adicional para el cliente**; el cliente solo paga por activar lo externo (cuenta Meta, trunk SIP, proveedor de voz IA).

### 8.4 Nota sobre cambios Meta 2026 (consulta del cliente) ✅

Los cambios recientes de Meta/WhatsApp afectan **precios y reglas de uso** (pago por mensaje, plantillas Utility, prohibición de chatbots IA de propósito general, BSUID/usernames), **no la tecnología base**: la integración es agnóstica al proveedor (`Notifier`), usa plantillas transaccionales (el formato más estable), guardará el identificador BSUID desde el día 1 y la IA se diseña como agente de negocio acotado (exigencia Meta). **El código no quedará obsoleto**; detalle en §6 del plan de fases.

---

## 9. Inteligencia Artificial en el Sistema — Propuesta en 3 Bloques (2026-08-13) 🤖

> **Nuevo requerimiento del cliente (2026-08-13):** evaluar IA práctica para el negocio.
> La arquitectura ya está diseñada (capa de agentes `app/core/agents/` con puerto hexagonal
> `BaseSkill` — hoy sin skills concretos, listo para activar). Esta propuesta diferencia
> dos tecnologías que suelen confundirse:

| | **Herramientas (Tool Calling)** | **RAG (Retrieval de documentos)** |
|---|---|---|
| Qué usa | Datos **estructurados** de la BD (PostgreSQL) | Documentos **no estructurados** (PDF, manuales, textos) |
| Cómo responde | La IA elige una función SQL del catálogo y la ejecuta | Busca el fragmento relevante (embeddings + pgvector) y responde con él |
| Exactitud | **Alta (dato real, verificable)** | Media (depende del documento) |
| Ideal para | "¿Cuánto vendió la Zona 1 esta semana?" | "¿Cuál es el procedimiento para X?" |
| Riesgo | Cero SQL libre (catálogo cerrado) | Alucinación si no hay documento |

**Regla del sistema:** datos que ya están en la BD → **siempre tool calling** (exactitud);
solo conocimiento que NO está en la BD → RAG.

### 9.1 Bloque A — "Pregúntale al Sistema" (F5, agente en vivo para el dueño) 📊

- **Qué es**: chat en el panel del dueño — escribe en lenguaje natural y obtiene respuesta
  con datos reales al instante ("¿qué producto se vendió más hoy por delivery?").
- **Cómo**: implementar los skills que el puerto ya tiene diseñado —
  `VentasSkill` (top productos, ventas por zona/canal, embudo, ROAS, ticket promedio)
  e `InventarioSkill` (stock bajo, rotación, sugerencias de compra), vía
  `SkillRegistry` + LLM con function calling (OpenAI/DeepSeek).
- **Seguridad**: catálogo SQL cerrado (la IA no escribe SQL libre), solo lectura,
  permisos por rol/tenant, log de consultas (quién preguntó qué y cuándo).
- **Esfuerzo**: 3–5 sem (MVP delivery) · **S/ 5,000 – 8,000**; extensión por módulo ~S/ 1,500–3,000.
- **Nota para el cliente**: *para KPIs en vivo se usa tool calling, NO RAG* — los datos
  ya están estructurados; RAG no aporta exactitud aquí.

> **ESTADO 2026-08-14: IMPLEMENTADO Y DESPLEGADO en producción como F5** — chat flotante en el Panel del Dueño (`/panel`), 10 consultas delivery del catálogo seguro, fallback determinista sin LLM, E2E en caliente 6/6 con datos reales (respuesta: "Ticket promedio de delivery: S/ 47.92 en 38 pedidos"). Ver spec 08 y §5.3 fila 6.

### 9.2 Bloque B — "Knowledge Agent" (RAG para usuarios del sistema) 📚

- **Qué es**: el equipo pregunta al sistema sobre procedimientos: "¿cómo registro una
  compra con factura?", "¿qué hacer cuando un repartidor no llega?".
- **Cómo**: se cargan los documentos del negocio (manuales, guías, recetas en texto)
  → embeddings (pgvector, ya disponible en PostgreSQL 16) → retrieval + respuesta
  citando la fuente.
- **Frontera clara**: recetas/insumos están en BD → tool calling (ver Bloque A);
  RAG solo para conocimiento NO estructurado. Sin documento → la IA lo dice, no inventa.
- **Esfuerzo**: 2–4 sem (carga inicial + chat en panel + fuentes citadas) · **S/ 3,000 – 5,000**.

### 9.3 Bloque C — Evaluación de outputs de IA (transversal, garantía de calidad) 🧪

> Cierra un vacío identificado: **no existe hoy ningún proceso de evaluación de
> respuestas generadas por modelos de IA** en la documentación del proyecto.

- **Golden queries / test sets por skill**: cada skill (ventas, inventario) trae
  consultas de prueba con respuesta esperada (calculada contra la BD real).
- **Chequeo de exactitud**: toda respuesta con dato numérico se valida contra la BD
  (el dato del reporte = el dato de la query) — el cliente puede verificar.
- **Guardrails**: catálogo SQL cerrado, permisos por tenant, rate limiting, sin escritura.
- **Human-in-the-loop**: respuestas con baja confianza → "no estoy seguro, ¿quieres que
  revise un reporte?" en vez de inventar.
- **Logging**: cada Q&A queda registrado (pregunta, tool usada, respuesta, tiempo) —
  auditable y sirve para mejorar los test sets.
- **Esfuerzo**: integrado en cada bloque (no se cotiza aparte; ~10% del esfuerzo de A/B).

### 9.4 Por qué ya es viable (ventaja de la arquitectura)

- La capa `app/core/agents/base.py` (BaseSkill, SkillResult, AgentContext, SkillRegistry)
  está **diseñada y lista** — es deuda técnica consciente (#8) con puerto hexagonal:
  se implementan los skills sin rediseñar nada.
- PostgreSQL 16 + pgvector ya disponibles (RAG sin infraestructura nueva).
- Multi-tenant, permisos por rol y logging ya existen en el ERP (se reutilizan).
- Precios orientativos; el detalle operativo (LLM mensual ~US$5–20, embeddings) es
  marginal frente al valor.

---

*Bloques A y B son independientes y contratables por separado; el Bloque C acompaña
a cualquiera de ellos. Orden sugerido: A primero (valor inmediato con datos reales),
B después (documentación), C siempre activo.*

---

*Documento vivo elaborado a partir de la documentación técnica del proyecto (especificaciones SDD verificadas contra el sistema y la base de datos de producción). **Este informe se actualiza con cada nuevo requerimiento**: ver sección 5 (Mapa de Requerimientos ↔ Specs). Última actualización: 14/08/2026 (F1 WhatsApp en Vivo ✅, F2 Central Telefónica ✅, F3 Recepcionista IA ✅ y F5 Pregúntale al Sistema ✅ IMPLEMENTADAS Y DEPLOYADAS — Plan Integral de Canales: WhatsApp en Vivo, Central telefónica, Recepcionista IA, Franquicia Conectada (propuesta), Pregúntale al Sistema; ver §8; + §9 Propuesta IA en 3 Bloques: Bloque A ya implementado como F5).*
