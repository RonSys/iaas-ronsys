# 📋 Plan: Pipeline OpenRouter — Modelos por Agente

> **Estado actual:** Auth-profiles migrados a OpenRouter  
> **Pendiente:** Que cada agente use el modelo correcto sin fallar  
> **ChatBot:** Se mantiene con DeepSeek (NO se toca)

---

## 🔍 Diagnóstico — ¿Por qué falla hoy?

### Causa raíz

El `openclaw.json` define un **modelo default global**:

```json
"model": { "primary": "deepseek/deepseek-v4-pro" }
```

Cuando cualquier agente (excepto ChatBot) abre una sesión:
1. Toma el modelo default → `deepseek/deepseek-v4-pro`
2. Busca una API key para el provider `deepseek`
3. No la encuentra (solo tiene `openrouter:default`)
4. ❌ Falla: "No se encontró una clave de API para el proveedor 'deepseek'"

### Archivos involucrados

| Archivo | Propósito |
|---------|-----------|
| `/home/ron/.openclaw/openclaw.json` | Define modelo default + providers + modelos disponibles |
| `/home/ron/.openclaw/agents/<id>/agent/auth-profiles.json` | Define API keys por agente |

---

## 🎯 Solución

Hay **2 opciones**. Depende de cómo quieras trabajar.

---

## Opción A: Cambiar el modelo default a OpenRouter (Recomendada)

### Cambio 1: `openclaw.json` — Modelo default

| Dónde | Línea/Sección | ANTES | DESPUÉS |
|-------|--------------|-------|---------|
| `agents.defaults.model.primary` | ~línea 10 | `"deepseek/deepseek-v4-pro"` | `"openrouter/deepseek/deepseek-v4-pro"` |

```diff
 "model": {
-  "primary": "deepseek/deepseek-v4-pro"
+  "primary": "openrouter/deepseek/deepseek-v4-pro"
 }
```

**Efecto:** TODOS los agentes nuevos arrancan usando OpenRouter por defecto. ChatBot mantiene su sesión actual con DeepSeek.

### Cambio 2: `chatbot/agent/auth-profiles.json` — Agregar OpenRouter

ChatBot necesita poder cambiar a OpenRouter si es necesario (aunque su default siga siendo DeepSeek en la sesión actual). No es obligatorio, pero es buena práctica si alguna vez inicias una nueva sesión de ChatBot.

Ruta: `/home/ron/.openclaw/agents/chatbot/agent/auth-profiles.json`

```diff
 {
   "version": 1,
   "profiles": {
-    "deepseek:default": { ... }
+    "deepseek:default": { ... },
+    "openrouter:default": {
+      "type": "api_key",
+      "provider": "openrouter",
+      "key": "***…<tu_key_openrouter>"
+    }
   }
 }
```

### Cambio 3: `jarvis/agent/auth-profiles.json` — Dejar ambas keys (ya está hecho)

JARVIS ya tiene ambas keys → no necesita cambios.

### Resultado final

| Agente | Auth profiles | Modelo al iniciar | ¿Funciona? |
|--------|:------------:|-------------------|:----------:|
| 🤖 **Jarvis** | DeepSeek + OpenRouter | `openrouter/deepseek/deepseek-v4-pro` | ✅ |
| 🏗️ **Architecture** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| 🧠 **Backend Dev** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| ⚛️ **Frontend Dev** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| 📋 **PO Agent** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| 🧪 **QA Agent** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| 🔧 **DevOps** | Solo OpenRouter | `openrouter/deepseek/deepseek-v4-pro` (default OR) | ✅ |
| 🤖💬 **ChatBot** | Solo DeepSeek | `deepseek/deepseek-v4-pro` (sesión actual) | ✅ |

**Pasos restantes:** Solo `openclaw.json` (1 línea) + opcional `chatbot/auth-profiles.json`

---

## Opción B: Mantener DeepSeek como default + key DeepSeek en todos los agentes

### Cambio 1: Los 6 agentes — Agregar key de DeepSeek

Los 6 agentes (Architecture, Backend, Frontend, PO, QA, DevOps) necesitan la key de DeepSeek **además** de OpenRouter (igual que JARVIS).

Ruta (para cada agente): `/home/ron/.openclaw/agents/<id>/agent/auth-profiles.json`

