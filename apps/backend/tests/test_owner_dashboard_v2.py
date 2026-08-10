"""
Tests del Panel del Dueño V2 (Spec 04 §3.1-V2) — bloques CA10-CA14.

Cubre: heatmap (CA10), márgenes por canal con costeo (CA11), comparativa
semana vs semana (CA12), export CSV (CA13) y alertas vs promedio 7 días (CA14).

Patrón de mocks: AsyncSession con side_effects sobre db.execute (mismo patrón
que test_owner_dashboard.py / test_delivery).
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.user import User
from app.services.owner_dashboard_service import (
    ALERT_METRICS,
    COSTABLE_NOTE,
    _alerts,
    _avg_metrics,
    _comparison,
    _heatmap,
    _margins_by_channel,
    _period_summary,
    render_owner_csv,
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


def _capture_db(rows):
    """AsyncSession mock que captura el statement SQL y devuelve rows en .all()."""
    captured = {}
    db = AsyncMock()

    async def fake_execute(stmt, *args, **kwargs):
        captured["stmt"] = stmt
        r = MagicMock()
        r.one.return_value = rows
        r.all.return_value = rows
        r.scalar.return_value = rows
        return r

    db.execute.side_effect = fake_execute
    return db, captured


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
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_user, None)
    c = TestClient(app)
    headers = {"X-Tenant-ID": "1"}
    r = getattr(c, method)(path, headers=headers)
    assert r.status_code == 401


def _sample_dashboard() -> dict:
    """Payload de ejemplo del contrato completo (V1 + V2) para export/render."""
    return {
        "period": {"date_from": "2026-08-01", "date_to": "2026-08-10"},
        "kpis": {
            "sales_total": 4850.5, "orders_count": 42, "avg_ticket": 115.5,
            "orders_delivery": 15, "orders_dine_in": 20, "orders_takeout": 7,
            "delivery_pct": 35.7, "kitchen_open": 3, "delivery_in_route": 2,
        },
        "sales_by_hour": [
            {"hour": 12, "dine_in": 320.0, "delivery": 0.0},
            {"hour": 13, "dine_in": 0.0, "delivery": 100.0},
        ],
        "sales_by_weekday": [{"weekday": 1, "total": 850.0}],
        "channels": {"dine_in": 2450.0, "takeout": 620.0, "delivery": 1780.5},
        "top_platos": [{"name": "Ceviche Clásico", "qty": 15, "total": 375.0}],
        "payments": {"yape": 500.0, "cash": 400.0},
        "delivery": {
            "orders_by_zone": [{"zone": "Zona 1", "orders": 12}],
            "funnel": {
                "received": 18, "preparing": 3, "ready": 2,
                "out_for_delivery": 2, "delivered": 9, "cancelled": 2,
            },
        },
        "campaigns": [{
            "campaign_id": 1, "name": "Meta Jul", "channel": "meta",
            "spend": 100, "orders": 8, "gmv": 240, "aov": 30, "roas": 2.4,
        }],
        "heatmap": {"dine_in": {"rows": []}, "delivery": {"rows": []}},
        "margins": {
            "by_channel": [
                {"channel": "dine_in", "revenue": 2450.0, "cost": 980.0, "margin_pct": 60.0},
            ],
            "costable_note": COSTABLE_NOTE,
        },
        "comparison": {
            "current": {"sales_total": 4850.5, "orders_count": 42, "avg_ticket": 115.5, "delivery_pct": 35.7},
            "previous": {"sales_total": 4100.0, "orders_count": 38, "avg_ticket": 107.9, "delivery_pct": 31.2},
            "deltas": {
                "sales_total_pct": 18.3, "orders_count_pct": 10.5,
                "avg_ticket_pct": 7.0, "delivery_pct_delta": 4.5,
            },
        },
        "alerts": [
            {"severity": "red", "metric": "sales_total", "message": "Hoy Ventas -50% vs promedio últimos 7 días"},
        ],
    }


# ═══════════════════════════════════════════════════════════════
# CA10 — Heatmap hora×día por canal
# ═══════════════════════════════════════════════════════════════

class TestHeatmap:
    @pytest.mark.asyncio
    async def test_rows_completos_24x7_con_ceros(self):
        """Hasta 24×7=168 rows por canal, celdas sin ventas con total 0 (CA10)."""
        db = _make_db([(0, 1, "dine_in", 100.0)])
        out = await _heatmap(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert set(out) == {"dine_in", "delivery"}
        assert len(out["dine_in"]["rows"]) == 24 * 7
        assert len(out["delivery"]["rows"]) == 24 * 7
        # orden hora-mayor: índice = hora*7 + (weekday-1)
        assert out["dine_in"]["rows"][0] == {"hour": 0, "weekday": 1, "total": 100.0}
        assert out["dine_in"]["rows"][167] == {"hour": 23, "weekday": 7, "total": 0.0}
        assert out["delivery"]["rows"][0] == {"hour": 0, "weekday": 1, "total": 0.0}
        # todos los weekdays/horas válidos
        cells = {(r["hour"], r["weekday"]) for r in out["dine_in"]["rows"]}
        assert cells == {(h, d) for h in range(24) for d in range(1, 8)}

    @pytest.mark.asyncio
    async def test_takeout_suma_a_dine_in(self):
        """takeout suma a dine_in (convención V1); delivery queda separado (CA10)."""
        db = _make_db([
            (12, 3, "takeout", 50.0),
            (12, 3, "dine_in", 100.0),
            (12, 3, "delivery", 30.0),
        ])
        out = await _heatmap(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        idx = 12 * 7 + (3 - 1)  # hour=12, weekday=3
        assert out["dine_in"]["rows"][idx] == {"hour": 12, "weekday": 3, "total": 150.0}
        assert out["delivery"]["rows"][idx] == {"hour": 12, "weekday": 3, "total": 30.0}

    @pytest.mark.asyncio
    async def test_excluye_ventas_anuladas(self):
        """El query filtra is_voided=False (consistente con CA2)."""
        db, captured = _capture_db([])
        await _heatmap(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert "is_voided" in str(captured["stmt"])


# ═══════════════════════════════════════════════════════════════
# CA11 — Margen por canal con costeo
# ═══════════════════════════════════════════════════════════════

class TestMargins:
    @pytest.mark.asyncio
    async def test_costeo_por_receta(self):
        """Costo = Σ cantidad × average_cost vía recetas; margen a 1 decimal (CA11)."""
        channels = {"dine_in": 2450.0, "takeout": 620.0, "delivery": 1780.5}
        db = _make_db([("dine_in", 980.0), ("delivery", 890.25)])
        out = await _margins_by_channel(db, 1, date(2026, 8, 1), date(2026, 8, 10), channels)
        assert [b["channel"] for b in out["by_channel"]] == ["dine_in", "takeout", "delivery"]
        assert out["by_channel"][0] == {"channel": "dine_in", "revenue": 2450.0, "cost": 980.0, "margin_pct": 60.0}
        assert out["by_channel"][2] == {"channel": "delivery", "revenue": 1780.5, "cost": 890.25, "margin_pct": 50.0}
        assert out["costable_note"] == COSTABLE_NOTE

    @pytest.mark.asyncio
    async def test_canal_sin_receta_no_aporta_costo(self):
        """R2: ventas sin receta no aportan costo → margen 100% (parcial, con nota)."""
        channels = {"dine_in": 0.0, "takeout": 620.0, "delivery": 0.0}
        db = _make_db([])  # sin costos: ningún ítem con receta
        out = await _margins_by_channel(db, 1, date(2026, 8, 1), date(2026, 8, 10), channels)
        takeout = out["by_channel"][1]
        assert takeout["revenue"] == 620.0
        assert takeout["cost"] == 0.0
        assert takeout["margin_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_revenue_cero_margin_cero(self):
        """revenue=0 → cost 0.0 y margin_pct 0.0 (contrato CA11)."""
        db = _make_db([])
        out = await _margins_by_channel(db, 1, date(2026, 8, 1), date(2026, 8, 10), {})
        for b in out["by_channel"]:
            assert b == {"channel": b["channel"], "revenue": 0.0, "cost": 0.0, "margin_pct": 0.0}

    @pytest.mark.asyncio
    async def test_excluye_ventas_anuladas(self):
        db, captured = _capture_db([])
        await _margins_by_channel(db, 1, date(2026, 8, 1), date(2026, 8, 10), {})
        assert "is_voided" in str(captured["stmt"])


# ═══════════════════════════════════════════════════════════════
# CA12 — Comparativa semana vs semana
# ═══════════════════════════════════════════════════════════════

class TestComparison:
    @pytest.mark.asyncio
    async def test_period_summary(self):
        """Resumen base de la comparativa (mismas fórmulas que _kpis, sin en-vivo)."""
        db = _make_db(
            (4850.5, 42),
            [("delivery", 15), ("dine_in", 20), ("takeout", 7)],
        )
        out = await _period_summary(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out == {"sales_total": 4850.5, "orders_count": 42,
                       "avg_ticket": 115.49, "delivery_pct": 35.7}

    @pytest.mark.asyncio
    async def test_deltas_correctos(self):
        """Deltas *_pct a 1 decimal; delivery_pct_delta en puntos (CA12)."""
        db = _make_db(
            (4850.5, 42),
            [("delivery", 15), ("dine_in", 20), ("takeout", 7)],
            (4100.0, 38),
            [("delivery", 12)],
        )
        out = await _comparison(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        assert out["current"] == {"sales_total": 4850.5, "orders_count": 42,
                                  "avg_ticket": 115.49, "delivery_pct": 35.7}
        assert out["previous"] == {"sales_total": 4100.0, "orders_count": 38,
                                   "avg_ticket": 107.89, "delivery_pct": 31.6}
        d = out["deltas"]
        assert d["sales_total_pct"] == round((4850.5 - 4100.0) / 4100.0 * 100, 1)   # 18.3
        assert d["orders_count_pct"] == round((42 - 38) / 38 * 100, 1)              # 10.5
        assert d["avg_ticket_pct"] == round((115.49 - 107.89) / 107.89 * 100, 1)    # 7.0
        assert d["delivery_pct_delta"] == round(35.7 - 31.6, 1)                     # 4.1 pts

    @pytest.mark.asyncio
    async def test_previous_cero_devuelve_null(self):
        """previous=0 → *_pct null (sin división por cero); delta de pct se mantiene."""
        db = _make_db(
            (1000.0, 10),
            [("delivery", 5)],
            (0.0, 0),
            [],
        )
        out = await _comparison(db, 1, date(2026, 8, 1), date(2026, 8, 10))
        d = out["deltas"]
        assert d["sales_total_pct"] is None
        assert d["orders_count_pct"] is None
        assert d["avg_ticket_pct"] is None
        assert d["delivery_pct_delta"] == 50.0  # 50.0 - 0.0

    @pytest.mark.asyncio
    async def test_periodo_previo_igual_longitud(self):
        """El período previo mide lo mismo que el actual, inmediatamente anterior."""
        db = _make_db(
            (100.0, 2),      # current [2026-08-05, 2026-08-06] → 2 días
            [("delivery", 1)],
            (50.0, 1),       # previous [2026-08-03, 2026-08-04] → 2 días
            [("delivery", 0)],
        )
        out = await _comparison(db, 1, date(2026, 8, 5), date(2026, 8, 6))
        # La longitud del período previo es la misma que la actual
        assert out["previous"]["orders_count"] == 1
        assert out["deltas"]["sales_total_pct"] == 100.0


# ═══════════════════════════════════════════════════════════════
# CA14 — Alertas vs promedio 7 días
# ═══════════════════════════════════════════════════════════════

def _alerts_db(current_total: float, prev_total: float = 100.0):
    """Ventana: 7 días previos con prev_total/2 pedidos + día actual con current_total/2."""
    prev_days = [date(2026, 8, 3) + timedelta(days=i) for i in range(7)]
    daily = [(d, prev_total, 2) for d in prev_days] + [(date(2026, 8, 10), current_total, 2)]
    deliv = [(d, 1) for d in prev_days] + [(date(2026, 8, 10), 1)]
    return _make_db(daily, deliv)


class TestAlerts:
    @pytest.mark.asyncio
    async def test_red_yellow_thresholds(self):
        """-50% → red; -15% → yellow; sin desviación → sin alerta (CA14)."""
        # -50% (red)
        out = await _alerts(_alerts_db(50.0), 1, date(2026, 8, 10), date(2026, 8, 10))
        by_metric = {a["metric"]: a for a in out}
        assert by_metric["sales_total"]["severity"] == "red"
        assert by_metric["avg_ticket"]["severity"] == "red"
        assert "-50%" in by_metric["sales_total"]["message"]
        assert by_metric["sales_total"]["message"].startswith("Hoy")
        assert set(ALERT_METRICS) == {"sales_total", "orders_count", "avg_ticket", "delivery_pct"}
        assert "orders_count" not in by_metric   # 0% de desviación → sin alerta

        # -15% (yellow)
        out = await _alerts(_alerts_db(85.0), 1, date(2026, 8, 10), date(2026, 8, 10))
        assert all(a["severity"] == "yellow" for a in out)
        assert {a["metric"] for a in out} == {"sales_total", "avg_ticket"}

        # 0% (sin desviación)
        out = await _alerts(_alerts_db(100.0), 1, date(2026, 8, 10), date(2026, 8, 10))
        assert out == []

    @pytest.mark.asyncio
    async def test_sin_data_devuelve_lista_vacia(self):
        """Sin data previa → alerts [] (nunca null)."""
        db = _make_db([], [])
        out = await _alerts(db, 1, date(2026, 8, 10), date(2026, 8, 10))
        assert out == []

    @pytest.mark.asyncio
    async def test_periodo_multidia_promedio_diario(self):
        """Período multi-día compara promedio diario del período vs 7 días previos."""
        prev_days = [date(2026, 7, 29) + timedelta(days=i) for i in range(7)]  # Jul 29 - Ago 4
        period_days = [date(2026, 8, 5) + timedelta(days=i) for i in range(6)]  # Ago 5-10
        daily = [(d, 100.0, 2) for d in prev_days] + [(d, 50.0, 2) for d in period_days]
        deliv = [(d, 1) for d in prev_days + period_days]
        db = _make_db(daily, deliv)
        out = await _alerts(db, 1, date(2026, 8, 5), date(2026, 8, 10))
        by_metric = {a["metric"]: a for a in out}
        assert by_metric["sales_total"]["severity"] == "red"   # promedio diario 50 vs 100
        assert by_metric["sales_total"]["message"].startswith("Período")

    def test_avg_metrics_ignora_dias_sin_pedidos(self):
        """avg_ticket/delivery_pct solo promedian días con pedidos."""
        daily = {
            date(2026, 8, 1): {"sales_total": 100.0, "orders_count": 2, "avg_ticket": 50.0, "delivery_pct": 50.0},
            date(2026, 8, 2): {"sales_total": 0.0, "orders_count": 0, "avg_ticket": 0.0, "delivery_pct": 0.0},
        }
        days = [date(2026, 8, 1), date(2026, 8, 2)]
        avg = _avg_metrics(days, daily)
        assert avg["sales_total"] == 50.0      # (100 + 0) / 2
        assert avg["orders_count"] == 1.0      # (2 + 0) / 2
        assert avg["avg_ticket"] == 50.0       # solo el día con pedidos
        assert avg["delivery_pct"] == 50.0     # solo el día con pedidos


# ═══════════════════════════════════════════════════════════════
# CA13 — Export CSV
# ═══════════════════════════════════════════════════════════════

class TestRenderCsv:
    def test_todas_las_secciones(self):
        """El CSV contiene las 12 secciones con cabeceras descriptivas (CA13)."""
        csv_text = render_owner_csv(_sample_dashboard())
        for section in ("kpis", "sales_by_hour", "sales_by_weekday", "channels",
                        "top_platos", "payments", "delivery_funnel", "delivery_zones",
                        "campaigns", "comparison", "margins", "alerts"):
            assert f"# {section}" in csv_text
        assert "metric,value" in csv_text
        assert "hour,dine_in,delivery" in csv_text
        assert "weekday,total" in csv_text
        assert "channel,total" in csv_text
        assert "name,qty,total" in csv_text
        assert "method,amount" in csv_text
        assert "status,orders" in csv_text
        assert "zone,orders" in csv_text
        assert "channel,revenue,cost,margin_pct" in csv_text
        assert "severity,metric,message" in csv_text
        assert f"# costable_note: {COSTABLE_NOTE}" in csv_text

    def test_datos_por_seccion(self):
        csv_text = render_owner_csv(_sample_dashboard())
        assert "sales_total,4850.5" in csv_text
        assert "12,320.0,0.0" in csv_text          # sales_by_hour: hora,dine_in,delivery
        assert "Ceviche Clásico,15,375.0" in csv_text
        assert "delivered,9" in csv_text            # delivery_funnel
        assert "Zona 1,12" in csv_text              # delivery_zones
        assert "Meta Jul,meta,100,8,240,30,2.4" in csv_text
        assert "sales_total,4850.5,4100.0,18.3" in csv_text   # comparison
        assert "dine_in,2450.0,980.0,60.0" in csv_text         # margins
        assert "red,sales_total,Hoy Ventas -50% vs promedio últimos 7 días" in csv_text


class TestExportEndpoint:
    def test_requiere_auth(self):
        _assert_protected("get", "/api/v1/dashboard/owner/export")

    def test_format_invalido_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner/export", params={"format": "xlsx"})
        assert r.status_code == 422
        assert "csv" in r.json()["detail"]

    def test_export_csv_ok(self, client):
        with patch("app.services.owner_dashboard_service.get_owner_dashboard",
                   new=AsyncMock(return_value=_sample_dashboard())):
            r = client.get("/api/v1/dashboard/owner/export", params={"format": "csv"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        disposition = r.headers["content-disposition"]
        assert "attachment" in disposition
        # `filename` plano en ASCII + `filename*` con el nombre UTF-8 (ñ)
        assert "panel_dueno_20260810.csv" in disposition
        assert "filename*=UTF-8''panel_due%C3%B1o_20260810.csv" in disposition
        assert "# kpis" in r.text
        assert "# margins" in r.text
        assert "# alerts" in r.text

    def test_export_fecha_invalida_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner/export",
                       params={"format": "csv", "date_from": "mal"})
        assert r.status_code == 422
        assert "Fecha inválida" in r.json()["detail"]
