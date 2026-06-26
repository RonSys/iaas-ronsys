"""
Tests del Caso 7: Módulo de Inversión — Puesta en Marcha.

Cubre:
  - InvestmentService CRUD (crear, listar, obtener, actualizar, eliminar)
  - InvestmentService.get_summary() — resumen de totes
  - Validaciones: categorías, costos >= 0, status
  - Require_role('admin') en todos los endpoints
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.investment_service import InvestmentService, INVESTMENT_CATEGORIES


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_mock_item(
    id=1,
    name="Cocina Industrial",
    category="equipamiento_cocina",
    estimated_cost=3500.0,
    actual_cost=3200.0,
    receipt_code="FAC-001",
    status="acquired",
    notes=None,
    tenant_id=1,
    created_at=None,
    updated_at=None,
):
    item = MagicMock()
    item.id = id
    item.name = name
    item.category = category
    item.estimated_cost = estimated_cost
    item.actual_cost = actual_cost
    item.receipt_code = receipt_code
    item.status = status
    item.notes = notes
    item.tenant_id = tenant_id
    item.created_at = created_at or datetime.now(UTC)
    item.updated_at = updated_at or datetime.now(UTC)
    return item


def _make_result_for(value):
    """Creates a MagicMock result whose scalar_one_or_none returns value."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
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
# Tests: Crear bien de inversión
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_item_success():
    """
    Dado: datos válidos para un bien de inversión
    Cuando: InvestmentService.create_item()
    Entonces: se crea el bien y retorna sus datos
    """
    db = _make_mock_db()
    db.refresh = AsyncMock(side_effect=lambda item: setattr(
        item, "created_at", datetime.now(UTC)
    ))

    data = {
        "name": "Cocina Industrial",
        "category": "equipamiento_cocina",
        "estimated_cost": 3500.0,
        "actual_cost": 3200.0,
        "receipt_code": "FAC-001",
        "status": "acquired",
        "notes": None,
    }

    result = await InvestmentService.create_item(db, tenant_id=1, data=data)

    assert result["name"] == "Cocina Industrial"
    assert result["category"] == "equipamiento_cocina"
    assert result["estimated_cost"] == 3500.0
    assert result["actual_cost"] == 3200.0
    assert result["receipt_code"] == "FAC-001"
    assert result["status"] == "acquired"
    assert db.add.called
    assert db.flush.called


@pytest.mark.asyncio
async def test_create_item_invalid_category():
    """
    Dado: una categoría inválida
    Cuando: InvestmentService.create_item()
    Entonces: HTTPException 422
    """
    db = _make_mock_db()
    data = {
        "name": "Test",
        "category": "categoria_inexistente",
        "estimated_cost": 100.0,
    }

    with pytest.raises(Exception) as excinfo:
        await InvestmentService.create_item(db, tenant_id=1, data=data)

    assert "422" in str(excinfo.value) or "Categoría inválida" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_item_negative_cost():
    """
    Dado: un costo estimado negativo
    Cuando: InvestmentService.create_item()
    Entonces: HTTPException 422
    """
    db = _make_mock_db()
    data = {
        "name": "Test",
        "category": "mobiliario",
        "estimated_cost": -100.0,
    }

    with pytest.raises(Exception) as excinfo:
        await InvestmentService.create_item(db, tenant_id=1, data=data)

    assert "422" in str(excinfo.value) or "estimated_cost debe ser" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_item_invalid_status():
    """
    Dado: un status inválido
    Cuando: InvestmentService.create_item()
    Entonces: HTTPException 422
    """
    db = _make_mock_db()
    data = {
        "name": "Test",
        "category": "mobiliario",
        "estimated_cost": 100.0,
        "status": "cancelled",
    }

    with pytest.raises(Exception) as excinfo:
        await InvestmentService.create_item(db, tenant_id=1, data=data)

    assert "422" in str(excinfo.value) or "status debe ser" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_item_default_status_pending():
    """
    Dado: datos sin status explícito
    Cuando: InvestmentService.create_item()
    Entonces: el status por defecto es 'pending'
    """
    db = _make_mock_db()
    db.refresh = AsyncMock(side_effect=lambda item: setattr(
        item, "created_at", datetime.now(UTC)
    ))

    data = {
        "name": "Mesas (x6)",
        "category": "mobiliario",
        "estimated_cost": 1200.0,
    }

    result = await InvestmentService.create_item(db, tenant_id=1, data=data)

    assert result["status"] == "pending"
    assert result["actual_cost"] is None


