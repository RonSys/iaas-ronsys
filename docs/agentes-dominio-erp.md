# Agentes de Dominio — IaaS-RonSys
> **Propuesta de agentes expertos por módulo del ERP**
> **Versión:** v0.1 (exploratorio — nada decidido aún)
> **Fecha:** 20 de mayo de 2026
> **Basado en:** `arquitectura-agentes.md`, `03-erp-ia.md`, investigación tributaria peruana

---

## 📑 Índice

| Sección | Contenido |
|---------|-----------|
| **1. Concepto** | Por qué agentes de dominio y no un solo chatbot genérico |
| **2. Agentes Propuestos** | Lista completa con descripción |
| **3. Tabla Comparativa** | Módulo vs Agente vs Conocimiento necesario |
| **4. ¿Cómo Funcionarían?** | Arquitectura de cada agente interno |
| **5. Roadmap Sugerido** | Por dónde empezar y qué priorizar |
| **6. Lo que NO está decidido** | Dudas abiertas para discutir después |

---

## 1. Concepto

Actualmente el ERP tiene agentes para **construir el software** (Backend Agent, Frontend Agent, QA, etc.). Pero una vez que el ERP esté funcionando, los **usuarios finales** (dueños de cevicherías) necesitan agentes **dentro del producto** que sepan de sus problemas reales:

```
HOY:  Agentes de desarrollo → Construyen el ERP
MAÑANA: Agentes de dominio  → Viven DENTRO del ERP y ayudan al usuario
```

### La idea clave

En lugar de un chatbot genérico que "sabe de todo un poco", tener **agentes especializados** donde cada uno es experto en un área:

> Así como no le pides al contador que cocine ceviche ni al cocinero que haga la declaración SUNAT, cada agente domina su módulo y sabe cuándo derivar a otro agente.

---

## 2. Agentes Propuestos

### 🧾 A1 — Agente Contable (Perú) ⭐ PRIORIDAD ALTA

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | PCGE (Plan Contable General Empresarial), libros contables, asientos de apertura/cierre, depreciación, provisiones, diferencias de cambio, NIC/NIIF para MYPE |
| **¿Qué hace?** | Sugiere asientos contables basados en ventas/compras, explica en lenguaje simple "¿por qué este asiento?", detecta errores contables antes de que SUNAT los vea, auto-genera el asiento de apertura del balance, responde "¿cómo registro esto?" |
| **¿Por qué duele?** | El 90% de las cevicherías en Perú NO llevan contabilidad bien hecha. Esto les da un "contador virtual" 24/7. |
| **Inputs** | Boletas emitidas, facturas de compra, movimientos de caja, nómina |
| **Outputs** | Asientos sugeridos, alertas de errores, explicaciones en español simple |

**Ejemplo de interacción:**
> Usuario: *"Compré pescado por S/ 200 al contado, ¿cómo lo registro?"*
> Agente: *"Es una compra de insumos. El asiento sería: Débito 601 (Compras) por S/ 200, Crédito 111 (Caja) por S/ 200. ¿Lo registro?"*

---

### 📦 A2 — Agente de Kardex / Inventario ⭐ PRIORIDAD ALTA

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Métodos de valoración (promedio ponderado, PEPS, UEPS), control de mermas, stock de seguridad, punto de reorden, FIFO para perecibles |
| **¿Qué hace?** | Sugiere cuándo reordenar insumos, alerta cuando un producto lleva mucho tiempo en stock (pescado = perecible = urgente), calcula merma esperada vs real, detecta robos/fugas, responde "¿cuánto me queda de limón?" |
| **¿Por qué duele?** | En una cevichería el pescado es el insumo más caro y más perecible. Una mala gestión del inventario mata el margen. |
| **Inputs** | Compras, ventas (recetas), mermas registradas, fechas de vencimiento |
| **Outputs** | Alertas de stock crítico, sugerencias de compra, cálculo de merma |

