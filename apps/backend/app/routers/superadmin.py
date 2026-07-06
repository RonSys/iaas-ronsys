"""
🛡️ Superadmin Endpoints — Gestión global multi-tenant.

FEATURE: Superadmin
  - CRUD de empresas (tenants)
  - CRUD de usuarios en cualquier tenant
  - Dashboard global
  - Solo accesible por rol 'superadmin'

Estructura de endpoints:
  /api/superadmin/companies      → CRUD empresas
  /api/superadmin/users          → CRUD usuarios multi-tenant
  /api/superadmin/dashboard      → Estadísticas globales
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.models.accounting import Company
from app.core.dependencies import get_current_active_user, require_role
from app.core.security import hash_password
from app.models.user import User

router = APIRouter(prefix="/api/superadmin", tags=["Superadmin"])


# ═══════════════════════════════════════════════════════════════
# Dependencia: solo superadmin
# ═══════════════════════════════════════════════════════════════

SuperAdminOnly = Depends(require_role("superadmin"))


# ═══════════════════════════════════════════════════════════════
# FEATURE 2 — CRUD de Empresas (Tenants)
# ═══════════════════════════════════════════════════════════════


class CompanyCreateRequest(BaseModel):
    """Schema para crear una empresa desde superadmin."""
    name: str
    ruc: str
    address: Optional[str] = None
    economic_activity: Optional[str] = None
    business_type: str = "restaurant"


class CompanyUpdateRequest(BaseModel):
    """Schema para actualizar una empresa."""
    name: Optional[str] = None
    address: Optional[str] = None
    economic_activity: Optional[str] = None
    business_type: Optional[str] = None
    setup_complete: Optional[bool] = None


class SuperadminUserCreateRequest(BaseModel):
    """Schema para crear usuario desde superadmin (incluye tenant_id)."""
    email: str
    full_name: str
    password: str
    role: str = "operator"
    tenant_id: int
    is_verified: bool = True


class DashboardStats(BaseModel):
    """Estadísticas globales del dashboard superadmin."""
    total_companies: int = 0
    total_users: int = 0
    companies_by_type: dict = {}
    users_by_role: dict = {}
    active_companies: int = 0
    inactive_companies: int = 0
    active_users: int = 0
    recent_companies: list = []
    recent_users: list = []


# ═══════════════════════════════════════════════════════════════
# FEATURE 2 — Companies CRUD
# ═══════════════════════════════════════════════════════════════


@router.post("/companies", status_code=201)
async def create_company(
    data: CompanyCreateRequest,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Crea una nueva empresa (tenant). Solo superadmin."""
    # Verificar RUC único
    existing = await db.execute(
        select(Company).where(Company.ruc == data.ruc)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una empresa con RUC {data.ruc}",
        )

    company = Company(
        name=data.name,
        ruc=data.ruc,
        address=data.address,
        economic_activity=data.economic_activity,
        business_type=data.business_type,
        setup_complete=False,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)

    return {
        "id": company.id,
        "name": company.name,
        "ruc": company.ruc,
        "business_type": company.business_type,
        "setup_complete": company.setup_complete,
        "message": f"Empresa '{company.name}' creada exitosamente",
    }


@router.get("/companies")
async def list_companies(
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
    business_type: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = True,
    limit: int = 50,
    offset: int = 0,
):
    """Lista todas las empresas. Filtros opcionales."""
    query = select(Company)

    if business_type:
        query = query.where(Company.business_type == business_type)
    if search:
        query = query.where(
            Company.name.ilike(f"%{search}%")
        )

    total = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total.scalar()

    query = query.order_by(Company.id).offset(offset).limit(limit)
    result = await db.execute(query)
    companies = result.scalars().all()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "companies": [
            {
                "id": c.id,
                "name": c.name,
                "ruc": c.ruc,
                "address": c.address,
                "economic_activity": c.economic_activity,
                "business_type": c.business_type,
                "setup_complete": c.setup_complete,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in companies
        ],
    }


@router.get("/companies/{company_id}")
async def get_company(
    company_id: int,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene detalle de una empresa por ID."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    return {
        "id": company.id,
        "name": company.name,
        "ruc": company.ruc,
        "address": company.address,
        "economic_activity": company.economic_activity,
        "business_type": company.business_type,
        "setup_complete": company.setup_complete,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
    }


