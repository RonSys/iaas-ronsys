"""
Schemas Pydantic para Autenticación.

US-04 a US-09: Request/Response schemas para auth y admin.

Principio de seguridad:
  - UserResponse NUNCA incluye hashed_password, failed_login_attempts, locked_until
  - LoginRequest usa contraseña en texto plano (efímero — solo en request body)
  - Anti-enumeración: mensajes de error genéricos
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# ═══════════════════════════════════════════════════════════════
# User / Token Schemas
# ═══════════════════════════════════════════════════════════════


class UserResponse(BaseModel):
    """Datos públicos de usuario (NUNCA incluye campos sensibles)."""
    id: int
    email: str
    full_name: str
    role: str
    company_id: int
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Respuesta de login/refresh exitoso."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


# ═══════════════════════════════════════════════════════════════
# Login
# ═══════════════════════════════════════════════════════════════


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(TokenResponse):
    """Login incluye datos del usuario además de tokens."""
    user: UserResponse


# ═══════════════════════════════════════════════════════════════
# Refresh / Logout
# ═══════════════════════════════════════════════════════════════


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"


# ═══════════════════════════════════════════════════════════════
# Admin — Crear Usuario
# ═══════════════════════════════════════════════════════════════


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "viewer"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """US-08: 8+ caracteres, 1 mayúscula, 1 número."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least 1 uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least 1 number")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "manager", "operator", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


# ═══════════════════════════════════════════════════════════════
# Admin — Listar Usuarios
# ═══════════════════════════════════════════════════════════════


class AdminUserResponse(BaseModel):
    """User listados por admin — incluye metadata de seguridad."""
    id: int
    email: str
    full_name: str
    role: str
    company_id: int
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
# Generic
# ═══════════════════════════════════════════════════════════════


class MessageResponse(BaseModel):
    message: str
