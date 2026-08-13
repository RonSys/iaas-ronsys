"""
📞 CallService — Central Telefónica (Spec 05 F2, §3.2/§3.4/§3.5).

Responsabilidades (P2 + P4 del plan F2):
  - `upsert_from_ami`: eventos del call-bridge (AMI: Newchannel/Newstate/
    Hangup) → upsert idempotente por `external_call_id` (R8, Uniqueid de
    Asterisk) → broadcast WS `/ws/calls/{tenant}` + publish `call.*` (R3).
  - Resolución DID→tenant por `companies.settings.calls.dids` (R4, D-03).
  - `convert_to_order`: REUSA `DeliveryService.create_order` (R7) — Sale →
    kárdex → asiento → KitchenOrder → DeliveryOrder (DLV-); 1 sola
    conversión por llamada (R6 → 409); 422 si la llamada sigue en curso.
  - `suggest_zone_by_address`: match por distrito sobre `delivery_zones.districts`
    (brecha Fase R §2.1 — la zona se sugiere si el panel no la manda).
  - `originate`: click-to-call — valida número, crea el CallRecord outbound
    (ringing) e integra con el call-bridge vía HTTP interno (fire-and-forget
    con fallback logueado; contrato documentado abajo).

La llamada/pedido NUNCA dependen de RabbitMQ ni del call-bridge (R3).
"""

import logging
import re
import time as _time
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import Company
from app.adapters.db.models.calls import ACTIVE_STATUSES, CallRecord
from app.adapters.db.models.delivery import DeliveryZone
from app.config import settings
from app.core.ws_manager import manager
from app.schemas import CallSettings
from app.services.delivery_service import create_order as delivery_create_order
from app.services.notify_events import publish_call_event

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


# ═══════════════════════════════════════════════════════════════
# CallSettings (patrón D-03) + resolución DID→tenant (R4)
# ═══════════════════════════════════════════════════════════════

def call_settings_from_company(company: Company | None) -> CallSettings:
    """Lee `companies.settings.calls` con defaults (patrón D-03).

    Igual que `_whatsapp_from_raw` del worker: lo persistido gana, los
    campos ausentes toman el default del schema (CallSettings).
    """
    raw = (company.settings or {}) if company else {}
    raw = raw if isinstance(raw, dict) else {}
    calls = raw.get("calls", {}) if isinstance(raw.get("calls"), dict) else {}
    return CallSettings(**calls)


async def _company(db: AsyncSession, tenant_id: int) -> Company:
    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


def _normalize_did(did: str) -> str:
    """Normaliza un DID para match: solo dígitos (+51 1 555 1234 → 5115551234)."""
    return "".join(ch for ch in str(did) if ch.isdigit())


async def resolve_tenant_by_did(db: AsyncSession, did: str) -> int | None:
    """R4: resuelve el tenant cuyo `CallSettings.dids` contiene el DID.

    Escanea `companies.settings.calls.dids` (patrón D-03) comparando solo
    dígitos (el bridge puede reportar el DID con formato distinto al
    guardado). Retorna None si ningún tenant lo tiene configurado (el
    evento se registra igual con tenant_id del payload cuando viene).
    """
    target = _normalize_did(did)
    if not target:
        return None
    companies = (await db.execute(select(Company))).scalars().all()
    for company in companies:
        cs = call_settings_from_company(company)
        if any(_normalize_did(d) == target for d in (cs.dids or [])):
            return int(company.id)
    return None


# ═══════════════════════════════════════════════════════════════
# Upsert de eventos AMI (R8) + broadcast WS + publish call.*
# ═══════════════════════════════════════════════════════════════

async def _get_by_external(
    db: AsyncSession, external_call_id: str,
) -> CallRecord | None:
    return (await db.execute(
        select(CallRecord).where(CallRecord.external_call_id == external_call_id)
    )).scalar_one_or_none()


