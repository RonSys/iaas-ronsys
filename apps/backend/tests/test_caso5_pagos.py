"""
Tests — Caso 5: Métodos de Pago (Yape + Efectivo).

Cubre:
  - ClosePayService.pay_table() con split payments
  - Validación de montos (no cubren total)
  - Formato legacy (payment_method + amount)
  - ClosePayService.get_table_orders_status()
  - Integración HTTP endpoint GET /tables/{id}/orders/status
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.adapters.db.database import get_db
from app.services.restaurant_service import ClosePayService

# ═══════════════════════════════════════════════════════════════
# Helpers comunes
# ═══════════════════════════════════════════════════════════════

TENANT_ID = 1
TABLE_ID = 1


def _make_result(scalar_one_or_none_val=None, scalar_val=0):
    """Crea un MagicMock resultado de SQLAlchemy execute()."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_one_or_none_val
    r.scalar.return_value = scalar_val
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    r.scalars.return_value = scalars_mock
    unique_mock = MagicMock()
    unique_mock.scalars.return_value = scalars_mock
    r.unique.return_value = unique_mock
    return r


def _make_pos_session():
    """Mock de PosSession abierta."""
    s = MagicMock()
    s.id = 99
    s.tenant_id = TENANT_ID
    s.status = "open"
    return s


def _make_kitchen_order(order_id=1, status="delivered", items=None, table_id=1):
    """Mock de KitchenOrder."""
    o = MagicMock()
    o.id = order_id
    o.tenant_id = TENANT_ID
    o.table_id = table_id
    o.status = status
    o.items = items or [
        {"menu_item_id": 1, "name": "Hamburguesa", "quantity": 2,
         "unit_price": 12.0, "total": 24.0},
        {"menu_item_id": 2, "name": "Gaseosa", "quantity": 1,
         "unit_price": 5.0, "total": 5.0},
    ]
    o.notes = None
    o.ordered_at = None
    o.started_at = None
    o.completed_at = None
    return o


class _MockDBSession:
    """Sesión mock con execute async controlado.

    Simula los patrones SQLAlchemy: execute(), scalar_one_or_none(),
    scalars().all(), add(), flush() con autoincrement simulado.
    """

    def __init__(self, session=None, table=None, orders=None,
                 sale_count=0, modifiers_by_id=None):
        self._session = session
        self._table = table
        self._orders = orders
        self._sale_count = sale_count
        self._modifiers_by_id = modifiers_by_id or {}
        self._call_count = 0
        self.added_objects = []
        self._id_counters = {}

    def _table_name(self, stmt) -> str:
        """Intenta extraer el nombre de la tabla del stmt."""
        try:
            froms = stmt.froms if hasattr(stmt, 'froms') else []
            if froms:
                # Try get_final_froms first (newer SQLAlchemy)
                pass
            return str(froms[0]) if froms else ""
        except Exception:
            pass
        try:
            return str(stmt.get_final_froms()[0]) if hasattr(stmt, 'get_final_froms') else ""
        except Exception:
            return ""

    def _has_modifier_lookup(self, stmt) -> tuple[bool, any]:
        """Intenta extraer modifier id de la cláusula WHERE."""
        try:
            where = stmt._where_criteria[0]
            mid = where.right.value
            return True, mid
        except Exception:
            return False, None

    async def execute(self, stmt):
        self._call_count += 1

        # Intentar modifier lookup
        is_mod, mid = self._has_modifier_lookup(stmt)
        if is_mod and mid in self._modifiers_by_id:
            return _make_result(self._modifiers_by_id[mid])

        tbl = self._table_name(stmt)
        stmt_str = str(stmt).lower() if hasattr(stmt, '__str__') else str(stmt)

        # PosSession query
        if "pos_sessions" in tbl and "open" in stmt_str:
            return _make_result(self._session)

        # KitchenOrder query — devolver órdenes mock
        if "kitchen_orders" in tbl or "kitchenorder" in tbl:
            if self._orders is not None:
                all_mock = MagicMock()
                all_mock.all.return_value = self._orders
                r = _make_result()
                r.scalars.return_value = all_mock
                return r
            return _make_result()

        # Sale count query
        if "sales" in tbl and "count" in stmt_str:
            return _make_result(scalar_val=self._sale_count)

        # Table query
        if "tables" in tbl:
            return _make_result(self._table)

        return _make_result()

    def add(self, obj):
        self.added_objects.append(obj)

    async def flush(self):
        """Simula autoincrement: asigna ID secuencial a cada objeto nuevo."""
        for obj in self.added_objects:
            if hasattr(obj, "id") and obj.id is None:
                cls_name = type(obj).__name__
                self._id_counters[cls_name] = self._id_counters.get(cls_name, 0) + 1
                obj.id = self._id_counters[cls_name]

    async def refresh(self, obj):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def get(self, model, pk):
        return None

    async def delete(self, obj):
        pass


