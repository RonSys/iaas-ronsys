# Deuda Técnica — Fase 0

> Archivo de seguimiento para deudas técnicas identificadas durante la Fase 0.
> Cada deuda tiene asignada una versión target donde se planea resolverla.

---

## 🗺️ Roadmap: Fases → Versión 1.0

| Fase | Enfoque | Versión |
|:----:|---------|:-------:|
| **Fase 0** | MVP Restaurante + Ferretería Básico (3 sprints) | v0.x (actual) |
| **Fase 1** | Corrección Hexagonal + Persistencia Config + Reorg Frontend | v0.x |
| **Fase 2** | Cocina/Producción + Delivery Avanzado + Compras | v0.x |
| **Fase 3** | Inventario Completo + Finanzas Operativas | v0.x |
| **Fase 4** | Reportes ERP + Config Completa + Infraestructura | v0.x |
| **🎯 v1.0** | **Todas las Fases completadas** | **🚀 Release** |

> ⚠️ La versión **1.0** se alcanza solo al completar las Fases 0, 1, 2, 3 y 4.
> Las deudas de Fase 0 pueden resolverse en versiones **1.1, 1.2, 2.x** (post-1.0)
> o durante el desarrollo de las Fases 1-4 si el análisis lo recomienda.

---

## 📋 Registro de Deudas

| ID | Deuda | Severidad | Versión Target | Estado |
|----|-------|:---------:|:--------------:|:------:|
| DT-F0-001 | Bottom Sheet de modifiers se cierra al tocar en tablets táctiles. Fix parcial: `data-vaul-no-drag` en v5. Pendiente validación en tablet real. | 🟡 Media | v1.2 | 🟡 Pendiente validación |
| DT-F0-002 | Kanban de cocina muestra todos los items del pedido (incluyendo gaseosas, productos fríos, etc.). Debe filtrar solo platos que se preparan en cocina. | 🟢 Baja | v1.2 | 📝 Pendiente |
| DT-F0-003 | Validar creación de items de menú contra el motor contable (asociación a cuentas contables). Aprovechar motor contable ya implementado. | 🟢 Baja | v1.2 | 📝 Pendiente |
| DT-F0-004 | Cancelar comanda: notificar al mesero que la generó + motivo de cancelación con opciones predefinidas. | 🟡 Media | ~~v1.2~~ → **Fase 2** 🔼 | 📝 Pendiente |
| DT-F0-005 | Módulo de Pérdidas: registrar productos malogrados, actualizar stock, calcular platos disponibles según recetas (MP + suministros). | 🟡 Media | v2.x | 📝 Pendiente |
| DT-F0-006 | Promociones: validar que botón "Crear" funcione correctamente y restringir a solo administradores. | 🟡 Media | ~~v1.9~~ → **Fase 1** 🔼 | 📝 Pendiente |
| DT-F0-007 | Promociones: validación general del módulo (aplicación automática al cerrar cuenta, mejor opción para el cliente). | 🟢 Baja | v1.2 | 📝 Pendiente |
| DT-F0-008 | Evolución cocina: niveles de cocineros (jefe, junior, encargado, habilitador) + comandos de voz IA para cocina. | 🟢 Baja | v3 / v3.5 | 📝 Pendiente |
| DT-F0-009 | Módulo Ferretería: validar asociación categorías ↔ productos, precios mayorista/detal, seriales/trazabilidad, ventas. Pendiente análisis completo. | 🟡 Media | v0.9 / v1.1 | 📝 Pendiente análisis |

---

### DT-F0-001 — Bottom Sheet en tablets táctiles

**Problema:** Al seleccionar un modifier en el bottom sheet desde una tablet, vaul interpreta el micro-movimiento táctil como swipe de cierre.

**Fix aplicado en v5:** `data-vaul-no-drag` en elementos interactivos. Pendiente validación en tablet física.

**Archivo:** `apps/web/src/components/restaurante/ModifierBottomSheet.tsx`

---

### DT-F0-002 — Filtro en Kanban de cocina

**Problema:** La ventana de cocina (Kanban) muestra todos los items del pedido, incluyendo bebidas/gaseosas y productos fríos que no requieren preparación. Debería filtrar solo items de categorías relevantes para cocina.

**Propuesta:** Agregar flag `requires_preparation` en modelo de menú. Kanban filtra por ese flag.

**Archivo relacionado:** `KitchenKanban.tsx`, modelo `MenuItem`

---

### DT-F0-003 — Items de menú vs Motor Contable

**Problema:** Al crear/modificar items del menú, no hay validación de cuentas contables.

**Propuesta:** Aprovechar módulo contable existente (`simulador-financiero/docs/03-logica-contable.md`) para validar cuentas por item.

**Archivos relacionados:** `MenuPage.tsx`, modelos contables

---

### DT-F0-004 — Cancelar comanda + notificar mesero

**Problema:** Cuando un cocinero cancela una comanda (Pendiente o Preparando), el sistema debe:
- Notificar al mesero que generó la comanda
- Incluir el motivo de cancelación
- Tener opciones predefinidas de motivo (no solo texto libre)

