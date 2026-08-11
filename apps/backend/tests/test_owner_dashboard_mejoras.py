"""
Tests del Panel del Dueño — Iteración 3 (Spec 04 §3.2-V2: CA-M1..M4).

Cubre: top_waiters (CA-M1), cancellation_rate (CA-M2), avg_ticket_by (CA-M3),
delivery_campaign_effect (CA-M4), CSV ampliado (CA-M5), PDF ampliado (CA-M6)
y el wire completo del endpoint.

Patrón de mocks: AsyncSession con side_effects sobre db.execute (mismo patrón
que test_owner_dashboard.py / test_owner_dashboard_v2.py).
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
    _avg_ticket_by,
    _cancellation_rate,
    _delivery_campaign_effect,
    _top_waiters,
    render_owner_csv,
    render_owner_pdf,
)
from tests.test_owner_dashboard_pdf import _pdf_contains
from tests.test_owner_dashboard_v2 import _sample_dashboard

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_db(*side_effects):
    """AsyncSession mock: cada execute() devuelve un resultado con .one()/.all()/.scalar()."""
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


def _sample_dashboard_con_mejoras() -> dict:
    """_sample_dashboard() + los 4 bloques nuevos (CA-M1..M4)."""
    d = dict(_sample_dashboard())
    d.update({
        "top_waiters": {
            "rows": [
                {"user_id": 1, "name": "Dueño", "sales_count": 5, "total": 400.0, "avg_ticket": 80.0},
            ],
            "total_sales": 20,
        },
        "cancellation_rate": {
            "voided_count": 2, "total_count": 25, "rate_pct": 8.0,
            "top_reasons": [{"reason": "cliente no vino", "count": 2}],
        },
        "avg_ticket_by": {
            "channel": [
                {"channel": "dine_in", "ticket": 265.0},
                {"channel": "delivery", "ticket": 200.0},
            ],
            "shift": [
                {"shift": "morning", "ticket": 100.0, "orders": 1},
                {"shift": "afternoon", "ticket": 200.0, "orders": 1},
                {"shift": "evening", "ticket": 300.0, "orders": 1},
            ],
        },
        "delivery_campaign_effect": {
            "by_campaign": [
                {"campaign_id": 1, "campaign_name": "Meta Jul", "orders": 8, "gmv": 240.0, "aov": 30.0},
                {"campaign_id": None, "campaign_name": "Sin campaña", "orders": 3, "gmv": 100.0, "aov": 33.33},
            ],
            "by_channel": [
                {"source": "meta", "orders": 8, "gmv": 240.0, "aov": 30.0},
                {"source": "directo", "orders": 3, "gmv": 100.0, "aov": 33.33},
            ],
        },
    })
    return d


def _client_with_db(db) -> TestClient:
    """TestClient con overrides y un AsyncSession mock con side_effects."""
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)
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
        return db

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════
# CA-M1 — Top meseros
# ═══════════════════════════════════════════════════════════════

class TestTopWaiters:
    @pytest.mark.asyncio
    async def test_contrato(self):
        """Keys exactas, orden desc por total y total_sales presente (CA-M1)."""
        db = _make_db(
            [(1, "Dueño", 5, 400.0), (2, "Mesero", 3, 200.0), (3, "Ayudante", 1, 50.0)],
            20,
        )
        out = await _top_waiters(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert set(out) == {"rows", "total_sales"}
        assert out["total_sales"] == 20
        assert [r["name"] for r in out["rows"]] == ["Dueño", "Mesero", "Ayudante"]
        assert out["rows"][0] == {
            "user_id": 1, "name": "Dueño", "sales_count": 5,
            "total": 400.0, "avg_ticket": 80.0,
        }

    @pytest.mark.asyncio
    async def test_sin_ventas(self):
        db = _make_db([], 0)
        out = await _top_waiters(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out == {"rows": [], "total_sales": 0}


# ═══════════════════════════════════════════════════════════════
# CA-M2 — % anulaciones + motivos
# ═══════════════════════════════════════════════════════════════

class TestCancellationRate:
    @pytest.mark.asyncio
    async def test_sin_anuladas(self):
        """rate_pct 1 decimal; top_reasons [] sin datos (CA-M2)."""
        db = _make_db(0, 30, [])
        out = await _cancellation_rate(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out == {"voided_count": 0, "total_count": 30, "rate_pct": 0.0, "top_reasons": []}

    @pytest.mark.asyncio
    async def test_con_motivos(self):
        db = _make_db(3, 30, [("cliente no vino", 2), ("error de caja", 1)])
        out = await _cancellation_rate(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out["voided_count"] == 3
        assert out["total_count"] == 30
        assert out["rate_pct"] == 10.0
        assert out["top_reasons"] == [
            {"reason": "cliente no vino", "count": 2},
            {"reason": "error de caja", "count": 1},
        ]

    @pytest.mark.asyncio
    async def test_sin_ninguna_venta_no_divide(self):
        db = _make_db(0, 0, [])
        out = await _cancellation_rate(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out["rate_pct"] == 0.0


# ═══════════════════════════════════════════════════════════════
# CA-M3 — Ticket promedio por canal y turno
# ═══════════════════════════════════════════════════════════════

class TestAvgTicketBy:
    @pytest.mark.asyncio
    async def test_contrato_canales_y_turnos(self):
        """2 canales (dine_in agrega takeout) + 3 turnos completos (CA-M3)."""
        db = _make_db(
            [("dine_in", 320.0, 15), ("takeout", 100.0, 5), ("delivery", 200.0, 4)],
            [(time(9, 0), 100.0), (time(14, 0), 200.0), (time(20, 0), 300.0)],
        )
        out = await _avg_ticket_by(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert set(out) == {"channel", "shift"}
        # dine_in = (320*15 + 100*5) / 20 = 265.0
        assert out["channel"] == [
            {"channel": "dine_in", "ticket": 265.0},
            {"channel": "delivery", "ticket": 200.0},
        ]
        assert [s["shift"] for s in out["shift"]] == ["morning", "afternoon", "evening"]
        assert out["shift"][0] == {"shift": "morning", "ticket": 100.0, "orders": 1}
        assert out["shift"][1] == {"shift": "afternoon", "ticket": 200.0, "orders": 1}
        assert out["shift"][2] == {"shift": "evening", "ticket": 300.0, "orders": 1}

    @pytest.mark.asyncio
    async def test_huecos_con_ceros(self):
        """Sin data: canales y turnos completos con 0 (sin agujeros)."""
        db = _make_db([], [])
        out = await _avg_ticket_by(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out["channel"] == [
            {"channel": "dine_in", "ticket": 0.0},
            {"channel": "delivery", "ticket": 0.0},
        ]
        assert len(out["shift"]) == 3
        assert all(s["ticket"] == 0.0 and s["orders"] == 0 for s in out["shift"])


# ═══════════════════════════════════════════════════════════════
# CA-M4 — Delivery: campaña vs sin campaña
# ═══════════════════════════════════════════════════════════════

class TestDeliveryCampaignEffect:
    @pytest.mark.asyncio
    async def test_contrato(self):
        """by_campaign 'Sin campaña' con null; by_channel 'directo' con utm vacío; excluye cancelled."""
        results = [
            [(1, {"source": "meta"}, 240.0), (None, None, 100.0), (2, {}, 50.0)],
            [(1, "Meta Jul"), (2, "Google Ads")],
        ]
        captured = []
        db = AsyncMock()

        async def fake_execute(stmt, *args, **kwargs):
            captured.append(str(stmt))
            r = MagicMock()
            rows = results.pop(0)
            r.one.return_value = rows
            r.all.return_value = rows
            r.scalar.return_value = rows
            return r

        db.execute.side_effect = fake_execute
        out = await _delivery_campaign_effect(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert set(out) == {"by_campaign", "by_channel"}
        # excluye cancelados en el WHERE (status != :status_1, bound param de SQLAlchemy)
        assert "status != :status_1" in captured[0]
        # orden desc por GMV: Meta Jul (240) → Sin campaña (100) → Google Ads (50)
        assert [c["campaign_name"] for c in out["by_campaign"]] == ["Meta Jul", "Sin campaña", "Google Ads"]
        assert out["by_campaign"][0] == {
            "campaign_id": 1, "campaign_name": "Meta Jul",
            "orders": 1, "gmv": 240.0, "aov": 240.0,
        }
        assert out["by_campaign"][1] == {
            "campaign_id": None, "campaign_name": "Sin campaña",
            "orders": 1, "gmv": 100.0, "aov": 100.0,
        }
        # utm None y {} → "directo" (2 pedidos)
        assert [c["source"] for c in out["by_channel"]] == ["meta", "directo"]
        assert out["by_channel"][1] == {"source": "directo", "orders": 2, "gmv": 150.0, "aov": 75.0}


# ═══════════════════════════════════════════════════════════════
# CA-M5 — CSV ampliado
# ═══════════════════════════════════════════════════════════════

class TestCsvMejoras:
    def test_incluye_secciones_nuevas(self):
        """Las 4 secciones nuevas + las 12 originales (CA-M5)."""
        csv_text = render_owner_csv(_sample_dashboard_con_mejoras())
        for section in ("kpis", "sales_by_hour", "sales_by_weekday", "channels",
                        "top_platos", "payments", "delivery_funnel", "delivery_zones",
                        "campaigns", "comparison", "margins", "alerts",
                        "top_waiters", "cancellation_rate", "avg_ticket_by",
                        "delivery_campaign_effect"):
            assert f"# {section}" in csv_text
        assert "1,Dueño,5,400.0,80.0" in csv_text
        assert "2,25,8.0" in csv_text
        assert "cliente no vino,2" in csv_text
        assert "dine_in,265.0" in csv_text
        assert "morning,100.0,1" in csv_text
        assert "Sin campaña,3,100.0,33.33" in csv_text
        assert "directo,3,100.0,33.33" in csv_text


# ═══════════════════════════════════════════════════════════════
# CA-M6 — PDF ampliado
# ═══════════════════════════════════════════════════════════════

class TestPdfMejoras:
    def test_incluye_secciones_nuevas(self):
        """Secciones 10-12 presentes en el PDF (CA-M6)."""
        out = render_owner_pdf(_sample_dashboard_con_mejoras())
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")
        for clave in ("10. Top meseros", "11. Anulaciones", "12. Ticket por turno",
                      "Campaña vs sin campaña"):
            assert _pdf_contains(out, clave), f"sección no encontrada: {clave!r}"

    def test_sin_datos_no_explota(self):
        out = render_owner_pdf(_sample_dashboard())
        assert out.startswith(b"%PDF")


# ═══════════════════════════════════════════════════════════════
# Wire — endpoint completo con los 4 bloques nuevos
# ═══════════════════════════════════════════════════════════════

class TestWireContratoCompleto:
    def test_response_contiene_ca_m1_m4(self):
        """GET /api/v1/dashboard/owner → las 4 keys nuevas con tipos correctos."""
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
            [(12, 1, "dine_in", 320.0), (13, 2, "delivery", 100.0)],  # _heatmap
            [("dine_in", 300.0), ("delivery", 40.0)],    # _margins
            (2000.0, 50),              # _comparison current base
            [("delivery", 20), ("dine_in", 25), ("takeout", 5)],  # _comparison current canales
            (1800.0, 45),              # _comparison previous base
            [("delivery", 15)],       # _comparison previous canales
            [(date(2026, 8, 1), 100.0, 3), (date(2026, 8, 2), 100.0, 3)],  # _alerts diario
            [(date(2026, 8, 1), 1), (date(2026, 8, 2), 1)],  # _alerts delivery diario
            # Iteración 3 — CA-M1..M4
            [(1, "Dueño", 5, 400.0), (2, "Mesero", 3, 200.0)],  # _top_waiters rows
            20,                         # _top_waiters total_sales
            2,                          # _cancellation_rate voided
            25,                         # _cancellation_rate total
            [("cliente no vino", 2)],   # _cancellation_rate reasons
            [("dine_in", 320.0, 15), ("delivery", 100.0, 2)],  # _avg_ticket_by canales
            [(time(12, 0), 320.0), (time(20, 0), 100.0)],      # _avg_ticket_by turnos
            [(1, {"source": "meta"}, 240.0), (None, None, 100.0)],  # _dce rows
            [(1, "Meta Jul")],          # _dce camp names
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
            client = _client_with_db(db)
            r = client.get("/api/v1/dashboard/owner")
        assert r.status_code == 200
        body = r.json()
        for key in ("top_waiters", "cancellation_rate", "avg_ticket_by", "delivery_campaign_effect"):
            assert key in body, f"key faltante: {key}"

        tw = body["top_waiters"]
        assert set(tw) == {"rows", "total_sales"}
        assert isinstance(tw["rows"], list)
        assert tw["total_sales"] == 20
        assert tw["rows"][0] == {
            "user_id": 1, "name": "Dueño", "sales_count": 5,
            "total": 400.0, "avg_ticket": 80.0,
        }

        cr = body["cancellation_rate"]
        assert set(cr) == {"voided_count", "total_count", "rate_pct", "top_reasons"}
        assert cr["voided_count"] == 2 and cr["total_count"] == 25
        assert cr["rate_pct"] == 8.0
        assert cr["top_reasons"] == [{"reason": "cliente no vino", "count": 2}]

        atb = body["avg_ticket_by"]
        assert set(atb) == {"channel", "shift"}
        assert len(atb["channel"]) == 2
        assert [s["shift"] for s in atb["shift"]] == ["morning", "afternoon", "evening"]
        # time(12,0) → afternoon; time(20,0) → evening
        assert atb["shift"][1] == {"shift": "afternoon", "ticket": 320.0, "orders": 1}
        assert atb["shift"][2] == {"shift": "evening", "ticket": 100.0, "orders": 1}

        dce = body["delivery_campaign_effect"]
        assert set(dce) == {"by_campaign", "by_channel"}
        assert dce["by_campaign"][0]["campaign_name"] == "Meta Jul"
        assert dce["by_campaign"][1]["campaign_name"] == "Sin campaña"
        assert dce["by_channel"][0]["source"] == "meta"
        assert dce["by_channel"][1] == {"source": "directo", "orders": 1, "gmv": 100.0, "aov": 100.0}
