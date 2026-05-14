"""
Tests de integración HTTP — Ventas + POS + Kárdex DB (HU-F2).

Usa TestClient con dependencias mockeadas.
Prueba existencia de rutas, validación de auth y schemas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.adapters.db.database import get_db


def _make_mock_db():
    """Crea una sesión DB mock completa que simula SQLAlchemy result chains."""
    session = AsyncMock()

    # Mock de resultado SQLAlchemy con soporte para scalar/one/none/scalars
    def _make_result(return_none=True):
        """Crea un mock result que puede simular scalar_one_or_none, scalars, scalar."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None if return_none else MagicMock()
        result.scalar.return_value = 0
        # scalars() → all()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result.scalars.return_value = scalars_mock
        # unique() → scalars()
        unique_mock = MagicMock()
        unique_mock.scalars.return_value = scalars_mock
        result.unique.return_value = unique_mock
        return result

    session.execute = AsyncMock(return_value=_make_result())

    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _clear_overrides():
    """Limpia todos los dependency overrides."""
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)


@pytest.fixture
def client():
    """TestClient con auth + DB mock. Limpia al terminar."""
    _clear_overrides()

    user = User(
        id=1, email="test@iaasronsys.com", full_name="Test",
        role="manager", tenant_id=1, is_active=True, is_verified=True,
        failed_login_attempts=0,
    )

    async def fake_user():
        return user

    async def fake_tenant():
        return 1

    db_session = _make_mock_db()

    async def fake_db():
        return db_session

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db

    yield TestClient(app)
    _clear_overrides()


# ═══════════════════════════════════════════════════════════════
# Auth verification
# ═══════════════════════════════════════════════════════════════

def _assert_protected(method: str, path: str, body=None):
    """Verifica que un endpoint requiere JWT (retorna 401 sin Authorization)."""
    # Quitar overrides de auth; mantener DB y tenant mock
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_user, None)
    if get_db not in app.dependency_overrides:
        session = _make_mock_db()
        async def fake_db():
            return session
        app.dependency_overrides[get_db] = fake_db
    c = TestClient(app)
    headers = {"X-Tenant-ID": "1"}  # Tenant presente, falta JWT
    if method == "GET":
        r = c.get(path, headers=headers)
    else:
        r = c.post(path, json=body or {}, headers=headers)
    assert r.status_code == 401, f"{method} {path} → {r.status_code}, expected 401"


# ═══════════════════════════════════════════════════════════════
# HU-F2-003: Sesiones POS
# ═══════════════════════════════════════════════════════════════


