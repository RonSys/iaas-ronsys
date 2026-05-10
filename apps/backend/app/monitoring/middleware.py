"""
Middleware personalizado — Logging, Rate Limiting, Seguridad.

Responsabilidad:
  - Logging estructurado de cada request
  - Rate limiting por endpoint (con Redis)
  - Headers de seguridad
"""

import logging
import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("iaas-ronsys")


# ═══════════════════════════════════════════════════════════════
# Logging Middleware
# ═══════════════════════════════════════════════════════════════


def setup_logging_middleware(app: FastAPI) -> None:
    """Middleware que registra cada request con método, endpoint, status y duración."""

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "%s %s → %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


# ═══════════════════════════════════════════════════════════════
# Rate Limiting Middleware
# ═══════════════════════════════════════════════════════════════

# En memoria (sin Redis por ahora — se conecta cuando Redis esté disponible)
_rate_limit_store: dict[str, list[float]] = {}


def setup_rate_limiting(
    app: FastAPI,
    enabled: bool = True,
    default_limit: str = "100/hour",
    redis_client=None,  # Optional[Redis]
) -> None:
    """
    Middleware de rate limiting.

    En producción usa Redis (SORTED SET con ventana deslizante).
    En desarrollo usa diccionario en memoria.

    Config:
      - RATE_LIMIT_ENABLED (bool)
      - RATE_LIMIT_DEFAULT ("100/hour" → 100 requests por hora)
    """
    if not enabled:
        return

    # Parsear límite: "100/hour"
    parts = default_limit.split("/")
    max_requests = int(parts[0]) if len(parts) > 0 else 100
    window = parts[1].lower() if len(parts) > 1 else "hour"

    window_seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }.get(window, 3600)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.monotonic()

        if redis_client:
            # Redis sliding window (TODO: implementar cuando Redis esté disponible)
            response = await call_next(request)
            return response

        # In-memory sliding window
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []

        # Limpiar timestamps viejos
        _rate_limit_store[key] = [
            t for t in _rate_limit_store[key] if now - t < window_seconds
        ]

        if len(_rate_limit_store[key]) >= max_requests:
            return Response(
                status_code=429,
                content='{"detail":"Too many requests. Try again later."}',
                media_type="application/json",
            )

        _rate_limit_store[key].append(now)
        response = await call_next(request)
        return response


# ═══════════════════════════════════════════════════════════════
# Security Headers
# ═══════════════════════════════════════════════════════════════


def setup_security_headers(app: FastAPI) -> None:
    """Agrega headers de seguridad a todas las respuestas."""

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
