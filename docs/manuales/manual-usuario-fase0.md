# Manual de Usuario — IaaS-RonSys (Fase 0)

> **Versión:** Fase 0 — MVP Restaurante + Ferretería Básico  
> **Fecha:** 2026-05-14  
> **Producto:** IaaS-RonSys ERP by **El Segoviano** 🐟  
> **URL:** http://localhost:80

---

## 1. Introducción

**IaaS-RonSys** es un sistema ERP pensado para la franquicia **"El Segoviano"**. Esta primera fase (Fase 0) incluye los módulos de **Restaurante** (salones, menú digital, cocina, take away y promociones) y **Ferretería/Inventario** (ventas al por mayor/detal, categorías y trazabilidad por seriales).

> 🎯 **¿Para quién es este manual?**  
> Para meseros, cocineros, cajeros, administradores y dueños que operan el día a día del negocio. Está escrito en lenguaje sencillo, sin jerga técnica.

> 🏷️ **Leyenda de tipos de negocio:**  
> 🐟 = Solo disponible para **Restaurante**  
> 🏪 = Solo disponible para **Ferretería**  
> ✅ = Disponible para **ambos tipos**

### 1.1 Métricas de Éxito — ¿Qué puede hacer el cliente?

> ✅ **Fase 0:** Cliente puede abrir una mesa, tomar pedido, enviar a cocina, cerrar cuenta (con promociones); realizar ventas al por mayor/detal en ferretería; registrar productos con seriales (trazabilidad individual) y productos sin serial (solo cantidad); el campo `barcode` existe en la base de datos pero no se utiliza en la interfaz.
>
> 🏷️ **HU-F0-016 — Modificadores:** Cliente puede personalizar cualquier plato del menú desde un bottom sheet deslizable al hacer clic en un ítem con modificadores; cada modificador puede ser gratuito ("Sin cebolla", "Término medio") o con costo adicional ("Huevo frito +S/3.00", "Con conchas +S/5.00"); el precio total se recalcula automáticamente al seleccionar modificadores; el sistema impide exceder el límite máximo de cada modificador (ej. máximo 3 huevos fritos por plato); los modificadores funcionan tanto en **Pedidos en Mesa** como en **Take Away**; el pedido final muestra cada combinación plato+modificadores en su propia fila con el precio ajustado.

---

## 2. Acceso al Sistema

### 2.0 ¿Qué tipo de negocio eres?

El sistema se comporta diferente según el tipo de empresa. Antes de empezar, identifica con qué credenciales debes entrar:

| Si eres... | Usa estas credenciales | Y verás... |
|------------|----------------------|------------|
| 🐟 **Restaurante** | `admin@elsegoviano.pe` / `admin123` | Mesas, menú, cocina, takeaway, promos |
| 🏪 **Ferretería** | `ferretero@elsegoviano.pe` / `ferreteria123` | Categorías, productos, ventas mayor/detal |

> ⚠️ **Importante:** Para cambiar de Restaurante a Ferretería (o viceversa) debes **cerrar sesión** e iniciar sesión con el otro usuario. Cada empresa tiene sus datos completamente separados (son tenants distintos).

### 2.1 Ingresar

1. Abrí tu navegador (Chrome, Firefox, Edge) en la dirección que te dé el administrador.  
   *Ejemplo:* `http://localhost:80` o `http://192.168.1.35`
2. Verás la pantalla de inicio de sesión.
3. Ingresá tu **correo electrónico** y **contraseña**.
4. Presioná **"Iniciar Sesión"**.

| Campo | Ejemplo |
|-------|---------|
| 📧 Correo | `admin@elsegoviano.pe` |
| 🔐 Contraseña | `admin123` |

> ℹ️ Si olvidaste tu contraseña, contactá al administrador del sistema.

### 2.2 Navegación

Una vez dentro, verás una **barra lateral izquierda** (sidebar) con todas las secciones del sistema agrupadas por módulos:

| Sección | Ícono | Contenido |
|---------|:-----:|-----------|
| 🏗️ Proyecto de Inversión | 📊 | Dashboard, Setup, Simulador, Reportes |
| 🧾 Ventas / POS | 💳 | Caja, Facturación, Historial |
| 🍽️ Restaurante | 🪑 | Mesas, Menú, Cocina, Take Away, Promociones |
| 📦 Inventario | 📊 | Kárdex, Categorías |
| 💰 Finanzas | 💵 | Flujo de Caja |
| ⚙️ Configuración | 🎨 | Marca / Branding |

