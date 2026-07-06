"""
Tests del Caso 3: Gestión de Modificadores en el Menú.

Cubre:
  - MenuService.create_item() con modifiers
  - MenuService.list_items() devuelve modifiers con cada ítem
  - MenuService.update_item() reemplaza modifiers cuando se envía
  - MenuService.update_item() preserva modifiers cuando no se envía
  - MenuService.update_item() con modifiers=[] elimina todos
  - MenuService.update_item() sin changes en modifiers los preserva
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest

from app.services.restaurant_service import MenuService

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_mock_menu_item(
    id=1, name="Ceviche Mixto", price=28.0, cost_price=14.0,
    category="Entradas", item_type="dish", active=True,
    description=None, image_url=None,
):
    item = MagicMock()
    item.id = id
    item.name = name
    item.price = price
    item.cost_price = cost_price
    item.category = category
    item.item_type = item_type
    item.active = active
    item.description = description
    item.image_url = image_url
    item.updated_at = datetime.now(UTC)
    item.modifiers = []
    return item


def _make_mock_modifier(id, name, price_adjustment=0, max_select=1):
    mod = MagicMock()
    mod.id = id
    mod.name = name
    mod.price_adjustment = price_adjustment
    mod.max_select = max_select
    return mod


def _make_result_for(value):
    """Creates a MagicMock result whose scalar_one_or_none returns value."""
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


def _make_result_for_scalars_all(values):
    """Creates a MagicMock whose scalars().all() returns the given values."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    r.scalar.return_value = 0
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = values
    r.scalars.return_value = scalars_mock
    unique_mock = MagicMock()
    unique_mock.scalars.return_value = scalars_mock
    r.unique.return_value = unique_mock
    return r


def _extract_menu_item_id_from_where(stmt):
    """Intenta extraer menu_item_id de la cláusula WHERE de un Select."""
    try:
        where = getattr(stmt, '_where_criteria', [])
        for crit in where:
            try:
                left = crit.left
                if hasattr(left, 'key') and left.key in ('menu_item_id',):
                    return crit.right.value
            except (AttributeError, ValueError):
                pass
    except Exception:
        pass
    return None


def _make_mock_db():
    """
    Crea un AsyncMock de sesión DB con ejecución flexible.

    - Consultas que contienen menu_item_id en el WHERE retornan modifiers del registry
    - Cualquier otra query retorna None
    """
    session = AsyncMock()
    _modifiers_registry: dict[int, list] = {}
    _deleted_modifiers: list = []

    async def _execute(stmt):
        nonlocal _modifiers_registry

        mid = _extract_menu_item_id_from_where(stmt)
        if mid is not None:
            mods = _modifiers_registry.get(mid, [])
            return _make_result_for_scalars_all(mods)

        return _make_result_for(None)

    session.execute = _execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = MagicMock(side_effect=lambda obj: _deleted_modifiers.append(obj))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    session._modifiers_registry = _modifiers_registry
    session._deleted_modifiers = _deleted_modifiers

    return session


def _register_modifiers(db, menu_item_id, modifiers):
    """Registers modifiers that will be returned for a given menu_item_id."""
    db._modifiers_registry[menu_item_id] = list(modifiers)


def _get_added_menu_modifiers(db):
    """Retorna los objetos MenuModifier que fueron añadidos vía session.add()."""
    result = []
    for call_args, _ in db.add.call_args_list:
        obj = call_args[0]
        if type(obj).__name__ == "MenuModifier":
            result.append(obj)
    return result


# ═══════════════════════════════════════════════════════════════
# Tests: create_item with modifiers
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_item_with_modifiers():
    """
    Dado: datos de plato con 2 modificadores
    Cuando: MenuService.create_item()
    Entonces: se crea el item y los MenuModifier se agregan a la sesión
    """
    db = _make_mock_db()
    body = {
        "name": "Ceviche Mixto",
        "price": 28.0,
        "category": "Entradas",
        "modifiers": [
            {"name": "Conchas negras", "price_adjustment": 5.0, "max_select": 3},
            {"name": "Sin cebolla", "price_adjustment": 0, "max_select": 1},
        ],
    }

    result = await MenuService.create_item(db, tenant_id=1, data=body)

    assert result["name"] == "Ceviche Mixto"
    added = _get_added_menu_modifiers(db)
    assert len(added) == 2

    assert added[0].name == "Conchas negras"
    assert added[0].price_adjustment == 5.0
    assert added[0].max_select == 3

    assert added[1].name == "Sin cebolla"
    assert added[1].price_adjustment == 0
    assert added[1].max_select == 1


