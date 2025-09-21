"""
CSV Cache Core functionality.

This module provides the core caching infrastructure for CSV data
with memory management and observer pattern support.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

import pandas as pd
from cachetools import LRUCache, TTLCache
from loguru import logger

from .cache_interfaces import (
    CacheEvent,
    CacheEventType,
    CacheSubject,
    ICacheManager,
    create_standard_cache_observers,
)
from .cache_statistics import CacheStatistics
from .memory_tracker import MemoryTracker


class CSVCacheCore(CacheSubject, ICacheManager):
    """Core caching functionality with memory management and observer pattern support."""

    # Configuration constants
    DEFAULT_CACHE_SIZE = 100
    MAX_MEMORY_MB = 512  # Maximum cache memory usage in MB
    MAX_CACHE_CLEAR_RETRIES = 3  # Maximum retries for cache clearing to prevent infinite loops

    def __init__(self, cache_size: int = DEFAULT_CACHE_SIZE, enable_observers: bool = True):
        """Initialize the CSV cache core with observer pattern support."""
        super().__init__()  # Initialize CacheSubject

        if cache_size <= 0:
            raise ValueError("Cache size must be positive")
        if cache_size > 1000:
            logger.warning(f"Large cache size ({cache_size}) may consume significant memory")

        self.cache: LRUCache[str, pd.DataFrame] = LRUCache(maxsize=cache_size)
        self._cache_lock = RLock()  # Thread-safe cache access

        # File stat cache to optimize cache key generation (5 minute TTL)
        self._file_stat_cache: TTLCache[str, float] = TTLCache(maxsize=1000, ttl=300)
        self._stat_cache_lock = RLock()

        # Initialize components
        self._statistics = CacheStatistics()
        self._memory_tracker = MemoryTracker(memory_limit_mb=self.MAX_MEMORY_MB)
        # Use bounded LRUCache to prevent memory leaks from unlimited dict growth
        self._access_counts: LRUCache[str, int] = LRUCache(maxsize=cache_size * 2)

        # Deferred notification system for performance optimization (thread-safe)
        self._pending_events: list[CacheEvent] = []
        self._events_lock = RLock()  # Separate lock for event queue thread safety
        self._batch_mode = False  # Flag to control immediate vs deferred notifications

        # Set up default observers if enabled
        if enable_observers:
            for observer in create_standard_cache_observers():
                self.add_observer(observer)

    @contextmanager
    def batch_operations(self) -> Generator["CSVCacheCore"]:
        """Context manager for efficient batch cache operations.

        During batch mode, observer notifications are deferred until the context exits,
        improving performance for bulk operations while maintaining event delivery.

        Example:
            with cache.batch_operations():
                for file_path in files:
                    await cache.set(key, data)  # No immediate notifications
            # All notifications sent here
        """
        with self._events_lock:
            old_batch_mode = self._batch_mode
            self._batch_mode = True

        try:
            yield self
        finally:
            with self._events_lock:
                self._batch_mode = old_batch_mode
                if not self._batch_mode:
                    # Flush all pending events when exiting batch mode
                    self._flush_pending_events()

    @property
    def _memory_usage_mb(self) -> float:
        """Backward compatibility accessor for memory usage."""
        return self._memory_tracker.get_memory_usage()

    def _set_memory_usage_for_testing(self, value: float) -> None:
        """Controlled setter for memory usage (for testing only).

        This method provides a safe way to set memory usage for testing purposes
        with proper validation, bounds checking, and thread safety.
        """
        # Delegate to memory tracker's thread-safe method
        self._memory_tracker.set_memory_usage_for_testing(value)

    def _queue_event(self, event: CacheEvent) -> None:
        """Queue an event for deferred notification (thread-safe)."""
        with self._events_lock:
            self._pending_events.append(event)

    def _flush_pending_events(self) -> None:
        """Notify observers of all pending events and clear the queue (thread-safe).

        Respects batch mode - if in batch mode, events remain queued.
        """
        # Don't flush events if we're in batch mode
        with self._events_lock:
            if self._batch_mode or not self._pending_events:
                return
            events_to_notify = self._pending_events[:]
            self._pending_events.clear()

        # Notify observers outside of lock to prevent deadlocks
        for event in events_to_notify:
            self.notify_observers(event)

    def _build_cache_key(self, file_path_or_components: Path | dict[str, Any]) -> str:
        """Build cache key from file path or components including file modification time."""
        # Handle backward compatibility - accept either Path object or dict
        if isinstance(file_path_or_components, dict):
            file_path = file_path_or_components.get("file_path")
        else:
            file_path = file_path_or_components

        if file_path and hasattr(file_path, "exists") and file_path.exists():
            mtime = self._get_cached_file_mtime(file_path)
            return f"{file_path}:{mtime}"
        else:
            return str(file_path) if file_path else "unknown"

    def _get_cached_file_mtime(self, file_path: Path) -> int:
        """Get file modification time with aggressive caching to minimize I/O operations."""
        file_str = str(file_path)

        with self._stat_cache_lock:
            # Check if we have a cached mtime (TTLCache automatically handles expiration)
            if file_str in self._file_stat_cache:
                return int(self._file_stat_cache[file_str])

            # Cache miss - perform I/O operation only when necessary
            try:
                stat = file_path.stat()
                mtime = stat.st_mtime_ns
                self._file_stat_cache[file_str] = float(mtime)
                return mtime
            except OSError:
                # File might not exist or be accessible - use deterministic fallback
                # instead of current time to avoid cache invalidation
                default_mtime = hash(file_str) % (2**32)  # Deterministic hash-based fallback
                self._file_stat_cache[file_str] = float(default_mtime)
                return default_mtime

    def _check_cache_hit(self, cache_key: str, metadata: dict[str, Any]) -> pd.DataFrame | None:
        """Check cache for existing entry and return if found."""
        result = None

        with self._cache_lock:
            if cache_key in self.cache:
                self._statistics.record_hit()
                # Track access frequency for LFU eviction
                self._access_counts[cache_key] = self._access_counts.get(cache_key, 0) + 1
                logger.debug(f"Cache hit for {metadata.get('file_path', 'unknown')}")
                # Queue cache hit event for deferred notification
                self._queue_event(
                    CacheEvent(
                        CacheEventType.CACHE_HIT,
                        cache_key,
                        {**metadata, "cache_size": len(self.cache)},
                    )
                )
                result = self.cache[cache_key].copy()
            else:
                self._statistics.record_miss()
                # Queue cache miss event for deferred notification
                self._queue_event(
                    CacheEvent(
                        CacheEventType.CACHE_MISS,
                        cache_key,
                        {**metadata, "cache_size": len(self.cache)},
                    )
                )

        # Notify observers outside of lock
        self._flush_pending_events()
        return result

    def _validate_and_cache_result(
        self, df: pd.DataFrame, cache_key: str, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        """Validate DataFrame and cache the result with memory tracking."""
        df_memory_mb = self._validate_memory_constraints(df)

        with self._cache_lock:
            self._ensure_cache_space(df, df_memory_mb)
            self._store_in_cache(df, cache_key, df_memory_mb, metadata)

        return df

    def _validate_memory_constraints(self, df: pd.DataFrame) -> float:
        """Validate DataFrame memory constraints and return memory size."""
        can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(df)

        # Prevent infinite loop: if DataFrame is larger than memory limit, reject immediately
        if df_memory_mb > self.MAX_MEMORY_MB:
            raise MemoryError(
                f"DataFrame ({df_memory_mb:.1f}MB) exceeds cache memory limit ({self.MAX_MEMORY_MB}MB)"
            )

        return df_memory_mb

    def _ensure_cache_space(self, df: pd.DataFrame, _df_memory_mb: float) -> None:
        """Clear cache if needed to make room for new DataFrame with retry limits."""
        can_add, _ = self._memory_tracker.check_memory_before_add(df)
        retries = 0

        while not can_add and retries < self.MAX_CACHE_CLEAR_RETRIES:
            if not self.cache:  # No more items to remove
                raise MemoryError("Cannot fit data in cache even after clearing")

            logger.warning(
                f"Cache memory limit approached ({self._memory_tracker.get_memory_usage():.1f}MB), "
                f"clearing cache (attempt {retries + 1}/{self.MAX_CACHE_CLEAR_RETRIES})"
            )
            self._clear_cache_internal()
            can_add, _ = self._memory_tracker.check_memory_before_add(df)
            retries += 1

        if not can_add:
            raise MemoryError(
                f"Cannot fit data in cache after {self.MAX_CACHE_CLEAR_RETRIES} clearing attempts. "
                f"DataFrame size ({_df_memory_mb:.1f}MB) may exceed memory limit ({self.MAX_MEMORY_MB}MB)"
            )

    def _store_in_cache(
        self, df: pd.DataFrame, cache_key: str, df_memory_mb: float, metadata: dict[str, Any]
    ) -> None:
        """Store DataFrame in cache with proper tracking."""
        self.cache[cache_key] = df.copy()
        self._access_counts[cache_key] = 1  # Initialize access count
        self._memory_tracker.add_memory_usage(df_memory_mb)

        logger.debug(
            f"Cached {metadata.get('file_name', 'unknown')} ({df_memory_mb:.1f}MB), "
            f"total cache: {self._memory_tracker.get_memory_usage():.1f}MB"
        )

    def clear_cache(self) -> None:
        """Clear the data cache (thread-safe)."""
        with self._cache_lock:
            old_size = len(self.cache)
            old_memory = self._memory_tracker.get_memory_usage()
            self._clear_cache_internal()

            # Queue cache clear event for deferred notification
            self._queue_event(
                CacheEvent(
                    CacheEventType.CACHE_CLEAR,
                    "cache_clear",
                    {
                        "cleared_entries": old_size,
                        "freed_memory_mb": old_memory,
                        "new_cache_size": 0,
                    },
                )
            )

        # Notify observers outside of lock
        self._flush_pending_events()
        logger.info("Data cache cleared")

    def _clear_cache_internal(self) -> None:
        """Internal cache clearing without additional locking."""
        self.cache.clear()
        self._access_counts.clear()  # LRUCache.clear() is still available and thread-safe
        self._memory_tracker.clear_memory_usage()

    def _evict_lfu_items(self, target_memory_mb: float) -> None:
        """Evict least frequently used items to reach target memory usage."""
        # Sort items by access count (ascending = least frequently used first)
        sorted_items = sorted(self._access_counts.items(), key=lambda x: x[1])

        current_memory = self._memory_tracker.get_memory_usage()
        for cache_key, _ in sorted_items:
            if current_memory <= target_memory_mb or not self.cache:
                break

            if cache_key in self.cache:
                # Remove item and update memory tracking
                df = self.cache.pop(cache_key)
                self._access_counts.pop(cache_key, None)
                df_memory = self._memory_tracker.estimate_dataframe_memory(df)
                self._memory_tracker.subtract_memory_usage(df_memory)
                current_memory -= df_memory

                logger.debug(f"LFU evicted cache key: {cache_key}")
                self._queue_event(
                    CacheEvent(
                        CacheEventType.CACHE_EVICTION,
                        cache_key,
                        {"reason": "LFU", "memory_freed_mb": df_memory},
                    )
                )

    # ICacheManager interface implementation
    async def get(self, key: str) -> pd.DataFrame | None:
        """Retrieve data from cache (ICacheManager interface)."""
        result = None

        with self._cache_lock:
            if key in self.cache:
                self._statistics.record_hit()
                self._queue_event(CacheEvent(CacheEventType.CACHE_HIT, key))
                result = self.cache[key].copy()
            else:
                self._statistics.record_miss()
                self._queue_event(CacheEvent(CacheEventType.CACHE_MISS, key))

        # Notify observers outside of lock
        self._flush_pending_events()
        return result

    async def set(self, key: str, value: pd.DataFrame) -> None:
        """Store data in cache (ICacheManager interface)."""
        # Check memory BEFORE adding to cache
        can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(value)

        with self._cache_lock:
            # Clear cache if needed to make room (with retry limits)
            retries = 0
            while not can_add and retries < self.MAX_CACHE_CLEAR_RETRIES:
                if not self.cache:  # No more items to remove
                    raise MemoryError("Cannot fit data in cache even after clearing")
                self._queue_event(
                    CacheEvent(
                        CacheEventType.MEMORY_WARNING,
                        key,
                        {
                            "memory_usage_percent": self._memory_tracker.get_memory_usage_percent(),
                            "retry_attempt": retries + 1,
                            "max_retries": self.MAX_CACHE_CLEAR_RETRIES,
                        },
                    )
                )
                self._clear_cache_internal()
                can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(value)
                retries += 1

            if not can_add:
                raise MemoryError(
                    f"Cannot fit data in cache after {self.MAX_CACHE_CLEAR_RETRIES} clearing attempts"
                )

            self.cache[key] = value.copy()
            self._memory_tracker.add_memory_usage(df_memory_mb)

            self._queue_event(
                CacheEvent(
                    CacheEventType.CACHE_SET,
                    key,
                    {
                        "data_size_mb": df_memory_mb,
                        "total_memory_mb": self._memory_tracker.get_memory_usage(),
                    },
                )
            )

        # Notify observers outside of lock
        self._flush_pending_events()

    def clear(self) -> None:
        """Clear all cache entries (ICacheManager interface)."""
        self.clear_cache()

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics (ICacheManager interface)."""
        return self.get_cache_info()

    def recalculate_memory_usage(self) -> float:
        """Recalculate actual memory usage from cached DataFrames (thread-safe)."""
        with self._cache_lock:
            cache_values = list(self.cache.values())
            return self._memory_tracker.recalculate_memory_from_cache(cache_values, self)

    def get_cache_info(self) -> dict[str, int | float]:
        """Get cache statistics (thread-safe)."""
        with self._cache_lock:
            return self._statistics.get_detailed_stats(
                cache_size=len(self.cache),
                max_size=int(self.cache.maxsize) if self.cache.maxsize else 0,
                memory_usage_mb=self._memory_tracker.get_memory_usage(),
                memory_limit_mb=self.MAX_MEMORY_MB,
            )
