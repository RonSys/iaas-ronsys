"""
Tests unitarios — TakeawayService.create() con modifiers (HU-F0-016).

Cubre:
  - Cálculo de price_adjustment en item_total
  - Item sin modifiers (regresión)
  - Validación max_select (excedido y en límite)
  - Múltiples modifiers en un item
  - Consistencia con KitchenOrdersService.create_order()
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.restaurant_service import TakeawayService


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_mock_menu_item(id=1, name="Hamburguesa", price=12.0, active=True):
    """Crea un MenuItem mock con los atributos mínimos relevantes."""
    item = MagicMock()
    item.id = id
    item.name = name
    item.price = price
    item.active = active
    return item


def _make_mock_modifier(id, name, price_adjustment, max_select):
    """Crea un MenuModifier mock."""
    mod = MagicMock()
    mod.id = id
    mod.name = name
    mod.price_adjustment = price_adjustment
    mod.max_select = max_select
    return mod


def _make_result_for(value):
    """Crea un MagicMock result SQLAlchemy con scalar_one_or_none(value)."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = 0
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    r.scalars.return_value = scalars_mock
    unique_mock = MagicMock()
    unique_mock.scalars.return_value = scalars_mock
    r.unique.return_value = unique_mock
    return r


def _make_mock_db(modifiers_by_id=None, fallback_scalar_one_or_none=None):
    """Crea un AsyncMock DB session que resuelve lookups de modifiers.

    El execute resuelve lookups de MenuModifier extrayendo el id de la
    cláusula where. Para cualquier otra query, retorna fallback_scalar_one_or_none.

    MenuService.get_item se patchea por separado.
    """
    session = AsyncMock()

    if modifiers_by_id is None:
        modifiers_by_id = {}

    async def _execute(stmt):
        # Intentar extraer el modifier id de la cláusula where: MenuModifier.id == X
        try:
            where = stmt._where_criteria[0]
            mid = where.right.value
            mod = modifiers_by_id.get(mid)
            if mod is not None:
                return _make_result_for(mod)
        except Exception:
            pass
        return _make_result_for(fallback_scalar_one_or_none)

    session.execute = _execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ═══════════════════════════════════════════════════════════════
# Test: Item CON modifiers — price_adjustment summed
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_item_with_modifiers_price_adjustment_summed():
    """
    Given: Hamburgesa S/12 + huevo frito +S/2.00 + extra queso +S/1.50
    When: TakeawayService.create()
    Then: item_total = qty * (unit_price + Σ price_adjustment)
          = 1 * (12 + 2 + 1.5) = 15.5
    """
    modifier_map = {
        101: _make_mock_modifier(id=101, name="Huevo frito", price_adjustment=2.0, max_select=2),
        102: _make_mock_modifier(id=102, name="Extra queso", price_adjustment=1.5, max_select=2),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=1, name="Hamburguesa", price=12.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "customer_name": "Juan",
            "items": [
                {
                    "menu_item_id": 1,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 101, "name": "Huevo frito", "price_adjustment": 2.0},
                        {"id": 102, "name": "Extra queso", "price_adjustment": 1.5},
                    ],
                }
            ],
        })

    item = result["items"][0]
    assert item["unit_price"] == 12.0
    assert item["modifiers_total"] == 3.5  # 2.0 + 1.5
    assert item["total"] == 15.5  # 1 * (12 + 3.5)


@pytest.mark.asyncio
async def test_item_with_modifiers_and_quantity():
    """
    Given: Hamburgesa S/12, qty=2, huevo frito +S/2.00
    Then: item_total = 2 * (12 + 2) = 28
    """
    modifier_map = {
        201: _make_mock_modifier(id=201, name="Huevo frito", price_adjustment=2.0, max_select=3),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=1, name="Hamburguesa", price=12.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 1,
                    "quantity": 2,
                    "modifiers": [
                        {"id": 201, "name": "Huevo frito", "price_adjustment": 2.0},
                    ],
                }
            ],
        })

    item = result["items"][0]
    assert item["quantity"] == 2
    assert item["modifiers_total"] == 2.0
    assert item["total"] == 28.0  # 2 * (12 + 2)


