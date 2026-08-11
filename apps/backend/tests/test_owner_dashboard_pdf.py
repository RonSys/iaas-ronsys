"""
Tests del Panel del Dueño — Export PDF (Spec 04 §3.1-V2 CA13-b).

Cubre: render_owner_pdf (9 secciones, reportlab platypus) y el router
(format=pdf → application/pdf; format inválido → 422; regresión CSV).

Patrón de mocks: reutiliza _sample_dashboard() y el fixture `client` de
test_owner_dashboard_v2 (mismo patrón TestClient + overrides).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.user import User
from app.services.owner_dashboard_service import render_owner_pdf
from tests.test_owner_dashboard_v2 import _sample_dashboard

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


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

# Chars en WinAnsi pero fuera de Latin-1 (reportlab los escribe como su byte WinAnsi)
_WINANSI_EXTRA = {"—": "\x97", "•": "\x95", "–": "\x96", "…": "\x85"}


def _winansi_escaped(text: str) -> str:
    """Replica el escape de reportlab para fuentes estándar: bytes >127 → \\ooo."""
    out: list[str] = []
    for c in text:
        ch = _WINANSI_EXTRA.get(c)
        if ch is None:
            try:
                ch = c.encode("latin-1").decode("latin-1")
            except UnicodeEncodeError:
                ch = "?"  # fuera de WinAnsi: no buscable en bytes
        b = ord(ch)
        if b > 127 or b in (40, 41, 92):  # ( ) \ también se escapan
            out.append(f"\\{b:03o}")
        else:
            out.append(ch)
    return "".join(out)


def _pdf_contains(pdf: bytes, text: str) -> bool:
    """True si `text` aparece en los bytes del PDF (tolerante a escapes de reportlab)."""
    if text.encode("utf-8") in pdf:
        return True
    return _winansi_escaped(text).encode("utf-8") in pdf


# ═══════════════════════════════════════════════════════════════
# CA13-b — render_owner_pdf
# ═══════════════════════════════════════════════════════════════

class TestRenderPdf:
    def test_devuelve_bytes_pdf_validos(self):
        """Estructura válida: cabecera %PDF y /Type /Catalog."""
        out = render_owner_pdf(_sample_dashboard())
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")
        assert b"/Type /Catalog" in out
        assert len(out) > 500

    def test_contiene_las_9_secciones(self):
        """Las 9 secciones del contrato CA13-b presentes en el PDF."""
        out = render_owner_pdf(_sample_dashboard())
        for clave in (
            "Panel del Dueño", "KPIs", "Comparativa", "Márgenes",
            "Top platos", "Canales", "Ventas por hora", "Delivery",
            "Campañas", "Alertas",
        ):
            assert _pdf_contains(out, clave), f"sección no encontrada: {clave!r}"

    def test_encabezado_periodo_y_fecha(self):
        """Encabezado: título, período efectivo y fecha de generación."""
        out = render_owner_pdf(_sample_dashboard())
        assert _pdf_contains(out, "Panel del Dueño")
        assert _pdf_contains(out, "2026-08-01")
        assert _pdf_contains(out, "2026-08-10")
        assert _pdf_contains(out, "Fecha de generación")

    def test_contenido_por_seccion(self):
        """Spot-checks de data real del contrato en las secciones 2-8."""
        out = render_owner_pdf(_sample_dashboard())
        # KPIs
        assert _pdf_contains(out, "S/ 4,850.50")
        assert _pdf_contains(out, "42")
        # Comparativa (deltas ▲ + valor)
        assert _pdf_contains(out, "18.3")
        # Márgenes
        assert _pdf_contains(out, "S/ 980.00")
        assert _pdf_contains(out, "60.0%")
        # Top platos
        assert _pdf_contains(out, "Ceviche Clásico")
        # Canales + pagos
        assert _pdf_contains(out, "Yape")
        # Ventas por hora
        assert _pdf_contains(out, "12:00")
        # Delivery + campañas
        assert _pdf_contains(out, "Zona 1")
        assert _pdf_contains(out, "Entregados")
        assert _pdf_contains(out, "Meta Jul")
        assert _pdf_contains(out, "ROAS")

    def test_deltas_nulos_muestran_guion(self):
        """Comparativa con delta None → '—' (contrato: ▲▼ solo si no nulos)."""
        data = _sample_dashboard()
        data["comparison"]["deltas"]["sales_total_pct"] = None
        out = render_owner_pdf(data)
        assert _pdf_contains(out, "—")

    def test_alertas_vacias_sin_alertas(self):
        """alerts=[] → 'Sin alertas en el período' (nunca null)."""
        data = _sample_dashboard()
        data["alerts"] = []
        out = render_owner_pdf(data)
        assert _pdf_contains(out, "Sin alertas en el período")

    def test_alertas_con_severidad_roja_y_ambar(self):
        """Alertas rojas/ámbar con severidad legible (⚠️ + Roja/Ámbar)."""
        data = _sample_dashboard()
        data["alerts"] = [
            {"severity": "red", "metric": "sales_total",
             "message": "Hoy Ventas -50% vs promedio últimos 7 días"},
            {"severity": "yellow", "metric": "avg_ticket",
             "message": "Hoy Ticket promedio -12% vs promedio últimos 7 días"},
        ]
        out = render_owner_pdf(data)
        assert _pdf_contains(out, "Roja")
        assert _pdf_contains(out, "Ámbar")
        assert _pdf_contains(out, "sales_total")
        assert _pdf_contains(out, "-50%")

    def test_sin_datos_no_explota(self):
        """Dashboard vacío (lists/dicts vacíos) → PDF válido con placeholder."""
        data = _sample_dashboard()
        data["sales_by_hour"] = []
        data["top_platos"] = []
        data["campaigns"] = []
        data["delivery"]["orders_by_zone"] = []
        data["channels"] = {}
        data["payments"] = {}
        data["alerts"] = []
        out = render_owner_pdf(data)
        assert out.startswith(b"%PDF")
        assert _pdf_contains(out, "Sin datos en el período")
        assert _pdf_contains(out, "Sin alertas en el período")


# ═══════════════════════════════════════════════════════════════
# CA13-b — Router /owner/export?format=pdf
# ═══════════════════════════════════════════════════════════════

class TestExportPdfEndpoint:
    def test_requiere_auth(self):
        _assert_protected("get", "/api/v1/dashboard/owner/export")

    def test_format_pdf_ok(self, client):
        with patch("app.services.owner_dashboard_service.get_owner_dashboard",
                   new=AsyncMock(return_value=_sample_dashboard())):
            r = client.get("/api/v1/dashboard/owner/export", params={"format": "pdf"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        disposition = r.headers["content-disposition"]
        assert "attachment" in disposition
        assert "panel_dueno_20260810.pdf" in disposition
        assert "filename*=UTF-8''panel_due%C3%B1o_20260810.pdf" in disposition

    def test_format_invalido_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner/export", params={"format": "xlsx"})
        assert r.status_code == 422
        assert "csv" in r.json()["detail"]

    def test_format_csv_sigue_funcionando(self, client):
        """Regresión CA13: format=csv → text/csv con las secciones CSV."""
        with patch("app.services.owner_dashboard_service.get_owner_dashboard",
                   new=AsyncMock(return_value=_sample_dashboard())):
            r = client.get("/api/v1/dashboard/owner/export", params={"format": "csv"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "# kpis" in r.text
        assert "# alerts" in r.text

    def test_fecha_invalida_devuelve_422(self, client):
        r = client.get("/api/v1/dashboard/owner/export",
                       params={"format": "pdf", "date_from": "mal"})
        assert r.status_code == 422
        assert "Fecha inválida" in r.json()["detail"]
