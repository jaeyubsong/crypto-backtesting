"""
Cache Interfaces and Observer Pattern implementation.

This module provides abstract interfaces for caching systems and implements
the Observer Pattern for cache event monitoring and notification.
"""

import weakref
from abc import ABC, abstractmethod
from enum import Enum
from threading import RLock
from typing import Any, Protocol

import pandas as pd
from loguru import logger


class CacheEventType(Enum):
    """Types of cache events for observer notifications."""

    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SET = "cache_set"
    CACHE_EVICTION = "cache_eviction"
    CACHE_CLEAR = "cache_clear"
    MEMORY_WARNING = "memory_warning"
    MEMORY_CRITICAL = "memory_critical"


class CacheEvent:
    """Represents a cache event with associated metadata."""

    def __init__(
        self,
        event_type: CacheEventType,
        cache_key: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize cache event."""
        self.event_type = event_type
        self.cache_key = cache_key
        self.metadata = metadata or {}
        self.timestamp = pd.Timestamp.now()

    def __repr__(self) -> str:
        return f"CacheEvent(type={self.event_type.value}, key={self.cache_key[:20]}...)"


class CacheObserver(Protocol):
    """Protocol for cache event observers."""

    def notify(self, event: CacheEvent) -> None:
        """Handle cache event notification."""
        ...


class ICacheManager(ABC):
    """Abstract interface for cache management."""

    @abstractmethod
    async def get(self, key: str) -> pd.DataFrame | None:
        """Retrieve data from cache."""

    @abstractmethod
    async def set(self, key: str, value: pd.DataFrame) -> None:
        """Store data in cache."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""

    @abstractmethod
    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics."""

    @abstractmethod
    def add_observer(self, observer: CacheObserver) -> None:
        """Add cache event observer."""

    @abstractmethod
    def remove_observer(self, observer: CacheObserver) -> None:
        """Remove cache event observer."""


class CacheSubject:
    """Subject class implementing the Observer Pattern for cache events."""

    def __init__(self) -> None:
        """Initialize cache subject with observer management using weak references."""
        self._observers: weakref.WeakSet[CacheObserver] = weakref.WeakSet()
        self._observers_lock = RLock()

    def add_observer(self, observer: CacheObserver) -> None:
        """Add an observer to the notification list."""
        with self._observers_lock:
            self._observers.add(observer)
            logger.debug(f"Added cache observer: {type(observer).__name__}")

    def remove_observer(self, observer: CacheObserver) -> None:
        """Remove an observer from the notification list."""
        with self._observers_lock:
            self._observers.discard(observer)
            logger.debug(f"Removed cache observer: {type(observer).__name__}")

    def notify_observers(self, event: CacheEvent) -> None:
        """Notify all observers of a cache event."""
        with self._observers_lock:
            # Create a copy of observers to avoid modification during iteration
            observers_copy = list(self._observers)
            for observer in observers_copy:
                try:
                    observer.notify(event)
                except Exception as e:
                    logger.error(f"Observer notification failed: {e}")


class CacheMetricsObserver:
    """Observer that tracks cache metrics and performance."""

    def __init__(self) -> None:
        """Initialize metrics tracking."""
        self.stats = {
            "total_hits": 0,
            "total_misses": 0,
            "total_sets": 0,
            "total_evictions": 0,
            "total_clears": 0,
            "memory_warnings": 0,
        }
        self._lock = RLock()

    def notify(self, event: CacheEvent) -> None:
        """Handle cache event for metrics tracking."""
        with self._lock:
            if event.event_type == CacheEventType.CACHE_HIT:
                self.stats["total_hits"] += 1
            elif event.event_type == CacheEventType.CACHE_MISS:
                self.stats["total_misses"] += 1
            elif event.event_type == CacheEventType.CACHE_SET:
                self.stats["total_sets"] += 1
            elif event.event_type == CacheEventType.CACHE_EVICTION:
                self.stats["total_evictions"] += 1
            elif event.event_type == CacheEventType.CACHE_CLEAR:
                self.stats["total_clears"] += 1
            elif event.event_type in [
                CacheEventType.MEMORY_WARNING,
                CacheEventType.MEMORY_CRITICAL,
            ]:
                self.stats["memory_warnings"] += 1

    def get_metrics(self) -> dict[str, int]:
        """Get current cache metrics."""
        with self._lock:
            hit_rate = 0.0
            total_requests = self.stats["total_hits"] + self.stats["total_misses"]
            if total_requests > 0:
                hit_rate = (self.stats["total_hits"] / total_requests) * 100

            return {
                **self.stats,
                "hit_rate_percent": int(round(hit_rate, 2)),
                "total_requests": total_requests,
            }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        with self._lock:
            for key in self.stats:
                self.stats[key] = 0


class CacheLoggingObserver:
    """Observer that logs cache events for debugging and monitoring."""

    def __init__(self, log_level: str = "DEBUG"):
        """Initialize logging observer with configurable log level."""
        self.log_level = log_level.upper()

    def notify(self, event: CacheEvent) -> None:
        """Handle cache event for logging."""
        message = f"Cache event: {event.event_type.value} for key {event.cache_key[:20]}..."

        if event.metadata:
            message += f" | Metadata: {event.metadata}"

        if self.log_level == "DEBUG":
            logger.debug(message)
        elif self.log_level == "INFO":
            logger.info(message)
        elif self.log_level == "WARNING" and event.event_type in [
            CacheEventType.MEMORY_WARNING,
            CacheEventType.CACHE_EVICTION,
        ]:
            logger.warning(message)
        elif self.log_level == "ERROR" and event.event_type == CacheEventType.MEMORY_CRITICAL:
            logger.error(message)


class CachePerformanceObserver:
    """Observer that monitors cache performance and alerts on issues."""

    def __init__(self, hit_rate_threshold: float = 70.0, memory_threshold: float = 80.0):
        """Initialize performance monitoring with configurable thresholds."""
        self.hit_rate_threshold = hit_rate_threshold
        self.memory_threshold = memory_threshold
        self._recent_events: list[CacheEvent] = []
        self._performance_window = 100  # Number of events to track
        self._lock = RLock()

    def notify(self, event: CacheEvent) -> None:
        """Handle cache event for performance monitoring."""
        with self._lock:
            self._recent_events.append(event)

            # Keep only recent events
            if len(self._recent_events) > self._performance_window:
                self._recent_events = self._recent_events[-self._performance_window :]

            # Check performance metrics
            self._check_hit_rate_performance()
            self._check_memory_usage(event)

    def _check_hit_rate_performance(self) -> None:
        """Check cache hit rate and alert if below threshold."""
        if len(self._recent_events) < 50:  # Need minimum events for reliable metrics
            return

        hits = sum(1 for e in self._recent_events if e.event_type == CacheEventType.CACHE_HIT)
        misses = sum(1 for e in self._recent_events if e.event_type == CacheEventType.CACHE_MISS)
        total = hits + misses

        if total > 0:
            hit_rate = (hits / total) * 100
            if hit_rate < self.hit_rate_threshold:
                logger.warning(
                    f"Cache hit rate ({hit_rate:.1f}%) below threshold ({self.hit_rate_threshold}%)"
                )

    def _check_memory_usage(self, event: CacheEvent) -> None:
        """Check memory usage and alert on issues."""
        if event.event_type in [CacheEventType.MEMORY_WARNING, CacheEventType.MEMORY_CRITICAL]:
            memory_percent = event.metadata.get("memory_usage_percent", 0)
            if memory_percent > self.memory_threshold:
                logger.warning(f"Cache memory usage high: {memory_percent:.1f}%")


# Factory functions for common observer configurations
def create_standard_cache_observers() -> list[CacheObserver]:
    """Create standard set of cache observers for typical use cases."""
    return [
        CacheMetricsObserver(),
        CacheLoggingObserver(log_level="INFO"),
        CachePerformanceObserver(),
    ]


def create_debug_cache_observers() -> list[CacheObserver]:
    """Create debug-focused cache observers for development."""
    return [
        CacheMetricsObserver(),
        CacheLoggingObserver(log_level="DEBUG"),
        CachePerformanceObserver(hit_rate_threshold=60.0),
    ]


def create_production_cache_observers() -> list[CacheObserver]:
    """Create production-focused cache observers for monitoring."""
    return [
        CacheMetricsObserver(),
        CacheLoggingObserver(log_level="WARNING"),
        CachePerformanceObserver(hit_rate_threshold=80.0, memory_threshold=75.0),
    ]
