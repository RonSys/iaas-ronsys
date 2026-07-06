# 🏛️ Arquitectura Frontend — IaaS-RonSys

> **Stack**: React 19 + Vite 6 + TailwindCSS 3.4 + TypeScript 5.7  
> **Patrón**: SPA con router, code-splitting, hooks como capa de datos

---

## 📐 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────┐
│                      index.html                         │
│                    <div id="root"/>                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                     main.tsx                            │
│              createRoot + <StrictMode>                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      App.tsx                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │           usePalette() → :root CSS vars          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              <BrowserRouter>                      │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │  │
│  │  │ Suspense   │ │ Suspense   │ │ Suspense   │   │  │
│  │  │ Dashboard  │ │ Setup      │ │ Simulador  │   │  │
│  │  │ (lazy)     │ │ (lazy)     │ │ (lazy)     │   │  │
│  │  └────────────┘ └────────────┘ └────────────┘   │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │  │
│  │  │ Suspense   │ │ Suspense   │ │ Suspense   │   │  │
│  │  │ Reportes   │ │ Kárdex     │ │ Ajustes    │   │  │
│  │  │ (lazy)     │ │ (lazy)     │ │ (lazy)     │   │  │
│  │  └────────────┘ └────────────┘ └────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🧱 Capas de la Aplicación

```
┌──────────────────────────────────────────────────────┐
│                    PAGES (6)                          │
│  Dashboard  SetupWizard  Simulator  Reports          │
│  Kardex     Settings                                 │
│                                                      │
│  Responsabilidad: Composición de componentes,        │
│  llamadas a hooks, estado local de UI                │
└──────────────────────┬───────────────────────────────┘
                       │ usa
┌──────────────────────▼───────────────────────────────┐
│                  COMPONENTS                           │
│  AppShell  KPICard  CashflowChart  TrafficLight      │
│  Skeleton  SliderField  FormField  Modals           │
│                                                      │
│  Responsabilidad: UI reutilizable, sin lógica        │
│  de negocio, reciben props y renderizan              │
└──────────────────────┬───────────────────────────────┘
                       │ usa
┌──────────────────────▼───────────────────────────────┐
│                    HOOKS (2)                          │
│  usePalette()      useAccounting()                   │
│  useBCSS()         useIncomeStatement()              │
│  useBalanceSheet() useRatios()                       │
│  useKardexInventory() useKardex()                    │
│  useSimulation()                                     │
│                                                      │
│  Responsabilidad: Fetch + estado (data/loading/      │
│  error/refetch), transformación de datos             │
└──────────────────────┬───────────────────────────────┘
                       │ usa
┌──────────────────────▼───────────────────────────────┐
│                  SERVICES (1)                         │
│  api.ts — apiFetch wrapper + 15 endpoint functions   │
│                                                      │
│  Responsabilidad: HTTP calls, headers, error         │
│  handling, serialización JSON                        │
└──────────────────────┬───────────────────────────────┘
                       │ usa
┌──────────────────────▼───────────────────────────────┐
│                    TYPES (3)                          │
│  accounting.ts  settings.ts  index.ts                │
│                                                      │
│  Responsabilidad: Interfaces TypeScript,             │
│  espejo de Pydantic schemas del backend              │
└──────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### 1. Carga de Paleta (usePalette)

```
App mount
  │
  ▼
usePalette()
  │
  ├─ GET /api/settings/palette
  │     │
  │     ▼
  │   setPalette(data)
  │     │
  │     ▼
  │   document.documentElement.style.setProperty(...)
  │     │
  │     ▼
  │   Tailwind theme.extend.colors.brand.* ← CSS vars
  │     │
  │     ▼
  │   Todos los componentes reaccionan
  │
  └─ changePalette(p) → PATCH /api/settings/palette → re-apply
```

### 2. Fetch de Datos Contables (useAccounting)

```
Page mount / user action
  │
  ▼
useBCSS() / useIncomeStatement() / ...
  │
  ├─ loading = true
  ▼
  apiFetch("/api/accounting/bcss")
  │
  ├─ Éxito → data = response, loading = false
  │
  └─ Error → error = message, loading = false

Page re-render con { data, loading, error }
```

### 3. Simulación (useSimulation)

```
SetupWizard / Simulator
  │
  ▼
User cambia sliders → debounce 400ms
  │
  ▼
POST /api/accounting/setup (InvestmentInput)
  │
  ▼
FinancialReportResponse { bcss, income_statement, balance_sheet, ratios }
  │
  ▼