**Ejemplo de interacción:**
> Usuario: *"¿Cuánto pescado necesito comprar mañana?"*
> Agente: *"Has vendido 40 platos de ceviche hoy. Con tu receta estándar (250g/plato), necesitas 10kg. Te quedan 3kg. Deberías comprar 7kg para mañana."*

---

### 💰 A3 — Agente Financiero

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Estados financieros (balance, PYG, flujo de caja), ratios, VAN/TIR, payback, punto de equilibrio |
| **¿Qué hace?** | Conectado al simulador financiero. Responde "¿cuánto gané este mes?", "¿cuándo recupero la inversión?", "¿conviene migrar de NRUS a RMT?", auto-genera reportes ejecutivos, proyecta escenarios |
| **¿Por qué duele?** | Los dueños de cevicherías no saben leer balances. Este agente se los traduce a lenguaje de la calle. |
| **Inputs** | Ventas, costos, gastos, inversión inicial, préstamos |
| **Outputs** | Reportes mensuales, alertas de rentabilidad, proyecciones |

**Ejemplo de interacción:**
> Usuario: *"¿Estoy ganando o perdiendo?"*
> Agente: *"Este mes vendiste S/ 6,000. Tus costos fueron S/ 4,175. Ganancia neta: S/ 1,825 (30% de margen). Vas bien, pero tu margen bajó 5% vs el mes pasado. ¿Quieres ver por qué?"*

---

### 👥 A4 — Agente de RRHH (Perú)

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Leyes laborales peruanas: CTS, gratificaciones (julio/diciembre), ESSALUD, ONP/AFP, vacaciones, horas extras, contratos, régimen MYPE |
| **¿Qué hace?** | Calcula planillas automáticamente, recuerda fechas de pago de CTS/gratificaciones, sugiere el tipo de contrato según el caso, responde "¿cuánto le debo pagar a mi ayudante?", calcula liquidación |
| **¿Por qué duele?** | Las multas de SUNAFIL por no pagar CTS o gratificaciones a tiempo son altísimas. Un error le puede costar S/ 10,000+ a una cevichería. |
| **Inputs** | Datos del trabajador, horas trabajadas, régimen, fecha de ingreso |
| **Outputs** | Planilla mensual, alertas de vencimientos, cálculo de CTS/gratificaciones |

**Ejemplo de interacción:**
> Usuario: *"Tengo un ayudante que trabaja 6 horas diarias, 6 días a la semana. ¿Cuánto le debo pagar?"*
> Agente: *"Con esa jornada (36h/sem), le corresponde S/ 1,025/mes (RMV 2026 ≈ S/ 1,130 proporcional). Además, en julio le deberás pagar gratificación. ¿Lo registro en planilla?"*

---

### 📊 A5 — Agente de Ventas / POS

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Patrones de venta, estacionalidad, platos más/menos vendidos, ticket promedio, hora pico, día pico |
| **¿Qué hace?** | Sugiere qué platos promocionar, detecta productos que no rotan, alerta cuando un plato baja en ventas, responde "¿cuál fue mi mejor día?", "¿qué plato se vende más los fines de semana?" |
| **¿Por qué duele?** | Sin datos, el dueño decide por corazonada. Con este agente, decide con data. |
| **Inputs** | Tickets de venta, historial de pedidos, estacionalidad |
| **Outputs** | Reportes de ventas, sugerencias de menú, detección de tendencias |

---

### 📋 A6 — Agente Tributario (SUNAT)

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Todos los regímenes (NRUS, RER, RMT, RG), formularios SUNAT, fechas de vencimiento, cronograma de pagos, límites por régimen, comprobantes electrónicos |
| **¿Qué hace?** | Alerta cuando te acercas al límite del NRUS (S/ 96,000/año), sugiere migrar de régimen en el momento óptimo, recuerda pagos de cuotas, detecta inconsistencias en las declaraciones, responde "¿qué formulario lleno?", "¿hasta cuándo puedo pagar?" |
| **¿Por qué duele?** | Las multas de SUNAT por declaraciones fuera de plazo o incorrectas pueden ser de S/ 4,400+. Un agente que te recuerde y guíe evita eso. |
| **Inputs** | Ventas acumuladas, compras acumuladas, régimen actual, fecha de inicio |
| **Outputs** | Alertas de límites, recordatorios de pago, sugerencias de cambio de régimen |

