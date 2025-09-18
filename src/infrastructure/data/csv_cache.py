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

from .csv_validator import CSVValidator


class CSVCache:
    """Handles caching and single file loading for CSV data."""

    def __init__(self, cache_size: int = 100):
        """Initialize the CSV cache."""
        self.cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = RLock()  # Thread-safe cache access

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
                return self.cache[cache_key].copy()
        return None

    async def _load_csv_from_disk(self, file_path: Path) -> pd.DataFrame:
        """Load CSV file from disk using async executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: pd.read_csv(
                file_path,
                dtype={
                    "timestamp": "int64",
                    "open": "float64",
                    "high": "float64",
                    "low": "float64",
                    "close": "float64",
                    "volume": "float64",
                },
            ),
        )

    def _validate_and_cache_result(
        self, df: pd.DataFrame, cache_key: str, file_path: Path
    ) -> pd.DataFrame:
        """Validate DataFrame and cache the result."""
        CSVValidator.validate_csv_structure(df, file_path)

        with self._cache_lock:
            self.cache[cache_key] = df.copy()

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
            self.cache.clear()
        logger.info("Data cache cleared")

    def get_cache_info(self) -> dict[str, int]:
        """Get cache statistics (thread-safe)."""
        with self._cache_lock:
            return {
                "cache_size": len(self.cache),
                "max_size": int(self.cache.maxsize) if self.cache.maxsize else 0,
                "hits": getattr(self.cache, "hits", 0),
                "misses": getattr(self.cache, "misses", 0),
            }
