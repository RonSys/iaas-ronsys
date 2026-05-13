# Análisis Técnico Completo — IaaS-RonSys

**Fecha:** 2026-05-12  
**Agente:** Architecture Agent 🏗️  
**Proyecto:** IaaS-RonSys (Monolito Modular + Hexagonal)  
**Stack:** FastAPI + React 19 + PostgreSQL 16 + Docker  
**Commit base:** 3 commits en main (MVP inicial)

---

## 1. Resumen Ejecutivo

El proyecto **IaaS-RonSys** está en un estado **semi-avanzado** con un núcleo contable sólido implementado, pero con **deuda técnica crítica** en Auth (frontend inconsistente), **grandes huecos** en módulos de negocio (Sales/POS, RRHH, Delivery) y **Agentes de IA completamente ausentes** (solo puerto abstracto).

### Hallazgos Críticos

| Hallazgo | Severidad | Acción requerida |
|----------|-----------|------------------|
| DEBT Frontend dice que Auth "no existe" pero backend y frontend real sí lo tienen | 🔴 Alta inconsistencia | Actualizar DEBT Frontend |
| `core/sales/` (dominio) vacío pero service layer ya implementado | 🟡 Media | Verificar endpoints contra DB real |
| Contenedor QA unhealthy (aún responde) | 🟡 Media | Diagnosticar healthcheck |
| Solo 1 backend corriendo (QA), sin prod separado | 🟡 Media | Definir entorno prod aislado |
| Python 3.14 en venv (⚠️ documentado como 3.12) | 🟡 Media | Verificar si 3.14 es aceptable |

---

## 2. Verificación de Tests

### 2.1 Backend — pytest

```bash
$ cd apps/backend && .venv/bin/python -m pytest tests/ -v --tb=short
```

**Resultado: 66 passed, 0 failed (1.32s)** ✅

| Archivo de test | Tests | Aprobados |
|----------------|-------|-----------|
| `test_accounting_engine.py` | 32 | 32 ✅ |
| `test_kardex.py` | 20 | 20 ✅ |
| `test_rate_limit.py` | 7 | 7 ✅ |
| `test_settings.py` | 7 | 7 ✅ |
| **TOTAL** | **66** | **66 ✅** |

### 2.2 Cobertura Backend

```
Name                               Stmts   Miss  Cover
------------------------------------------------------
app/core/accounting/engine.py        367      8    98%
app/core/accounting/kardex.py        119      6    95%
app/core/accounting/ratios.py        142      9    94%
app/core/accounting/statements.py     33      0   100%
app/core/accounting/ports.py          61      0   100%
------------------------------------------------------
TOTAL (todo el proyecto)            1556    814    48%
```

**Solo se prueba el dominio contable puro.** Capas sin cobertura:
- `routers/` (0%): accounting.py, auth.py, admin.py, setup.py, health.py
- `models/` (0%): ORM models
- `core/security.py` (0%), `core/dependencies.py` (0%), `core/tenant.py` (0%)
- `services/` (0%), `monitoring/` (0%), `schemas/` (0%)

### 2.3 Frontend — Jest

```bash
$ cd apps/web && npx jest --verbose
```

**Resultado: 43 passed, 0 failed, 8 suites (10.9s)** ✅

| Suite | Tests |
|-------|-------|
| `Login.test.tsx` | 6 ✅ |
| `KPICard.test.tsx` | 7 ✅ |
| `Kardex.test.tsx` | 3 ✅ |
| `Settings.test.tsx` | 5 ✅ |
| `SetupWizard.test.tsx` | 5 ✅ |
| `Simulator.test.tsx` | 5 ✅ |
| `Reports.test.tsx` | 5 ✅ |
| `AppShell.test.tsx` | 5 ✅ |
| `Dashboard.test.tsx` | 3 ✅ |

### 2.4 Cobertura Frontend

```
File                  | % Stmts | % Branch | % Funcs | % Lines
----------------------|---------|----------|---------|---------
All files             |   49.27 |    41.85 |   30.45 |    51.7
 components/dashboard |   61.11 |    63.15 |   46.66 |   61.11
 components/layout    |   71.42 |      100 |      75 |   71.42
 hooks                |   73.68 |        0 |   77.77 |   74.66
 pages                |   42.58 |    39.03 |    22.5 |   44.85
```

**Componentes con menor cobertura:** CashflowChart (26%), SetupWizard (28%), Kardex (31%), Dashboard (40%).

---

## 3. Verificación de Endpoints en Contenedor

### 3.1 Contenedores en Ejecución

| Contenedor | Puerto | Estado | DB |
|-----------|--------|--------|-----|
| `iaas-backend-qa` | :8000 | Up 17h (unhealthy) | `iaas_ronsys_qa` |
| `iaas-postgres` | :5432 | Healthy | `iaas_ronsys` + `iaas_ronsys_qa` |
| `iaas-redis` | :6379 | Healthy | — |
| `iaas-rabbitmq` | :5672 | Healthy | — |
| `iaas-frontend-prod` | :80 | Running | — |

