"""
Modelos ORM — Simulador de Escenarios (HU-SIM-001).

Tablas:
  - scenarios:  Escenarios guardados del simulador financiero
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.models.accounting import Base


class Scenario(Base):
    """Escenario de simulación financiera guardado por el usuario."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value

    __table_args__ = (
        Index("idx_scenarios_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name={self.name!r})>"
