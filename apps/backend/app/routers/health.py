"""
Endpoints de Health Check — Monitoreo de estado del servicio.
"""

from fastapi import APIRouter, Response
from app.config import settings
from app.adapters.db.database import get_engine
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health():
    """Health check básico — el servicio está vivo."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/ready")
async def ready():
    """
    Readiness check — el servicio está listo para recibir tráfico.
    Verifica conexión a PostgreSQL.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "service": settings.app_name,
        }
    except Exception as e:
        return Response(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e),
            },
            media_type="application/json",
        )
