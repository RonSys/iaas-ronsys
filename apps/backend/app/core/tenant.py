"""
🏢 Tenant Middleware — X-Tenant-ID.

US-10: Extrae y valida el header X-Tenant-ID de cada request.
Es una dependencia explícita (no middleware global) para permitir endpoints públicos.

Uso:
    @router.get("/protegido")
    async def endpoint(tenant_id: int = Depends(get_tenant_id)):
        ...
"""

from fastapi import HTTPException, Request, status


async def get_tenant_id(request: Request) -> int:
    """
    Dependencia FastAPI que extrae X-Tenant-ID del header.

    Raises 400 si falta o no es numérico.
    Los endpoints públicos NO deben usar esta dependencia.
    """
    header = request.headers.get("X-Tenant-ID")

    if header is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header required",
        )

    try:
        tenant_id = int(header)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID must be an integer",
        )

    return tenant_id
