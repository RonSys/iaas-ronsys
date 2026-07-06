# 🖥️ IaaS-RonSys — Frontend Web

> **ERP SaaS con Agentes de IA para la franquicia "El Segoviano"**
> React + Vite + TailwindCSS + TypeScript

---

## 📋 Stack

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| React | 19.x | UI library |
| Vite | 6.x | Bundler / dev server |
| TypeScript | 5.7 | Tipado estricto |
| TailwindCSS | 3.4 | Utility-first CSS |
| React Router | 7.x | Routing SPA |
| Recharts | 2.15 | Gráficos (flujo de caja) |
| Zustand | 5.x | State management (instalado, uso futuro) |

### Testing

| Herramienta | Versión | Propósito |
|------------|---------|-----------|
| Jest | 30.x | Test runner |
| React Testing Library | 16.x | Tests de componentes |
| ts-jest | — | TypeScript → Jest |
| jest-environment-jsdom | — | Simula DOM en Node |

---

## 🚀 Quick Start

### Requisitos

- Node.js ≥ 18
- Backend corriendo en `localhost:8000` (ver `../../README.md`)

### Instalación

```bash
cd apps/web
npm install
```

### Desarrollo

```bash
npm run dev        # → http://localhost:5173
```

El proxy de Vite redirige `/api/*` → `http://localhost:8000`. No se necesita CORS adicional en desarrollo.

### Build

```bash
npm run build       # → dist/
npm run preview     # Previsualizar build
npx tsc --noEmit    # TypeScript check
```

### Tests

```bash
npx jest --verbose   # 43 tests, 8 suites
npx jest --coverage  # Con cobertura
```

---

## 🗂️ Estructura del Proyecto

```
apps/web/
├── index.html                     ← Entry HTML
├── package.json
├── tsconfig.json                  ← TypeScript estricto + paths
├── vite.config.ts                 ← Vite + proxy /api → :8000
├── tailwind.config.ts             ← theme.extend.colors.brand.* (CSS vars)
├── postcss.config.js
├── jest.config.cjs                ← Jest + ts-jest
│
└── src/
    ├── main.tsx                   ← createRoot + render <App/>
    ├── App.tsx                    ← Router + lazy loading + Suspense
    ├── index.css                  ← Tailwind + CSS custom properties + componentes base
    │
    ├── types/                     ← Tipos TypeScript (espejo de Pydantic schemas)
    │   ├── index.ts               ← Re-exporta todo
    │   ├── accounting.ts          ← InvestmentInput, BCSS, PYG, Balance, Ratios, Kárdex
    │   └── settings.ts            ← ColorPalette, CompanySettings
    │
    ├── services/                  ← Capa de API
    │   ├── api.ts                 ← fetch wrapper + 15 funciones endpoint
    │   ├── index.ts               ← Re-export
    │   └── __mocks__/             ← Manual mock para tests
    │
    ├── hooks/                     ← React hooks
    │   ├── usePalette.ts          ← GET/PATCH palette → CSS custom properties
    │   └── useAccounting.ts       ← 7 hooks: BCSS, PYG, Balance, Ratios, Kárdex, Simulación
    │
    ├── components/
    │   ├── layout/
    │   │   └── AppShell.tsx       ← Header + nav (desktop/mobile) + footer
    │   └── dashboard/
    │       ├── KPICard.tsx        ← KPICard, TrafficLight, Skeleton, formateadores
    │       └── CashflowChart.tsx  ← Gráficos Recharts (BarChart + LineChart)
    │
    ├── pages/                     ← Páginas (código splitteado con React.lazy)
    │   ├── Dashboard.tsx          ← Panel principal (KPIs, PYG, Balance, Ratios, BCSS, gráficos)
    │   ├── SetupWizard.tsx        ← Formulario de inversión inicial → POST /setup
    │   ├── Simulator.tsx          ← 5 sliders + resultados en vivo + comparativa escenarios
    │   ├── Reports.tsx            ← 4 tabs: PYG, Balance, BCSS, Ratios
    │   ├── Kardex.tsx             ← Inventario + movimientos + modales entrada/salida
    │   └── Settings.tsx           ← Paleta de colores + 4 presets + info empresa
    │
    ├── tests/
    │   └── setup.ts               ← Jest setup (jest-dom + TextEncoder polyfill)
    │
    └── __tests__/                 ← Tests unitarios (43 tests, 8 suites)
        ├── KPICard.test.tsx
        ├── AppShell.test.tsx
        ├── Dashboard.test.tsx
        ├── SetupWizard.test.tsx
        ├── Simulator.test.tsx
        ├── Reports.test.tsx
        ├── Kardex.test.tsx
        └── Settings.test.tsx
```

