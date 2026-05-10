"""
Tests para el Kárdex — Control de Inventarios.

Cubre:
  - Registro de productos
  - Entradas con promedio ponderado
  - Salidas valorizadas
  - Cierre de almacén
  - Validaciones (stock insuficiente, etc.)
"""

import pytest
from datetime import date

from app.core.accounting.kardex import KardexEngine, MovementType
from app.core.accounting.engine import EntryType


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> KardexEngine:
    return KardexEngine()


@pytest.fixture
def engine_with_products(engine) -> KardexEngine:
    engine.register_product("ARR-001", "Arroz", "kg")
    engine.register_product("PESC-001", "Pescado", "kg")
    engine.register_product("LIM-001", "Limón", "kg")
    return engine


# ═══════════════════════════════════════════════════════════════
# Tests: Productos
# ═══════════════════════════════════════════════════════════════


class TestProductRegistration:
    def test_register_product(self, engine):
        p = engine.register_product("ARR-001", "Arroz", "kg")
        assert p.code == "ARR-001"
        assert p.name == "Arroz"
        assert p.current_stock == 0
        assert p.average_cost == 0

    def test_register_with_initial_stock(self, engine):
        p = engine.register_product("ARR-001", "Arroz", "kg", initial_stock=50, initial_cost=3.50)
        assert p.current_stock == 50
        assert p.average_cost == 3.50
        assert p.total_value == 175.0

    def test_duplicate_rejected(self, engine):
        engine.register_product("ARR-001", "Arroz")
        with pytest.raises(ValueError, match="ya existe"):
            engine.register_product("ARR-001", "Arroz Premium")

    def test_get_product(self, engine_with_products):
        p = engine_with_products.get_product("ARR-001")
        assert p.name == "Arroz"

    def test_get_missing_product(self, engine):
        with pytest.raises(KeyError):
            engine.get_product("NOEXISTE")


# ═══════════════════════════════════════════════════════════════
# Tests: Entradas (Compras)
# ═══════════════════════════════════════════════════════════════


class TestKardexEntries:
    def test_first_entry_sets_cost(self, engine_with_products):
        record, entry = engine_with_products.record_entry(
            "ARR-001", quantity=50, unit_cost=3.50,
            concept="Compra inicial", movement_date=date(2026, 6, 1),
        )
        assert record.balance_quantity == 50
        assert record.balance_avg_cost == 3.50
        assert record.total == 175.0
        assert record.movement_type == MovementType.ENTRADA

    def test_weighted_average(self, engine_with_products):
        """Prueba el promedio ponderado como en el doc 10-kardex.md."""
        # Primera compra: 50 kg a S/ 3.50
        engine_with_products.record_entry(
            "ARR-001", 50, 3.50, "Compra 1", date(2026, 6, 1),
        )
        # Segunda compra: 30 kg a S/ 4.00
        record2, _ = engine_with_products.record_entry(
            "ARR-001", 30, 4.00, "Compra 2", date(2026, 6, 5),
        )
        # Promedio esperado: (50*3.50 + 30*4.00) / (50+30) = (175+120)/80 = 3.6875
        assert record2.balance_quantity == 80
        assert record2.balance_avg_cost == pytest.approx(3.6875, abs=0.01)
        assert record2.balance_total == pytest.approx(295.0, abs=0.01)

    def test_entry_generates_accounting_journal(self, engine_with_products):
        _, entry = engine_with_products.record_entry(
            "ARR-001", 50, 3.50, "Compra arroz", date(2026, 6, 1),
        )
        assert entry is not None
        assert entry.entry_type == EntryType.COMPRA
        # Debe: 12 Inventarios  /  Haber: 10 Efectivo
        assert any(line.account_code == "12" and line.debit > 0 for line in entry.lines)
        assert any(line.account_code == "10" and line.credit > 0 for line in entry.lines)
        assert entry.is_balanced()

    def test_rejects_zero_quantity(self, engine_with_products):
        with pytest.raises(ValueError, match="> 0"):
            engine_with_products.record_entry("ARR-001", 0, 3.50, "Test", date.today())


# ═══════════════════════════════════════════════════════════════
# Tests: Salidas (Ventas/Mermas)
# ═══════════════════════════════════════════════════════════════


