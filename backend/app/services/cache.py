"""Lightweight cache abstraction — Redis if configured, else in-memory.

Used for rate-limiting hooks and short-lived result caching. Kept intentionally
tiny; the in-memory fallback keeps the service runnable without Redis.
"""
from __future__ import annotations

import time
from threading import Lock

from app.config import get_settings


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, str]] = {}
        self._lock = Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires, value = item
            if expires is not None and expires < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        with self._lock:
            expires = time.time() + ttl if ttl else None
            self._store[key] = (expires, value)

    def incr(self, key: str, ttl: int | None = None) -> int:
        with self._lock:
            current = self.get(key)
            n = (int(current) if current else 0) + 1
            expires = time.time() + ttl if ttl else None
            self._store[key] = (expires, str(n))
            return n


class _RedisCache:  # pragma: no cover - exercised only when Redis present
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._r.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._r.set(key, value, ex=ttl)

    def incr(self, key: str, ttl: int | None = None) -> int:
        n = self._r.incr(key)
        if ttl and n == 1:
            self._r.expire(key, ttl)
        return int(n)


_cache = None


def get_cache():
    global _cache
    if _cache is not None:
        return _cache
    url = get_settings().redis_url
    if url:
        try:
            _cache = _RedisCache(url)
            return _cache
        except Exception:  # pragma: no cover
            pass
    _cache = _MemoryCache()
    return _cache