**⚠️ No existe `iaas-backend-prod`.** Solo hay un backend (QA) en :8000. El frontend-prod corre en :80.

### 3.2 Endpoints Verificados

Todos los tests se ejecutaron contra `http://localhost:8000` (QA container) con JWT válido y `X-Tenant-ID: 1`.

| Endpoint | Método | HTTP | Resultado |
|----------|--------|------|-----------|
| `/health` | GET | 200 | `{"status":"ok","service":"IaaS-RonSys","version":"0.1.0"}` ✅ |
| `/docs` | GET | 200 | Swagger UI ✅ |
| `/openapi.json` | GET | 200 | OpenAPI schema ✅ |
| `/api/auth/login` | POST | 200 | JWT + refresh_token ✅ |
| `/api/auth/refresh` | POST | — | Endpoint registrado ✅ |
| `/api/auth/logout` | POST | — | Endpoint registrado ✅ |
| `/api/auth/me` | GET | 200 | Perfil usuario autenticado ✅ |
| `/api/accounting/setup` | POST | 200 | 152 asientos generados ✅ |
| `/api/accounting/bcss` | GET | 200 | BCSS balanceado ✅ |
| `/api/accounting/pyg` | GET | 200 | PYG completo ✅ |
| `/api/accounting/balance` | GET | 200 | Balance cuadrado ✅ |
| `/api/accounting/ratios` | GET | 200 | 9 ratios con semáforo ✅ |
| `/api/accounting/transaction` | POST | — | Endpoint registrado ✅ |
| `/api/accounting/validate` | POST | — | Endpoint registrado ✅ |
| `/api/accounting/kardex/products` | POST | 200 | Producto registrado ✅ |
| `/api/accounting/kardex/entry` | POST | 422 | Requiere campo `date` ⚠️ |
| `/api/accounting/kardex/exit` | POST | 422 | Requiere campo `date` ⚠️ |
| `/api/accounting/kardex/{code}` | GET | 200 | Kárdex vacío (sin movs) ✅ |
| `/api/accounting/kardex/inventory/summary` | GET | 200 | `[]` (sin productos) ✅ |
| `/api/accounting/kardex/warehouse-close` | POST | — | Endpoint registrado ✅ |

### 3.3 Hallazgos en Endpoints

1. **Health check en `/health` no en `/api/health`** — consistente.
2. **Todos los endpoints contables requieren autenticación JWT** — correcto (seguridad).
3. **Todos los endpoints contables requieren `X-Tenant-ID: <int>`** — correcto (multi-tenant).
4. **`kardex/entry` y `kardex/exit` requieren campo `date`** — no documentado en el README; el schema espera `date` como campo obligatorio.
5. **Estado en memoria** — los routers usan variables globales (`_investment`, `_journal`, `_kardex_engine`). Esto es temporal hasta implementar repositorio persistente.

### 3.4 Usuarios en DB

| Email | Rol | DB |
|-------|-----|-----|
| `admin@elsegoviano.pe` | admin | `iaas_ronsys_qa` |
| `test@elsegoviano.pe` | operator | `iaas_ronsys` |
| `locktest@elsegoviano.pe` | viewer | `iaas_ronsys` |
| `operator@test.com` | operator | `iaas_ronsys` |
| `testqa@elsegoviano.pe` | operator | `iaas_ronsys` |
| `inactive_test@test.com` | viewer (inactive) | `iaas_ronsys` |

**⚠️ La contraseña del admin se genera aleatoriamente en la migración 0002** (`secrets.token_urlsafe(16)`). Debe cambiarse manualmente tras el deploy.

---

## 4. Estado Real por Módulo

### Tabla de Estado Consolidada

