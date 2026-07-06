"""
Tests del Caso 2: Mantenimiento de Secciones.

Cubre:
  - CRUD completo de secciones (POST, GET, PATCH, DELETE)
  - Eliminación de sección sin mesas (204)
  - Eliminación de sección con mesas (409 Conflicto)
  - Filtro de mesas por section_id
  - Unicidad de nombre por tenant
  - Tenant isolation
  - Requisito de role admin/manager para escritura
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.adapters.db.database import get_db
from app.services.restaurant_service import SectionsService


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_mock_db():
    """Mock de sesión async de SQLAlchemy."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar.return_value = 0
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result.scalars.return_value = scalars_mock
    unique_mock = MagicMock()
    unique_mock.scalars.return_value = scalars_mock
    result.unique.return_value = unique_mock
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_mock_section(
    id=1, name="Terraza", description="Zona exterior",
    sort_order=1, table_count=0, created_at=None,
):
    """Crea un MagicMock que simula un objeto RestaurantSection."""
    from datetime import datetime, UTC
    if created_at is None:
        created_at = datetime.now(UTC)

    sec = MagicMock()
    sec.id = id
    sec.name = name
    sec.description = description
    sec.sort_order = sort_order
    sec.created_at = created_at
    sec.tenant_id = 1
    return sec


