"""
Tests del Panel del Dueño (Spec 04, V1) — service + endpoint HTTP.

Unit: cálculos del service con AsyncSession mock (patrón test_delivery).
HTTP: TestClient con dependency overrides (patrón test_sales_routes) —
  verifica auth (401 sin token), roles (403 operator) y 422 fechas inválidas.
"""
from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.user import User
from app.services.owner_dashboard_service import (
    _money,
    _parse_date,
    _resolve_dates,
    get_owner_dashboard,
)

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_db(*side_effects):
    """AsyncSession mock: cada execute() devuelve un resultado con .one()/.all()."""
    db = AsyncMock()

    def _result_for(value):
        r = MagicMock()
        r.one.return_value = value
        r.all.return_value = value
        r.scalar.return_value = value
        s = MagicMock()
        s.all.return_value = value
        r.scalars.return_value = s
        return r

    db.execute.side_effect = [_result_for(v) for v in side_effects]
    return db


def _clear_overrides():
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)


@pytest.fixture
def client():
    _clear_overrides()
    user = User(
        id=1, email="dueno@elsegoviano.pe", full_name="Dueño",
        role="manager", company_id=1, is_active=True, is_verified=True,
        failed_login_attempts=0,
    )

    async def fake_user():
        return user

    async def fake_tenant():
        return 1

    async def fake_db():
        return AsyncMock()

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    _clear_overrides()


def _assert_protected(method: str, path: str):
    """Verifica 401 sin Authorization (con X-Tenant-ID presente)."""
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_user, None)
    c = TestClient(app)
    headers = {"X-Tenant-ID": "1"}  # Tenant presente, falta JWT (patrón test_sales_routes)
    r = getattr(c, method)(path, headers=headers)
    assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Unit — helpers
# ═══════════════════════════════════════════════════════════════

class TestHelpers:
    def test_parse_date_valid(self):
        assert _parse_date("2026-08-10") == date(2026, 8, 10)

    def test_parse_date_invalid(self):
        with pytest.raises(ValueError):
            _parse_date("mal")

    def test_resolve_default_30_dias(self):
        frm, to = _resolve_dates(None, None)
        assert to == date.today()
        assert (to - frm).days == 29  # rango de 30 días

    def test_resolve_rango_invertido(self):
        with pytest.raises(ValueError):
            _resolve_dates("2026-08-10", "2026-08-01")

    def test_money(self):
        assert _money("12.3456") == 12.35
        assert _money(None) == 0.0


# ═══════════════════════════════════════════════════════════════
# Unit — get_owner_dashboard (estructura del contrato §3.1)
# ═══════════════════════════════════════════════════════════════

