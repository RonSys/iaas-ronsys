# Estrategia de Precios — IaaS-RonSys
> **Proyecto:** IaaS-RonSys (Intelligence as a Service)
> **Producto:** ERP SaaS con Agentes de IA para Franquicia "El Segoviano"
> **Versión del documento:** v0.1 (iterativo)
> **Fecha:** 19 de mayo de 2026
> **Última actualización:** 19 de mayo de 2026

---

## 📑 Índice de Contenido

| Sección | Archivo relacionado | Contenido |
|---------|-------------------|-----------|
| **1. Benchmark de Mercado** | `investigacion/comparativa-rapifac-bufeotec-defontana.md` | Comparativa de 3 proveedores peruanos |
| **1a. Bufeo Tec — Premio Avonni** | `investigacion/premio-avonni-2023-bufeotec.md` | Investigación del Premio Avonni 2023 |
| **1b. Bufeo Tec — Precios** | `investigacion/bufeotec-analisis-precios-combinaciones.md` | Análisis de combinaciones y rangos de precios |
| **2. Estrategia de Precios** | *(este documento)* | Propuesta de pricing tiers, justificación |
| **3. Decisiones Registradas** | *(sección al final)* | Historial de iteraciones y decisiones |

---

## 1. Benchmark de Mercado

### 1.1 Proveedores Analizados

De la investigación en `investigacion/comparativa-rapifac-bufeotec-defontana.md`:

| Proveedor | Origen | Enfoque | Rango precio/mes |
|-----------|--------|---------|:----------------:|
| 🟢 **Rapifac** | Peruano | Solo ferreterías (POS) | S/ 50 – 100 |
| 🟡 **Bufeo Tec** | Peruano | Multisectorial (ERP + App + Web) | S/ 100 – 300 |
| 🔴 **Defontana** | Chileno | ERP Corporativo (multi-sucursal) | S/ 200 – 600+ |

### 1.2 Combinaciones de Bufeo Tec (competidor más cercano)

De `investigacion/bufeotec-analisis-precios-combinaciones.md`:

| # | Combinación | Mes (S/) | Año (S/) |
|:-:|-------------|:--------:|:--------:|
| 1 | Solo ERP | 100 – 150 | 1,500 |
| 2 | ERP + App | 150 – 230 | 2,280 |
| 3 | ERP + Web | 130 – 200 | 1,980 |
| 4 | ⭐ **ERP + App + Web** | **180 – 280** | **2,760** |
| 5 | Pack + Estadística | 210 – 330 | 3,240 |
| 6 | A medida + Setup | 180 – 280 + setup | 3,310 |

> **Conclusión del benchmark:** El pack completo de Bufeo Tec para restaurant está en **S/ 180 – 280/mes** (~S/ 2,160 – 3,360/año).

---

## 2. Estrategia de Precios para IaaS-RonSys

### 2.1 Principios Rectores

```
1. PRECIO ≠ COSTO — El precio refleja el VALOR entregado, no las horas de desarrollo
2. IA es el diferenciador — Los agentes de IA justifican un premium sobre ERPs tradicionales
3. Escalabilidad — Precios que crecen con el cliente (no al revés)
4. Franquicia first — El pricing debe soportar el modelo de franquicia
5. Iterativo — Los precios se ajustan con feedback real (este documento se actualiza)
```

### 2.2 Propuesta de Tiers (v0.1)

#### 🔵 Plan Básico — "El Segoviano Local" (para el piloto 4 Motupe)

| Componente | Incluye |
|------------|---------|
| POS / Ventas | ✅ |
| Inventario básico | ✅ |
| Reportes diarios | ✅ |
| Agentes IA | ❌ (básico) |
| Simulador financiero | ❌ |

| Precio | Valor |
|--------|:-----:|
| **Mensual** | **S/ 0** (costo interno — licencia variable, ver contrato) |
| **Regalía Ron** | S/ 0 – 2,000/mes (según flujo del local) |

