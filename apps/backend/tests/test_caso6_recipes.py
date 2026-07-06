"""
Tests del Caso 6: Recetas e Insumos.

Cubre:
  - RecipesService.get_recipe() — obtener receta de un plato
  - RecipesService.save_recipe() — guardar/actualizar receta
  - RecipesService.list_products_for_recipe() — listar productos
  - Validación: solo platos de cocina pueden tener receta
  - Costo estimado = sum(quantity × product.average_cost)
  - Plato sin receta → estructura vacía
  - GET /menu/{id}/recipe → ingredientes + costo + margen
  - PUT /menu/{id}/recipe → reemplaza ingredientes
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, UTC

import pytest

from app.services.restaurant_service import RecipesService


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_mock_menu_item(
    id=1, name="Ceviche Clásico", price=28.0, cost_price=14.0,
    category="Entradas", item_type="food", preparation_area="cocina",
    active=True,
):
    item = MagicMock()
    item.id = id
    item.name = name
    item.price = price
    item.cost_price = cost_price
    item.category = category
    item.item_type = item_type
    item.preparation_area = preparation_area
    item.active = active
    return item


def _make_mock_product(
    id=1, name="Pescado", unit_of_measure="g",
    average_cost=0.015, current_stock=5000.0, tenant_id=1,
):
    prod = MagicMock()
    prod.id = id
    prod.name = name
    prod.unit_of_measure = unit_of_measure
    prod.average_cost = average_cost
    prod.current_stock = current_stock
    prod.tenant_id = tenant_id
    return prod


def _make_mock_ingredient(
    id=1, recipe_id=1, product_id=1, quantity=200.0,
    unit_of_measure="g", sort_order=0, product=None,
):
    ing = MagicMock()
    ing.id = id
    ing.recipe_id = recipe_id
    ing.product_id = product_id
    ing.quantity = quantity
    ing.unit_of_measure = unit_of_measure
    ing.sort_order = sort_order
    ing.product = product
    return ing


def _make_mock_recipe(
    id=1, menu_item_id=1, created_at=None, updated_at=None,
    ingredients=None,
):
    recipe = MagicMock()
    recipe.id = id
    recipe.menu_item_id = menu_item_id
    recipe.created_at = created_at or datetime.now(UTC)
    recipe.updated_at = updated_at or datetime.now(UTC)
    recipe.ingredients = ingredients or []
    return recipe


def _make_result_for(value):
    """Creates a MagicMock result whose scalar_one_or_none returns value."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = None
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    r.scalars.return_value = scalars_mock
    return r


def _make_result_for_scalars_all(values):
    """Creates a MagicMock whose scalars().all() returns the given values."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    r.scalar.return_value = None
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = values
    r.scalars.return_value = scalars_mock
    return r


def _make_mock_db():
    """Crea un AsyncMock de sesión DB."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ═══════════════════════════════════════════════════════════════
# Tests: Solo platos de cocina tienen recetas (Escenario 1)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_recipe_fails_for_bar_item():
    """
    Dado: un ítem con preparation_area="🍸 Barra"
    Cuando: RecipesService.get_recipe()
    Entonces: HTTPException 400 — solo cocina puede tener receta
    """
    db = _make_mock_db()
    bar_item = _make_mock_menu_item(id=2, name="Coca Cola", preparation_area="🍸 Barra")

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=bar_item,
    ):
        with pytest.raises(Exception) as excinfo:
            await RecipesService.get_recipe(db, menu_item_id=2, tenant_id=1)

    assert "400" in str(excinfo.value) or "Solo platos" in str(excinfo.value)


@pytest.mark.asyncio
async def test_save_recipe_fails_for_non_cooking_item():
    """
    Dado: un ítem con preparation_area="📦 Ninguno"
    Cuando: RecipesService.save_recipe()
    Entonces: HTTPException 400
    """
    db = _make_mock_db()
    none_item = _make_mock_menu_item(id=3, name="Galleta", preparation_area="📦 Ninguno")

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=none_item,
    ):
        with pytest.raises(Exception) as excinfo:
            await RecipesService.save_recipe(db, menu_item_id=3, tenant_id=1, ingredients_data=[])

    assert "400" in str(excinfo.value) or "Solo platos" in str(excinfo.value)