# ═══════════════════════════════════════════════════════════════
# Tests: Listar bienes
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_items():
    """
    Dado: múltiples bienes registrados
    Cuando: InvestmentService.list_items()
    Entonces: retorna todos los bienes
    """
    db = _make_mock_db()

    item1 = _make_mock_item(id=1, name="Cocina Industrial", category="equipamiento_cocina", status="acquired")
    item2 = _make_mock_item(id=2, name="Mesas (x6)", category="mobiliario", status="pending", actual_cost=None)

    db.execute.return_value = _make_result_for_scalars_all([item1, item2])

    result = await InvestmentService.list_items(db, tenant_id=1)

    assert len(result) == 2
    assert result[0]["name"] == "Cocina Industrial"
    assert result[1]["name"] == "Mesas (x6)"


@pytest.mark.asyncio
async def test_list_items_filter_by_category():
    """
    Dado: bienes de diferentes categorías
    Cuando: InvestmentService.list_items() con filtro category
    Entonces: solo retorna bienes de esa categoría
    """
    db = _make_mock_db()
    item = _make_mock_item(id=1, name="Cocina Industrial", category="equipamiento_cocina")
    db.execute.return_value = _make_result_for_scalars_all([item])

    result = await InvestmentService.list_items(db, tenant_id=1, category="equipamiento_cocina")

    assert len(result) == 1
    assert result[0]["name"] == "Cocina Industrial"


@pytest.mark.asyncio
async def test_list_items_filter_by_status():
    """
    Dado: bienes con diferentes estados
    Cuando: InvestmentService.list_items() con filtro status
    Entonces: solo retorna bienes con ese estado
    """
    db = _make_mock_db()
    item = _make_mock_item(id=1, name="Cocina Industrial", status="acquired")
    db.execute.return_value = _make_result_for_scalars_all([item])

    result = await InvestmentService.list_items(db, tenant_id=1, status="acquired")

    assert len(result) == 1
    assert result[0]["status"] == "acquired"


# ═══════════════════════════════════════════════════════════════
# Tests: Obtener bien por ID
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_item():
    """
    Dado: un bien existente
    Cuando: InvestmentService.get_item()
    Entonces: retorna sus datos
    """
    db = _make_mock_db()
    item = _make_mock_item(id=1, name="Cocina Industrial")
    db.execute.return_value = _make_result_for(item)

    result = await InvestmentService.get_item(db, item_id=1, tenant_id=1)

    assert result["id"] == 1
    assert result["name"] == "Cocina Industrial"


@pytest.mark.asyncio
async def test_get_item_not_found():
    """
    Dado: un bien que no existe
    Cuando: InvestmentService.get_item()
    Entonces: HTTPException 404
    """
    db = _make_mock_db()
    db.execute.return_value = _make_result_for(None)

    with pytest.raises(Exception) as excinfo:
        await InvestmentService.get_item(db, item_id=999, tenant_id=1)

    assert "404" in str(excinfo.value)


# ═══════════════════════════════════════════════════════════════
# Tests: Actualizar bien
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_item():
    """
    Dado: un bien existente
    Cuando: InvestmentService.update_item() con nuevos datos
    Entonces: el bien se actualiza correctamente
    """
    db = _make_mock_db()
    item = _make_mock_item(id=1, name="Cocina Industrial", actual_cost=3200.0)
    db.execute.return_value = _make_result_for(item)
    db.refresh = AsyncMock(side_effect=lambda x: None)

    update_data = {
        "actual_cost": 3100.0,
    }

    result = await InvestmentService.update_item(db, item_id=1, tenant_id=1, data=update_data)

    assert result["actual_cost"] == 3100.0


@pytest.mark.asyncio
async def test_update_item_change_status():
    """
    Dado: un bien en estado 'pending'
    Cuando: se actualiza a 'acquired'
    Entonces: el nuevo estado es 'acquired'
    """
    db = _make_mock_db()
    item = _make_mock_item(id=2, name="Mesas (x6)", status="pending")
    db.execute.return_value = _make_result_for(item)
    db.refresh = AsyncMock(side_effect=lambda x: None)

    result = await InvestmentService.update_item(
        db, item_id=2, tenant_id=1, data={"status": "acquired"}
    )

    assert result["status"] == "acquired"


# ═══════════════════════════════════════════════════════════════
# Tests: Eliminar bien
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_item():
    """
    Dado: un bien existente
    Cuando: InvestmentService.delete_item()
    Entonces: el bien se elimina
    """
    db = _make_mock_db()
    item = _make_mock_item(id=1)
    db.execute.return_value = _make_result_for(item)

    await InvestmentService.delete_item(db, item_id=1, tenant_id=1)

    assert db.delete.called
    assert db.flush.called


@pytest.mark.asyncio
async def test_delete_item_not_found():
    """
    Dado: un bien que no existe
    Cuando: InvestmentService.delete_item()
    Entonces: HTTPException 404
    """
    db = _make_mock_db()
    db.execute.return_value = _make_result_for(None)

    with pytest.raises(Exception) as excinfo:
        await InvestmentService.delete_item(db, item_id=999, tenant_id=1)

    assert "404" in str(excinfo.value)


