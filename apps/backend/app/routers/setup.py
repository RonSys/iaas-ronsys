"""
Endpoints de Configuración de Empresa — Branding + Preferencias.

Endpoints:
  GET  /api/settings          → Obtener configuración actual
  PATCH /api/settings         → Actualizar configuración (parcial)
  GET  /api/settings/palette  → Solo paleta de colores (más rápido)

Spec 03 — Fix D-03 (Fase A): la configuración se persiste en
`companies.settings` (JSONB) por tenant — deja de ser una variable global
en memoria (deuda D-03 del Plan Integral v3). Sin cambio de contrato API.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.adapters.db.models.accounting import Company
from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas import ColorPalette, CompanySettings

router = APIRouter(prefix="/api/settings", tags=["Configuración"])

# ─── Defaults (usados como base cuando el tenant aún no guardó nada) ───
_default_settings = CompanySettings(
    palette=ColorPalette(
        primary="#1a365d",
        secondary="#2b6cb0",
        accent="#e53e3e",
        background="#f7fafc",
        surface="#ffffff",
        text_primary="#1a202c",
        text_secondary="#718096",
        success="#38a169",
        warning="#d69e2e",
        error="#e53e3e",
    ),
    logo_url=None,
    favicon_url=None,
    date_format="DD/MM/YYYY",
    currency="PEN",
    timezone="America/Lima",
)


async def _load_company(db: AsyncSession, tenant_id: int) -> Company:
    company = (await db.execute(
        select(Company).where(Company.id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


def _merge_settings(company: Company) -> CompanySettings:
    """Defaults + settings persistidos del tenant (los persistidos ganan).

    Estructura de companies.settings:
      {branding: {palette, logo_url, ...}, delivery: {yape_phone, ...}}
    """
    raw = company.settings or {}
    raw = raw if isinstance(raw, dict) else {}
    branding = raw.get("branding", {}) if isinstance(raw.get("branding"), dict) else {}
    delivery = raw.get("delivery", {}) if isinstance(raw.get("delivery"), dict) else {}
    merged = _default_settings.model_dump()
    merged.update({k: v for k, v in branding.items() if v is not None})
    if delivery:
        merged["delivery"] = delivery
    return CompanySettings(**merged)


@router.get("", response_model=CompanySettings)
async def get_settings(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene la configuración completa de la empresa (persistida)."""
    company = await _load_company(db, tenant_id)
    return _merge_settings(company)


@router.patch("", response_model=CompanySettings)
async def update_settings(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: CompanySettings,
):
    """
    Actualiza la configuración de la empresa (persistida en companies.settings).
    Envía los campos que quieras cambiar — los demás se preservan.
    """
    company = await _load_company(db, tenant_id)
    updated = data.model_dump(exclude_unset=True)
    current = _merge_settings(company).model_dump()
    current.update(updated)

    # Copia nueva del dict (SQLAlchemy JSON: asignar el mismo objeto no marca dirty)
    stored = dict(company.settings or {})
    stored["branding"] = {k: v for k, v in current.items() if k != "delivery"}
    stored["delivery"] = current.get("delivery") or {}
    company.settings = stored
    await db.commit()

    return CompanySettings(**current)


@router.get("/palette", response_model=ColorPalette)
async def get_palette(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retorna solo la paleta de colores (optimizado para carga inicial)."""
    company = await _load_company(db, tenant_id)
    return _merge_settings(company).palette


@router.patch("/palette", response_model=ColorPalette)
async def update_palette(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    palette: ColorPalette,
):
    """Actualiza solo la paleta de colores (persistida)."""
    company = await _load_company(db, tenant_id)
    # Copia nueva del dict (SQLAlchemy JSON: asignar el mismo objeto no marca dirty)
    stored = dict(company.settings or {})
    current = _merge_settings(company).model_dump()
    current["palette"] = palette.model_dump()
    stored["branding"] = {k: v for k, v in current.items() if k != "delivery"}
    stored["delivery"] = current.get("delivery") or {}
    company.settings = stored
    await db.commit()
    return palette