@router.put("/companies/{company_id}")
async def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza datos de una empresa."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**update_data)
        )
        await db.commit()

    return {"message": f"Empresa ID {company_id} actualizada correctamente"}


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: int,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina una empresa (solo si no tiene usuarios activos)."""
    # Verificar que exista
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Verificar usuarios
    user_result = await db.execute(
        select(func.count()).select_from(
            select(User).where(User.tenant_id == company_id, User.is_active == True).subquery()
        )
    )
    active_users = user_result.scalar()
    if active_users and active_users > 0:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar: {active_users} usuario(s) activo(s) en esta empresa. Desactívalos primero.",
        )

    await db.execute(delete(Company).where(Company.id == company_id))
    await db.commit()
    return None


# ═══════════════════════════════════════════════════════════════
# FEATURE 3 — Gestión de Usuarios Multi-Tenant
# ═══════════════════════════════════════════════════════════════


@router.post("/users", status_code=201)
async def create_user(
    data: SuperadminUserCreateRequest,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Crea un usuario en CUALQUIER tenant.
    Solo superadmin puede asignar el tenant_id explícitamente.
    """
    # Validar que el tenant exista
    tenant_check = await db.execute(
        select(Company).where(Company.id == data.tenant_id)
    )
    if not tenant_check.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail=f"Tenant ID {data.tenant_id} no existe",
        )

    # Validar roles permitidos
    allowed_roles = {"admin", "manager", "operator", "viewer"}
    if data.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Role inválido. Permitidos: {', '.join(sorted(allowed_roles))}",
        )

    # Verificar email único
    existing = await db.execute(
        select(User).where(User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        tenant_id=data.tenant_id,
        is_active=True,
        is_verified=data.is_verified,
        failed_login_attempts=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "message": f"Usuario '{user.full_name}' creado en tenant {data.tenant_id}",
    }


@router.get("/users")
async def list_all_users(
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Optional[int] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Lista todos los usuarios de todas las empresas. Solo superadmin."""
    query = select(User)

    if tenant_id is not None:
        query = query.where(User.tenant_id == tenant_id)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )

    total = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total.scalar()

    query = query.order_by(User.tenant_id, User.id).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "tenant_id": u.tenant_id,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ],
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: SuperadminUserCreateRequest,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza un usuario (incluye change de tenant). Solo superadmin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No permitir modificar al propio superadmin
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes modificarte a ti mismo aquí")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    else:
        update_data.pop("password", None)

    await db.execute(
        update(User).where(User.id == user_id).values(**update_data)
    )
    await db.commit()

    return {"message": f"Usuario ID {user_id} actualizado correctamente"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Desactiva un usuario (soft-delete). No permite borrar al superadmin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Protección: no eliminar al superadmin
    if user.role == "superadmin":
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar/desactivar al superadmin del sistema",
        )

    # Soft-delete: desactivar
    user.is_active = False
    await db.commit()

    return {"message": f"Usuario {user.email} desactivado correctamente"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-activa un usuario desactivado."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    return {"message": f"Usuario {user.email} reactivado correctamente"}


# ═══════════════════════════════════════════════════════════════
# FEATURE 4 — Dashboard Global
# ═══════════════════════════════════════════════════════════════


@router.get("/dashboard")
async def dashboard(
    current_user: Annotated[User, SuperAdminOnly],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Estadísticas globales del sistema. Solo superadmin."""
    # Total empresas
    total_companies = await db.execute(select(func.count()).select_from(Company))
    total_companies_count = total_companies.scalar()

    # Total usuarios
    total_users = await db.execute(select(func.count()).select_from(User))
    total_users_count = total_users.scalar()

    # Empresas por tipo
    companies_by_type_query = await db.execute(
        select(Company.business_type, func.count().label("cnt"))
        .group_by(Company.business_type)
    )
    companies_by_type = {row[0]: row[1] for row in companies_by_type_query.all()}

    # Usuarios por rol
    users_by_role_query = await db.execute(
        select(User.role, func.count().label("cnt"))
        .group_by(User.role)
    )
    users_by_role = {row[0]: row[1] for row in users_by_role_query.all()}

    # Empresas activas (con setup_complete)
    active_companies_result = await db.execute(
        select(func.count()).select_from(
            select(Company).where(Company.setup_complete == True).subquery()
        )
    )
    active_companies = active_companies_result.scalar()

    # Usuarios activos
    active_users_result = await db.execute(
        select(func.count()).select_from(
            select(User).where(User.is_active == True).subquery()
        )
    )
    active_users = active_users_result.scalar()

    # Últimas empresas creadas
    recent_companies_result = await db.execute(
        select(Company).order_by(Company.id.desc()).limit(5)
    )
    recent_companies = [
        {
            "id": c.id,
            "name": c.name,
            "business_type": c.business_type,
            "setup_complete": c.setup_complete,
        }
        for c in recent_companies_result.scalars().all()
    ]

    # Últimos usuarios creados
    recent_users_result = await db.execute(
        select(User).order_by(User.id.desc()).limit(5)
    )
    recent_users = [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "tenant_id": u.tenant_id,
        }
        for u in recent_users_result.scalars().all()
    ]

    return {
        "total_companies": total_companies_count,
        "total_users": total_users_count,
        "companies_by_type": companies_by_type,
        "users_by_role": users_by_role,
        "active_companies": active_companies,
        "inactive_companies": total_companies_count - active_companies,
        "active_users": active_users,
        "inactive_users": total_users_count - active_users,
        "recent_companies": recent_companies,
        "recent_users": recent_users,
    }