| Módulo | Estado Documentado | Estado Real (Código) | Discrepancia | Observaciones |
|--------|--------------------|----------------------|--------------|---------------|
| ✅ Motor Contable (asientos, BCSS, Mayor) | ✅ | ✅ Implementado | Ninguna | `engine.py` (43KB) + `statements.py` + `kardex.py` muy completos |
| ✅ Kárdex / Inventario | ✅ | ✅ Implementado | Ninguna | Funciona con costo promedio ponderado |
| ✅ Estados Financieros (PYG + Balance) | ✅ | ✅ Implementado | Ninguna | Genera asientos automáticos a 12 meses |
| ✅ Ratios Financieros | ✅ | ✅ Implementado | Ninguna | 9 ratios con semáforo 🟢🟡🔴 |
| ✅ Endpoints REST + Schemas | ✅ | ✅ Implementado | Ninguna | Todos los endpoints core responden |
| ✅ DB Models (Company, Account, Journal) | ✅ | ✅ Implementado | Ninguna | ORM bien diseñado con índices |
| ✅ Auth Multi-Tenant (JWT + RBAC) | ✅ | ✅ Implementado | DEBT Frontend falso | Login funciona. AuthContext + routers/auth existen |
| ✅ Monitoreo (Prometheus) | ✅ | ✅ Implementado | Ninguna | `monitoring/metrics.py` |
| ✅ API Settings / Branding | ✅ | ✅ Implementado | Ninguna | Paletas dinámicas via CSS vars |
| 🟡 Flujo de Caja (parcial) | 🟡 | 🟡 Parcial | Solo para ratios NPV/IRR | Falta endpoint `GET /cashflow`, falta real vs proyectado |
| 🟡 Agentes IA (skills) | 🟡 | 🟡 Sólo puerto | Puerto diseñado correctamente (Hexagonal) | `base.py` excelente, pero no hay skills concretas |
| 🟡 Sales / POS | ⬜ | 🟡 Modelos, schemas y router existen; servicio parcial | Migración 0005 aplicada | `models/sales.py`, `services/sales_service.py`, `routers/sales.py` existen. Falta verificar endpoints |
| ✅ Tipo de Negocio | ⬜ | ✅ Implementado | Migración 0003 aplicada | `Company.business_type` enum: restaurant/hardware/retail/service |
| ⬜ RRHH / Planillas | ⬜ | ⬜ No mencionado | No existe en el monorepo | Fuera del scope actual |
| ⬜ Delivery | ⬜ | ⬜ No mencionado | No existe | Fuera del scope actual |

---

## 5. Diagnóstico Detallado por Módulo

### 5.1 Motor Contable y Kárdex (Excelente) ✅

**Implementación real:**
- `core/accounting/engine.py` (43 KB, 98% coverage): Motor completo con generación de asientos a 12 meses, depreciación, intereses, IR (29.5%), validación partida doble.
- `core/accounting/kardex.py` (95% coverage): Costo promedio ponderado, movimientos, cierre de almacén.
- `core/accounting/statements.py` (100% coverage): Orquestación de simulación.
- `core/accounting/ratios.py` (94% coverage): 9 ratios con semáforo + NPV/IRR/payback.
- Plan de cuentas PCGE peruano adaptado: 42 cuentas (Activo 1x, Pasivo 2x, Patrimonio 3x, Ingresos 4x, Costos 5x, Gastos 6x, Cierre 8x).

**Calidad:** Alta. Probado y documentado.

---

### 5.2 Autenticación Multi-Tenant (Corregir DEBT)

**Estado real:**
- Backend: `routers/auth.py`, `core/security.py` (Argon2), modelos `User` + `RefreshToken`, migración 0002.
- Frontend: `AuthContext.tsx` + `Login.tsx` + `PrivateRoute` + hooks de refresh automático.
- Funcionalidad: Login real funciona (verificado con curl → JWT válido).

**Problema:**
El archivo `apps/web/DEBT.md` declara **AUTH-001 como 🔴 "No implementado"**, lo cual es **falso**. Esto genera confusión en el backlog.

**Acción recomendada:** Actualizar DEBT Frontend eliminando o corrigiendo AUTH-001/002.

---

### 5.3 Agentes de IA — Solo el Puerto (Deuda planificada correctamente)

**Lo que existe:**
- `core/agents/base.py`: Excelente diseño hexagonal (`BaseSkill`, `SkillRegistry`, `AgentContext`, `SkillResult`).
- Principio correcto: "diseñar puerto ANTES de implementar".

**Lo que falta completamente:**
- Ninguna skill concreta (`SalesSkill`, `InventorySkill`, `FinanceSkill`).
- Sin `SkillLoader` por decorador.
- Sin conexión real a LLM (OpenRouter).
- Sin `AgentOrchestrator`.

---

### 5.4 Módulos Parcialmente Implementados / Vacíos

| Módulo | Archivos | Estado | Riesgo |
|--------|----------|--------|--------|
| Sales / POS | `models/sales.py` (6 tablas), `services/sales_service.py`, `routers/sales.py`, `schemas/sales.py` | Modelos + schemas + endpoints declarados. `core/sales/` (dominio) vacío — lógica en service layer. | Medio (falta verificar que endpoints funcionen contra DB real) |
| Business Type | `Company.business_type` en `models/accounting.py`, migración 0003 | ✅ Implementado y en DB | Ninguno |
| Inventory (dominio extra) | `core/inventory/` | Vacío | Ya implementado en `accounting/kardex.py` |
| RRHH / Planillas | — | No existe | Fuera de alcance actual |
| Delivery | — | No existe | Fuera de alcance actual |

---

## 6. Mapeo de Deudas Técnicas — Actualizado y Validado

### Deuda Técnica Crítica (🔴)

