"""Tiny in-memory TTL cache. Swap for Redis in production (see docs)."""
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        expires, value = item
        if expires < time.time():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any):
        self._store[key] = (time.time() + self.ttl, value)

    def clear(self):
        self._store.clear()


cache = TTLCache(ttl_seconds=300)

# Redis equivalent (needs `pip install redis` and a running server):
#   r = redis.Redis(); r.setex(key, 300, value); r.get(key)
