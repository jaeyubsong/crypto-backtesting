"""
Memory tracking utilities for cache management.

This module provides memory tracking and management functionality for data caching.
"""

from threading import RLock
from typing import Any

import pandas as pd
from loguru import logger

from .cache_interfaces import CacheEvent, CacheEventType, CacheSubject


class MemoryTracker:
    """Handles memory usage tracking and limits for cache operations."""

    def __init__(self, memory_limit_mb: float = 512.0) -> None:
        """Initialize memory tracker with specified limit."""
        self._memory_lock = RLock()
        self._memory_usage_mb = 0.0
        self.memory_limit_mb = memory_limit_mb

    def estimate_dataframe_memory(self, df: pd.DataFrame) -> float:
        """Estimate DataFrame memory usage in MB."""
        return float(df.memory_usage(deep=True).sum() / (1024 * 1024))

    def check_memory_before_add(self, df: pd.DataFrame) -> tuple[bool, float]:
        """
        Check if DataFrame can be added without exceeding memory limit.

        Returns:
            tuple: (can_add: bool, df_memory_mb: float)
        """
        df_memory_mb = self.estimate_dataframe_memory(df)

        # Prevent caching if single DataFrame exceeds memory limit
        if df_memory_mb > self.memory_limit_mb:
            raise MemoryError(
                f"DataFrame size ({df_memory_mb:.1f}MB) exceeds cache memory limit "
                f"({self.memory_limit_mb}MB)"
            )

        with self._memory_lock:
            can_add = (self._memory_usage_mb + df_memory_mb) <= self.memory_limit_mb
            return can_add, df_memory_mb

    def add_memory_usage(self, memory_mb: float) -> None:
        """Add memory usage to tracker."""
        with self._memory_lock:
            self._memory_usage_mb += memory_mb

    def clear_memory_usage(self) -> float:
        """Clear all memory usage and return the amount that was cleared."""
        with self._memory_lock:
            cleared_memory = self._memory_usage_mb
            self._memory_usage_mb = 0.0
            return cleared_memory

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        with self._memory_lock:
            return self._memory_usage_mb

    def get_memory_usage_percent(self) -> float:
        """Get current memory usage as percentage of limit."""
        with self._memory_lock:
            return (self._memory_usage_mb / self.memory_limit_mb) * 100

    def recalculate_memory_from_cache(
        self, cache_values: list[pd.DataFrame], observer: CacheSubject | None = None
    ) -> float:
        """
        Recalculate memory usage from actual cached DataFrames.

        Args:
            cache_values: List of DataFrames currently in cache
            observer: Optional observer to notify of memory changes

        Returns:
            New total memory usage in MB
        """
        total_memory_mb = 0.0
        for df in cache_values:
            total_memory_mb += self.estimate_dataframe_memory(df)

        with self._memory_lock:
            old_memory = self._memory_usage_mb
            self._memory_usage_mb = total_memory_mb

            # Notify observer if memory usage changed significantly (>5% difference)
            if observer and abs(old_memory - total_memory_mb) > (old_memory * 0.05):
                observer.notify_observers(
                    CacheEvent(
                        CacheEventType.MEMORY_WARNING,
                        "memory_recalculation",
                        metadata={
                            "old_memory_mb": old_memory,
                            "new_memory_mb": total_memory_mb,
                            "drift_mb": total_memory_mb - old_memory,
                        },
                    )
                )
                logger.info(
                    f"Memory usage recalculated: {old_memory:.1f}MB → {total_memory_mb:.1f}MB "
                    f"(drift: {total_memory_mb - old_memory:+.1f}MB)"
                )

            return total_memory_mb

    def should_clear_cache_for_memory(self, new_data_mb: float) -> bool:
        """Check if cache should be cleared to accommodate new data."""
        with self._memory_lock:
            return (self._memory_usage_mb + new_data_mb) > self.memory_limit_mb

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory tracking statistics."""
        with self._memory_lock:
            return {
                "memory_usage_mb": round(self._memory_usage_mb, 2),
                "memory_limit_mb": self.memory_limit_mb,
                "memory_usage_percent": round(self.get_memory_usage_percent(), 1),
                "available_memory_mb": round(self.memory_limit_mb - self._memory_usage_mb, 2),
            }
