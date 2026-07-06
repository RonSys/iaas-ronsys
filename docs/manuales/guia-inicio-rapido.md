# 🚀 Guía de Inicio Rápido — IaaS-RonSys

> **Versión:** 2.1  
> **Fecha:** 2026-05-26  
> **Sistema:** IaaS-RonSys v0.3.0 — ERP SaaS Financiero-Contable + POS + Restaurante  
> **Franquicia:** El Segoviano 🐟

---

## 📋 ¿Qué es IaaS-RonSys?

IaaS-RonSys es el sistema ERP financiero-contable de la franquicia **"El Segoviano"**. Te permite:

- Simular la inversión de un negocio nuevo 🔧
- Generar estados financieros automáticamente (PYG, Balance, Ratios) 📊
- Controlar inventarios con kárdex valorizado 📦
- **Visualizar flujo de caja proyectado vs real** 💰
- **Gestionar ventas con POS integrado** 🧾
- **Adaptar la interfaz según tu tipo de negocio** (restaurante/ferretería/retail) 🏪
- Personalizar la apariencia del sistema 🎨

---

## 🔗 Acceso al Sistema

| Elemento | 🚀 Producción |
|----------|:---:|
| **Aplicación Web** | `http://localhost` |
| **API / Backend** | `http://localhost:8000` |
| **Swagger Docs** | `http://localhost:8000/docs` |
| **RabbitMQ Management** | `http://localhost:15672` (guest/guest) |

### Credenciales de Demostración

| Campo | Valor |
|--------|-------|
| **Email** | `admin@elsegoviano.pe` |
| **Contraseña** | `admin123` |
| **Rol** | admin (acceso total al sistema) |

> ⚠️ Cambia la contraseña al ingresar por seguridad.

---

## 🏃 Primeros Pasos (5 minutos)

### Paso 1: Iniciar Sesión

1. Abre `http://localhost` en tu navegador
2. Ingresa `admin@elsegoviano.pe` / `admin123`
3. Haz clic en **Iniciar Sesión**

La sesión dura **15 minutos** y se **renueva automáticamente**.

### Paso 2: Configurar una Empresa (Setup Wizard)

1. En la barra de navegación, haz clic en **🏗️ Setup**
2. Llena los datos de inversión de tu negocio:

| Sección | Qué configurar | Ejemplo |
|---------|---------------|---------|
| **Inversión** | Capital propio + préstamo | S/ 50,000 + S/ 30,000 |
| **Instalación** | Equipos, muebles, licencias | S/ 15,000 equipos |
| **Gastos Fijos** | Alquiler, sueldos, servicios | S/ 2,500 alquiler |
| **Proyección** | Ventas por mes, costo de insumos | S/ 25,000/mes, 40% costo |

3. Haz clic en **⚡ Ejecutar Simulación**
4. Verás un resumen con KPIs financieros

### Paso 3: Explorar el Dashboard

Después de la simulación, visita:

| Sección | Qué ver |
|---------|---------|
| **📊 Dashboard** | 4 KPIs principales, gráficos de flujo de caja |
| **💰 Flujo de Caja** | Proyectado, Real y Comparativa con alertas automáticas |
| **📋 Reportes** | PYG, Balance, BCSS, Ratios con semáforo 🟢🟡🔴 |
| **🎮 Simulador** | Sliders interactivos para probar escenarios |

---

## 🧭 Navegación General

La barra superior cambia según tu **tipo de negocio**:

| Menú | Ruta | ¿Qué hace? |
|------|------|-----------|
| 📊 **Dashboard** | `/` | Panel principal — KPIs, gráficos |
| 💰 **Flujo de Caja** | `/cashflow` | Proyectado / Real / Comparativa |
| 🧾 **Caja** | `/caja` | Turno POS — abrir/cerrar caja |
| ➕ **Nueva Venta** | `/ventas/nueva` | Registrar venta con items + pagos |
| 📋 **Ventas** | `/ventas` | Historial de ventas + filtros |
| 📦 **Kárdex** | `/kardex` | Inventario — productos, entradas, salidas |
| 🏗️ **Setup** | `/setup` | Configuración inicial de inversión |
| 🎮 **Simulador** | `/simulador` | Sliders interactivos |
| 📋 **Reportes** | `/reportes` | PYG, Balance, BCSS, Ratios |
| ⚙️ **Ajustes** | `/settings` | Paleta de colores, branding |

### Navegación condicional según tipo de negocio

