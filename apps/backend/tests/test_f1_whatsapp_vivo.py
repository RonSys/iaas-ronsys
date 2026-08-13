"""
Tests Spec 04 — F1 "WhatsApp en Vivo" (backend, Spec §3.5/§3.8).

Cubre los cambios backend de F1:
  - Campo `bsuid` en el payload de eventos (D3) sin romper el contrato §7.4.
  - Persistencia del BSUID en `delivery_orders.whatsapp_bsuid` por el worker
    (update ligero, fire-and-forget, solo si NULL — R-F1.6 / CA-F1.10).
  - `contact` en `PublicMenuResponse`: null sin config activa (CA-F1.14) y
    poblado con config activa (D5: wa.me + tel: + mensaje prefabricado).
  - El BSUID del pedido viaja en eventos de transición (update_status).

Regla dura R-F1.3: NINGÚN test usa ni referencia el número wacli del agente
(prohibido en settings/plantillas/enlaces/logs de F1) — solo números de
prueba del negocio (D4).
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

import pytest
from sqlalchemy.sql import Update

from app.schemas import CompanySettings
from app.schemas.delivery import PublicMenuResponse
from app.services.delivery_service import get_public_menu, update_status
from app.services.notify_events import build_delivery_event_payload
from app.services.notify_worker import _persist_bsuid, _process_event

# Número de prueba del negocio (D4 — NUNCA el wacli del agente, R-F1.3)
BUSINESS_PHONE = "+51 999 999 999"
BUSINESS_DIGITS = "51999999999"
MENSAJE_PREFABRICADO = "¡Hola! Quiero hacer un pedido por el menú. 🍽️"


def _payload(event_type="confirmed", **overrides):
    data = {
        "event": f"delivery.{event_type}",
        "event_type": event_type,
        "tenant_id": 1,
        "tracking_code": "DLV-f1test01",
        "sale_id": 99,
        "customer_phone": "999888777",
        "status": "received",
        "total": 55.0,
        "items_resumen": [{"name": "Item 10", "qty": 2}],
        "zone": "Zona 1",
        "timestamp": "2026-08-12T00:00:00+00:00",
    }
    data.update(overrides)
    return data


def _company(settings: dict | None):
    company = MagicMock()
    company.settings = settings
    company.id = 1
    return company


def _session_factory_patch(company, raise_on_enter=False):
    """Parchea get_session_factory → db AsyncMock que resuelve `company`."""
    db = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    res.scalar_one_or_none.return_value = company
    db.execute.return_value = res
    cm = MagicMock()
    if raise_on_enter:
        cm.__aenter__ = AsyncMock(side_effect=Exception("BD caída"))
    else:
        cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    return patch("app.services.notify_worker.get_session_factory", return_value=factory), db


def _httpx_client_patch():
    client = AsyncMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    client.post.return_value = resp
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.whatsapp_notifier.httpx.AsyncClient", return_value=cm), client


def _find_delivery_update(db) -> Update | None:
    """Busca en db.execute el UPDATE a delivery_orders (el de BSUID)."""
    for call in db.execute.call_args_list:
        stmt = call.args[0]
        if isinstance(stmt, Update) and getattr(stmt, "table", None) is not None:
            if stmt.table.name == "delivery_orders":
                return stmt
    return None


# ═══════════════════════════════════════════════════════════════
# D3 / CA-F1.10 — payload de eventos con bsuid (sin romper §7.4)
# ═══════════════════════════════════════════════════════════════

class TestPayloadConBsuid:
    def test_payload_incluye_bsuid_opcional(self):
        payload = build_delivery_event_payload(
            event_type="confirmed",
            tenant_id=1,
            tracking_code="DLV-abc",
            sale_id=99,
            customer_phone="999888777",
            status="received",
            total=55.0,
            items_resumen=[{"name": "X", "qty": 1}],
            zone="Zona 1",
        )
        # Contrato §7.4 intacto (Spec 03)
        assert payload["tenant_id"] == 1
        assert payload["tracking_code"] == "DLV-abc"
        assert payload["sale_id"] == 99
        assert payload["customer_phone"] == "999888777"
        assert payload["status"] == "received"
        assert payload["total"] == 55.0
        assert payload["items_resumen"] == [{"name": "X", "qty": 1}]
        assert payload["zone"] == "Zona 1"
        assert payload["timestamp"]
        # F1 (D3): bsuid opcional, presente aunque venga None
        assert "bsuid" in payload
        assert payload["bsuid"] is None

    def test_payload_con_bsuid(self):
        payload = build_delivery_event_payload(
            event_type="status_changed",
            tenant_id=1,
            tracking_code="DLV-abc",
            sale_id=99,
            customer_phone="999888777",
            status="preparing",
            bsuid="BSUID-2026-1234567890",
        )
        assert payload["bsuid"] == "BSUID-2026-1234567890"

    def test_schema_company_acepta_whatsapp_sin_cambios(self):
        # Regresión: CompanySettings sigue validando igual (D-03)
        cs = CompanySettings(whatsapp={
            "enabled": True, "business_phone": BUSINESS_PHONE,
        })
        assert cs.whatsapp.business_phone == BUSINESS_PHONE
        assert cs.whatsapp.enabled is True


# ═══════════════════════════════════════════════════════════════
# D3 / CA-F1.10 — worker persiste el BSUID (fire-and-forget)
# ═══════════════════════════════════════════════════════════════

class TestWorkerPersisteBsuid:
    @pytest.mark.asyncio
    async def test_persiste_bsuid_cuando_payload_lo_trae(self):
        factory_patch, db = _session_factory_patch(_company(None))
        with factory_patch:
            await _persist_bsuid(_payload("confirmed", bsuid="BSUID-abc123"))

        stmt = _find_delivery_update(db)
        assert stmt is not None, "debe ejecutar un UPDATE a delivery_orders"
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "whatsapp_bsuid" in sql
        assert "BSUID-abc123" in sql
        assert "whatsapp_bsuid IS NULL" in sql  # no sobreescribe valores previos
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sin_bsuid_no_toca_la_bd(self):
        factory_patch, db = _session_factory_patch(_company(None))
        with factory_patch:
            await _persist_bsuid(_payload("confirmed"))  # sin bsuid

        db.execute.assert_not_awaited()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fallo_de_bd_no_bloquea_envio(self):
        # fire-and-forget: un error de BD no debe propagarse (no reintenta/DLQ)
        factory_patch, _db = _session_factory_patch(
            _company(None), raise_on_enter=True,
        )
        with factory_patch:
            await _persist_bsuid(_payload("confirmed", bsuid="BSUID-x"))  # no lanza

    @pytest.mark.asyncio
    async def test_process_event_persiste_y_envia(self):
        company = _company({
            "whatsapp": {
                "enabled": True, "token": "tok-f1", "phone_number_id": "456",
                "business_phone": BUSINESS_PHONE, "alert_phone": "+51999000000",
                "templates": {"confirmed": "pedido_confirmado"},
            },
        })
        factory_patch, db = _session_factory_patch(company)
        httpx_patch, client = _httpx_client_patch()
        with factory_patch, httpx_patch:
            await _process_event(_payload("confirmed", bsuid="BSUID-zz99"))

        # envío real normal (CA-B3)
        assert client.post.await_count == 1
        # y BSUID persistido (CA-F1.10)
        stmt = _find_delivery_update(db)
        assert stmt is not None
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "BSUID-zz99" in sql
        assert "whatsapp_bsuid IS NULL" in sql

    @pytest.mark.asyncio
    async def test_sin_bsuid_process_event_no_persiste(self):
        company = _company({
            "whatsapp": {
                "enabled": True, "token": "t", "phone_number_id": "1",
                "templates": {"confirmed": "pc"},
            },
        })
        factory_patch, db = _session_factory_patch(company)
        with factory_patch, patch(
            "app.services.notify_worker.build_notifier",
            return_value=AsyncMock(),
        ):
            await _process_event(_payload("confirmed"))  # sin bsuid

        assert _find_delivery_update(db) is None


# ═══════════════════════════════════════════════════════════════
# D5 / CA-F1.14 — contact en el menú público
# ═══════════════════════════════════════════════════════════════

def _menu_db(company):
    db = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    res.scalar_one_or_none.return_value = company
    db.execute.return_value = res
    return db


class TestContactPublicMenu:
    @pytest.mark.asyncio
    async def test_contact_null_sin_config(self):
        """CA-F1.14: sin settings.whatsapp → contact null (botones ocultos)."""
        menu = await get_public_menu(_menu_db(_company({"delivery": {}})), 1)
        assert menu["contact"] is None

    @pytest.mark.asyncio
    async def test_contact_null_con_enabled_false(self):
        """CA-F1.14: enabled=false aunque haya business_phone → null."""
        menu = await get_public_menu(_menu_db(_company({
            "whatsapp": {"enabled": False, "business_phone": BUSINESS_PHONE},
        })), 1)
        assert menu["contact"] is None

    @pytest.mark.asyncio
    async def test_contact_null_sin_business_phone(self):
        """CA-F1.14: enabled=true pero sin business_phone → null."""
        menu = await get_public_menu(_menu_db(_company({
            "whatsapp": {"enabled": True, "alert_phone": "+51999000000"},
        })), 1)
        assert menu["contact"] is None

    @pytest.mark.asyncio
    async def test_contact_null_si_business_phone_invalido(self):
        menu = await get_public_menu(_menu_db(_company({
            "whatsapp": {"enabled": True, "business_phone": "solo texto"},
        })), 1)
        assert menu["contact"] is None

    @pytest.mark.asyncio
    async def test_contact_poblado_con_config_activa(self):
        """D5: enabled=true + business_phone → wa.me + tel: + mensaje."""
        menu = await get_public_menu(_menu_db(_company({
            "whatsapp": {"enabled": True, "business_phone": BUSINESS_PHONE},
        })), 1)
        contact = menu["contact"]
        assert contact is not None
        expected_url = f"https://wa.me/{BUSINESS_DIGITS}?text={quote(MENSAJE_PREFABRICADO)}"
        assert contact["whatsapp_link"] == expected_url
        assert contact["phone"] == "tel:+51999999999"
        assert contact["whatsapp_message"] == MENSAJE_PREFABRICADO

    def test_contact_serializa_en_public_menu_response(self):
        """El contrato de la API (response_model) acepta contact poblado y null."""
        menu_dict = {
            "tenant_name": "El Segoviano",
            "delivery_window": {"from": "19:00:00", "to": "23:59:59"},
            "currency": "PEN",
            "yape_phone": None,
            "branding": {},
            "contact": {
                "whatsapp_link": f"https://wa.me/{BUSINESS_DIGITS}?text=x",
                "phone": "tel:+51999999999",
                "whatsapp_message": MENSAJE_PREFABRICADO,
            },
            "sections": [],
            "promotions": [],
        }
        parsed = PublicMenuResponse(**menu_dict)
        assert parsed.contact is not None
        assert parsed.contact.whatsapp_link.startswith("https://wa.me/")
        assert parsed.contact.phone == "tel:+51999999999"

        menu_dict["contact"] = None
        assert PublicMenuResponse(**menu_dict).contact is None


# ═══════════════════════════════════════════════════════════════
# D3 — el BSUID del pedido viaja en eventos de transición
# ═══════════════════════════════════════════════════════════════

class TestBsuidEnTransiciones:
    def _order(self, bsuid="BSUID-pedido-1"):
        o = MagicMock()
        o.id = 5
        o.status = "received"
        o.courier_id = None
        o.sale_id = None
        o.tenant_id = 1
        o.tracking_code = "DLV-f1test01"
        o.customer_name = "X"
        o.customer_phone = "999888777"
        o.customer_address = "dir"
        o.zone_id = None
        o.campaign_id = None
        o.utm = None
        o.fee = 5.0
        o.eta_min = 35
        o.notes = None
        o.whatsapp_bsuid = bsuid
        o.created_at = datetime.now(UTC)
        return o

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    async def test_update_status_envia_bsuid_del_pedido(
        self, mock_broadcast, mock_whatsapp_publisher,
    ):
        order = self._order(bsuid="BSUID-pedido-1")
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )

        await update_status(db, order_id=5, tenant_id=1, new_status="preparing")

        pub = mock_whatsapp_publisher["status"]
        assert pub.await_count == 1
        assert pub.await_args.kwargs["bsuid"] == "BSUID-pedido-1"
        assert pub.await_args.kwargs["tracking_code"] == "DLV-f1test01"

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    async def test_update_status_sin_bsuid_envia_none(
        self, mock_broadcast, mock_whatsapp_publisher,
    ):
        order = self._order(bsuid=None)
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )

        await update_status(db, order_id=5, tenant_id=1, new_status="preparing")

        pub = mock_whatsapp_publisher["status"]
        assert pub.await_count == 1
        assert pub.await_args.kwargs["bsuid"] is None