---

## 🎨 Sistema de Branding

La paleta de colores se carga dinámicamente desde el backend al iniciar la app.

### Flujo

```
GET /api/settings/palette → usePalette() → :root CSS custom properties
                                          → Tailwind theme.extend.colors.brand.*
```

### Colores configurables (10)

| Variable CSS | Propósito |
|-------------|-----------|
| `--color-primary` | Color principal (header, botones, acentos) |
| `--color-secondary` | Color secundario |
| `--color-accent` | Acento (valores destacados) |
| `--color-background` | Fondo de página |
| `--color-surface` | Fondo de tarjetas |
| `--color-text-primary` | Texto principal |
| `--color-text-secondary` | Texto secundario |
| `--color-success` | Éxito / verde |
| `--color-warning` | Advertencia / ámbar |
| `--color-error` | Error / rojo |

### Paletas predefinidas

- **Azul Marino** (default)
- **Verde Bosque**
- **Rojizo Cálido**
- **Púrpura**

Todas accesibles desde Settings.tsx con un clic.

---

## 🔌 Conexión con el Backend

| Endpoint | Método | Función en api.ts |
|----------|--------|-------------------|
| `/api/health` | GET | `getHealth()` |
| `/api/accounting/setup` | POST | `setupAccounting()` |
| `/api/accounting/bcss` | GET | `getBCSS()` |
| `/api/accounting/pyg` | GET | `getIncomeStatement()` |
| `/api/accounting/balance` | GET | `getBalanceSheet()` |
| `/api/accounting/ratios` | GET | `getRatios()` |
| `/api/settings` | GET/PATCH | `getSettings()` / `updateSettings()` |
| `/api/settings/palette` | GET/PATCH | `getPalette()` / `updatePalette()` |
| `/api/accounting/kardex/*` | GET/POST | 6 funciones kárdex |

Todos los hooks (`useAccounting.ts`) exponen `{ data, loading, error, refetch }`.

---

## 🧩 Code Splitting

Cada página se carga en su propio chunk vía `React.lazy` + `Suspense`:

| Chunk | Tamaño (gzip) | Cuándo carga |
|-------|:------------:|-------------|
| Core | 77 KB | Siempre |
| Dashboard | 111 KB | Al visitar `/` |
| Reports | 3 KB | Al visitar `/reportes` |
| Kardex | 3 KB | Al visitar `/kardex` |
| Simulator | 3 KB | Al visitar `/simulador` |
| SetupWizard | 2 KB | Al visitar `/setup` |
| Settings | 2 KB | Al visitar `/settings` |

La carga inicial es **77 KB** (sin Recharts). Recharts (D3) solo se carga al entrar al Dashboard.

---

## 🧠 Decisiones de Diseño

1. **CSS Custom Properties para branding** — Permite cambiar la paleta sin recompilar. Tailwind consume las variables vía `theme.extend.colors.brand.*`.

2. **Componentes base en CSS puro** (`.card`, `.btn`, `.input-field`) — Tailwind `@apply` no soporta opacity modifiers con CSS variables. Los componentes reutilizables usan CSS estándar para mantener el diseño consistente.