> 💡 **Tip:** Las secciones se pueden expandir o colapsar haciendo clic en el nombre del módulo. El sistema recuerda tu preferencia.
>
> 💡 **Tip:** Si tu negocio **no es restaurante** (ej. ferretería), la sección 🍽️ Restaurante **no se mostrará** automáticamente.

### 2.3 Cerrar Sesión

1. En la **parte inferior** de la barra lateral, siempre visible sin importar el scroll, encontrás el botón **"🚪 Cerrar Sesión"**.
2. Hacé clic y se cerrará tu sesión, volviendo a la pantalla de inicio.

---

## 3. 🐟 Módulo Restaurante

> Este módulo solo está disponible si tu negocio está configurado como **Restaurante** (`business_type = 'restaurant'`).  
> **Credenciales para probar:** `admin@elsegoviano.pe` / `admin123`

### 3.1 Mapa de Mesas

**📍 Ruta:** Sidebar → Restaurante → Mesas (o `/restaurante/mesas`)

El mapa de mesas te da una vista de todo el salón. Cada mesa aparece como una tarjeta de color según su estado:

| Color | Estado | Significado |
|:-----:|--------|-------------|
| 🟢 Verde | **Libre** | Disponible para nuevos clientes |
| 🔴 Rojo | **Ocupada** | Clientes sentados, pedido en curso |
| 🟡 Amarillo | **Reservada** | Apartada para clientes. Presioná **📅 Reservar** desde una mesa libre |
| ⚪ Gris | **Limpieza** | En mantenimiento, no disponible |

#### Ver mesas disponibles

Al cargar la página, verás todas las mesas con su **número**, **capacidad** (cuántas personas entran) y **sección** (Terraza, Salón Principal, VIP).

En la parte superior se muestra un resumen: *"14 mesas · 8 libres"*.

#### Abrir una mesa (recibir clientes)

1. Hacé clic en la mesa que esté en estado **🟢 Libre**.
2. Se abre una ventana modal donde debés ingresar:
   - **N° de Comensales:** cuántas personas son (no puede exceder la capacidad de la mesa).
   - **Nombre del Mesero:** se autocompleta automáticamente con tu **nombre completo** (obtenido de tu sesión). Podés:
     - ✅ Usarlo tal cual (es lo más común — solo presioná **"Abrir Mesa"**)
     - 🔽 Elegir **"Otro…"** del desplegable y escribir manualmente otro nombre (ej. si estás cubriendo para un compañero)
3. Presioná **"Abrir Mesa"**.
4. ✅ La mesa cambiará a color **🔴 Ocupada**.

> 💡 **¿Cómo sabe el sistema tu nombre?** Al iniciar sesión, el sistema obtiene tus datos (nombre, email, rol) del backend. El campo "Nombre del Mesero" se completa automáticamente para que no tengas que escribirlo cada vez que abrís una mesa.

#### Reservar una mesa (para cuando llegarán clientes)

1. Hacé clic en una mesa **🟢 Libre**.
2. En el modal, presioná el botón **"📅 Reservar"**.
3. ✅ La mesa pasa a color **🟡 Amarillo** (Reservada).
4. Los demás meseros verán que la mesa está apartada.

> 💡 La mesa reservada no puede recibir pedidos hasta que la liberes o la ocupes.

#### Liberar una reserva

1. Hacé clic en la mesa **🟡 Reservada**.
2. Presioná **"🔓 Liberar Reserva"**.
3. ✅ La mesa vuelve a **🟢 Libre**.

> También podés abrir una mesa reservada directamente con **"Abrir Mesa"** si los clientes ya llegaron — la reserva se cancela automáticamente.

#### Ver info de una mesa ocupada

Pasá el mouse sobre una mesa roja para ver un tooltip con:
- 👥 N° de comensales
- 👤 Mesero asignado
- 🕐 Hora de apertura
- 💰 Total acumulado (provisional)

#### Editar o eliminar una mesa

1. Hacé clic en una mesa libre → se abre el modal.
2. Verás botones:
   - **✏️ Editar:** cambiá el número, capacidad o sección.
   - **🗑️ Eliminar:** eliminá la mesa (solo si está libre, con confirmación).

