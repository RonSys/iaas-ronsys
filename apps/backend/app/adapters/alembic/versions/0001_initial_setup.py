"""${message}

Revision ID: 0001_initial
Revises: None
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Companies ───────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("ruc", sa.String(20), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("economic_activity", sa.String(200), nullable=True),
        sa.Column("setup_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ruc"),
    )

    # ─── Accounts ────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("parent_code", sa.String(10), nullable=True),
        sa.Column("nature", sa.String(1), nullable=False, server_default="D"),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("is_balance_sheet", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["parent_code"], ["accounts.code"]),
    )
    op.create_index("ix_accounts_code", "accounts", ["code"])

    # ─── Journal Entries ─────────────────────────────────
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("entry_number", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("idx_journal_entries_c_d", "journal_entries", ["company_id", "date"])

    # ─── Journal Entry Lines ─────────────────────────────
    op.create_table(
        "journal_entry_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.String(10), nullable=False),
        sa.Column("debit", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["entry_id"], ["journal_entries.id"]),
        sa.ForeignKeyConstraint(["account_code"], ["accounts.code"]),
    )
    op.create_index("idx_jel_entry_id", "journal_entry_lines", ["entry_id"])

    # ─── Products ────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_of_measure", sa.String(10), nullable=False, server_default="kg"),
        sa.Column("current_stock", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("average_cost", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )

    # ─── Kardex Movements ────────────────────────────────
    op.create_table(
        "kardex_movements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(10), nullable=False),
        sa.Column("concept", sa.String(200), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_avg_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("balance_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
    )
    op.create_index("idx_kardex_p_d", "kardex_movements", ["product_id", "date"])

    # ─── Seed: plan de cuentas ───────────────────────────
    _seed_accounts(op)


def downgrade() -> None:
    op.drop_table("kardex_movements")
    op.drop_table("products")
    op.drop_table("journal_entry_lines")
    op.drop_table("journal_entries")
    op.drop_table("accounts")
    op.drop_table("companies")


def _seed_accounts(op) -> None:
    """Inserta el plan de cuentas PCGE adaptado."""
    accounts = [
        # Activo
        ("10", "Efectivo y Equivalentes", None, "D", "asset", True),
        ("101", "Caja", "10", "D", "asset", True),
        ("102", "Bancos", "10", "D", "asset", True),
        ("11", "Cuentas por Cobrar", None, "D", "asset", True),
        ("12", "Inventarios", None, "D", "asset", True),
        ("121", "Insumos de cocina", "12", "D", "asset", True),
        ("13", "Inmuebles, Maquinaria y Equipo", None, "D", "asset", True),
        ("131", "Equipamiento de cocina", "13", "D", "asset", True),
        ("132", "Mobiliario del local", "13", "D", "asset", True),
        ("133", "Equipos de cómputo", "13", "D", "asset", True),
        ("14", "Activos Intangibles", None, "D", "asset", True),
        ("141", "Software (ERP, licencias)", "14", "D", "asset", True),
        ("142", "Marca y derechos", "14", "D", "asset", True),
        ("15", "Depósitos en Garantía", None, "D", "asset", True),
        ("151", "Garantía de alquiler", "15", "D", "asset", True),
        ("19", "Depreciación Acumulada", None, "A", "contra_asset", True),
        ("191", "Dep. Acum. Equipamiento cocina", "19", "A", "contra_asset", True),
        ("192", "Dep. Acum. Mobiliario", "19", "A", "contra_asset", True),
        ("193", "Dep. Acum. Equipos cómputo", "19", "A", "contra_asset", True),
        # Pasivo
        ("20", "Tributos por Pagar", None, "A", "liability", True),
        ("201", "IGV por pagar", "20", "A", "liability", True),
        ("202", "Impuesto a la Renta por pagar", "20", "A", "liability", True),
        ("21", "Cuentas por Pagar Comerciales", None, "A", "liability", True),
        ("22", "Préstamos Bancarios", None, "A", "liability", True),
        ("221", "Préstamo CP", "22", "A", "liability", True),
        ("222", "Préstamo LP", "22", "A", "liability", True),
        ("23", "Remuneraciones por Pagar", None, "A", "liability", True),
        ("24", "Cuentas por Pagar Varias", None, "A", "liability", True),
        # Patrimonio
        ("30", "Capital", None, "A", "equity", True),
        ("301", "Aporte de socios", "30", "A", "equity", True),
        ("31", "Resultados Acumulados", None, "A", "equity", True),
        ("32", "Resultado del Ejercicio", None, "A", "equity", True),
        # Ingresos
        ("40", "Ventas", None, "A", "income", False),
        ("401", "Venta de platos y bebidas", "40", "A", "income", False),
        ("41", "Otros Ingresos", None, "A", "income", False),
        # Costos
        ("50", "Costo de Ventas", None, "D", "cost", False),
        ("501", "Materia prima e insumos", "50", "D", "cost", False),
        ("502", "Mano de obra directa", "50", "D", "cost", False),
        ("503", "Costos indirectos", "50", "D", "cost", False),
        # Gastos
        ("60", "Gastos de Personal", None, "D", "expense", False),
        ("601", "Sueldos y salarios", "60", "D", "expense", False),
        ("602", "Beneficios sociales", "60", "D", "expense", False),
        ("61", "Gastos de Operación", None, "D", "expense", False),
        ("611", "Alquiler del local", "61", "D", "expense", False),
        ("612", "Servicios públicos", "61", "D", "expense", False),
        ("613", "Mantenimiento", "61", "D", "expense", False),
        ("62", "Gastos de Ventas y Marketing", None, "D", "expense", False),
        ("621", "Publicidad y redes", "62", "D", "expense", False),
        ("622", "Delivery", "62", "D", "expense", False),
        ("63", "Gastos Administrativos", None, "D", "expense", False),
        ("631", "Útiles de oficina", "63", "D", "expense", False),
        ("632", "Suscripciones (software)", "63", "D", "expense", False),
        ("64", "Gastos Financieros", None, "D", "expense", False),
        ("641", "Intereses de préstamo", "64", "D", "expense", False),
        ("642", "Comisiones bancarias", "64", "D", "expense", False),
        ("65", "Depreciación", None, "D", "expense", False),
        ("66", "Otros Gastos", None, "D", "expense", False),
        # Cierre
        ("80", "Resumen de Resultados", None, "A", "closing", False),
        ("81", "Pérdidas y Ganancias", None, "A", "closing", False),
    ]

    # bulk_insert with raw SQL since we don't have the model tables yet
    accounts_table = sa.table(
        "accounts",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("parent_code", sa.String),
        sa.column("nature", sa.String),
        sa.column("category", sa.String),
        sa.column("is_balance_sheet", sa.Boolean),
        sa.column("active", sa.Boolean),
    )

    op.bulk_insert(
        accounts_table,
        [
            {
                "code": a[0],
                "name": a[1],
                "parent_code": a[2],
                "nature": a[3],
                "category": a[4],
                "is_balance_sheet": a[5],
                "active": True,
            }
            for a in accounts
        ],
    )