@pytest.mark.asyncio
async def test_create_item_without_modifiers():
    """
    Dado: datos de plato SIN modificadores
    Cuando: MenuService.create_item()
    Entonces: se crea el item, no se agrega ningún MenuModifier
    """
    db = _make_mock_db()
    body = {
        "name": "Arroz con Pollo",
        "price": 22.0,
        "category": "Principales",
    }

    result = await MenuService.create_item(db, tenant_id=1, data=body)

    assert result["name"] == "Arroz con Pollo"
    added = _get_added_menu_modifiers(db)
    assert len(added) == 0


@pytest.mark.asyncio
async def test_create_item_with_empty_modifiers_list():
    """
    Dado: datos de plato con modifiers=[]
    Cuando: MenuService.create_item()
    Entonces: se crea el item sin MenuModifier
    """
    db = _make_mock_db()
    body = {
        "name": "Papa a la Huancaína",
        "price": 18.0,
        "category": "Entradas",
        "modifiers": [],
    }

    result = await MenuService.create_item(db, tenant_id=1, data=body)

    assert result["name"] == "Papa a la Huancaína"
    added = _get_added_menu_modifiers(db)
    assert len(added) == 0


# ═══════════════════════════════════════════════════════════════
# Tests: update_item with modifiers (REPLACE strategy)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_item_replaces_modifiers():
    """
    Dado: un ítem con 2 modificadores existentes
    Cuando: update_item() recibe modifiers con 1 modificador nuevo
    Entonces:
      - Los modifiers existentes son eliminados
      - Se crea el nuevo MenuModifier
    """
    db = _make_mock_db()
    mod1 = _make_mock_modifier(id=10, name="Conchas negras", price_adjustment=5.0, max_select=3)
    mod2 = _make_mock_modifier(id=11, name="Sin cebolla", price_adjustment=0, max_select=1)
    _register_modifiers(db, menu_item_id=1, modifiers=[mod1, mod2])

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        result = await MenuService.update_item(db, item_id=1, tenant_id=1, data={
            "name": "Ceviche Mixto Clásico",
            "modifiers": [
                {"name": "Extra queso", "price_adjustment": 3.0, "max_select": 1},
            ],
        })

    # Verificar que los 2 modifiers antiguos fueron eliminados
    assert len(db._deleted_modifiers) == 2
    assert db._deleted_modifiers[0] is mod1
    assert db._deleted_modifiers[1] is mod2

    # Verificar que se creó 1 nuevo MenuModifier
    added = _get_added_menu_modifiers(db)
    assert len(added) == 1
    assert added[0].name == "Extra queso"
    assert added[0].price_adjustment == 3.0
    assert added[0].max_select == 1

    # Verificar que se actualizó el nombre
    assert menu_item.name == "Ceviche Mixto Clásico"
    assert result["name"] == "Ceviche Mixto Clásico"


@pytest.mark.asyncio
async def test_update_item_preserves_modifiers_when_not_sent():
    """
    Dado: un ítem con 2 modificadores existentes
    Cuando: update_item() NO recibe modifiers en el body
    Entonces: los modifiers existentes NO se tocan
    """
    db = _make_mock_db()
    mod1 = _make_mock_modifier(id=10, name="Conchas negras", price_adjustment=5.0, max_select=3)
    mod2 = _make_mock_modifier(id=11, name="Sin cebolla", price_adjustment=0, max_select=1)
    _register_modifiers(db, menu_item_id=1, modifiers=[mod1, mod2])

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        result = await MenuService.update_item(db, item_id=1, tenant_id=1, data={
            "price": 30.0,
        })

    # No se debe haber eliminado ningún modifier
    assert len(db._deleted_modifiers) == 0

    # No se debe haber agregado ningún nuevo MenuModifier
    added = _get_added_menu_modifiers(db)
    assert len(added) == 0

    # Verificar que se actualizó el precio
    assert menu_item.price == 30.0
    assert result["active"] is True


@pytest.mark.asyncio
async def test_update_item_removes_all_modifiers_with_empty_list():
    """
    Dado: un ítem con 2 modificadores existentes
    Cuando: update_item() recibe modifiers=[]
    Entonces: todos los modifiers existentes son eliminados
    """
    db = _make_mock_db()
    mod1 = _make_mock_modifier(id=10, name="Conchas negras", price_adjustment=5.0, max_select=3)
    mod2 = _make_mock_modifier(id=11, name="Sin cebolla", price_adjustment=0, max_select=1)
    _register_modifiers(db, menu_item_id=1, modifiers=[mod1, mod2])

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        result = await MenuService.update_item(db, item_id=1, tenant_id=1, data={
            "modifiers": [],
        })

    # Los 2 modifiers existentes deben haber sido eliminados
    assert len(db._deleted_modifiers) == 2

    # No se debe haber agregado ningún nuevo MenuModifier
    added = _get_added_menu_modifiers(db)
    assert len(added) == 0
    assert result["active"] is True


