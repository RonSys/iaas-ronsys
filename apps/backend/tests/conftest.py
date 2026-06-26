"""
Fixtures compartidas para todos los tests del backend.
"""

import pytest

# ═══════════════════════════════════════════════════════════════
# Fixtures de dominio
# ═══════════════════════════════════════════════════════════════

from app.core.accounting import InvestmentVariables


@pytest.fixture
def sample_investment() -> InvestmentVariables:
    """Variables típicas para un restaurante pequeño."""
    return InvestmentVariables(
        capital=50000.0,
        loan_amount=30000.0,
        loan_rate_annual=0.12,
        loan_term_months=12,
        equipment_cost=20000.0,
        furniture_cost=5000.0,
        computer_cost=3000.0,
        software_cost=1000.0,
        guarantee_deposit=3000.0,
        initial_inventory=5000.0,
        monthly_sales=[25000.0] * 12,
        monthly_cost_pct=0.40,
        monthly_rent=1500.0,
        monthly_utilities=800.0,
        monthly_salaries=5000.0,
        monthly_marketing=500.0,
        monthly_admin=300.0,
        monthly_maintenance=200.0,
        equipment_life_years=8,
        furniture_life_years=10,
        computer_life_years=5,
        software_life_years=3,
    )


@pytest.fixture
def minimal_vars() -> InvestmentVariables:
    """Variables mínimas para tests unitarios rápidos."""
    return InvestmentVariables(
        capital=10000.0,
        equipment_cost=5000.0,
        monthly_sales=[1000.0] * 3,
        monthly_cost_pct=0.40,
        monthly_rent=200.0,
        monthly_salaries=300.0,
    )
