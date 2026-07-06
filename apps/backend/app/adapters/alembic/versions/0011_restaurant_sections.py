"""Caso 2: Mantenimiento de Secciones — restaurant_sections + section_id FK en tables.

Migration:
  - Crear tabla restaurant_sections
  - Agregar section_id FK a tables (SET NULL on delete)
  - Migrar datos existentes: DISTINCT section → restaurant_sections
  - UPDATE tables SET section_id WHERE section matches

Revision ID: 0011_restaurant_sections
Revises: 0010_product_categories_missing_columns
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0011_restaurant_sections"
down_revision: Union[str, None] = "0010_product_categories_missing_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Crear tabla restaurant_sections ──────────────────────
    op.create_table(
        "restaurant_sections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_section_tenant_name"),
    )
    op.create_index(
        "idx_sections_tenant_sort", "restaurant_sections", ["tenant_id", "sort_order"],
    )

    # ─── Agregar section_id FK a tables ───────────────────────
    op.add_column("tables", sa.Column("section_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tables_section_id",
        "tables", "restaurant_sections",
        ["section_id"], ["id"],
        ondelete="SET NULL",
    )

    # ─── Migrar datos existentes ──────────────────────────────
    # Insertar secciones únicas desde el campo section de tables
    conn = op.get_bind()

    # Obtener (tenant_id, section) únicos donde section no es NULL
    rows = conn.execute(
        sa.text(
            "SELECT DISTINCT tenant_id, section FROM tables "
            "WHERE section IS NOT NULL AND section != '' "
            "ORDER BY tenant_id, section"
        )
    ).fetchall()

    section_map = {}  # (tenant_id, section_name) → new_section_id
    for tenant_id, section_name in rows:
        result = conn.execute(
            sa.text(
                "INSERT INTO restaurant_sections (tenant_id, name, sort_order, created_at, updated_at) "
                "VALUES (:tid, :name, 0, NOW(), NOW()) "
                "ON CONFLICT (tenant_id, name) DO NOTHING "
                "RETURNING id"
            ),
            {"tid": tenant_id, "name": section_name},
        )
        inserted = result.fetchone()
        if inserted:
            section_map[(tenant_id, section_name)] = inserted[0]
        else:
            # Ya existe — obtener su id
            existing = conn.execute(
                sa.text(
                    "SELECT id FROM restaurant_sections "
                    "WHERE tenant_id = :tid AND name = :name"
                ),
                {"tid": tenant_id, "name": section_name},
            ).fetchone()
            if existing:
                section_map[(tenant_id, section_name)] = existing[0]

    # Actualizar tables.section_id
    for (tenant_id, section_name), section_id in section_map.items():
        conn.execute(
            sa.text(
                "UPDATE tables SET section_id = :sid "
                "WHERE tenant_id = :tid AND section = :name AND section_id IS NULL"
            ),
            {"sid": section_id, "tid": tenant_id, "name": section_name},
        )


def downgrade() -> None:
    # Remover FK y columna
    op.drop_constraint("fk_tables_section_id", "tables", type_="foreignkey")
    op.drop_column("tables", "section_id")
    # Eliminar tabla
    op.drop_index("idx_sections_tenant_sort", table_name="restaurant_sections")
    op.drop_table("restaurant_sections")
