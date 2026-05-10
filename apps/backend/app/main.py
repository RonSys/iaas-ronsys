"""
IaaS-RonSys Backend — Punto de entrada FastAPI.
Monolito Modular + Hexagonal (Ports & Adapters).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.monitoring import (
    setup_logging_middleware,
    setup_metrics,
    setup_rate_limiting,
    setup_security_headers,
)
from app.routers.health import router as health_router
from app.routers.accounting import router as accounting_router, kardex_router
from app.routers.setup import router as settings_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: inicialización y apagado limpio."""
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Monitoreo ────────────────────────────────────────────────
if settings.metrics_enabled:
    setup_metrics(app)

# ─── Middleware ───────────────────────────────────────────────
setup_logging_middleware(app)
setup_security_headers(app)
setup_rate_limiting(
    app,
    enabled=settings.rate_limit_enabled,
    default_limit=settings.rate_limit_default,
)

# ─── Routers ──────────────────────────────────────────────────
app.include_router(health_router, tags=["Health"])
app.include_router(accounting_router)
app.include_router(kardex_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }
