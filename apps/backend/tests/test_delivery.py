"""
Tests unitarios — DeliveryService (Spec 03, Fase A).

Cubre: disponibilidad horaria, checkout (fee como ítem de servicio, IGV,
promo, min_order, yape), máquina de estados, atribución de campaña y el
refactor de PromotionsService.compute_discount.
"""

from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.delivery_service import (
    _item_available,
    _resolve_dates,
    create_order,
    metrics_campaigns,
    metrics_overview,
    resolve_campaign,
    update_status,
)
from app.services.restaurant_service import PromotionsService

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _menu_item(id=1, price=25.0, delivery_enabled=True, available_from=None, available_to=None):
    item = MagicMock()
    item.id = id
    item.name = f"Item {id}"
    item.price = price
    item.active = True
    item.delivery_enabled = delivery_enabled
    item.available_from = available_from
    item.available_to = available_to
    item.item_type = "food"
    item.preparation_area = "cocina"
    item.modifiers = []
    item.description = None
    item.category = "Principales"
    item.delivery_surcharge = 0
    item.image_url = None
    return item


def _modifier(id=1, price_adjustment=2.0, max_select=3):
    mod = MagicMock()
    mod.id = id
    mod.name = f"Mod {id}"
    mod.price_adjustment = price_adjustment
    mod.max_select = max_select
    return mod


def _zone(id=1, fee=5.0, min_order=35.0, eta_min=35, active=True):
    z = MagicMock()
    z.id = id
    z.name = "Zona 1"
    z.fee = fee
    z.min_order = min_order
    z.eta_min = eta_min
    z.active = active
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


def _make_db(many=None, one=None, scalar=None, scalar_one_or_none=None):
    """AsyncSession mock con execute() configurable por llamada."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = many if many is not None else []
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalar.return_value = scalar
    if one is not None:
        result.one.return_value = one
    db.execute.return_value = result
    return db


def _result(one_or_none=None, all_items=None, first=None, one_row=None, scalar=None):
    """Resultado de execute() con las proyecciones usadas por el servicio."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = one_or_none
    r.scalar.return_value = scalar
    r.one.return_value = one_row
    s = MagicMock()
    s.all.return_value = all_items if all_items is not None else []
    s.first.return_value = first
    r.scalars.return_value = s
    return r


def _checkout_db(zone=None, item=None):
    """db mock con la secuencia de queries de create_order.

    Orden: zona → item → promos (scalars.all) → campaña (scalars.first).
    """
    db = AsyncMock()
    db.execute.side_effect = [
        _result(one_or_none=zone),
        _result(one_or_none=item),
        _result(all_items=[]),
        _result(first=None),
    ]
    return db


# ═══════════════════════════════════════════════════════════════
# Disponibilidad horaria (R1)
# ═══════════════════════════════════════════════════════════════

class TestItemAvailable:
    def test_sin_ventana_rige_delivery_enabled(self):
        assert _item_available(_menu_item(delivery_enabled=True), dtime(15, 0)) is True
        assert _item_available(_menu_item(delivery_enabled=False), dtime(15, 0)) is False

    def test_dentro_de_ventana(self):
        it = _menu_item(available_from=dtime(19, 0), available_to=dtime(23, 59, 59))
        assert _item_available(it, dtime(20, 30)) is True

    def test_fuera_de_ventana(self):
        it = _menu_item(available_from=dtime(19, 0), available_to=dtime(23, 59, 59))
        assert _item_available(it, dtime(15, 0)) is False

    def test_ventana_que_cruza_medianoche(self):
        it = _menu_item(available_from=dtime(22, 0), available_to=dtime(2, 0))
        assert _item_available(it, dtime(23, 30)) is True
        assert _item_available(it, dtime(1, 0)) is True
        assert _item_available(it, dtime(12, 0)) is False


# ═══════════════════════════════════════════════════════════════
# Checkout
# ═══════════════════════════════════════════════════════════════