# ═══════════════════════════════════════════════════════════════
# Test: Item SIN modifiers — regresión
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_item_without_modifiers_base_price_unchanged():
    """
    Given: Item sin modifiers en el payload
    Then: item_total = qty * unit_price (sin cambios, sin errores)
    """
    db = _make_mock_db(modifiers_by_id={})
    menu_item = _make_mock_menu_item(id=1, name="Coca Cola", price=5.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {"menu_item_id": 1, "quantity": 3, "modifiers": []},
            ],
        })

    item = result["items"][0]
    assert item["unit_price"] == 5.0
    assert item["modifiers_total"] == 0.0
    assert item["total"] == 15.0  # 3 * 5
    assert item["modifiers"] == []


@pytest.mark.asyncio
async def test_item_no_modifiers_key_in_payload():
    """
    Given: Item payload sin la key 'modifiers'
    Then: Se trata como lista vacía, total = qty * unit_price
    """
    db = _make_mock_db(modifiers_by_id={})
    menu_item = _make_mock_menu_item(id=2, name="Pizza", price=20.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {"menu_item_id": 2, "quantity": 1},
            ],
        })

    item = result["items"][0]
    assert item["total"] == 20.0
    assert item["modifiers_total"] == 0.0
    assert item["modifiers"] == []


# ═══════════════════════════════════════════════════════════════
# Test: max_select validation
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_max_select_exceeded_returns_422():
    """
    Given: Modifier con max_select=1, pero enviado 2 veces
    Then: HTTPException 422 con mensaje claro
    """
    modifier_map = {
        301: _make_mock_modifier(id=301, name="Palta extra", price_adjustment=3.0, max_select=1),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=3, name="Sandwich", price=10.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), pytest.raises(HTTPException) as exc_info:
        await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 3,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 301, "name": "Palta extra", "price_adjustment": 3.0},
                        {"id": 301, "name": "Palta extra", "price_adjustment": 3.0},
                    ],
                }
            ],
        })

    assert exc_info.value.status_code == 422
    assert "Palta extra" in exc_info.value.detail
    assert "máximo 1" in exc_info.value.detail
    assert "enviados 2" in exc_info.value.detail


@pytest.mark.asyncio
async def test_max_select_at_limit_accepted():
    """
    Given: Modifier con max_select=2, enviado exactamente 2 veces
    Then: Se acepta sin error; price_adjustment se cuenta 2 veces
    """
    modifier_map = {
        401: _make_mock_modifier(id=401, name="Extra queso", price_adjustment=1.0, max_select=2),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=4, name="Burrito", price=15.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 4,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 401, "name": "Extra queso", "price_adjustment": 1.0},
                        {"id": 401, "name": "Extra queso", "price_adjustment": 1.0},
                    ],
                }
            ],
        })

    item = result["items"][0]
    assert item["modifiers_total"] == 2.0  # 2 × 1.0
    assert item["total"] == 17.0  # 1 * (15 + 2)


@pytest.mark.asyncio
async def test_max_select_defaults_to_one():
    """
    Given: Modifier con max_select=1 (default), enviado 2 veces
    Then: 422 porque max_select es 1
    """
    modifier_map = {
        501: _make_mock_modifier(id=501, name="Sin cebolla", price_adjustment=0.0, max_select=1),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=5, name="Taco", price=8.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), pytest.raises(HTTPException) as exc_info:
        await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 5,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 501, "name": "Sin cebolla", "price_adjustment": 0.0},
                        {"id": 501, "name": "Sin cebolla", "price_adjustment": 0.0},
                    ],
                }
            ],
        })

    assert exc_info.value.status_code == 422
    assert "Sin cebolla" in exc_info.value.detail


