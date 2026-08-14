"""
🤖 Modelo ORM — Asistente "Pregúntale al Sistema" (Spec 08 F5, §3.2).

Alcance aprobado (F5, D1–D7):
  - query_catalog: Catálogo SEGURO de consultas. Único lugar donde existe SQL
    en todo el flujo (R1): el LLM elige `id` + llena `params` tipados vía
    tool calling; el motor ejecuta `sql_template` con parámetros vinculados.
  - query_logs:    Auditoría total (R4) — toda pregunta (resuelta o no) queda
    registrada con pregunta cruda, catálogo usado, params finales, resumen de
    resultado, tokens, latencia y rejected.

Diseño (Spec 08 §3.2):
  - `tenant_scope=true` + `:tenant_id` SIEMPRE inyectado por el motor desde
    `get_tenant_id` (R2) — nunca por el LLM.
  - `params` jsonb = [{name, type: 'date'|'int'|'enum', required,
    description_es, allowed_values?}] con CHECK array en BD.
  - `allowed_roles` filtra qué consultas ve el LLM y el dueño por rol (R8).
  - `result_summary` guarda SOLO resumen (rows/total) — la data completa va al
    cliente, no a la BD (evita duplicar datos sensibles en logs).
  - `rejected=true` registra preguntas no resueltas (R5) → insumo para
    ampliar el catálogo.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.models.accounting import Base

# Roles permitidos por defecto (Spec 04 D5/D6 — misma convención del panel)
DEFAULT_ALLOWED_ROLES = ["admin", "manager", "viewer"]


class QueryCatalog(Base):
    """Catálogo de consultas seguras del asistente (Spec 08 §3.2)."""

    __tablename__ = "query_catalog"
    __table_args__ = (
        UniqueConstraint("name", name="uq_query_catalog_name"),
        CheckConstraint("jsonb_typeof(params) = 'array'",
                        name="ck_query_catalog_params_array"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 'delivery' (MVP, D4); luego sales|inventory|finance|report
    skill: Mapped[str] = mapped_column(String(50), nullable=False)
    # slug interno UNIQUE: 'top_products_delivery', 'sales_by_zone', ...
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # para el LLM (tool description) y para el dueño
    description_es: Mapped[str] = mapped_column(Text, nullable=False)
    # SELECT parametrizado con :params (solo lectura R7)
    sql_template: Mapped[str] = mapped_column(Text, nullable=False)
    # [{name, type: 'date'|'int'|'enum', required, description_es, allowed_values?}]
    params: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    allowed_roles: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: list(DEFAULT_ALLOWED_ROLES),
    )
    # true: :tenant_id inyectado por el motor (R2), nunca por el LLM
    tenant_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class QueryLog(Base):
    """Auditoría de preguntas del asistente (Spec 08 §3.2, R4)."""

    __tablename__ = "query_logs"
    __table_args__ = (
        Index("ix_query_logs_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    # texto crudo del dueño (auditoría)
    pregunta: Mapped[str] = mapped_column(Text, nullable=False)
    # null = rechazado/fallback (R5)
    query_catalog_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("query_catalog.id", ondelete="SET NULL"), nullable=True,
    )
    # params finales ejecutados (auditoría)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {rows:int, total?:float} — resumen, NUNCA data completa
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
