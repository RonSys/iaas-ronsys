"""
Tests para el Rate Limiter — In-Memory Fallback.

US-13 + US-14: Rate limiting de login por IP y email.
"""

import asyncio
import time

import pytest

from app.core.rate_limit import RateLimiter


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def limiter():
    """Rate limiter sin Redis — usa fallback in-memory."""
    return RateLimiter(redis_url=None)


def _run(coro):
    """Helper: ejecuta coroutine async en contexto sync."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════


class TestRateLimiterInMemory:

    def test_first_request_allowed(self, limiter):
        result = _run(limiter.check("test:key", max_requests=5, window_seconds=60))
        assert result.allowed
        assert result.remaining == 4
        assert result.limit == 5

    def test_requests_within_limit(self, limiter):
        key = "test:within"
        for i in range(5):
            result = _run(limiter.check(key, max_requests=5, window_seconds=60))
            assert result.allowed, f"Request {i + 1} should be allowed"
        # 6to request bloqueado
        result = _run(limiter.check(key, max_requests=5, window_seconds=60))
        assert not result.allowed
        assert result.retry_after_seconds > 0
        assert result.remaining == 0

    def test_returns_retry_after_header(self, limiter):
        key = "test:retry"
        for _ in range(5):
            _run(limiter.check(key, max_requests=5, window_seconds=60))
        result = _run(limiter.check(key, max_requests=5, window_seconds=60))
        assert not result.allowed
        assert result.retry_after_seconds > 0
        assert result.limit == 5

    def test_different_keys_independent(self, limiter):
        for _ in range(5):
            _run(limiter.check("test:a", max_requests=5, window_seconds=60))
        # key_b no afectado
        result = _run(limiter.check("test:b", max_requests=5, window_seconds=60))
        assert result.allowed

    def test_window_expires(self, limiter):
        key = "test:expire"
        for _ in range(5):
            _run(limiter.check(key, max_requests=5, window_seconds=1))
        result = _run(limiter.check(key, max_requests=5, window_seconds=1))
        assert not result.allowed
        time.sleep(1.1)
        result = _run(limiter.check(key, max_requests=5, window_seconds=1))
        assert result.allowed

    def test_ip_email_key_format(self, limiter):
        ip_key = "login:ip:192.168.1.100"
        email_key = "login:email:admin@elsegoviano.pe"
        assert _run(limiter.check(ip_key, max_requests=5, window_seconds=60)).allowed
        assert _run(limiter.check(email_key, max_requests=5, window_seconds=60)).allowed

    def test_no_redis_uses_memory(self, limiter):
        assert limiter._redis_available is None
        result = _run(limiter.check("test:noredis", max_requests=5, window_seconds=60))
        assert result.allowed
        assert limiter._redis_available is False
        assert len(limiter._memory) == 1