async def upsert_from_ami(db: AsyncSession, data: dict) -> dict:
    """Upsert idempotente por `external_call_id` (R8, CA-F2.1).

    El call-bridge es re-arrancable: los eventos AMI (Newchannel/Newstate/
    Hangup) actualizan el MISMO registro. `created=True` en la primera
    inserción; `False` en actualizaciones. La UNIQUE constraint es el
    backstop ante concurrencia (un segundo insert fallaría y se re-lee).

    Efectos secundarios (Spec 05 §3.5.2/§3.5.3):
      - broadcast WS /ws/calls/{tenant_id}: call.incoming / call.answered /
        call.ended / call.recording_ready (según transición de estado).
      - publish `call.new` / `call.ended` / `call.recording_ready`
        (fire-and-forget, cola iaas-tasks).
    """
    external_call_id = str(data["external_call_id"])
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        # R4: resolver por DID cuando el payload no trae tenant (inbound)
        tenant_id = await resolve_tenant_by_did(db, data.get("callee") or data.get("caller") or "")
        if tenant_id is None:
            raise HTTPException(
                status_code=422,
                detail="No se pudo resolver tenant: payload sin tenant_id y DID no configurado",
            )
    tenant_id = int(tenant_id)

    record = await _get_by_external(db, external_call_id)
    created = record is None
    if record is None:
        record = CallRecord(
            tenant_id=tenant_id,
            external_call_id=external_call_id,
            caller=str(data["caller"]),
            callee=str(data["callee"]),
            direction=data["direction"],
            status=data["status"],
            started_at=data["started_at"],
            answered_at=data.get("answered_at"),
            ended_at=data.get("ended_at"),
            duration=int(data.get("duration") or 0),
            recording_path=data.get("recording_path"),
            metadata_=data.get("metadata"),
        )
        db.add(record)
    else:
        prev_status = record.status
        record.status = data["status"]
        if data.get("answered_at") is not None:
            record.answered_at = data["answered_at"]
        if data.get("ended_at") is not None:
            record.ended_at = data["ended_at"]
        if data.get("duration") is not None:
            record.duration = int(data["duration"])
        if data.get("recording_path") is not None:
            record.recording_path = data["recording_path"]
        if data.get("metadata") is not None:
            meta = dict(record.metadata_ or {})
            meta.update(data["metadata"])
            record.metadata_ = meta
        # Missed/failed: el bridge manda ended_at aunque nunca contestó
        if record.status in ("missed", "failed") and record.ended_at is None:
            record.ended_at = data.get("ended_at") or _now()

    await db.flush()
    await db.commit()
    await db.refresh(record)

    # ── Broadcast WS (Spec 05 §3.5.3) ──────────────────────
    event_map = {
        "ringing": ("call.incoming", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "callee": record.callee,
            "started_at": record.started_at.isoformat() if record.started_at else None,
        }),
        "in_progress": ("call.incoming", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "callee": record.callee,
            "started_at": record.started_at.isoformat() if record.started_at else None,
        }),
        "answered": ("call.answered", {
            "external_call_id": record.external_call_id,
            "caller": record.caller,
            "answered_at": record.answered_at.isoformat() if record.answered_at else None,
        }),
        "missed": ("call.ended", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "duration": record.duration,
            "status": record.status,
            "hangup_cause": (record.metadata_ or {}).get("hangup_cause"),
        }),
        "completed": ("call.ended", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "duration": record.duration,
            "status": record.status,
            "hangup_cause": (record.metadata_ or {}).get("hangup_cause"),
        }),
        "failed": ("call.ended", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "duration": record.duration,
            "status": record.status,
            "hangup_cause": (record.metadata_ or {}).get("hangup_cause"),
        }),
    }
    ws_event, ws_payload = event_map.get(
        record.status, ("call.incoming", {"external_call_id": record.external_call_id}),
    )
    try:
        await manager.broadcast_to_calls(tenant_id, ws_event, ws_payload)
    except Exception:  # noqa: BLE001 — el WS nunca rompe el upsert
        logger.warning("broadcast WS call.%s falló (tenant %s)", ws_event, tenant_id, exc_info=True)

    # recording_path recién llegado → evento dedicado (CA-F2.2)
    if record.recording_path:
        try:
            await manager.broadcast_to_calls(tenant_id, "call.recording_ready", {
                "external_call_id": record.external_call_id,
                "recording_path": record.recording_path,
            })
        except Exception:  # noqa: BLE001
            logger.warning("broadcast call.recording_ready falló (tenant %s)", tenant_id, exc_info=True)

    # ── Publish call.* (R3 — fire-and-forget, nunca bloquea) ──
    await _publish_for_status(record)

    return {"id": record.id, "created": created}