#### Crear una nueva mesa

1. Presioná el botón **"➕ Nueva Mesa"** (arriba a la derecha).
2. Completá:
   - **Número de Mesa:** entero positivo (ej. `15`).
   - **Capacidad:** 2, 4, 6, 8, 10 o 12 personas.
   - **Sección:** opcional (ej. `Terraza`, `VIP`).
3. Presioná **"Crear Mesa"**.
4. ✅ La nueva mesa aparecerá en el mapa.

> 🔄 El mapa se actualiza automáticamente cada **30 segundos**, así que si otro mesero cambia una mesa, lo verás reflejado sin recargar la página.

---

### 3.2 Menú Digital

**📍 Ruta:** Sidebar → Restaurante → Menú (o `/restaurante/menu`)

Aquí ves todos los **platos, bebidas, postres y combos** disponibles, organizados por categoría (ej. "Platos", "Bebidas", "Postres").

#### Ver el menú

- Cada ítem muestra: **nombre**, **descripción** (si tiene), **precio**, y si tiene **modificadores**.
- Si un ítem está inactivo, se ve en gris con la etiqueta **"Agotado"**.
- Usá el buscador 🔍 para filtrar por nombre o categoría al instante.

#### ¿Qué son los modificadores?

Los **modificadores** son opciones de personalización que el cliente puede agregar a un plato. Aparecen como un distintivo 🏷️ en la tarjeta del ítem. Al hacer clic en un plato que tiene modificadores, se abre un **selector con tres tipos de opciones**:

| Tipo | Cómo se ve | Ejemplo |
|------|-----------|---------|
| 🔢 **Cuantificable** | Botones **− / +** para elegir cantidad | "Huevo frito +S/3.00" — se puede pedir 1, 2 o hasta 3 por plato |
| ☑️ **Opción sí/no** | Un simple **checkbox** para activar/desactivar | "Sin cebolla" — va o no va |
| 🔘 **Grupo excluyente** | **Botones de radio** — solo uno del grupo | "Término de cocción" — medio, 3/4 o bien cocido (solo uno) |

> 💡 **Reglas:**
> - Los modificadores **cuantificables** tienen un límite máximo (`max_select`). Ej: "Huevo frito" máximo 3. Si intentás más, el sistema te avisa.
> - Los modificadores **sí/no** son binarios: están o no están.
> - Los **grupos excluyentes** permiten elegir solo una opción del grupo (ej: no podés pedir término medio Y 3/4 al mismo tiempo).
> - El **precio total se recalcula automáticamente** conforme seleccionás modificadores.
> - Los modificadores funcionan tanto en **Pedidos en Mesa** como en **Take Away**.

#### Agregar un ítem al menú (administradores)

1. Presioná **"+ Nuevo Ítem"** (arriba a la derecha).
2. Completá:
   - **Nombre:** ej. "Ceviche Mixto".
   - **Descripción:** opcional.
   - **Categoría:** ej. "Platos", "Bebidas".
   - **Tipo:** Plato, Bebida, Postre o Combo.
   - **Precio:** cuánto se cobra al cliente.
   - **Costo:** cuánto cuesta prepararlo (opcional, para márgenes).
3. Presioná **"Crear"**.

#### Editar o desactivar un ítem

- **Editar:** hacé clic en "Editar" al costado del ítem para modificar nombre, precio, etc.
- **Desactivar:** usá el interruptor (toggle) al costado del ítem. Si está apagado, el plato aparece como "Agotado" y no se puede pedir.

---

### 3.3 Tomar Pedido

El proceso de tomar pedido ocurre desde el **Mapa de Mesas**:

1. Hacé clic en una **mesa ocupada** 🔴.
2. Se abre el modal con los datos de la mesa (comensales, mesero, capacidad).
3. Presioná el botón **"🍽️ Tomar Pedido"**.
4. Se despliega el **menú completo** con todos los platos activos, agrupados por categoría (Entradas, Platos de Fondo, Bebidas, Postres).
5. Cada ítem del menú muestra:
   - 🏷️ **Nombre** del plato
   - 💰 **Precio** (ej. S/ 28.00)
   - Un botón **"➕"** para agregarlo al pedido