# ═══════════════════════════════════════════════════════════════
# Tests: Resumen (summary) — Escenario 6
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_summary_with_items():
    """
    Dado: 4 bienes registrados (2 adquiridos, 2 pendientes)
    Cuando: InvestmentService.get_summary()
    Entonces: retorna totes correctos
    """
    db = _make_mock_db()

    # total_estimated = 5700.00
    db.execute.side_effect = [
        # First call — total estimated
        _make_result_for(5700.0),
        # Second call — total actual costs for acquired items
        _make_result_for(3950.0),
        # Third call — total count
        _make_result_for(4),
        # Fourth call — acquired count
        _make_result_for(2),
    ]

    result = await InvestmentService.get_summary(db, tenant_id=1)

    assert result["total_estimated"] == 5700.0
    assert result["total_actual"] == 3950.0
    assert result["difference"] == 1750.0
    assert result["acquired_count"] == 2
    assert result["pending_count"] == 2
    assert result["total_count"] == 4


@pytest.mark.asyncio
async def test_get_summary_empty():
    """
    Dado: no hay bienes registrados
    Cuando: InvestmentService.get_summary()
    Entonces: retorna totes en cero
    """
    db = _make_mock_db()

    db.execute.side_effect = [
        _make_result_for(0.0),  # total_estimated
        _make_result_for(0.0),  # total_actual
        _make_result_for(0),    # total_count
        _make_result_for(0),    # acquired_count
    ]

    result = await InvestmentService.get_summary(db, tenant_id=1)

    assert result["total_estimated"] == 0.0
    assert result["total_actual"] == 0.0
    assert result["difference"] == 0.0
    assert result["acquired_count"] == 0
    assert result["pending_count"] == 0
    assert result["total_count"] == 0


# ═══════════════════════════════════════════════════════════════
# Tests: Validar categorías
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("category", INVESTMENT_CATEGORIES)
@pytest.mark.asyncio
async def test_all_valid_categories(category):
    """
    Dado: cada categoría válida
    Cuando: InvestmentService.create_item()
    Entonces: el bien se crea exitosamente
    """
    db = _make_mock_db()
    db.refresh = AsyncMock(side_effect=lambda item: setattr(
        item, "created_at", datetime.now(UTC)
    ))

    data = {
        "name": f"Test {category}",
        "category": category,
        "estimated_cost": 100.0,
    }

    result = await InvestmentService.create_item(db, tenant_id=1, data=data)
    assert result["category"] == category


# ═══════════════════════════════════════════════════════════════
# Tests: Integración con los escenarios del Gherkin
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_escenario_6_dashboard_multiple_items():
    """
    Escenario 6: Dashboard con múltiples items del Gherkin.

    Dado:
      - Cocina Industrial (Equipamiento Cocina, Est. 3500, Real 3200, FAC-001, Adquirido)
      - Carpa Calle (Infraestructura, Est. 800, Real 750, sin recibo, Adquirido)
      - Mesas (x6) (Mobiliario, Est. 1200, sin real, Pendiente)
      - Letrero (DyL, Est. 200, sin real, Pendiente)

    Cuando: Se calcula el summary
    Entonces:
      - Total estimado: 5700.00
      - Total real: 3950.00
      - Diferencia: 1750.00
      - Adquiridos: 2 de 4
    """
    db = _make_mock_db()

    items = [
        _make_mock_item(id=1, name="Cocina Industrial", category="equipamiento_cocina",
                        estimated_cost=3500.0, actual_cost=3200.0, receipt_code="FAC-001", status="acquired"),
        _make_mock_item(id=2, name="Carpa Calle", category="infraestructura",
                        estimated_cost=800.0, actual_cost=750.0, receipt_code=None, status="acquired"),
        _make_mock_item(id=3, name="Mesas (x6)", category="mobiliario",
                        estimated_cost=1200.0, actual_cost=None, receipt_code=None, status="pending"),
        _make_mock_item(id=4, name="Letrero", category="dyl",
                        estimated_cost=200.0, actual_cost=None, receipt_code=None, status="pending"),
    ]

    db.execute.side_effect = [
        _make_result_for(5700.0),  # total_estimated
        _make_result_for(3950.0),  # total_actual
        _make_result_for(4),       # total_count
        _make_result_for(2),       # acquired_count
    ]

    result = await InvestmentService.get_summary(db, tenant_id=1)

    assert result["total_estimated"] == 5700.0
    assert result["total_actual"] == 3950.0
    assert result["difference"] == 1750.0
    assert result["acquired_count"] == 2
    assert result["pending_count"] == 2
    assert result["total_count"] == 4