async def _publish_for_status(record: CallRecord) -> None:
    """Publica `call.new` / `call.ended` / `call.recording_ready` (Spec §3.4)."""
    common = {
        "tenant_id": record.tenant_id,
        "external_call_id": record.external_call_id,
        "caller": record.caller,
        "callee": record.callee,
        "direction": record.direction,
        "status": record.status,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "answered_at": record.answered_at.isoformat() if record.answered_at else None,
        "ended_at": record.ended_at.isoformat() if record.ended_at else None,
        "duration": record.duration,
        "hangup_cause": (record.metadata_ or {}).get("hangup_cause"),
    }
    try:
        if record.status in ("ringing", "in_progress", "answered"):
            await publish_call_event("new", **common)
        if record.status in ("missed", "completed", "failed"):
            await publish_call_event("ended", **common)
        if record.recording_path:
            await publish_call_event(
                "recording_ready", recording_path=record.recording_path, **common,
            )
    except Exception:  # noqa: BLE001 — R3: el evento nunca rompe la llamada
        logger.warning(
            "publish call.* falló (external=%s)", record.external_call_id, exc_info=True,
        )


# ═══════════════════════════════════════════════════════════════
# Listado / detalle (staff, tenant-scoped — R4/CA-F2.6)
# ═══════════════════════════════════════════════════════════════

