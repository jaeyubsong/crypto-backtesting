"""
CSV Data Caching utilities.

This module provides efficient caching and single file loading for CSV data.
"""

import asyncio
from pathlib import Path
from threading import RLock

import pandas as pd
from cachetools import LRUCache
from loguru import logger

from src.core.exceptions.backtest import DataError

from .cache_interfaces import (
    CacheEvent,
    CacheEventType,
    CacheSubject,
    ICacheManager,
    create_standard_cache_observers,
)
from .cache_statistics import CacheStatistics
from .csv_validator import CSVValidator
from .memory_tracker import MemoryTracker


class CSVCache(CacheSubject, ICacheManager):
    """Handles caching and single file loading for CSV data with Observer Pattern support."""

    # Configuration constants
    DEFAULT_CACHE_SIZE = 100
    MAX_MEMORY_MB = 512  # Maximum cache memory usage in MB

    def __init__(self, cache_size: int = DEFAULT_CACHE_SIZE, enable_observers: bool = True):
        """Initialize the CSV cache with observer pattern support."""
        super().__init__()  # Initialize CacheSubject

        if cache_size <= 0:
            raise ValueError("Cache size must be positive")
        if cache_size > 1000:
            logger.warning(f"Large cache size ({cache_size}) may consume significant memory")

        self.cache: LRUCache[str, pd.DataFrame] = LRUCache(maxsize=cache_size)
        self._cache_lock = RLock()  # Thread-safe cache access

        # Initialize components
        self._statistics = CacheStatistics()
        self._memory_tracker = MemoryTracker(memory_limit_mb=self.MAX_MEMORY_MB)
        self._access_counts: dict[str, int] = {}  # Track access frequency for LFU eviction

        # Set up default observers if enabled
        if enable_observers:
            for observer in create_standard_cache_observers():
                self.add_observer(observer)

    @property
    def _memory_usage_mb(self) -> float:
        """Backward compatibility accessor for memory usage."""
        return self._memory_tracker.get_memory_usage()

    @_memory_usage_mb.setter
    def _memory_usage_mb(self, value: float) -> None:
        """Backward compatibility setter for memory usage (for testing)."""
        # This is primarily for test compatibility
        # Direct manipulation should be avoided in production code
        self._memory_tracker._memory_usage_mb = value

    async def load_single_file(self, file_path: Path) -> pd.DataFrame:
        """Load a single CSV file with caching."""
        cache_key = self._build_cache_key(file_path)

        # Check cache first
        cached_result = self._check_cache_hit(cache_key, file_path)
        if cached_result is not None:
            return cached_result

        # Load from disk if not cached
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            logger.debug(f"Loading file: {file_path}")
            df = await self._load_csv_from_disk(file_path)
            return self._validate_and_cache_result(df, cache_key, file_path)

        except pd.errors.EmptyDataError:
            return self._handle_empty_file()
        except OSError as e:
            logger.error(f"File system error loading {file_path.name}: {str(e)}")
            raise DataError(f"File system error loading {file_path.name}") from e
        except Exception as e:
            return self._handle_loading_error(e, file_path)

    def _build_cache_key(self, file_path: Path) -> str:
        """Build cache key including file modification time."""
        if file_path.exists():
            stat = file_path.stat()
            return f"{file_path}:{stat.st_mtime_ns}"
        else:
            return str(file_path)

    def _check_cache_hit(self, cache_key: str, file_path: Path) -> pd.DataFrame | None:
        """Check cache for existing entry and return if found."""
        with self._cache_lock:
            if cache_key in self.cache:
                self._statistics.record_hit()
                # Track access frequency for LFU eviction
                self._access_counts[cache_key] = self._access_counts.get(cache_key, 0) + 1
                logger.debug(f"Cache hit for {file_path}")
                # Notify observers of cache hit
                self.notify_observers(
                    CacheEvent(
                        CacheEventType.CACHE_HIT,
                        cache_key,
                        {"file_path": str(file_path), "cache_size": len(self.cache)},
                    )
                )
                return self.cache[cache_key].copy()
            else:
                self._statistics.record_miss()
                # Notify observers of cache miss
                self.notify_observers(
                    CacheEvent(
                        CacheEventType.CACHE_MISS,
                        cache_key,
                        {"file_path": str(file_path), "cache_size": len(self.cache)},
                    )
                )
        return None

    async def _load_csv_from_disk(self, file_path: Path) -> pd.DataFrame:
        """Load CSV file from disk using async executor with proper resource management."""
        loop = asyncio.get_event_loop()

        def _read_csv_safely() -> pd.DataFrame:
            """Read CSV with proper file handle management."""
            try:
                return pd.read_csv(
                    file_path,
                    dtype={
                        "timestamp": "int64",
                        "open": "float64",
                        "high": "float64",
                        "low": "float64",
                        "close": "float64",
                        "volume": "float64",
                    },
                )
            except Exception as e:
                # Ensure any file handles are properly cleaned up
                logger.debug(f"CSV read failed for {file_path.name}: {str(e)}")
                raise

        return await loop.run_in_executor(None, _read_csv_safely)

    def _validate_and_cache_result(
        self, df: pd.DataFrame, cache_key: str, file_path: Path
    ) -> pd.DataFrame:
        """Validate DataFrame and cache the result with memory tracking."""
        CSVValidator.validate_csv_structure(df, file_path)

        # Check memory BEFORE adding to cache to prevent overages
        can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(df)

        with self._cache_lock:
            # Clear cache if needed to make room
            while not can_add:
                if not self.cache:  # No more items to remove
                    raise MemoryError("Cannot fit data in cache even after clearing")
                logger.warning(
                    f"Cache memory limit approached ({self._memory_tracker.get_memory_usage():.1f}MB), clearing cache"
                )
                self._clear_cache_internal()
                can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(df)

            # Now safe to add to cache
            self.cache[cache_key] = df.copy()
            self._access_counts[cache_key] = 1  # Initialize access count
            self._memory_tracker.add_memory_usage(df_memory_mb)

            logger.debug(
                f"Cached {file_path.name} ({df_memory_mb:.1f}MB), total cache: {self._memory_tracker.get_memory_usage():.1f}MB"
            )

        return df

    def _handle_empty_file(self) -> pd.DataFrame:
        """Handle empty CSV files gracefully."""
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _handle_loading_error(self, error: Exception, file_path: Path) -> pd.DataFrame:
        """Handle CSV loading errors with proper sanitization."""
        logger.error(f"CSV file loading failed: {file_path.name}", exc_info=True)
        raise DataError(f"Failed to load CSV file: {file_path.name}") from error

    def clear_cache(self) -> None:
        """Clear the data cache (thread-safe)."""
        with self._cache_lock:
            old_size = len(self.cache)
            old_memory = self._memory_tracker.get_memory_usage()
            self._clear_cache_internal()

            # Notify observers of cache clear
            self.notify_observers(
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
        logger.info("Data cache cleared")

    def _clear_cache_internal(self) -> None:
        """Internal cache clearing without additional locking."""
        self.cache.clear()
        self._access_counts.clear()
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
                self.notify_observers(
                    CacheEvent(
                        CacheEventType.CACHE_EVICTION,
                        cache_key,
                        {"reason": "LFU", "memory_freed_mb": df_memory},
                    )
                )

    # ICacheManager interface implementation
    async def get(self, key: str) -> pd.DataFrame | None:
        """Retrieve data from cache (ICacheManager interface)."""
        with self._cache_lock:
            if key in self.cache:
                self._statistics.record_hit()
                self.notify_observers(CacheEvent(CacheEventType.CACHE_HIT, key))
                return self.cache[key].copy()
            else:
                self._statistics.record_miss()
                self.notify_observers(CacheEvent(CacheEventType.CACHE_MISS, key))
                return None

    async def set(self, key: str, value: pd.DataFrame) -> None:
        """Store data in cache (ICacheManager interface)."""
        # Check memory BEFORE adding to cache
        can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(value)

        with self._cache_lock:
            # Clear cache if needed to make room
            while not can_add:
                if not self.cache:  # No more items to remove
                    raise MemoryError("Cannot fit data in cache even after clearing")
                self.notify_observers(
                    CacheEvent(
                        CacheEventType.MEMORY_WARNING,
                        key,
                        {"memory_usage_percent": self._memory_tracker.get_memory_usage_percent()},
                    )
                )
                self._clear_cache_internal()
                can_add, df_memory_mb = self._memory_tracker.check_memory_before_add(value)

            self.cache[key] = value.copy()
            self._memory_tracker.add_memory_usage(df_memory_mb)

            self.notify_observers(
                CacheEvent(
                    CacheEventType.CACHE_SET,
                    key,
                    {
                        "data_size_mb": df_memory_mb,
                        "total_memory_mb": self._memory_tracker.get_memory_usage(),
                    },
                )
            )

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
