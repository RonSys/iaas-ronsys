"""
🧪 SPIKE F5 — Eval mínimo (Bloque C en miniatura): golden queries + exactitud.

Cada golden query tiene:
  - pregunta (lenguaje natural)
  - tool esperada
  - verificación: función que valida el resultado contra la BD real (SQL esperado)

Métricas:
  - tool_accuracy: % de veces que eligió la tool correcta
  - data_accuracy: % de respuestas con dato numérico correcto (dato == BD real)
  - avg_ms: latencia promedio

Modo: --llm (DeepSeek) o --fallback (determinista).
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import ask  # noqa: E402
from ventas_skill import _conn  # noqa: E402

# ═══════════════════════════════════════════════════════════════
# Golden queries (respuestas esperadas calculadas contra la BD QA)
# ═══════════════════════════════════════════════════════════════

GOLDEN = [
    {
        "id": "G1",
        "pregunta": "¿cuánto vendió hoy en delivery?",
        "tool": "ventas_del_dia",
        "check": lambda r: abs(r["total_ventas"] - 205.00) < 0.01,
        "detalle": "total_ventas == 205.00 (6 ventas de hoy: 28+37+32+42+30+36)",
    },
    {
        "id": "G2",
        "pregunta": "¿qué producto se vendió más hoy?",
        "tool": "top_productos_dia",
        "check": lambda r: r["top"][0]["producto"] == "Arroz con Mariscos",
        "detalle": "top[0] == Arroz con Mariscos (2 und, S/64)",
    },
    {
        "id": "G3",
        "pregunta": "¿cuál es el top 3 de productos hoy?",
        "tool": "top_productos_dia",
        "check": lambda r: len(r["top"]) == 3,
        "detalle": "len(top) == 3 (límite respetado)",
    },
    {
        "id": "G4",
        "pregunta": "¿cuánto vendió la zona de Montenegro hoy?",
        "tool": "ventas_por_zona_dia",
        "check": lambda r: any(z["zona"] == "Montenegro" and abs(z["total_soles"] - 95.00) < 0.01 for z in r["zonas"]),
        "detalle": "Montenegro == S/95 (DLV 1001+1002+1005 de hoy: 28+37+30)",
    },
    {
        "id": "G5",
        "pregunta": "¿cuánto vendimos ayer?",
        "tool": "ventas_del_dia",
        "check": lambda r: abs(r["total_ventas"] - 28.00) < 0.01,
        "detalle": "ayer == S/28 (1 venta SPK-0901)",
    },
]


def run_eval(use_llm: bool) -> dict:
    results = []
    for g in GOLDEN:
        started = time.time()
        try:
            r = ask(g["pregunta"], use_llm=use_llm)
            elapsed = time.time() - started
            tool_ok = r["tool"] == g["tool"]
            # El check recibe el result de la tool
            tool_result = r.get("_tool_result")
            data_ok = bool(g["check"](tool_result)) if tool_result is not None else False
            results.append(
                {
                    "id": g["id"],
                    "pregunta": g["pregunta"],
                    "tool_esperada": g["tool"],
                    "tool_usada": r["tool"],
                    "tool_ok": tool_ok,
                    "data_ok": data_ok,
                    "ms": r["elapsed_ms"],
                    "modo": r["modo"],
                    "resumen": r["resumen"],
                }
            )
        except Exception as e:  # noqa: BLE001
            results.append(
                {"id": g["id"], "pregunta": g["pregunta"], "tool_ok": False, "data_ok": False, "ms": 0, "modo": "error", "error": str(e)[:100]}
            )

    n = len(results)
    tool_acc = sum(1 for x in results if x["tool_ok"]) / n
    data_acc = sum(1 for x in results if x["data_ok"]) / n
    avg_ms = sum(x.get("ms", 0) for x in results) / n
    return {
        "modo": "llm" if use_llm else "fallback",
        "golden": results,
        "tool_accuracy": tool_acc,
        "data_accuracy": data_acc,
        "avg_ms": int(avg_ms),
    }


if __name__ == "__main__":
    use_llm = "--llm" in sys.argv
    report = run_eval(use_llm)
    print(f"\n📊 EVAL SPIKE F5 (modo: {report['modo'].upper()})")
    print(f"{'='*70}")
    for x in report["golden"]:
        status = "✅" if (x["tool_ok"] and x["data_ok"]) else "❌"
        print(
            f"{status} {x['id']} [{x.get('tool_usada', '?')}] {x['pregunta']} "
            f"({x.get('ms', 0)}ms)"
        )
        if not x["tool_ok"]:
            print(f"   tool esperada: {x['tool_esperada']} — usada: {x.get('tool_usada', 'N/A')}")
        if not x.get("data_ok", False):
            print(f"   data: {x.get('resumen', x.get('error', '?'))[:100]}")
    print(f"{'='*70}")
    print(
        f"🎯 Tool accuracy: {report['tool_accuracy']*100:.0f}% "
        f"| Data accuracy: {report['data_accuracy']*100:.0f}% "
        f"| Promedio: {report['avg_ms']}ms"
    )
    # Guardar reporte JSON
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_report.json")
    with open(out, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 Reporte: {out}")