def _call_out(record: CallRecord) -> dict:
    return {
        "id": record.id,
        "external_call_id": record.external_call_id,
        "caller": record.caller,
        "callee": record.callee,
        "direction": record.direction,
        "status": record.status,
        "started_at": record.started_at,
        "answered_at": record.answered_at,
        "ended_at": record.ended_at,
        "duration": record.duration,
        "recording_path": record.recording_path,
        "converted_order_id": record.converted_order_id,
        "metadata": record.metadata_,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def list_calls(
    db: AsyncSession, tenant_id: int,
    status: str | None = None,
    direction: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50, offset: int = 0,
) -> dict:
    """GET /api/v1/calls — SIEMPRE filtrado por tenant (R4, CA-F2.6)."""
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    filters = [CallRecord.tenant_id == tenant_id]
    if status:
        filters.append(CallRecord.status == status)
    if direction:
        filters.append(CallRecord.direction == direction)
    if date_from:
        filters.append(CallRecord.started_at >= date_from)
    if date_to:
        filters.append(CallRecord.started_at <= date_to)

    total = (await db.execute(
        select(func.count(CallRecord.id)).where(*filters)
    )).scalar() or 0

    records = (await db.execute(
        select(CallRecord).where(*filters)
        .order_by(CallRecord.started_at.desc())
        .limit(limit).offset(offset)
    )).scalars().all()

    return {"items": [_call_out(r) for r in records], "total": int(total)}


async def get_call(db: AsyncSession, tenant_id: int, call_id: int) -> dict:
    """GET /api/v1/calls/{id} — 404 si no existe o es cross-tenant (CA-F2.6)."""
    record = (await db.execute(
        select(CallRecord).where(
            CallRecord.id == call_id,
            CallRecord.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    return _call_out(record)


# ═══════════════════════════════════════════════════════════════
# Conversión llamada → pedido (R6/R7, §3.5.1)
# ═══════════════════════════════════════════════════════════════

async def suggest_zone_by_address(
    db: AsyncSession, tenant_id: int, address: str,
) -> DeliveryZone | None:
    """Sugiere la zona de delivery por distrito de la dirección.

    Match case-insensitive sobre `delivery_zones.districts` (jsonb list):
    el distrito es substring de la dirección o la dirección lo contiene
    (ej. "Av. Montenegro 123, SJL" → distrito "San Juan de Lurigancho" no
    matchea "SJL", pero el operador captura la dirección completa en el
    panel — el match es best-effort, la zona SIEMPRE es editable).
    """
    address = (address or "").strip().lower()
    if not address:
        return None
    zones = (await db.execute(
        select(DeliveryZone).where(
            DeliveryZone.tenant_id == tenant_id,
            DeliveryZone.active.is_(True),
        )
    )).scalars().all()
    best: DeliveryZone | None = None
    best_len = 0
    for zone in zones:
        for district in (zone.districts or []):
            d = str(district).strip().lower()
            if not d:
                continue
            if d in address or address in d:
                # Preferir el distrito más específico (mayor longitud)
                if len(d) > best_len:
                    best, best_len = zone, len(d)
    return best


async def convert_to_order(
    db: AsyncSession, tenant_id: int, call_id: int, data: dict,
) -> dict:
    """POST /api/v1/calls/{id}/convert-to-order (§3.5.1, R6/R7).

    404 llamada inexistente/cross-tenant · 422 si sigue en curso (ringing/
    in_progress/missed/failed) o sin zona · 409 conversión duplicada.
    201 reusa `DeliveryService.create_order` (Sale → kárdex → asiento →
    KitchenOrder → DeliveryOrder DLV-) y vincula `converted_order_id`.
    """
    record = (await db.execute(
        select(CallRecord).where(
            CallRecord.id == call_id,
            CallRecord.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")

    # R6: 1 sola conversión por llamada → 409
    if record.converted_order_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"La llamada ya fue convertida (delivery_orders id {record.converted_order_id})",
        )

    # La llamada debe estar atendida o terminada correctamente (§3.5.1):
    # 422 si sigue en curso (ringing/in_progress) o no fue atendida (missed/failed).
    if record.status not in ("answered", "completed"):
        raise HTTPException(
            status_code=422,
            detail=f"La llamada está en estado '{record.status}' — solo se convierte si está "
                   "answered o completed",
        )

    customer = dict(data.get("customer") or {})
    # Default: el número de la llamada como teléfono del cliente (§3.5.1)
    if not customer.get("phone"):
        customer["phone"] = record.caller

    # Zona: explícita (validada por create_order) o sugerida por distrito
    zone_id = data.get("zone_id")
    if not zone_id:
        suggested = await suggest_zone_by_address(
            db, tenant_id, customer.get("address") or "",
        )
        if suggested is None:
            raise HTTPException(
                status_code=422,
                detail="Se requiere zona de delivery (no se pudo inferir del distrito de la dirección)",
            )
        zone_id = suggested.id

    order_data = {
        "zone_id": int(zone_id),
        "items": data.get("items") or [],
        "customer": customer,
        "payment": data.get("payment") or {},
        "notes": data.get("notes"),
    }
    # R7: REUSA el motor de ventas existente (validaciones de ítems, promo,
    # min_order, pago yape/plin/cash, Sale → kárdex → asiento → cocina → DLV-).
    result = await delivery_create_order(db, tenant_id, order_data)

    # Vincular la DeliveryOrder creada (sale_id → delivery_orders)
    delivery_order = await _delivery_order_id_for_sale(db, tenant_id, result["sale_id"])
    if delivery_order is None:
        raise HTTPException(status_code=500, detail="No se pudo vincular el pedido a la llamada")
    record.converted_order_id = delivery_order.id
    await db.flush()
    await db.commit()
    await db.refresh(record)

    # Broadcast WS panel en vivo: call.converted (§3.5.3)
    try:
        await manager.broadcast_to_calls(tenant_id, "call.converted", {
            "external_call_id": record.external_call_id,
            "tracking_code": result["tracking_code"],
            "sale_id": result["sale_id"],
        })
    except Exception:  # noqa: BLE001 — el WS nunca rompe la conversión
        logger.warning("broadcast call.converted falló (tenant %s)", tenant_id, exc_info=True)

    return {
        "tracking_code": result["tracking_code"],
        "sale_id": result["sale_id"],
        "sale_number": result.get("sale_number"),
        "status": result.get("status", "received"),
        "totals": result.get("totals", {}),
        "call_id": record.id,
    }


async def _delivery_order_id_for_sale(
    db: AsyncSession, tenant_id: int, sale_id: int,
) -> Any | None:
    """Resuelve la DeliveryOrder por sale_id (para vincular converted_order_id)."""
    from app.adapters.db.models.delivery import DeliveryOrder
    return (await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.sale_id == sale_id,
            DeliveryOrder.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════
# Click-to-call / Originate (§3.5.1, CA-F2.8)
# ═══════════════════════════════════════════════════════════════

# Perú: móvil 9 dígitos (9XXXXXXXX) o fijo 7-8 dígitos; E.164 = +51 + número.
_PERU_NUMBER_RE = re.compile(r"^(?:\+?51)?\s*(\d{7,9})$")


def _validate_peru_number(target: str) -> str:
    """Valida/normaliza un número peruano → E.164 (+51...). 400 si inválido."""
    raw = str(target or "").strip()
    match = _PERU_NUMBER_RE.match(raw.replace(" ", ""))
    if not match:
        raise HTTPException(
            status_code=400,
            detail=f"Número inválido '{target}' (formato esperado: +51 999 999 999)",
        )
    local = match.group(1)
    return f"+51{local}"


async def originate(
    db: AsyncSession, tenant_id: int, target: str, extension: str,
) -> dict:
    """POST /api/v1/calls/originate (§3.5.1, CA-F2.8).

    - 400 número inválido; 409 el operador (extensión) ya tiene una llamada
      activa (1 línea activa por operador).
    - Crea el CallRecord outbound (status=ringing, caller=destino,
      callee=extensión del operador — Spec 05 §3.2 nota de diseño).
    - Integra con el call-bridge vía HTTP interno (fire-and-forget): si el
      bridge no responde la llamada NO se pierde — el registro ya existe y
      el bridge re-intenta el Originate por `external_call_id` al arrancar
      (R8). 202 siempre.

    Contrato documentado con call-bridge (Punto de integración F2):
      POST {settings.call_bridge_url}/api/v1/bridge/originate
      Body: { "external_call_id": str, "tenant_id": int,
              "target": "+51999...", "extension": "100" }
      Respuesta esperada: 202 { "accepted": true } (ARI Originate en curso).
      Si el bridge aún no está desplegado → warning logueado, 202 igual.
    """
    e164 = _validate_peru_number(target)
    extension = str(extension or "").strip()

    # 1 línea activa por operador → 409
    active = (await db.execute(
        select(CallRecord).where(
            CallRecord.tenant_id == tenant_id,
            CallRecord.status.in_(ACTIVE_STATUSES),
            or_(CallRecord.callee == extension, CallRecord.caller == extension),
        )
    )).scalars().first()
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"La extensión {extension} ya tiene una llamada activa "
                   f"(external_call_id {active.external_call_id})",
        )

    external_call_id = f"ORIGINATE-{tenant_id}-{int(_time.time() * 1000)}"
    record = CallRecord(
        tenant_id=tenant_id,
        external_call_id=external_call_id,
        caller=e164,
        callee=extension,
        direction="outbound",
        status="ringing",
        started_at=_now(),
        metadata_={"origin": "click-to-call", "extension": extension, "originate": True},
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Broadcast WS: la saliente aparece en el panel en vivo (CA-F2.8)
    try:
        await manager.broadcast_to_calls(tenant_id, "call.incoming", {
            "external_call_id": record.external_call_id,
            "caller": record.caller, "callee": record.callee,
            "started_at": record.started_at.isoformat(),
        })
    except Exception:  # noqa: BLE001
        logger.warning("broadcast originate falló (tenant %s)", tenant_id, exc_info=True)

    # Publish call.new (R3 — fire-and-forget)
    await _publish_for_status(record)

    # Integración con call-bridge (best-effort, ver contrato arriba)
    await _ask_bridge_originate(record)

    return {"external_call_id": external_call_id, "status": "ringing"}


async def _ask_bridge_originate(record: CallRecord) -> None:
    """Pide el Originate ARI al call-bridge (HTTP interno, fallback logueado).

    El contrato (documentado en `originate`) es propiedad del subagente del
    bridge; aquí solo se dispara el POST y se loguea cualquier fallo — el
    202 ya fue decidido, la llamada registrada y el bridge puede re-intentar
    por `external_call_id` (R8: idempotencia por diseño).
    """
    if not settings.call_bridge_url:
        logger.info("call_bridge_url vacío — Originate queda solo registrado (external=%s)", record.external_call_id)
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.call_bridge_url.rstrip('/')}/api/v1/bridge/originate",
                json={
                    "external_call_id": record.external_call_id,
                    "tenant_id": record.tenant_id,
                    "target": record.caller,
                    "extension": record.callee,
                },
            )
            if resp.status_code >= 300:
                logger.warning(
                    "call-bridge respondió %s al Originate (external=%s): %s",
                    resp.status_code, record.external_call_id, resp.text[:200],
                )
            else:
                logger.info(
                    "Originate aceptado por call-bridge (external=%s)", record.external_call_id,
                )
    except Exception as exc:  # noqa: BLE001 — best-effort: nunca romper el 202
        logger.warning(
            "call-bridge no disponible para Originate (external=%s): %s",
            record.external_call_id, exc,
        )
