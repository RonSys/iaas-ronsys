"""
Tests Spec 08 — F5.3 "API de costos IA" (backend, mock-based como F5).

Cubre (aprobado Ron, alcance acotado — sin BD en el pipeline):
  - Seguridad: solo admin puede ver costos (dato sensible) → viewer 403.
  - Rango default: sin from/to → últimos 30 días (patrón R9).
  - Agregación de ambas fuentes: query_logs (costo estimado por tokens) +
    call_records.cost_usd (costo real F3) → total + by_source.
  - Validación: from > to → 422.

Regla dura (precedente F2 D4): ningún test usa números personales del agente.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.dependencies import require_role
from app.models.user import User
from app.routers.assistant import costs

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _admin_user() -> User:
    return User(
        id=1, email="admin@iaasronsys.com", full_name="Admin",
        role="admin", company_id=1, is_active=True, is_verified=True,
        failed_login_attempts=0,
    )


def _viewer_user() -> User:
    return User(
        id=2, email="viewer@iaasronsys.com", full_name="Viewer",
        role="viewer", company_id=1, is_active=True, is_verified=True,
        failed_login_attempts=0,
    )


class _FakeMappings:
    """Fake de execute().mappings().all() — patrón test_f5_assistant.py."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


def _run_costs(db, *, from_date=None, to_date=None, user=None):
    return asyncio.run(costs(
        from_date=from_date,
        to_date=to_date,
        tenant_id=1,
        current_user=user or _admin_user(),
        db=db,
    ))


# ═══════════════════════════════════════════════════════════════
# Seguridad (solo admin)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_costs_requires_admin():
    """F5.3: rol viewer → 403 (require_role('admin') rechaza)."""
    with pytest.raises(HTTPException) as exc:
        await require_role("admin")(_viewer_user())
    assert exc.value.status_code == 403


# ═══════════════════════════════════════════════════════════════
# Rango default (R9 — últimos 30 días)
# ═══════════════════════════════════════════════════════════════

def test_costs_default_range_30d():
    """F5.3: sin from/to → date_from = hoy-29, date_to = hoy."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_FakeMappings([]))
    resp = _run_costs(db)
    assert resp.date_from == date.today() - timedelta(days=29)
    assert resp.date_to == date.today()
    assert resp.total_cost_usd == 0.0
    assert resp.by_source == {}
    assert resp.items == []


# ═══════════════════════════════════════════════════════════════
# Agregación de ambas fuentes
# ═══════════════════════════════════════════════════════════════

def test_costs_aggregates_both_sources():
    """F5.3: query_logs (assistant) + call_records (voice_ai) → total/by_source.

    assistant: 20000 tokens → 20000 * 0.0005 / 1000 = $0.01
               5000 tokens  → 5000 * 0.0005 / 1000  = $0.0025
    voice_ai:  cost_usd real = $0.05
    """
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _FakeMappings([
            {"day": date(2026, 8, 1), "requests": 10, "tokens": 20000},
            {"day": date(2026, 8, 2), "requests": 5, "tokens": 5000},
        ]),
        _FakeMappings([
            {"day": date(2026, 8, 1), "requests": 3, "cost": Decimal("0.0500")},
        ]),
    ])
    resp = _run_costs(db, from_date=date(2026, 8, 1), to_date=date(2026, 8, 2))

    assert resp.tenant_id == 1
    assert resp.date_from == date(2026, 8, 1)
    assert resp.date_to == date(2026, 8, 2)
    assert resp.total_cost_usd == pytest.approx(0.0625)
    assert resp.by_source == {"assistant": pytest.approx(0.0125), "voice_ai": 0.05}
    # orden por (date, source)
    assert [(it.date, it.source) for it in resp.items] == [
        (date(2026, 8, 1), "assistant"),
        (date(2026, 8, 1), "voice_ai"),
        (date(2026, 8, 2), "assistant"),
    ]
    assert resp.items[0].requests == 10
    assert resp.items[0].tokens_used == 20000
    assert resp.items[0].cost_usd == pytest.approx(0.01)
    assert resp.items[1].tokens_used is None  # voice_ai no usa tokens
    assert resp.items[1].cost_usd == pytest.approx(0.05)


# ═══════════════════════════════════════════════════════════════
# Validación de rango
# ═══════════════════════════════════════════════════════════════

def test_costs_from_gt_to_422():
    """F5.3: from > to → HTTP 422 sin tocar la BD."""
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        _run_costs(db, from_date=date(2026, 8, 13), to_date=date(2026, 8, 1))
    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()