class TestOwnerDashboardService:
    @pytest.mark.asyncio
    async def test_contrato_completo(self):
        """El response contiene todos los bloques del contrato §3.1."""
        db = _make_db(
            (1000.0, 30),            # _kpis: sales_total, orders_count
            [("delivery", 12), ("dine_in", 15), ("takeout", 3)],  # _kpis canales
            2,                        # _kpis kitchen_open
            3,                        # _kpis delivery_in_route
            [(12, "dine_in", 320.0), (13, "delivery", 100.0)],  # _sales_by_hour
            [(1, 850.0), (7, 500.0)],  # _sales_by_weekday
            [("dine_in", 680.0), ("delivery", 320.0)],  # _channels
            [("Ceviche", 15, 375.0)],  # _top_platos
            [("yape", 500.0)],        # _payments
            [("Zona 1", 12)],         # _delivery_block zonas
            [("delivered", 9), ("cancelled", 2)],  # _delivery_block funnel
            # V2 — bloques CA10-CA14 (orden de ejecución anexado al final)
            [(12, 1, "dine_in", 320.0), (13, 2, "delivery", 100.0)],  # _heatmap (hora, dia, canal, total)
            [("dine_in", 300.0), ("delivery", 40.0)],    # _margins (costo por canal)
            (2000.0, 50),              # _comparison current base
            [("delivery", 20), ("dine_in", 25), ("takeout", 5)],  # _comparison current canales
            (1800.0, 45),              # _comparison previous base
            [("delivery", 15)],       # _comparison previous canales
            [(date(2026, 8, 1), 100.0, 3), (date(2026, 8, 2), 100.0, 3)],  # _alerts diario (fecha, total, n)
            [(date(2026, 8, 1), 1), (date(2026, 8, 2), 1)],  # _alerts delivery diario
            # Iteración 3 — CA-M1..M4 (orden anexado al final)
            [(1, "Dueño", 5, 400.0), (2, "Mesero", 3, 200.0)],  # _top_waiters rows (user_id, name, n, total)
            20,                        # _top_waiters total_sales
            2,                         # _cancellation_rate voided
            25,                        # _cancellation_rate total
            [("cliente no vino", 2)],  # _cancellation_rate reasons
            [("dine_in", 320.0, 15), ("delivery", 100.0, 2)],  # _avg_ticket_by canales (tipo, avg, n)
            [(time(12, 0), 320.0), (time(20, 0), 100.0)],       # _avg_ticket_by turnos (hora, total)
            [(1, {"source": "meta"}, 240.0), (None, None, 100.0)],  # _delivery_campaign_effect rows
            [(1, "Meta Jul")],        # _delivery_campaign_effect camp names
            # metrics_overview + metrics_campaigns (parcheados)
        )
        with patch("app.services.owner_dashboard_service.metrics_overview",
                   new=AsyncMock(return_value={"orders": 9, "gmv": 450.5,
                                               "fee_total": 90.0,
                                               "avg_delivery_min": 32.4,
                                               "cancelled": 2})), \
             patch("app.services.owner_dashboard_service.metrics_campaigns",
                   new=AsyncMock(return_value=[{"campaign_id": 1, "name": "Meta Jul",
                                                "channel": "meta", "spend": 100,
                                                "orders": 8, "gmv": 240,
                                                "aov": 30, "roas": 2.4}])):
            out = await get_owner_dashboard(db, 1, "2026-08-01", "2026-08-10")

        assert out["period"] == {"date_from": "2026-08-01", "date_to": "2026-08-10"}
        k = out["kpis"]
        assert k["sales_total"] == 1000.0
        assert k["orders_count"] == 30
        assert k["avg_ticket"] == round(1000 / 30, 2)
        assert k["orders_delivery"] == 12
        assert k["orders_dine_in"] == 15
        assert k["orders_takeout"] == 3
        assert k["delivery_pct"] == 40.0  # 12/30
        assert k["kitchen_open"] == 2
        assert k["delivery_in_route"] == 3

        # Serie por hora: 24 huecos sin agujeros (CA3)
        assert len(out["sales_by_hour"]) == 24
        assert out["sales_by_hour"][12] == {"hour": 12, "dine_in": 320.0, "delivery": 0.0}
        assert out["sales_by_hour"][13] == {"hour": 13, "dine_in": 0.0, "delivery": 100.0}

        # Semana: 7 días
        assert len(out["sales_by_weekday"]) == 7
        assert out["sales_by_weekday"][0] == {"weekday": 1, "total": 850.0}

        assert out["channels"] == {"dine_in": 680.0, "delivery": 320.0}
        assert out["top_platos"][0]["name"] == "Ceviche"
        assert out["payments"] == {"yape": 500.0}

        d = out["delivery"]
        assert d["orders_by_zone"] == [{"zone": "Zona 1", "orders": 12}]
        assert d["funnel"]["delivered"] == 9
        assert d["funnel"]["cancelled"] == 2
        assert d["funnel"]["out_for_delivery"] == 0
        assert d["gmv"] == 450.5
        assert d["fee_total"] == 90.0
        assert d["avg_delivery_min"] == 32.4

        assert out["campaigns"][0]["roas"] == 2.4

        # ── V2 — bloques del contrato §3.1-V2 (CA10-CA14) ──
        assert set(out["heatmap"]) == {"dine_in", "delivery"}
        assert len(out["heatmap"]["dine_in"]["rows"]) == 24 * 7   # 24×7 completos (CA10)
        assert len(out["heatmap"]["delivery"]["rows"]) == 24 * 7
        # orden hora-mayor: índice = hora*7 + (weekday-1)
        assert out["heatmap"]["dine_in"]["rows"][12 * 7] == {"hour": 12, "weekday": 1, "total": 320.0}
        assert out["heatmap"]["delivery"]["rows"][13 * 7 + 1] == {"hour": 13, "weekday": 2, "total": 100.0}

        m = out["margins"]
        assert [b["channel"] for b in m["by_channel"]] == ["dine_in", "takeout", "delivery"]
        assert m["by_channel"][0]["margin_pct"] == 55.9   # (680-300)/680*100
        assert m["by_channel"][1] == {"channel": "takeout", "revenue": 0.0, "cost": 0.0, "margin_pct": 0.0}
        assert m["by_channel"][2]["margin_pct"] == 87.5   # (320-40)/320*100
        assert "costable_note" in m

        comp = out["comparison"]
        assert comp["current"]["sales_total"] == 2000.0
        assert comp["previous"]["sales_total"] == 1800.0
        assert comp["deltas"]["sales_total_pct"] == round((2000 - 1800) / 1800 * 100, 1)
        assert comp["deltas"]["orders_count_pct"] == round((50 - 45) / 45 * 100, 1)
        assert comp["deltas"]["delivery_pct_delta"] == round(40.0 - 33.3, 1)  # puntos porcentuales

        assert isinstance(out["alerts"], list)   # nunca null (CA14)

    @pytest.mark.asyncio
    async def test_sin_ventas_devuelve_ceros(self):
        """Sin data: KPIs en 0 y series completas (sin errores de división)."""
        db = _make_db(
            (0.0, 0),        # kpis ventas
            [],              # canales
            0,               # kitchen_open
            0,               # delivery_in_route
            [],              # hours
            [],              # weekday
            [],              # channels
            [],              # top
            [],              # payments
            [],              # zonas
            [],              # funnel
            # V2 — sin data (CA10-CA14)
            [],              # heatmap
            [],              # margins
            (0.0, 0),        # comparison current base
            [],              # comparison current canales
            (0.0, 0),        # comparison previous base
            [],              # comparison previous canales
            [],              # alerts diario
            [],              # alerts delivery diario
            # Iteración 3 — CA-M1..M4 (sin data)
            [],              # _top_waiters rows
            0,               # _top_waiters total_sales
            0,               # _cancellation_rate voided
            0,               # _cancellation_rate total
            [],              # _cancellation_rate reasons
            [],              # _avg_ticket_by canales
            [],              # _avg_ticket_by turnos
            [],              # _delivery_campaign_effect rows (sin ids → no query de nombres)
        )
        with patch("app.services.owner_dashboard_service.metrics_overview",
                   new=AsyncMock(return_value={"orders": 0, "gmv": 0.0, "fee_total": 0.0,
                                               "avg_delivery_min": None, "cancelled": 0})), \
             patch("app.services.owner_dashboard_service.metrics_campaigns",
                   new=AsyncMock(return_value=[])):
            out = await get_owner_dashboard(db, 1)
        assert out["kpis"]["avg_ticket"] == 0.0
        assert out["kpis"]["delivery_pct"] == 0.0
        assert len(out["sales_by_hour"]) == 24
        assert len(out["sales_by_weekday"]) == 7
        # V2 sin data
        assert len(out["heatmap"]["dine_in"]["rows"]) == 168
        assert all(r["total"] == 0.0 for r in out["heatmap"]["dine_in"]["rows"])
        assert all(b["margin_pct"] == 0.0 for b in out["margins"]["by_channel"])
        assert out["comparison"]["deltas"]["sales_total_pct"] is None   # previous=0 → null
        assert out["alerts"] == []