def _build_mock_db(session=None, table=None, orders=None,
                   sale_count=0, modifiers_by_id=None):
    return _MockDBSession(
        session=session, table=table, orders=orders,
        sale_count=sale_count, modifiers_by_id=modifiers_by_id,
    )


# ═══════════════════════════════════════════════════════════════
# Test: ClosePayService.pay_table() — Multi-payment
# ═══════════════════════════════════════════════════════════════

class TestPayTableMultiPayment:

    @pytest.mark.asyncio
    async def test_split_payment_cash_yape(self):
        """
        Escenario 5: Pago dividido — parte Yape + parte Efectivo.
        Dado total S/85.00
        Cuando se pagan S/50 Yape + S/35 Efectivo
        Entonces se registran 2 SalePayment y mesa liberada.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"
        mock_table.guests = 2
        mock_table.waiter_name = "Carlos"

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Lomo Saltado", "quantity": 1,
                 "unit_price": 35.0, "total": 35.0},
                {"menu_item_id": 2, "name": "Ceviche", "quantity": 2,
                 "unit_price": 25.0, "total": 50.0},
            ]),
        ]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        payment_data = {
            "user_id": 1,
            "payments": [
                {"method": "yape", "amount": 50.0, "reference": "Juan Pérez"},
                {"method": "cash", "amount": 35.0},
            ],
            "guest_count": 2,
            "waiter_name": "Carlos",
        }

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert result["sale_id"] is not None
        assert result["total"] == 85.0
        assert len(result["payments"]) == 2
        assert result["payments"][0]["method"] == "yape"
        assert result["payments"][0]["amount"] == 50.0
        assert result["payments"][0]["reference"] == "Juan Pérez"
        assert result["payments"][1]["method"] == "cash"
        assert result["payments"][1]["amount"] == 35.0
        assert result["payment_method"] == "yape"  # legacy: primer método
        assert result["amount_paid"] == 85.0
        assert result["change"] == 0.0

        # Verificar mesa NO liberada (libera manual)
        assert mock_table.status == "occupied"
        assert mock_table.guests == 2

    @pytest.mark.asyncio
    async def test_payment_amounts_not_covering_total_raises_400(self):
        """
        Escenario 6: Validación — montos no cubren el total.
        Total S/85, se pagan S/30 + S/30 = S/60
        → HTTPException 400.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Lomo Saltado", "quantity": 1,
                 "unit_price": 50.0, "total": 50.0},
                {"menu_item_id": 2, "name": "Ceviche", "quantity": 1,
                 "unit_price": 35.0, "total": 35.0},
            ]),
        ]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        payment_data = {
            "user_id": 1,
            "payments": [
                {"method": "yape", "amount": 30.0},
                {"method": "cash", "amount": 30.0},
            ],
        }

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ), pytest.raises(HTTPException) as exc_info:
            await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert exc_info.value.status_code == 400
        assert "no cubren el total" in exc_info.value.detail
        assert "85" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_payment_empty_list_raises_400(self):
        """payments vacío → HTTPException 400."""
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"

        orders = [_make_kitchen_order(order_id=1, status="delivered")]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        payment_data = {"user_id": 1, "payments": []}

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ), pytest.raises(HTTPException) as exc_info:
            await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert exc_info.value.status_code == 400
        assert "al menos un método de pago" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_legacy_single_payment_method_cash(self):
        """
        Escenario 3 (compatibilidad legacy):
        payment_method + amount → convertido a payments.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Pizza", "quantity": 1,
                 "unit_price": 30.0, "total": 30.0},
            ]),
        ]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        payment_data = {
            "user_id": 1,
            "payment_method": "cash",
            "amount": 30.0,
            "reference": "Pago en efectivo",
            "guest_count": 1,
        }

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert result["total"] == 30.0
        assert result["payment_method"] == "cash"
        assert result["amount_paid"] == 30.0
        assert len(result["payments"]) == 1
        assert result["payments"][0]["method"] == "cash"
        assert result["payments"][0]["amount"] == 30.0
        assert result["payments"][0]["reference"] == "Pago en efectivo"
        assert mock_table.status == "occupied"

    @pytest.mark.asyncio
    async def test_legacy_yape_with_reference(self):
        """
        Escenario 7: Yape + referencia (legacy format).
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Menu Ejecutivo", "quantity": 1,
                 "unit_price": 18.0, "total": 18.0},
            ]),
        ]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        payment_data = {
            "user_id": 1,
            "payment_method": "yape",
            "amount": 18.0,
            "reference": "OP-12345 - María López",
            "guest_count": 1,
        }

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert result["payment_method"] == "yape"
        assert result["payments"][0]["reference"] == "OP-12345 - María López"

    @pytest.mark.asyncio
    async def test_change_calculation(self):
        """
        Si se paga más del total, change > 0.
        Total S/20, se paga S/50 en efectivo (legacy) → vuelto S/30.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID
        mock_table.number = "T1"
        mock_table.status = "occupied"

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Café", "quantity": 2,
                 "unit_price": 10.0, "total": 20.0},
            ]),
        ]

        db = _build_mock_db(
            session=_make_pos_session(),
            table=mock_table,
            orders=orders,
            sale_count=0,
        )

        # Paga 50 cuando el total es 20 → vuelto 30
        payment_data = {
            "user_id": 1,
            "payment_method": "cash",
            "amount": 50.0,
        }

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.pay_table(
                db, TABLE_ID, TENANT_ID, payment_data
            )

        assert result["total"] == 20.0
        assert result["amount_paid"] == 50.0
        assert result["change"] == 30.0


# ═══════════════════════════════════════════════════════════════
# Test: get_table_orders_status
# ═══════════════════════════════════════════════════════════════

class TestGetTableOrdersStatus:

    @pytest.mark.asyncio
    async def test_all_delivered_true(self):
        """
        Escenario 1: Todas las comandas entregadas → all_delivered=True.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        orders = [
            _make_kitchen_order(order_id=1, status="delivered"),
            _make_kitchen_order(order_id=2, status="delivered"),
        ]

        db = _build_mock_db(orders=orders)

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["all_delivered"] is True
        assert result["orders_count"] == 2
        assert result["delivered_count"] == 2

    @pytest.mark.asyncio
    async def test_all_delivered_false_when_pending(self):
        """
        Escenario 2: Comanda en estado 'pending' → all_delivered=False.
        """
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        orders = [
            _make_kitchen_order(order_id=1, status="pending"),
            _make_kitchen_order(order_id=2, status="delivered"),
        ]

        db = _build_mock_db(orders=orders)

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["all_delivered"] is False
        assert result["orders_count"] == 2
        assert result["delivered_count"] == 1

    @pytest.mark.asyncio
    async def test_all_delivered_false_when_preparing(self):
        """Comanda en preparación → all_delivered=False."""
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        orders = [_make_kitchen_order(order_id=1, status="preparing")]

        db = _build_mock_db(orders=orders)

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["all_delivered"] is False

    @pytest.mark.asyncio
    async def test_all_delivered_false_when_ready(self):
        """Comanda lista pero no entregada → all_delivered=False."""
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        orders = [_make_kitchen_order(order_id=1, status="ready")]

        db = _build_mock_db(orders=orders)

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["all_delivered"] is False

    @pytest.mark.asyncio
    async def test_total_summary(self):
        """Verifica que el total y items se calculen correctamente."""
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        orders = [
            _make_kitchen_order(order_id=1, status="delivered", items=[
                {"menu_item_id": 1, "name": "Hamburguesa", "quantity": 2,
                 "unit_price": 12.0, "total": 24.0},
            ]),
            _make_kitchen_order(order_id=2, status="delivered", items=[
                {"menu_item_id": 2, "name": "Papas Fritas", "quantity": 1,
                 "unit_price": 8.0, "total": 8.0},
                {"menu_item_id": 3, "name": "Gaseosa", "quantity": 2,
                 "unit_price": 5.0, "total": 10.0},
            ]),
        ]

        db = _build_mock_db(orders=orders)

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["total"] == 42.0  # 24 + 8 + 10
        assert len(result["items"]) == 3
        assert result["items"][0]["name"] == "Hamburguesa"
        assert result["items"][2]["name"] == "Gaseosa"

    @pytest.mark.asyncio
    async def test_no_orders_returns_all_delivered_false(self):
        """Sin órdenes → all_delivered=False, total=0."""
        mock_table = MagicMock()
        mock_table.id = TABLE_ID
        mock_table.tenant_id = TENANT_ID

        db = _build_mock_db(orders=[])

        with patch(
            "app.services.restaurant_service.TablesService.get_table",
            new_callable=AsyncMock,
            return_value=mock_table,
        ):
            result = await ClosePayService.get_table_orders_status(
                db, TABLE_ID, TENANT_ID
            )

        assert result["all_delivered"] is False
        assert result["orders_count"] == 0
        assert result["total"] == 0.0
        assert result["items"] == []