class TestCreateOrder:
    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_happy_path_fee_como_item_servicio(
        self, mock_sale, mock_user, mock_broadcast
    ):
        mock_user.return_value = 7
        mock_sale.return_value = {
            "sale": {"id": 99, "sale_number": "VEN-2026-00001-123"},
            "message": "ok",
        }
        db = _checkout_db(zone=_zone(), item=_menu_item(10, price=25.0))

        resp = await create_order(db, tenant_id=1, data=_valid_checkout())

        assert resp["sale_id"] == 99
        assert resp["status"] == "received"
        assert resp["totals"]["fee"] == 5.0
        assert resp["totals"]["subtotal"] == 50.0  # 2 x 25
        assert resp["totals"]["total"] == 55.0     # 50 + fee
        # El Sale se crea con fee como ítem de servicio
        sale_data = mock_sale.await_args.kwargs["data"]
        item_names = [i["item_name"] for i in sale_data["items"]]
        assert "Delivery fee" in item_names
        fee_item = sale_data["items"][-1]
        assert fee_item["item_type"] == "service" and fee_item["total"] == 5.0
        assert sale_data["restaurant_data"]["order_type"] == "delivery"
        assert sale_data["restaurant_data"]["delivery_address"] == "Av. Montenegro 123, SJL"
        # DeliveryOrder creada con utm + tracking
        assert resp["tracking_code"].startswith("DLV-")
        # Comanda de cocina + broadcast
        assert mock_broadcast.await_count >= 1
        event = mock_broadcast.await_args.args[1]
        assert event == "new_delivery"

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_min_order_no_cumplido_422(self, mock_sale, mock_user, mock_broadcast):
        db = _checkout_db(zone=_zone(min_order=60.0), item=_menu_item(10, price=25.0))

        with pytest.raises(HTTPException) as exc:
            await create_order(db, tenant_id=1, data=_valid_checkout())
        assert exc.value.status_code == 422
        assert "mínimo" in exc.value.detail
        mock_sale.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_yape_sin_reference_400(self, mock_sale, mock_user, mock_broadcast):
        db = _checkout_db(zone=_zone(), item=_menu_item(10))

        with pytest.raises(HTTPException) as exc:
            await create_order(
                db, tenant_id=1,
                data=_valid_checkout(payment={"method": "yape", "reference": None}),
            )
        assert exc.value.status_code == 400
        mock_sale.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    @patch("app.services.delivery_service._system_user_id", new_callable=AsyncMock)
    @patch("app.services.delivery_service.SaleService.create_sale", new_callable=AsyncMock)
    async def test_item_fuera_de_horario_422(self, mock_sale, mock_user, mock_broadcast):
        item = _menu_item(10, price=25.0)
        item.available_from = dtime(19, 0)
        item.available_to = dtime(23, 59, 59)
        db = _checkout_db(zone=_zone(), item=item)

        class _FakeDT:
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 8, 3, 15, 0, tzinfo=tz or UTC)

        with patch("app.services.delivery_service.datetime", _FakeDT):
            with pytest.raises(HTTPException) as exc:
                await create_order(db, tenant_id=1, data=_valid_checkout())
        assert exc.value.status_code == 422
        assert "horario" in exc.value.detail
        mock_sale.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════
# Máquina de estados
# ═══════════════════════════════════════════════════════════════

class TestUpdateStatus:
    @pytest.mark.asyncio
    @patch("app.services.delivery_service.manager.broadcast_to_kitchen", new_callable=AsyncMock)
    async def test_transicion_valida_setea_timestamp(self, mock_broadcast):
        order = MagicMock()
        order.id = 5
        order.status = "received"
        order.courier_id = None
        order.sale_id = None
        order.tenant_id = 1
        order.tracking_code = "DLV-abc"
        order.customer_name = "X"
        order.customer_phone = "1"
        order.customer_address = "dir"
        order.zone_id = None
        order.campaign_id = None
        order.utm = None
        order.fee = 5.0
        order.eta_min = 35
        order.notes = None
        order.created_at = datetime.now(UTC)

        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )

        await update_status(db, order_id=5, tenant_id=1, new_status="preparing")
        assert order.status == "preparing"
        assert order.preparing_at is not None

    @pytest.mark.asyncio
    async def test_transicion_invalida_400(self):
        order = MagicMock()
        order.status = "received"

        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=order),
        )
        with pytest.raises(HTTPException) as exc:
            await update_status(db, order_id=5, tenant_id=1, new_status="delivered")
        assert exc.value.status_code == 400
        assert "Transición inválida" in exc.value.detail


