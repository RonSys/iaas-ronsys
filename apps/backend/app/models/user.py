"""
Modelos ORM — User y RefreshToken.

US-02: Modelos de datos para autenticación.

Tablas:
  - users:           Usuarios del sistema (FK → companies)
  - refresh_tokens:  Refresh tokens opacos con hash SHA-256

Compatibilidad SQLite: role es VARCHAR(20) con check constraint, no ENUM nativo.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.models.accounting import Base


class User(Base):
    """
    Usuario del sistema. Pertenece a una Company (tenant).

    Campos de seguridad: failed_login_attempts y locked_until
    se usan para bloqueo de cuenta por fuerza bruta (US-15).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="viewer"
    )  # ENUM: admin|manager|operator|viewer
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id (DB column renamed by migration)."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'manager', 'operator', 'viewer')",
            name="ck_users_role",
        ),
    )


class RefreshToken(Base):
    """
    Refresh token opaco almacenado en BD.

    - token_hash: SHA-256 del token (el token en texto plano NUNCA se guarda)
    - replaced_by_id: cadena de rotación (FK a sí mismo)
    - family revocation: si se detecta reuso, se revocan TODOS los tokens del usuario
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    @property
    def company_id(self) -> int:
        """Backward compatibility alias for tenant_id."""
        return self.tenant_id

    @company_id.setter
    def company_id(self, value: int):
        self.tenant_id = value
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    replaced_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("refresh_tokens.id"), nullable=True
    )

    __table_args__ = ()