> 💡 Si el ítem tiene modificadores 🏷️, se abre un **bottom sheet** (panel deslizable) con tres tipos de opciones:
> - 🔢 **Cuantificables** (ej: Huevo frito +S/3.00): botones −/+ para elegir hasta el máximo.
> - ☑️ **Sí/no** (ej: Sin cebolla): checkbox para activar/desactivar.
> - 🔘 **Grupo excluyente** (ej: Término de cocción): radio buttons, solo uno.
> 
> El precio se actualiza en tiempo real. Al confirmar, el modificador se suma automáticamente al ítem.

#### Ticket actual (📋 Pedido Actual)

Arriba del menú se muestra el **ticket** del pedido con los items ya agregados. Cada fila muestra:

```
⊖ 2 ⊕ Ceviche Clásico               S/ 56.00
⊖ 1 ⊕ Lomo Saltado (Huevo frito)    S/ 38.00
⊖ 1 ⊕ Chicha Morada                  S/  4.00
─────────────────────────────────────────────
TOTAL                                 S/ 98.00
```

- **⊖ / ⊕** — Aumentá o disminuí la cantidad de cada producto
- Si tienen **modificadores**, cada variante (ej. "Lomo Saltado" vs "Lomo Saltado + Huevo frito") aparece en **su propia fila** con su precio ajustado
- **TOTAL** suma todos los items incluyendo modificadores

1. Revisá el ticket con los items agregados.
2. Presioná el botón **"📨 Enviar a Cocina"**.
3. ✅ Aparece un mensaje de confirmación verde *"Comanda enviada ✅"*.
4. En la cocina, la comanda aparece automáticamente en la columna **"⏳ Pendientes"** del Kanban.
5. El menú sigue disponible para agregar más items si los clientes piden después.

---

### 3.4 Enviar a Cocina (Kanban)

**📍 Ruta:** Sidebar → Restaurante → Cocina (o `/restaurante/cocina`)

Esta es la **pantalla del cocinero**. Muestra las comandas en formato **Kanban** (columnas que se mueven):

| Columna | Ícono | Significado |
|---------|:-----:|-------------|
| ⏳ Pendientes | ⏳ | Comandas que esperan ser preparadas |
| 🔥 Preparando | 🔥 | Platos que se están cocinando |
| ✅ Listos | ✅ | Platos terminados listos para servir |
| 📤 Entregados | 📤 | Platos que ya fueron al salón |

#### Flujo del cocinero

1. **Nueva comanda:** aparece en **"Pendientes"** automáticamente (sin recargar la página).
2. **Iniciar preparación:** presioná **"🔥 Iniciar"** → la comanda se mueve a "Preparando".
3. **Marcar como listo:** cuando el plato está terminado, presioná **"✅ Listo"** → pasa a "Listos".
4. **Entregar:** el mesero presiona **"📤 Entregado"** cuando lleva el plato al cliente.

#### Control de tiempos

Cada comanda muestra **minutos transcurridos** desde que se pidió:

- ⚠️ **Naranja:** más de 15 minutos — aviso de demora.
- 🔴 **Rojo:** más de 30 minutos — tiempo crítico.

#### Cancelar una comanda

1. En una comanda Pendiente o Preparando, presioná **"🗑️"**.
2. Se abre un modal para ingresar el **motivo de cancelación**.
3. Confirmá → la comanda se marca como cancelada.

> 🔄 La pantalla de cocina se actualiza **cada 10 segundos** automáticamente.

---

### 3.5 💰 Cerrar Cuenta con Promociones

#### Cerrar una mesa (liberar)

Cuando los clientes terminan de comer y el cocinero entregó todo, el mesero debe cerrar la mesa:

1. Desde el **Mapa de Mesas**, seleccioná la mesa **🔴 Ocupada**.
2. En el modal, primero presioná **"📋 Cerrar Mesa"** (azul).
   - El sistema genera la cuenta con todos los items consumidos.
3. Luego presioná **"💰 Pagar"** (verde).
   - El sistema procesa el pago.
4. ✅ La mesa vuelve a estado **🟢 Libre** y desaparece de la cocina.

> 💡 Si hay promociones aplicables (combos, descuentos), se aplican automáticamente al cerrar la mesa. El sistema elige la mejor opción.

#### ¿Cómo funcionan las promociones?

Las promociones se aplican **automáticamente** al cerrar la cuenta. No necesitás calcular nada. El sistema elige la mejor opción para el cliente.

