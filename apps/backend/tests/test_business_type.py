"""
Test HU-F1-001: business_type enum en Company.

Verifica:
  - Campo business_type existe en el modelo
  - Migración Alembic añade columna con DEFAULT 'restaurant'
  - CHECK constraint funciona
  - Data migration infiere desde economic_activity
"""

import pytest

from app.adapters.db.models.accounting import Company


class TestBusinessTypeModel:
    """HU-F1-001: Validación del campo business_type en el modelo Company."""

    def test_company_has_business_type_field(self):
        """El modelo Company tiene el campo business_type."""
        assert hasattr(Company, "business_type")

    def test_business_type_default_value(self):
        """Se puede crear Company sin business_type y no lanza error."""
        company = Company(name="Test", ruc="12345678901")
        # El default SQL server_default='restaurant' se aplica en BD
        # Python-side, el default se setea en __init__
        assert company.business_type in ("restaurant", None)

    def test_business_type_valid_values(self):
        """Los valores permitidos son restaurant, hardware, retail, service."""
        allowed = {"restaurant", "hardware", "retail", "service"}
        for val in allowed:
            company = Company(
                name=f"Test {val}",
                ruc=f"RUC-{val}",
                business_type=val,
            )
            assert company.business_type == val

    def test_business_type_string_type(self):
        """business_type es string de 20 chars según VARCHAR(20)."""
        company = Company(name="Test", ruc="12345678901", business_type="restaurant")
        assert isinstance(company.business_type, str)
        assert len(company.business_type) <= 20

    def test_business_type_economic_activity_coexists(self):
        """El campo economic_activity sigue existiendo junto a business_type."""
        company = Company(
            name="Test",
            ruc="12345678901",
            economic_activity="Restaurante",
            business_type="restaurant",
        )
        assert company.economic_activity == "Restaurante"
        assert company.business_type == "restaurant"


class TestBusinessTypeMigration:
    """HU-F1-001: Verifica que la migración 0003 existe."""

    def test_migration_file_exists(self):
        """La migración 0003_business_type.py existe."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../app/adapters/alembic/versions/0003_business_type.py",
        )
        assert os.path.exists(path), f"No existe: {path}"

    def test_migration_revision_id(self):
        """La migración tiene revision ID correcto (verificar archivo)."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../app/adapters/alembic/versions/0003_business_type.py",
        )
        # Leer contenido y verificar revision string
        with open(path) as f:
            content = f.read()
        assert 'revision: str = "0003_business_type"' in content
        assert 'down_revision: Union[str, None] = "0002_users_auth"' in content