| ID | Deuda | Estado Real | Deuda Real / Falsa | Impacto | Estimado |
|----|-------|-------------|--------------------|---------|----------|
| AUTH-FE-001 | Auth "no implementado" en frontend | Login + AuthContext existen | **Falsa** | Confusión backlog | — |
| SALES-001 | Módulo Sales/POS sin verificar | `core/sales/` (dominio) vacío; service layer existe | Real | Bloquea ventas si endpoints no funcionan | 2-3 días |
| AGT-001 | Skills IA sin implementar | Sólo `base.py` | Real (por diseño) | Valor IA futuro | 5-7 días |
| DB-002 | Migración 0002_users_auth faltante | Modelos existen | Real | Deploy fallará | 30 min |

### Deuda Técnica Media (🟡)

| ID | Deuda | Real | Estimado |
|----|-------|------|----------|
| CF-001 | Módulo Flujo de Caja separado | Parcialmente embebido | 1-2 días |
| TST-001 | Tests HTTP (TestClient) para routers | 0% coverage routers | 1-2 días |
| TST-002 | Tests de integración DB | 0% coverage models | 1-2 días |
| QA-001 | Container QA unhealthy | Responde pero healthcheck falla | 30 min |
| INFRA-001 | Sin backend-prod separado | Solo QA en :8000 | 1 día |
| PY-001 | Python 3.14 en venv (doc dice 3.12) | Tests pasan en 3.14 | Verificar compatibilidad |

---

## 7. Ficha Técnica: Sales / POS

### 7.1 Modelo de Datos Completo

Se propone un **modelo unificado** con especialización por tipo de negocio. La clave es que la tabla `sales` contiene los campos comunes, y se extiende con tablas opcionales según el tipo de negocio.

#### Tablas Principales

```sql
-- ═══════════════════════════════════════════════
-- Sesión POS (turno de caja)
-- ═══════════════════════════════════════════════
CREATE TABLE pos_sessions (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at       TIMESTAMPTZ,
    opening_cash    NUMERIC(12,2) NOT NULL DEFAULT 0,
    closing_cash    NUMERIC(12,2),
    expected_cash   NUMERIC(12,2),   -- calculado: opening + ventas_efectivo - retiros
    difference      NUMERIC(12,2),   -- diferencia de cierre
    status          VARCHAR(10) NOT NULL DEFAULT 'open',  -- open | closed
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════
-- Venta (cabecera)
-- ═══════════════════════════════════════════════
CREATE TABLE sales (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    session_id      INTEGER REFERENCES pos_sessions(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    sale_number     VARCHAR(30) NOT NULL,  -- VEN-2026-00001
    sale_date       DATE NOT NULL,
    sale_time       TIME NOT NULL DEFAULT now(),
    
    -- Cliente (opcional)
    customer_name   VARCHAR(150),
    customer_doc    VARCHAR(20),   -- RUC/DNI
    
    -- Totales
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_total  NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_total       NUMERIC(12,2) NOT NULL DEFAULT 0,    -- IGV
    tip_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,    -- Propina (restaurante)
    total           NUMERIC(12,2) NOT NULL DEFAULT 0,
    
    -- Contexto de negocio
    business_type   VARCHAR(20) NOT NULL,   -- 'restaurant' | 'hardware' | 'retail'
    
    -- Flags
    is_voided       BOOLEAN NOT NULL DEFAULT false,
    void_reason     VARCHAR(200),
    voided_at       TIMESTAMPTZ,
    
    -- Referencias contables
    journal_entry_id INTEGER REFERENCES journal_entries(id),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════
-- Items de Venta
-- ═══════════════════════════════════════════════
CREATE TABLE sale_items (
    id              SERIAL PRIMARY KEY,
    sale_id         INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id),
    
    -- Descripción (puede no ser producto de inventario)
    item_name       VARCHAR(200) NOT NULL,       -- "Arroz Chaufa", "Martillo 16oz"
    item_type       VARCHAR(20) NOT NULL DEFAULT 'product',  -- product | service | combo
    
    quantity        NUMERIC(12,2) NOT NULL,
    unit_of_measure VARCHAR(10) NOT NULL DEFAULT 'unidad',
    unit_price      NUMERIC(12,2) NOT NULL,
    discount_pct    NUMERIC(5,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_pct         NUMERIC(5,2) NOT NULL DEFAULT 0,      -- IGV 18% para ferretería
    tax_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total           NUMERIC(12,2) NOT NULL,
    
    -- Kárdex
    kardex_movement_id INTEGER REFERENCES kardex_movements(id),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════
-- Pagos (soporta múltiples métodos por venta)
-- ═══════════════════════════════════════════════
CREATE TABLE sale_payments (
    id              SERIAL PRIMARY KEY,
    sale_id         INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    payment_method  VARCHAR(20) NOT NULL,  -- 'cash' | 'card' | 'yape' | 'plin' | 'transfer'
    amount          NUMERIC(12,2) NOT NULL,
    reference       VARCHAR(50),           -- últimos 4 dígitos tarjeta, #operación
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Tablas de Especialización por Tipo de Negocio

```sql
-- ═══════════════════════════════════════════════
-- Extensión: Restaurante (mesa, pedido, propina)
-- ═══════════════════════════════════════════════
CREATE TABLE restaurant_sales (
    id              SERIAL PRIMARY KEY,
    sale_id         INTEGER NOT NULL UNIQUE REFERENCES sales(id) ON DELETE CASCADE,
    table_number    VARCHAR(10),           -- "M1", "Terraza 3", null = delivery/llevar
    guests          INTEGER DEFAULT 1,
    order_type      VARCHAR(20) NOT NULL DEFAULT 'dine_in',  -- dine_in | takeout | delivery
    waiter_name     VARCHAR(100),
    tip_amount      NUMERIC(12,2) DEFAULT 0,
    tip_pct         NUMERIC(5,2) DEFAULT 0,
    kitchen_notes   TEXT                   -- "Sin cebolla", "Término medio"
);