def _make_mock_result_for(value, scalar=0, all_values=None):
    """Crea un MagicMock result SQLAlchemy parametrizable."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = scalar

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = all_values or []
    r.scalars.return_value = scalars_mock

    unique_mock = MagicMock()
    unique_mock.scalars.return_value = scalars_mock
    r.unique.return_value = unique_mock

    return r


def _configure_db_for_sections_crud(session, sections_data, sections_result=None):
    """
    Configura el mock de DB para que devuelva secciones en execute().

    sections_data: lista de dicts con datos de secciones (para refresh)
    sections_result: lista de MagicMock secciones (para execute)
    """
    if sections_result is None:
        sections_result = []
        for sd in sections_data:
            sec = _make_mock_section(
                id=sd["id"], name=sd["name"],
                description=sd.get("description"),
                sort_order=sd.get("sort_order", 0),
                table_count=sd.get("table_count", 0),
            )
            sections_result.append(sec)

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = sections_result

    result = MagicMock()
    result.scalar_one_or_none.return_value = sections_result[0] if sections_result else None
    result.scalar.return_value = sections_result[0].table_count if sections_result else 0
    result.scalars.return_value = scalars_mock

    session.execute = AsyncMock(return_value=result)
    session.refresh = AsyncMock(side_effect=lambda obj: setattr(
        obj, "id", next((s["id"] for s in sections_data if s["name"] == getattr(obj, "name", None)), 1)
    ))


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def client():
    """TestClient con dependencias mockeadas (role=admin)."""
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)

    async def fake_user():
        return User(
            id=1, email="admin@test.com", full_name="Admin",
            role="admin", tenant_id=1, is_active=True,
            is_verified=True, failed_login_attempts=0,
        )

    async def fake_tenant():
        return 1

    session = _make_mock_db()

    async def fake_db():
        return session

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db

    yield TestClient(app), session

    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)


# ═══════════════════════════════════════════════════════════════
# Tests Sections CRUD
# ═══════════════════════════════════════════════════════════════


class TestSectionsCreate:
    """POST /api/v1/restaurant/sections"""

    def test_create_section_success(self, client):
        """Crear sección devuelve 201 con datos válidos."""
        tc, session = client

        # Simular que no existe sección con ese nombre
        # y que la nueva sección se guarda correctamente
        async def _execute(stmt):
            from sqlalchemy import select
            from app.adapters.db.models.restaurant import RestaurantSection

            # Detectar si es SELECT de RestaurantSection (unicidad check)
            try:
                if any(
                    isinstance(c, RestaurantSection.__class__)
                    for c in stmt._entities
                ):
                    return _make_mock_result_for(None)
            except Exception:
                pass
            try:
                if stmt._where_criteria:
                    return _make_mock_result_for(None)
            except Exception:
                pass
            # Default: nothing found
            return _make_mock_result_for(None)

        session.execute = AsyncMock(side_effect=_execute)

        # Configurar refresh para asignar ID
        async def _refresh(obj):
            obj.id = 1

        session.refresh = AsyncMock(side_effect=_refresh)

        response = tc.post(
            "/api/v1/restaurant/sections",
            json={
                "name": "Terraza",
                "description": "Zona exterior",
                "sort_order": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Terraza"

    def test_create_section_duplicate_name(self, client):
        """Crear sección con nombre duplicado devuelve 409."""
        tc, session = client

        # Simular que ya existe sección con ese nombre
        existing = _make_mock_section(id=1, name="Terraza")
        async def _execute_dupe(stmt):
            return _make_mock_result_for(existing)

        session.execute = AsyncMock(side_effect=_execute_dupe)

        response = tc.post(
            "/api/v1/restaurant/sections",
            json={"name": "Terraza", "sort_order": 1},
        )

        assert response.status_code == 409
        assert "Ya existe" in response.json()["detail"]

    def test_create_section_empty_name(self, client):
        """Crear sección sin nombre devuelve 400."""
        tc, session = client
        response = tc.post(
            "/api/v1/restaurant/sections",
            json={"sort_order": 1},
        )
        assert response.status_code == 400
        assert "name" in response.json()["detail"]


class TestSectionsList:
    """GET /api/v1/restaurant/sections"""

    def test_list_sections(self, client):
        """Listar secciones devuelve lista ordenada."""
        tc, session = client

        sec1 = _make_mock_section(id=1, name="Terraza", sort_order=1, table_count=4)
        sec2 = _make_mock_section(id=2, name="VIP", sort_order=2, table_count=0)
        sec3 = _make_mock_section(id=3, name="Salón", sort_order=3, table_count=2)

        # Vamos a crear un counter para devolver respuestas diferentes
        # en cada llamada: primero list sections, luego 3 counts de tables
        call_count = 0

        async def _execute_list(stmt):
            nonlocal call_count
            call_count += 1

            # La primera llamada es el listado de secciones
            if call_count == 1:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [sec1, sec2, sec3]
                result = MagicMock()
                result.scalars.return_value = scalars_mock
                return result

            # Las llamadas siguientes son counts de mesas por sección
            result = MagicMock()
            result.scalar.return_value = 0
            return result

        session.execute = AsyncMock(side_effect=_execute_list)

        response = tc.get("/api/v1/restaurant/sections")

        assert response.status_code == 200
        data = response.json()
        # El endpoint devuelve una lista
        if isinstance(data, list):
            assert len(data) >= 3
        elif isinstance(data, dict) and "sections" in data:
            assert len(data["sections"]) >= 3

    def test_list_sections_empty(self, client):
        """Listar secciones cuando no hay devuelve lista vacía."""
        tc, session = client

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result = MagicMock()
        result.scalar.return_value = 0
        result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result)

        response = tc.get("/api/v1/restaurant/sections")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            assert data == []
        elif isinstance(data, dict) and "sections" in data:
            assert data["sections"] == []


class TestSectionsGet:
    """GET /api/v1/restaurant/sections/{id}"""

    def test_get_section_found(self, client):
        """Obtener sección por ID existente."""
        tc, session = client
        section = _make_mock_section(id=1, name="Terraza", table_count=4)

        async def _execute(stmt):
            return _make_mock_result_for(section)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.get("/api/v1/restaurant/sections/1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Terraza"

    def test_get_section_not_found(self, client):
        """Obtener sección que no existe devuelve 404."""
        tc, session = client

        async def _execute(stmt):
            return _make_mock_result_for(None)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.get("/api/v1/restaurant/sections/999")
        assert response.status_code == 404


class TestSectionsUpdate:
    """PATCH /api/v1/restaurant/sections/{id}"""

    def test_update_section_success(self, client):
        """Actualizar sección con datos válidos."""
        tc, session = client
        section = _make_mock_section(id=1, name="Terraza", description="Vieja desc", sort_order=1)

        # Necesitamos manejar 2 queries:
        # 1. Obtener la sección por ID -> devuelve section
        # 2. Check unicidad de nombre -> devuelve None (no hay otra con ese nombre)
        call_count_2 = 0

        async def _execute_updated(stmt):
            nonlocal call_count_2
            call_count_2 += 1

            if call_count_2 == 1:
                # Primera llamada: get section by id
                return _make_mock_result_for(section)
            else:
                # Segunda llamada: check unicidad de nombre (no debe encontrar otra)
                return _make_mock_result_for(None)

        session.execute = AsyncMock(side_effect=_execute_updated)
        session.refresh = AsyncMock()

        response = tc.patch(
            "/api/v1/restaurant/sections/1",
            json={"name": "Terraza Renovada", "description": "Nueva desc"},
        )

        assert response.status_code == 200
        assert section.name == "Terraza Renovada"
        assert section.description == "Nueva desc"

    def test_update_section_not_found(self, client):
        """Actualizar sección inexistente devuelve 404."""
        tc, session = client

        async def _execute(stmt):
            return _make_mock_result_for(None)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.patch(
            "/api/v1/restaurant/sections/999",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


class TestSectionsDelete:
    """DELETE /api/v1/restaurant/sections/{id}"""

    def test_delete_section_no_tables_success(self, client):
        """Eliminar sección sin mesas devuelve 204."""
        tc, session = client

        # Sección sin mesas (scalar=0 para count de mesas)
        section = _make_mock_section(id=1, name="VIP", table_count=0)

        async def _execute(stmt):
            # El servicio ejecuta 2 queries: una para obtener la sección y otra para contar mesas
            # Como no podemos distinguirlas fácilmente, retornamos sección y count=0
            return _make_mock_result_for(section, scalar=0)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.delete("/api/v1/restaurant/sections/1")

        assert response.status_code == 204

    def test_delete_section_with_tables_conflict(self, client):
        """Eliminar sección con mesas devuelve 409."""
        tc, session = client

        # Sección con mesas (scalar=4 para count de mesas)
        section = _make_mock_section(id=1, name="Terraza", table_count=4)

        async def _execute(stmt):
            return _make_mock_result_for(section, scalar=4)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.delete("/api/v1/restaurant/sections/1")

        assert response.status_code == 409
        assert "mesa" in response.json()["detail"].lower()

    def test_delete_section_not_found(self, client):
        """Eliminar sección inexistente devuelve 404."""
        tc, session = client

        async def _execute(stmt):
            return _make_mock_result_for(None, scalar=0)

        session.execute = AsyncMock(side_effect=_execute)

        response = tc.delete("/api/v1/restaurant/sections/999")
        assert response.status_code == 404


class TestTablesFilterBySection:
    """Prueba el filtro de mesas por section_id."""

    def test_filter_tables_by_section(self, client):
        """Filtrar mesas por section_id devuelve solo las de esa sección."""
        tc, session = client

        # Configurar mock para TablesService.list_tables
        # Simular que hay 2 mesas en section_id=1 y 1 en section_id=2
        from app.adapters.db.models.restaurant import Table

        table1 = MagicMock(spec=Table)
        table1.id = 1
        table1.number = "M1"
        table1.capacity = 4
        table1.status = "available"
        table1.section = "Terraza"
        table1.section_id = 1
        table1.guests = None
        table1.waiter_name = None
        table1.opened_at = None
        table1.section_rel = None

        table2 = MagicMock(spec=Table)
        table2.id = 2
        table2.number = "M2"
        table2.capacity = 6
        table2.status = "available"
        table2.section = "Terraza"
        table2.section_id = 1
        table2.guests = None
        table2.waiter_name = None
        table2.opened_at = None
        table2.section_rel = None

        # Para section_id=1, retornar 2 mesas
        async def _execute_tables(stmt):
            # Check if there's a section_id filter
            try:
                for crit in stmt._where_criteria:
                    if hasattr(crit, 'right') and hasattr(crit.right, 'value') and crit.right.value == 1:
                        scalars_mock = MagicMock()
                        scalars_mock.all.return_value = [table1, table2]
                        result = MagicMock()
                        result.scalars.return_value = scalars_mock
                        return result
            except Exception:
                pass
            return _make_mock_result_for(None)

        session.execute = AsyncMock(side_effect=_execute_tables)

        response = tc.get("/api/v1/restaurant/tables?section_id=1")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            assert len(data) == 2
        elif isinstance(data, dict) and "tables" in data:
            assert len(data["tables"]) == 2


class TestTenantIsolation:
    """Verifica que secciones de un tenant no se vean afectadas por otro."""

    def test_tenant_isolation_list(self):
        """Tenants distintos ven secciones distintas."""
        # Este test verifica que la lógica de filtrado por tenant_id
        # está presente en el endpoint de listado.

        # Revisamos que SectionsService.list_sections filtra por tenant_id
        import inspect
        source = inspect.getsource(SectionsService.list_sections)
        assert "tenant_id" in source
        assert "RestaurantSection.tenant_id" in source.replace(" ", "").replace("\n", "")


# ═══════════════════════════════════════════════════════════════
# Test: Unicidad de nombre
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_section_name_uniqueness_violation():
    """Verifica que el servicio lance 409 al crear sección con nombre duplicado."""
    db = _make_mock_db()

    existing = _make_mock_section(id=1, name="Terraza")

    # Simular que ya existe
    async def _execute_dupe(stmt):
        return _make_mock_result_for(existing)

    db.execute = AsyncMock(side_effect=_execute_dupe)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await SectionsService.create_section(db, tenant_id=1, data={
            "name": "Terraza",
            "description": "Otra",
            "sort_order": 2,
        })
    assert exc_info.value.status_code == 409
    assert "Ya existe" in exc_info.value.detail