# ═══════════════════════════════════════════════════════════════
# Atribución de campaña (R4)
# ═══════════════════════════════════════════════════════════════

class TestResolveCampaign:
    @pytest.mark.asyncio
    async def test_match_activo(self):
        campaign = MagicMock()
        campaign.id = 42
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=campaign))),
        )
        assert await resolve_campaign(
            db, 1, {"source": "meta", "medium": "cpc", "campaign": "lanzamiento"}
        ) == 42

    @pytest.mark.asyncio
    async def test_sin_utm_retorna_none(self):
        db = AsyncMock()
        assert await resolve_campaign(db, 1, None) is None

    @pytest.mark.asyncio
    async def test_sin_campaign_no_matchea(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))),
        )
        assert await resolve_campaign(
            db, 1, {"source": "meta", "medium": "cpc", "campaign": "otra"}
        ) is None


# ═══════════════════════════════════════════════════════════════
# PromotionsService.compute_discount (refactor — regresión)
# ═══════════════════════════════════════════════════════════════

class TestComputeDiscount:
    def _promo(self, promo_type, discount_value, rules=None):
        p = MagicMock()
        p.promo_type = promo_type
        p.discount_value = discount_value
        p.rules = rules or {}
        return p

    @pytest.mark.asyncio
    async def test_discount_pct(self):
        items = [{"menu_item_id": 1, "quantity": 2, "unit_price": 25.0, "total": 50.0}]
        d = await PromotionsService.compute_discount(
            self._promo("discount_pct", 10), items
        )
        assert d == 5.0

    @pytest.mark.asyncio
    async def test_bogof(self):
        items = [
            {"menu_item_id": 1, "quantity": 2, "unit_price": 25.0, "total": 50.0},
        ]
        d = await PromotionsService.compute_discount(
            self._promo("bogof", 0, {"buy_item_id": 1}), items
        )
        assert d == 25.0  # 1 unidad gratis

    @pytest.mark.asyncio
    async def test_combo_sin_items_requeridos(self):
        items = [{"menu_item_id": 1, "quantity": 1, "unit_price": 25.0, "total": 25.0}]
        d = await PromotionsService.compute_discount(
            self._promo("combo", 30.0, {"items": [1, 2]}), items
        )
        assert d == 0.0

    @pytest.mark.asyncio
    async def test_descuento_no_excede_subtotal(self):
        items = [{"menu_item_id": 1, "quantity": 1, "unit_price": 25.0, "total": 25.0}]
        d = await PromotionsService.compute_discount(
            self._promo("discount_fixed", 50.0, {"min_amount": 10}), items
        )
        assert d == 25.0


# ═══════════════════════════════════════════════════════════════
# Settings delivery (D-03 / D4 — fix yape_phone configurable)
# ═══════════════════════════════════════════════════════════════

class TestSettingsDelivery:
    def test_company_settings_acepta_delivery_yape_phone(self):
        from app.schemas import CompanySettings
        s = CompanySettings(delivery={"yape_phone": "912057784"})
        assert s.delivery.yape_phone == "912057784"

    @pytest.mark.asyncio
    async def test_update_settings_persiste_delivery_fuera_de_branding(self):
        from app.routers.setup import update_settings
        from app.schemas import CompanySettings

        company = MagicMock()
        company.settings = {"branding": {"currency": "PEN"}}
        company.id = 1

        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=company),
        )

        data = CompanySettings(delivery={"yape_phone": "912057784"})
        await update_settings(tenant_id=1, current_user=None, db=db, data=data)

        # Persistido en companies.settings: delivery FUERA de branding
        saved = company.settings
        assert saved["delivery"]["yape_phone"] == "912057784"
        assert "delivery" not in saved["branding"]
        assert saved["branding"]["currency"] == "PEN"  # branding intacto


# ═══════════════════════════════════════════════════════════════
# Métricas con rango de fechas (Spec 03 §3.4.2 — bug 2026-08-11)
# ═══════════════════════════════════════════════════════════════