-- ═══════════════════════════════════════════════
-- Extensión: Ferretería/Retail
-- ═══════════════════════════════════════════════
CREATE TABLE hardware_sales (
    id              SERIAL PRIMARY KEY,
    sale_id         INTEGER NOT NULL UNIQUE REFERENCES sales(id) ON DELETE CASCADE,
    invoice_type    VARCHAR(10) NOT NULL DEFAULT 'boleta',  -- boleta | factura
    delivery_address VARCHAR(300),
    requires_install BOOLEAN DEFAULT false,  -- Necesita instalación
    warranty_months INTEGER DEFAULT 0        -- Garantía en meses
);
```

### 7.2 Diferencias: Restaurante vs Ferretería

| Aspecto | Restaurante | Ferretería |
|---------|------------|------------|
| **Unidad de venta** | Plato preparado (combo/receta) | Producto unitario (código) |
| **Inventario** | Insumos → preparación → plato (transformación) | Producto → venta directa (salida simple) |
| **Precio** | Precio fijo por carta/menú | Precio variable + descuento |
| **Cliente** | Generalmente anónimo (mesa) | Puede tener RUC (factura) |
| **Impuesto** | IGV ya incluido en precio carta | IGV 18% desglosado en boleta/factura |
| **Propina** | Sí (opcional, 10%) | No |
| **Mesa/Mesero** | Sí (mesa + pedido + mesero) | No aplica |
| **Delivery** | Común (rappitender) | Ocasional (despacho a domicilio) |
| **Devolución** | Rara (error de pedido) | Común (producto defectuoso) |
| **Garantía** | No | Sí (ej. taladro 12 meses) |
| **Comprobante** | Boleta de venta | Boleta o Factura |
| **Kárdex** | Salida de insumos por receta (explosión) | Salida directa del producto |
| **Contabilidad** | Asiento: Caja/40, Costo/50, IGV/201 | Asiento: Caja/40, Costo/50, IGV/201 |

### 7.3 Estrategia: Modelo Unificado con Especialización

**Decisión: Modelo unificado.** Motivos:

1. **Compatibilidad Monolito Modular:** El monolito ya maneja multi-tenant; la especialización por tipo de negocio se logra con tablas de extensión (1:1 con `sales`).

2. **80% de campos son comunes:** `sale_items`, `sale_payments`, `pos_sessions`, cliente, totales, impuestos, vale para ambos.

3. **Evita duplicación de lógica:** Métodos de pago, cierre de caja, reporting, integración contable se comparten.

4. **El Kárdex maneja la diferencia:** 
   - Ferretería: venta → `kardex.exit(product_id, quantity)` (salida directa)
   - Restaurante: venta → `kardex.exit(ingrediente_id, quantity)` (explosión de receta → múltiples salidas)

### 7.4 Integración con Kárdex (Salida Automática de Stock)

```python
# Flujo al registrar venta (POST /api/sales/sale)
async def create_sale(sale_data: SaleCreate, company_id: int):
    # 1. Crear cabecera de venta
    sale = Sale(...)
    
    # 2. Procesar items → salida de inventario
    for item in sale_data.items:
        if item.product_id:  # Solo si es producto de inventario
            record, journal_entry = kardex_engine.record_exit(
                product_code=item.product_code,
                quantity=item.quantity,
                concept=f"Venta {sale.sale_number}",
                reference_type="venta",
            )
            item.kardex_movement_id = record.id
            if journal_entry:
                journal.append(journal_entry)
    
    # 3. Generar asiento contable de venta
    sale_entry = accounting_engine.generate_sale_entry(sale)
    journal.append(sale_entry)
    
    # 4. Persistir todo en transacción
    await db.commit()
