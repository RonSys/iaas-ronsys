# 🧭 Arquitectura de Observabilidad IA — LangChain + LangGraph + LangSmith (F5 y plataforma)

> **Autor:** Jarvis (orquestador) · **Fecha:** 2026-08-14 · **Estado:** 🟡 PROPUESTA (para validación de Ron)
> **Base:** investigación de Ron (`~/investigacion/07-varios/20260808_LangChain-vs-LangGraph-vs-LangSmith-Cual-Usar-en-2.md`)
> **Alcance:** preparar la arquitectura de F5 (y futuros agentes IA: F3 voz, RAG Bloque B) para los 3 frameworks, con **observabilidad total** y **mapeo de costos por agente**.

---

## 0. Contexto real verificado (2026-08-14, contra código y prod)

| Hecho | Estado verificado |
|---|---|
| **F5 NO es RAG** | F5 = NL2SQL controlado (tool calling: el LLM elige `query_catalog_id` + params tipados, NUNCA escribe SQL). El **RAG es el Bloque B** ("Knowledge Agent") de la §9 del informe — aún NO implementado |
| **F5 ya audita** | `query_logs` guarda por consulta: `pregunta`, `query_catalog_id`, `params`, `tokens_used`, `latency_ms`, `rejected` (R4). Tabla real en prod |
| **F3 ya gobierna costos** | `voice_ai_service`: `cost_usd` por llamada + `get_daily_cost_usd` + presupuesto diario por tenant + **kill-switch** (R4/R5) |
| **Prometheus activo** | Backend expone `/metrics` en PROD (verificado: responde métricas `iaas_http_*`, `iaas_simulations_*`, etc.) |
| **Grafana/Prometheus apagados** | Contenedores `infra-grafana`, `infra-prometheus` existen pero **Exited 25h**; config `infra/docker/monitoring/prometheus.yml` sin servicio en docker-compose |
| **LangSmith NO instalado** | `grep langsmith` en requirements/app = vacío |
| **Puerto de skills** | `app/core/agents/base.py` (BaseSkill, deuda #8) — F5 implementa `DeliverySkill`; el puerto ya permite más skills sin rediseño |

---

## 1. ¿Cómo encajan los 3 frameworks? (capas, no competencia)

```
┌─────────────────────────────────────────────────────────────────────┐
│  LANGSMITH — TABLERO DE CONTROL (observabilidad + costos)           │
│  Trazas en árbol por run: qué nodo corrió, prompt exacto,           │
│  tokens, costo por ejecución, dónde se torció.                      │
│  Se activa con 2 env vars — SIN instrumentar el código.             │
├─────────────────────────────────────────────────────────────────────┤
│  LANGGRAPH — SISTEMA NERVIOSO (orquestación multi-paso, con estado) │
│  Checkpoints (durabilidad), human-in-the-loop (interrupt),          │
│  replay/fork de ejecuciones. CUANDO F5 crezca a multi-agente.       │
├─────────────────────────────────────────────────────────────────────┤
│  LANGCHAIN — BLOQUES DE CONSTRUCCIÓN (LLM client, prompts, RAG)     │
│  La tubería RAG (Bloque B futuro) vive aquí. F5 hoy NO lo necesita. │
├─────────────────────────────────────────────────────────────────────┤
│  NUESTRA CAPA (ya existe):                                          │
│  BaseSkill (puerto hexagonal) → assistant_service (pipeline 8 pasos)│
│  → LLMClient (OpenAI/DeepSeek compatible) → query_logs (auditoría)  │
│  → rate limit + tenant scope + roles (R8/R9)                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Lectura correcta (2026):** no se elige "uno de los 3" — se apilan por capa:
- **LangChain** = piezas (modelos, prompt templates, tubería RAG). Para F5 actual: ya tenemos nuestro `LLMClient` que cumple el rol; LangChain entra cuando implementemos **RAG (Bloque B)** o queramos estandarizar integraciones.
- **LangGraph** = lo agéntico/multi-paso. F5 hoy es un pipeline lineal de 8 pasos (no necesita grafo). LangGraph entra cuando: (a) F5 crezca a multi-agente (chat + voz + RAG coordinados), (b) haya loops de retry/self-eval, (c) necesitemos checkpoints para procesos largos.
- **LangSmith** = observabilidad. **Se enciende DESDE EL PRIMER DÍA en producción** — es 2 variables de entorno y responde la pregunta de Ron: *"¿por qué este agente costó $400 el martes?"*.

---

## 2. ¿Grafana o LangSmith? → AMBOS, con responsabilidades distintas

| Dimensión | **LangSmith** | **Grafana + Prometheus** |
|---|---|---|
| **Qué observa** | Ejecuciones LLM: trazas en árbol por run, prompt exacto, qué tool llamó, tokens por paso, **costo por run/agente** | Infraestructura + negocio: HTTP por endpoint, latencia, errores, simulaciones, asientos, estado de servicios |
| **Cómo se activa** | 2 env vars (`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`) — **cero instrumentación** | Ya existe: `/metrics` activo en prod; falta levantar los contenedores |
| **Responde** | *¿Qué hizo la IA y cuánto costó cada ejecución?* | *¿Está sano el sistema y cuánto le pesa cada endpoint?* |
| **Costo** | SaaS (ver §4) | Gratis (open source) |

**Conclusión:** **no se reemplazan, se complementan.**
- **LangSmith** → observabilidad **LLM** (trazas, costos por agente/run, prompts) — el valor agregado que pide Ron.
- **Grafana/Prometheus** → observabilidad **de infraestructura y negocio** — ya está el 80% hecho (métricas + config), solo falta: añadir el servicio al docker-compose, exponer puertos, y crear dashboards. Además: Grafana puede **consumir las trazas de LangSmith** como data source para un dashboard unificado.

**Recomendación de Ron "¿se debe usar Grafana?":** Sí — pero con rol **complementario** (infra/negocio), no como sustituto de LangSmith (LLM). Los dos juntos = observabilidad total.

---

## 3. Costo por agente — el modelo de datos que ya tenemos + LangSmith

**Hoy (sin LangSmith):**
- F5: `query_logs.tokens_used` + `latency_ms` por consulta → podemos calcular $/consulta con la tarifa del modelo.
- F3: `cost_usd` por llamada + presupuesto diario + kill-switch → **gobernanza de costo ya operativa**.

**Con LangSmith:**
- **Da costo por run/agente directamente** (si el proveedor reporta usage — DeepSeek/OpenAI lo reportan vía API OpenAI-compatible).
- Traza el **árbol completo**: si una ejecución del agente hace 5 llamadas al LLM, LangSmith muestra el costo TOTAL de la rama y de cada nodo — algo que `query_logs` (1 fila por consulta) NO captura.

**Combinación recomendada (lo mejor de ambos):**
```
query_logs (BD, R4) ── auditoría de NEGOCIO: qué preguntó el dueño, qué consulta usó,
                      params, rechazos, tenant. Filtrable por tenant/rol/fecha.
        +
LangSmith ── telemetría de EJECUCIÓN: traza completa, prompt exacto, costo por run,
             uso de tokens por paso, latencia por nodo.
        +
F3 budget (BD) ── tope diario por tenant + kill-switch (gobernanza).
        +
Grafana ── dashboard unificado: $/día por agente (suma query_logs/F3) + salud del
           sistema + alertas (Prometheus Alertmanager).
```
**Mapeo por agente:** `tenant_id + skill/agente + fecha` es la clave de agrupación en los 4 sistemas → mismo dashboard de "costo por agente por tenant por día".

---

## 4. Riesgos y consideraciones (verificado 2026-08)

| Tema | Detalle |
|---|---|
| **LangSmith es SaaS** | Plan free: ~5k trazas/mes (suficiente para empezar). Planes pagos por trazas. **Self-hosted**: existe (imagen docker), pero SmithDB (capa de datos Rust, 2026-05) corre la nube US — self-host limitado vs SaaS. Recomendación: **SaaS free primero**, evaluar self-host cuando el volumen crezca |
| **Versiones 2026** | LangChain 1.0 (2025-10), LangGraph 1.0, **Agent Builder → LangSmith Fleet** (2026-03), **SmithDB** (2026-05). Tutoriales viejos = obsoletos. Nuestra arquitectura (puerto hexagonal BaseSkill) nos protege: el framework es un adapter, no el core |
| **Compatibilidad DeepSeek** | LangSmith traza **cualquier proveedor OpenAI-compatible** (DeepSeek lo es — F5 ya lo usa vía LLMClient). Se puede instrumentar con `langsmith` SDK directo (sin LangChain) o con `langchain-openai` — ambos funcionan |
| **LangGraph ≠ necesario hoy** | F5 es pipeline lineal → LangGraph ahora sería "ceremonia". Riesgo de sobre-ingeniería. Se introduce con un caso real: multi-agente o retry/self-eval |
| **Grafana apagado** | No es deuda de IA: es tarea de infra (devops) — levantar servicios + dashboard. Bajo esfuerzo, ya está configurado |
| **F5 sin LLM key en prod** | Hoy prod corre con fallback determinista (sin API key configurada). LangSmith traza solo cuando hay llamadas LLM reales → al conectar la key DeepSeek se activa la telemetría completa |

---

## 5. Roadmap de adopción (fases, costo incremental)

| Fase | Qué | Esfuerzo | Cuándo |
|---|---|---|---|
| **F5.1 — LangSmith YA** | Instalar `langsmith` + 2 env vars en F5 (y F3 voice_ai). Trazas + costo por run desde el día 1. Verificar con 1 consulta real | ~0.5–1 día | **Ahora** (valor inmediato, responde la duda de costos de Ron) |
| **F5.2 — Grafana on** | Añadir `prometheus` + `grafana` al docker-compose (config ya existe), dashboard "Costo IA por agente/tenant/día" (fuente: query_logs + F3) + alertas | ~1–2 días | Próximo sprint devops |
| **F5.3 — Costo unificado** | Vista en el backend: `GET /api/v1/assistant/costs?from=&to=&agent=` (agrega query_logs + F3 cost_usd + tarifas) → API lista para Grafana o para el panel | ~1 día | Con F5.2 |
| **RAG (Bloque B)** | Implementar con **LangChain** (tubería RAG: embeddings + pgvector ya disponible) — primera pieza real de LangChain | 2–4 sem (proyecto aparte) | Cuando Ron apruebe Bloque B |
| **F5 Multi-agente** | Si F5 crece a chat + voz + RAG coordinados o necesita retry/self-eval → migrar el pipeline de 8 pasos a **LangGraph** (checkpoints, interrupt) | Solo cuando haya caso real | Futuro |
| **LangSmith Fleet** | Evaluar despliegue/operación de agentes cuando haya varios en producción | — | Futuro |

**Orden de valor:** LangSmith YA (costos) → Grafana (infra) → API de costos → LangChain (RAG, cuando se apruebe) → LangGraph (solo si multi-agente).

---

## 6. Decisión pedida a Ron

1. ✅ **¿Autorizas LangSmith (plan free, ~5k trazas/mes) para F5 y F3?** — costo $0 para empezar, 2 env vars, sin tocar código de negocio.
2. ✅ **¿Autorizas levantar Grafana/Prometheus en el compose** (config ya lista) con dashboard de costos por agente?
3. 📌 F4 queda **pendiente para el domingo 16/08** (confirmado por Ron, 2026-08-14).

---

## 7. Referencias

- Investigación de Ron: `~/investigacion/07-varios/20260808_LangChain-vs-LangGraph-vs-LangSmith-Cual-Usar-en-2.md`
- Spec 08 (F5): `docs/specs/06-asistente-ia/08-spec-preguntale-al-sistema-v0.1.md`
- Puerto BaseSkill: `apps/backend/app/core/agents/base.py`
- Métricas: `apps/backend/app/monitoring/metrics.py` · `infra/docker/monitoring/prometheus.yml`
- Informe ejecutivo §9 (Bloques A/B/C): `docs/reports/informe-ejecutivo-cliente-2026-08.md`