> 💡 El piloto no paga. Ron define su regalía mensual vía contrato de licencia.

#### 🟢 Plan Starter — "Cevichería Tech"

| Componente | Incluye |
|------------|---------|
| POS / Ventas | ✅ |
| Inventario completo | ✅ |
| Facturación electrónica | ✅ |
| Compras / Proveedores | ✅ |
| Dashboard / Reportes | ✅ |
| Agente IA básico | ✅ (1 skill) |
| App móvil (pedidos) | ✅ |
| Soporte WhatsApp | ✅ |

| Precio | Valor |
|--------|:-----:|
| **Mensual** | **S/ 149 – 199** |
| **Anual (2 meses gratis)** | **S/ 1,490 – 1,990** |
| **Setup / Implementación** | S/ 0 (autogestionado) |

> 🎯 Competidores: Bufeo Tec solo ERP (S/ 100-150) — aquí ganas con IA incluida.

#### 🟡 Plan Pro — "Franquicia Ready"

| Componente | Incluye |
|------------|---------|
| Todo del Starter | ✅ |
| Agentes IA completos | ✅ (todos los skills) |
| Simulador financiero | ✅ |
| Múltiples sucursales (hasta 3) | ✅ |
| CRM básico | ✅ |
| Dashboard ejecutivo | ✅ |
| Capacitación | ✅ (1 sesión) |
| Soporte prioritario | ✅ |

| Precio | Valor |
|--------|:-----:|
| **Mensual** | **S/ 299 – 399** |
| **Anual (2 meses gratis)** | **S/ 2,990 – 3,990** |
| **Setup / Implementación** | S/ 299 (único) |

> 🎯 Competidores: Bufeo Tec pack completo (S/ 180-280) — aquí pagas más pero tienes IA + simulador + multi-sucursal.

#### 🔴 Plan Enterprise — "Multi-Franquicia"

| Componente | Incluye |
|------------|---------|
| Todo del Pro | ✅ |
| Sucursales ilimitadas | ✅ |
| CRM completo | ✅ |
| RRHH / Planillas | ✅ |
| API pública | ✅ |
| White label (marca propia) | ✅ |
| Agentes IA personalizados | ✅ |
| Soporte 24/7 | ✅ |
| SLA garantizado | ✅ |
| Onboarding dedicado | ✅ |

| Precio | Valor |
|--------|:-----:|
| **Mensual** | **S/ 699 – 999** |
| **Anual** | **S/ 6,990 – 9,990** |
| **Setup** | S/ 999 (único) |

> 🎯 Competidores: Defontana (S/ 200-600) — compites en features, pero con IA + especialización cevichería justificas el premium.

---

## 3. Tabla Comparativa vs Competidores

### Por Plan

| Aspecto | Bufeo Tec (Pack) | IaaS-RonSys Starter | IaaS-RonSys Pro | Defontana |
|---------|:----------------:|:-------------------:|:---------------:|:---------:|
| **Precio/mes** | S/ 180 – 280 | **S/ 149 – 199** | **S/ 299 – 399** | S/ 200 – 600+ |
| POS | ✅ | ✅ | ✅ | ✅ |
| Inventario | ✅ | ✅ | ✅ | ✅ |
| Fact. Electrónica | ✅ | ✅ | ✅ | ✅ |
| Contabilidad | ✅ | ✅ | ✅ | ✅ |
| **IA / Agentes** | ❌ | ✅ (1 skill) | ✅ (todos) | ❌ |
| **Simulador Financiero** | ❌ | ❌ | ✅ | ❌ |
| **App Móvil** | ✅ (aparte) | ✅ | ✅ | ✅ |
| Múltiples sucursales | ❌ | ❌ | ✅ (hasta 3) | ✅ |
| CRM | ❌ | ❌ | ✅ (básico) | ❌ |
| Planilla/RRHH | ❌ | ❌ | ❌ | ✅ |
| **Especialización cevichería** | ❌ | ✅🔥 | ✅🔥 | ❌ |
| Soporte WhatsApp | ✅ | ✅ | ✅ (prioritario) | ⚠️ |