# ═══════════════════════════════════════════════════════════════
# Test: HTTP Integration — GET /tables/{id}/orders/status
# ═══════════════════════════════════════════════════════════════

def _setup_http_overrides(db_session):
    """Configura dependency overrides para test HTTP."""
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)

    user = User(
        id=1, email="test@iaasronsys.com", full_name="Test",
        role="waiter", company_id=1, is_active=True, is_verified=True,
        failed_login_attempts=0,
    )

    async def fake_user():
        return user

    async def fake_tenant():
        return TENANT_ID

    async def fake_db():
        return db_session

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db


class TestOrdersStatusHttpEndpoint:

    def _clean_overrides(self):
        for key in list(app.dependency_overrides.keys()):
            app.dependency_overrides.pop(key, None)

    def test_orders_status_endpoint_exists(self):
        """GET /api/v1/restaurant/tables/{id}/orders/status → no 404."""
        self._clean_overrides()

        db = _build_mock_db()

        with patch(
            "app.services.restaurant_service.ClosePayService.get_table_orders_status",
            new_callable=AsyncMock,
            return_value={
                "all_delivered": True,
                "total": 85.0,
                "items": [{"name": "Lomo", "quantity": 1, "total": 85.0}],
                "orders_count": 1,
                "delivered_count": 1,
            },
        ):
            _setup_http_overrides(db)
            client = TestClient(app)
            r = client.get(
                f"/api/v1/restaurant/tables/{TABLE_ID}/orders/status",
                headers={"X-Tenant-ID": str(TENANT_ID),
                         "Authorization": "Bearer x"},
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_orders_status_all_delivered_true_response(self):
        """Verifica formato de respuesta."""
        self._clean_overrides()

        db = _build_mock_db()

        with patch(
            "app.services.restaurant_service.ClosePayService.get_table_orders_status",
            new_callable=AsyncMock,
            return_value={
                "all_delivered": True,
                "total": 85.0,
                "items": [{"name": "Lomo Saltado", "quantity": 1, "total": 85.0}],
                "orders_count": 1,
                "delivered_count": 1,
            },
        ):
            _setup_http_overrides(db)
            client = TestClient(app)
            r = client.get(
                f"/api/v1/restaurant/tables/{TABLE_ID}/orders/status",
                headers={"X-Tenant-ID": str(TENANT_ID),
                         "Authorization": "Bearer x"},
            )
            data = r.json()
            assert data["all_delivered"] is True
            assert data["total"] == 85.0
            assert len(data["items"]) == 1

    def test_orders_status_requires_auth(self):
        """Sin token → 401."""
        self._clean_overrides()

        db = _build_mock_db()
        async def fake_db():
            return db
        app.dependency_overrides[get_db] = fake_db

        client = TestClient(app)
        r = client.get(
            f"/api/v1/restaurant/tables/{TABLE_ID}/orders/status",
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
        assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Test: PayTableRequest.resolve_payments
# ═══════════════════════════════════════════════════════════════

class TestResolvePayments:

    def test_new_format_payments_list(self):
        """payments list se devuelve directamente."""
        from app.schemas.restaurant import PayTableRequest
        data = {
            "payments": [
                {"method": "yape", "amount": 50.0, "reference": "Juan"},
                {"method": "cash", "amount": 35.0},
            ],
        }
        result = PayTableRequest.resolve_payments(data)
        assert len(result) == 2
        assert result[0]["method"] == "yape"
        assert result[0]["amount"] == 50.0
        assert result[0]["reference"] == "Juan"
        assert result[1]["method"] == "cash"
        assert result[1]["amount"] == 35.0

    def test_legacy_format_payment_method_and_amount(self):
        """payment_method + amount se convierte a lista de 1."""
        from app.schemas.restaurant import PayTableRequest
        data = {
            "payment_method": "cash",
            "amount": 100.0,
            "reference": "Test ref",
        }
        result = PayTableRequest.resolve_payments(data)
        assert len(result) == 1
        assert result[0]["method"] == "cash"
        assert result[0]["amount"] == 100.0
        assert result[0]["reference"] == "Test ref"

    def test_empty_data_returns_empty_list(self):
        """Sin payments ni payment_method + amount → []."""
        from app.schemas.restaurant import PayTableRequest
        result = PayTableRequest.resolve_payments({"user_id": 1})
        assert result == []

    def test_payments_takes_precedence(self):
        """Si ambos vienen, payments gana."""
        from app.schemas.restaurant import PayTableRequest
        data = {
            "payments": [{"method": "yape", "amount": 50.0}],
            "payment_method": "cash",
            "amount": 100.0,
        }
        result = PayTableRequest.resolve_payments(data)
        assert len(result) == 1
        assert result[0]["method"] == "yape"
        assert result[0]["amount"] == 50.0
