# 🎭 Tests E2E — IaaS-RonSys Web

> Suite de tests end-to-end con Playwright para validar flujos completos de usuario.

---

## 📋 Requisitos

- Node.js ≥ 18
- Dependencias instaladas (`npm install` en `apps/web/`)
- Playwright browsers instalados:
  ```bash
  npx playwright install chromium
  ```

Si el sistema operativo no es soportado por Playwright (ej. Ubuntu 26.04),
los tests están diseñados pero no podrán ejecutarse hasta que el proyecto
corra en un entorno compatible (CI, dev container, etc.).

---

## 🚀 Ejecución

```bash
# Todos los tests
npm run test:e2e

# UI mode (debug visual)
npm run test:e2e:ui

# Un archivo específico
npx playwright test e2e/login.spec.ts

# Un test específico por nombre
npx playwright test -g "login exitoso"

# Con reporte HTML
npx playwright test --reporter=html
npm run test:e2e:report
```

---

## 📂 Estructura

```
e2e/
├── playwright.config.ts        ← Config: baseURL, timeout, browsers, webServer
├── fixtures/
│   ├── mocks.ts                ← Mocks de API (auth, contabilidad, kárdex, settings)
│   └── auth.fixture.ts         ← Fixture: login automático vía refresh token
├── login.spec.ts               ← 7 tests: formulario, login, errores, rate limit, logout
├── dashboard.spec.ts           ← 5 tests: KPIs, ratios, gráficos, BCSS
├── simulador.spec.ts           ← 5 tests: sliders, resultados, escenarios, comparativa
├── reportes.spec.ts            ← 4 tests: PYG, Balance, BCSS, Ratios tabs
├── kardex.spec.ts              ← 6 tests: inventario, movimientos, modales, entrada/salida
├── settings.spec.ts            ← 4 tests: paleta, presets, color pickers, preview
└── README.md                   ← Este archivo
```

---

## 🧪 Tests por archivo

### `login.spec.ts` (7 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | Formulario de login | Campos email, password, botón, título |
| 2 | Login exitoso | Redirección a `/` después de auth |
| 3 | Credenciales inválidas | Mensaje "Email o contraseña inválidos" |
| 4 | Email vacío | Validación client-side "El email es requerido" |
| 5 | Password vacío | Validación client-side "La contraseña es requerida" |
| 6 | Rate limiting 429 | Mensaje "Demasiados intentos" |
| 7 | Usuario autenticado → login | Redirige a `/` sin mostrar login |

### `dashboard.spec.ts` (5 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | KPIs visibles | Título "Panel de Control", iconos de KPI |
| 2 | KPICard con valores | Emojis 💰📈💎🏦 visibles |
| 3 | Ratios con semáforo | Sección "🚦 Ratios Financieros" + tarjetas |
| 4 | Gráfico Recharts | SVG `.recharts-surface` renderizado |
| 5 | BCSS con totales | "✅ Sí" (is_balanced) visible |

### `simulador.spec.ts` (5 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | Sliders visibles | 5 sliders con labels y valores default |
| 2 | Botón manual | "🔄 Simular Ahora" clickeable |
| 3 | Resultados en vivo | "📊 Resultados en Vivo" + ventas/utilidad |
| 4 | Guardar escenario | Tabla de comparativa aparece con "Realista" |
| 5 | Columnas comparativa | Precio, Ventas, Utilidad, Payback, VAN visibles |

### `reportes.spec.ts` (4 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | 4 tabs visibles | PYG, Balance, BCSS, Ratios |
| 2 | PYG datos | Utilidad Bruta, EBITDA, UTILIDAD NETA |
| 3 | Balance datos | ACTIVOS, PASIVO + PATRIMONIO, TOTAL ACTIVOS |
| 4 | Ratios datos | Liquidez Corriente, Margen Bruto, ROE con valores |

### `kardex.spec.ts` (6 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | Productos en inventario | Arroz y Pollo visibles en grid |
| 2 | Seleccionar producto | Tabla de movimientos con "Compra inicial" |
| 3 | Modal nuevo producto | Abre/cierra con Cancelar |
| 4 | Botones deshabilitados | +Entrada y -Salida disabled sin selección |
| 5 | Registrar entrada | Modal → llenar → submit → se cierra |
| 6 | Registrar salida | Modal → llenar → submit → se cierra |

### `settings.spec.ts` (4 tests)
| # | Test | Qué valida |
|---|------|-----------|
| 1 | Paleta y presets | "🎨 Paleta de Colores" + 4 presets |
| 2 | 10 color pickers | `input[type="color"]` count = 10 |
| 3 | Vista previa | "👁️ Vista Previa" + labels Primario/Acento/Éxito/Error |
| 4 | Info empresa | PEN, America/Lima visibles |

---

## 🔧 Credenciales de prueba

| Campo | Valor |
|-------|-------|
| Email | `admin@elsegoviano.pe` |
| Password | `admin123` |

Estas credenciales son para los tests mock. En el backend real, deben existir
como seed data (ver `apps/backend/scripts/seed.py`).

---

## 🏗️ Arquitectura de Mocks

Los tests no dependen del backend real. Usan `page.route()` de Playwright para
interceptar todas las llamadas HTTP y devolver datos mock. Esto permite:

- Tests autónomos (sin backend corriendo)
- Respuestas determinísticas
- Simulación de errores (401, 429, 423)

Los mocks están centralizados en `fixtures/mocks.ts` con funciones helper:
- `mockLogin(page, status)` — simula login con diferentes códigos HTTP
- `mockSetup(page)` — respuesta completa del simulador
- `mockPYG(page)` / `mockBalance(page)` / `mockRatios(page)` — datos contables
- `mockKardexInventory(page)` / `mockKardexDetail(page)` — inventario
- `mockPalette(page)` / `mockSettings(page)` — configuración

---

## ⚠️ Notas

- **Sistema operativo no soportado**: Si Playwright no puede instalar Chromium
  (ej. Ubuntu 26.04), los tests no se ejecutarán. Usar CI o dev container.
- **Timeout**: 30s por test, 10s para expect. Ajustar en `playwright.config.ts` si es necesario.
- **Vite dev server**: El config incluye `webServer` que levanta `npm run dev` automáticamente.
- **Paralelo**: `fullyParallel: true` — todos los tests corren en paralelo por defecto.

---

> **Última actualización**: 2026-05-10