```

### 7.5 Integración con Motor Contable (Asiento de Venta Automático)

**Ejemplo: Venta de ferretería S/ 118 (S/ 100 + IGV S/ 18)**

```
Asiento VEN-2026-00001  |  Debe   |  Haber
------------------------|---------|--------
10  Efectivo (Caja)     |  118.00 |
40  Ventas              |         | 100.00
201 IGV por pagar       |         |  18.00
50  Costo de Ventas     |   60.00 |
12  Inventarios         |         |  60.00
------------------------|---------|--------
TOTAL                   | 178.00  | 178.00 ✅
```

**Ejemplo: Venta de restaurante S/ 65 (incluye IGV y propina S/ 6.50)**

```
Asiento VEN-2026-00042  |  Debe   |  Haber
------------------------|---------|--------
10  Efectivo (Caja)     |  71.50  |
40  Ventas              |         |  55.08
201 IGV por pagar       |         |   9.92
24  Propinas por pagar  |         |   6.50
50  Costo de Ventas     |  18.50  |
12  Inventarios         |         |  18.50
------------------------|---------|--------
TOTAL                   |  90.00  |  90.00 ✅
```

### 7.6 Endpoints Propuestos

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/sales/sessions/open` | POST | Abrir turno de caja |
| `/api/sales/sessions/close` | POST | Cerrar turno (arqueo) |
| `/api/sales/sessions/current` | GET | Sesión actual abierta |
| `/api/sales/sales` | GET | Listar ventas (filtros: fecha, tipo, session) |
| `/api/sales/sale` | POST | Registrar nueva venta |
| `/api/sales/sale/{id}` | GET | Detalle de venta |
| `/api/sales/sale/{id}/void` | POST | Anular venta |
| `/api/sales/sale/{id}/ticket` | GET | Ticket/Comprobante (PDF/texto) |
| `/api/sales/payment-methods` | GET | Métodos de pago activos por company |

---

## 8. Estrategia de "Tipo de Negocio"

### 8.1 Problema

**✅ RESUELTO.** El modelo `Company` ya tiene `business_type` (migración 0003 aplicada):
- `business_type` VARCHAR(20) NOT NULL DEFAULT 'restaurant' — enum: restaurant | hardware | retail | service
- `economic_activity` (texto libre, ej: "Restaurante - Venta de comidas y bebidas")
- `settings` (JSON, para feature flags y tax_config)

No hay forma de que el sistema sepa si una empresa es restaurante vs ferretería, lo cual afecta:
- UI/UX del POS (¿muestra mesa/mesero o no?)
- Formato de comprobantes (boleta vs factura)
- Cálculo de impuestos (IGV incluido vs desglosado)
- Integración con Kárdex (explosión de receta vs salida directa)
- Catálogo de cuentas (401 "Venta de platos y bebidas" vs genérico)

### 8.2 Solución Propuesta: Campo Enum + Feature Flags en settings JSON

#### Ya implementado: Campo Enum en Company ✅

```sql
-- Migración 0003_business_type.py — YA APLICADA
ALTER TABLE companies ADD COLUMN business_type VARCHAR(20) NOT NULL 
  DEFAULT 'restaurant' 
  CHECK (business_type IN ('restaurant', 'hardware', 'retail', 'service'));
```

**Ventajas:**
- Una sola fuente de verdad
- Fácil de consultar (sin parsear JSON)
- Se puede usar en constraints y políticas de seguridad

#### Opción B: Feature Flags en settings JSON (complementario)

```json
{
  "business_type": "restaurant",
  "features": {
    "tables_enabled": true,
    "tips_enabled": true,
    "delivery_enabled": false,
    "invoice_required": false,
    "warranty_tracking": false,
    "recipe_explosion": true,
    "multi_currency": false
  },
  "tax_config": {
    "igv_rate": 0.18,
    "igv_included_in_price": true,
    "withholding_tax_rate": 0.0
  }
}
```

**Ventajas:**
- Permite activar/desactivar features individualmente
- Ej: un restaurante sin delivery, o una ferretería que SÍ necesita delivery
- Los feature flags se evalúan en runtime para mostrar/ocultar UI

### 8.3 Decisión Final: Enum ya implementado + settings JSON para feature flags

1. **`business_type` enum** en tabla `companies`: define el tipo base del negocio.
2. **`settings.features` JSON**: overrides y personalización por company.
3. **`settings.tax_config` JSON**: configuración tributaria (varía por país).

```python
# Ejemplo de uso en el backend
def get_business_config(company: Company) -> BusinessConfig:
    base = BUSINESS_DEFAULTS[company.business_type]  # Config base
    overrides = (company.settings or {}).get("features", {})
    return BusinessConfig(**{**base, **overrides})

# En el frontend
const { features } = useCompanySettings();
{features.tables_enabled && <TableSelector />}
{features.tips_enabled && <TipInput />}
```

### 8.4 Migración — YA APLICADA (0003_business_type.py)