```json
{
  "version": 1,
  "profiles": {
    "deepseek:default": {
      "type": "api_key",
      "provider": "deepseek",
      "key": "***…<tu_key_deepseek>"
    },
    "openrouter:default": {
      "type": "api_key",
      "provider": "openrouter",
      "key": "***…<tu_key_openrouter>"
    }
  }
}
```

**6 archivos a modificar:**

| # | Agente | Ruta |
|---|--------|------|
| 1 | Architecture | `/home/ron/.openclaw/agents/architecture-agent/agent/auth-profiles.json` |
| 2 | Backend Dev | `/home/ron/.openclaw/agents/backend-dev-agent/agent/auth-profiles.json` |
| 3 | Frontend Dev | `/home/ron/.openclaw/agents/frontend-dev-agent/agent/auth-profiles.json` |
| 4 | PO Agent | `/home/ron/.openclaw/agents/product-owner-agent/agent/auth-profiles.json` |
| 5 | QA Agent | `/home/ron/.openclaw/agents/qa-agent/agent/auth-profiles.json` |
| 6 | DevOps | `/home/ron/.openclaw/agents/devops-agent/agent/auth-profiles.json` |

### Cambio 2: No tocar `openclaw.json`

El modelo default `deepseek/deepseek-v4-pro` se mantiene. Los agentes arrancan con DeepSeek y luego usas `/model` para cambiarlos a OpenRouter.

### Resultado final

| Agente | Auth profiles | Al iniciar | Para usar OR |
|--------|:------------:|-----------|--------------|
| 🤖 **Jarvis** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 🏗️ **Architecture** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 🧠 **Backend Dev** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| ⚛️ **Frontend Dev** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 📋 **PO Agent** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 🧪 **QA Agent** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 🔧 **DevOps** | DeepSeek + OR | ✅ DeepSeek | `/model` manual |
| 🤖💬 **ChatBot** | Solo DeepSeek | ✅ DeepSeek | ❌ No necesita |

**Pasos restantes:** Modificar 6 archivos `auth-profiles.json`

---

## 📊 Comparativa de Opciones

| Aspecto | Opción A (Default OR) | Opción B (Default DeepSeek) |
|---------|:--------------------:|:--------------------------:|
| **Archivos a modificar** | 1 (`openclaw.json`) | 6 (`auth-profiles.json`) |
| **Agentes arrancan con** | OpenRouter | DeepSeek |
| **Cambiar modelo** | Solo si querés otro OR | `/model` en cada sesión |
| **ChatBot afectado?** | ❌ (sesión actual intacta) | ❌ |
| **Comandos `/model` necesarios** | 0 (todos arrancan con el que toca) | 7 (cada agente excepto ChatBot) |

---

## 📝 Después de aplicar el cambio

Cuando todo funcione, los agentes seguirán usando DeepSeek V4 Pro por defecto. Para que usen el modelo que corresponde según el escenario Realista, necesitás ejecutar `/model` en la sesión de cada uno:

| Agente | Comando `/model` |
|--------|-----------------|
| 🤖 **Jarvis** (si Opción B) | `/model openrouter/deepseek/deepseek-v4-pro` |
| 🏗️ **Architecture** | `/model openrouter/x-ai/grok-4.3` |
| 🧠 **Backend Dev** | `/model openrouter/moonshotai/kimi-k2.6` |
| ⚛️ **Frontend Dev** | `/model openrouter/moonshotai/kimi-k2.6` |
| 📋 **PO Agent** | `/model openrouter/moonshotai/kimi-k2.6` |
| 🧪 **QA Agent** | `/model openrouter/inclusionai/ring-2.6-1t:free` |
| 🔧 **DevOps** | `/model openrouter/inclusionai/ring-2.6-1t:free` |

> 📌 **Nota:** El cambio de modelo con `/model` es **por sesión**. Si el gateway se reinicia, las sesiones se pierden y hay que volver a ejecutar `/model`.

---

## ✅ Verificación final

```bash
# Verificar que todos los agentes arrancan sin error
# Ir a Control UI → abrir cada agente → enviar un mensaje

# Verificar modelo activo en cada sesión
# En cualquier agente: /model
# Debe mostrar el modelo correcto (OR o DeepSeek según el caso)
```
