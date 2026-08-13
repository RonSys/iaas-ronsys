"""
🤖 Router — Recepcionista IA por Voz (Spec 06 F3, §3.5).

Extiende el recurso `/api/v1/calls` de F2 (misma superficie, work NUEVO de
F3 — la spec 06 los define como contratos propios):

  - Bridge interno (token de servicio + allowlist IP, IGUAL que /events de
    F2 — CA-F2.5): POST /{external_call_id}/transcript,
    GET/PATCH /{external_call_id}/ai-state, PATCH /{external_call_id}/ai-context,
    POST /{external_call_id}/transfer, POST /{external_call_id}/complete.
  - Staff (JWT + X-Tenant-ID): GET /{id|external_call_id}/transcript (CA-F3-3).
  - Alias de compatibilidad: POST /api/v1/ai-calls/{external_call_id}/transfer
    → mismo handler (HU-F3-03, contrato original del encargo).

WebSocket: los eventos `ai_call_state` / `call.transferred` se publican en el
canal WS de F2 (manager.broadcast_to_calls) — no hay WS nuevo.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.routers.calls import _authorize_bridge
from app.schemas.voice_ai import (
    AiCompleteIn,
    AiCompleteOut,
    AiContextIn,
    AiContextOut,
    AiStateIn,
    AiStateOut,
    AiTransferIn,
    AiTransferOut,
    TranscriptionIn,
    TranscriptionOut,
)
from app.services import voice_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calls", tags=["Recepcionista IA (F3)"])
# Alias de compatibilidad del contrato original del encargo (HU-F3-03)
alias_router = APIRouter(prefix="/api/v1/ai-calls", tags=["Recepcionista IA (F3)"])


# ═══════════════════════════════════════════════════════════════
# Transcripción (D8/R3 — §3.5.1 bridge / §3.5.2 staff)
# ═══════════════════════════════════════════════════════════════

@router.post("/{external_call_id}/transcript", response_model=TranscriptionOut, status_code=201)
async def save_transcript(
    external_call_id: str,
    body: TranscriptionIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Persiste la transcripción (streaming o final) — upsert por llamada.

    201 TranscriptionOut | 404 llamada inexistente/cross-tenant | 401/403 auth bridge.
    """
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.save_transcription(
        db, tenant_id, external_call_id, body.model_dump(),
    )


@router.get("/{call_ref}/transcript", response_model=TranscriptionOut)
async def get_transcript(
    call_ref: str,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """CA-F3-3: transcripción recuperable (por id de llamada o external_call_id)."""
    return await voice_ai_service.get_transcription(db, tenant_id, call_ref)


# ═══════════════════════════════════════════════════════════════
# Estado IA (R10 — §3.5.1 PATCH / GET + PATCH ai-context)
# ═══════════════════════════════════════════════════════════════

@router.get("/{external_call_id}/ai-state", response_model=AiStateOut)
async def get_ai_state(
    external_call_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Estado conversacional + costo acumulado + contexto (R10, panel en vivo)."""
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.get_ai_state(db, tenant_id, external_call_id)


@router.patch("/{external_call_id}/ai-state", response_model=AiStateOut)
async def patch_ai_state(
    external_call_id: str,
    body: AiStateIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza ai_state (§3.6) → emite WS ai_call_state (R10)."""
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.update_ai_state(
        db, tenant_id, external_call_id, body.model_dump(exclude_unset=True),
    )


@router.patch("/{external_call_id}/ai-context", response_model=AiContextOut)
async def patch_ai_context(
    external_call_id: str,
    body: AiContextIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resumen incremental para el operador (D9, §3.5.1)."""
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.update_context(
        db, tenant_id, external_call_id, body.context_summary,
    )


# ═══════════════════════════════════════════════════════════════
# Transferencia (D9/R2 — §3.5.1) + alias de compatibilidad
# ═══════════════════════════════════════════════════════════════

@router.post("/{external_call_id}/transfer", response_model=AiTransferOut)
async def transfer_call(
    external_call_id: str,
    body: AiTransferIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Transferencia a humano con contexto completo (D9).

    200 {transferred_to, via: "sip"} — el ring a la extensión del operador lo
    ejecuta el bridge (Fase 2); el panel ve el motivo + resumen en vivo.
    """
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.transfer_call(
        db, tenant_id, external_call_id, body.model_dump(exclude_unset=True),
    )


@alias_router.post("/{external_call_id}/transfer", response_model=AiTransferOut)
async def transfer_call_alias(
    external_call_id: str,
    body: AiTransferIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Alias /api/v1/ai-calls/{external_call_id}/transfer → mismo handler (HU-F3-03)."""
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.transfer_call(
        db, tenant_id, external_call_id, body.model_dump(exclude_unset=True),
    )


# ═══════════════════════════════════════════════════════════════
# Cierre (R4/R7/R9 — §3.5.1)
# ═══════════════════════════════════════════════════════════════

@router.post("/{external_call_id}/complete", response_model=AiCompleteOut)
async def complete_call(
    external_call_id: str,
    body: AiCompleteIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Cierre de la llamada IA: costo (R4) + create_order si hubo items (R7/R9)."""
    _authorize_bridge(request)
    tenant_id = await _bridge_tenant(request, db)
    return await voice_ai_service.complete_call(
        db, tenant_id, external_call_id, body.model_dump(exclude_unset=True),
    )


# ═══════════════════════════════════════════════════════════════
# Helper: tenant del bridge
# ═══════════════════════════════════════════════════════════════

async def _bridge_tenant(request: Request, db: AsyncSession) -> int:
    """Resuelve el tenant del bridge desde el CallRecord.

    El call-bridge de F2 envía `external_call_id` (Uniqueid de Asterisk,
    UNIQUE global — R8): el tenant se deriva del registro, nunca de headers
    del bridge (X-Tenant-ID es del staff). 404 si la llamada no existe.
    """
    from sqlalchemy import select

    from app.adapters.db.models.calls import CallRecord
    external_call_id = str(request.path_params.get("external_call_id", ""))
    rec = (await db.execute(
        select(CallRecord).where(CallRecord.external_call_id == external_call_id)
    )).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    return int(rec.tenant_id)
