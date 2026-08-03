# Manual de Usuario — Delivery Nocturno / Dark Kitchen 🛵

> **Versión:** 1.0 (Spec 03 — Fase A)  
> **Fecha:** 2026-08-03  
> **Producto:** IaaS-RonSys ERP by **El Segoviano** 🐟  
> **Landing pública:** `https://www.ronsyserp.com/menu/el-segoviano`  
> **Panel staff:** Menú lateral → Restaurante → **Delivery Nocturno**

---

## 1. ¿Qué es el Delivery Nocturno?

El local **no opera de noche**; con este módulo aprovechamos esa capacidad instalada:

- 🌙 **Menú nocturno** (de 19:00 a 24:00): los clientes piden desde una **página pública** con su celular.
- 💳 **Pago**: Yape, Plin o contraentrega (efectivo al recibir).
- 📍 **Seguimiento**: el cliente puede ver en qué estado va su pedido con un código.
- 🧾 **Todo contabilizado**: cada pedido genera su venta, descuenta inventario (kárdex) y su asiento contable automáticamente — sin trabajo extra para el staff.
- 📢 **Campañas medibles**: cada anuncio tiene su link con UTM; el sistema muestra cuánto vendió cada campaña (ROAS).

> 🎯 **¿Para quién es este manual?**  
> Para el **cliente** que pide (sección 2) y para el **equipo del local** que atiende (sección 3): cocina, cajeros y administradores.
>
> 🔑 **Credenciales de acceso por tenant** (usuarios demo del sistema): ver `docs/manuales/credenciales-por-tenant.md` (usuario principal del panel: `admin@elsegoviano.pe` / `admin123`).

---

## 2. Para el Cliente — Cómo Pedir desde la Landing

### 2.1 Abrir el menú

1. Entra al link del local: `https://www.ronsyserp.com/menu/el-segoviano`
   (los anuncios de Facebook/Instagram/Google llevan a este mismo link).
2. Verás el **menú nocturno** con los platos disponibles en ese momento.
   - Si el delivery está cerrado, verás un aviso con el horario (19:00–24:00).

### 2.2 Armar el pedido

1. Toca un plato para **agregarlo a tu pedido**.
   - Si el plato es personalizable (ej. "sin cebolla"), se abrirá el selector de opciones.
2. Ajusta las cantidades desde el carrito (panel derecho en computadora, abajo en el celular).
3. Verás el **subtotal** y, al elegir zona, el **costo de delivery**.

### 2.3 Completar la entrega

1. **Zona de entrega**: elige tu zona (cada una muestra su costo y tiempo estimado).
   - ⚠️ Si tu pedido no llega al mínimo de la zona, el sistema te avisará.
2. **Datos**: nombre, teléfono y dirección.
3. **Pago**:
   - **Yape**: yapea al número que se muestra en pantalla y copia el **código de referencia** de tu Yape.
   - **Plin**: igual que Yape.
   - **Contraentrega**: pagas en efectivo cuando llega el pedido.
4. Toca **Confirmar pedido**.

### 2.4 Después de pedir

- Verás la confirmación con tu **código de seguimiento** (ej. `DLV-9fc5fe4655`) y el tiempo estimado.
- Toca **"Seguir mi pedido"** (o la pestaña 📍 Seguir pedido del menú) e ingresa el código para ver el avance:

```
📥 Pedido recibido → 👨🍳 En cocina → 🍽️ Listo → 🛵 En camino → 🏠 Entregado
```

---

## 3. Para el Equipo del Local — Panel Delivery Nocturno

