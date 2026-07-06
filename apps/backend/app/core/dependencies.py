"""
🔐 Dependencias de Autenticación — FastAPI.

US-03: Motor de JWT + dependencias inyectables para proteger endpoints.

Uso:
    @router.get("/protegido")
    async def endpoint(
        current_user: User = Depends(get_current_active_user),
        tenant_id: int = Depends(get_tenant_id),
    ):
        ...
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.adapters.db.database import get_db
from app.config import settings
from app.core.security import decode_access_token
from app.models.user import User

# ─── OAuth2 Scheme ───────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,  # Permite endpoints públicos sin token
)


# ─── Dependencias ────────────────────────────────────────────


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> User:
    """
    Extrae el usuario del JWT en el header Authorization.

    US-03: Valida el token, extrae sub, busca el usuario en BD.
    Si hay X-Tenant-ID, valida que user.company_id == tenant_id (US-10).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # ─── Validación de tenant (US-10) ────────────────────
    # Superadmin puede acceder a cualquier tenant
    if user.role != "superadmin":
        tenant_id = _get_tenant_from_request(request)
        if tenant_id is not None and user.company_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verifica que el usuario esté activo.

    US-03: Rechaza usuarios con is_active=False (HTTP 403).
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_role(*allowed_roles: str):
    """
    Factory de dependencia que restringe acceso por rol.

    US-03: Uso: Depends(require_role("admin", "manager"))
    Superadmin siempre pasa cualquier restricción de rol.
    """

    async def _require_role(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        # Superadmin tiene todos los permisos
        if current_user.role == "superadmin":
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' does not have sufficient permissions",
            )
        return current_user

    return _require_role


# ─── Tenant Helper ────────────────────────────────────────────


def _get_tenant_from_request(request: Request) -> Optional[int]:
    """
    Extrae X-Tenant-ID del header sin lanzar error.
    Retorna None si no está presente (para endpoints públicos).
    """
    header = request.headers.get("X-Tenant-ID")
    if header is None:
        return None
    try:
        return int(header)
    except (TypeError, ValueError):
        return None
