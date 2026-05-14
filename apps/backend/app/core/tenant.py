"""
🏢 Tenant Middleware — X-Tenant-ID / JWT fallback.

HU-F0-001: Extrae y valida el tenant_id de cada request.
Soporta dos fuentes (por orden de precedencia):
  1. Header X-Tenant-ID (explícito) — validado contra JWT company_id
  2. JWT decoded payload (campo 'company_id' como fallback)

Si X-Tenant-ID está presente:
  - Requiere autenticación JWT válida
  - Valida que X-Tenant-ID == user.tenant_id (JWT company_id)
  - Si no coinciden → 403 Forbidden
  - Si no hay JWT → 401 Unauthorized

Si solo JWT está presente:
  - Usa user.tenant_id (JWT company_id)

Uso:
    @router.get("/protegido")
    async def endpoint(tenant_id: int = Depends(get_tenant_id)):
        ...
"""

from fastapi import Depends, HTTPException, Request, status

from app.core.dependencies import get_current_active_user
from app.models.user import User


async def get_tenant_id(
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> int:
    """
    Dependencia FastAPI que extrae y valida tenant_id.

    Prioridad:
      1. Header X-Tenant-ID → validado contra JWT company_id
      2. JWT payload['company_id'] como fallback

    Raises:
      401 si no hay autenticación
      403 si X-Tenant-ID no coincide con el tenant del usuario
    """
    header = request.headers.get("X-Tenant-ID")

    if header is not None:
        try:
            tid = int(header)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID must be an integer",
            )

        # Validar que coincida con el tenant del usuario autenticado
        if tid != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant mismatch: X-Tenant-ID does not match user's tenant",
            )
        return tid

    # Fallback: usar tenant_id del usuario autenticado
    return current_user.tenant_id