@pytest.mark.asyncio
async def test_update_item_only_basic_fields_without_modifiers():
    """
    Dado: un ítem SIN modifiers
    Cuando: update_item() actualiza solo campos básicos
    Entonces: funciona correctamente, no hay operaciones de modifiers
    """
    db = _make_mock_db()
    _register_modifiers(db, menu_item_id=1, modifiers=[])

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        result = await MenuService.update_item(db, item_id=1, tenant_id=1, data={
            "name": "Ceviche Clásico",
            "price": 30.0,
            "active": False,
        })

    assert result["name"] == "Ceviche Clásico"
    assert result["active"] is False
    assert len(db._deleted_modifiers) == 0


# ═══════════════════════════════════════════════════════════════
# Tests: list_items returns modifiers
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_items_returns_modifiers():
    """
    Dado: items de menú, algunos con modifiers y otros sin
    Cuando: MenuService.list_items()
    Entonces: cada item incluye su lista de modifiers
    """
    db = _make_mock_db()
    mod1 = _make_mock_modifier(id=10, name="Conchas negras", price_adjustment=5.0, max_select=3)
    mod2 = _make_mock_modifier(id=11, name="Sin cebolla", price_adjustment=0, max_select=1)
    mod3 = _make_mock_modifier(id=12, name="Extra queso", price_adjustment=3.0, max_select=1)

    _register_modifiers(db, menu_item_id=1, modifiers=[mod1, mod2])
    _register_modifiers(db, menu_item_id=2, modifiers=[mod3])
    _register_modifiers(db, menu_item_id=3, modifiers=[])

    item1 = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)
    item2 = _make_mock_menu_item(id=2, name="Lomo Saltado", price=32.0)
    item3 = _make_mock_menu_item(id=3, name="Arroz con Pollo", price=22.0)

    # Build the actual query that list_items uses to get the correct type
    # and then detect it by checking the from clause / entity
    async def _execute(stmt):
        # 1. Check if it's a MenuItem query (has _where_criteria with tenant_id)
        mid = _extract_menu_item_id_from_where(stmt)
        if mid is not None:
            mods = db._modifiers_registry.get(mid, [])
            return _make_result_for_scalars_all(mods)

        # 2. Otherwise, return menu items
        return _make_result_for_scalars_all([item1, item2, item3])

    db.execute = _execute

    result = await MenuService.list_items(db, tenant_id=1)

    assert len(result) == 3

    # Item con 2 modifiers
    assert result[0]["name"] == "Ceviche Mixto"
    assert len(result[0]["modifiers"]) == 2
    mod_names = [m["name"] for m in result[0]["modifiers"]]
    assert "Conchas negras" in mod_names
    assert "Sin cebolla" in mod_names

    # Item con 1 modifier
    assert result[1]["name"] == "Lomo Saltado"
    assert len(result[1]["modifiers"]) == 1
    assert result[1]["modifiers"][0]["name"] == "Extra queso"

    # Item sin modifiers
    assert result[2]["name"] == "Arroz con Pollo"
    assert len(result[2]["modifiers"]) == 0


# ═══════════════════════════════════════════════════════════════
# Test: update_item replaces many modifiers (regression)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_item_replaces_complex_modifiers():
    """
    Dado: un ítem con 3 modificadores variados
    Cuando: se actualizan todos los modifiers a 4 nuevos
    Entonces: se reemplazan exactamente con los nuevos datos
    """
    db = _make_mock_db()

    existing = [
        _make_mock_modifier(id=1, name="Conchas negras", price_adjustment=5.0, max_select=3),
        _make_mock_modifier(id=2, name="Sin cebolla", price_adjustment=0, max_select=1),
        _make_mock_modifier(id=3, name="Extra queso", price_adjustment=3.0, max_select=1),
    ]
    _register_modifiers(db, menu_item_id=1, modifiers=existing)

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Mixto", price=28.0)

    new_modifiers = [
        {"name": "Cocción término medio", "price_adjustment": 0, "max_select": 1},
        {"name": "Cocción bien cocido", "price_adjustment": 0, "max_select": 1},
        {"name": "Cocción poco cocido", "price_adjustment": 0, "max_select": 1},
        {"name": "Conchas negras", "price_adjustment": 5.0, "max_select": 3},
    ]

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        result = await MenuService.update_item(db, item_id=1, tenant_id=1, data={
            "modifiers": new_modifiers,
        })

    # Verificar que los 3 existentes fueron borrados
    assert len(db._deleted_modifiers) == 3

    # Verificar que se agregaron 4 nuevos
    added = _get_added_menu_modifiers(db)
    assert len(added) == 4

    assert added[0].name == "Cocción término medio"
    assert added[0].price_adjustment == 0
    assert added[0].max_select == 1

    assert added[3].name == "Conchas negras"
    assert added[3].price_adjustment == 5.0
    assert added[3].max_select == 3

    assert result["active"] is True