| Tipo de Promoción | Cómo funciona | Ejemplo |
|-------------------|---------------|---------|
| 🎁 **Combo** | Si los items del combo están en el pedido, se cobra el precio especial. | Ceviche + Causa = S/ 45 en vez de S/ 53 |
| 📉 **Descuento %** | Descuento porcentual sobre el subtotal. | 15% de descuento en toda la cuenta |
| 💵 **Descuento Fijo** | Descuento en soles, si se supera un mínimo. | S/ 10 de descuento en compras > S/ 50 |
| 2️⃣×1️⃣ **2x1 (BOGOF)** | Por cada 2 unidades del mismo producto, una sale gratis. | 2 cervezas → pagás 1 |

> ℹ️ **Regla:** Si hay varias promociones aplicables, el sistema aplica la **de mayor beneficio para el cliente**. No se acumulan.

#### Administrar promociones

**📍 Ruta:** Sidebar → Restaurante → Promociones (o `/restaurante/promociones`)

1. Presioná **"+ Nueva Promoción"**.
2. Completá:
   - **Nombre:** ej. "Happy Hour".
   - **Descripción:** opcional.
   - **Tipo:** Combo, Descuento %, Descuento Fijo o 2x1.
   - **Valor:** porcentaje o monto en soles.
   - **Vigencia:** fecha desde / fecha hasta.
3. Presioná **"Crear"**.
4. Para desactivar una promoción, presioná el botón **"Desactivar"** al costado de la promoción.

---

### 3.6 Takeaway (Pedidos para llevar)

**📍 Ruta:** Sidebar → Restaurante → Take Away (o `/restaurante/takeaway`)

#### Crear un pedido para llevar

1. En la pestaña **"+ Nuevo Pedido"**:
   - **Seleccioná items del menú:** buscá o navegá por categoría, hacé clic para agregar al carrito.
   - Si el ítem tiene **modificadores** 🏷️, se abre un **bottom sheet** con las opciones:
     - Marcá los modificadores que quiere el cliente (ej. "Sin cebolla", "Huevo frito +S/3.00").
     - El **total se actualiza automáticamente** conforme seleccionás.
     - Cada modificador respeta su **límite máximo** (no podés excederlo).
     - Presioná **"Agregar"** para confirmar.
   - **Ajustá cantidades:** usá los campos numéricos ⊕/⊖ en el carrito.
   - Completá los **datos del cliente**:
     - **Nombre * (obligatorio):** ej. "María López".
     - **Teléfono:** ej. "999 888 777".
     - **Hora de Recojo:** cuándo pasará el cliente.
     - **Notas:** ej. "Llamar antes de entregar".
   - Revisá el **total** en el resumen (incluye el costo de los modificadores).
   - Presioná **"🥡 Confirmar Pedido"**.

2. ✅ Aparece el mensaje *"✅ Pedido Take Away registrado"*.

> 💡 **Ejemplo:** Si pedís un **Ceviche Clásico (S/28.00) + Con conchas (+S/5.00)** y un **Lomo Saltado (S/35.00) + Huevo frito (+S/3.00)**, el total será **S/71.00** (28+5 + 35+3). El sistema calcula todo automáticamente.

#### Ver pedidos activos

1. Cambiá a la pestaña **"📋 Pedidos"**.
2. Verás la lista de todos los pedidos take away con su estado:

| Estado | Color | Significado |
|--------|:-----:|-------------|
| Pendiente | 🟡 Amarillo | Esperando ser preparado |
| Preparando | 🔵 Azul | Se está cocinando |
| Listo | 🟢 Verde | Ya se puede recoger |
| Recogido | ⚪ Gris | Cliente ya lo retiró |
| Cancelado | 🔴 Rojo | Pedido anulado |

---

## 4. 🏪 Módulo Ferretería

> Este módulo está disponible solo para negocios configurados como **Ferretería** (`business_type = 'hardware'`).  
> **Credenciales para probar:** `ferretero@elsegoviano.pe` / `ferreteria123`

### 4.1 Categorías de Productos

**📍 Ruta:** Sidebar → Inventario → Categorías (o `/inventario/categorias`)

Las categorías organizan tus productos en grupos lógicos: "Fierros", "Cemento", "Pinturas", "Herramientas", etc.

#### Crear una categoría

