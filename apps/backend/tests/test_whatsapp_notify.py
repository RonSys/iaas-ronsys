"""
Tests Fase B — Notificaciones WhatsApp (Spec 03 §7, CA-B1..B8).

Cubre: publicación de eventos en checkout y transiciones, worker consumidor
(proveedor Meta Cloud mockeado vía httpx), reintentos → DLQ, dry-run sin
config/token, PATCH /api/settings persistencia, y destinatario cliente vs
local (CA-B8). El pedido NUNCA depende de la notificación (fire-and-forget).
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas import CompanySettings, WhatsAppSettings
from app.services.delivery_service import create_order, update_status
from app.services.notify_events import (
    publish_checkout_events,
    publish_delivery_event,
    publish_status_event,
)
from app.services.notify_worker import (
    _handle_message,
    _process_event,
    _recipient_and_template,
    _whatsapp_from_raw,
)
from app.services.whatsapp_notifier import (
    DryRunNotifier,
    MetaCloudNotifier,
    build_notifier,
)

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _menu_item(id=1, price=25.0):
    item = MagicMock()
    item.id = id
    item.name = f"Item {id}"
    item.price = price
    item.active = True
    item.delivery_enabled = True
    item.available_from = None
    item.available_to = None
    item.item_type = "food"
    item.preparation_area = "cocina"
    item.modifiers = []
    return item


def _zone(id=1, fee=5.0, min_order=35.0, eta_min=35):
    z = MagicMock()
    z.id = id
    z.name = "Zona 1"
    z.fee = fee
    z.min_order = min_order
    z.eta_min = eta_min
    z.active = True
    return z


def _valid_checkout(**overrides):
    data = {
        "items": [{"menu_item_id": 10, "quantity": 2, "modifiers": []}],
        "customer": {
            "name": "Cliente Test", "phone": "999888777",
            "address": "Av. Montenegro 123, SJL",
        },
        "zone_id": 1,
        "payment": {"method": "yape", "reference": "REF123"},
        "utm": {"source": "meta", "medium": "cpc", "campaign": "lanzamiento"},
        "notes": "Sin cebolla",
    }
    data.update(overrides)
    return data


def _checkout_db(zone=None, item=None):
    """db mock con la secuencia de queries de create_order (ver test_delivery)."""
    db = AsyncMock()

    def _result(one_or_none=None, all_items=None, first=None):
        r = MagicMock()
        r.scalar_one_or_none.return_value = one_or_none
        s = MagicMock()
        s.all.return_value = all_items if all_items is not None else []
        s.first.return_value = first
        r.scalars.return_value = s
        return r

    db.execute.side_effect = [
        _result(one_or_none=zone),
        _result(one_or_none=item),
        _result(all_items=[]),
        _result(first=None),
    ]
    return db


def _company(settings: dict | None):
    company = MagicMock()
    company.settings = settings
    company.id = 1
    return company


def _session_factory_patch(company):
    """Parchea get_session_factory para que _load_company devuelva `company`."""
    db = AsyncMock()
    db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=company),
    )
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    return patch("app.services.notify_worker.get_session_factory", return_value=factory)


def _httpx_client_patch():
    """Parchea httpx.AsyncClient (whatsapp_notifier) → cliente fake que responde 200."""
    client = AsyncMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    client.post.return_value = resp
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    patcher = patch(
        "app.services.whatsapp_notifier.httpx.AsyncClient", return_value=cm,
    )
    return patcher, client


def _payload(event_type="confirmed", **overrides):
    data = {
        "event": f"delivery.{event_type}",
        "event_type": event_type,
        "tenant_id": 1,
        "tracking_code": "DLV-abc123",
        "sale_id": 99,
        "customer_phone": "999888777",
        "status": "received",
        "total": 55.0,
        "items_resumen": [{"name": "Item 10", "qty": 2}],
        "zone": "Zona 1",
        "timestamp": "2026-08-11T00:00:00+00:00",
    }
    data.update(overrides)
    return data


class _FakeMessage:
    def __init__(self, body: bytes, message_id: str = "m1"):
        self.body = body
        self.message_id = message_id
        self.content_type = "application/json"
        self.acked = False
        self.nacked = False
        self.requeued = False

    async def ack(self):
        self.acked = True

    async def nack(self, requeue=False):
        self.nacked = True
        self.requeued = requeue


@pytest.fixture(autouse=True)
def _clean_worker_attempts():
    from app.services.notify_worker import _attempts

    _attempts.clear()
    yield
    _attempts.clear()


# ═══════════════════════════════════════════════════════════════
# CA-B1: checkout 201 → evento delivery.confirmed publicado
# ═══════════════════════════════════════════════════════════════

class TestCAB1CheckoutPublicaEvento:
    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_checkout_201_publica_evento_con_payload(
        self, mock_sale, mock_user, mock_broadcast, mock_whatsapp_publisher,
    ):
        mock_user.return_value = 7
        mock_sale.return_value = {"sale": {"id": 99, "sale_number": "VEN-1"}, "message": "ok"}
        db = _checkout_db(zone=_zone(), item=_menu_item(10, price=25.0))

        resp = await create_order(db, tenant_id=1, data=_valid_checkout())

        assert resp["sale_id"] == 99
        assert resp["status"] == "received"
        pub = mock_whatsapp_publisher["checkout"]
        assert pub.await_count == 1
        kwargs = pub.await_args.kwargs
        assert kwargs["tracking_code"].startswith("DLV-")
        assert kwargs["customer_phone"] == "999888777"
        assert kwargs["total"] == 55.0
        assert kwargs["items_resumen"] == [{"name": "Item 10", "qty": 2}]
        assert kwargs["zone"] == "Zona 1"
        assert kwargs["sale_id"] == 99

    @pytest.mark.asyncio
    @patch("app.services.notify_events.publish_delivery_event", new_callable=AsyncMock)
    async def test_publish_checkout_emite_confirmed_y_new_order(self, mock_pub):
        await publish_checkout_events(
            tenant_id=1, tracking_code="DLV-1", sale_id=99,
            customer_phone="999888777", total=55.0,
            items_resumen=[{"name": "X", "qty": 1}], zone="Zona 1",
        )
        assert mock_pub.await_count == 2
        events = [c.args[0] for c in mock_pub.await_args_list]
        assert events == ["confirmed", "new_order"]
        for c in mock_pub.await_args_list:
            assert c.kwargs["status"] == "received"

    @pytest.mark.asyncio
    async def test_publish_delivery_event_routing_y_payload(self):
        connect = AsyncMock()
        channel = MagicMock()
        channel.declare_queue = AsyncMock()
        channel.default_exchange = MagicMock()
        channel.default_exchange.publish = AsyncMock()
        connect.return_value.channel.return_value = channel
        with patch("app.services.notify_events.aio_pika.connect", connect):
            ok = await publish_delivery_event(
                "confirmed", tenant_id=1, tracking_code="DLV-abc",
                sale_id=99, customer_phone="999888777", status="received",
                total=55.0, items_resumen=[{"name": "X", "qty": 1}], zone="Zona 1",
            )

        assert ok is True
        from app.config import settings as _settings

        channel.declare_queue.assert_awaited_once_with("iaas-tasks", durable=True)
        pub = channel.default_exchange.publish
        assert pub.await_count == 1
        assert pub.await_args.kwargs["routing_key"] == "iaas-tasks"
        # default exchange rutea por NOMBRE DE COLA; el worker despacha por payload.event_type
        body = json.loads(pub.await_args.args[0].body)
        assert body["event_type"] == "confirmed"
        assert body["event"] == "delivery.confirmed"
        assert body["tenant_id"] == 1
        assert body["customer_phone"] == "999888777"
        assert _settings.rabbitmq_queue == "iaas-tasks"  # cola del contrato §7.4


# ═══════════════════════════════════════════════════════════════
# CA-B2: transición válida → evento status_changed con status correcto
# ═══════════════════════════════════════════════════════════════

class TestCAB2TransicionPublicaEvento:
    def _order(self, status="received"):
        o = MagicMock()
        o.id = 5
        o.status = status
        o.courier_id = None
        o.sale_id = None
        o.tenant_id = 1
        o.tracking_code = "DLV-abc"
        o.customer_name = "X"
        o.customer_phone = "999888777"
        o.customer_address = "dir"
        o.zone_id = None
        o.campaign_id = None
        o.utm = None
        o.fee = 5.0
        o.eta_min = 35
        o.notes = None
        o.created_at = datetime.now(UTC)
        return o

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    async def test_transicion_valida_publica_status_changed(
        self, mock_broadcast, mock_whatsapp_publisher,
    ):
        order = self._order()
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )

        await update_status(db, order_id=5, tenant_id=1, new_status="preparing")

        pub = mock_whatsapp_publisher["status"]
        assert pub.await_count == 1
        kwargs = pub.await_args.kwargs
        assert kwargs["new_status"] == "preparing"
        assert kwargs["tracking_code"] == "DLV-abc"
        assert kwargs["customer_phone"] == "999888777"
        assert kwargs["tenant_id"] == 1

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    async def test_transicion_invalida_no_publica_evento(
        self, mock_broadcast, mock_whatsapp_publisher,
    ):
        order = self._order()
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )
        with pytest.raises(HTTPException) as exc:
            await update_status(db, order_id=5, tenant_id=1, new_status="delivered")
        assert exc.value.status_code == 400
        mock_whatsapp_publisher["status"].assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.services.notify_events.publish_delivery_event", new_callable=AsyncMock)
    async def test_cancelacion_publica_status_changed_y_cancelled(self, mock_pub):
        """Cancelación: cliente vía status_changed(cancelled) + alerta local vía cancelled."""
        await publish_status_event(
            tenant_id=1, tracking_code="DLV-abc", sale_id=99,
            customer_phone="999888777", new_status="cancelled",
        )
        assert mock_pub.await_count == 2
        events = [c.args[0] for c in mock_pub.await_args_list]
        assert events == ["status_changed", "cancelled"]
        assert mock_pub.await_args_list[0].kwargs["status"] == "cancelled"
        assert mock_pub.await_args_list[1].kwargs["status"] == "cancelled"


# ═══════════════════════════════════════════════════════════════
# CA-B3: worker consume → Meta Cloud API con payload correcto
# ═══════════════════════════════════════════════════════════════

class TestCAB3WorkerLlamaProveedor:
    @pytest.mark.asyncio
    async def test_meta_cloud_payload_correcto(self):
        company = _company({
            "whatsapp": {
                "enabled": True, "provider": "meta_cloud",
                "phone_number_id": "456", "token": "tok-secreto",
                "business_phone": "+5112345678", "alert_phone": "+51999000000",
                "templates": {"confirmed": "pedido_confirmado"},
            },
        })
        httpx_patch, client = _httpx_client_patch()
        with _session_factory_patch(company), httpx_patch:
            await _process_event(_payload("confirmed"))

        assert client.post.await_count == 1
        kwargs = client.post.await_args.kwargs
        body = kwargs["json"]
        assert body["messaging_product"] == "whatsapp"
        assert body["to"] == "999888777"                      # customer_phone (CA-B8)
        assert body["type"] == "template"
        assert body["template"]["name"] == "pedido_confirmado"
        assert body["template"]["language"]["code"] == "es"
        assert kwargs["headers"]["Authorization"] == "Bearer tok-secreto"
        assert (
            client.post.await_args.args[0]
            == "https://graph.facebook.com/v21.0/456/messages"
        )


# ═══════════════════════════════════════════════════════════════
# CA-B4: fallo del proveedor → reintento (0/60/300s) → DLQ
# ═══════════════════════════════════════════════════════════════

class TestCAB4ReintentosYDLQ:
    @pytest.mark.asyncio
    @patch("app.services.notify_worker._process_event", new_callable=AsyncMock)
    async def test_fallo_proveedor_reintenta_y_exito(self, mock_process):
        """CA-B4: 1er envío falla (proveedor), 2º OK → ack, nunca DLQ."""
        mock_process.side_effect = [Exception("HTTP 500"), None]
        msg = _FakeMessage(json.dumps(_payload()).encode())

        first = await _handle_message(msg, delays=(0.0, 0.0, 0.0))
        second = await _handle_message(msg, delays=(0.0, 0.0, 0.0))

        assert first is False          # reencolado para reintento
        assert msg.nacked and msg.requeued
        assert second is True          # reintento exitoso → ack
        assert msg.acked
        assert mock_process.await_count == 2

    @pytest.mark.asyncio
    @patch("app.services.notify_worker._process_event", new_callable=AsyncMock)
    @patch("app.services.notify_worker._publish_to_dlq", new_callable=AsyncMock)
    async def test_reintentos_agotados_va_a_dlq(self, mock_dlq, mock_process):
        """CA-B4: falla siempre → 3 reintentos (0/60/300s) → DLQ + ack."""
        mock_process.side_effect = Exception("provider caído")
        msg = _FakeMessage(json.dumps(_payload()).encode())

        for _ in range(3):  # intento inicial + 2 reintentos
            await _handle_message(msg, delays=(0.0, 0.0, 0.0))
            assert msg.acked is False
        final = await _handle_message(msg, delays=(0.0, 0.0, 0.0))

        assert final is False
        mock_dlq.assert_awaited_once_with(msg)
        assert msg.acked                       # sacado de la cola principal
        assert mock_process.await_count == 4   # 1 inicial + 3 reintentos

    @pytest.mark.asyncio
    async def test_publish_to_dlq_usa_cola_dlq(self):
        connect = AsyncMock()
        channel = MagicMock()
        channel.declare_queue = AsyncMock()
        channel.default_exchange = MagicMock()
        channel.default_exchange.publish = AsyncMock()
        connect.return_value.channel.return_value = channel
        msg = _FakeMessage(json.dumps(_payload()).encode())
        with patch("app.services.notify_worker.aio_pika.connect", connect):
            from app.services.notify_worker import _publish_to_dlq

            await _publish_to_dlq(msg)

        channel.declare_queue.assert_awaited_once_with("iaas-tasks-dlq", durable=True)
        assert channel.default_exchange.publish.await_args.kwargs["routing_key"] == "iaas-tasks-dlq"


# ═══════════════════════════════════════════════════════════════
# CA-B5 / CA-B7: sin config / sin token → dry-run, cero HTTP
# ═══════════════════════════════════════════════════════════════

class TestCAB5CAB7DryRun:
    @pytest.mark.asyncio
    async def test_tenant_sin_config_no_rompe_no_envia(self):
        """CA-B5: tenant sin settings.whatsapp → sin excepción, sin HTTP."""
        httpx_patch, client = _httpx_client_patch()
        with _session_factory_patch(_company(None)), httpx_patch:
            await _process_event(_payload("confirmed"))  # no debe lanzar

        client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sin_token_usa_dryrun_sin_http(self):
        """CA-B7: enabled + plantillas pero sin token → DryRunNotifier, cero HTTP."""
        assert isinstance(
            build_notifier(WhatsAppSettings(enabled=True)), DryRunNotifier,
        )
        assert isinstance(
            build_notifier(WhatsAppSettings()), DryRunNotifier,
        )
        assert isinstance(
            build_notifier(WhatsAppSettings(enabled=True, token="t")), DryRunNotifier,
        )

        company = _company({
            "whatsapp": {
                "enabled": True,  # sin token ni phone_number_id
                "templates": {"confirmed": "pedido_confirmado"},
            },
        })
        httpx_patch, client = _httpx_client_patch()
        with _session_factory_patch(company), httpx_patch:
            await _process_event(_payload("confirmed"))

        client.post.assert_not_awaited()

    def test_build_notifier_meta_solo_con_config_completa(self):
        n = build_notifier(WhatsAppSettings(
            enabled=True, token="t", phone_number_id="123",
        ))
        assert isinstance(n, MetaCloudNotifier)


# ═══════════════════════════════════════════════════════════════
# CA-B6: PATCH /api/settings whatsapp → persiste en companies.settings
# ═══════════════════════════════════════════════════════════════

class TestCAB6PatchSettingsWhatsapp:
    @pytest.mark.asyncio
    async def test_patch_persiste_whatsapp_en_settings(self):
        from app.routers.setup import update_settings

        company = MagicMock()
        company.settings = {"branding": {"currency": "PEN"}}
        company.id = 1
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=company),
        )

        data = CompanySettings(whatsapp={
            "enabled": True, "token": "tok", "phone_number_id": "456",
            "alert_phone": "+51999000000",
            "templates": {"confirmed": "pedido_confirmado", "new_order": "nuevo_pedido"},
        })
        await update_settings(tenant_id=1, current_user=None, db=db, data=data)

        saved = company.settings
        assert saved["whatsapp"]["enabled"] is True
        assert saved["whatsapp"]["token"] == "tok"
        assert saved["whatsapp"]["templates"]["confirmed"] == "pedido_confirmado"
        assert "whatsapp" not in saved["branding"]          # fuera de branding
        assert saved["branding"]["currency"] == "PEN"        # branding intacto
        # delivery preservado (default yape_phone=None, patrón D4 intacto)
        assert saved["delivery"]["yape_phone"] is None

    @pytest.mark.asyncio
    async def test_patch_parcial_preserva_campos_no_enviados(self):
        from app.routers.setup import update_settings

        company = MagicMock()
        company.settings = {
            "branding": {},
            "whatsapp": {
                "enabled": True, "token": "viejo-token",
                "alert_phone": "+51999000000",
            },
        }
        company.id = 1
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=company),
        )

        # PATCH parcial: solo cambia enabled → el token NO enviado se preserva
        await update_settings(
            tenant_id=1, current_user=None, db=db,
            data=CompanySettings(whatsapp={"enabled": False}),
        )

        saved = company.settings["whatsapp"]
        assert saved["enabled"] is False
        assert saved["token"] == "viejo-token"
        assert saved["alert_phone"] == "+51999000000"

    def test_schema_whatsapp_defaults(self):
        s = WhatsAppSettings()
        assert s.enabled is False
        assert s.provider == "meta_cloud"
        assert s.phone_number_id is None and s.token is None
        assert s.templates == {}
        cs = CompanySettings()
        assert cs.whatsapp == s
        # yape_phone de delivery NO se rompe (regresión D4)
        cs2 = CompanySettings(delivery={"yape_phone": "912057784"})
        assert cs2.delivery.yape_phone == "912057784"


# ═══════════════════════════════════════════════════════════════
# CA-B8: mensajes al cliente vs alertas al local
# ═══════════════════════════════════════════════════════════════

class TestCAB8DestinatarioClienteVsLocal:
    def _settings(self):
        return WhatsAppSettings(
            enabled=True, token="t", phone_number_id="123",
            alert_phone="+51999000000",
            templates={
                "confirmed": "pedido_confirmado", "preparing": "en_cocina",
                "cancelled": "pedido_cancelado", "new_order": "nuevo_pedido",
                "order_cancelled": "pedido_cancelado_local",
            },
        )

    def test_cliente_recibe_confirmed_status_changed(self):
        ws = self._settings()
        phone, tpl = _recipient_and_template("confirmed", _payload(), ws)
        assert phone == "999888777" and tpl == "pedido_confirmado"
        phone, tpl = _recipient_and_template(
            "status_changed", _payload("status_changed", status="preparing"), ws,
        )
        assert phone == "999888777" and tpl == "en_cocina"
        phone, tpl = _recipient_and_template(
            "status_changed", _payload("status_changed", status="cancelled"), ws,
        )
        assert phone == "999888777" and tpl == "pedido_cancelado"

    def test_local_recibe_new_order_y_cancelled(self):
        ws = self._settings()
        phone, tpl = _recipient_and_template("new_order", _payload("new_order"), ws)
        assert phone == "+51999000000" and tpl == "nuevo_pedido"
        phone, tpl = _recipient_and_template("cancelled", _payload("cancelled"), ws)
        assert phone == "+51999000000" and tpl == "pedido_cancelado_local"

    @pytest.mark.asyncio
    async def test_worker_envia_alerta_new_order_a_alert_phone(self):
        company = _company({
            "whatsapp": {
                "enabled": True, "token": "t", "phone_number_id": "123",
                "alert_phone": "+51999000000",
                "templates": {"new_order": "nuevo_pedido"},
            },
        })
        notifier = AsyncMock()
        with _session_factory_patch(company), patch(
            "app.services.notify_worker.build_notifier", return_value=notifier,
        ):
            await _process_event(_payload("new_order"))

        notifier.send.assert_awaited_once()
        kwargs = notifier.send.await_args.kwargs
        assert kwargs["phone"] == "+51999000000"       # alert_phone, NO customer
        assert kwargs["template"] == "nuevo_pedido"
        assert kwargs["params"]["tracking_code"] == "DLV-abc123"


# ═══════════════════════════════════════════════════════════════
# Plus: el checkout NO se rompe si RabbitMQ no está disponible
# ═══════════════════════════════════════════════════════════════

class TestPlusCheckoutNoDependeDeRabbitMQ:
    @pytest.mark.asyncio
    async def test_publish_devuelve_false_si_rabbitmq_caido(self):
        connect = AsyncMock(side_effect=Exception("connection refused"))
        with patch("app.services.notify_events.aio_pika.connect", connect):
            ok = await publish_delivery_event(
                "confirmed", tenant_id=1, tracking_code="DLV-abc",
                sale_id=99, customer_phone="999888777", status="received",
            )
        assert ok is False  # fire-and-forget: no levanta

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_checkout_201_aunque_publicador_falle(
        self, mock_sale, mock_user, mock_broadcast, mock_whatsapp_publisher,
    ):
        mock_user.return_value = 7
        mock_sale.return_value = {"sale": {"id": 99, "sale_number": "VEN-1"}, "message": "ok"}
        mock_whatsapp_publisher["checkout"].side_effect = Exception("RabbitMQ down")
        db = _checkout_db(zone=_zone(), item=_menu_item(10, price=25.0))

        resp = await create_order(db, tenant_id=1, data=_valid_checkout())

        # El pedido se crea igual: el evento es best-effort (CA-B1/§7.4)
        assert resp["sale_id"] == 99
        assert resp["status"] == "received"
        assert resp["tracking_code"].startswith("DLV-")
        mock_whatsapp_publisher["checkout"].assert_awaited_once()


# ═══════════════════════════════════════════════════════════════
# Contrato del payload (§7.4) — resolución de settings del worker
# ═══════════════════════════════════════════════════════════════

class TestWorkerSettingsResolution:
    def test_whatsapp_from_raw_defaults(self):
        ws = _whatsapp_from_raw(None)
        assert ws.enabled is False and ws.templates == {}
        ws2 = _whatsapp_from_raw({"whatsapp": {"enabled": True, "token": "t"}})
        assert ws2.enabled is True and ws2.token == "t"
        assert ws2.provider == "meta_cloud"  # defaults completan el resto
