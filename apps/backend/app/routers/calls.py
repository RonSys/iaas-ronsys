"""
📞 Router — Central Telefónica (Spec 05 F2, §3.5).

  - Staff (JWT + X-Tenant-ID): GET /api/v1/calls, GET /api/v1/calls/{id},
    POST /api/v1/calls/{id}/convert-to-order, POST /api/v1/calls/originate,
    WS /api/v1/calls/ws/{tenant_id} (panel en vivo, §3.5.3).
  - Servicio interno (call-bridge): POST /api/v1/calls/events con token de
    servicio + allowlist de IPs (§3.5.2, CA-F2.5).

El WS sigue el patrón de /api/v1/restaurant/ws/kitchen/{tenant_id}: el
prefijo del router aplica también a websockets → el shorthand de la spec
`/ws/calls/{tenant}` se resuelve a `/api/v1/calls/ws/{tenant_id}` (mismo
criterio documentado en apps/web/src/services/callsApi.ts).
"""

import ipaddress
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.config import settings
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.core.ws_manager import manager
from app.models.user import User
from app.schemas.calls import (
    CallEventIn,
    CallEventOut,
    CallListResponse,
    CallRecordOut,
    ConvertToOrderRequest,
    ConvertToOrderResponse,
    OriginateRequest,
    OriginateResponse,
)
from app.services import call_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calls", tags=["Central Telefónica"])


# ═══════════════════════════════════════════════════════════════
# Llamadas — staff (auth JWT + X-Tenant-ID, siempre tenant-scoped)
# ═══════════════════════════════════════════════════════════════

@router.get("", response_model=CallListResponse)
async def list_calls(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtro por estado"),
    direction: str | None = Query(None, description="inbound | outbound"),
    from_dt: datetime | None = Query(None, alias="from", description="Inicio rango started_at"),
    to_dt: datetime | None = Query(None, alias="to", description="Fin rango started_at"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Histórico de llamadas del tenant (R4 — aislamiento por tenant)."""
    return await call_service.list_calls(
        db, tenant_id, status=status, direction=direction,
        date_from=from_dt, date_to=to_dt, limit=limit, offset=offset,
    )


@router.get("/{call_id}", response_model=CallRecordOut)
async def get_call(
    call_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Detalle de una llamada — 404 si no existe o es cross-tenant (CA-F2.6)."""
    return await call_service.get_call(db, tenant_id, call_id)


@router.post("/{call_id}/convert-to-order", response_model=ConvertToOrderResponse, status_code=201)
async def convert_to_order(
    call_id: int,
    body: ConvertToOrderRequest,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Convierte la llamada en pedido de delivery (R6/R7).

    201 {tracking_code, sale_id, sale_number, status, totals, call_id} |
    404 | 409 conversión duplicada | 422 llamada en curso / sin zona / ítems.
    """
    return await call_service.convert_to_order(
        db, tenant_id, call_id, body.model_dump(exclude_unset=True),
    )


@router.post("/originate", response_model=OriginateResponse, status_code=202)
async def originate(
    body: OriginateRequest,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Click-to-call (CA-F2.8): registra la saliente y pide el Originate al bridge.

    202 {external_call_id, status: "ringing"} | 400 número inválido |
    409 operador con llamada activa.
    """
    return await call_service.originate(
        db, tenant_id, body.target, body.extension,
    )


# ═══════════════════════════════════════════════════════════════
# Evento interno del call-bridge (token de servicio + allowlist IP)
# ═══════════════════════════════════════════════════════════════

def _client_ips(request: Request) -> list[str]:
    """IPs a evaluar contra la allowlist: cliente directo + X-Forwarded-For.

    Detrás de nginx el `client.host` es el proxy; el call-bridge en la misma
    máquina (AMI/ARI bind 127.0.0.1, D3) llega como 127.0.0.1 o por la red
    interna de docker (172.x) — el deploy configura la subred real en
    `CALL_EVENTS_ALLOWED_IPS`. X-Forwarded-For solo se considera si lo
    configura nginx para la ruta interna (nunca se confía a ciegas).
    """
    ips: list[str] = []
    if request.client and request.client.host:
        ips.append(request.client.host)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            ips.append(first)
    return ips


def _ip_allowed(ip: str) -> bool:
    """Permite IPs/CIDR listados en settings.call_events_allowed_ips."""
    raw = settings.call_events_allowed_ips or ""
    for entry in [e.strip() for e in raw.split(",") if e.strip()]:
        try:
            if "/" in entry:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(entry, strict=False):
                    return True
            elif ipaddress.ip_address(ip) == ipaddress.ip_address(entry):
                return True
        except ValueError:
            logger.warning("allowlist call-events con entrada inválida: %r", entry)
            continue
    return False


def _authorize_bridge(request: Request) -> None:
    """CA-F2.5: 401 sin token de servicio configurado/incorrecto; 403 IP no autorizada."""
    if not settings.call_bridge_token:
        raise HTTPException(
            status_code=401,
            detail="Token de servicio no configurado (CALL_BRIDGE_TOKEN vacío)",
        )
    token = (
        request.headers.get("X-Service-Token")
        or (request.headers.get("Authorization", "").removeprefix("Bearer ").strip())
        or ""
    )
    if token != settings.call_bridge_token:
        raise HTTPException(status_code=401, detail="Token de servicio inválido")
    if not any(_ip_allowed(ip) for ip in _client_ips(request)):
        raise HTTPException(status_code=403, detail="IP no autorizada para eventos de llamadas")


@router.post("/events", response_model=CallEventOut)
async def call_events(
    body: CallEventIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Upsert de eventos AMI del call-bridge (R8, §3.5.2).

    `X-Service-Token: <token>` (o Authorization Bearer) + IP en allowlist.
    200 {id, created: bool} | 401 sin token | 403 IP no autorizada.
    """
    _authorize_bridge(request)
    return await call_service.upsert_from_ami(db, body.model_dump())


# ═══════════════════════════════════════════════════════════════
# WS panel en vivo (§3.5.3 — clon de /api/v1/restaurant/ws/kitchen)
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/{tenant_id}")
async def calls_websocket(ws: WebSocket, tenant_id: int):
    """Panel de llamadas en vivo: /api/v1/calls/ws/{tenant_id}.

    Eventos del servidor → cliente: call.incoming / call.answered /
    call.ended / call.recording_ready / call.converted. Ping/pong igual que
    /ws/kitchen. Solo recibe eventos de SU tenant (CA-F2.6 — broadcast por
    dict tenant en WsManager).
    """
    await manager.connect_calls(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect_calls(tenant_id, ws)
    except Exception:
        manager.disconnect_calls(tenant_id, ws)