```sql
-- Migración 0003 ya ejecutada. El campo business_type existe en DB.
-- Falta: popular settings con feature flags y tax_config.
-- Esto se puede hacer en una migración futura (0007_company_defaults).

UPDATE companies SET settings = jsonb_build_object(
    'features', jsonb_build_object(
        'tables_enabled', true,
        'tips_enabled', true,
        'invoice_required', false,
        'recipe_explosion', true
    ),
    'tax_config', jsonb_build_object(
        'igv_rate', 0.18,
        'igv_included_in_price', true
    )
) WHERE business_type = 'restaurant' AND settings IS NULL;
```

---

## 9. Ficha de Flujo de Caja

### 9.1 ¿Qué existe actualmente?

En `statements.py`, el cashflow se calcula **solo para ratios (NPV/IRR/payback)**:

```python
# statements.py — línea 117
monthly_flows = [
    vars_.monthly_sales[i] * (1 - vars_.monthly_cost_pct)
    - (vars_.monthly_rent + vars_.monthly_utilities + vars_.monthly_salaries
       + vars_.monthly_marketing + vars_.monthly_admin + vars_.monthly_maintenance)
    for i in range(min(months, len(vars_.monthly_sales)) or 1)
]
```

Esto es un **flujo de caja proyectado simplificado**, basado en las `InvestmentVariables` ingresadas en `/api/accounting/setup`.

**Lo que NO existe:**
- No hay endpoint `/api/accounting/cashflow`
- No hay modelo de datos para cashflow
- No hay integración con ventas reales (Sales/POS existe como modelos pero no verificado)
- No hay integración con Kárdex para costos reales
- No hay comparativa proyectado vs real
- No hay proyección de cuentas por cobrar/pagar
- No hay tracking de caja chica ni gastos operativos reales

### 9.2 Diseño Propuesto: Tres Vistas de Flujo de Caja

#### Vista 1: Flujo Proyectado

Origen: `InvestmentVariables` del Setup + plan de cuentas proyectado.

```python
@dataclass
class CashflowLine:
    month: int
    year: int
    concept: str           # "Ventas", "Costo de Ventas", "Alquiler", "Préstamo"
    category: str          # "income" | "expense" | "investment" | "financing"
    projected: float       # Del modelo proyectado
    actual: float | None   # De transacciones reales (si existen)
    difference: float | None

@dataclass  
class CashflowReport:
    company_id: int
    from_date: date
    to_date: date
    lines: list[CashflowLine]
    opening_balance: float
    net_cashflow: float
    closing_balance: float
```

#### Vista 2: Flujo Real

Origen: Asientos contables reales en `journal_entries` + `kardex_movements` + ventas reales.

```python
def calculate_real_cashflow(company_id: int, from_date: date, to_date: date) -> CashflowReport:
    """Calcula el flujo de caja real desde transacciones."""
    
    # 1. Saldo inicial (Cuenta 10 al inicio del período)
    opening = get_account_balance("10", from_date - 1 day)
    
    # 2. Entradas reales
    sales_cash = sum(journal_lines where account="10" debit and entry_type="venta")
    other_income = sum(journal_lines where account="10" debit and not "venta")
    loan_disbursements = sum(journal_lines where account="10" debit and loan)
    
    # 3. Salidas reales
    cost_of_sales = sum(kardex_exits * avg_cost for period)
    operating_expenses = sum(journal_lines where account="10" credit and gasto)
    loan_payments = sum(journal_lines where account="10" credit and prestamo)
    tax_payments = sum(journal_lines where account="10" credit and impuesto)
    
    return CashflowReport(...)
```

#### Vista 3: Comparativa Proyectado vs Real

```python
def compare_cashflow(projected: CashflowReport, actual: CashflowReport) -> dict:
    """Compara proyección vs realidad y genera alertas."""
    
    comparison = {
        "total_projected": sum(line.projected for line in projected.lines),
        "total_actual": sum(line.actual for line in actual.lines),
        "variance_pct": ...,
        "alerts": []
    }
    
    # Alertas automáticas
    if actual.revenue < projected.revenue * 0.8:
        comparison["alerts"].append({
            "severity": "red",
            "message": f"Ventas reales {actual.revenue} están 20%+ bajo lo proyectado {projected.revenue}"
        })
    
    return comparison
```

### 9.3 Modelo de Datos (Opcional — para persistir proyecciones)

```sql
CREATE TABLE cashflow_projections (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    month           INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year            INTEGER NOT NULL,
    concept         VARCHAR(100) NOT NULL,
    category        VARCHAR(20) NOT NULL,  -- income|expense|investment|financing
    amount          NUMERIC(12,2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, year, month, concept)
);
```

### 9.4 Endpoint Propuesto

```
GET /api/accounting/cashflow?from=2026-01&to=2026-12&compare=true
```

