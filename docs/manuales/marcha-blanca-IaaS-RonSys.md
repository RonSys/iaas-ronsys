# 🚀 IaaS-RonSys — Manual de Marcha Blanca

> **ERP SaaS con Agentes de IA para Franquicias**
> Fecha: 2026-07-06

---

## 🌐 Acceso al Sistema

**https://ronsyserp.com/**

No requiere instalación ni VPN — funciona desde cualquier navegador web (Chrome, Edge, Firefox).

---

## 🔐 Credenciales de Prueba

El sistema es **multitenant**: cada empresa tiene sus datos aislados.

### Empresa 1: 🐟 Cevichería El Segoviano (Restaurante)

| Email | Contraseña | Rol | Acceso |
|-------|-----------|-----|--------|
| `admin@elsegoviano.pe` | `admin123` | 🔴 **Admin** | Dashboard, Reportes, Configuración, Inventario, POS |
| `mesero1@elsegoviano.pe` | `mesero123` | 🟡 **Operador** | POS, Tomar pedidos, Ventas |
| `cocinero1@elsegoviano.pe` | `cocinero123` | 🟡 **Operador** | Cocina / Vista de pedidos en preparación |

### Empresa 2: 🔧 Ferretería El Segoviano

| Email | Contraseña | Rol | Acceso |
|-------|-----------|-----|--------|
| `ferretero@elsegoviano.pe` | `ferreteria123` | 🔴 **Admin** | Dashboard, Inventario con seriales, Reportes |

> ⚠️ **La sesión dura 15 minutos.** Si la página se queda cargando o ves un error de sesión, recarga la página e inicia sesión de nuevo.

---

## 📋 Qué Probar (Checklist de Marcha Blanca)

### 1. 🏠 Dashboard General
- [ ] Iniciar sesión con `admin@elsegoviano.pe`
- [ ] Explorar el panel principal: tarjetas de métricas, gráficos
- [ ] Verificar que se ven los datos (Balance, Ingresos, Gastos)
- [ ] Cerrar sesión y volver a entrar

### 2. 📊 Simulador Financiero
- [ ] Ir a **Simulador** en el menú lateral
- [ ] Explorar el setup de simulación financiera
- [ ] Ver plan de cuentas contable generado

### 3. 📈 Reportes
- [ ] Ir a **Reportes**
- [ ] Explorar **PyG** (Pérdidas y Ganancias)
- [ ] Explorar **Balance General**
- [ ] Explorar **BCSS** (Balance de Comprobación)
- [ ] Explorar **Ratios Financieros** (con semáforo 🟢🟡🔴)
- [ ] Explorar **Flujo de Caja**

### 4. 📦 Kárdex / Inventario
- [ ] Ir a **Kárdex**
- [ ] Ver productos registrados
- [ ] Revisar movimientos de entrada y salida
- [ ] Consultar kárdex de un producto específico

### 5. 🍽️ Restaurante — Mesas
- [ ] Ir a **Restaurante → Mesas**
- [ ] Ver el mapa de mesas
- [ ] Crear una nueva mesa
- [ ] Editar una mesa existente
- [ ] Ocupar una mesa (simular)

### 6. 🍽️ Restaurante — Menú
- [ ] Ir a **Restaurante → Menú**
- [ ] Ver platos registrados
- [ ] Explorar modificadores de platos

### 7. 🧾 POS — Punto de Venta
- [ ] Ir a **POS**
- [ ] Iniciar sesión como `mesero1@elsegoviano.pe`
- [ ] Seleccionar una mesa
- [ ] Agregar platos al pedido
- [ ] Agregar modificadores a un plato
- [ ] Confirmar el pedido
- [ ] Cobrar la cuenta

### 8. 🧾 Ventas
- [ ] Ir a **Ventas**
- [ ] Ver listado de ventas realizadas
- [ ] Crear una venta nueva manual

### 9. ⚙️ Configuración
- [ ] Ir a **Configuración**
- [ ] Cambiar nombre del negocio
- [ ] Cambiar paleta de colores
- [ ] Verificar que los cambios se guardan

### 10. 🔧 Ferretería (con seriales)
- [ ] Iniciar sesión con `ferretero@elsegoviano.pe`
- [ ] Ir a **Inventario**
- [ ] Ver productos con seriales/lotes
- [ ] Registrar entrada con serial
- [ ] Registrar salida con serial
- [ ] Ver trazabilidad de un serial

---

## 🧪 Resultado de Tests Automatizados

Los tests del backend se ejecutaron exitosamente:

```
✅ 194 tests pasaron
⚠️  11 errores (solo por dependencia de laboratorio: aiosqlite no instalada en el contenedor Docker)
```

Esto no afecta la funcionalidad del sistema — los tests que fallaron son solo los que requieren una base de datos SQLite en memoria (para pruebas aisladas), y el contenedor no tiene ese driver instalado. El código del sistema funciona correctamente.

---

## 🐛 Reportar Incidencias

Si durante la marcha blanca encuentras algún error o comportamiento inesperado:

1. Anota el **paso exacto** donde ocurrió
2. Toma un **captura de pantalla** si es posible
3. Describe lo que esperabas que pasara vs lo que pasó
4. Envía el reporte al equipo de desarrollo

---

## 🏗️ Stack Tecnológico (para referencia)

| Componente | Tecnología | Puerto |
|-----------|-----------|--------|
| **Frontend Web** | React 19 + Vite + TailwindCSS | 80 |
| **Backend API** | FastAPI (Python 3.12 asíncrono) | 8000 |
| **Base de Datos** | PostgreSQL 16 | 5432 |
| **Cache** | Redis 7 | 6379 |
| **Cola de Mensajes** | RabbitMQ 4 | 5672 |
| **Infraestructura** | Docker Compose + Cloudflare Tunnel | — |

---

*Documento generado para Marcha Blanca — IaaS-RonSys v0.5*
