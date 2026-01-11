"""Query caching service."""

import hashlib
import json
from typing import Any

from loguru import logger


class CacheService:
    """
    Simple in-memory cache service.
    
    In production, replace with Redis for distributed caching.
    TTL: 60 minutes (configurable)
    """

    # Class-level cache storage (in production, use Redis)
    _cache: dict[str, dict[str, Any]] = {}
    _ttl_seconds: int = 3600  # 60 minutes

    @staticmethod
    def generate_key(query: str) -> str:
        """
        Generate cache key from query.
        
        Normalizes query by lowercasing and trimming whitespace.
        """
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get cached value by key."""
        import time
        
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check TTL
        if time.time() - entry.get("timestamp", 0) > self._ttl_seconds:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit: {key}")
        return entry.get("data")

    async def set(self, key: str, data: dict[str, Any]) -> None:
        """Set cache value with TTL."""
        import time
        
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }
        logger.debug(f"Cache set: {key}")

    async def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key}")

    async def invalidate_all(self) -> None:
        """Invalidate all cache entries (e.g., after document update)."""
        self._cache.clear()
        logger.info("All cache entries invalidated")

    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "ttl_seconds": self._ttl_seconds,
        }
