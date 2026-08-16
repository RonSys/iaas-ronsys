"""Spec 07 (F6 — "Agenda de Citas"): entidad `appointments` + estado de voz.

F6 crea el módulo de agenda/reservas por mesa que hoy NO existe (solo el
toggle `tables.status='reserved'` sin datos de reserva — ver Spec 07 §2.1).
Decisiones cerradas por Ron (2026-08-15): D1 espejo tables.status ·
D3 ventana independiente configurable (default 12:00–23:00) ·
D4 mesa libre con duración (overlap de rangos, sin grilla) ·
D7 source ∈ {voice_ai, whatsapp, web, in_person} desde el día 1.

Esta migración:

1) Tabla `appointments`:
     - id             BIGSERIAL PK
     - tenant_id      FK companies ON DELETE CASCADE (R7 aislamiento).
     - table_id       FK tables ON DELETE SET NULL (nullable: por confirmar).
     - customer_name  TEXT NOT NULL · customer_phone TEXT (WhatsApp D6).
     - guests         INTEGER CHECK 1–50.
     - starts_at      TIMESTAMPTZ (fecha+hora local de la cita).
     - duration_min   INTEGER CHECK 15–240, default 60 (D4).
     - status         CHECK solicitada|confirmada|cumplida|cancelada|no_show
                      (default 'solicitada' — R5 transiciones).
     - source         CHECK voice_ai|whatsapp|web|in_person (D7, default
                      in_person; NUNCA null → trazabilidad R6).
     - notes TEXT · call_id varchar(64) (trazabilidad voz F3/R6) ·
       created_by FK users ON DELETE SET NULL ·
       reminded_at TIMESTAMPTZ NULL (recordatorio 24h idempotente, R9) ·
       created_at/updated_at TIMESTAMPTZ.
     - UNIQUE (tenant_id, table_id, starts_at) — anti-doble-reserva D2
       (caso exacto; el overlap de rangos parciales lo valida el servicio
       con query atómica: starts_at < new_end AND ends_at > new_start sobre
       citas activas solicitada|confirmada).
     - Índices: idx_appointments_tenant_date (tenant_id, starts_at) e
       idx_appointments_tenant_state (tenant_id, status).

2) Grants (patrón dashboard_ro / dashboard_rw_revision de SC-005/F1):
     - dashboard_ro         → SELECT
     - dashboard_rw_revision → SELECT, UPDATE (transiciones de estado)
   Defensivos: el GRANT se ejecuta SOLO si el rol existe (los roles de
   dashboard viven en el cluster de prod; en dev/QA pueden no estar).

3) Estado de voz F3 (D5): `taking_reservation` se añade al CHECK
   `ck_call_records_ai_state` de la migración 0019 (espejo de AI_STATES
   en app/adapters/db/models/calls.py) — el PATCH /ai-state puede persistir
   la máquina extendida sin 422 de BD. El downgrade restaura el CHECK
   original de F3 (0019 intacta).

Revision ID: 0021_appointments
Revises: 0020_assistant
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0021_appointments"
down_revision: Union[str, Sequence[str], None] = "0020_assistant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Espejo de AI_STATES (Spec 06 §3.6) + taking_reservation (Spec 07 D5)
_AI_STATES_F3 = (
    "'greeting','taking_order','clarifying','confirming',"
    "'transfer','hangup','completed','failed'"
)
_AI_STATES_F6 = (
    "'greeting','taking_order','clarifying','confirming',"
    "'taking_reservation','transfer','hangup','completed','failed'"
)


def _grant_if_role_exists(role: str, privileges: str) -> None:
    """GRANT defensivo: solo si el rol de dashboard existe en el cluster.

    Los roles dashboard_ro/dashboard_rw_revision son de prod (SC-005/F1);
    en BD de dev/QA pueden no existir → el upgrade NO debe romper por eso.
    """
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                EXECUTE 'GRANT {privileges} ON appointments TO {role}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "table_id", sa.Integer(),
            sa.ForeignKey("tables.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("customer_name", sa.Text(), nullable=False),
        sa.Column("customer_phone", sa.Text(), nullable=True),
        sa.Column("guests", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False,
                  server_default="60"),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="solicitada"),
        sa.Column("source", sa.String(20), nullable=False,
                  server_default="in_person"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("call_id", sa.String(64), nullable=True),
        sa.Column(
            "created_by", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "table_id", "starts_at",
            name="uq_appointments_tenant_table_start",
        ),
    )
    op.create_check_constraint(
        "ck_appointments_guests", "appointments", "guests BETWEEN 1 AND 50",
    )
    op.create_check_constraint(
        "ck_appointments_duration_min", "appointments",
        "duration_min BETWEEN 15 AND 240",
    )
    op.create_check_constraint(
        "ck_appointments_status", "appointments",
        "status IN ('solicitada','confirmada','cumplida','cancelada','no_show')",
    )
    op.create_check_constraint(
        "ck_appointments_source", "appointments",
        "source IN ('voice_ai','whatsapp','web','in_person')",
    )
    op.create_index(
        "idx_appointments_tenant_date", "appointments",
        ["tenant_id", "starts_at"],
    )
    op.create_index(
        "idx_appointments_tenant_state", "appointments",
        ["tenant_id", "status"],
    )

    # Grants defensivos (dashboard_ro SELECT / dashboard_rw_revision SELECT+UPDATE)
    _grant_if_role_exists("dashboard_ro", "SELECT")
    _grant_if_role_exists("dashboard_rw_revision", "SELECT, UPDATE")

    # F3 (D5): ampliar el dominio de ai_state con taking_reservation
    op.drop_constraint("ck_call_records_ai_state", "call_records", type_="check")
    op.create_check_constraint(
        "ck_call_records_ai_state", "call_records",
        f"ai_state IN ({_AI_STATES_F6})",
    )


def downgrade() -> None:
    # Restaurar el CHECK de F3 (sin taking_reservation — 0019 intacta)
    op.drop_constraint("ck_call_records_ai_state", "call_records", type_="check")
    op.create_check_constraint(
        "ck_call_records_ai_state", "call_records",
        f"ai_state IN ({_AI_STATES_F3})",
    )

    op.drop_index("idx_appointments_tenant_state", table_name="appointments")
    op.drop_index("idx_appointments_tenant_date", table_name="appointments")
    op.drop_table("appointments")
