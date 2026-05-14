"""
📡 WebSocket Manager — Cocina + Meseros (F0-006).

Gestiona conexiones WebSocket para:
  - Pantalla de cocina (kitchen): recibe nuevas comandas en tiempo real
  - Notificaciones a meseros (waiter): comandas listas

Uso:
    from app.core.ws_manager import manager
    await manager.broadcast_to_kitchen(tenant_id, event_type, data)
"""

import json
from typing import Any

from fastapi import WebSocket


class WsManager:
    """Gestor centralizado de conexiones WebSocket por tenant y rol."""

    def __init__(self):
        # {tenant_id: [WebSocket, ...]}
        self._kitchen: dict[int, list[WebSocket]] = {}
        # {tenant_id: [WebSocket, ...]}
        self._waiters: dict[int, list[WebSocket]] = {}

    # ─── Conexión / Desconexión ──────────────────────────────

    async def connect_kitchen(self, tenant_id: int, ws: WebSocket):
        await ws.accept()
        self._kitchen.setdefault(tenant_id, []).append(ws)

    def disconnect_kitchen(self, tenant_id: int, ws: WebSocket):
        if tenant_id in self._kitchen and ws in self._kitchen[tenant_id]:
            self._kitchen[tenant_id].remove(ws)

    async def connect_waiter(self, tenant_id: int, ws: WebSocket):
        await ws.accept()
        self._waiters.setdefault(tenant_id, []).append(ws)

    def disconnect_waiter(self, tenant_id: int, ws: WebSocket):
        if tenant_id in self._waiters and ws in self._waiters[tenant_id]:
            self._waiters[tenant_id].remove(ws)

    # ─── Broadcast ───────────────────────────────────────────

    async def broadcast_to_kitchen(self, tenant_id: int, event: str, data: Any):
        """Envía un evento a todas las pantallas de cocina del tenant."""
        payload = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        for ws in self._kitchen.get(tenant_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_kitchen(tenant_id, ws)

    async def broadcast_to_waiter(self, tenant_id: int, event: str, data: Any):
        """Envía una notificación a todos los meseros del tenant."""
        payload = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        for ws in self._waiters.get(tenant_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_waiter(tenant_id, ws)


# Singleton
manager = WsManager()
