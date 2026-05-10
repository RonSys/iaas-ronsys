# 🚀 Guía de Inicio Rápido — IaaS-RonSys

> **Versión:** 1.0  
> **Fecha:** 2026-05-10  
> **Sistema:** IaaS-RonSys v0.1.0 — ERP SaaS Financiero-Contable  
> **Franquicia:** El Segoviano 🐟

---

## 📋 ¿Qué es IaaS-RonSys?

IaaS-RonSys es el sistema ERP financiero-contable de la franquicia **"El Segoviano"**. Te permite:

- Simular la inversión de una cevichería nueva 🔧
- Generar estados financieros automáticamente (PYG, Balance, Ratios) 📊
- Controlar inventarios con kárdex valorizado 📦
- Personalizar la apariencia del sistema 🎨

---

## 🔗 Acceso al Sistema

| Elemento | URL |
|----------|-----|
| **Aplicación Web** | `http://localhost:5173` |
| **API / Backend** | `http://localhost:8000` |
| **Documentación API (Swagger)** | `http://localhost:8000/docs` |

### Credenciales de Demostración

| Campo | Valor |
|--------|-------|
| **Email** | `admin@elsegoviano.pe` |
| **Contraseña** | `admin123` |

> ⚠️ Esta es una cuenta demo de administrador. Cambia la contraseña apenas ingreses por seguridad.

---

## 🏃 Primeros Pasos (5 minutos)

### Paso 1: Iniciar Sesión

1. Abre `http://localhost:5173` en tu navegador
2. Ingresa el email `admin@elsegoviano.pe` y la contraseña `admin123`
3. Haz clic en **Iniciar Sesión**

Verás el **Dashboard** con KPIs en cero — es normal, todavía no hay simulación.

### Paso 2: Configurar una Empresa (Setup Wizard)

1. En la barra de navegación superior, haz clic en **🏗️ Setup**
2. Llena los datos de inversión de tu cevichería:

| Sección | Qué configurar | Ejemplo |
|---------|---------------|---------|
| **Inversión** | Capital propio + préstamo | S/ 50,000 + S/ 30,000 |
| **Instalación** | Equipos, muebles, licencias | S/ 15,000 equipos |
| **Gastos Fijos** | Alquiler, sueldos, servicios | S/ 2,500 alquiler |
| **Proyección** | Ventas por mes, costo de insumos | S/ 25,000/mes, 40% costo |

3. Haz clic en **⚡ Ejecutar Simulación**
4. Verás un resumen con KPIs financieros: ventas totales, utilidad neta, payback

### Paso 3: Explorar Resultados

Después de la simulación, visita:

| Sección | Qué ver |
|---------|---------|
| **📊 Dashboard** | 4 KPIs principales (ventas, utilidad neta, EBITDA, activos), gráficos de flujo de caja |
| **📋 Reportes** | Estado de Resultados (PYG), Balance General, BCSS, Ratios con semáforo 🟢🟡🔴 |
| **🎮 Simulador** | Sliders interactivos para probar escenarios "¿qué pasa si...?" |

---

## 🧭 Navegación General

La barra superior tiene 6 secciones:

| Menú | Ruta | ¿Qué hace? |
|------|------|-----------|
| 📊 **Dashboard** | `/` | Panel principal — KPIs, gráficos, ratios |
| 🏗️ **Setup** | `/setup` | Configuración inicial de inversión |
| 🎮 **Simulador** | `/simulador` | Sliders interactivos + escenarios comparativos |
| 📋 **Reportes** | `/reportes` | PYG, Balance, BCSS, Ratios detallados |
| 📦 **Kárdex** | `/kardex` | Inventario — productos, entradas, salidas |
| ⚙️ **Ajustes** | `/settings` | Paleta de colores, branding (solo admin/manager) |

---

## 👤 Roles de Usuario

El sistema tiene 4 roles con permisos diferenciados:

| Rol | Capacidades |
|-----|------------|
| 👑 **admin** | Acceso total — crear usuarios, configurar empresa, ver todo |
| 🧑‍💼 **manager** | Operar sistema + cambiar branding (no administra usuarios) |
| 👨‍🍳 **operator** | Registrar operaciones diarias (kárdex, ventas) |
| 👀 **viewer** | Solo lectura — ver reportes, dashboard |

---

## 📦 Kárdex / Inventario (Básico)

Para registrar productos en inventario:

1. Ve a **📦 Kárdex**
2. Haz clic en **+ Producto** — ingresa código, nombre, stock inicial y costo unitario
3. Selecciona un producto y usa **+ Entrada** para compras o **- Salida** para ventas/mermas
4. El sistema calcula automáticamente el **costo promedio ponderado**

---

## 🎨 Personalización Rápida

Para cambiar los colores del sistema:

1. Ve a **⚙️ Ajustes** (requiere rol admin o manager)
2. Elige una paleta predefinida: Azul Marino, Verde Bosque, Rojizo Cálido o Púrpura
3. O personaliza cada color individualmente con los selectores de color
4. Los cambios se aplican al instante en toda la interfaz

---

## ❓ Problemas Comunes

| Problema | Solución |
|----------|----------|
| **No veo datos en el Dashboard** | Ejecuta primero el Setup Wizard (🏗️ Setup) |
| **"Email o contraseña inválidos"** | Verifica email y contraseña. Si falla 10 veces, la cuenta se bloquea 15 min |
| **"Cuenta bloqueada"** | Espera 15 minutos o pide a un admin que la desbloquee |
| **La página se ve rara / sin colores** | Recarga con F5. Si persiste, el backend puede estar caído |
| **Error al guardar producto en Kárdex** | Asegúrate de que el código del producto no esté duplicado |
| **No puedo acceder a Ajustes** | Solo roles `admin` y `manager`. Pide cambio de rol a tu admin |

---

## 📞 ¿Necesitas Ayuda?

- **Manual completo**: consulta `manual-usuario.md` para guía detallada de cada módulo
- **Manual de administrador**: consulta `manual-admin.md` para gestión de usuarios y troubleshooting avanzado
- **API Reference**: `http://localhost:8000/docs` — documentación técnica de todos los endpoints

---

> IaaS-RonSys · El Segoviano · v0.1.0  
> *"Inteligencia financiera al alcance de tu cevichería"*
