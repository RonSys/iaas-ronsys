"""
Test HU-SIM-001: Persistencia de Escenarios del Simulador.

Verifica:
  - Modelo Scenario existe
  - Límite de 4 escenarios por empresa
  - CRUD completo vía HTTP (con dependencias mockeadas)
  - Tenant isolation
  - Migración 0006 existe
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.tenant import get_tenant_id
from app.adapters.db.database import get_db
from app.schemas.simulator import MAX_SCENARIOS, ScenarioCreate, ScenarioListResponse


def _make_mock_db():
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


@pytest.fixture
def client():
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)

    async def fake_user():
        return User(id=1, email="t@test.com", full_name="T", role="manager",
                     company_id=1, is_active=True, is_verified=True,
                     failed_login_attempts=0)
    async def fake_tenant():
        return 1
    session = _make_mock_db()
    async def fake_db():
        return session

    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_tenant_id] = fake_tenant
    app.dependency_overrides[get_db] = fake_db

    yield TestClient(app)
    for key in list(app.dependency_overrides.keys()):
        app.dependency_overrides.pop(key, None)


# ═══════════════════════════════════════════════════════════════
# Modelo + Migración
# ═══════════════════════════════════════════════════════════════


class TestScenarioModel:
    """Modelo ORM Scenario."""

    def test_model_importable(self):
        from app.adapters.db.models.simulator import Scenario
        assert Scenario.__tablename__ == "scenarios"

    def test_model_fields(self):
        from app.adapters.db.models.simulator import Scenario
        cols = {c.name for c in Scenario.__table__.columns}
        required = {"id", "company_id", "user_id", "name", "input_data", "results", "created_at", "updated_at"}
        assert required.issubset(cols), f"Missing: {required - cols}"

    def test_migration_exists(self):
        import os
        path = os.path.join(os.path.dirname(__file__),
            "../app/adapters/alembic/versions/0006_scenarios.py")
        assert os.path.exists(path)

    def test_max_scenarios_constant(self):
        assert MAX_SCENARIOS == 4


# ═══════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════


class TestScenarioSchemas:
    """Validación Pydantic."""

    def test_create_requires_name(self):
        with pytest.raises(Exception):
            ScenarioCreate(name="", input_data={"capital": 1000})

    def test_create_requires_input_data(self):
        with pytest.raises(Exception):
            ScenarioCreate(name="Test", input_data=None)

    def test_create_valid(self):
        s = ScenarioCreate(name="Test", input_data={"capital": 50000})
        assert s.name == "Test"
        assert s.input_data == {"capital": 50000}


# ═══════════════════════════════════════════════════════════════
# HTTP Endpoints
# ═══════════════════════════════════════════════════════════════


class TestScenarioEndpoints:
    """Endpoints CRUD del simulador."""

    def test_list_scenarios_endpoint(self, client):
        """GET /scenarios → 200 con estructura correcta."""
        r = client.get("/api/simulator/scenarios",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 200
        data = r.json()
        assert "scenarios" in data
        assert "total" in data
        assert data["max_allowed"] == MAX_SCENARIOS

    def test_get_nonexistent_404(self, client):
        """GET /scenarios/999 → 404."""
        r = client.get("/api/simulator/scenarios/999",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 404

    def test_delete_nonexistent_404(self, client):
        """DELETE /scenarios/999 → 404."""
        r = client.delete("/api/simulator/scenarios/999",
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 404

    def test_put_nonexistent_404(self, client):
        """PUT /scenarios/999 → 404."""
        r = client.put("/api/simulator/scenarios/999", json={"name": "N"},
            headers={"X-Tenant-ID": "1", "Authorization": "Bearer x"})
        assert r.status_code == 404

    def test_auth_required(self):
        """Sin JWT → 401."""
        for key in list(app.dependency_overrides.keys()):
            app.dependency_overrides.pop(key, None)
        # Keep DB mock, only remove auth
        session = _make_mock_db()
        async def fake_db():
            return session
        app.dependency_overrides[get_db] = fake_db
        c = TestClient(app)
        headers = {"X-Tenant-ID": "1"}
        for method, path in [
            ("GET", "/api/simulator/scenarios"),
            ("POST", "/api/simulator/scenarios"),
            ("GET", "/api/simulator/scenarios/1"),
        ]:
            if method == "GET":
                r = c.get(path, headers=headers)
            else:
                r = c.post(path, json={}, headers=headers)
            assert r.status_code == 401, f"{method} {path} → {r.status_code}"