3. **Hooks genéricos con loading/error** — Cada hook (`useBCSS`, `useIncomeStatement`, etc.) sigue el mismo patrón `{ data, loading, error, refetch }` para consistencia.

4. **TypeScript estricto** — `strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`. Tipos espejo exactos de los Pydantic schemas del backend.

5. **Tests de renderizado mínimo por componente** — Cada página tiene al menos un test que verifica renderizado, títulos y estados vacíos.

---

## 📚 Documentación Relacionada

| Documento | Ruta |
|-----------|------|
| Arquitectura frontend | `../docs/arquitectura-frontend.md` |
| Backend README | `../../README.md` |
| Simulador docs | `../../../simulador-financiero/docs/` |
| UI/UX design | `../../../simulador-financiero/docs/08-ui-ux.md` |

---

## 🚀 Despliegue (Deploy)

El frontend se despliega en **dos entornos** usando el script `deploy.sh` desde la raíz:

```bash
# Entorno QA — Vite dev server (:5173)
cd ../.. && ./deploy.sh --env qa
# → Hot-reload | Proxy /api → localhost:8001

# Entorno Producción — Nginx (:80)
cd ../.. && ./deploy.sh --env prod
# → Archivos compilados | Proxy /api → localhost:8000
```

### Entornos

| Entorno | Frontend URL | Backend | Build | Comando |
|---------|-------------|---------|-------|---------|
| 🧪 **QA** | `http://localhost:5173` | `:8001` | Vite dev (HMR) | `./deploy.sh --env qa` |
| 🚀 **Prod** | `http://localhost` | `:8000` | Nginx (compilado) | `./deploy.sh --env prod` |

> 💡 Ambos entornos pueden coexistir sin conflictos. Ver [`docs/manuales/guia-despliegue.md`](../../docs/manuales/guia-despliegue.md).

### Desarrollo Local

```bash
# Dev server con hot-reload + proxy al backend QA
npm run dev                # → http://localhost:5173

# El proxy de Vite redirige /api/* → http://localhost:8001 (QA)
# Asegurate de que el backend QA esté corriendo:
#   cd ../.. && ./deploy.sh --env qa
```

### Build de Producción

```bash
# TypeScript check + Vite build
npm run build              # → dist/

# La salida está en dist/:
#   dist/index.html
#   dist/assets/*.js
#   dist/assets/*.css
```

### Docker + Nginx

```bash
# Desplegar con nginx (incluido en deploy.sh --prod)
docker compose -f ../../docker-compose.yml -f ../../docker-compose.prod.yml up -d frontend

# Verificar
curl http://localhost/
```

La imagen usa **multistage build**:
1. **Stage 1** (`node:20-alpine`): instala deps, corre `tsc` + `vite build`
2. **Stage 2** (`nginx:alpine`): copia `dist/` + `nginx.conf`, expone puerto 80

El `nginx.conf` incluido:
- Sirve archivos estáticos con cache de 1 año para assets hasheados
- Hace proxy reverso de `/api/*` → `http://backend:8000`
- Maneja SPA routing (todas las rutas → `index.html`)
- Incluye headers de seguridad (X-Frame-Options, X-Content-Type-Options, etc.)

---

## ⚠️ Troubleshooting

| Problema | Solución |
|----------|----------|
| `npm run dev` no conecta al backend | Verificar que el backend corre en `:8000` (`docker-compose up -d`) |
| Errores CORS | En dev, Vite proxy maneja esto. En prod, configurar backend CORS |
| `tsc --noEmit` falla | Revisar imports no usados, tipos incorrectos |
| Tests fallan con `TextEncoder` | Asegurar que `src/tests/setup.ts` tiene el polyfill |
| Chunk size warning en build | Normal: Recharts es grande. Code-splitting ya está aplicado |

---

> **Última actualización**: 2026-05-10