**Ejemplo de interacción:**
> Usuario: *"Ya llevo S/ 8,500 en ventas este mes, ¿pasa algo?"*
> Agente: *"⚠️ Has superado el límite mensual del NRUS (S/ 8,000). Deberías migrar a RMT el próximo mes. ¿Quieres que te prepare los pasos?"*

---

### 🍽️ A7 — Agente de Recetas / Menú

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Costos por plato, rendimiento de insumos, recetas estándar, márgenes por plato, estacionalidad de insumos |
| **¿Qué hace?** | Calcula el costo real de cada plato vs su precio de venta, sugiere ajustes de precio cuando sube el insumo, alerta cuando un plato está dando pérdida, responde "¿cuánto me cuesta hacer un ceviche?", "¿cuál es mi plato más rentable?" |
| **¿Por qué duele?** | Muchas cevicherías venden platos sin saber si ganan o pierden dinero. Una subida del limón o el pescado puede dejar un plato en negativo sin que el dueño se dé cuenta. |
| **Inputs** | Recetas (ingredientes + cantidades), precios de insumos, precios de venta |
| **Outputs** | Margen por plato, sugerencias de precio, alertas de platos no rentables |

---

### 🤖 A0 — Asistente General (Orquestador de Agentes)

| Aspecto | Detalle |
|---------|---------|
| **¿Qué sabe?** | Un poco de todo, pero su fuerte es **derivar** al agente correcto |
| **¿Qué hace?** | Es la cara del sistema. El usuario le habla a él y él decide qué agente interno necesita. "Quiero registrar una compra" → Agente Contable. "Se me está acabando el pescado" → Agente Kardex. "¿Ganamos plata este mes?" → Agente Financiero. |
| **Inputs** | Lenguaje natural del usuario |
| **Outputs** | Respuesta directa o derivación al agente especializado |

---

## 3. Tabla Comparativa: Módulo → Agente → Conocimiento

| Módulo ERP | Agente | Conocimiento Especializado | ¿Existe en otro ERP? |
|------------|--------|---------------------------|:--------------------:|
| Contabilidad | 🧾 **A1 Contable** | PCGE, NIC/NIIF MYPE, SUNAT | ❌ No (solo libros) |
| Inventario | 📦 **A2 Kardex** | PEPS/Promedio, perecibles, mermas | ❌ No (solo stock) |
| Financiero | 💰 **A3 Financiero** | VAN/TIR, BCSS, ratios, proyecciones | ⚠️ Parcial (solo reportes) |
| RRHH | 👥 **A4 RRHH Perú** | CTS, gratif., ESSALUD, ONP/AFP, SUNAFIL | ❌ No (solo planilla) |
| Ventas | 📊 **A5 Ventas** | Patrones de venta, estacionalidad | ⚠️ Parcial (solo dashboard) |
| Tributario | 📋 **A6 SUNAT** | Regímenes, formularios, multas, plazos | ❌ No existe en ningún ERP |
| Recetas | 🍽️ **A7 Recetas** | Costeo por plato, rendimiento, margen | ❌ No (ni idea) |
| General | 🤖 **A0 Asistente** | Orquestación, lenguaje natural | ⚠️ Chatbots genéricos (sin especialización) |

> 🔥 **Diferenciador clave:** Ningún ERP del mercado peruano tiene agentes especializados por dominio. Los chatbots existentes son genéricos. Esto sería **único en el mercado**.

---

## 4. ¿Cómo Funcionarían Técnicamente?

### 4.1 Arquitectura Interna (Dentro del ERP)