**Flujo actual:**
1. En comanda Pendiente o Preparando, presionar "🗑️"
2. Se abre modal para ingresar motivo
3. Confirmar → comanda se marca como cancelada
4. 🔄 Pantalla de cocina se actualiza cada 10s (hoy 30s)

**Lo que falta:**
- Comunicación al mesero que generó la comanda (quién, qué, por qué se rechazó)
- Motivos predefinidos seleccionables
- La pantalla de cocina se actualiza cada 10s automáticamente

**Archivos relacionados:** `KitchenKanban.tsx`, WebSocket manager

---

### DT-F0-005 — Módulo de Pérdidas (productos malogrados)

**Problema:** No hay registro de productos que se malogran/desperdician en cocina. Esto impide:
- Tener stock actualizado preciso
- Calcular cantidad de platos disponibles según recetas
- Control de mermas

**Propuesta de arquitectura:**

**Materia Prima (MP):** Ej: cantidad de pescado disponible.
**Suministros:** Sal, pimienta, aceite — siempre deben estar en stock mínimo.
**Recetas:** Cada plato define su MP principal + cantidades de suministros.

**Cálculo de platos disponibles:**
Se realiza en función de la **MP principal** del producto. Si varios platos comparten la misma MP (ej: pescado usado en ceviche, jalea, sudado), se puede calcular cuántos platos de cada tipo se pueden preparar con el stock actual.

**A implementar:**
- Modelo de recetas (ingredientes + cantidades por plato)
- Registro de pérdidas (qué, cuánto, por qué, quién registró)
- Stock ajustado por pérdidas
- Cálculo de platos disponibles basado en MP principal

**Archivos relacionados:** Nuevos modelos + servicios

---

### DT-F0-006 — Promociones: botón "Crear" + roles

**Problema:** El botón "Crear" del módulo de promociones no refleja acción alguna al presionarlo. Además, cualquier usuario puede crear promociones — debe ser solo administradores.

**Propuesta:**
- Validar que el endpoint `POST /promotions` y el formulario frontend funcionen correctamente
- Restringir creación a rol `admin` (backend + frontend)
- Las promociones se aplican automáticamente al cerrar la cuenta, el sistema elige la mejor opción para el cliente

**Archivos relacionados:** `PromotionsPage.tsx`, `restaurant.py` (routers)

---

### DT-F0-007 — Promociones: validación general

**Problema:** Validar que el módulo de promociones funcione correctamente:
- ¿Cómo funcionan las promociones? Se aplican automáticamente al cerrar cuenta
- El sistema elige la mejor opción para el cliente
- Verificar que la lógica de aplicación automática esté correcta

**Archivos relacionados:** `PromotionsPage.tsx`, `restaurant.py`

---

### DT-F0-008 — Evolución cocina: niveles + IA por voz

**Problema:** El sistema de cocina no tiene diferenciación de roles ni interacción por voz.

**Futuro (v3):**
- Comandos de voz IA para que el cocinero interactúe con el sistema (manos ocupadas)

**Futuro (v3.5):**
- Niveles de cocineros:
  - Cocinero jefe
  - Cocinero junior
  - Encargado de cocina
  - Habilitador
  - (y otros roles por definir)

**Archivos relacionados:** Por definir

---

### DT-F0-009 — Módulo Ferretería: validación completa

**Problema:** El módulo Ferretería tiene funcionalidades documentadas pero no validadas contra la implementación real:

**Categorías ↔ Productos:**
- Cada producto puede tener una categoría asignada
- Al crear una categoría, muestra contador de productos asociados (ej: "Fierros — 0 producto(s)")
- La asignación se realiza al crear o editar un producto desde Ventas / POS
- No hay página dedicada a "Productos" (CRUD completo pendiente)
- Soporte para jerarquía de categorías (subcategorías) pendiente

**Ventas Mayorista / Detal:**
- Productos con dos tipos de precio: minorista (retail) y mayorista (wholesale)
- Cantidad mínima para aplicar precio mayorista
- El sistema debe aplicar el precio automáticamente según cantidad vendida
- Validar flujo completo: creación de producto con precios → venta minorista → venta mayorista

**Seriales / Trazabilidad:**
- Productos con control por números de serie
- Activar seriales en un producto (flag `has_serial`)
- Registrar seriales en inventario (número, fecha compra, precio costo)
- Stock calculado automáticamente como cantidad de seriales disponibles
- Vender productos con serial (modal de selección de seriales específicos)
- Anular venta → seriales vuelven a "Disponible"
- Consultar trazabilidad: producto → venta, venta → producto, garantía
- Productos SIN serial: stock por cantidad total (comportamiento tradicional)

**Versión target:** v0.9 / v1.1

**Archivos relacionados:** `CategoriesPage.tsx`, `SalesNew.tsx`, `Kardex.tsx`, modelos de producto/serial

---

*Generado: 2026-05-15. Actualizar al resolver cada deuda.*
