"""
📞 Schemas — Central Telefónica (Spec 05 F2, §3.5).

Contratos de los endpoints:
  - Staff (JWT + X-Tenant-ID): GET /calls, GET /calls/{id},
    POST /calls/{id}/convert-to-order, POST /calls/originate.
  - Servicio interno (token de servicio + allowlist IP del call-bridge):
    POST /calls/events (§3.5.2).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Estados/direcciones permitidos (espejo del CHECK en BD — Spec 05 §3.2)
CALL_STATUSES = ("ringing", "in_progress", "answered", "missed", "completed", "failed")
CALL_DIRECTIONS = ("inbound", "outbound")


# ═══════════════════════════════════════════════════════════════
# Listado / detalle (staff)
# ═══════════════════════════════════════════════════════════════

class CallRecordOut(BaseModel):
    """Detalle de un CallRecord (§3.5.1)."""

    id: int
    external_call_id: str
    caller: str
    callee: str
    direction: str
    status: str
    started_at: datetime
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: int = 0
    recording_path: Optional[str] = None
    converted_order_id: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CallListResponse(BaseModel):
    items: list[CallRecordOut] = Field(default_factory=list)
    total: int


# ═══════════════════════════════════════════════════════════════
# Conversión llamada → pedido de delivery (§3.5.1, R6/R7)
# ═══════════════════════════════════════════════════════════════

class ConvertOrderItem(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1)
    modifiers: list[dict] = Field(default_factory=list)


class ConvertOrderCustomer(BaseModel):
    name: Optional[str] = None
    # La llamada ya trae `caller` como phone default si el operador no lo captura
    phone: Optional[str] = None
    # Requerida: si el cliente no tiene dirección, el operador la captura (§3.5.1)
    address: str = Field(min_length=5)


class ConvertOrderPayment(BaseModel):
    method: str  # yape | plin | cash
    reference: Optional[str] = None


class ConvertToOrderRequest(BaseModel):
    """POST /api/v1/calls/{id}/convert-to-order — Request.

    `zone_id` opcional en el contrato backend: el frontend lo selecciona
    (spec), y si viene null el servicio intenta sugerir la zona por distrito
    de la dirección (helper `suggest_zone_by_address`, §3.5.1); sin zona al
    final → 422 (brecha Fase R §2.1).
    """

    zone_id: Optional[int] = None
    items: list[ConvertOrderItem] = Field(min_length=1)
    customer: ConvertOrderCustomer
    payment: ConvertOrderPayment
    notes: Optional[str] = None


class ConvertToOrderResponse(BaseModel):
    """POST /api/v1/calls/{id}/convert-to-order — 201 (§3.5.1)."""

    tracking_code: str
    sale_id: int
    sale_number: str
    status: str = "received"
    totals: dict = Field(default_factory=dict)
    call_id: int


# ═══════════════════════════════════════════════════════════════
# Click-to-call (§3.5.1, outbound)
# ═══════════════════════════════════════════════════════════════

class OriginateRequest(BaseModel):
    target: str = Field(..., min_length=5, max_length=20, description="Número a llamar (E.164/Perú)")
    extension: str = Field(..., min_length=1, max_length=10, description="Extensión del operador")


class OriginateResponse(BaseModel):
    """202: el CallRecord outbound nace en estado ringing (§3.5.1)."""

    external_call_id: str
    status: str = "ringing"


# ═══════════════════════════════════════════════════════════════
# Evento interno call-bridge → backend (§3.5.2, token de servicio)
# ═══════════════════════════════════════════════════════════════

class CallEventIn(BaseModel):
    """POST /api/v1/calls/events — payload AMI del call-bridge.

    Upsert por `external_call_id` (R8). `tenant_id` opcional: si no viene,
    el servicio lo resuelve por DID (R4, MVP 1 tenant).
    """

    external_call_id: str = Field(..., min_length=1, max_length=64)
    tenant_id: Optional[int] = None
    caller: str = Field(..., max_length=32)
    callee: str = Field(..., max_length=32)
    direction: str = Field(..., pattern=r"^(inbound|outbound)$")
    status: str = Field(..., pattern=r"^(ringing|in_progress|answered|missed|completed|failed)$")
    started_at: datetime
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[int] = Field(None, ge=0)
    recording_path: Optional[str] = None
    metadata: Optional[dict] = None

    @field_validator("caller", "callee", mode="before")
    @classmethod
    def _coerce_str(cls, v):
        return str(v) if v is not None else v


class CallEventOut(BaseModel):
    """200: `created` indica si el evento insertó (True) o actualizó (False)."""

    id: int
    created: bool