```
                      ┌─────────────────────────────┐
                      │     USUARIO (dueño)         │
                      │   "¿Cuánto gané ayer?"      │
                      └──────────┬──────────────────┘
                                 │
                      ┌──────────▼──────────────────┐
                      │  🤖 A0 — ASISTENTE GENERAL  │
                      │  (Clasifica la intención)    │
                      └──────────┬──────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ 🧾 A1 Contable  │   │ 📦 A2 Kardex    │   │ 💰 A3 Financiero│
│                 │   │                 │   │                 │
│ Prompt: "Eres   │   │ Prompt: "Eres   │   │ Prompt: "Eres   │
│ un contador     │   │ un experto en   │   │ un analista     │
│ peruano experto │   │ inventarios de  │   │ financiero con  │
│ en PCGE..."     │   │ cevichería..."  │   │ conocimiento de │
│                 │   │                 │   │ VAN/TIR..."     │
│ Tools:          │   │ Tools:          │   │ Tools:          │
│ • Leer asientos │   │ • Leer stock    │   │ • Leer ventas   │
│ • Sugerir      │   │ • Sugerir compra│   │ • Generar BCSS  │
│   asiento       │   │ • Detectar      │   │ • Calcular      │
│ • Explicar     │   │   merma anómala  │   │   proyección    │
│   en español    │   │                 │   │                 │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### 4.2 Cada Agente Tendría

| Componente | Ejemplo (Agente Contable) |
|------------|--------------------------|
| **System Prompt** | *"Eres un contador peruano experto en PCGE. Conoces las NIC/NIIF para MYPE, los regímenes tributarios NRUS/RMT/RG, y las obligaciones ante SUNAT. Respondes en español simple, sin jerga contable a menos que el usuario la pida."* |
| **Knowledge Base** | PCGE actualizado, normas SUNAT, tabla de depreciación, tasas de impuestos |
| **Herramientas (Tools)** | `leer_asientos()`, `sugerir_asiento()`, `explicar_cuenta()`, `generar_balance()` |
| **Datos a los que accede** | Tabla `asientos_contables`, `plan_contable`, `facturas_compra`, `boletas_emitidas` |
| **Límites** | No modifica nada sin aprobación del usuario. Solo sugiere. |
| **Costo por consulta** | ~$0.01 – 0.05 por llamada a OpenAI/Claude |

### 4.3 Estrategia de Prompts

Cada agente tendría un prompt que define su **personalidad y expertise**:

```
AGENTE CONTABLE:
"Eres un contador público colegiado del Perú con 20 años de experiencia.
Conoces el PCGE al detalle. Has trabajado con cientos de MYPE y restaurantes.
Tu misión es ayudar al dueño a llevar su contabilidad en orden.
Hablas claro, sin tecnicismos innecesarios.
NUNCA registras un asiento sin explicar por qué.
Si algo no está claro, preguntas antes de actuar."

AGENTE KARDEX:
"Eres un jefe de almacén de una cevichería con 15 años de experiencia.
Sabes que el pescado fresco no puede esperar.
Conoces los métodos de valoración de inventarios.
Eres obsesivo con el control de mermas.
Alertas tempranas son tu especialidad."

AGENTE TRIBUTARIO:
"Eres un especialista en tributación peruana.
Conoces todos los regímenes, formularios y plazos.
Has visto a cientos de negocios caer en multas evitables.
Tu objetivo: que el usuario nunca tenga una multa de SUNAT.
Eres preventivo, no reactivo."
```

---

## 5. Roadmap Sugerido

### Fase 1 — Piloto (los 2 más críticos)

```
Orden:  A1 (Contable) + A6 (Tributario)
¿Por qué?
  - Son los que más multas/errores evitan
  - El conocimiento es estable (PCGE no cambia cada mes)
  - Alto impacto inmediato para el dueño
```

### Fase 2 — Operaciones

```
Orden:  A2 (Kardex) + A7 (Recetas)
¿Por qué?
  - Afectan directamente el margen del negocio
  - El kardex + recetas = control de costos real
  - Dependen de datos que ya genera el POS
```

### Fase 3 — Crecimiento

```
Orden:  A3 (Financiero) + A5 (Ventas)
¿Por qué?
  - Necesitan data histórica (mínimo 3 meses de operación)
  - Sirven para tomar decisiones estratégicas
