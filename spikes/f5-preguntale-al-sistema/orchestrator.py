"""
🧪 SPIKE F5 — Orquestador con function calling (DeepSeek) + fallback determinista.

Flujo:
  1. El usuario hace una pregunta en lenguaje natural.
  2. El LLM (DeepSeek, compatible OpenAI) decide QUÉ tool llamar y con QUÉ args
     (function calling real — la IA no escribe SQL).
  3. Se ejecuta la tool (SOLO LECTURA) contra la BD QA.
  4. El LLM resume el resultado en lenguaje natural.

Fallback determinista (sin API key / error): un clasificador simple por
palabras clave elige la tool — valida el flujo end-to-end igualmente.

Seguridad (diseño F5):
  - Catálogo cerrado: la IA solo elige entre TOOLS definidas (nunca SQL libre).
  - Args validados: solo keys del schema de la tool, tipos saneados.
  - Solo SELECT: las queries son fijas en ventas_skill.py.
  - Tenant scope: tenant_id siempre fijado (default 1 en QA).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ventas_skill import TOOLS, run_tool  # noqa: E402

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.environ.get("F5_MODEL", "deepseek-v4-flash")
DEEPSEEK_TIMEOUT = int(os.environ.get("F5_TIMEOUT", "45"))


# ═══════════════════════════════════════════════════════════════
# Schema de tools para function calling (formato OpenAI-compatible)
# ═══════════════════════════════════════════════════════════════

def tools_schema() -> list[dict]:
    out = []
    for t in TOOLS:
        props, required = {}, []
        for p in t.params:
            ptype = "string" if p["type"] == "string" else "integer"
            props[p["name"]] = {
                "type": ptype,
                "description": p.get("description", ""),
            }
            if p.get("required"):
                required.append(p["name"])
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            }
        )
    return out


# ═══════════════════════════════════════════════════════════════
# Cliente LLM (DeepSeek — compatible OpenAI)
# ═══════════════════════════════════════════════════════════════

def _call_llm(system: str, user: str) -> dict:
    """Chat completion con tools. Devuelve mensaje del asistente."""
    import urllib.request

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "tools": tools_schema(),
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=DEEPSEEK_TIMEOUT) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]


# ═══════════════════════════════════════════════════════════════
# Fallback determinista (sin LLM) — valida el flujo end-to-end
# ═══════════════════════════════════════════════════════════════

_FALLBACK_RULES = [
    ("top_productos_dia", ["producto", "vendió más", "vendido más", "top", "cuál se vendió", "más vendido", "qué plato", "más pedido"]),
    ("ventas_por_zona_dia", ["zona", "distrito", "por zona", "zona 1", "zona 2", "zona 3"]),
    ("ventas_del_dia", ["cuánto vendió", "cuánto se vendió", "total", "venta total", "cuántos pedidos", "cuánto vendimos", "cuánto fue", "resumen", "hoy"]),
]


def _fallback_tool(question: str) -> tuple[str, dict]:
    """Elige tool por palabras clave. Devuelve (tool_name, args)."""
    q = question.lower()
    # Fecha: detectar "ayer"
    args: dict[str, Any] = {}
    import datetime
    if re.search(r"\bayer\b|día de ayer|de ayer", q):
        args["fecha"] = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for name, keywords in _FALLBACK_RULES:
        if any(k in q for k in keywords):
            if name == "top_productos_dia":
                m = re.search(r"\b(3|5|10)\b", q)
                if m:
                    args["limite"] = int(m.group(1))
            return name, args
    return "ventas_del_dia", args


# ═══════════════════════════════════════════════════════════════
# Resumen en lenguaje natural (template simple)
# ═══════════════════════════════════════════════════════════════

def _summarize(tool: str, result: dict, question: str) -> str:
    r = result.get("result", {})
    fecha = r.get("fecha", "hoy")
    if tool == "ventas_del_dia":
        canal = "delivery" if r.get("canal", "delivery") == "delivery" else "salón"
        return (
            f"📊 Ventas {canal} del {fecha}: **S/ {r['total_ventas']:.2f}** en "
            f"{r['num_ventas']} pedidos (S/ {r['total_entregado']:.2f} entregados)."
        )
    if tool == "top_productos_dia":
        canal = "delivery" if r.get("canal", "delivery") == "delivery" else "salón"
        lines = [f"🏆 Top {len(r.get('top', []))} productos {canal} del {fecha}:"]
        for i, p in enumerate(r.get("top", []), 1):
            lines.append(
                f"  {i}. {p['producto']} — {p['cantidad']:.0f} und en {p['ventas']} ventas (S/ {p['total_soles']:.2f})"
            )
        return "\n".join(lines)
    if tool == "ventas_por_zona_dia":
        lines = [f"🗺️ Ventas por zona del {fecha}:"]
        for z in r.get("zonas", []):
            lines.append(f"  • {z['zona']}: {z['pedidos']} pedidos — S/ {z['total_soles']:.2f}")
        return "\n".join(lines)
    return f"{tool}: {json.dumps(r, ensure_ascii=False)}"


# ═══════════════════════════════════════════════════════════════
# Orquestador principal
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "Eres el asistente de datos de El Segoviano (restaurante con delivery). "
    "El usuario pregunta en lenguaje natural sobre ventas. "
    "Usa SIEMPRE las herramientas disponibles (catálogo cerrado — nunca inventes SQL ni datos). "
    "Si la pregunta menciona salón, local, platos o comida preparada, usa business_type='restaurant'. "
    "Si menciona delivery, pedidos a domicilio o zonas, usa business_type='delivery'. "
    "Por defecto (sin pista de canal) usa business_type='restaurant' (es el canal con más ventas). "
    "Si la pregunta no coincide con ninguna herramienta, usa ventas_del_dia y di que es un resumen general. "
    "Responde en español, conciso, con números exactos de la herramienta. "
    "Si la fecha es 'ayer', pasa la fecha real (YYYY-MM-DD) en los argumentos."
)


def ask(question: str, use_llm: bool | None = None) -> dict:
    """
    Pregunta en lenguaje natural → respuesta con dato real.
    use_llm: True=DeepSeek, False=fallback, None=auto (LLM si hay key).
    """
    started = time.time()
    use_llm = (DEEPSEEK_API_KEY != "") if use_llm is None else use_llm
    mode = "llm" if use_llm else "fallback"

    tool_name, args = None, {}
    llm_message = None
    error = None

    if use_llm:
        try:
            msg = _call_llm(SYSTEM_PROMPT, question)
            llm_message = msg
            if msg.get("tool_calls"):
                tc = msg["tool_calls"][0]
                tool_name = tc["function"]["name"]
                args = json.loads(tc["function"].get("arguments") or "{}")
        except Exception as e:  # noqa: BLE001
            error = str(e)[:120]
            mode = "fallback"

    if not tool_name:
        tool_name, args = _fallback_tool(question)

    result = run_tool(tool_name, args)
    elapsed_ms = int((time.time() - started) * 1000)

    summary = _summarize(tool_name, result, question)
    return {
        "pregunta": question,
        "modo": mode,
        "tool": tool_name,
        "args": args,
        "resumen": summary,
        "elapsed_ms": elapsed_ms,
        "llm_error": error,
        "_tool_result": result.get("result"),  # para eval (data accuracy)
    }


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "¿cuánto vendió hoy?"
    force_fallback = "--fallback" in sys.argv
    r = ask(q, use_llm=False if force_fallback else None)
    print(f"Pregunta: {r['pregunta']}")
    print(f"Modo: {r['modo']} | Tool: {r['tool']} | Args: {r['args']} | {r['elapsed_ms']}ms")
    if r.get("llm_error"):
        print(f"(fallback por error LLM: {r['llm_error']})")
    print()
    print(r["resumen"])
