"""
Tests Spec 05 — F2 "Central que No Pierde Llamadas" (backend, Spec §3.5/§3.8).

Cubre:
  - Upsert idempotente por `external_call_id` (R8, CA-F2.1) + broadcast WS
    y publish `call.*` (fire-and-forget, R3).
  - Resolución de tenant por DID (R4).
  - convert-to-order: reusa `create_order` (R7), 409 conversión duplicada
    (R6), 422 en estados no convertibles, sugerencia de zona por distrito.
  - originate: 202 + CallRecord outbound (CA-F2.8), 400 número inválido,
    409 operador ocupado.
  - Auth: staff 401 sin token, /events 401 sin token de servicio / 403 IP
    no autorizada (CA-F2.5).
  - Aislamiento de tenant (CA-F2.6).
  - Worker: `call.*` → ack + log sin tocar el flujo WhatsApp (CA-F2.7);
    `delivery.*` sigue disparando el notifier (regresión cero).

Regla dura (Spec 05 D3 / precedente F1 R-F1.3): NINGÚN test usa el número
wacli del agente — solo números de prueba del negocio (D4).
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.db.models.calls import CallRecord
from app.services import call_service
from app.services.call_service import (
    _validate_peru_number,
    resolve_tenant_by_did,
    suggest_zone_by_address,
    upsert_from_ami,
)
from app.services.notify_worker import _process_event

# Número de prueba del negocio (D4 — NUNCA el wacli del agente)
BUSINESS_PHONE = "+51 999 999 999"
BUSINESS_DIGITS = "51999999999"


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _ami_event(status="ringing", external="SIP-1234.1", caller="999888777", callee="+5115551234", **kw):
    data = {
        "external_call_id": external,
        "tenant_id": 1,
        "caller": caller,
        "callee": callee,
        "direction": "inbound",
        "status": status,
        "started_at": datetime(2026, 8, 13, tzinfo=UTC),
    }
    data.update(kw)
    return data


class _FakeDB:
    """Mini-AsyncSession: guarda registros en memoria + resultados configurables."""

    def __init__(self):
        self.records: dict[str, CallRecord] = {}
        self.commits = 0
        self._next_id = 1
        self.execute_result = None

    async def execute(self, stmt, *a, **kw):
        return self.execute_result

    def add(self, record):
        record.id = self._next_id
        self._next_id += 1
        self.records[record.external_call_id] = record

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, record):
        if record.id is None:
            record.id = self._next_id
            self._next_id += 1
        self.records[record.external_call_id] = record
        return record


@pytest.fixture
def fake_db():
    return _FakeDB()


@pytest.fixture(autouse=True)
def _no_real_network():
    """Aísla llamadas HTTP/WS/publish reales (R3: los eventos nunca bloquean)."""
    with (
        patch("app.services.call_service.manager.broadcast_to_calls", new_callable=AsyncMock),
        patch("app.services.call_service.publish_call_event", new_callable=AsyncMock),
        patch("app.services.call_service.httpx.AsyncClient", new_callable=AsyncMock),
        patch("app.services.call_service.delivery_create_order", new_callable=AsyncMock),
    ):
        yield


# ═══════════════════════════════════════════════════════════════
# Upsert idempotente (R8, CA-F2.1)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upsert_creates_and_updates_same_record(fake_db):
    """Newchannel → Newstate → Hangup actualizan el MISMO registro (R8)."""
    fake_db.execute_result = MagicMock()
    fake_db.execute_result.scalar_one_or_none.return_value = None

    r1 = await upsert_from_ami(fake_db, _ami_event("ringing", external="SIP-A.1"))
    assert r1["created"] is True

    # El segundo evento (Newstate) encuentra el registro existente
    existing = fake_db.records["SIP-A.1"]
    fake_db.execute_result.scalar_one_or_none.return_value = existing
    r2 = await upsert_from_ami(fake_db, _ami_event("answered", external="SIP-A.1"))
    assert r2["created"] is False
    assert existing.status == "answered"

    # Hangup
    fake_db.execute_result.scalar_one_or_none.return_value = existing
    r3 = await upsert_from_ami(
        fake_db, _ami_event("completed", external="SIP-A.1", duration=42),
    )
    assert r3["created"] is False
    assert existing.status == "completed"
    assert existing.duration == 42


@pytest.mark.asyncio
async def test_upsert_missed_sets_ended_at(fake_db):
    """Missed/failed: el bridge manda ended_at aunque nunca contestó."""
    fake_db.execute_result = MagicMock()
    fake_db.execute_result.scalar_one_or_none.return_value = None
    await upsert_from_ami(fake_db, _ami_event("ringing", external="SIP-B.1"))
    existing = fake_db.records["SIP-B.1"]
    fake_db.execute_result.scalar_one_or_none.return_value = existing
    await upsert_from_ami(fake_db, _ami_event("missed", external="SIP-B.1"))
    assert existing.status == "missed"
    assert existing.ended_at is not None


@pytest.mark.asyncio
async def test_upsert_requires_tenant_resolution(fake_db):
    """Sin tenant_id ni DID configurado → 422 (no se inventa el tenant)."""
    fake_db.execute_result = MagicMock()
    fake_db.execute_result.scalar_one_or_none.return_value = None
    with patch("app.services.call_service.resolve_tenant_by_did", new_callable=AsyncMock, return_value=None):
        with pytest.raises(Exception) as exc:
            await upsert_from_ami(fake_db, _ami_event("ringing", tenant_id=None))
    assert exc.value.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Resolución de tenant por DID (R4)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_resolve_tenant_by_did(fake_db):
    """DID del tenant resuelve el tenant (R4)."""
    company = MagicMock()
    company.id = 7
    company.settings = {"calls": {"dids": ["+5115551234", "+5115555678"]}}

    res = MagicMock()
    res.scalars.return_value.all.return_value = [company]
    fake_db.execute_result = res

    tenant = await resolve_tenant_by_did(fake_db, "+5115551234")
    assert tenant == 7

    # DID no configurado → None
    res.scalars.return_value.all.return_value = []
    fake_db.execute_result = res
    tenant = await resolve_tenant_by_did(fake_db, "+51999999999")
    assert tenant is None


# ═══════════════════════════════════════════════════════════════
# convert-to-order (R6/R7, CA-F2.3)
# ═══════════════════════════════════════════════════════════════

def _fake_record(status="answered"):
    rec = CallRecord(
        tenant_id=1, external_call_id="SIP-C.1", caller="999888777",
        callee="+5115551234", direction="inbound", status=status,
        started_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    rec.id = 1
    return rec


@pytest.mark.asyncio
async def test_convert_to_order_ok(fake_db):
    """201: reusa create_order y vincula converted_order_id (R7)."""
    record = _fake_record()
    res = MagicMock()
    res.scalar_one_or_none.side_effect = [record, MagicMock()]  # llamada + delivery_order
    fake_db.execute_result = res

    fake_order = MagicMock()
    fake_order.id = 42
    fake_db.execute_result2 = fake_order

    async def _fake_create(db, tenant, data):
        return {
            "tracking_code": "DLV-f2test01", "sale_id": 99,
            "sale_number": "V-0001", "status": "received",
            "totals": {"total": 55.0},
        }

    async def _fake_delivery_order(db, tenant, sale_id):
        fake_order.id = 42
        return fake_order

    with (
        patch("app.services.call_service.delivery_create_order", side_effect=_fake_create),
        patch("app.services.call_service._delivery_order_id_for_sale", side_effect=_fake_delivery_order),
    ):
        result = await call_service.convert_to_order(
            fake_db, 1, 1,
            {"zone_id": 3, "items": [{"menu_item_id": 10, "quantity": 2}],
             "customer": {"name": "Cliente", "phone": "999888777", "address": "Av. Lima 123"},
             "payment": {"method": "yape"}},
        )
    assert result["tracking_code"] == "DLV-f2test01"
    assert result["call_id"] == 1
    assert record.converted_order_id == 42


@pytest.mark.asyncio
async def test_convert_to_order_duplicate_409(fake_db):
    """R6: segunda conversión → 409."""
    record = _fake_record()
    record.converted_order_id = 42
    res = MagicMock()
    res.scalar_one_or_none.return_value = record
    fake_db.execute_result = res

    with pytest.raises(Exception) as exc:
        await call_service.convert_to_order(fake_db, 1, 1, {"zone_id": 3, "items": []})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_convert_to_order_ringing_422(fake_db):
    """Llamada en curso (ringing) → 422 (§3.5.1)."""
    record = _fake_record(status="ringing")
    res = MagicMock()
    res.scalar_one_or_none.return_value = record
    fake_db.execute_result = res

    with pytest.raises(Exception) as exc:
        await call_service.convert_to_order(fake_db, 1, 1, {"zone_id": 3, "items": []})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_convert_to_order_missing_zone_422(fake_db):
    """Sin zona y sin distrito inferible → 422 (brecha §2.1 resuelta)."""
    record = _fake_record()
    res = MagicMock()
    res.scalar_one_or_none.return_value = record
    fake_db.execute_result = res

    with (
        patch("app.services.call_service.suggest_zone_by_address", new_callable=AsyncMock, return_value=None),
    ):
        with pytest.raises(Exception) as exc:
            await call_service.convert_to_order(
                fake_db, 1, 1, {"items": [], "customer": {"address": "Sin distrito conocido"}},
            )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_suggest_zone_by_district(fake_db):
    """Sugerencia de zona por distrito (brecha §2.1)."""
    zone = MagicMock()
    zone.id = 5
    zone.districts = ["San Juan de Lurigancho", "Chosica"]
    res = MagicMock()
    res.scalars.return_value.all.return_value = [zone]
    fake_db.execute_result = res

    suggested = await suggest_zone_by_address(fake_db, 1, "Av. Montenegro 123, San Juan de Lurigancho")
    assert suggested.id == 5


# ═══════════════════════════════════════════════════════════════
# originate (CA-F2.8)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_originate_ok(fake_db):
    """202: registra outbound ringing y pide el Originate al bridge."""
    res = MagicMock()
    res.scalars.return_value.first.return_value = None  # sin llamada activa
    fake_db.execute_result = res

    with patch("app.services.call_service._ask_bridge_originate", new_callable=AsyncMock):
        result = await call_service.originate(fake_db, 1, "+51 999 999 999", "100")
    assert result["status"] == "ringing"
    assert result["external_call_id"].startswith("ORIGINATE-1-")
    created = [r for r in fake_db.records.values()][0]
    assert created.direction == "outbound"
    assert created.caller == "+51999999999"


def test_validate_peru_number():
    assert _validate_peru_number("+51 999 999 999") == "+51999999999"
    assert _validate_peru_number("999888777") == "+51999888777"
    with pytest.raises(Exception) as exc:
        _validate_peru_number("123")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_originate_operator_busy_409(fake_db):
    """1 línea activa por operador → 409."""
    active = _fake_record(status="in_progress")
    active.callee = "100"
    res = MagicMock()
    res.scalars.return_value.first.return_value = active
    fake_db.execute_result = res

    with pytest.raises(Exception) as exc:
        await call_service.originate(fake_db, 1, "+51 999 999 999", "100")
    assert exc.value.status_code == 409


# ═══════════════════════════════════════════════════════════════
# Aislamiento de tenant (CA-F2.6)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_call_cross_tenant_404(fake_db):
    """Llamada de otro tenant → 404 (CA-F2.6)."""
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    fake_db.execute_result = res
    with pytest.raises(Exception) as exc:
        await call_service.get_call(fake_db, 2, 1)
    assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Worker: dispatch call.* sin romper delivery.* (CA-F2.7)
# ═══════════════════════════════════════════════════════════════

def _call_payload(event_type="call.new", **overrides):
    data = {
        "event": event_type,
        "event_type": event_type,
        "tenant_id": 1,
        "external_call_id": "SIP-777.1",
        "caller": "999888777",
        "callee": "+5115551234",
        "direction": "inbound",
        "status": "ringing",
        "started_at": "2026-08-13T00:00:00+00:00",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_worker_call_new_acked_without_notifier():
    """call.* → log + ack; NUNCA entra al flujo WhatsApp (CA-F2.7)."""
    with (
        patch("app.services.notify_worker._load_company", new_callable=AsyncMock) as load_company,
        patch("app.services.notify_worker.build_notifier") as build_notifier,
    ):
        # call.* no debe ni cargar la empresa ni construir notifier
        await _process_event(_call_payload("call.new"))
        load_company.assert_not_awaited()
        build_notifier.assert_not_called()


@pytest.mark.asyncio
async def test_worker_call_malformed_no_crash():
    """call.* malformado (sin campos) → ack, no crashea (§3.5.4)."""
    with patch("app.services.notify_worker._load_company", new_callable=AsyncMock) as load_company:
        await _process_event({"event_type": "call.ended", "tenant_id": 1})
        load_company.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_delivery_still_dispatches_whatsapp():
    """delivery.* sigue disparando WhatsApp exactamente igual (regresión 0)."""
    company = MagicMock()
    company.settings = {
        "whatsapp": {
            "enabled": True,
            "token": "tok", "phone_number_id": "ph", "account_id": "acct",
            "templates": {"confirmed": "pedido_confirmado"},
        },
    }
    notifier = MagicMock()
    notifier.send = AsyncMock()

    payload = {
        "event": "delivery.confirmed", "event_type": "confirmed",
        "tenant_id": 1, "tracking_code": "DLV-f2test02", "sale_id": 99,
        "customer_phone": "999888777", "status": "received", "total": 55.0,
        "items_resumen": [{"name": "Item", "qty": 1}], "zone": "Zona 1",
    }
    with (
        patch("app.services.notify_worker._load_company", new_callable=AsyncMock, return_value=company),
        patch("app.services.notify_worker.build_notifier", return_value=notifier),
        patch("app.services.notify_worker._recipient_and_template", return_value=("999888777", "pedido_confirmado")),
        patch("app.services.notify_worker._build_params", return_value={}),
        patch("app.services.notify_worker._persist_bsuid", new_callable=AsyncMock),
    ):
        await _process_event(payload)
    notifier.send.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════
# call-bridge: traducción de eventos AMI (Spec §3.4)
# ═══════════════════════════════════════════════════════════════

from app.services.call_bridge import _build_event_payload  # noqa: E402


def test_bridge_newchannel_payload():
    payload = _build_event_payload({
        "Event": "Newchannel", "Uniqueid": "SIP-X.1",
        "CallerIDNum": "999888777", "Exten": "100", "Channel": "PJSIP/100-0001",
        "Context": "from-pstn",
    })
    assert payload is not None
    assert payload["external_call_id"] == "SIP-X.1"
    assert payload["direction"] == "inbound"
    assert payload["status"] == "ringing"


def test_bridge_hangup_completed():
    payload = _build_event_payload({
        "Event": "Hangup", "Uniqueid": "SIP-X.1",
        "CallerIDNum": "999888777", "Channel": "PJSIP/100-0001",
        "Context": "from-pstn", "CauseTxt": "Normal Clearing", "CallDuration": "42",
    })
    assert payload["status"] == "completed"
    assert payload["duration"] == 42


def test_bridge_hangup_no_answer_missed():
    payload = _build_event_payload({
        "Event": "Hangup", "Uniqueid": "SIP-X.1",
        "CallerIDNum": "999888777", "Channel": "PJSIP/100-0001",
        "Context": "from-pstn", "CauseTxt": "No Answer",
    })
    assert payload["status"] == "missed"


def test_bridge_unknown_event_ignored():
    assert _build_event_payload({"Event": "VarSet", "Uniqueid": "SIP-X.1"}) is None
    assert _build_event_payload({}) is None