Render KPIs, PYG, Balance, Ratios
```

---

## 🎨 Sistema de Branding / Temas

```
┌────────────────────────────────────────────────────┐
│                 GET /api/settings/palette          │
│                        │                           │
│            ┌───────────▼──────────┐                │
│            │   usePalette hook    │                │
│            └───────────┬──────────┘                │
│                        │                           │
│        ┌───────────────┼───────────────┐           │
│        ▼               ▼               ▼           │
│  :root CSS vars   React state    PATCH API         │
│  --color-primary  palette obj    (al cambiar)      │
│  --color-sec...                                  │
│        │                                           │
│        ▼                                           │
│  tailwind.config.ts                                │
│  theme.extend.colors.brand.*                       │
│        │                                           │
│        ▼                                           │
│  Todos los componentes                             │
│  bg-brand-primary, text-brand-surface, etc.        │
└────────────────────────────────────────────────────┘
```

---

## 📦 Code Splitting Strategy

Cada página es un **chunk independiente** cargado bajo demanda:

```typescript
// App.tsx
const Dashboard = lazy(() => import("@/pages/Dashboard").then(m => ({ default: m.Dashboard })));
const SetupWizard = lazy(() => import("@/pages/SetupWizard").then(m => ({ default: m.SetupWizard })));
// ... etc

// Cada ruta envuelta en <Suspense fallback={<PageLoader />}>
```

**Beneficio**: La carga inicial es ~77 KB (gzip). Recharts (~110 KB gzip) solo se descarga al visitar el Dashboard.

**Trade-off**: Navegación entre páginas muestra un spinner de 100-300ms la primera vez que se visita cada chunk.

---

## 🧪 Estrategia de Testing

### Estructura

```
src/
├── tests/
│   └── setup.ts              ← jest-dom + polyfills
├── services/
│   └── __mocks__/
│       └── index.ts          ← Mock manual de todos los endpoints
└── __tests__/
    ├── KPICard.test.tsx      ← 10 tests (componente + formateadores)
    ├── AppShell.test.tsx     ← 5 tests (layout)
    ├── Dashboard.test.tsx    ← 3 tests (render + empty states)
    ├── SetupWizard.test.tsx ← 4 tests (formulario)
    ├── Simulator.test.tsx    ← 4 tests (sliders)
    ├── Reports.test.tsx      ← 5 tests (tabs)
    ├── Kardex.test.tsx       ← 6 tests (CRUD modales)
    └── Settings.test.tsx     ← 6 tests (paleta)
```

### Principios

1. **Mock de API global** — `services/__mocks__/index.ts` devuelve datos vacíos/null por defecto
2. **Renderizado mínimo** — Cada página prueba que renderiza títulos, secciones, y estados vacíos
3. **Interacción básica** — Click en tabs, apertura de modales, valores por defecto
4. **Sin integración real** — No se prueba contra el backend real (eso va en e2e)

---

## 🚦 Manejo de Estados

Cada página maneja 4 estados visuales:

| Estado | UI |
|--------|----|
| **Loading** | `<Skeleton />` animado con pulsos |
| **Empty** | Mensaje amigable ("Ejecutá una simulación...") |
| **Error** | Banner rojo con mensaje del backend |
| **Data** | Componentes normales con datos reales |

Implementado vía hooks genéricos:
```typescript
const { data, loading, error, refetch } = useIncomeStatement();
```

---

## 🔗 Relación con el Backend

### Tipos sincronizados

Los tipos en `src/types/` son un espejo exacto de los Pydantic schemas en `apps/backend/app/schemas/__init__.py`:

| Frontend Type | Backend Schema |
|---------------|---------------|
| `InvestmentInput` | `InvestmentInput` |
| `BCSSResponse` | `BCSSResponse` |
| `IncomeStatementResponse` | `IncomeStatementResponse` |
| `BalanceSheetResponse` | `BalanceSheetResponse` |
| `RatioItem` | `RatioItemResponse` |
| `ColorPalette` | `ColorPalette` |
| `CompanySettings` | `CompanySettings` |
| `KardexProduct` | `KardexProductResponse` |
| `KardexRecord` | `KardexRecordResponse` |

### Proxy en desarrollo

```typescript
// vite.config.ts
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
}
```

---

## 📐 Convenciones de Código

### Nombrado

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Componentes | PascalCase | `KPICard`, `AppShell` |
| Hooks | camelCase, prefijo `use` | `usePalette`, `useBCSS` |
| Funciones API | camelCase, verbo HTTP implícito | `getBCSS()`, `setupAccounting()` |
| Tipos/Interfaces | PascalCase | `InvestmentInput`, `ColorPalette` |
| Archivos de página | PascalCase | `Dashboard.tsx` |
| Archivos de utilidad | camelCase | `api.ts` |

### Estructura de archivos

```typescript
// 1. Imports de React
import { useState } from "react";

// 2. Imports de librerías
import { BarChart } from "recharts";

// 3. Imports locales (@/)
import { useBCSS } from "@/hooks/useAccounting";
import { KPICard } from "@/components/dashboard/KPICard";

// 4. Tipos
import type { InvestmentInput } from "@/types";

// 5. Componente
export function MyComponent() { ... }

// 6. Sub-componentes (si son exclusivos de este archivo)
function HelperRow() { ... }
```

---

> **Última actualización**: 2026-05-10