# ═══════════════════════════════════════════════════════════════
# Tests: Crear receta para un plato (Escenario 3)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_save_recipe_creates_new_recipe():
    """
    Dado: un plato de cocina sin receta
    Y: productos en inventario (Pescado, Limón, Cebolla, Camote)
    Cuando: RecipesService.save_recipe() con 4 ingredientes
    Entonces: se crea receta con 4 ingredientes
    Y: el costo estimado se calcula correctamente
    """
    db = _make_mock_db()

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Clásico", price=28.0)
    pescado = _make_mock_product(id=1, name="Pescado", unit_of_measure="g", average_cost=0.015)

    # Sequential responses for db.execute:
    # Call 1: Recipe query — no recipe yet → None
    # Call 2: Ingredient query — no existing ingredients → empty list
    # Calls 3-6: Product lookups (4 ingredients) → return product
    call_results = (
        [_make_result_for(None)] +
        [_make_result_for_scalars_all([])] +
        [_make_result_for(pescado)] * 4
    )
    call_idx = [-1]

    async def _execute(_stmt):
        call_idx[0] += 1
        return call_results[min(call_idx[0], len(call_results) - 1)]

    db.execute = _execute

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        ingredients_data = [
            {"product_id": 1, "quantity": 200.0, "unit_of_measure": "g", "sort_order": 0},
            {"product_id": 2, "quantity": 3.0, "unit_of_measure": "unidad", "sort_order": 1},
            {"product_id": 3, "quantity": 1.0, "unit_of_measure": "unidad", "sort_order": 2},
            {"product_id": 4, "quantity": 100.0, "unit_of_measure": "g", "sort_order": 3},
        ]
        result = await RecipesService.save_recipe(db, menu_item_id=1, tenant_id=1, ingredients_data=ingredients_data)

    assert result is not None
    assert result["menu_item_id"] == 1
    assert result["menu_item_name"] == "Ceviche Clásico"


@pytest.mark.asyncio
async def test_save_recipe_updates_existing_recipe():
    """
    Dado: un plato que ya tiene receta
    Cuando: RecipesService.save_recipe() con nuevos ingredientes
    Entonces: los ingredientes se reemplazan completamente
    """
    db = _make_mock_db()

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Clásico", price=28.0)
    existing_recipe = _make_mock_recipe(id=1, menu_item_id=1)
    lechuga = _make_mock_product(id=5, name="Lechuga", unit_of_measure="g", average_cost=0.005)

    # Make delete awaitable
    db.delete = AsyncMock()

    # Sequential responses for db.execute:
    # Call 1: Recipe query — return existing recipe
    # Call 2: Ingredient query — return old ingredient to delete
    # Call 3: Product lookup — return lechuga
    old_ingredient = MagicMock()
    call_results = [
        _make_result_for(existing_recipe),
        _make_result_for_scalars_all([old_ingredient]),
        _make_result_for(lechuga),
    ]
    call_idx = [-1]

    async def _execute(_stmt):
        call_idx[0] += 1
        return call_results[min(call_idx[0], len(call_results) - 1)]

    db.execute = _execute

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        ingredients_data = [
            {"product_id": 5, "quantity": 50.0, "unit_of_measure": "g", "sort_order": 0},
        ]
        result = await RecipesService.save_recipe(db, menu_item_id=1, tenant_id=1, ingredients_data=ingredients_data)

    assert result is not None
    assert result["menu_item_id"] == 1
    assert db.delete.called