1. Presioná **"+ Nueva Categoría"**.
2. Ingresá:
   - **Nombre * (obligatorio):** ej. "Fierros".
   - **Descripción:** opcional, ej. "Varillas, alambres y perfiles metálicos".
3. Presioná **"Crear"**.
4. ✅ La nueva categoría aparece en la lista con el contador de productos asignados.

#### Editar o eliminar una categoría

- **Editar:** presioná "Editar" al costado → cambiá nombre o descripción.
- **Eliminar:** presioná "Eliminar".
  - ❌ **No se puede eliminar** si tiene productos asignados. El sistema muestra el mensaje *"Categoría con productos asignados"*.

#### ¿Cómo se asocian las categorías con los productos?

Cada producto puede tener una **categoría asignada**. Al crear una categoría, esta muestra cuántos productos tiene asociados (ej: "Fierros — 0 producto(s)").

La asignación se realiza al **crear o editar un producto** desde Ventas / POS. Cuando se registra un producto nuevo, se selecciona su categoría. El contador se actualiza automáticamente.

> 💡 Actualmente no hay una página dedicada a "Productos". Los productos se crean desde el flujo de **Ventas / POS → Facturación**. En futuras versiones habrá una página de gestión de productos con CRUD completo.

> 💡 Las categorías ya tienen soporte para **jerarquía** (subcategorías), disponible en futuras versiones.

### 4.2 🏪 Ventas al por Mayor y Detal

**📍 Ruta:** Sidebar → Ventas / POS → Facturación (o `/ventas/nueva`)

Podés vender productos con **dos tipos de precio**:

| Tipo de Precio | Cuándo se aplica |
|----------------|------------------|
| 🏪 **Minorista (retail)** | Venta al detal, para clientes que compran pocas unidades |
| 🏭 **Mayorista (wholesale)** | Venta al por mayor, cuando se supera la cantidad mínima |

#### ¿Cómo funciona?

Cuando creás un producto (desde Kárdex), podés configurar:

- **Precio Minorista:** el precio de lista normal.
- **Precio Mayorista:** precio especial para compras grandes.
- **Cantidad Mínima Mayorista:** cuántas unidades debe comprar el cliente para acceder al precio mayorista (ej. 10 unidades).

**Ejemplo práctico:**

| Producto | Precio Minorista | Precio Mayorista | Cant. Mínima |
|----------|:----------------:|:-----------------:|:------------:|
| Cemento Sol (bolsa) | S/ 28.50 | S/ 25.00 | 10 bolsas |

- Cliente compra **5 bolsas** → se cobra a **S/ 28.50** c/u (precio minorista).
- Cliente compra **12 bolsas** → se cobra a **S/ 25.00** c/u (precio mayorista).

> ℹ️ El sistema **aplica el precio automáticamente** según la cantidad vendida. No necesitás hacer cuentas.

#### Registrar una venta

1. Desde **Facturación**, completá el formulario:
   - **Cliente:** seleccioná o creá un cliente.
   - **Productos:** buscá productos por nombre o código de barras.
   - **Cantidad:** ingresá cuántas unidades.
   - El sistema calcula automáticamente si aplica precio mayorista.
2. Revisá los totales (subtotal, IGV, total final).
3. Seleccioná el **método de pago** (efectivo, tarjeta, etc.).
4. Presioná **"Registrar Venta"**.

---

### 4.3 🏪 Productos con Seriales (Trazabilidad Individual)

**📍 Ruta:** Sidebar → Inventario → Kárdex

Para productos que necesitan **trazabilidad individual** (ej. herramientas eléctricas, motores, equipos), podés activar el control por **números de serie**.

#### ¿Qué productos necesitan seriales?

Cualquier producto donde quieras saber **exactamente qué unidad** se vendió a cada cliente:
- 🔧 Taladros, esmeriles (cada uno tiene su serial)
- ⚙️ Motores, bombas de agua
- 📱 Equipos electrónicos
- 🧰 Herramientas con garantía

#### Activar seriales en un producto

1. Desde **Kárdex**, creá o editá un producto.
2. Activá la opción **"Tiene Serial"** (`has_serial = Sí`).
3. Configurá opcionalmente **"Meses de Garantía"** (ej. 12 meses).
4. Guardá el producto.

#### Registrar seriales en inventario

Una vez que el producto tiene serial activado:

1. Desde la ficha del producto, presioná **"Agregar Seriales"**.
2. Ingresá los números de serie uno por uno:
   - **Número de Serie:** ej. "SN-2026-001", "TAL-23456".
   - **Fecha de Compra:** cuándo ingresó al almacén.
   - **Precio de Costo:** opcional, cuánto pagaste por esa unidad.
   - **Notas:** opcional, ej. "Recibido del proveedor XYZ".
3. Presioná **"Guardar"**.
4. ✅ Los seriales aparecen como **disponibles** en el inventario.

> 🔢 El stock del producto se calcula automáticamente como la cantidad de seriales **disponibles**.

#### Vender productos con serial

1. En **Facturación**, agregá el producto al carrito.
2. Si el producto **tiene serial**:
   - Se abre un modal para **seleccionar los seriales específicos** a vender.
   - Elegí los seriales disponibles (se muestran con su número).
   - Confirmá la selección.
3. ✅ Al registrar la venta, los seriales pasan a estado **"Vendido"** y se asocian a la venta.

#### ¿Qué pasa si se anula una venta?

Si se anula una venta que incluía productos con serial:
- ✅ Los seriales **vuelven a estado "Disponible"** automáticamente.
- Se desasocian de la venta anulada.

#### Consultar trazabilidad

Podés rastrear:
- **De producto a venta:** qué serial se vendió, en qué venta, a qué cliente.
- **De venta a producto:** qué seriales incluyó una venta específica.
- **Garantía:** saber cuándo vence la garantía de cada unidad.

#### Productos SIN serial

Si un producto tiene `has_serial = No` (valor por defecto):
- El stock se maneja por **cantidad total** (como siempre).
- No requiere seleccionar seriales al vender.
- Se comporta como inventario tradicional.

---

## 5. Sidebar y Navegación

La barra lateral (sidebar) es el menú principal del sistema.

### 🖥️ En escritorio (pantalla grande)

- La sidebar está **siempre visible** a la izquierda.
- Las secciones se agrupan por **módulos**: Proyecto de Inversión, Ventas/POS, Restaurante, Inventario, Finanzas, Configuración.
- Cada sección se **expande o colapsa** con un clic en su título.
- El botón **"🚪 Cerrar Sesión"** está siempre visible en la **parte inferior**, aunque haya muchas secciones abiertas.

### 📱 En móvil (pantalla chica)

- La sidebar está **oculta** por defecto.
- Presioná el ícono ☰ (hamburguesa) en la esquina superior izquierda para abrirla.
- Se muestra como un **panel superpuesto** con fondo oscuro semitransparente.
- Tocá fuera del panel o presioná ✕ para cerrarlo.

### 🧭 Secciones condicionales

- Si tu negocio es **Restaurante** → la sección 🍽️ Restaurante aparece completa (Mesas, Menú, Cocina, Take Away, Promociones).
- Si tu negocio es **Ferretería** → la sección Restaurante NO se muestra.
- Si tu negocio tiene ambos → se muestran ambas secciones.

### 🌐 Rutas directas

Podés acceder escribiendo directamente la ruta en el navegador:

| Página | Ruta |
|--------|------|
| Dashboard | `/` |
| Setup del proyecto | `/setup` |
| Simulador | `/simulador` |
| Caja / POS | `/ventas/pos` |
| Nueva venta | `/ventas/nueva` |
| Historial de ventas | `/ventas/historial` |
| Mapa de Mesas | `/restaurante/mesas` |
| Menú | `/restaurante/menu` |
| Cocina | `/restaurante/cocina` |
| Take Away | `/restaurante/takeaway` |
| Promociones | `/restaurante/promociones` |
| Kárdex | `/inventario/kardex` |
| Categorías | `/inventario/categorias` |
| Flujo de Caja | `/finanzas/cashflow` |
| Marca / Branding | `/config/marca` |

---

## 6. Preguntas Frecuentes

### 🔄 ¿Cada cuánto se actualizan las pantallas?

| Pantalla | Frecuencia |
|----------|:----------:|
| Mapa de Mesas | Cada **30 segundos** |
| Pantalla de Cocina | Cada **10 segundos** |
| Las demás pantallas | Al hacer clic o al cargar la página |

### 🏷️ ¿Cómo funcionan los modificadores?