```

### Fase 4 — Staff

```
Orden:  A4 (RRHH)
¿Por qué?
  - Complejidad legal alta (CTS, gratificaciones, etc.)
  - Baja prioridad inicial (el piloto quizá no tenga empleados)
  - Cuando contrates personal, actívalo
```

---

## 6. Dudas Abiertas (Nada Decidido)

| Pregunta | Para decidir después |
|----------|---------------------|
| ¿Cada agente usa su propio modelo de IA o comparten uno? | Costo vs especialización |
| ¿Los agentes actúan automáticamente o solo sugieren? | Seguridad vs comodidad |
| ¿El agente contable puede registrar asientos por sí solo o necesita aprobación? | Riesgo vs eficiencia |
| ¿Costo por consulta de IA se lo cobras al cliente o lo absorbes? | Margen vs precio |
| ¿Los prompts de los agentes los puede editar el cliente avanzado? | Personalización vs soporte |
| ¿Un mismo agente sirve para NRUS y RG o necesitan variantes? | Simplicidad vs precisión |
| ¿El agente RRHH necesita conexión con SUNAT/ESSALUD para calcular en vivo? | Integración vs offline |

---

## 7. Costo Estimado de IA por Cliente

| Agente | Consultas estimadas/día | Costo por consulta | Costo/mes/cliente |
|--------|:----------------------:|:------------------:|:-----------------:|
| A0 Asistente General | 10 | ~$0.02 | ~$6 |
| A1 Contable | 3 | ~$0.04 | ~$3.60 |
| A2 Kardex | 2 | ~$0.03 | ~$1.80 |
| A3 Financiero | 1 | ~$0.05 | ~$1.50 |
| A4 RRHH | 0.5 | ~$0.04 | ~$0.60 |
| A5 Ventas | 2 | ~$0.02 | ~$1.20 |
| A6 Tributario | 1 | ~$0.04 | ~$1.20 |
| A7 Recetas | 2 | ~$0.03 | ~$1.80 |
| **Total** | **~21.5 consultas/día** | | **~$17.70/mes/cliente** |

> 💡 ~$18/mes en IA por cliente. Con un plan Pro de ~$100/mes, el margen sigue siendo saludable.

---

## 8. Resumen

| Agente | Prioridad | Dificultad | Impacto | Diferenciador |
|--------|:---------:|:----------:|:-------:|:-------------:|
| 🧾 A1 Contable | 🥇 Alta | Media | 🔥 Altísimo | ✅ Único en Perú |
| 📋 A6 Tributario | 🥇 Alta | Baja | 🔥 Altísimo | ✅ Único en Perú |
| 📦 A2 Kardex | 🥈 Media | Baja | Alto | ✅ Perecibles = cevichería |
| 🍽️ A7 Recetas | 🥈 Media | Media | Alto | ✅ Especializado |
| 💰 A3 Financiero | 🥉 Baja | Alta | Medio | ⚠️ Existe en ERPs caros |
| 📊 A5 Ventas | 🥉 Baja | Baja | Medio | ⚠️ Existe en dashboards |
| 👥 A4 RRHH | 🥉 Baja | Alta | Medio | ⚠️ Existe en planillas |

---

## 9. Archivos Relacionados

| Archivo | Contenido |
|---------|-----------|
| `IaaS-RonSys/docs/arquitectura-agentes.md` | Arquitectura actual de agentes de desarrollo |
| `IaaS-RonSys/docs/estrategia-precios.md` | Estrategia de precios (para calcular margen con IA) |
| `IaaS-RonSys/docs/costos-aws-breakeven.md` | Costos de infraestructura |
| `proyecto-franquicia/docs/03-erp-ia.md` | Módulos del ERP |
| `investigacion/nrus-documentacion-operaciones-erp.md` | Conocimiento tributario para A6 |
| `investigacion/tipos-empresa-regimenes-tributarios-peru.md` | Base legal para A1 y A6 |

---

*Documento generado por Asistente para Ron — v0.1 — 20 de mayo de 2026*
*Nada está decidido aún. Esto es una exploración de posibilidades para discutir después.*
