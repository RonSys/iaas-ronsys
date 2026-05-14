"""
🏢 Tenant Middleware — X-Tenant-ID.

US-10: Extrae y valida el header X-Tenant-ID de cada request.
Como fallback, extrae tenant_id del JWT (payload.company_id) cuando
el header no está presente. Esto permite que usuarios autenticados
no necesiten enviar el header explícitamente.

Uso:
    @router.get("/protegido")
    async def endpoint(tenant_id: int = Depends(get_tenant_id)):
        ...
"""

import jwt as pyjwt
from fastapi import HTTPException, Request, status

from app.config import settings


async def get_tenant_id(request: Request) -> int:
    """
    Extrae tenant_id del header X-Tenant-ID, con fallback al JWT.

    1. Si el header X-Tenant-ID existe, lo usa (validando que sea entero).
    2. Si no hay header, intenta extraer company_id del JWT en Authorization.
    3. Si ambos fallan, retorna 400.
    """
    # 1. Intentar desde header
    header = request.headers.get("X-Tenant-ID")
    if header is not None:
        try:
            return int(header)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID must be an integer",
            )

    # 2. Fallback: extraer tenant_id del JWT
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = pyjwt.decode(
                token,
                settings.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
            company_id = payload.get("company_id")
            if company_id is not None:
                return int(company_id)
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError, ValueError):
            pass

    # 3. Sin header y sin JWT válido
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="X-Tenant-ID header required",
    )