Los modificadores son personalizaciones que el cliente puede agregar a un plato. Al hacer clic en un ítem con el distintivo 🏷️, se abre un selector con **tres tipos**:

- **🔢 Cuantificables** (ej: Huevo frito +S/3.00): elegís la cantidad con botones −/+ hasta un máximo. El precio se multiplica por la cantidad.
- **☑️ Opción sí/no** (ej: Sin cebolla): un checkbox para activar o desactivar.
- **🔘 Grupo excluyente** (ej: Término de cocción): radio buttons donde solo podés elegir una opción del grupo.

El precio se recalcula automáticamente. Funcionan tanto en **Pedidos en Mesa** como en **Take Away**.

### ❌ ¿Qué hago si veo un error?

1. Primero, presioná el botón **"Reintentar"** que aparece en el mensaje de error.
2. Si el error persiste, refrescá la página (F5).
3. Si aún así no funciona, contactá al administrador.

### 🍽️ ¿Puedo tener Restaurante y Ferretería al mismo tiempo?

Sí. La configuración del negocio determina qué secciones se muestran. Consultá con el administrador para cambiar el tipo de negocio.

### 🏷️ ¿Cómo aplico una promoción manualmente?

**No es necesario.** Las promociones se aplican **automáticamente** al cerrar la cuenta. El sistema elige la mejor opción para el cliente.

### 📦 ¿Puedo tener productos con y sin serial?

Sí. Cada producto se configura individualmente:

- `has_serial = Sí` → trazabilidad por serial, stock = cantidad de seriales disponibles.
- `has_serial = No` → stock por cantidad total, sin seriales.

### 🔢 ¿El sistema soporta código de barras?

En esta versión, el campo **código de barras** (`barcode`) está disponible al crear productos, pero **no hay lógica de escáner** todavía. Podés ingresar el código manualmente. La funcionalidad de escáner llegará en una versión futura.

### 🧾 ¿Cómo facturo electrónicamente?

La facturación electrónica (SUNAT) **no está disponible** en esta versión. Llegará en fases futuras. Por ahora, las ventas se registran internamente.

### 🚚 ¿Hay delivery?

No en esta versión. El delivery (con repartidores, zonas y tracking) está planificado para una versión futura.

---

## 7. Referencias Técnicas

> Esta sección es para administradores y personal técnico.

### URLs del Sistema

| Servicio | URL |
|----------|-----|
| Frontend (usuario) | http://localhost:80 |
| Backend API | http://localhost:8000 |
| Documentación API (Swagger) | http://localhost:8000/docs |
| Backend (LAN) | http://192.168.1.35 |

### Datos Semilla (precargados)

| Tabla | Registros |
|-------|:---------:|
| `tables` | 17 mesas (Terraza, Salón Principal, VIP) |
| `menu_items` | 11 ítems (entradas, fondos, bebidas, postres) |
| `menu_modifiers` | 7 modificadores (3 en Ceviche Clásico, 4 en Lomo Saltado) |
| `promotions` | 1 combo (Ceviche + Causa - ahorro S/8) |

### Tecnología del Sistema

| Componente | Tecnología |
|------------|------------|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.12) |
| Base de Datos | PostgreSQL 16 |
| Cache | Redis 7 |
| Cola de mensajes | RabbitMQ |
| Autenticación | JWT + Argon2id |
| Contenedores | Docker + Docker Compose |

### Módulos de Fase 0

| # | Módulo | Estado |
|---|--------|:------:|
| 1 | 🍽️ Restaurante (mesas, menú, comandas) | ✅ Completado |
| 2 | 🥡 Take Away | ✅ Completado |
| 3 | 🏷️ Modificadores en Take Away y Pedidos (bottom sheet) | ✅ Completado |
| 4 | 🎟️ Promociones (combos, descuentos, 2x1) | ✅ Completado |
| 5 | 👨‍🍳 Pantalla de Cocina (Kanban) | ✅ Completado |
| 6 | 🧾 POS mayorista/detal (2 precios) | ✅ Completado |
| 7 | 📦 Seriales en inventario | ✅ Completado |
| 8 | 📂 Categorías de productos | ✅ Completado |
| 9 | 🧭 Sidebar jerárquico colapsable | ✅ Completado |

---

> 🐟 **El Segoviano** — *"Sabor que conquista, sistema que administra"*  
> Documento generado por el equipo de documentación técnica de IaaS-RonSys.
