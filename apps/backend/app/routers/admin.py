"""
🛡️ Admin Endpoints — Gestión de usuarios.

US-08: POST /api/admin/users   — admin crea usuario
US-09: GET  /api/admin/users    — admin lista usuarios de su tenant

Solo accesible por rol 'admin'. Scoping automático por tenant.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.tenant import get_tenant_id
from app.core.security import hash_password
from app.models.user import User
from app.adapters.db.repositories.user import UserRepository
from app.schemas.auth import AdminUserResponse, CreateUserRequest, UserResponse

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ═══════════════════════════════════════════════════════════════
# US-08: Crear Usuario
# ═══════════════════════════════════════════════════════════════


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: CreateUserRequest,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Crea un nuevo usuario en el tenant del admin autenticado.

    El company_id siempre es el del admin, NUNCA del request body.
    """
    repo = UserRepository(db, company_id=tenant_id)

    # Verificar email único en este tenant
    existing = await repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        company_id=tenant_id,  # Siempre del admin, no del body
        is_active=True,
        is_verified=False,
        failed_login_attempts=0,
    )

    created = await repo.create(user)
    return UserResponse.model_validate(created)


# ═══════════════════════════════════════════════════════════════
# US-09: Listar Usuarios
# ═══════════════════════════════════════════════════════════════


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Lista usuarios del tenant del admin autenticado.

    Query params opcionales: role, is_active, search.
    """
    repo = UserRepository(db, company_id=tenant_id)
    users = await repo.get_all(
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [AdminUserResponse.model_validate(u) for u in users]