class TestMetrics:
    """metrics_overview / metrics_campaigns con from/to.

    Bug prod 2026-08-11: las fechas llegaban como str y se comparaban contra
    created_at (timestamptz) → 500 (operator does not exist). El fix parsea
    con _resolve_dates y compara contra datetime.combine(d, time.min/max).
    """

    @staticmethod
    def _stmt(db, index=0):
        return db.execute.call_args_list[index].args[0]

    @staticmethod
    def _bounds(frm, to):
        return datetime.combine(frm, dtime.min), datetime.combine(to, dtime.max)

    @pytest.mark.asyncio
    async def test_metrics_overview_con_rango_fechas(self):
        row = (5, 250.0, 25.0, 1200.0)  # orders, gmv, fee, epoch secs
        db = _make_db(one=row, scalar=2)

        resp = await metrics_overview(
            db, tenant_id=1, date_from="2026-08-01", date_to="2026-08-10",
        )

        assert resp == {
            "orders": 5,
            "gmv": 250.0,
            "fee_total": 25.0,
            "avg_delivery_min": round(1200.0 / 60 / 5, 1),
            "cancelled": 2,
        }
        # Ambas queries (entregados + cancelados) filtran created_at por el rango
        lo, hi = self._bounds(date(2026, 8, 1), date(2026, 8, 10))
        for i in (0, 1):
            stmt = self._stmt(db, i)
            clause = str(stmt.whereclause)
            assert "created_at >= :created_at_1" in clause
            assert "created_at <= :created_at_2" in clause
            params = stmt.compile().params
            assert params["created_at_1"] == lo
            assert params["created_at_2"] == hi

    @pytest.mark.asyncio
    async def test_metrics_overview_sin_fechas_default_30_dias(self):
        db = _make_db(one=(0, None, None, None), scalar=0)

        resp = await metrics_overview(db, tenant_id=1)

        assert set(resp) == {"orders", "gmv", "fee_total", "avg_delivery_min", "cancelled"}
        assert resp["orders"] == 0 and resp["cancelled"] == 0
        assert resp["avg_delivery_min"] is None
        # Default: últimos 30 días (incluye hoy), sin 500
        to = datetime.now(UTC).date()
        frm = to - timedelta(days=29)
        params = self._stmt(db).compile().params
        assert params["created_at_1"] == datetime.combine(frm, dtime.min)
        assert params["created_at_2"] == datetime.combine(to, dtime.max)

    @pytest.mark.asyncio
    async def test_metrics_campaigns_con_rango_fechas(self):
        c = MagicMock()
        c.id = 1
        c.name = "Lanzamiento"
        c.channel = "meta"
        c.spend = 50.0
        db = _make_db(many=[c], one=(4, 200.0))

        resp = await metrics_campaigns(
            db, tenant_id=1, date_from="2026-08-01", date_to="2026-08-10",
        )

        assert len(resp) == 1
        assert resp[0]["campaign_id"] == 1
        assert resp[0]["orders"] == 4
        assert resp[0]["gmv"] == 200.0
        assert resp[0]["aov"] == 50.0
        assert resp[0]["roas"] == 4.0
        # La query de agregación filtra created_at por el rango
        agg = self._stmt(db, 1)
        clause = str(agg.whereclause)
        assert "created_at >= :created_at_1" in clause
        assert "created_at <= :created_at_2" in clause
        params = agg.compile().params
        assert params["created_at_1"] == datetime.combine(date(2026, 8, 1), dtime.min)
        assert params["created_at_2"] == datetime.combine(date(2026, 8, 10), dtime.max)

    @pytest.mark.asyncio
    async def test_metrics_campaigns_con_rango_sin_campañas(self):
        db = _make_db(many=[])

        resp = await metrics_campaigns(
            db, tenant_id=1, date_from="2026-08-01", date_to="2026-08-10",
        )

        assert resp == []

    def test_resolve_dates_acepta_datetime_del_panel(self):
        # owner_dashboard pasa datetime.combine(d, time.min/max) — debe aceptarlos
        frm, to = _resolve_dates(
            datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 10, 23, 59, 59),
        )
        assert frm == date(2026, 8, 1)
        assert to == date(2026, 8, 10)
