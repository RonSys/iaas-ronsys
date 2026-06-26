"""
Métricas Prometheus para monitoreo del backend.

Expone endpoint /metrics para Prometheus scrape.
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# ═══════════════════════════════════════════════════════════════
# Métricas
# ═══════════════════════════════════════════════════════════════

# Contadores de requests
REQUEST_COUNT = Counter(
    "iaas_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Latencia de requests
REQUEST_LATENCY = Histogram(
    "iaas_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Requests en vuelo
REQUESTS_IN_FLIGHT = Gauge(
    "iaas_http_requests_in_flight",
    "HTTP requests currently being processed",
)

# Errores
ERROR_COUNT = Counter(
    "iaas_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status"],
)

# ─── Métricas de Negocio ──────────────────────────────────────

SIMULATION_COUNT = Counter(
    "iaas_simulations_total",
    "Total financial simulations run",
)

JOURNAL_ENTRY_COUNT = Counter(
    "iaas_journal_entries_total",
    "Total journal entries created",
    ["entry_type"],
)

KARDEX_MOVEMENT_COUNT = Counter(
    "iaas_kardex_movements_total",
    "Total kardex movements",
    ["movement_type"],
)


# ═══════════════════════════════════════════════════════════════
# Middleware de Métricas
# ═══════════════════════════════════════════════════════════════


class MetricsMiddleware:
    """
    Middleware ASGI que registra métricas por request.

    Mide:
      - Contador de requests (por method, endpoint, status)
      - Latencia (P50, P95, P99)
      - Requests en vuelo
      - Errores

    Uso:
        app.add_middleware(MetricsMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        start = time.monotonic()
        REQUESTS_IN_FLIGHT.inc()

        async def _send(message):
            if message["type"] == "http.response.start":
                status = str(message.get("status", 200))
                duration = time.monotonic() - start

                REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
                REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

                if int(status) >= 400:
                    ERROR_COUNT.labels(method=method, endpoint=path, status=status).inc()

                REQUESTS_IN_FLIGHT.dec()

            await send(message)

        await self.app(scope, receive, _send)


# ═══════════════════════════════════════════════════════════════
# Setup de Métricas en FastAPI
# ═══════════════════════════════════════════════════════════════


def setup_metrics(app: FastAPI) -> None:
    """Configura el endpoint /metrics para Prometheus."""

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Agregar middleware directamente
    # FastAPI no soporta middleware como clase callable directamente desde add_middleware
    # Lo manejamos con un middleware ASGI puro o un decorator
    # Para simplicidad, usamos app.middleware("http")
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable):
        method = request.method
        path = request.url.path
        start = time.monotonic()
        REQUESTS_IN_FLIGHT.inc()

        response = await call_next(request)

        duration = time.monotonic() - start
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

        if response.status_code >= 400:
            ERROR_COUNT.labels(method=method, endpoint=path, status=status).inc()

        REQUESTS_IN_FLIGHT.dec()
        return response