class TestKardexExits:
    def test_sale_valued_at_average(self, engine_with_products):
        # Comprar para tener stock
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        engine_with_products.record_entry("ARR-001", 30, 4.00, "Compra 2", date(2026, 6, 5))

        # Vender 15 kg
        record, entry = engine_with_products.record_exit(
            "ARR-001", quantity=15, concept="Venta ceviche",
            movement_date=date(2026, 6, 7), reference_type="venta",
        )
        # 15 * 3.6875 = 55.31
        assert record.quantity == 15
        assert record.unit_cost == pytest.approx(3.6875, abs=0.01)
        assert record.balance_quantity == 65  # 80 - 15
        assert record.balance_avg_cost == pytest.approx(3.6875, abs=0.01)

    def test_sale_generates_cost_of_sales_entry(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        _, entry = engine_with_products.record_exit(
            "ARR-001", 10, "Venta", date(2026, 6, 3), "venta",
        )
        # Debe: 50 Costo Ventas  /  Haber: 12 Inventarios
        assert any(line.account_code == "50" for line in entry.lines)
        assert any(line.account_code == "12" and line.credit > 0 for line in entry.lines)

    def test_merma_generates_loss_entry(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        _, entry = engine_with_products.record_exit(
            "ARR-001", 5, "Merma", date(2026, 6, 5), "merma",
        )
        assert any(line.account_code == "66" for line in entry.lines)

    def test_insufficient_stock(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 10, 3.50, "Compra", date(2026, 6, 1))
        with pytest.raises(ValueError, match="Stock insuficiente"):
            engine_with_products.record_exit("ARR-001", 20, "Venta", date(2026, 6, 2))


# ═══════════════════════════════════════════════════════════════
# Tests: Inventario Inicial
# ═══════════════════════════════════════════════════════════════


class TestInitialInventory:
    def test_initial_inventory(self, engine_with_products):
        record, entry = engine_with_products.record_initial_inventory(
            "ARR-001", quantity=100, unit_cost=3.00,
            concept="Inventario apertura",
        )
        assert record.balance_quantity == 100
        assert record.balance_avg_cost == 3.00
        assert entry.is_balanced()
        # Debe usar cuenta 30 (Capital) en lugar de 10
        assert any(line.account_code == "30" for line in entry.lines)


# ═══════════════════════════════════════════════════════════════
# Tests: Consultas y Cierre
# ═══════════════════════════════════════════════════════════════


class TestKardexQueries:
    def test_kardex_history(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra 1", date(2026, 6, 1))
        engine_with_products.record_entry("ARR-001", 30, 4.00, "Compra 2", date(2026, 6, 5))
        engine_with_products.record_exit("ARR-001", 15, "Venta", date(2026, 6, 7))
        engine_with_products.record_exit("ARR-001", 10, "Venta 2", date(2026, 6, 10))

        kardex = engine_with_products.get_kardex("ARR-001")
        assert len(kardex) == 4

    def test_total_inventory_value(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        engine_with_products.record_entry("PESC-001", 20, 15.00, "Compra", date(2026, 6, 1))

        total = engine_with_products.get_total_inventory_value()
        expected = (50 * 3.50) + (20 * 15.00)  # 175 + 300 = 475
        assert total == pytest.approx(475.0, abs=0.01)

    def test_cost_of_sales(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        engine_with_products.record_exit("ARR-001", 10, "Venta", date(2026, 6, 3), "venta")
        engine_with_products.record_exit("ARR-001", 5, "Venta", date(2026, 6, 5), "venta")
        engine_with_products.record_exit("ARR-001", 2, "Merma", date(2026, 6, 7), "merma")

        cos = engine_with_products.get_cost_of_sales("ARR-001")
        expected = (10 * 3.50) + (5 * 3.50)  # merma no se cuenta como costo de venta
        assert cos == pytest.approx(52.5, abs=0.05)

    def test_warehouse_close_balanced(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        engine_with_products.record_entry("PESC-001", 20, 15.00, "Compra", date(2026, 6, 1))

        total = engine_with_products.get_total_inventory_value()
        result = engine_with_products.warehouse_close(total)
        assert result["is_balanced"]
        assert result["difference"] == 0

    def test_warehouse_close_mismatch(self, engine_with_products):
        engine_with_products.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))

        result = engine_with_products.warehouse_close(200.0)  # Distinto del real 175
        assert not result["is_balanced"]
        assert result["difference"] != 0


# ═══════════════════════════════════════════════════════════════
# Tests: Escenario del Doc (10-kardex.md)
# ═══════════════════════════════════════════════════════════════


class TestDocScenario:
    """Reproduce el escenario del documento 10-kardex.md."""

    def test_full_kardex_flow(self):
        engine = KardexEngine()
        engine.register_product("ARR-001", "Arroz", "kg")

        # 01-06: Compra 50 kg a S/ 3.50
        r1, _ = engine.record_entry("ARR-001", 50, 3.50, "Compra", date(2026, 6, 1))
        assert r1.balance_quantity == 50
        assert r1.balance_avg_cost == 3.50

        # 03-06: Venta 10 kg
        r2, _ = engine.record_exit("ARR-001", 10, "Venta", date(2026, 6, 3))
        assert r2.balance_quantity == 40
        assert r2.balance_avg_cost == 3.50  # No cambia en salida

        # 05-06: Compra 30 kg a S/ 4.00
        r3, _ = engine.record_entry("ARR-001", 30, 4.00, "Compra 2", date(2026, 6, 5))
        # Promedio: (40*3.50 + 30*4.00) / 70 = (140+120)/70 = 3.7143
        assert r3.balance_quantity == 70
        assert r3.balance_avg_cost == pytest.approx(3.7143, abs=0.01)
        assert r3.balance_total == pytest.approx(260.0, abs=0.01)

        # 07-06: Venta 15 kg
        r4, _ = engine.record_exit("ARR-001", 15, "Venta", date(2026, 6, 7))
        assert r4.balance_quantity == 55
        assert r4.balance_avg_cost == pytest.approx(3.7143, abs=0.01)
        assert r4.balance_total == pytest.approx(204.29, abs=0.05)
