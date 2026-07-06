"""
Endpoints de Configuración de Empresa — Branding + Preferencias.

Endpoints:
  GET  /api/settings          → Obtener configuración actual
  PATCH /api/settings         → Actualizar configuración (parcial)
  GET  /api/settings/palette  → Solo paleta de colores (más rápido)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_active_user
from app.core.tenant import get_tenant_id
from app.models.user import User
from app.schemas import ColorPalette, CompanySettings

router = APIRouter(prefix="/api/settings", tags=["Configuración"])

# ─── Estado en memoria ───
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

_current_settings = _default_settings


@router.get("", response_model=CompanySettings)
async def get_settings(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """Obtiene la configuración completa de la empresa."""
    return _current_settings


@router.patch("", response_model=CompanySettings)
async def update_settings(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], data: CompanySettings):
    """
    Actualiza la configuración de la empresa.
    Envía los campos que quieras cambiar — los demás se preservan.
    """
    global _current_settings

    updated = data.model_dump(exclude_unset=True)
    current = _current_settings.model_dump()
    current.update(updated)
    _current_settings = CompanySettings(**current)

    return _current_settings


@router.get("/palette", response_model=ColorPalette)
async def get_palette(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Retorna solo la paleta de colores.
    Endpoint optimizado para carga inicial del frontend.
    """
    return _current_settings.palette


@router.patch("/palette", response_model=ColorPalette)
async def update_palette(tenant_id: Annotated[int, Depends(get_tenant_id)], current_user: Annotated[User, Depends(get_current_active_user)], palette: ColorPalette):
    """
    Actualiza solo la paleta de colores.
    """
    global _current_settings
    _current_settings.palette = palette
    return _current_settings.palette
