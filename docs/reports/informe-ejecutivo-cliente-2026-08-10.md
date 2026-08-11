# 📊 Informe Ejecutivo — Sistema de Gestión El Segoviano

- **Fecha:** 10 de agosto de 2026
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
- La funcionalidad de "asistentes inteligentes" dentro del sistema está diseñada pero **no operativa**.
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
| 2 | **💬 Notificaciones WhatsApp (Fase B del Delivery)** — avisos automáticos al cliente (confirmado, en cocina, en camino, entregado, cancelado) y alertas al local. Motor de eventos (colas RabbitMQ) desplegado en producción y verificado en vivo el 2026-08-11; envío real requiere cuenta WhatsApp Business API (Meta) — plan en `plan-cuenta-meta-whatsapp.md` | 🟠 Media | `docs/specs/03-delivery/03-spec-delivery-dark-kitchen-v0.1.md` §7 | 🟡 **MOTOR DESPLEGADO (2026-08-11) — envío real pendiente de cuenta Meta** — backend completo (Notifier MetaCloud/DryRun, publicador RabbitMQ fire-and-forget, worker con reintentos + DLQ), QA 8/8 CA, verificado en vivo: checkout→confirmed+new_order, transición→status_changed, cancelación→cancelled (todo dry-run, cero HTTP). Config: `companies.settings.whatsapp` | 2026-08-11 |

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
4. **💬 Notificaciones por WhatsApp** — avisos automáticos al cliente (pedido confirmado, en camino, entregado) y alertas al local.
5. **🤝 Integraciones con Rappi / PedidosYa** — recibir pedidos de las plataformas directamente en la cocina del sistema.
6. **💳 Pago online directo** — que el cliente pague con tarjeta al momento de ordenar (no solo Yape/Plin/contraentrega).
7. **📊 Panel de indicadores para el dueño** — un resumen ejecutivo (ventas del día, canal más rentable, platos más vendidos) en una sola pantalla.
8. **🏢 Nuevas empresas en la plataforma** — aprovechar el panel global para incorporar otros negocios de la franquicia o terceros, cada uno con sus datos, marca y enlace público propios.

> Todas las opciones se pueden priorizar por **impacto en ventas** y **costo de implementación**. El equipo puede preparar una propuesta con alcance y tiempos para las que el cliente elija.

---

*Documento vivo elaborado a partir de la documentación técnica del proyecto (especificaciones SDD verificadas contra el sistema y la base de datos de producción el 10/08/2026). **Este informe se actualiza con cada nuevo requerimiento**: ver sección 5 (Mapa de Requerimientos ↔ Specs). Última actualización: 11/08/2026 (Mejoras V2 Panel del Dueño — iteración 3, Spec 04 §3.2-V2).*
