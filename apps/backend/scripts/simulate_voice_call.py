"""
📞 Simulador del Voice-Bridge F3 (Fase 2a) — validación end-to-end SIN Asterisk.

Crea un call_record de prueba vía la API del backend (POST /api/v1/calls/events
con external_call_id 'f3-sim-<ts>') y ejecuta el flujo del bridge en modo
simulado (STT echo, LLM determinista de Fase 1, TTS stub), terminando en
POST /complete (con create_order si hubo items confirmados — R7/R9).

El menú del contexto es DATOS DE DEMOSTRACIÓN del simulador (no el menú
real del tenant — R1 aplica al servicio en producción, no a este harness).

Uso:
  cd apps/backend
  SERVICE_TOKEN=<token> BACKEND_INTERNAL_URL=http://127.0.0.1:8000 \
    .venv/bin/python -m scripts.simulate_voice_call \
      --turns "Hola, buenas noches" "Quiero 2 ceviches mixtos" "Sí, confirmo mi pedido" \
      --zone-id 1

Exit 0 = flujo completo OK; 1 = error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.voice_bridge import VoiceBridge, build_providers  # noqa: E402

logger = logging.getLogger("simulate_voice_call")

# Datos de DEMO del simulador (NO es el menú real — ver docstring)
DEMO_CONTEXT = {
    "tenant_name": "El Segoviano (simulador F3)",
    "currency": "PEN",
    "sections": [
        {
            "name": "Marinos",
            "items": [
                {"id": 10, "name": "Ceviche Mixto", "price": 38.0, "modifiers": []},
                {"id": 11, "name": "Jalea Mixta", "price": 45.0, "modifiers": []},
                {"id": 12, "name": "Arroz con Mariscos", "price": 42.0, "modifiers": []},
            ],
        }
    ],
    "zones": [{"id": 1, "name": "Zona Demo"}],
    "rules": {"no_inventar": "contexto de DEMO del simulador — no es el menú real"},
}

DEFAULT_TURNS = [
    "Hola, buenas noches",
    "Quiero 2 ceviches mixtos",
    "Sí, confirmo mi pedido",
]


async def _load_real_menu(tenant_id: int) -> dict:
    """Carga el menú REAL del tenant desde la BD (R1 — el simulador no inventa).

    Reemplaza el DEMO_CONTEXT cuando DATABASE_URL está disponible: usa
    get_public_menu/get_public_zones del servicio de delivery (los mismos que
    usa la IA en producción) para que create_order valide items reales.
    """
    import logging as _log

    from app.services.delivery_service import get_public_menu, get_public_zones

    async with await _session_factory() as db:
        menu = await get_public_menu(db, tenant_id)
        zones = await get_public_zones(db, tenant_id)
        n_items = sum(len(s.get("items", [])) for s in menu.get("sections", []))
        _log.getLogger("simulate_voice_call").info(
            "menú real cargado: %d items, %d zonas (tenant %d)",
            n_items, len(zones or []), tenant_id,
        )
    return {
        "tenant_name": menu.get("tenant_name", "El Segoviano (QA)"),
        "currency": "PEN",
        "sections": menu.get("sections", []),
        "zones": zones or [],
    }


async def _session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    url = os.getenv("DATABASE_URL") or "postgresql+asyncpg://ron:ron123@localhost:5432/iaas_ronsys_qa"
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    return Session()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulador del voice-bridge F3 (Fase 2a)")
    p.add_argument("--turns", nargs="+", default=DEFAULT_TURNS,
                   help="Turnos del cliente (texto simulado, STT echo)")
    p.add_argument("--zone-id", type=int, default=1, help="Zona de delivery del pedido (demo)")
    p.add_argument("--tenant-id", type=int, default=1, help="Tenant (MVP 1 tenant)")
    p.add_argument("--external-call-id", default=None,
                   help="Default: f3-sim-<ts>")
    p.add_argument("--delay", type=float, default=0.0,
                   help="pausa en segundos entre turnos (demo E2E visible)")
    p.add_argument("--no-confirm", action="store_true",
                   help="No termina con confirmación → cierre sin create_order")
    return p.parse_args()


async def _main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not os.getenv("SERVICE_TOKEN"):
        logger.warning("SERVICE_TOKEN vacío — el backend rechazará los eventos (401)")

    external_call_id = args.external_call_id or f"f3-sim-{int(time.time())}"
    turns = args.turns or DEFAULT_TURNS
    if args.no_confirm:
        turns = turns[:-1]  # sin el turno de confirmación

    context = DEMO_CONTEXT
    if os.getenv("DATABASE_URL"):
        context = await _load_real_menu(args.tenant_id)

    bridge = VoiceBridge(
        providers=build_providers("echo", "local", "deterministic"),
        tenant_id=args.tenant_id,
        simulated=True,
    )

    logger.info(
        "simulando llamada %s (%d turnos) contra %s ...",
        external_call_id, len(turns), bridge.backend.base_url,
    )
    summary = await bridge.run_simulated_call(
        external_call_id, turns, context=context, order_zone_id=args.zone_id,
        turn_delay_sec=args.delay,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary.get("attended"):
        print(f"\n→ NO se atendió ({summary.get('reason')}) — ring_operator (R5)")
        return 0
    print(f"\n→ {summary.get('ended', '?')} | complete: {summary.get('complete')}")
    print(f"→ {len(summary.get('turns', []))} turnos | order: {'SÍ (create_order)' if summary.get('order') else 'no'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        logger.error("simulador falló: %s", exc)
        sys.exit(1)