# ═══════════════════════════════════════════════════════════════
# Test: Múltiples modifiers distintos en un item
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_multiple_different_modifiers_sum_all():
    """
    Given: Item con 3 modifiers distintos, cada uno con su propio price_adjustment
    Then: modifiers_total = suma de todos los price_adjustment
    """
    modifier_map = {
        601: _make_mock_modifier(id=601, name="Huevo", price_adjustment=2.0, max_select=2),
        602: _make_mock_modifier(id=602, name="Queso", price_adjustment=1.5, max_select=2),
        603: _make_mock_modifier(id=603, name="Tocino", price_adjustment=3.0, max_select=2),
    }
    db = _make_mock_db(modifiers_by_id=modifier_map)
    menu_item = _make_mock_menu_item(id=6, name="Hamburguesa XL", price=15.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 6,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 601, "name": "Huevo", "price_adjustment": 2.0},
                        {"id": 602, "name": "Queso", "price_adjustment": 1.5},
                        {"id": 603, "name": "Tocino", "price_adjustment": 3.0},
                    ],
                }
            ],
        })

    item = result["items"][0]
    assert item["modifiers_total"] == 6.5  # 2.0 + 1.5 + 3.0
    assert item["total"] == 21.5  # 1 * (15 + 6.5)


# ═══════════════════════════════════════════════════════════════
# Test: Consistencia Takeaway ↔ KitchenOrders
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_same_logic_as_kitchen_orders():
    """
    Dado el mismo item + modifiers, TakeawayService.create() y
    KitchenOrdersService.create_order() deben producir el mismo item_total
    (misma fórmula: qty * (unit_price + Σ price_adjustment)).

    Verificamos la consistencia inspeccionando los items validados que se
    guardan via db.add() en ambos servicios.
    """
    from app.services.restaurant_service import KitchenOrdersService

    modifier_map = {
        701: _make_mock_modifier(id=701, name="Huevo frito", price_adjustment=2.0, max_select=2),
        702: _make_mock_modifier(id=702, name="Extra queso", price_adjustment=1.5, max_select=2),
    }

    menu_item = _make_mock_menu_item(id=7, name="Hamburguesa", price=12.0)
    items_payload = [
        {
            "menu_item_id": 7,
            "quantity": 2,
            "modifiers": [
                {"id": 701, "name": "Huevo frito", "price_adjustment": 2.0},
                {"id": 702, "name": "Extra queso", "price_adjustment": 1.5},
            ],
        }
    ]

    # Capturar los items validados de db.add() para ambos servicios
    stored_takeaway_items: list = []
    stored_kitchen_items: list = []

    # --- Takeaway ---
    db_takeaway = _make_mock_db(modifiers_by_id=modifier_map)
    db_takeaway.add = MagicMock(side_effect=lambda obj: (
        stored_takeaway_items.extend(obj.items)
        if hasattr(obj, "items") and isinstance(obj.items, list) else None
    ))
    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        await TakeawayService.create(
            db_takeaway, tenant_id=1,
            data={"items": items_payload},
        )

    # --- KitchenOrders ---
    mock_table = MagicMock()
    mock_table.status = "occupied"
    mock_table.number = "T1"
    mock_table.id = 1

    # KitchenOrder mock para get_order_detail → get_order lookup
    mock_ko = MagicMock()
    mock_ko.id = 99
    mock_ko.tenant_id = 1
    mock_ko.table_id = 1
    mock_ko.status = "pending"
    mock_ko.items = []
    mock_ko.notes = None
    mock_ko.ordered_at = None
    mock_ko.started_at = None
    mock_ko.completed_at = None

    # create_order() primero busca orden existente (debe retornar None),
    # luego create_order -> get_order_detail -> get_order (debe retornar mock_ko).
    # Contador: 1ra query no-modifier = existing -> None, resto = mock_ko.
    db_kitchen = _make_mock_db(modifiers_by_id=modifier_map)  # fallback=None
    _ko_non_mod = [0]
    async def _ko_execute(stmt):
        try:
            where = stmt._where_criteria[0]
            mid = where.right.value
            mod = modifier_map.get(mid)
            if mod is not None:
                return _make_result_for(mod)
        except Exception:
            pass
        _ko_non_mod[0] += 1
        if _ko_non_mod[0] == 1:
            return _make_result_for(None)  # existing order -> None
        return _make_result_for(mock_ko)

    db_kitchen.execute = _ko_execute
    db_kitchen.add = MagicMock(side_effect=lambda obj: (
        stored_kitchen_items.extend(obj.items)
        if hasattr(obj, "items") and isinstance(obj.items, list) else None
    ))
    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ), patch(
        "app.services.restaurant_service.TablesService.get_table",
        new_callable=AsyncMock,
        return_value=mock_table,
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        await KitchenOrdersService.create_order(
            db_kitchen, tenant_id=1, table_id=1,
            items_data=items_payload,
        )

    item_t = stored_takeaway_items[0]
    item_k = stored_kitchen_items[0]

    # Ambos servicios deben calcular el mismo item_total con la misma fórmula
    assert item_t["total"] == item_k["total"], (
        f"Takeaway total={item_t['total']} ≠ KitchenOrders total={item_k['total']}"
    )
    assert item_t["modifiers_total"] == item_k["modifiers_total"]
    # Fórmula: qty * (unit_price + Σ price_adjustment) = 2 * (12 + 3.5) = 31
    assert item_t["total"] == 31.0
    assert item_t["modifiers_total"] == 3.5


# ═══════════════════════════════════════════════════════════════
# Test: Total del pedido refleja todos los items
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_order_total_sums_all_items_with_modifiers():
    """
    Given: 2 items, cada uno con modifiers
    Then: El total del pedido es la suma de todos los item_total
    """
    modifier_map = {
        801: _make_mock_modifier(id=801, name="Huevo", price_adjustment=2.0, max_select=2),
        802: _make_mock_modifier(id=802, name="Queso", price_adjustment=1.0, max_select=2),
    }

    burger = _make_mock_menu_item(id=8, name="Hamburguesa", price=12.0)
    soda = _make_mock_menu_item(id=9, name="Gaseosa", price=5.0)

    db = _make_mock_db(modifiers_by_id=modifier_map)

    # MenuService.get_item será llamado 2 veces — usamos side_effect
    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        side_effect=[burger, soda],
    ), patch("app.services.restaurant_service.manager.broadcast_to_kitchen", new_callable=AsyncMock):
        result = await TakeawayService.create(db, tenant_id=1, data={
            "items": [
                {
                    "menu_item_id": 8,
                    "quantity": 1,
                    "modifiers": [
                        {"id": 801, "name": "Huevo", "price_adjustment": 2.0},
                    ],
                },
                {
                    "menu_item_id": 9,
                    "quantity": 2,
                    "modifiers": [
                        {"id": 802, "name": "Queso", "price_adjustment": 1.0},
                    ],
                },
            ],
        })

    # Item 1: 1 * (12 + 2) = 14
    # Item 2: 2 * (5 + 1) = 12
    # Total = 26
    assert result["items"][0]["total"] == 14.0
    assert result["items"][1]["total"] == 12.0
    order_sum = sum(item["total"] for item in result["items"])
    assert order_sum == 26.0


# ═══════════════════════════════════════════════════════════════
# Test: Empty items
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_empty_items_returns_400():
    """Items vacíos debe retornar 400."""
    db = _make_mock_db()
    with pytest.raises(HTTPException) as exc_info:
        await TakeawayService.create(db, tenant_id=1, data={"items": []})
    assert exc_info.value.status_code == 400
    assert "ítem" in exc_info.value.detail.lower()