### Por Precio — Posicionamiento Visual

```
S/ 0     100    200    300    400    500    600    700    800    900   1000
├───────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┤
        │      │      │      │      │      │      │      │      │
        Rapifac      │      │      │      │      │      │      │
        S/50-100     │      │      │      │      │      │      │
                     │      │      │      │      │      │
              🟢 Starter    🟡 Pro         │      │      │
              S/149-199   S/299-399        │      │      │
                                            🔴 Enterprise
                     Bufeo Tec              S/699-999
                     S/180-280
                                            Defontana
                                            S/200-600+
```

---

## 4. Justificación de Precios

### 4.1 ¿Por qué Starter es más barato que Bufeo Tec?

| Razón | Explicación |
|-------|-------------|
| **Sin app móvil propia** | Starter no incluye app nativa (solo web responsiva) |
| **Sin desarrollo a medida** | Es producto estándar, no hay personalización |
| **Estrategia de entrada** | Precio agresivo para capturar mercado rápido |
| **Diferenciador IA** | Aunque es más barato, ya tienes IA que ellos no tienen |

### 4.2 ¿Por qué Pro es más caro que Bufeo Tec?

| Razón | Explicación |
|-------|-------------|
| **Agentes IA completos** | Skills de ventas, inventario, finanzas — nadie más lo ofrece |
| **Simulador financiero** | Proyecciones, VAN/TIR, BCSS, flujo de caja |
| **Multi-sucursal** | Hasta 3 locales desde una plataforma |
| **CRM básico** | Gestión de clientes y campañas |
| **Especialización** | No es un ERP genérico, sabe de cevicherías |

### 4.3 Elasticidad del Precio

| Variable | Impacto en precio |
|----------|:-----------------:|
| +1 skill de IA | + S/ 30 – 50/mes |
| +1 sucursal | + S/ 50 – 80/mes |
| App móvil nativa | + S/ 50 – 100/mes |
| Capacitación presencial | + S/ 150 – 300 (único) |
| Soporte 24/7 | + S/ 100 – 200/mes |
| White label | + S/ 200 – 400/mes |

---

## 5. Modelo de Ingresos Proyectado

### 5.1 Por Cliente (anual)

| Plan | Mensual | Anual | Clientes target |
|------|:-------:|:-----:|:---------------:|
| Starter | S/ 174 | S/ 1,740 | Cevicherías independientes |
| Pro | S/ 349 | S/ 3,490 | Franquiciados "El Segoviano" |
| Enterprise | S/ 849 | S/ 8,490 | Cadenas de restaurantes |

### 5.2 Escenarios (cuando haya clientes reales)

| Escenario | 10 clientes | 50 clientes | 100 clientes |
|-----------|:-----------:|:-----------:|:------------:|
| Solo Starter | S/ 17,400/año | S/ 87,000/año | S/ 174,000/año |
| Mix 60% Starter + 40% Pro | S/ 25,800/año | S/ 129,000/año | S/ 258,000/año |
| Mix 50% Starter + 30% Pro + 20% Enterprise | S/ 36,300/año | S/ 181,500/año | S/ 363,000/año |

> 💡 Con solo **10 clientes Pro** facturas más que Bufeo Tec con 30 clientes de su pack completo.

---

## 6. Estrategia de Lanzamiento

### Fase 1: Piloto (ahora)
- **Cliente:** El Segoviano — 4 Motupe
- **Precio:** S/ 0 (licencia variable según contrato)
- **Objetivo:** Validar producto, ajustar features, documentar casos de uso

### Fase 2: Beta Cerrada (Q4 2026)
- **Clientes:** 3 – 5 cevicherías conocidas
- **Precio:** S/ 99/mes (50% descuento por ser beta testers)
- **Objetivo:** Feedback real, pulir UX, estabilizar infraestructura

### Fase 3: Lanzamiento Público (Q1 2027)
- **Planes:** Starter / Pro / Enterprise
- **Precios:** Los definidos en sección 2.2
- **Objetivo:** Capturar mercado, empezar a escalar