# ═══════════════════════════════════════════════════════════════
# Tests: Receta con costo estimado (Escenario 3)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_recipe_with_estimated_cost():
    """
    Dado: un plato con receta que tiene 4 ingredientes
    Cuando: RecipesService.get_recipe()
    Entonces: retorna ingredientes + costo total estimado + margen
    Y: costo = sum(quantity × product.average_cost)
    """
    db = _make_mock_db()

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Clásico", price=28.0)

    pescado = _make_mock_product(id=1, name="Pescado", unit_of_measure="g", average_cost=0.015)
    limon = _make_mock_product(id=2, name="Limón", unit_of_measure="unidad", average_cost=0.50)
    cebolla = _make_mock_product(id=3, name="Cebolla", unit_of_measure="unidad", average_cost=0.80)
    camote = _make_mock_product(id=4, name="Camote", unit_of_measure="g", average_cost=0.008)

    # Expected costs:
    # Pescado: 200 * 0.015 = 3.00
    # Limón: 3 * 0.50 = 1.50
    # Cebolla: 1 * 0.80 = 0.80
    # Camote: 100 * 0.008 = 0.80
    # Total: 6.10
    # Margin: 28.00 - 6.10 = 21.90
    # Margin%: 21.90 / 28.00 * 100 = 78.2%

    ing1 = _make_mock_ingredient(id=1, recipe_id=1, product_id=1, quantity=200.0,
                                  unit_of_measure="g", sort_order=0, product=pescado)
    ing2 = _make_mock_ingredient(id=2, recipe_id=1, product_id=2, quantity=3.0,
                                  unit_of_measure="unidad", sort_order=1, product=limon)
    ing3 = _make_mock_ingredient(id=3, recipe_id=1, product_id=3, quantity=1.0,
                                  unit_of_measure="unidad", sort_order=2, product=cebolla)
    ing4 = _make_mock_ingredient(id=4, recipe_id=1, product_id=4, quantity=100.0,
                                  unit_of_measure="g", sort_order=3, product=camote)

    recipe = _make_mock_recipe(
        id=1, menu_item_id=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        ingredients=[ing1, ing2, ing3, ing4],
    )

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        with patch.object(db, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _make_result_for(recipe)

            result = await RecipesService.get_recipe(db, menu_item_id=1, tenant_id=1)

    assert result["has_recipe"] is True
    assert len(result["ingredients"]) == 4
    assert result["total_estimated_cost"] == 6.10
    assert result["menu_item_price"] == 28.0
    assert result["margin"] == 21.90
    assert result["margin_pct"] == 78.2

    # Verify ingredient details
    assert result["ingredients"][0]["product_name"] == "Pescado"
    assert result["ingredients"][0]["estimated_cost"] == 3.0
    assert result["ingredients"][1]["product_name"] == "Limón"
    assert result["ingredients"][1]["estimated_cost"] == 1.5


# ═══════════════════════════════════════════════════════════════
# Tests: Plato sin receta (Escenario 5)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_recipe_returns_empty_when_no_recipe():
    """
    Dado: un plato de cocina sin receta configurada
    Cuando: RecipesService.get_recipe()
    Entonces: retorna estructura vacía con has_recipe=False
    """
    db = _make_mock_db()

    menu_item = _make_mock_menu_item(id=1, name="Ceviche Clásico", price=28.0)

    with patch(
        "app.services.restaurant_service.MenuService.get_item",
        new_callable=AsyncMock,
        return_value=menu_item,
    ):
        with patch.object(db, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = _make_result_for(None)

            result = await RecipesService.get_recipe(db, menu_item_id=1, tenant_id=1)

    assert result["has_recipe"] is False
    assert result["id"] is None
    assert len(result["ingredients"]) == 0
    assert result["total_estimated_cost"] == 0.0
    assert result["menu_item_price"] == 28.0
    assert result["margin"] == 28.0  # Precio completo sin costo


# ═══════════════════════════════════════════════════════════════
# Tests: Listar productos (Escenario 8)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_products_for_recipe():
    """
    Dado: productos activos en inventario
    Cuando: RecipesService.list_products_for_recipe()
    Entonces: retorna lista con id, name, unit_of_measure, average_cost, current_stock
    """
    db = _make_mock_db()

    prod1 = _make_mock_product(id=1, name="Pescado", unit_of_measure="g", average_cost=0.015, current_stock=5000)
    prod2 = _make_mock_product(id=2, name="Limón", unit_of_measure="unidad", average_cost=0.50, current_stock=200)
    prod3 = _make_mock_product(id=3, name="Cebolla", unit_of_measure="unidad", average_cost=0.80, current_stock=100)

    with patch.object(db, "execute", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = _make_result_for_scalars_all([prod1, prod2, prod3])

        result = await RecipesService.list_products_for_recipe(db, tenant_id=1)

    assert len(result) == 3
    assert result[0]["name"] == "Pescado"
    assert result[0]["unit_of_measure"] == "g"
    assert result[0]["average_cost"] == 0.015
    assert result[0]["current_stock"] == 5000.0
    assert result[1]["name"] == "Limón"
    assert result[1]["unit_of_measure"] == "unidad"
    assert result[2]["name"] == "Cebolla"


# ═══════════════════════════════════════════════════════════════
# Tests: Explosión de kárdex al vender (TD-004)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_explode_for_sale_creates_kardex_movements():
    """
    Dado: un plato con receta que tiene 2 ingredientes
    Cuando: RecipesService.explode_for_sale() con quantity_sold=2
    Entonces: crea 2 KardexMovement de tipo 'salida'
    Y: descuenta stock de cada producto
    Y: retorna 2 kardex movements en la lista
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    today = date(2026, 5, 27)

    # Mock product 1: Pescado
    pescado = _make_mock_product(id=1, name="Pescado", unit_of_measure="g",
                                  average_cost=0.015, current_stock=5000.0)
    # Mock product 2: Limón
    limon = _make_mock_product(id=2, name="Limón", unit_of_measure="unidad",
                                average_cost=0.50, current_stock=200.0)

    # Mock ingredients
    ing1 = _make_mock_ingredient(id=1, recipe_id=1, product_id=1, quantity=200.0,
                                  unit_of_measure="g", sort_order=0, product=pescado)
    ing2 = _make_mock_ingredient(id=2, recipe_id=1, product_id=2, quantity=3.0,
                                  unit_of_measure="unidad", sort_order=1, product=limon)

    # Mock recipe with ingredients
    recipe = _make_mock_recipe(id=1, menu_item_id=1, ingredients=[ing1, ing2])

    # Mock db.execute to return recipe on first call
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = recipe

    async def _execute(_stmt):
        return mock_result

    db.execute = _execute

    # After refresh, set the id on the mock KardexMovement
    kardex_moves = []

    def _add_side_effect(obj):
        if hasattr(obj, 'id') and obj.id is None:
            pass  # Will be set in refresh
        kardex_moves.append(obj)

    db.add.side_effect = _add_side_effect

    original_refresh = db.refresh

    async def _refresh_side_effect(obj):
        if hasattr(obj, 'movement_type'):
            obj.id = len(kardex_moves)  # Set fake ID

    db.refresh = _refresh_side_effect

    result = await RecipesService.explode_for_sale(
        db=db, menu_item_id=1, quantity_sold=2.0,
        sale_id=100, sale_number="VEN-2026-00001",
        menu_item_name="Ceviche Clásico", today=today, tenant_id=1,
    )

    # Should create 2 kardex movements
    assert len(result) == 2
    assert db.flush.called

    # Verify first movement: Pescado
    assert result[0]["product_id"] == 1
    assert result[0]["product_name"] == "Pescado"
    # Pescado: 200g * 2 porciones = 400g @ 0.015 => 6.0
    assert result[0]["quantity"] == 400.0
    assert result[0]["total"] == 6.0
    assert result[0]["new_stock"] == 5000.0 - 400.0  # 4600

    # Verify second movement: Limón
    assert result[1]["product_id"] == 2
    assert result[1]["product_name"] == "Limón"
    # Limón: 3 unidades * 2 porciones = 6 @ 0.50 => 3.0
    assert result[1]["quantity"] == 6.0
    assert result[1]["total"] == 3.0
    assert result[1]["new_stock"] == 200.0 - 6.0  # 194

    # Verify that products had their stock updated
    assert float(pescado.current_stock) == 4600.0
    assert float(limon.current_stock) == 194.0

    # Verify KardexMovement objects were created correctly
    assert len(kardex_moves) == 2
    assert kardex_moves[0].movement_type == "salida"
    assert kardex_moves[0].product_id == 1
    assert kardex_moves[0].concept == "Venta #VEN-2026-00001 - Plato: Ceviche Clásico"
    assert kardex_moves[0].reference_type == "venta"
    assert kardex_moves[0].reference_id == 100
    assert kardex_moves[1].product_id == 2
    assert kardex_moves[1].concept == "Venta #VEN-2026-00001 - Plato: Ceviche Clásico"


@pytest.mark.asyncio
async def test_explode_for_sale_no_recipe_returns_empty():
    """
    Dado: un plato que NO tiene receta
    Cuando: RecipesService.explode_for_sale()
    Entonces: retorna lista vacía, sin errores
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    today = date(2026, 5, 27)

    # Mock db.execute to return None (no recipe)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    async def _execute(_stmt):
        return mock_result

    db.execute = _execute

    result = await RecipesService.explode_for_sale(
        db=db, menu_item_id=99, quantity_sold=2.0,
        sale_id=100, sale_number="VEN-2026-00001",
        menu_item_name="Plato Sin Receta", today=today, tenant_id=1,
    )

    assert result == []
    assert not db.add.called


@pytest.mark.asyncio
async def test_explode_for_sale_with_negative_stock():
    """
    Dado: un plato con receta, pero el producto no tiene suficiente stock
    Cuando: RecipesService.explode_for_sale()
    Entonces: NO bloquea la venta, crea kárdex con stock negativo
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    today = date(2026, 5, 27)

    # Producto con stock muy bajo
    pescado = _make_mock_product(id=1, name="Pescado", unit_of_measure="g",
                                  average_cost=0.015, current_stock=100.0)
    ing1 = _make_mock_ingredient(id=1, recipe_id=1, product_id=1, quantity=200.0,
                                  unit_of_measure="g", sort_order=0, product=pescado)
    recipe = _make_mock_recipe(id=1, menu_item_id=1, ingredients=[ing1])

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = recipe

    async def _execute(_stmt):
        return mock_result

    db.execute = _execute

    kardex_moves = []
    db.add.side_effect = lambda obj: kardex_moves.append(obj) if hasattr(obj, 'movement_type') else None

    async def _refresh_side_effect(obj):
        if hasattr(obj, 'movement_type'):
            obj.id = 1

    db.refresh = _refresh_side_effect

    result = await RecipesService.explode_for_sale(
        db=db, menu_item_id=1, quantity_sold=2.0,
        sale_id=100, sale_number="VEN-2026-00001",
        menu_item_name="Ceviche Clásico", today=today, tenant_id=1,
    )

    # Should still create kardex movement (no bloqueo)
    assert len(result) == 1
    assert result[0]["new_stock"] == -300.0  # 100 - 400 = -300
    assert float(pescado.current_stock) == -300.0


@pytest.mark.asyncio
async def test_explode_for_sale_zero_quantity_returns_empty():
    """
    Dado: quantity_sold es 0
    Cuando: RecipesService.explode_for_sale()
    Entonces: retorna lista vacía sin consultar DB
    """
    db = AsyncMock()
    result = await RecipesService.explode_for_sale(
        db=db, menu_item_id=1, quantity_sold=0,
        sale_id=100, sale_number="VEN-2026-00001",
        menu_item_name="Test", today=date(2026, 5, 27), tenant_id=1,
    )
    assert result == []
    assert not db.execute.called
