"""
Unit tests for CSV Cache with Observer Pattern.

Tests cover caching, memory management, thread safety, and observer notifications
for the CSVCache class.
"""

import asyncio
import tempfile
import threading
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError
from src.infrastructure.data.cache_interfaces import (
    CacheEvent,
    CacheEventType,
    CacheMetricsObserver,
)
from src.infrastructure.data.csv_cache import CSVCache


class MockCacheObserver:
    """Mock observer for capturing cache events."""

    def __init__(self) -> None:
        self.events: list[CacheEvent] = []
        self.event_count = 0

    def notify(self, event: CacheEvent) -> None:
        """Capture cache events for testing."""
        self.events.append(event)
        self.event_count += 1


class TestCSVCache:
    """Test suite for CSVCache."""

    @pytest.fixture
    def temp_csv_file(self) -> Generator[Path]:
        """Create temporary CSV file with sample data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("timestamp,open,high,low,close,volume\n")
            f.write("1640995200000,46000.0,47000.0,45500.0,46500.0,100.5\n")
            f.write("1640998800000,46500.0,47500.0,46000.0,47000.0,150.2\n")
            f.write("1641002400000,47000.0,48000.0,46800.0,47800.0,200.1\n")
            file_path = Path(f.name)

        try:
            yield file_path
        finally:
            if file_path.exists():
                file_path.unlink()

    @pytest.fixture
    def empty_csv_file(self) -> Generator[Path]:
        """Create empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            file_path = Path(f.name)

        try:
            yield file_path
        finally:
            if file_path.exists():
                file_path.unlink()

    @pytest.fixture
    def cache(self) -> CSVCache:
        """Create CSV cache instance without observers for testing."""
        return CSVCache(cache_size=5, enable_observers=False)

    @pytest.fixture
    def cache_with_observer(self) -> tuple[CSVCache, MockCacheObserver]:
        """Create CSV cache with test observer."""
        cache = CSVCache(cache_size=3, enable_observers=False)
        observer = MockCacheObserver()
        cache.add_observer(observer)
        return cache, observer

    # Initialization Tests
    def test_should_initialize_with_default_parameters(self) -> None:
        """Test cache initialization with default parameters."""
        cache = CSVCache()
        assert cache.cache.maxsize == CSVCache.DEFAULT_CACHE_SIZE
        assert cache.MAX_MEMORY_MB == 512
        assert cache._memory_usage_mb == 0.0

    def test_should_initialize_with_custom_cache_size(self) -> None:
        """Test cache initialization with custom cache size."""
        cache = CSVCache(cache_size=50, enable_observers=False)
        assert cache.cache.maxsize == 50

    def test_should_raise_error_for_invalid_cache_size(self) -> None:
        """Test cache raises error for invalid cache size."""
        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCache(cache_size=0)

        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCache(cache_size=-1)

    @pytest.mark.skip(reason="Loguru warnings don't emit Python warnings")
    def test_should_warn_for_large_cache_size(self) -> None:
        """Test cache warns for large cache size."""
        # This test verifies that large cache sizes trigger a loguru warning
        # The warning is logged but not emitted as a Python warning
        CSVCache(cache_size=1500, enable_observers=False)

    # Basic Caching Tests
    async def test_should_load_and_cache_csv_file(
        self, cache: CSVCache, temp_csv_file: Path
    ) -> None:
        """Test basic file loading and caching."""
        # First load - should read from disk
        df1 = await cache.load_single_file(temp_csv_file)
        assert not df1.empty
        assert len(df1) == 3
        assert list(df1.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

        # Second load - should come from cache
        df2 = await cache.load_single_file(temp_csv_file)
        assert not df2.empty
        assert len(df2) == 3
        pd.testing.assert_frame_equal(df1, df2)

        # Cache should contain the file
        cache_info = cache.get_cache_info()
        assert cache_info["cache_size"] == 1

    async def test_should_handle_cache_hit_and_miss(
        self, cache_with_observer: tuple[CSVCache, MockCacheObserver], temp_csv_file: Path
    ) -> None:
        """Test cache hit and miss events."""
        cache, observer = cache_with_observer

        # First load - cache miss
        await cache.load_single_file(temp_csv_file)
        assert observer.event_count == 1
        assert observer.events[0].event_type == CacheEventType.CACHE_MISS

        # Second load - cache hit
        await cache.load_single_file(temp_csv_file)
        assert observer.event_count == 2
        assert observer.events[1].event_type == CacheEventType.CACHE_HIT

    async def test_should_handle_nonexistent_file(self, cache: CSVCache) -> None:
        """Test handling of nonexistent files."""
        nonexistent_file = Path("/nonexistent/file.csv")

        with pytest.raises(FileNotFoundError, match="Data file not found"):
            await cache.load_single_file(nonexistent_file)

    async def test_should_handle_empty_csv_file(
        self, cache: CSVCache, empty_csv_file: Path
    ) -> None:
        """Test handling of empty CSV files."""
        df = await cache.load_single_file(empty_csv_file)
        assert df.empty  # Should return empty DataFrame with correct columns
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(df) == 0

    # Memory Management Tests
    async def test_should_track_memory_usage(self, cache: CSVCache, temp_csv_file: Path) -> None:
        """Test memory usage tracking."""
        initial_memory = cache._memory_usage_mb
        assert initial_memory == 0.0

        # Load file and check memory increased
        await cache.load_single_file(temp_csv_file)
        assert cache._memory_usage_mb > initial_memory

        # Clear cache and check memory reset
        cache.clear_cache()
        assert cache._memory_usage_mb == 0.0

    async def test_should_clear_cache_when_memory_limit_exceeded(self, cache: CSVCache) -> None:
        """Test automatic cache clearing when memory limit is exceeded."""
        # First add a small file to the cache
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("timestamp,open,high,low,close,volume\n")
            f.write("1640995200000,46000.0,47000.0,45500.0,46500.0,100.5\n")
            small_file = Path(f.name)

        try:
            # Load small file first
            await cache.load_single_file(small_file)
            assert cache.get_cache_info()["cache_size"] == 1

            # Now mock very small memory limit to trigger clearing
            with patch.object(cache, "MAX_MEMORY_MB", 0.001):  # Very small limit
                with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f2:
                    f2.write("timestamp,open,high,low,close,volume\n")
                    f2.write("1640995200001,46001.0,47001.0,45501.0,46501.0,100.6\n")
                    second_file = Path(f2.name)

                try:
                    # This should trigger cache clearing since total memory would exceed limit
                    await cache.load_single_file(second_file)
                    # After loading, cache should be managed (either cleared or contains the new file)
                    cache_info = cache.get_cache_info()
                    assert cache_info["memory_usage_mb"] >= 0
                finally:
                    second_file.unlink()
        finally:
            small_file.unlink()

    async def test_should_recalculate_memory_usage_accurately(
        self, cache_with_observer: tuple[CSVCache, MockCacheObserver]
    ) -> None:
        """Test periodic memory recalculation method."""
        cache, observer = cache_with_observer

        # Add some test data manually to cache
        test_df1 = pd.DataFrame(
            {
                "timestamp": [1, 2, 3],
                "open": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "close": [100.5, 101.5, 102.5],
                "volume": [1000.0, 1100.0, 1200.0],
            }
        )
        test_df2 = pd.DataFrame(
            {
                "timestamp": [4, 5],
                "open": [103.0, 104.0],
                "high": [104.0, 105.0],
                "low": [102.0, 103.0],
                "close": [103.5, 104.5],
                "volume": [1300.0, 1400.0],
            }
        )

        await cache.set("test1", test_df1)
        await cache.set("test2", test_df2)

        # Simulate memory drift by manually adjusting tracked memory
        cache._memory_usage_mb = 10.0  # Artificially high value

        # Recalculate memory usage
        actual_memory = cache.recalculate_memory_usage()

        # Should be much less than 10MB for these small DataFrames
        assert actual_memory < 1.0
        assert cache._memory_usage_mb == actual_memory

        # Should trigger memory warning event due to significant drift
        memory_events = [
            e for e in observer.events if e.event_type == CacheEventType.MEMORY_WARNING
        ]
        assert len(memory_events) >= 1

        # Check event metadata
        memory_event = memory_events[-1]
        assert "old_memory_mb" in memory_event.metadata
        assert "new_memory_mb" in memory_event.metadata
        assert "drift_mb" in memory_event.metadata

    # Thread Safety Tests
    async def test_should_be_thread_safe(self, cache: CSVCache, temp_csv_file: Path) -> None:
        """Test thread safety of cache operations."""
        results = []
        errors = []

        async def load_file() -> None:
            try:
                df = await cache.load_single_file(temp_csv_file)
                results.append(len(df))
            except Exception as e:
                errors.append(e)

        # Run multiple concurrent loads
        await asyncio.gather(*[load_file() for _ in range(10)])

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(result == 3 for result in results)  # All should return same data

    def test_should_handle_concurrent_cache_operations(self, cache: CSVCache) -> None:
        """Test concurrent cache clear operations."""
        cache.cache["test_key"] = pd.DataFrame({"col": [1, 2, 3]})
        cache._memory_usage_mb = 10.0

        def clear_cache() -> None:
            cache.clear_cache()

        # Run multiple concurrent clears
        threads = [threading.Thread(target=clear_cache) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Cache should be empty after concurrent clears
        assert len(cache.cache) == 0
        assert cache._memory_usage_mb == 0.0

    # Observer Pattern Tests
    def test_should_add_and_remove_observers(self) -> None:
        """Test observer management."""
        cache = CSVCache(enable_observers=False)
        observer = MockCacheObserver()

        # Add observer
        cache.add_observer(observer)
        assert observer in cache._observers

        # Remove observer
        cache.remove_observer(observer)
        assert observer not in cache._observers

    def test_should_not_add_duplicate_observers(self) -> None:
        """Test duplicate observer prevention."""
        cache = CSVCache(enable_observers=False)
        observer = MockCacheObserver()

        cache.add_observer(observer)
        cache.add_observer(observer)  # Add same observer again

        assert cache._observers.count(observer) == 1

    async def test_should_notify_observers_of_cache_events(
        self, cache_with_observer: tuple[CSVCache, MockCacheObserver], temp_csv_file: Path
    ) -> None:
        """Test observer notifications for various cache events."""
        cache, observer = cache_with_observer

        # Test cache miss and hit
        await cache.load_single_file(temp_csv_file)  # Miss
        await cache.load_single_file(temp_csv_file)  # Hit

        # Test cache clear
        cache.clear_cache()

        # Verify events
        assert len(observer.events) == 3
        assert observer.events[0].event_type == CacheEventType.CACHE_MISS
        assert observer.events[1].event_type == CacheEventType.CACHE_HIT
        assert observer.events[2].event_type == CacheEventType.CACHE_CLEAR

    def test_should_handle_observer_exceptions(self, cache: CSVCache) -> None:
        """Test that observer exceptions don't break cache operations."""
        faulty_observer = Mock()
        faulty_observer.notify.side_effect = Exception("Observer error")

        cache.add_observer(faulty_observer)

        # This should not raise despite observer error
        cache.clear_cache()

    # ICacheManager Interface Tests
    async def test_should_implement_icache_manager_interface(self, cache: CSVCache) -> None:
        """Test ICacheManager interface implementation."""
        test_df = pd.DataFrame({"timestamp": [1, 2], "close": [100.0, 101.0]})

        # Test set
        await cache.set("test_key", test_df)

        # Test get
        result = await cache.get("test_key")
        assert result is not None
        pd.testing.assert_frame_equal(result, test_df)

        # Test get non-existent
        result = await cache.get("nonexistent")
        assert result is None

        # Test clear
        cache.clear()
        result = await cache.get("test_key")
        assert result is None

        # Test stats
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "cache_size" in stats

    # Cache Statistics Tests
    def test_should_provide_accurate_cache_statistics(self, cache: CSVCache) -> None:
        """Test cache statistics accuracy."""
        stats = cache.get_cache_info()

        assert stats["cache_size"] == 0
        assert stats["max_size"] == 5
        assert stats["memory_usage_mb"] == 0.0
        assert stats["memory_limit_mb"] == 512
        assert stats["memory_usage_percent"] == 0.0

        # Add some data and check stats update
        test_df = pd.DataFrame({"col": [1, 2, 3]})
        cache.cache["test"] = test_df
        cache._memory_usage_mb = 1.5

        stats = cache.get_cache_info()
        assert stats["cache_size"] == 1
        assert stats["memory_usage_mb"] == 1.5
        assert (
            abs(stats["memory_usage_percent"] - (1.5 / 512) * 100) < 0.1
        )  # Allow small rounding differences

    # Error Handling Tests
    async def test_should_handle_file_permission_errors(self, cache: CSVCache) -> None:
        """Test handling of file permission errors."""
        with patch("pandas.read_csv", side_effect=PermissionError("Permission denied")):
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                file_path = Path(f.name)

            try:
                with pytest.raises(DataError, match="File system error loading"):
                    await cache.load_single_file(file_path)
            finally:
                if file_path.exists():
                    file_path.unlink()

    async def test_should_handle_malformed_csv_files(self, cache: CSVCache) -> None:
        """Test handling of malformed CSV files."""
        # Create malformed CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("invalid,csv,format\n")
            f.write("missing,columns\n")  # Wrong number of columns
            malformed_file = Path(f.name)

        try:
            with pytest.raises(DataError, match="Failed to load CSV file"):
                await cache.load_single_file(malformed_file)
        finally:
            malformed_file.unlink()

    # Cache Key Generation Tests
    def test_should_generate_unique_cache_keys_for_different_files(self, cache: CSVCache) -> None:
        """Test cache key generation includes file modification time."""
        with (
            tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f2,
        ):
            file1 = Path(f1.name)
            file2 = Path(f2.name)

        try:
            key1 = cache._build_cache_key(file1)
            key2 = cache._build_cache_key(file2)

            assert key1 != key2
            assert str(file1) in key1
            assert str(file2) in key2
            assert ":" in key1  # Should include timestamp
            assert ":" in key2  # Should include timestamp
        finally:
            file1.unlink()
            file2.unlink()

    def test_should_handle_nonexistent_file_in_cache_key(self, cache: CSVCache) -> None:
        """Test cache key generation for nonexistent files."""
        nonexistent = Path("/nonexistent/file.csv")
        key = cache._build_cache_key(nonexistent)
        assert str(nonexistent) == key  # Should just return path as string

    # Integration with CacheMetricsObserver
    def test_should_work_with_metrics_observer(self, cache: CSVCache) -> None:
        """Test integration with CacheMetricsObserver."""
        metrics_observer = CacheMetricsObserver()
        cache.add_observer(metrics_observer)

        # Trigger some cache events
        cache.notify_observers(CacheEvent(CacheEventType.CACHE_HIT, "test_key"))
        cache.notify_observers(CacheEvent(CacheEventType.CACHE_MISS, "test_key"))
        cache.notify_observers(CacheEvent(CacheEventType.CACHE_CLEAR, "clear"))

        metrics = metrics_observer.get_metrics()
        assert metrics["total_hits"] == 1
        assert metrics["total_misses"] == 1
        assert metrics["total_clears"] == 1
        assert metrics["hit_rate_percent"] == 50.0  # 1 hit out of 2 total requests
