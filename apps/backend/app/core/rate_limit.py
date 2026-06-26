"""
⏱️ Rate Limiter — Redis sliding window con fallback in-memory.

US-13 + US-14: Rate limiting para login por IP y email.

Estrategia:
  - Redis SORTED SET con ventana deslizante (producción)
  - Diccionario Python con timestamps (fallback si Redis no está)
  - Timeout Redis: 1 segundo → automáticamente cae a in-memory

Uso:
    limiter = RateLimiter(redis_url="redis://localhost:6379/0")
    ok, retry_after = await limiter.check("login:ip:192.168.1.1", max_req=5, window=60)
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int
    remaining: int
    limit: int


class RateLimiter:
    """
    Rate limiter con Redis sliding window + fallback in-memory.

    Ventana deslizante: cuenta requests en los últimos N segundos.
    Si Redis no responde en 1 segundo, usa diccionario en memoria.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url
        self._redis = None
        self._redis_available: Optional[bool] = None
        # Fallback in-memory: { key: [timestamp, ...] }
        self._memory: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def check(
        self, key: str, max_requests: int = 5, window_seconds: int = 60
    ) -> RateLimitResult:
        """
        Verifica si un request excede el rate limit.

        Args:
            key: Clave única (ej: "login:ip:192.168.1.1")
            max_requests: Máximo de requests en la ventana
            window_seconds: Duración de la ventana en segundos

        Returns:
            RateLimitResult con allowed, retry_after_seconds, remaining, limit
        """
        # Intentar Redis primero
        if self._redis_available is None:
            await self._try_connect_redis()

        if self._redis_available:
            try:
                return await asyncio.wait_for(
                    self._redis_check(key, max_requests, window_seconds),
                    timeout=1.0,
                )
            except (asyncio.TimeoutError, Exception):
                self._redis_available = False

        # Fallback in-memory
        return self._memory_check(key, max_requests, window_seconds)

    async def _try_connect_redis(self) -> None:
        """Intenta conectar a Redis. Marca unavailable si falla."""
        if not self._redis_url:
            self._redis_available = False
            return

        try:
            import redis.asyncio as aioredis

            self._redis = await asyncio.wait_for(
                aioredis.from_url(self._redis_url, decode_responses=True),
                timeout=1.0,
            )
            await asyncio.wait_for(self._redis.ping(), timeout=1.0)
            self._redis_available = True
        except Exception:
            self._redis_available = False
            self._redis = None

    async def _redis_check(
        self, key: str, max_requests: int, window_seconds: int
    ) -> RateLimitResult:
        """Ventana deslizante con Redis SORTED SET."""
        now_ms = time.time() * 1000
        window_start = now_ms - (window_seconds * 1000)

        # Pipeline atómico: eliminar miembros viejos + contar + agregar actual
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.expire(key, window_seconds + 1)
            _, count, _, _ = await pipe.execute()

        count = int(count)  # ya incluye el request actual
        remaining = max(0, max_requests - count)

        if count > max_requests:
            # El request más antiguo en la ventana determina cuándo liberar
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_ms = oldest[0][1] + window_seconds * 1000 - now_ms
                retry_after = max(1, int(retry_ms / 1000))
            else:
                retry_after = window_seconds
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                remaining=0,
                limit=max_requests,
            )

        return RateLimitResult(
            allowed=True,
            retry_after_seconds=0,
            remaining=remaining,
            limit=max_requests,
        )

    def _memory_check(
        self, key: str, max_requests: int, window_seconds: int
    ) -> RateLimitResult:
        """Ventana deslizante en memoria (thread-safe con lock)."""
        now = time.monotonic()

        if key not in self._memory:
            self._memory[key] = []

        # Limpiar timestamps viejos
        self._memory[key] = [
            t for t in self._memory[key] if now - t < window_seconds
        ]

        count = len(self._memory[key])
        remaining = max(0, max_requests - count)

        if count >= max_requests:
            oldest = min(self._memory[key])
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                remaining=0,
                limit=max_requests,
            )

        self._memory[key].append(now)
        return RateLimitResult(
            allowed=True,
            retry_after_seconds=0,
            remaining=max_requests - count - 1,
            limit=max_requests,
        )


# ═══════════════════════════════════════════════════════════════
# Instancia global (singleton, inicializada en main.py o lazy)
# ═══════════════════════════════════════════════════════════════

_limiter: Optional[RateLimiter] = None


def get_rate_limiter(redis_url: Optional[str] = None) -> RateLimiter:
    """Retorna la instancia global del rate limiter."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(redis_url=redis_url)
    return _limiter
