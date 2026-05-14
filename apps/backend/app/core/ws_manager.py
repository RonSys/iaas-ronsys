"""
🔌 WebSocket Manager — Comunicación cocina/meseros en tiempo real.

HU-F0-006: WebSockets para:
  - Pantalla de cocina:  /ws/kitchen/{tenant_id}
  - Notificaciones meseros: /ws/waiter/{tenant_id}

Eventos:
  - new_order:        Nueva comanda enviada a cocina
  - order_ready:      Cocina marca orden como lista
  - order_cancelled:  Orden cancelada
  - state_sync:       Estado completo al reconectar (full state sync)

Fallback: Polling cada 10s si WS no está disponible (feature flag).
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestiona conexiones WebSocket agrupadas por tenant.

    Dos canales por tenant:
      - kitchen: pantalla de cocina (recibe new_order, envía order_ready)
      - waiter: notificaciones a meseros (recibe order_ready, envía new_order)
    """

    def __init__(self):
        self._kitchen: dict[int, list[WebSocket]] = {}  # tenant_id → [ws, ...]
        self._waiter: dict[int, list[WebSocket]] = {}   # tenant_id → [ws, ...]

    # ─── Conexión / Desconexión ──────────────────────────────

    async def connect_kitchen(self, tenant_id: int, ws: WebSocket):
        await ws.accept()
        if tenant_id not in self._kitchen:
            self._kitchen[tenant_id] = []
        self._kitchen[tenant_id].append(ws)
        logger.info(f"[WS] Kitchen connected: tenant={tenant_id}, total={len(self._kitchen[tenant_id])}")

    async def connect_waiter(self, tenant_id: int, ws: WebSocket):
        await ws.accept()
        if tenant_id not in self._waiter:
            self._waiter[tenant_id] = []
        self._waiter[tenant_id].append(ws)
        logger.info(f"[WS] Waiter connected: tenant={tenant_id}, total={len(self._waiter[tenant_id])}")

    def disconnect_kitchen(self, tenant_id: int, ws: WebSocket):
        if tenant_id in self._kitchen:
            self._kitchen[tenant_id] = [w for w in self._kitchen[tenant_id] if w != ws]
            if not self._kitchen[tenant_id]:
                del self._kitchen[tenant_id]

    def disconnect_waiter(self, tenant_id: int, ws: WebSocket):
        if tenant_id in self._waiter:
            self._waiter[tenant_id] = [w for w in self._waiter[tenant_id] if w != ws]
            if not self._waiter[tenant_id]:
                del self._waiter[tenant_id]

    # ─── Envío de eventos ────────────────────────────────────

    async def broadcast_to_kitchen(self, tenant_id: int, event: str, data: dict[str, Any]):
        """Envía evento a TODAS las pantallas de cocina de un tenant."""
        payload = json.dumps({"event": event, "data": data}, default=str)
        await self._broadcast(self._kitchen.get(tenant_id, []), payload)

    async def broadcast_to_waiter(self, tenant_id: int, event: str, data: dict[str, Any]):
        """Envía evento a TODOS los meseros de un tenant."""
        payload = json.dumps({"event": event, "data": data}, default=str)
        await self._broadcast(self._waiter.get(tenant_id, []), payload)

    async def broadcast_to_all(self, tenant_id: int, event: str, data: dict[str, Any]):
        """Envía evento a TODOS (cocina + meseros) de un tenant."""
        await self.broadcast_to_kitchen(tenant_id, event, data)
        await self.broadcast_to_waiter(tenant_id, event, data)

    async def _broadcast(self, connections: list[WebSocket], payload: str):
        """Envía payload a todas las conexiones activas, eliminando las caídas."""
        stale = []
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            try:
                await ws.close()
            except Exception:
                pass
        # Remover conexiones caídas de la lista original
        for ws in stale:
            if connections.count(ws):
                connections.remove(ws)

    # ─── Full state sync ─────────────────────────────────────

    async def send_state_sync(self, ws: WebSocket, orders: list[dict]):
        """Envía el estado completo de las órdenes activas (reconexión)."""
        payload = json.dumps({
            "event": "state_sync",
            "data": {"orders": orders},
        }, default=str)
        try:
            await ws.send_text(payload)
        except Exception:
            pass

    # ─── Stats ───────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "kitchen_connections": sum(len(v) for v in self._kitchen.values()),
            "waiter_connections": sum(len(v) for v in self._waiter.values()),
            "active_tenants_kitchen": len(self._kitchen),
            "active_tenants_waiter": len(self._waiter),
        }


# ─── Singleton ────────────────────────────────────────────────

manager = ConnectionManager()
