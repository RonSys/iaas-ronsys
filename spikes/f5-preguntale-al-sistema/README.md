# 🧪 SPIKE F5 — "Pregúntale al Sistema" (Bloque A §9)

> **Estado**: SPIKE de aprendizaje + validación de arquitectura (2026-08-13).
> **NO es producción** — solo toca la BD QA `iaas_ronsys_qa` (tenant 1), nunca prod.
> **Aprobado por Ron** para avanzar sobre la base del puerto hexagonal `BaseSkill`
> (deuda técnica #8: `apps/backend/app/core/agents/base.py`).

---

## 🎯 Qué valida este spike

1. **Tool calling real con LLM (DeepSeek)** — la IA elige qué función SQL usar
   (catálogo cerrado), NO escribe SQL libre. Arquitectura exacta del F5.
2. **Skills sobre el puerto BaseSkill** — `VentasSkill` con 3 tools SOLO LECTURA.
3. **Eval mínimo (Bloque C en miniatura)** — golden queries con verificación
   contra la BD real → reporte de exactitud.
4. **Fallback determinista** — sin LLM, el flujo end-to-end funciona igual.

---

## 📁 Contenido

| Archivo | Descripción |
|---|---|
| `ventas_skill.py` | `VentasSkill` mínimo: 3 tools SOLO LECTURA (ventas_del_dia, top_productos_dia, ventas_por_zona_dia) + registro |
| `orchestrator.py` | Orquestador: function calling DeepSeek + fallback determinista + resumen NL |
| `eval_golden.py` | Eval: 5 golden queries, tool accuracy + data accuracy vs BD real |
| `seed_qa.sql` | Data de prueba (6 ventas hoy + 1 ayer, 7 pedidos, 3 zonas, 5 productos) |
| `eval_report.json` | Último reporte de eval (fallback y LLM) |

---

## 🚀 Cómo correrlo

### Requisitos
- Docker postgres con `iaas_ronsys_qa` (schema 0018 + seed aplicado)
- Python venv del backend (`apps/backend/.venv` — tiene psycopg3)
- Opcional: `DEEPSEEK_API_KEY` en el entorno (si no, usa fallback)

### 1. Preparar BD QA (una vez)
```bash
# (esquema ya clonado de prod + alembic 0018 — ver "Setup BD QA" abajo)
docker cp spikes/f5-preguntale-al-sistema/seed_qa.sql iaas-postgres:/tmp/seed_qa.sql
docker exec iaas-postgres psql -U ron -d iaas_ronsys_qa \
  -c "TRUNCATE delivery_orders, sale_items, sales, delivery_zones, products, users RESTART IDENTITY CASCADE;" \
  && docker exec iaas-postgres psql -U ron -d iaas_ronsys_qa -f /tmp/seed_qa.sql
```

### 2. Demo interactiva (CLI)
```bash
# Fallback determinista (sin LLM — 35ms)
VENV/bin/python spikes/f5-preguntale-al-sistema/orchestrator.py "¿cuánto vendió hoy?" --fallback

# DeepSeek (function calling real — ~2s)
DEEPSEEK_API_KEY=sk-... VENV/bin/python spikes/f5-preguntale-al-sistema/orchestrator.py "¿qué producto se vendió más hoy?"

# ⚠️ Demo read-only contra PROD (data real — todo es SELECT puro):
F5_DATABASE_URL="postgresql://ron:ron123@localhost:5432/iaas_ronsys" \
  VENV/bin/python spikes/f5-preguntale-al-sistema/orchestrator.py "¿cuánto vendimos hoy en el salón?"
```

> **Nota data real (2026-08-13)**: en PROD el canal activo es `restaurant` (salón):
> hoy S/ 494 en 12 ventas. El canal `delivery` está vacío en prod (los 36 pedidos
> DLV- son de las E2E, todos `cancelled`). El LLM distingue canal por palabras clave
> (salón/local → restaurant; delivery/zonas → delivery).
> La BD QA tiene data sembrada de delivery (6 ventas hoy) para el eval controlado.

### 3. Eval mínimo
```bash
VENV/bin/python spikes/f5-preguntale-al-sistema/eval_golden.py            # fallback
VENV/bin/python spikes/f5-preguntale-al-sistema/eval_golden.py --llm      # DeepSeek
```

---

## 📊 Resultados del eval (2026-08-13, BD QA con seed)

| Modo | Tool accuracy | Data accuracy | Promedio |
|---|---|---|---|
| **Fallback determinista** | 100% (5/5) | 100% (5/5) | 44 ms |
| **DeepSeek (function calling)** | 100% (5/5) | 100% (5/5) | 5.2 s |

Golden queries: G1 "cuánto vendió hoy" (S/205), G2/G3 top productos,
G4 zona Montenegro (S/95), G5 "ayer" (S/28) — todas verificadas contra la BD.

**Demo read-only contra PROD (data real)**: "¿cuánto vendimos hoy en el salón?" →
S/ 494 en 12 ventas (restaurant, 2026-08-13) · "¿qué plato se vendió más hoy?" →
Delivery fee 12 und / Arroz con Mariscos S/224 · "¿ayer?" → delivery S/0 (correcto).

---

## 🧠 Aprendizajes clave

1. **El puerto hexagonal BaseSkill es correcto y suficiente** — el spike lo
   materializó sin tocar `app/core/agents/base.py`. Las tools son stateless,
   reciben contexto y devuelven `SkillResult`-like → escala horizontal.
2. **Function calling funciona con DeepSeek** (`deepseek-v4-flash`, API
   compatible OpenAI). El LLM eligió la tool correcta en 5/5 sin prompts
   complejos; solo con las descripciones de cada tool.
3. **Catálogo cerrado = seguridad real**: la IA solo elige entre 3 funciones
   fijas con SELECT puro. No hay forma de que escriba SQL libre ni acceda a
   otros tenants (tenant_id se fija en el runtime, no lo elige la IA).
4. **Fallback determinista es sorprendentemente bueno** (100% en el test set)
   y útil como respaldo de degradación elegante si el LLM cae.
5. **`fecha: ""` que manda el LLM debe sanearse a None** (la tool usa
   CURRENT_DATE en SQL cuando no hay fecha) — ya corregido en `run_tool`.
6. **Latencia**: 2.4s LLM vs 35ms fallback. Para el panel, 2.4s es aceptable
   para un chat; se puede cachear por (pregunta_normalizada, fecha).
7. **Bug corregido (fecha=None)**: la tool con `fecha=None` no filtraba por
   CURRENT_DATE (devolvía TODAS las ventas) → ahora `sale_date = CURRENT_DATE`.
   El eval G1/G4 se actualizó a los valores reales (S/205, S/95).
8. **Canal (business_type) parametrizable**: en prod el canal activo es
   `restaurant` (salón). El LLM lo infiere por palabras clave; el fallback
   prioriza restaurant por defecto.

---

## 🔒 Seguridad (diseño F5 validado)

- **Solo SELECT** — las queries están fijas en `ventas_skill.py`; ninguna tool
  acepta texto SQL.
- **Args validados** — solo keys del schema; strings vacíos → None.
- **Tenant scope** — todo filtrado por `tenant_id` (1 en QA).
- **Logging** — cada `ask()` devuelve pregunta, tool, args, modo, ms
  (base para el log de auditoría del F5 real).

---

## 📈 Cómo escala a F5 real (recomendación)

| Aspecto | Spike | F5 producción |
|---|---|---|
| Skills | 1 (VentasSkill, 3 tools) | + InventarioSkill, FinanzasSkill (mismo patrón) |
| Registro | lista simple | `SkillRegistry` existente + `SkillLoader` por decorador |
| Endpoint | CLI | `POST /api/v1/agents/ask` (auth JWT + rol dueño, rate limit) |
| UI | — | Chat en panel del dueño (v1) + WhatsApp (v2) |
| Eval | 5 golden | test set por skill + chequeo automático vs BD + human-in-the-loop |
| Logging | stdout | tabla `agent_qa_log` (quién, qué, cuándo, tool, respuesta) |
| LLM | DeepSeek flash | DeepSeek flash (barato) + fallback determinista en prod |

**Esfuerzo F5 real estimado**: 3–5 semanas (MVP delivery: 3 skills + endpoint +
chat panel + eval + logging). Precio sugerido **S/ 5,000 – 8,000** (según §9).

**Pendiente para F5 formal** (fuera del spike):
- Spec 09 en `docs/specs/` (SDD, Spec Anchor)
- Integración real con `app/core/agents/base.py` (BaseSkill + SkillRegistry)
- Endpoint autenticado + rate limiting + tabla de auditoría
- UI del chat + golden queries ampliadas + test suite

---

## ⚠️ Notas de entorno (lo que costó)

- La BD QA estaba en migración 0005 (vieja) y el grafo alembic tiene 3 ramas
  (baseline `0000_baseline` + principal + `4bc771f43a4e`) que **deadlockean el
  pool async de alembic en BD vacía** (2 conexiones se bloquean entre sí en
  migraciones con FK a tablas recién creadas). Solución usada: **clonar esquema
  de prod con `pg_dump --schema-only`** (solo estructura, sin datos) → restaurar
  en QA → fijar `alembic_version = 0018_call_records`. Rápido y fiel.
- Se creó `env_single.py` temporal (conexión única psycopg3) pero NO se usó
  para el esquema final (el dump fue más directo). El `env.py` original fue
  **restaurado** — verificar `git status` antes de commitear.
- `lock_timeout = 10s` quedó configurado global en postgres (ALTER SYSTEM) —
  conveniente para QA; no afecta funcionalidad.