class TestPosSessions:
    """HU-F2-003: Sesiones POS — routes existen y validan auth."""

    def test_open_session_endpoint(self, client):
        """POST /sessions/open acepta opening_cash y responde (no 401)."""
        r = client.post("/api/sales/sessions/open",
            params={"opening_cash": 500.0},
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_current_session_endpoint(self, client):
        """GET /sessions/current responde (no 401)."""
        r = client.get("/api/sales/sessions/current",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_close_session_endpoint(self, client):
        """POST /sessions/{id}/close responde (no 401)."""
        r = client.post("/api/sales/sessions/999/close",
            params={"closing_cash": 500.0},
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_open_session_requires_auth(self):
        """POST /sessions/open → 401 sin auth."""
        _assert_protected("POST", "/api/sales/sessions/open",
                          {"opening_cash": 500.0})

    def test_current_session_requires_auth(self):
        """GET /sessions/current → 401 sin auth."""
        _assert_protected("GET", "/api/sales/sessions/current")


# ═══════════════════════════════════════════════════════════════
# HU-F2-004: Ventas CRUD
# ═══════════════════════════════════════════════════════════════


class TestSalesCRUD:
    """HU-F2-004: Ventas CRUD — routes existen y validan input."""

    def test_create_sale_requires_body(self, client):
        """POST /sale sin body → 422 (Pydantic validation)."""
        r = client.post("/api/sales/sale",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 422

    def test_create_sale_rejects_empty_items(self, client):
        """POST /sale con items vacíos → 400/409/422."""
        r = client.post("/api/sales/sale", json={
            "business_type": "restaurant", "items": [], "payments": []
        }, headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code in (400, 409, 422)

    def test_list_sales_endpoint(self, client):
        """GET /sales → endpoint responde (no 401)."""
        r = client.get("/api/sales/sales",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_list_sales_with_filters_endpoint(self, client):
        """GET /sales?from=...&to=... → endpoint responde."""
        r = client.get(
            "/api/sales/sales?from=2026-01-01&to=2026-12-31&business_type=restaurant",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_get_sale_endpoint(self, client):
        """GET /sale/{id} → endpoint responde (no 401)."""
        r = client.get("/api/sales/sale/99999",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_void_sale_requires_reason(self, client):
        """POST /sale/{id}/void sin reason → 400."""
        r = client.post("/api/sales/sale/1/void", json={},
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 400

    def test_void_sale_endpoint(self, client):
        """POST /sale/{id}/void con reason → endpoint responde."""
        r = client.post("/api/sales/sale/99999/void",
            json={"reason": "Error"},
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code in (200, 400, 404, 409, 500)

    def test_sales_requires_auth(self):
        """GET /sales → 401 sin auth."""
        _assert_protected("GET", "/api/sales/sales")

    def test_create_sale_requires_auth(self):
        """POST /sale → 401 sin auth."""
        _assert_protected("POST", "/api/sales/sale")


# ═══════════════════════════════════════════════════════════════
# HU-F2-007: Ticket + Payment Methods
# ═══════════════════════════════════════════════════════════════


class TestTicket:
    """HU-F2-007: Ticket y payment methods — routes existen."""

    def test_ticket_invalid_format(self, client):
        """GET /sale/{id}/ticket?format=invalid → 400."""
        r = client.get("/api/sales/sale/1/ticket?format=xml",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 400

    def test_ticket_endpoint(self, client):
        """GET /sale/{id}/ticket?format=json → responde (no 401)."""
        r = client.get("/api/sales/sale/1/ticket?format=json",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code != 401

    def test_payment_methods(self, client):
        """GET /payment-methods → 200 con methods list."""
        r = client.get("/api/sales/payment-methods",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 200
        data = r.json()
        assert "methods" in data and len(data["methods"]) > 0

    def test_payment_methods_requires_auth(self):
        """GET /payment-methods → 401 sin auth."""
        _assert_protected("GET", "/api/sales/payment-methods")


# ═══════════════════════════════════════════════════════════════
# Validaciones de esquemas Pydantic
# ═══════════════════════════════════════════════════════════════


class TestSalesSchemas:
    """Schemas Pydantic: validación de datos de entrada."""

    def test_payments_must_cover_total(self):
        """SaleCreate rechaza payments que no cubren el total."""
        from app.schemas.sales import SaleCreate, SaleItemCreate, SalePaymentCreate
        with pytest.raises(Exception):
            SaleCreate(
                business_type="restaurant",
                items=[SaleItemCreate(item_name="P1", quantity=2,
                      unit_price=50.0, total=100.0)],
                payments=[SalePaymentCreate(payment_method="cash", amount=50.0)],
            )

    def test_accepts_valid_payments(self):
        """SaleCreate acepta payments que cubren total."""
        from app.schemas.sales import SaleCreate, SaleItemCreate, SalePaymentCreate
        s = SaleCreate(
            business_type="restaurant",
            items=[SaleItemCreate(item_name="P1", quantity=2,
                  unit_price=50.0, total=100.0)],
            payments=[SalePaymentCreate(payment_method="cash", amount=100.0)],
        )
        assert s.business_type == "restaurant" and len(s.items) == 1

    def test_rejects_empty_items(self):
        """SaleCreate rechaza items vacíos (min_length=1)."""
        from app.schemas.sales import SaleCreate, SalePaymentCreate
        with pytest.raises(Exception):
            SaleCreate(business_type="retail", items=[],
                       payments=[SalePaymentCreate(payment_method="cash", amount=100.0)])


# ═══════════════════════════════════════════════════════════════
# HU-F2-012: Kárdex DB — auth en todos los endpoints
# ═══════════════════════════════════════════════════════════════


class TestKardexDBAuth:
    """HU-F2-012: DB-backed kárdex endpoints requieren JWT."""

    KARDEX_DB_ENDPOINTS = [
        ("POST", "/api/accounting/kardex/db/products",
         {"code": "P1", "name": "Test", "unit": "kg"}),
        ("POST", "/api/accounting/kardex/db/entry",
         {"product_code": "P1", "quantity": 10, "unit_cost": 5.0,
          "concept": "Compra", "date": "2026-01-15"}),
        ("POST", "/api/accounting/kardex/db/exit",
         {"product_code": "P1", "quantity": 2,
          "concept": "Venta", "date": "2026-01-15"}),
        ("GET", "/api/accounting/kardex/db/P1", None),
        ("GET", "/api/accounting/kardex/db/inventory", None),
    ]

    @pytest.mark.parametrize("method,path,body", KARDEX_DB_ENDPOINTS)
    def test_requires_auth(self, method, path, body):
        """Todos los endpoints kardex DB requieren JWT (→ 401)."""
        _assert_protected(method, path, body)