### Fase 4: Franquicia (Q2 2027+)
- **Modelo:** License fee inicial (S/ 1,000 – 3,000) + regalía mensual (8-12% de ventas)
- **Incluye:** Marca + ERP + procesos + soporte
- **Objetivo:** El verdadero producto — la franquicia tecnológica

---

## 7. Análisis de Valor vs Precio

### ¿Cuánto ahorra tu cliente?

| Concepto | Sin ERP | Con IaaS-RonSys | Ahorro/mes |
|----------|:-------:|:----------------:|:----------:|
| Tiempo en inventario manual | 20h/mes | 2h/mes (IA) | 18h |
| Errores contables | S/ 200/mes | S/ 20/mes | S/ 180 |
| Pérdida por stock mal gestionado | S/ 300/mes | S/ 50/mes | S/ 250 |
| Tiempo en reportes | 8h/mes | 0.5h/mes (IA) | 7.5h |
| **Ahorro total estimado** | | | **S/ 430/mes + 25h** |

> Con un plan Pro de S/ 349/mes, el cliente recupera la inversión **en menos de un mes** solo en eficiencias.

---

## 8. Decisiones Registradas

| # | Fecha | Decisión | Quién | Estado |
|:-:|:-----:|----------|:-----:|:------:|
| 1 | 2026-05-18 | Benchmark vs Rapifac/Bufeo Tec/Defontana completado | Asistente | ✅ Hecho |
| 2 | 2026-05-19 | Avonni 2023 de Bufeo Tec investigado y documentado | Asistente | ✅ Hecho |
| 3 | 2026-05-19 | Combinaciones de precios de Bufeo Tec analizadas | Asistente | ✅ Hecho |
| 4 | 2026-05-19 | Propuesta de 4 tiers (Basic/Starter/Pro/Enterprise) | Asistente | 🟡 Borrador |
| 5 | — | Precios finales de Bufeo Tec vía WhatsApp | ⏳ Pendiente | ⏳ |
| 6 | — | Validar tiers con Nilton | ⏳ Pendiente | ⏳ |
| 7 | — | Definir % de regalía de franquicia | ⏳ Pendiente | ⏳ |
| 8 | — | Analizar Defontana en detalle (competidor Enterprise) | ⏳ Pendiente | ⏳ |

---

## 9. Metadatos y Archivos Relacionados

| Archivo | Ubicación | Rol |
|---------|-----------|-----|
| `comparativa-rapifac-bufeotec-defontana.md` | `investigacion/` | Benchmark principal |
| `premio-avonni-2023-bufeotec.md` | `investigacion/` | Detalle Avonni 2023 |
| `bufeotec-analisis-precios-combinaciones.md` | `investigacion/` | Análisis de combinaciones y precios |
| `03-erp-ia.md` | `proyecto-franquicia/docs/` | Módulos del ERP |
| `plan-exposicion-publica-v0.5.md` | `IaaS-RonSys/docs/` | Plan de salida a producción |
| **`costos-aws-breakeven.md`** | **`IaaS-RonSys/docs/`** | Costos AWS, break-even, decisiones de infraestructura |
| **`estrategia-precios.md`** | **`IaaS-RonSys/docs/`** | **(este documento)** |

---

## 10. Próximas Iteraciones

| Iteración | Qué incluirá |
|-----------|--------------|
| **v0.2** | Precios reales de Bufeo Tec (cuando respondan WhatsApp) |
| **v0.3** | Costos de infraestructura y margen por plan |
| **v0.4** | Modelo de franquicia (fee inicial + regalía %) |
| **v0.5** | Resultados de encuesta a cevicherías (disposición a pagar) |
| **v0.6** | Ajustes post-piloto 4 Motupe |

---

*Documento generado por Asistente para Ron — v0.1 — 19 de mayo de 2026*
*Este documento es iterativo. Cada decisión de precio se registra y justifica.*
