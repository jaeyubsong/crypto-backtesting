"""
Cache Statistics tracking utilities.

This module provides statistics tracking functionality for cache operations.
"""

from threading import RLock
from typing import Any

from loguru import logger


class CacheStatistics:
    """Handles cache statistics tracking with thread safety."""

    def __init__(self) -> None:
        """Initialize cache statistics tracker."""
        self._stats_lock = RLock()
        self._cache_hits = 0
        self._cache_misses = 0

    def record_hit(self) -> None:
        """Record a cache hit."""
        with self._stats_lock:
            self._cache_hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._stats_lock:
            self._cache_misses += 1

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        with self._stats_lock:
            total_requests = self._cache_hits + self._cache_misses
            if total_requests == 0:
                return 0.0
            return (self._cache_hits / total_requests) * 100

    def get_stats(self) -> dict[str, int]:
        """Get current statistics."""
        with self._stats_lock:
            return {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
            }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        with self._stats_lock:
            old_hits = self._cache_hits
            old_misses = self._cache_misses
            self._cache_hits = 0
            self._cache_misses = 0

            logger.debug(f"Cache statistics reset: {old_hits} hits, {old_misses} misses cleared")

    def get_detailed_stats(
        self, cache_size: int, max_size: int, memory_usage_mb: float, memory_limit_mb: float
    ) -> dict[str, Any]:
        """Get comprehensive cache statistics including external metrics."""
        with self._stats_lock:
            return {
                "cache_size": cache_size,
                "max_size": max_size,
                "memory_usage_mb": round(memory_usage_mb, 2),
                "memory_limit_mb": memory_limit_mb,
                "memory_usage_percent": round((memory_usage_mb / memory_limit_mb) * 100, 1),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate_percent": round(self.get_hit_rate(), 1),
            }
