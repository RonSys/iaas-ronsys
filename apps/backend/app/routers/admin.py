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
from app.schemas.sales import (
    CompanyFeaturesSettings,
    CompanySettingsUpdateRequest,
    FeatureFlags,
    TaxConfig,
    BUSINESS_TYPE_DEFAULTS,
)
from app.adapters.db.models.accounting import Company

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
    repo = UserRepository(db, tenant_id=tenant_id)

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
        tenant_id=tenant_id,  # Siempre del admin, no del body
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
    repo = UserRepository(db, tenant_id=tenant_id)
    users = await repo.get_all(
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [AdminUserResponse.model_validate(u) for u in users]


# ═══════════════════════════════════════════════════════════════
# HU-F1-002: Company Settings (Feature Flags + Tax Config)
# ═══════════════════════════════════════════════════════════════


@router.put("/company/settings")
async def update_company_settings(
    data: CompanySettingsUpdateRequest,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    HU-F1-002: Actualiza feature flags y tax_config de la empresa.

    PUT /api/admin/company/settings

    Valida que los feature flags sean permitidos y persiste en settings JSON.
    """
    result = await db.execute(
        select(Company).where(Company.id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    current_settings = dict(company.settings) if company.settings else {}

    # Merge features
    if data.features is not None:
        current_settings["features"] = data.features.model_dump()

    # Merge tax_config
    if data.tax_config is not None:
        current_settings["tax_config"] = data.tax_config.model_dump()

    # QA-02: Persistencia explícita — asignar + flag_modified para JSON columns
    company.settings = current_settings
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "settings")
    await db.flush()

    return {
        "company_id": company.id,
        "business_type": company.business_type,
        "settings": company.settings,
    }


DEFAULT_PALETTE = {
    "primary": "#1a365d",
    "secondary": "#2b6cb0",
    "accent": "#e53e3e",
    "background": "#f7fafc",
    "surface": "#ffffff",
    "text_primary": "#1a202c",
    "text_secondary": "#718096",
    "success": "#38a169",
    "warning": "#d69e2e",
    "error": "#e53e3e",
}


@router.get("/company/settings")
async def get_company_settings(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Obtiene la configuración completa de la empresa (features + tax + palette + branding).

    Retorna un objeto plano compatible con CompanySettingsResponse del frontend.
    """
    result = await db.execute(
        select(Company).where(Company.id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Merge con defaults del business_type
    defaults = BUSINESS_TYPE_DEFAULTS.get(
        company.business_type, BUSINESS_TYPE_DEFAULTS["retail"]
    )

    stored = company.settings or {}
    features_raw = stored.get("features", {})
    tax_raw = stored.get("tax_config", {})

    # Merge: stored overrides defaults
    merged_features = defaults.features.model_dump()
    merged_features.update(features_raw)

    merged_tax = defaults.tax_config.model_dump()
    merged_tax.update(tax_raw)

    # Palette: stored o defaults
    palette = stored.get("palette") or dict(DEFAULT_PALETTE)
    # Merge stored palette keys over defaults (por si solo guardaron algunos)
    if stored.get("palette"):
        merged_palette = dict(DEFAULT_PALETTE)
        merged_palette.update(stored["palette"])
        palette = merged_palette

    return {
        "company_id": company.id,
        "business_type": company.business_type,
        "business_name": company.name,
        "features": merged_features,
        "tax_config": merged_tax,
        "palette": palette,
        "logo_url": stored.get("logo_url"),
        "favicon_url": stored.get("favicon_url"),
        "date_format": stored.get("date_format", "DD/MM/YYYY"),
        "currency": stored.get("currency", "PEN"),
        "timezone": stored.get("timezone", "America/Lima"),
    }