> Ingresa al ERP (https://www.ronsyserp.com), ve a **Restaurante → Delivery Nocturno**.

### 3.1 📦 Pedidos (kanban)

Los pedidos llegan solos desde la landing y aparecen en columnas por estado:

| Columna | Significado | Qué hace el equipo |
|---|---|---|
| **Recibido** | El cliente confirmó y pagó (o pagará contraentrega) | Revisar platos y notas |
| **En cocina** | Se está preparando | La comanda ya está en la pantalla de cocina 🧑‍🍳 |
| **Listo** | Platos terminados | Empaquetar |
| **En ruta** | El repartidor va en camino | — |
| **Entregado / Cancelado** | Estado final | — |

**Acciones por pedido:**
- Botones **→ En cocina / → Listo / → En ruta / Entregar**: avanzan el estado (el cliente lo ve en su seguimiento).
- **✕ Cancelar**: cancela el pedido (solo desde estados no finales).
- **Asignar repartidor**: elige un repartidor disponible; al entregar/cancelar, el repartidor vuelve a "disponible".

> 💡 El sistema **solo permite avances válidos** (no se puede pasar de "Recibido" a "Entregado" sin pasar por cocina). Si algo falla, muestra el mensaje de transiciones permitidas.

### 3.2 🗺️ Zonas

Gestiona las zonas de reparto: **nombre, distritos, costo de delivery (fee), pedido mínimo y tiempo estimado (ETA)**.

- La **Zona 1** (Montenegro / Motupe / Canto Grande, S/5.00, mínimo S/35, 35 min) ya viene configurada.
- Para agregar otra zona: **+ Nueva Zona** → completa los datos → **Guardar**.
- Puedes **editar** (ajustar fee, mínimo, ETA) o **eliminar** zonas. Las zonas inactivas no aparecen en la landing.

### 3.3 🛵 Repartidores

Registra a los repartidores internos: **nombre, teléfono y vehículo** (moto, bicicleta, auto).

- Cada repartidor tiene un estado: **Disponible / En entrega / Desconectado**.
- Cuando asignas un pedido, pasa a **En entrega**; al entregarlo o cancelarlo, vuelve a **Disponible**.
- Usa **Poner offline** para que no se le asignen pedidos (ej. descanso).

### 3.4 📢 Campañas (Marketing Digital)

Para medir cuánto vende cada campaña de anuncios:

1. **+ Crear**: nombre de la campaña, canal (Meta/Instagram, Google, TikTok), `utm_source` (ej. `meta`) y `utm_campaign` (ej. `lanzamiento`).
2. Registra el **presupuesto** y, conforme avance el mes, el **gasto real** en anuncios.
3. El panel genera el **link para anuncios** (ej. `/menu/el-segoviano?utm_source=meta&utm_campaign=lanzamiento`) — **cópialo y úsalo en los anuncios**.
4. Cuando un cliente entra por ese link y pide, el pedido se **atribuye a la campaña automáticamente**.

### 3.5 📈 Métricas (ROAS)

- **Tarjetas superiores**: pedidos entregados, ventas totales (GMV), fee de delivery cobrado, tiempo promedio de entrega y cancelados.
- **Tabla por campaña**: gasto, pedidos, GMV, ticket promedio y **ROAS**.

> 💡 **ROAS = ventas ÷ gasto en anuncios.** Si es **mayor a 1.0**, cada sol invertido en anuncios genera más de un sol en ventas. Regla práctica: ROAS ≥ 2 es saludable para delivery.

---

## 4. Preguntas Frecuentes

| Pregunta | Respuesta |
|---|---|
| **¿Un plato no aparece en la landing?** | Puede estar fuera del horario nocturno o tener `delivery_enabled=false` (solo salón/takeaway). Revísalo en **Restaurante → Maestro de Platos**. |
| **¿El pedido descuenta inventario?** | Sí. Cada pedido genera la venta y descuenta los insumos de las recetas (kárdex) automáticamente. |
| **¿Necesito abrir caja (POS) para los pedidos online?** | No. Los pedidos de la landing se registran solos; igual se ven en el historial de ventas. |
| **¿Dónde veo el número Yape?** | En la landing, cuando el cliente elige "Yape". Se configura en la app (ver manual-admin §5.3). |
| **¿Se puede cambiar el fee de una zona?** | Sí, en **Delivery Nocturno → Zonas → Editar**, sin migraciones ni reinicio. |
| **¿Cómo sé qué campaña funcionó?** | En **Delivery Nocturno → Métricas**, comparando el ROAS de cada campaña. |

---

## 5. Notas técnicas (para el administrador)

- El fee de delivery se contabiliza en la cuenta **40 (Ventas)** como ítem "Delivery fee" (cuenta 705 diferida a futuro).
- Endpoints y detalles técnicos: `docs/manuales/manual-admin.md` §5.3, §5.4 y §10.5.
- Especificación: `docs/specs/03-spec-delivery-dark-kitchen-v0.1.md`.
