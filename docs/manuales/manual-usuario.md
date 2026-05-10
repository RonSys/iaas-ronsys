# 📘 Manual de Usuario — IaaS-RonSys

> **Versión:** 1.0  
> **Fecha:** 2026-05-10  
> **Sistema:** IaaS-RonSys v0.1.0 — ERP SaaS Financiero-Contable  
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
8. [Settings — Personalización](#8-settings--personalización)
9. [Gestión de Usuarios (Admin)](#9-gestión-de-usuarios-admin)
10. [FAQ / Problemas Comunes](#10-faq--problemas-comunes)

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

| Servicio | URL | Propósito |
|----------|-----|-----------|
| **Aplicación Web** | `http://localhost:5173` | Interfaz de usuario principal |
| **API / Backend** | `http://localhost:8000` | Endpoints REST |
| **Swagger Docs** | `http://localhost:8000/docs` | Documentación interactiva de API |

### Credenciales de Demostración

| Campo | Valor |
|--------|-------|
| Email | `admin@elsegoviano.pe` |
| Contraseña | `admin123` |
| Rol | admin |

> ⚠️ **Cambia la contraseña** apenas ingreses. Esta cuenta tiene acceso total al sistema.

### Iniciar Sesión

1. Abre `http://localhost:5173` en tu navegador
2. Aparece la pantalla de login con los campos **Email** y **Contraseña**
3. Ingresa tus credenciales
4. Haz clic en **Iniciar Sesión** (o presiona Enter)

La sesión dura **15 minutos** antes de requerir renovación automática del token. Si cierras la pestaña, deberás iniciar sesión nuevamente.

### Roles y Permisos

| Rol | Crear Usuarios | Setup/Simulador | Kárdex | Ajustes (Branding) | Ver Reportes |
|-----|:---:|:---:|:---:|:---:|:---:|
| 👑 **admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🧑‍💼 **manager** | ❌ | ✅ | ✅ | ✅ | ✅ |
| 👨‍🍳 **operator** | ❌ | ✅ | ✅ | ❌ | ✅ |
| 👀 **viewer** | ❌ | ❌ | ❌ | ❌ | ✅ |

### Cerrar Sesión

Para cerrar sesión, simplemente cierra la pestaña del navegador. El sistema utiliza tokens de sesión que expiran automáticamente tras 7 días de inactividad.

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

> 💡 Si no ves datos, haz clic en **🔄 Actualizar** o ejecuta primero el **Setup Wizard**.

---

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

## 8. Settings — Personalización

El módulo de Ajustes permite personalizar la apariencia visual del sistema.

> ⚠️ Solo accesible para roles **admin** y **manager**.

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

## 9. Gestión de Usuarios (Admin)

> 👑 Esta sección es **exclusiva del rol admin**. Si no eres admin, no verás estas opciones.

### 9.1 Crear un Usuario

1. Accede al panel de administración de usuarios (requiere implementación de UI de admin)
2. Completa los datos requeridos:

| Campo | Descripción | Restricciones |
|-------|-------------|---------------|
| **Email** | Correo electrónico del usuario | Único, formato válido |
| **Nombre completo** | Nombre y apellido | Mínimo 2 caracteres |
| **Rol** | admin / manager / operator / viewer | Debe ser un rol válido |
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

## 10. FAQ / Problemas Comunes

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

> IaaS-RonSys · El Segoviano · v0.1.0  
> *"Simula. Analiza. Decide. — Todo en un solo lugar"*