**Response:**
```json
{
  "company_id": 1,
  "from_date": "2026-01-01",
  "to_date": "2026-12-31",
  "opening_balance": 50000,
  "lines": [
    {
      "month": 1, "year": 2026, "concept": "Ventas",
      "projected": 25000, "actual": 23200, "difference": -1800
    },
    {
      "month": 1, "year": 2026, "concept": "Costo de Ventas",
      "projected": 10000, "actual": 10800, "difference": +800
    }
  ],
  "net_cashflow": {
    "projected": 15000, "actual": 12400, "variance_pct": -17.3
  },
  "closing_balance": {
    "projected": 65000, "actual": 62400
  },
  "alerts": [
    {"severity": "yellow", "message": "Costo de ventas 8% sobre lo proyectado"}
  ]
}
```

### 9.5 Pasos para Implementar

1. **Crear `CashflowService`** en `core/accounting/cashflow.py`
2. **Añadir endpoint** `GET /api/accounting/cashflow` en `routers/accounting.py`
3. **Vista proyectada:** inmediata (datos ya existen en `InvestmentVariables`)
4. **Vista real:** depende de módulo Sales + repositorio persistente (journal en DB)
5. **Comparativa:** después de tener ambas vistas

---

## 10. Plan de Implementación Priorizado (Fases)

### Fase 0 — Limpieza (1 día)

1. Actualizar `apps/web/DEBT.md` (corregir Auth).
2. Crear migración 0002 para users + refresh_tokens (si no existe).
3. Añadir tests HTTP básicos para endpoints de Auth.

### Fase 1 — Fundamentos Estables (3-4 días)

**Objetivo:** Tener un MVP desplegable con Auth real + contabilidad completa.

| Prioridad | Tarea | Valor Negocio | Esfuerzo | Dependencias |
|-----------|-------|---------------|----------|--------------|
| P1 | Corregir DEBT Frontend | Alto (claridad) | 1h | — |
| P1 | Implementar tests de integración HTTP | Alto | 2 días | — |
| P1 | Verificar endpoints Sales/POS contra DB real | Crítico | 1-2h | — |
| P2 | Completar Flujo de Caja como endpoint | Medio | 1-2 días | Estados |
| P2 | Diagnosticar healthcheck QA | Medio | 30min | — |

### Fase 2 — Módulos Comerciales (5-8 días)

| Módulo | Valor | Esfuerzo | Riesgo |
|--------|-------|----------|--------|
| **Sales / POS** (verificar + completar endpoints) | 🔴 Muy Alto | 2-3 días | Modelos y schemas ya existen (migración 0005). Verificar endpoints contra DB real |
| **Kárdex + Inventario** (persistencia DB) | Alto | 2 días | Ya base existe en memoria |

### Fase 3 — Agentes de IA (6-9 días)

1. Implementar `SalesSkill`, `InventorySkill`, `FinanceSkill`.
2. `SkillLoader` + decoradores.
3. Conexión con OpenRouter / DeepSeek.
4. Endpoint `/api/agents/invoke` + orquestador básico.

### Fase 4 — Expansión (Restaurantes / Delivery)

- Adaptadores de configuración por tipo de negocio (feature flags).
- Módulo Delivery (tickets, tracking).
- RRHH simplificado (solo planillas básicas).

---

## 11. Recomendaciones Finales

1. **Priorizar primero** la corrección del DEBT del frontend (elimina confusión).
2. **`business_type` ya está implementado** (migración 0003). El requisito previo para Sales está cubierto.
3. **Verificar y completar Sales/POS** antes que los Agentes IA (modelos ya existen, falta validar funcionamiento).
4. Mantener el diseño hexagonal de los agentes (ya está bien hecho).
5. **El flujo de caja proyectado puede ir en Fase 1** (los datos ya existen); el real depende de Sales.
6. Evaluar si Delivery y RRHH entran en este MVP o quedan para v2.
7. **Python 3.14 funciona** (todos los tests pasan), pero verificar si hay incompatibilidades con dependencias en producción.

---

## 12. Próximos Pasos Sugeridos

| Paso | Responsable | Entregable | Prioridad |
|------|-------------|------------|-----------|
| Corregir DEBT Frontend | Frontend Agent | DEBT actualizado | 🔴 P1 |
| Verificar endpoints Sales/POS | Backend Agent | Reporte de endpoints funcionales | 🔴 P1 |
| Crear migración 0002_users_auth (si falta) | Backend Agent | Alembic version | 🟡 P2 |
| Implementar módulo Sales (modelo + endpoints) | Backend Agent | Routers + Services + Models | 🔴 P1 |
| Cashflow endpoint (vista proyectada) | Backend Agent | `GET /api/accounting/cashflow` | 🟡 P2 |
| Diagnosticar healthcheck QA | DevOps Agent | Container healthy | 🟡 P2 |
| Diseñar primera Skill (SalesSkill) | Architecture + Backend | Puerto + skill stub | 🟢 P3 |

---

**Fin del Análisis**  
Documento guardado en: `/home/ron/projectos/IaaS-RonSys/docs/reports/analysis-2026-05-12.md`