# ═══════════════════════════════════════════════════════════════
# HTTP — endpoint /api/v1/dashboard/owner
# ═══════════════════════════════════════════════════════════════

class TestOwnerDashboardEndpoint:
    def test_requiere_auth(self):
        _assert_protected("get", "/api/v1/dashboard/owner")

    def test_fecha_invalida_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner", params={"date_from": "mal"})
        assert r.status_code == 422
        assert "Fecha inválida" in r.json()["detail"]

    def test_rango_invertido_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner",
                       params={"date_from": "2026-08-10", "date_to": "2026-08-01"})
        assert r.status_code == 422

    def test_operator_prohibido(self):
        """D6: solo admin/manager/viewer — operator recibe 403."""
        _clear_overrides()
        user = User(
            id=2, email="op@elsegoviano.pe", full_name="Op",
            role="operator", company_id=1, is_active=True, is_verified=True,
            failed_login_attempts=0,
        )

        async def fake_user():
            return user

        async def fake_tenant():
            return 1

        async def fake_db():
            return AsyncMock()

        app.dependency_overrides[get_current_active_user] = fake_user
        app.dependency_overrides[get_current_user] = fake_user
        app.dependency_overrides[get_tenant_id] = fake_tenant
        app.dependency_overrides[get_db] = fake_db
        r = TestClient(app).get("/api/v1/dashboard/owner")
        assert r.status_code == 403
        _clear_overrides()
