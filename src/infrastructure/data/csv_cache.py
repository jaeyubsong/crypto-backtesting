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
from .csv_validator import CSVValidator


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

        self.cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = RLock()  # Thread-safe cache access
        self._memory_usage_mb = 0.0  # Track approximate memory usage

        # Set up default observers if enabled
        if enable_observers:
            for observer in create_standard_cache_observers():
                self.add_observer(observer)

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

        # Estimate memory usage (rough approximation)
        df_memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

        with self._cache_lock:
            # Check if adding this would exceed memory limit
            if self._memory_usage_mb + df_memory_mb > self.MAX_MEMORY_MB:
                logger.warning(
                    f"Cache memory limit approached ({self._memory_usage_mb:.1f}MB), clearing cache"
                )
                self._clear_cache_internal()

            self.cache[cache_key] = df.copy()
            self._memory_usage_mb += df_memory_mb

            logger.debug(
                f"Cached {file_path.name} ({df_memory_mb:.1f}MB), total cache: {self._memory_usage_mb:.1f}MB"
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
            old_memory = self._memory_usage_mb
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
        self._memory_usage_mb = 0.0

    # ICacheManager interface implementation
    async def get(self, key: str) -> pd.DataFrame | None:
        """Retrieve data from cache (ICacheManager interface)."""
        with self._cache_lock:
            if key in self.cache:
                self.notify_observers(CacheEvent(CacheEventType.CACHE_HIT, key))
                return self.cache[key].copy()
            else:
                self.notify_observers(CacheEvent(CacheEventType.CACHE_MISS, key))
                return None

    async def set(self, key: str, value: pd.DataFrame) -> None:
        """Store data in cache (ICacheManager interface)."""
        df_memory_mb = value.memory_usage(deep=True).sum() / (1024 * 1024)

        with self._cache_lock:
            if self._memory_usage_mb + df_memory_mb > self.MAX_MEMORY_MB:
                self.notify_observers(
                    CacheEvent(
                        CacheEventType.MEMORY_WARNING,
                        key,
                        {
                            "memory_usage_percent": (self._memory_usage_mb / self.MAX_MEMORY_MB)
                            * 100
                        },
                    )
                )
                self._clear_cache_internal()

            self.cache[key] = value.copy()
            self._memory_usage_mb += df_memory_mb

            self.notify_observers(
                CacheEvent(
                    CacheEventType.CACHE_SET,
                    key,
                    {"data_size_mb": df_memory_mb, "total_memory_mb": self._memory_usage_mb},
                )
            )

    def clear(self) -> None:
        """Clear all cache entries (ICacheManager interface)."""
        self.clear_cache()

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics (ICacheManager interface)."""
        return self.get_cache_info()

    def get_cache_info(self) -> dict[str, int | float]:
        """Get cache statistics (thread-safe)."""
        with self._cache_lock:
            return {
                "cache_size": len(self.cache),
                "max_size": int(self.cache.maxsize) if self.cache.maxsize else 0,
                "memory_usage_mb": round(self._memory_usage_mb, 2),
                "memory_limit_mb": self.MAX_MEMORY_MB,
                "memory_usage_percent": round(
                    (self._memory_usage_mb / self.MAX_MEMORY_MB) * 100, 1
                ),
                # Note: LRUCache doesn't have built-in hit/miss statistics
                "hits": 0,  # Would need custom implementation for accurate tracking
                "misses": 0,
            }