| Feature Flag | Si está activo | Si está inactivo |
|-------------|---------------|:----------------:|
| `tables_enabled` | 🪑 Menú **Mesas** (/mesas) visible | Oculto |
| `invoice_required` | Selector boleta/factura en ventas | Solo boleta |
| `tips_enabled` | 💵 Campo propina en ventas | Oculto |
| `warranty_tracking` | 🔧 Campos garantía en ventas | Oculto |

---

## 🧾 POS — Punto de Venta

### Abrir Turno de Caja

1. Ve a **🧾 Caja**
2. Ingresa el monto de apertura (efectivo inicial en caja)
3. Haz clic en **Abrir Turno**

### Registrar una Venta

1. Con el turno abierto, ve a **➕ Nueva Venta**
2. Agrega productos (buscador automático de inventario)
3. Selecciona el método de pago: Efectivo, Tarjeta, Yape, Plin o Transferencia
4. Confirma la venta — el sistema:
   - ✅ Descuenta del inventario automáticamente
   - ✅ Genera el asiento contable
   - ✅ Muestra el ticket resumen

### Cerrar Turno

1. Ve a **🧾 Caja**
2. Ingresa el efectivo final en caja
3. El sistema calcula: `diferencia = cierre_esperado - cierre_real`
4. Confirma el cierre

### Especialización por tipo de negocio

| Tipo | Campos adicionales en venta |
|------|---------------------------|
| 🍽️ **Restaurante** | Mesa #, comensales, tipo orden (en mesa/llevar/delivery), mesero, propina, notas de cocina |
| 🔧 **Ferretería** | Boleta/Factura, RUC/DNI cliente, meses de garantía, dirección de despacho, requiere instalación |

---

## 💰 Flujo de Caja

### Vista Proyectada
- Muestra 12 meses de ingresos y egresos basados en el setup
- Barras verdes (ingresos) y rojas (egresos)
- 8 conceptos: Ventas, Costo de Ventas, Alquiler, Servicios, Salarios, Marketing, Administración, Mantenimiento

### Vista Real
- Datos de transacciones contables reales
- Requiere ventas registradas (POS) o asientos manuales

### Vista Comparativa
- Barras lado a lado: Proyectado (azul) vs Real (naranja)
- Alertas automáticas:
  - 🟢 Desviación < 5%
  - 🟡 Desviación 5-20%
  - 🔴 Desviación ≥ 20% o liquidez negativa

---

## 👤 Roles de Usuario

Actualmente el sistema cuenta con un usuario **admin** con acceso total:
- Ver y operar todos los módulos
- Configurar empresa y branding
- Gestionar usuarios

---

## 📦 Kárdex / Inventario

1. Ve a **📦 Kárdex**
2. **+ Producto** — ingresa código, nombre, stock inicial y costo unitario
3. **+ Entrada** para compras
4. **- Salida** para ventas/mermas
5. El sistema calcula automáticamente el **costo promedio ponderado**
6. Los datos ahora **persisten en base de datos** (no en memoria)

---

## 🎨 Personalización Rápida

1. Ve a **⚙️ Ajustes** (solo admin)
2. Elige una paleta predefinida: Azul Marino, Verde Bosque, Rojizo Cálido o Púrpura
3. O personaliza cada color individualmente
4. Los cambios se aplican al instante

---

## ❓ Problemas Comunes

| Problema | Solución |
|----------|----------|
| **No veo datos en el Dashboard** | Ejecuta primero el Setup Wizard (🏗️ Setup) |
| **No puedo registrar ventas** | Debes abrir un turno en **🧾 Caja** primero |
| **"Stock insuficiente"** | Registra una entrada en **📦 Kárdex** antes de vender |
| **Flujo de Caja en 0** | Ejecuta el Setup primero. La vista real necesita ventas registradas |
| **Login falla** | Verifica email y contraseña. Si falla 10 veces, la cuenta se bloquea 15 min |
| **No veo menús de ventas** | Depende del `business_type` configurado en tu empresa |
| **Error 500 en cashflow** | Asegúrate de que las migraciones se aplicaron (reinicie contenedor) |

---

## 📞 ¿Necesitas Ayuda?

- **Manual completo**: `manual-usuario.md` para guía detallada de cada módulo
- **Manual de administrador**: `manual-admin.md` para gestión de usuarios y troubleshooting
- **API Reference**: `http://localhost:8000/docs` — todos los endpoints documentados

---

> IaaS-RonSys · El Segoviano · v0.2.0
