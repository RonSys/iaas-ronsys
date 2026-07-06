# 📘 Manual de Usuario — IaaS-RonSys

> **Versión:** 2.3  
> **Fecha:** 2026-05-27  
> **Sistema:** IaaS-RonSys v0.4.1 — ERP SaaS + POS + Restaurante  
> **Franquicia:** El Segoviano 🐟  

---

## 📑 Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Acceso al Sistema](#2-acceso-al-sistema)
3. [Dashboard — Panel de Control](#3-dashboard--panel-de-control)
4. [Setup Wizard — Configuración Inicial](#4-setup-wizard--configuración-inicial)
5. [Simulador Financiero](#5-simulador-financiero)
6. [Reportes Financieros](#6-reportes-financieros)
7. [Kárdex — Inventario](#7-kárdex--inventario)
8. [Flujo de Caja](#8-flujo-de-caja)
9. [POS — Punto de Venta](#9-pos--punto-de-venta)
    - 9.1 [Abrir Turno de Caja](#91-abrir-turno-de-caja)
    - 9.2 [Registrar una Venta](#92-registrar-una-venta)
    - 9.3 [Campos Especializados por Tipo de Negocio](#93-campos-especializados-por-tipo-de-negocio)
    - 9.4 [Cerrar Turno de Caja](#94-cerrar-turno-de-caja)
    - 9.5 [Listado de Ventas](#95-listado-de-ventas)
    - 9.6 [Mantenimiento de Secciones](#96-mantenimiento-de-secciones)
    - 9.7 [Modificadores del Menú](#97-modificadores-del-menú)
    - 9.8 [Área de Preparación](#98-área-de-preparación)
10. [Settings — Personalización](#10-settings--personalización)
11. [Gestión de Usuarios (Admin)](#11-gestión-de-usuarios-admin)
12. [FAQ / Problemas Comunes](#12-faq--problemas-comunes)

---

## 1. Introducción

### ¿Qué es IaaS-RonSys?

IaaS-RonSys (Intelligence as a Service — Ron's System) es el **ERP SaaS financiero-contable** de la franquicia "El Segoviano". Diseñado para gestionar las finanzas de cevicherías franquiciadas, automatiza:

- **Simulación de inversión**: modela el capital necesario y proyecta retornos
- **Contabilidad completa**: asientos contables automáticos desde la simulación
- **Estados financieros**: PYG, Balance General y Balance de Comprobación
- **Ratios financieros**: con semáforo interpretativo (🟢 saludable, 🟡 precaución, 🔴 crítico)
- **Kárdex / Inventario**: control de productos con costo promedio ponderado
- **Branding**: personalización de colores para cada franquicia

### ¿Quién debe usar este manual?

Este manual es para **todos los usuarios** del sistema: administradores, gerentes, operadores y usuarios de solo lectura. Para tareas exclusivas de administrador (gestión de usuarios, troubleshooting avanzado), consulta el [Manual de Administrador](manual-admin.md).

### Convenciones

- Los **pasos numerados** indican una secuencia que debes seguir
- Las **tablas** presentan datos estructurados (opciones, valores)
- Los **emojis** identifican secciones y niveles de alerta:
  - ⚠️ Precaución / Importante
  - 💡 Tip / Consejo útil
  - ❌ Acción no recomendada

---

## 2. Acceso al Sistema

### URLs

| Servicio | 🚀 Producción | 🧪 QA (Pruebas) |
|----------|:---:|:---:|
| **Aplicación Web** | `http://localhost` | `http://localhost:5173` |
| **API / Backend** | `http://localhost:8000` | `http://localhost:8001` |
| **Swagger Docs** | `http://localhost:8000/docs` | `http://localhost:8001/docs` |

> 💡 Producción usa Nginx en el puerto 80 (sin número de puerto). QA usa Vite dev server en `:5173`.

### Credenciales de Demostración

| Campo | Valor |
|--------|-------|
| Email | `admin@elsegoviano.pe` |
| Contraseña | `admin123` |
| Rol | admin |

> ⚠️ **Cambia la contraseña** apenas ingreses. Esta cuenta tiene acceso total al sistema.

### Cómo Funciona la Sesión

IaaS-RonSys utiliza **JWT (JSON Web Tokens)** con dos tipos de token:

| Token | Duración | Almacenamiento | Propósito |
|-------|----------|---------------|-----------|
| **Access Token** | 15 minutos | Memoria (variable JS) | Autorizar cada request a la API |
| **Refresh Token** | 7 días | sessionStorage | Renovar access token sin re-login |

**Renovación automática:** Cuando el access token expira (15 min), el frontend **usa automáticamente el refresh token** para obtener uno nuevo. Este proceso es invisible — no verás interrupciones ni pantallas de login mientras uses la aplicación activamente.

**Al cerrar la pestaña del navegador**, el access token se pierde (está en memoria), pero el refresh token persiste en `sessionStorage`. Si vuelves a abrir la aplicación antes de que el refresh token expire (7 días), la sesión se restaura automáticamente sin pedir login.

### Iniciar Sesión

1. Abre la aplicación en tu navegador:
   - **Producción**: `http://localhost`
   - **QA**: `http://localhost:5173`
2. Aparece la pantalla de login con los campos **Email** y **Contraseña**
3. Ingresa tus credenciales
4. Haz clic en **Iniciar Sesión** (o presiona Enter)

### ### Roles y Permisos

Actualmente existe un usuario **admin** con acceso completo a todos los módulos del sistema:
- Configuracion de empresa (Setup)
- Dashboard y Reportes
- Kardex / Inventario
- POS / Ventas
- Flujo de Caja
- Ajustes de personalizacion
- Gestion de usuarios


### Cerrar Sesión

Para cerrar sesión de forma segura, haz clic en el botón de **Cerrar Sesión** en la barra de navegación. Esto:

1. **Revoca el refresh token** en el servidor (nadie más puede usarlo)
2. **Limpia el estado local** (access token y datos de usuario)
3. **Redirige a la pantalla de login**

Si solo cierras la pestaña sin hacer logout, el refresh token sigue siendo válido en el servidor hasta que expire (7 días) o sea revocado explícitamente.

---

## 3. Dashboard — Panel de Control

El Dashboard es la pantalla principal después del login. Muestra una vista resumida de la salud financiera de la empresa.

### KPIs Principales

| KPI | Descripción | Cálculo |
|-----|-------------|---------|
| 💰 **Ventas Totales** | Ingresos totales por ventas en el período simulado | Suma de ventas mensuales × 12 meses |
| 📈 **Utilidad Neta** | Ganancia después de todos los costos, gastos e impuestos | Ventas − Costos − Gastos − Impuestos |
| 📊 **EBITDA** | Utilidad operativa antes de intereses, depreciación e impuestos | Utilidad Operativa + Depreciación + Amortización |
| 💎 **Activos Totales** | Valor total de los activos de la empresa | Activo Corriente + Activo No Corriente |

Cada KPI se muestra en una tarjeta con:
- **Título** y emoji identificativo
- **Valor** formateado en la moneda configurada (S/ por defecto)
- **Estado**: normal, o vacío si no hay simulación

### PYG Resumido

Debajo de los KPIs, el Dashboard muestra un resumen del Estado de Resultados (PYG):

| Línea | Significado |
|-------|-------------|
| **Ventas Netas** | Ingresos totales por ventas |
| **Costo de Ventas** | Costo de los insumos para producir lo vendido |
| **Utilidad Bruta** | Ventas − Costo de Ventas |
| **Gastos Operativos** | Alquiler, sueldos, marketing, servicios, etc. |
| **Utilidad Operativa** | Utilidad Bruta − Gastos Operativos |
| **Gastos Financieros** | Intereses del préstamo |
| **Utilidad antes de Impuestos** | Utilidad Operativa − Gastos Financieros |
| **Impuesto a la Renta** | 29.5% de la utilidad imponible (régimen general Perú) |
| **Utilidad Neta** | Resultado final |

### Balance General Resumido

| Sección | Contenido |
|---------|-----------|
| **Activo Corriente** | Caja, inventarios, cuentas por cobrar |
| **Activo No Corriente** | Equipos, muebles, depreciación acumulada |
| **Pasivo Corriente** | Préstamo porción corto plazo, cuentas por pagar |
| **Pasivo No Corriente** | Préstamo porción largo plazo |
| **Patrimonio** | Capital social + Utilidad del ejercicio |

### Gráficos de Flujo de Caja

El Dashboard incluye dos gráficos generados automáticamente:
- **📊 Flujo de Caja Mensual**: barras apiladas (ingresos vs egresos por mes)
- **📈 Flujo de Caja Acumulado**: línea de tendencia del efectivo acumulado

> 💡 Para la vista completa con proyección, datos reales y comparativa con alertas, ve a **💰 Flujo de Caja** en la navegación (ver [Sección 8](#8-flujo-de-caja)).

## 4. Setup Wizard — Configuración Inicial

El Setup Wizard es el punto de partida. Aquí defines todos los parámetros financieros de tu cevichería y ejecutas la simulación contable.

### Secciones del Formulario

#### 4.1 Inversión Inicial

| Campo | Descripción | Valor sugerido |
|-------|-------------|----------------|
| **Capital propio** | Dinero que pones de tu bolsillo | S/ 50,000 |
| **Préstamo bancario** | Monto financiado por el banco | S/ 30,000 |
| **Tasa de interés anual** | Tasa del préstamo (ej: 12.5% = 0.125) | 0.125 |
| **Plazo del préstamo** | Meses para pagar | 24 |

#### 4.2 Gastos de Instalación (Pre-operativos)

| Campo | Descripción |
|-------|-------------|
| **Equipamiento** | Cocinas, refrigeradores, freidoras, campanas |
| **Mobiliario** | Mesas, sillas, barra, decoración |
| **Computadoras** | Laptops, impresoras, POS |
| **Software y licencias** | ERP, sistema de ventas, office |
| **Garantía de alquiler** | Depósito que pide el arrendador |
| **Inventario inicial** | Insumos para el primer mes (pescado, limón, etc.) |

#### 4.3 Gastos Fijos Mensuales

| Campo | Descripción |
|-------|-------------|
| **Alquiler mensual** | Renta del local |
| **Servicios (luz, agua, internet)** | Utilities mensuales |
| **Sueldos y salarios** | Planilla mensual total |
| **Marketing y publicidad** | Redes sociales, volantes, promociones |
| **Administración** | Contador externo, gestoría |
| **Mantenimiento** | Reparaciones, fumigación, limpieza profunda |

#### 4.4 Proyección de Ventas

| Campo | Descripción |
|-------|-------------|
| **Ventas por mes (12 meses)** | Array de 12 valores. Puedes variar por estacionalidad |
| **Costo de insumos (% de ventas)** | Típicamente 35-40% en cevicherías |

#### 4.5 Vida Útil de Activos (Depreciación)

| Activo | Vida útil típica | Depreciación mensual |
|--------|-----------------|---------------------|
| Equipos de cocina | 8 años | 1/96 del valor por mes |
| Muebles y enseres | 10 años | 1/120 del valor por mes |
| Computadoras | 5 años | 1/60 del valor por mes |
| Software | 3 años | 1/36 del valor por mes |

### Ejecutar Simulación

1. Llena todos los campos del formulario
2. Haz clic en **⚡ Ejecutar Simulación**
3. El sistema:
   - Genera asientos contables automáticos para los 12 meses
   - Calcula depreciación, intereses, impuestos
   - Produce estados financieros completos
4. Verás un **resumen de resultados** con enlaces al Dashboard y Simulador

> 💡 Puedes volver a ejecutar la simulación cuantas veces quieras. Cada ejecución **reemplaza** los datos anteriores.

---

## 5. Simulador Financiero

El Simulador es la herramienta interactiva para responder **"¿qué pasa si...?"** con sliders en tiempo real.

### Variables Ajustables

| Slider | Rango | Impacto |
|--------|-------|---------|
| 🏷️ **Precio promedio por plato** | S/ 10 a S/ 80 | Afecta directamente las ventas |
| 🍽️ **Platos por día** | 10 a 200 | Volumen de ventas diario |
| 📦 **Costo de insumos (%)** | 20% a 60% | Margen bruto |
| 🏠 **Alquiler mensual** | S/ 500 a S/ 10,000 | Gastos fijos |
| 👥 **Sueldos mensuales** | S/ 1,000 a S/ 20,000 | Gastos fijos |

### Cómo Funciona

1. Mueve cualquier slider → el sistema recalcula automáticamente (debounce de 400ms)
2. Los KPIs y resultados se actualizan **en vivo** sin recargar la página
3. Las variables de Setup se mantienen como base; los sliders solo modifican 5 variables clave

### Escenarios Comparativos

Puedes guardar hasta **4 escenarios** para comparar lado a lado:

1. Ajusta los sliders a un escenario deseado
2. Haz clic en **💾 Guardar Escenario**
3. Asígnale un nombre descriptivo (ej: "Pesimista", "Optimista", "Temporada Alta")
4. Repite para otros escenarios
5. La tabla de comparación muestra:

| Columna | Descripción |
|---------|-------------|
| Nombre | Identificador del escenario |
| Precio / Platos / Costo % | Variables del escenario |
| Ventas mensuales | Proyección de ingresos |
| Utilidad Neta | Ganancia proyectada |
| Payback (meses) | Tiempo para recuperar inversión |
| VAN | Valor Actual Neto |
| TIR | Tasa Interna de Retorno |

> 💡 Usa los escenarios para presentar a inversionistas o para planificar temporadas altas/bajas.

---

## 6. Reportes Financieros

La sección de Reportes tiene **4 tabs** con toda la información contable generada por la simulación.

### 6.1 📄 Estado de Resultados (PYG)

Muestra el desglose completo de ingresos, costos y gastos:

| Sección | Contenido |
|---------|-----------|
| **Ingresos Operativos** | Ventas netas del período |
| **Costo de Ventas** | Insumos directos para producir |
| **Utilidad Bruta** | Ingresos − Costo de Ventas |
| **Gastos Operativos** | Alquiler, sueldos, servicios, marketing, mantenimiento |
| **Depreciación** | Desgaste mensual de activos fijos |
| **Utilidad Operativa** | Utilidad Bruta − Gastos − Depreciación |
| **Gastos Financieros** | Intereses del préstamo |
| **Utilidad antes de Impuestos** | Base imponible |
| **Impuesto a la Renta (29.5%)** | Impuesto calculado |
| **Utilidad Neta** | Resultado final del ejercicio |

### 6.2 ⚖️ Balance General

Estado de situación financiera:

| Activo | Pasivo + Patrimonio |
|--------|---------------------|
| **Activo Corriente** | **Pasivo Corriente** |
| Caja y bancos | Préstamo corto plazo |
| Inventarios | Cuentas por pagar |
| **Activo No Corriente** | **Pasivo No Corriente** |
| Equipos (neto de depreciación) | Préstamo largo plazo |
| Muebles (neto de depreciación) | **Patrimonio** |
| Computadoras (neto) | Capital social |
| Software (neto) | Utilidad del ejercicio |

> La ecuación contable siempre debe cumplir: **Activo = Pasivo + Patrimonio**

### 6.3 🧾 BCSS — Balance de Comprobación

Tabla completa de todas las cuentas contables con 4 columnas:

| Columna | Significado |
|---------|-------------|
| **Código** | Código de cuenta (ej: 101 = Caja, 601 = Compras) |
| **Nombre** | Nombre de la cuenta contable |
| **Debe** | Suma de movimientos al debe |
| **Haber** | Suma de movimientos al haber |
| **Saldo** | Diferencia Debe − Haber |
| **Naturaleza** | D = Deudora, A = Acreedora |

> 💡 El BCSS es la base para generar el PYG y el Balance. La suma del Debe siempre debe igualar a la suma del Haber.

### 6.4 📊 Ratios Financieros

Tabla de ratios con semáforo interpretativo:

| Semáforo | Significado |
|:---:|---|
| 🟢 | Saludable — el ratio está dentro del rango óptimo |
| 🟡 | Precaución — el ratio está en zona de atención |
| 🔴 | Crítico — el ratio indica un problema financiero |

#### Ratios incluidos:

| Ratio | Fórmula | ¿Qué mide? | Meta |
|-------|---------|------------|------|
| **Liquidez Corriente** | Activo Corriente / Pasivo Corriente | Capacidad de pagar deudas de corto plazo | > 1.5 |
| **Prueba Ácida** | (Activo Cte − Inventario) / Pasivo Cte | Liquidez sin depender del inventario | > 1.0 |
| **Endeudamiento** | Pasivo Total / Activo Total | Qué % de la empresa está financiado con deuda | < 60% |
| **Margen Neto** | Utilidad Neta / Ventas | Rentabilidad sobre ventas | > 10% |
| **ROE** | Utilidad Neta / Patrimonio | Retorno sobre el capital invertido | > 15% |
| **ROA** | Utilidad Neta / Activo Total | Eficiencia en uso de activos | > 8% |
| **Cobertura de Intereses** | Utilidad Operativa / Gastos Financieros | Capacidad de pagar intereses | > 3.0 |
| **Rotación de Inventario** | Costo de Ventas / Inventario Promedio | Eficiencia del inventario | > 6 |
| **Payback (meses)** | Inversión Total / Utilidad Neta Mensual | Tiempo para recuperar inversión | < 24 |

---

## 7. Kárdex — Inventario

El módulo de Kárdex controla el inventario de productos usando el método de **costo promedio ponderado**.

### Conceptos Clave

| Término | Definición |
|---------|------------|
| **Producto** | Ítem con código único, nombre, stock y costo |
| **Entrada** | Ingreso de mercadería (compra a proveedor) |
| **Salida** | Egreso de mercadería (venta, consumo, merma) |
| **Costo Promedio Ponderado** | Se recalcula con cada entrada: `(stock × costo_anterior + cantidad × costo_nuevo) / (stock + cantidad)` |
| **Kárdex** | Historial de movimientos de un producto (fecha, tipo, cantidad, costo unitario, costo total, saldo) |

### 7.1 Registrar un Producto Nuevo

1. Ve a **📦 Kárdex**
2. Haz clic en **+ Producto**
3. Llena el formulario:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Código** | Identificador único del producto | `P001` |
| **Nombre** | Nombre descriptivo | `Pescado fresco (kg)` |
| **Stock inicial** | Cantidad con la que empiezas | 50 |
| **Costo unitario** | Costo de adquisición por unidad | 18.50 |

4. Haz clic en **Guardar**

> ⚠️ El código del producto debe ser **único**. No puede haber dos productos con el mismo código.

### 7.2 Registrar una Entrada (Compra)

1. Selecciona un producto haciendo clic en su tarjeta
2. Haz clic en **+ Entrada**
3. Ingresa:

| Campo | Descripción |
|-------|-------------|
| **Cantidad** | Unidades compradas |
| **Costo unitario** | Precio de compra por unidad |

4. El sistema recalcula automáticamente el costo promedio

### 7.3 Registrar una Salida (Consumo / Venta)

1. Selecciona un producto haciendo clic en su tarjeta
2. Haz clic en **- Salida**
3. Ingresa la **cantidad** a retirar
4. La salida se valora al **costo promedio actual** (no necesitas ingresar costo)

> ⚠️ No puedes retirar más unidades de las que hay en stock. El sistema valida que haya inventario suficiente.

### 7.4 Pantalla de Inventario

La vista principal muestra todos los productos en tarjetas:

| Dato | Descripción |
|------|-------------|
| **Código** | Identificador del producto |
| **Nombre** | Descripción del producto |
| **Stock** | Unidades disponibles |
| **Costo Promedio** | Costo unitario promedio ponderado |
| **Valor Total** | Stock × Costo Promedio |

### 7.5 Historial de Movimientos (Kárdex)

Al seleccionar un producto, se despliega su historial completo:

| Columna | Descripción |
|---------|-------------|
| **Fecha** | Cuándo ocurrió el movimiento |
| **Tipo** | Entrada o Salida |
| **Cantidad** | Unidades movidas |
| **Costo Unitario** | Costo por unidad en ese movimiento |
| **Costo Total** | Cantidad × Costo Unitario |
| **Saldo Cantidad** | Stock después del movimiento |
| **Saldo Costo Prom.** | Costo promedio después del movimiento |
| **Saldo Valor** | Valor total del inventario después del movimiento |

---

## 8. Flujo de Caja

La página **Flujo de Caja** (💰 en la navegación) te permite visualizar la liquidez de tu negocio en tres vistas diferentes, con alertas automáticas de desviaciones.

### 8.1 Selector de Vista y Período

En la parte superior de la página encontrarás:

- **Selector de vista**: Proyectado / Real / Comparativa
- **Selector de período**: Mes inicio y Mes fin (AAAA-MM)
- **Año**: para la vista proyectada

### 8.2 Vista Proyectada

Muestra 12 meses de ingresos y egresos basados en los datos del **Setup Wizard**.

- Barras **verdes** = ingresos (Ventas)
- Barras **rojas** = egresos (Costo de Ventas, Alquiler, Servicios, Salarios, Marketing, Administración, Mantenimiento)
- El saldo final de cada mes se calcula como: `saldo_inicial + ingresos - egresos`

> 💡 Si ves "No hay datos de proyección", ejecuta primero el **Setup Wizard** (🏗️ Setup).

### 8.3 Vista Real

Muestra los datos basados en transacciones contables reales:

- Ventas en efectivo registradas
- Costos de venta del kárdex
- Gastos operativos

> ⚠️ Requiere que hayas registrado ventas (POS) o asientos contables manuales en el período.

### 8.4 Vista Comparativa

Compara lado a lado lo proyectado vs lo real:

- Barras **azules** = proyectado
- Barras **naranjas** = real

Incluye **alertas automáticas** con semáforo:
| Alerta | Significado |
|:------:|-------------|
| 🟢 | Desviación < 5% — todo正常 |
| 🟡 | Desviación entre 5% y 20% — monitorear |
| 🔴 | Desviación ≥ 20% o flujo de caja neto negativo — requiere acción |

### 8.5 AlertsBanner

Cuando hay alertas activas, un banner de color se muestra en la parte superior:

- **Severidad red**: fondo rojo suave, texto "Requiere atención"
- **Severidad yellow**: fondo amarillo suave, texto "Monitorear"
- **Severidad green**: fondo verde suave, texto "Dentro de lo esperado"

Cada alerta incluye: concepto, valor proyectado, valor real y diferencia.

---

## 9. POS — Punto de Venta (ruta `/caja`)

El módulo POS (🧾) te permite gestionar turnos de caja y registrar ventas con integración automática a kárdex y contabilidad.

### 9.1 Abrir Turno de Caja

1. Ve a **🧾 Caja** (ruta `/caja`) en la navegación
2. Si no hay turno abierto, verás el botón **Abrir Turno**
3. Ingresa el monto de apertura (efectivo inicial en la caja)
4. El sistema crea el turno y muestra el estado actual

> Solo puede haber **un turno abierto a la vez**. Si ya hay uno, deberás cerrarlo primero.

### 9.2 Registrar una Venta

1. Con el turno abierto, ve a **➕ Nueva Venta**
2. **Agregar items**:
   - Busca productos en el campo de búsqueda (autocompletado del kárdex)
   - Selecciona producto, ingresa cantidad y el precio se llena automáticamente
   - Puedes modificar el precio si es necesario
3. **Seleccionar pagos**:
   | Método | Cómo se registra |
   |--------|------------------|
   | 💵 Efectivo | Ingresa monto recibido — el sistema calcula el vuelto |
   | 💳 Tarjeta | Ingresa monto — opcional: últimos 4 dígitos |
   | 📱 Yape | Ingresa monto — opcional: #operación |
   | 📱 Plin | Ingresa monto — opcional: #operación |
   | 🏦 Transferencia | Ingresa monto — opcional: referencia |
4. El sistema valida que los pagos cubran el total
5. Confirma la venta

**Lo que pasa automáticamente:**
- ✅ Se descuenta del inventario (kárdex)
- ✅ Se genera el asiento contable (Caja, Ventas, IGV, Costo de Ventas, Inventarios)
- ✅ Se muestra el ticket resumen

### 9.3 Campos Especializados por Tipo de Negocio

Dependiendo del `business_type` de tu empresa, aparecen campos adicionales:

#### 🍽️ Restaurante (business_type = restaurant)
| Campo | Descripción |
|-------|-------------|
| **Mesa #** | Número de mesa del comensal |
| **Comensales** | Cantidad de personas en la mesa |
| **Tipo de Orden** | En Mesa / Para Llevar / Delivery |
| **Mesero** | Nombre del mesero que tomó el pedido — se **autocompleta** automáticamente con el nombre del usuario logueado. Si se necesita otro nombre, se puede seleccionar "Otro…" y escribirlo manualmente |
| **Propina** | Monto o porcentaje de propina (visible si `tips_enabled = true`) |
| **Notas de Cocina** | Instrucciones especiales para la cocina |

#### 🔧 Ferretería/Retail (business_type = hardware)
| Campo | Descripción |
|-------|-------------|
| **Tipo Comprobante** | Boleta o Factura |
| **RUC/DNI** | Documento del cliente (requerido para factura) |
| **Meses de Garantía** | 0, 3, 6, 12, 24 o 36 meses (visible si `warranty_tracking = true`) |
| **Dirección de Despacho** | Dirección de entrega (opcional) |
| **Requiere Instalación** | Sí/No |

### 9.4 Cerrar Turno de Caja

1. Ve a **🧾 Caja** (ruta `/caja`)
2. Haz clic en **Cerrar Turno**
3. Ingresa el efectivo final en caja (cuenta física)
4. El sistema calcula:
   - `efectivo_esperado = apertura + total_ventas_efectivo_del_turno`
   - `diferencia = efectivo_final - efectivo_esperado`
5. Confirma el cierre

> Si la diferencia es significativa, el sistema lo resalta para que tomes acción.

### 9.5 Listado de Ventas

Ve a **📋 Ventas** para ver el historial completo:

- **Filtros**: por fecha (desde/hasta), tipo de negocio, método de pago
- **Tabla**: #venta, fecha, cliente, subtotal, IGV, total, método de pago
- **Acciones**: ver detalle completo o anular venta
- La anulación genera un asiento contable de reversión

### 9.6 Mantenimiento de Secciones

El módulo de **Secciones** permite agrupar las mesas del restaurante por zonas físicas (Terraza, Salón, VIP, Barra, etc.).

> Esta funcionalidad está disponible solo para negocios de tipo **restaurante** (`business_type = restaurant`).

---

#### 🎯 Escenario didáctico: \"El Segoviano\" crea sus zonas

**Objetivo:** El restaurante \"El Segoviano\" tiene 3 zonas físicas: Terraza (6 mesas), Salón Principal (10 mesas) y VIP (4 mesas). Quiere registrarlas en el sistema.

---

#### 1️⃣ Acceder al Módulo

| Opción | Ruta |
|--------|------|
| **Sidebar** | Haz clic en **🍽️ Secciones** |
| **Onboarding** | Si no hay mesas ni secciones, aparece un enlace directo en la pantalla de Mesas |

---

#### 2️⃣ Crear una Sección — Paso a Paso

**Ejemplo:** Crear la sección \"Terraza\"

1. Haz clic en **+ Nueva Sección**
2. Completa:

| Campo | Valor del ejemplo | Explicación |
|-------|------------------|-------------|
| **Nombre** | `Terraza` | Nombre visible en todos los desplegables |
| **Descripción** | `Mesas al aire libre, vista al mar` | Texto informativo (opcional) |
| **Orden** | `1` | Número para ordenar en listas (menor = primero) |

3. Haz clic en **Guardar**

**Resultado esperado:**
```
✅ Sección \"Terraza\" creada correctamente
```

**Repite** para las otras zonas:

| Sección | Descripción | Orden |
|---------|-------------|:-----:|
| `Salón Principal` | Zona interior del restaurante | 2 |
| `VIP` | Zona exclusiva para eventos | 3 |

---

#### 3️⃣ Ver las Secciones Creadas

En el listado de secciones verás:

| # | Nombre | Mesas | Descripción | Acciones |
|:-:|--------|:-----:|-------------|----------|
| 1 | 🪑 Terraza | 0 | Mesas al aire libre, vista al mar | ✏️ 🗑️ |
| 2 | 🏠 Salón Principal | 0 | Zona interior del restaurante | ✏️ 🗑️ |
| 3 | ⭐ VIP | 0 | Zona exclusiva para eventos | ✏️ 🗑️ |

La columna **Mesas** muestra cuántas mesas tiene asignadas cada sección (0 si son nuevas).

---

#### 4️⃣ Editar una Sección

**Ejemplo:** La \"Terraza\" ahora se llamará \"Terraza al Mar\"

1. Haz clic en **✏️ Editar** en la fila de \"Terraza\"
2. Cambia el nombre a `Terraza al Mar`
3. Haz clic en **Guardar**

---

#### 5️⃣ Eliminar una Sección

> ⚠️ **Regla de negocio:** No se puede eliminar una sección que tenga mesas asociadas.

**Caso A — Sección sin mesas (✅ permitido):**
1. Haz clic en **🗑️ Eliminar** en una sección vacía
2. Confirma → La sección se elimina

**Caso B — Sección con mesas (🚫 bloqueado):**
```
❌ Error: No se puede eliminar: la sección \"Salón Principal\" tiene 10 mesa(s) asociada(s)
```
Solución: Reasigna o elimina las mesas de esa sección primero.

---

#### 6️⃣ Vincular Secciones a Mesas

Al **crear** o **editar** una mesa en la pantalla **🪑 Mapa de Mesas**, aparece el campo:

| Campo | Comportamiento |
|-------|----------------|
| **Sección** | Desplegable con TODAS las secciones registradas + opción \"Sin sección\" |

**Ejemplo:** Crear mesa \"Mesa 1\" en la Terraza

| Campo | Valor |
|-------|-------|
| Número | `1` |
| Capacidad | `4` personas |
| Sección | **Terraza** (seleccionar del desplegable) |

**Resultado:**
```
Mesa #1 → Terraza  (la card muestra el badge \"Terraza\")
```

---

#### 7️⃣ Filtrar Mesas por Sección

En el **Mapa de Mesas**, hay un filtro desplegable en la parte superior:

| Opción del filtro | Resultado |
|-------------------|-----------|
| `Todas las secciones` | Muestra TODAS las mesas |
| `Terraza` | Solo mesas de la Terraza |
| `Salón Principal` | Solo mesas del Salón |
| `Sin sección` | Mesas sin sección asignada |

**Ejemplo:** Seleccionar \"Terraza\" en el filtro → solo se muestran las mesas con `section_id = Terraza`

---

#### 🔄 Flujo completo de ejemplo

```
1. Crear sección \"Terraza\"           → ✅ Creada
2. Crear sección \"Salón Principal\"    → ✅ Creada
3. Crear mesa \"Mesa 1\" → sección: Terraza → ✅ Badge \"Terraza\" visible
4. Crear mesa \"Mesa 2\" → sección: Terraza → ✅ Badge \"Terraza\" visible
5. Crear mesa \"Mesa 3\" → sección: Salón   → ✅ Badge \"Salón Principal\" visible
6. Filtrar por Terraza               → Se ven solo Mesa 1 y Mesa 2 ✅
7. Intentar eliminar \"Terraza\"       → ❌ Error: tiene 2 mesas
8. Eliminar Mesa 1 y Mesa 2          → ✅ Eliminadas
9. Eliminar \"Terraza\"                → ✅ Eliminada
```

![Placeholder: Captura del listado de secciones con 3 secciones]



### 9.7 Modificadores del Menú

Los **modificadores** son opciones adicionales que el cliente puede agregar a un plato al momento del pedido. Pueden tener costo adicional o ser gratuitos.

> Esta funcionalidad está disponible solo para negocios de tipo **restaurante** (`business_type = restaurant`).

---

#### 🎯 Escenario didáctico: Personalizar el \"Ceviche Clásico\"

**Objetivo:** El restaurante ofrece un Ceviche Clásico a S/28. El cliente quiere:
- Agregar **conchas negras** (+S/5)
- Que NO lleve **cebolla** (S/0, pedido especial)
- **Bien fresco** (observación para cocina)

El cocinero debe ver en su pantalla: `Ceviche Clásico | Conchas negras, Sin cebolla | 📝 Bien fresco`

---

#### 1️⃣ Crear el Plato con sus Modificadores

Ve a **🍽️ Menú → + Nuevo Ítem**

| Campo | Valor |
|-------|-------|
| Nombre | `Ceviche Clásico` |
| Categoría | `Entradas` |
| Precio | `28.00` |
| Tipo | `Plato` |
| Área de preparación | `🍳 Cocina` |

**Agrega los modificadores uno por uno:**

| # | Nombre | Precio adicional | Máx selección | Grupo |
|:-:|--------|:----------------:|:-------------:|-------|
| 1 | `Conchas negras` | S/ 5.00 | 3 | *(vacío)* |
| 2 | `Sin cebolla` | S/ 0.00 | 1 | *(vacío)* |
| 3 | `Extra queso` | S/ 3.00 | 1 | *(vacío)* |
| 4 | `Término medio` | S/ 0.00 | 1 | `Cocción` |
| 5 | `Bien cocido` | S/ 0.00 | 1 | `Cocción` |
| 6 | `Poco cocido` | S/ 0.00 | 1 | `Cocción` |

**Explicación de los grupos:**
- **Conchas negras** (máx 3) → Contador +/− en el modal, el cliente elige cuántas
- **Sin cebolla** (máx 1) → Checkbox, se marca o no
- **Cocción** (mismo grupo) → Radios 🔘, solo se puede elegir UNA opción

> 💡 Los modificadores con el **mismo nombre de grupo** se convierten en radios (excluyente). Los sin grupo son checkboxes o contadores.

---

#### 2️⃣ Ver los Modificadores en el Listado

En el listado del menú, el plato muestra:
```
Ceviche Clásico · S/ 28.00 · + 6 modificador(es)
```

---

#### 3️⃣ Tomar Pedido con Modificadores

**Flujo en la mesa:**

1. Mesa ocupada → click en **🍽️ Tomar Pedido**
2. Buscar \"Ceviche Clásico\" en el menú
3. Click en el plato → se abre el **ModifierBottomSheet**:

```
┌──────────────────────────────────────┐
│  Ceviche Clásico                      │
│  Precio base: S/ 28.00                │
│  Personalizá tu pedido                │
├──────────────────────────────────────┤
│  ☐ Conchas negras (+S/ 5.00)          │  ← Checkbox
│  ☐ Sin cebolla                        │  ← Checkbox (sin costo)
│  ☐ Extra queso (+S/ 3.00)             │  ← Checkbox
│                                        │
│  Elegí una opción                      │
│  ○ Término medio                       │  ← Radio (grupo \"Cocción\")
│  ○ Bien cocido                         │  ← Radio
│  ○ Poco cocido                         │  ← Radio
│                                        │
│  📝 Observaciones para cocina          │  ← Campo de texto
│  [Bien fresco                    ]    │
│                                        │
│  Ajuste por modificadores: +S/ 5.00   │
├──────────────────────────────────────┤
│  [     Agregar al pedido     ]        │
└──────────────────────────────────────┘
```

4. El mesero marca:
   - ✅ Conchas negras (+S/5.00)
   - ✅ Sin cebolla (S/0.00)
   - ✅ Término medio
   - Escribe: \"Bien fresco\"
5. Click en **Agregar al pedido**

---

#### 4️⃣ Ver el Item en el Resumen del Pedido

En la pantalla de la mesa, el pedido muestra:
```
📋 Pedido Actual
  1x Ceviche Clásico (Conchas negras, Término medio) +S/5.00 mods
                                        S/ 33.00
  ─────────────────────────────────────────────
  TOTAL                               S/ 33.00
```

---

#### 5️⃣ Enviar a Cocina

Click en **📨 Enviar a Cocina** → el cocinero ve:
```
┌──────────────────────────────────────┐
│  Mesa #5 · 2 comensales              │
│  🧑 Mesero 1                         │
├──────────────────────────────────────┤
│  1x Ceviche Clásico                   │
│  Conchas negras, Término medio       │
│  📝 Bien fresco                       │
└──────────────────────────────────────┘
```

**Nota:** Los modificadores con costo aparecen igual que los gratuitos — la cocina solo ve nombres y cantidades, sin precios.

---

#### 🧪 Casos adicionales de ejemplo

| Plato | Modificador | Costo | Tipo en UI |
|-------|-------------|:-----:|------------|
| Lomo Saltado | Extra salsa | S/ 0.00 | Checkbox |
| Lomo Saltado | Papas fritas | S/ 4.00 | Checkbox |
| Pizza | Pepperoni (hasta 3) | S/ 5.00 c/u | Contador +/− |
| Pizza | Tamaño: Personal/Mediana/Familiar | S/ 0.00 | Radios 🔘 |
| Jugo Natural | Sin azúcar | S/ 0.00 | Checkbox |
| Jugo Natural | Con hielo/Sin hielo | S/ 0.00 | Radios 🔘 |

---

#### 🔄 Flujo completo de ejemplo

```
1. Crear plato \"Ceviche Clásico\" S/28       → ✅ Creado
2. Agregar modificador \"Conchas negras\" +5   → ✅ Agregado
3. Agregar modificador \"Sin cebolla\" S/0     → ✅ Agregado
4. Agregar grupo \"Cocción\" con 3 opciones    → ✅ Grupo creado
5. Abrir mesa → Tomar Pedido → Click plato   → ✅ Modal con modificadores
6. Seleccionar: Conchas + Sin cebolla + TM   → ✅ Ajuste: +S/5.00
7. Escribir: \"Bien fresco\"                   → ✅ Nota guardada
8. Agregar al pedido → Ver resumen           → ✅ Total: S/33.00
9. Enviar a cocina                           → ✅ Cocinero ve todo
```

![Placeholder: Captura del formulario de creación de plato con modificadores]



### 9.8 Área de Preparación

> 🍽️ Esta funcionalidad está disponible solo para negocios de tipo **restaurante** (`business_type = restaurant`).

El **Área de Preparación** determina qué platos aparecen en el kanban de cocina y cuáles pasan directamente a barra o se entregan sin preparación.

---

#### 🎯 Escenario didáctico: Organizar el menú por áreas

**Objetivo:** El restaurante \"El Segoviano\" tiene 3 tipos de productos:

| Tipo | Ejemplo | ¿Se prepara en cocina? | ¿Va al kanban? |
|------|---------|:----------------------:|:--------------:|
| 🍳 **Platos** | Ceviche, Lomo Saltado | ✅ Sí, el cocinero lo prepara | ✅ Mostrar |
| 🍸 **Bebidas de barra** | Gaseosa, Cerveza | ❌ No, se sirven directo | ❌ Ocultar |
| 📦 **Productos** | Galletas, Snacks empaquetados | ❌ No, se entregan cerrados | ❌ Ocultar |

---

#### 1️⃣ Configurar el Área al Crear un Ítem

Al **crear** o **editar** un ítem en **🍽️ Menú**, aparece el campo:

| Valor | Significado | ¿Se ve en cocina? |
|-------|-------------|:-----------------:|
| 🍳 **Cocina** | El plato requiere preparación del cocinero | ✅ Sí |
| 🍸 **Barra** | Bebida o trago que se sirve sin pasar por cocina | ❌ No |
| 📦 **Ninguno** | Producto empaquetado, venta directa | ❌ No |

**Ejemplos de configuración:**

| Ítem | Tipo | Área de preparación | Resultado |
|------|:----:|:-------------------:|-----------|
| `Ceviche Clásico` | food | 🍳 **Cocina** | ✅ Visible en cocina |
| `Lomo Saltado` | food | 🍳 **Cocina** | ✅ Visible en cocina |
| `Coca Cola` | beverage | 🍸 **Barra** | ❌ Oculta en cocina |
| `Cerveza Artesanal` | beverage | 🍸 **Barra** | ❌ Oculta en cocina |
| `Galleta Empacada` | food | 📦 **Ninguno** | ❌ Oculta en cocina |
| `Papas Fritas Bolsa` | food | 📦 **Ninguno** | ❌ Oculta en cocina |

![Placeholder: Captura del campo \"Área de preparación\" con las 3 opciones]

---

#### 2️⃣ Comparativa: Antes vs Ahora

**Antes** (solo `item_type`):
```
Los jugos naturales (item_type=beverage) se ocultaban de cocina
Incluso si necesitaban preparación (exprimir naranjas)
```

**Ahora** (con `preparation_area`):
```
Jugo Natural → item_type=beverage → preparation_area=🍳cocina  ✅ Visible
Coca Cola    → item_type=beverage → preparation_area=🍸barra   ❌ Oculta

¡Cada item decide independientemente de su tipo!
```

---

#### 3️⃣ ¿Qué pasa con los ítems antiguos (legacy)?

Los ítems creados antes de esta funcionalidad NO tienen `preparation_area`. El sistema usa una **regla de compatibilidad**:

```
Si preparation_area está vacío → usa el fallback antiguo:
  - Si item_type = \"beverage\" → se OCULTA de cocina
  - Si item_type ≠ \"beverage\" → se MUESTRA en cocina
```

| Escenario | item_type | preparation_area | ¿Visible? |
|-----------|:---------:|:----------------:|:---------:|
| Plato legacy (no se tocó) | food | *(vacío)* | ✅ Sí (fallback) |
| Bebida legacy (no se tocó) | beverage | *(vacío)* | ❌ No (fallback) |
| Plato nuevo configurado | food | cocina | ✅ Sí |
| Bebida reconfigurada | beverage | cocina | ✅ Sí (¡forzado!) |

---

#### 4️⃣ Verificar en el Kanban de Cocina

**Escenario:** Un cliente pide:
- 1x Ceviche Clásico (🍳 cocina)
- 1x Lomo Saltado (🍳 cocina)
- 2x Coca Cola (🍸 barra)
- 1x Galleta (📦 ninguno)

**Lo que ve el cocinero:**
```
┌──────────────────────────────────────┐
│  ⏳ Pendientes (2)                    │
├──────────────────────────────────────┤
│  Mesa #5 · 4 comensales               │
│  🧑 Mesero 1                          │
│                                      │
│  1x Ceviche Clásico                  │  ← ✅ SE MUESTRA (cocina)
│  1x Lomo Saltado                     │  ← ✅ SE MUESTRA (cocina)
└──────────────────────────────────────┘

# Las Coca Cola y Galleta NO aparecen
# El cocinero solo ve lo que debe cocinar
```

**Lo que NO ve el cocinero** (se sirven directo):
```
❌ 2x Coca Cola  → preparation_area = barra  (va a barra)
❌ 1x Galleta    → preparation_area = none   (se entrega directo)
```

---

#### 🔄 Flujo completo de ejemplo

```
1. Crear \"Ceviche Clásico\" → área: 🍳 Cocina     ✅
2. Crear \"Lomo Saltado\"   → área: 🍳 Cocina     ✅
3. Crear \"Coca Cola\"      → área: 🍸 Barra      ✅
4. Crear \"Galleta\"        → área: 📦 Ninguno    ✅
5. Crear pedido con los 4 items                  ✅
6. Enviar a cocina                                ✅
7. Cocina muestra: Ceviche + Lomo (2 items)       ✅
8. Cocina NO muestra: Coca Cola + Galleta (0)     ✅
```

![Placeholder: Captura del kanban de cocina filtrando solo área \"Cocina\"]



## 10. Settings — Personalización

El módulo de Ajustes permite personalizar la apariencia visual del sistema.

> ⚠️ Solo accesible para el rol **admin**.

### 8.1 Paletas Predefinidas

Puedes elegir entre 4 paletas con un solo clic:

| Paleta | Colores principales | Vibra |
|--------|-------------------|-------|
| 🔵 **Azul Marino** | Azul corporativo, blanco | Profesional, serio |
| 🟢 **Verde Bosque** | Verde, crema, toques dorados | Natural, fresco |
| 🔴 **Rojizo Cálido** | Rojo oscuro, ámbar, fondo crema | Cálido, acogedor |
| 🟣 **Púrpura** | Púrpura, lavanda, blanco | Moderno, creativo |

### 8.2 Personalización Individual

10 colores configurables con selector visual:

| Color | Aplica a |
|-------|----------|
| **Primario** | Header, botones principales, enlaces |
| **Secundario** | Botones secundarios, acentos |
| **Acento** | Elementos destacados, badges |
| **Fondo** | Fondo general de la página |
| **Superficie** | Tarjetas, modales, paneles |
| **Texto Principal** | Títulos, párrafos |
| **Texto Secundario** | Subtítulos, etiquetas, metadatos |
| **Éxito** | KPIs positivos, mensajes de éxito |
| **Advertencia** | Alertas, precauciones |
| **Error** | Errores, KPIs negativos |

### 8.3 Información de Empresa

La sección inferior muestra datos de configuración (solo lectura):

| Campo | Descripción |
|-------|-------------|
| **Moneda** | Soles (PEN) |
| **Zona Horaria** | America/Lima |
| **Formato de Fecha** | DD/MM/YYYY |

> 💡 Los cambios de paleta se aplican inmediatamente a toda la interfaz sin recargar la página.

---

## 11. Gestión de Usuarios (Admin)

> 👑 Esta sección es **exclusiva del rol admin**. Si no eres admin, no verás estas opciones.

### 9.1 Crear un Usuario

1. En la barra de navegación, haz clic en **👥 Admin Users** (solo visible para rol `admin`)
2. Haz clic en **+ Crear Usuario**
3. Completa los datos requeridos:

| Campo | Descripción | Restricciones |
|-------|-------------|---------------|
| **Email** | Correo electrónico del usuario | Único, formato válido |
| **Nombre completo** | Nombre y apellido | Mínimo 2 caracteres |
| **Rol** | admin | Rol con acceso completo |
| **Contraseña** | Contraseña temporal | Mínimo 8 caracteres, 1 mayúscula, 1 número |

3. El usuario se crea en el mismo tenant (empresa) que el admin
4. Entrega la contraseña temporal al usuario — deberá cambiarla

> 💡 La contraseña temporal debe cumplir: mínimo 8 caracteres, al menos 1 mayúscula (`A-Z`), al menos 1 número (`0-9`).

### 9.2 Listar Usuarios

La lista de usuarios muestra:

| Columna | Descripción |
|---------|-------------|
| **Email** | Correo del usuario |
| **Nombre** | Nombre completo |
| **Rol** | Nivel de acceso |
| **Activo** | Si la cuenta está habilitada |
| **Verificado** | Si el email fue verificado (funcionalidad futura) |
| **Creado** | Fecha de creación de la cuenta |

Filtros disponibles: por rol, por estado (activo/inactivo), búsqueda por texto.

---

## 12. FAQ / Problemas Comunes

### Acceso y Login

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| **"Email o contraseña inválidos"** | Credenciales incorrectas | Verifica email y contraseña. Revisa mayúsculas/minúsculas |
| **"Cuenta bloqueada temporalmente"** | 10 intentos fallidos consecutivos | Espera 15 minutos. El contador se reinicia automáticamente |
| **"Demasiados intentos"** | Rate limiting — más de 5 intentos/minuto | Espera 60 segundos. El límite es por IP |
| **No llego a la pantalla de login** | Servidor caído | Verifica que Docker esté corriendo: `docker-compose ps` |
| **Pantalla en blanco** | Error de JavaScript | Abre las DevTools del navegador (F12), revisa la consola |

### Dashboard y Simulación

| Problema | Solución |
|----------|----------|
| **Dashboard sin datos** | Ejecuta el Setup Wizard primero. Sin simulación no hay datos que mostrar |
| **"Error al ejecutar simulación"** | Revisa que todos los campos del Setup tengan valores válidos (no negativos, no vacíos) |
| **KPIs en rojo o negativos** | Es esperado si la simulación no es rentable. Ajusta variables en el Simulador |
| **El gráfico no se ve** | Algunos gráficos requieren datos. Si no hay flujo de caja calculado, aparece vacío |

### Kárdex

| Problema | Solución |
|----------|----------|
| **No encuentro el producto que registré** | Usa el código exacto. El código distingue mayúsculas/minúsculas |
| **Error "Stock insuficiente"** | La cantidad de salida supera el stock actual. Registra una entrada primero |
| **El costo promedio no cambia** | Solo las entradas modifican el costo promedio. Las salidas usan el costo existente |

### Navegación y UI

| Problema | Solución |
|----------|----------|
| **La página tarda en cargar** | La primera vez que visitas una sección, se descarga el código (code-splitting). Es normal un spinner de 100-300ms |
| **"No tienes permisos para acceder"** | Tu rol no tiene acceso a esa sección. Contacta a tu admin |
| **Los colores no se aplican** | Recarga la página (F5). Si persiste, el backend podría no estar guardando la paleta |

### Backend / Conexión

| Problema | Solución |
|----------|----------|
| **Error "Failed to fetch"** | El backend no responde. Verifica `docker-compose logs backend` |
| **Error 500** | Error interno del servidor. Revisa los logs del backend |
| **Error 422** | Datos enviados con formato inválido. Revisa campos requeridos |

---

> 📞 **¿No encuentras tu problema?** Consulta el [Manual de Administrador](manual-admin.md) para troubleshooting avanzado o contacta al equipo técnico.

---

> IaaS-RonSys · El Segoviano · v0.3.0 🐟  
> *"Simula. Analiza. Decide. — Todo en un solo lugar"*
