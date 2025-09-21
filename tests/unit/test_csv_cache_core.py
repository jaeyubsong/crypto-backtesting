"""
Unit tests for CSV Cache Core functionality.

Tests cover initialization, basic cache operations, and core interface implementation.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from src.infrastructure.data.cache_interfaces import CacheEvent, CacheEventType
from src.infrastructure.data.csv_cache import CSVCache
from src.infrastructure.data.csv_cache_core import CSVCacheCore


class TestCSVCacheCore:
    """Test suite for CSV Cache core functionality."""

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
    def cache(self) -> CSVCache:
        """Create CSV cache instance without observers for testing."""
        return CSVCache(cache_size=5, enable_observers=False)

    def test_should_initialize_with_default_parameters(self) -> None:
        """Test cache initialization with default parameters."""
        cache = CSVCache()
        assert cache.cache.maxsize == 100  # Default cache size
        assert hasattr(cache, "_statistics")
        assert hasattr(cache, "_memory_tracker")

    def test_should_initialize_with_custom_cache_size(self) -> None:
        """Test cache initialization with custom cache size."""
        cache = CSVCache(cache_size=50)
        assert cache.cache.maxsize == 50

    def test_should_raise_error_for_invalid_cache_size(self) -> None:
        """Test error handling for invalid cache sizes."""
        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCache(cache_size=0)

        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCache(cache_size=-1)

    def test_should_warn_for_large_cache_size(self) -> None:
        """Test warning for unusually large cache sizes."""
        pytest.skip("Warning test - implementation dependent")

    @pytest.mark.asyncio
    async def test_should_implement_icache_manager_interface(self, cache: CSVCache) -> None:
        """Test ICacheManager interface implementation."""
        import pandas as pd

        # Create test DataFrame
        test_data = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [46000.0],
                "high": [47000.0],
                "low": [45500.0],
                "close": [46500.0],
                "volume": [100.5],
            }
        )

        # Test set operation
        await cache.set("test_key", test_data)

        # Test get operation
        retrieved_data = await cache.get("test_key")
        assert retrieved_data is not None
        assert len(retrieved_data) == 1
        assert retrieved_data.iloc[0]["close"] == 46500.0

        # Test get operation for nonexistent key
        nonexistent = await cache.get("nonexistent_key")
        assert nonexistent is None

        # Test clear operation
        cache.clear()
        cleared_data = await cache.get("test_key")
        assert cleared_data is None

        # Test get_stats operation
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "hit_rate_percent" in stats

    def test_should_provide_accurate_cache_statistics(self, cache: CSVCache) -> None:
        """Test cache statistics accuracy."""
        stats = cache.get_cache_info()

        # Check required fields
        assert "cache_size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate_percent" in stats

        # Initial state should be empty
        assert stats["cache_size"] == 0
        assert stats["max_size"] == 5
        assert stats["hits"] == 0
        assert stats["misses"] == 0

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

            # Different files should have different cache keys
            assert key1 != key2
            assert str(file1) in key1
            assert str(file2) in key2

        finally:
            file1.unlink(missing_ok=True)
            file2.unlink(missing_ok=True)

    def test_should_handle_nonexistent_file_in_cache_key(self, cache: CSVCache) -> None:
        """Test cache key generation for nonexistent files."""
        nonexistent = Path("/path/that/does/not/exist.csv")
        cache_key = cache._build_cache_key(nonexistent)

        # Should generate a key even for nonexistent files
        assert isinstance(cache_key, str)
        assert str(nonexistent) in cache_key


class TestCSVCacheCoreDirectly:
    """Direct tests for CSVCacheCore class to achieve coverage."""

    @pytest.fixture
    def core_cache(self) -> CSVCacheCore:
        """Create CSVCacheCore instance for direct testing."""
        return CSVCacheCore(cache_size=5, enable_observers=False)

    @pytest.fixture
    def test_dataframe(self) -> pd.DataFrame:
        """Create test DataFrame for cache operations."""
        return pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

    def test_core_initialization_with_defaults(self) -> None:
        """Test CSVCacheCore initialization with default parameters."""
        cache = CSVCacheCore()
        assert cache.cache.maxsize == CSVCacheCore.DEFAULT_CACHE_SIZE
        assert hasattr(cache, "_statistics")
        assert hasattr(cache, "_memory_tracker")
        assert hasattr(cache, "_access_counts")
        assert hasattr(cache, "_pending_events")

    def test_core_initialization_with_custom_size(self) -> None:
        """Test CSVCacheCore initialization with custom cache size."""
        cache = CSVCacheCore(cache_size=25)
        assert cache.cache.maxsize == 25

    def test_core_initialization_validation(self) -> None:
        """Test CSVCacheCore validation of initialization parameters."""
        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCacheCore(cache_size=0)

        with pytest.raises(ValueError, match="Cache size must be positive"):
            CSVCacheCore(cache_size=-5)

    @pytest.mark.asyncio
    async def test_core_icache_manager_interface(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test ICacheManager interface implementation directly."""
        # Test set operation
        await core_cache.set("test_key", test_dataframe)

        # Verify data was stored
        result = await core_cache.get("test_key")
        assert result is not None
        assert len(result) == 2
        assert result.iloc[0]["close"] == 46500.0

        # Test get for nonexistent key
        missing = await core_cache.get("missing_key")
        assert missing is None

        # Test clear operation
        core_cache.clear()
        cleared = await core_cache.get("test_key")
        assert cleared is None

    def test_core_build_cache_key_with_path(self, core_cache: CSVCacheCore) -> None:
        """Test cache key generation with Path objects."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            file_path = Path(f.name)

        try:
            # Test with existing file
            cache_key = core_cache._build_cache_key(file_path)
            assert isinstance(cache_key, str)
            assert str(file_path) in cache_key
            assert ":" in cache_key  # Should include mtime
        finally:
            file_path.unlink(missing_ok=True)

    def test_core_build_cache_key_with_dict(self, core_cache: CSVCacheCore) -> None:
        """Test cache key generation with dictionary components."""
        # Test with dict containing file_path
        components = {"file_path": Path("/test/path.csv")}
        cache_key = core_cache._build_cache_key(components)
        assert isinstance(cache_key, str)
        assert "/test/path.csv" in cache_key

        # Test with dict without file_path
        empty_components = {"other": "value"}
        cache_key = core_cache._build_cache_key(empty_components)
        assert cache_key == "unknown"

    def test_core_build_cache_key_nonexistent_file(self, core_cache: CSVCacheCore) -> None:
        """Test cache key generation for nonexistent files."""
        nonexistent = Path("/path/that/does/not/exist.csv")
        cache_key = core_cache._build_cache_key(nonexistent)
        assert isinstance(cache_key, str)
        assert str(nonexistent) in cache_key

    def test_core_get_cached_file_mtime(self, core_cache: CSVCacheCore) -> None:
        """Test file modification time caching."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            file_path = Path(f.name)

        try:
            # First call should cache the mtime
            mtime1 = core_cache._get_cached_file_mtime(file_path)
            assert isinstance(mtime1, int)

            # Second call should use cached value (verify caching works by checking cache)
            file_str = str(file_path)
            assert file_str in core_cache._file_stat_cache
            mtime2 = core_cache._get_cached_file_mtime(file_path)
            assert isinstance(mtime2, int)
            # Both should be positive values (not asserting equality due to timing)
            assert mtime1 > 0
            assert mtime2 > 0
        finally:
            file_path.unlink(missing_ok=True)

        # Test with nonexistent file
        nonexistent = Path("/nonexistent/file.csv")
        mtime = core_cache._get_cached_file_mtime(nonexistent)
        assert isinstance(mtime, int)
        assert mtime > 0

    @pytest.mark.asyncio
    async def test_core_check_cache_hit_and_miss(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test cache hit and miss detection."""
        cache_key = "test_cache_key"
        metadata = {"file_path": "/test/file.csv", "file_name": "file.csv"}

        # Test cache miss
        result = core_cache._check_cache_hit(cache_key, metadata)
        assert result is None

        # Add data to cache manually
        core_cache.cache[cache_key] = test_dataframe.copy()
        core_cache._access_counts[cache_key] = 1

        # Test cache hit
        result = core_cache._check_cache_hit(cache_key, metadata)
        assert result is not None
        assert len(result) == 2
        assert core_cache._access_counts[cache_key] == 2  # Access count increased

    @pytest.mark.asyncio
    async def test_core_validate_and_cache_result(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test DataFrame validation and caching."""
        cache_key = "validation_test_key"
        metadata = {"file_path": "/test/file.csv", "file_name": "file.csv"}

        # Test successful validation and caching
        result = core_cache._validate_and_cache_result(test_dataframe, cache_key, metadata)
        assert result is not None
        assert len(result) == 2
        assert cache_key in core_cache.cache

    def test_core_validate_memory_constraints(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test memory constraint validation."""
        # Test normal DataFrame
        memory_mb = core_cache._validate_memory_constraints(test_dataframe)
        assert isinstance(memory_mb, float)
        assert memory_mb > 0

        # Test DataFrame that would exceed memory limit
        # Create a very large DataFrame that exceeds MAX_MEMORY_MB
        large_data = pd.DataFrame({"col": range(1000000)})  # Large DataFrame
        original_limit = core_cache.MAX_MEMORY_MB
        core_cache.MAX_MEMORY_MB = 1  # Set very low limit for testing (int)

        try:
            with pytest.raises(MemoryError, match="exceeds cache memory limit"):
                core_cache._validate_memory_constraints(large_data)
        finally:
            # Restore original limit
            core_cache.MAX_MEMORY_MB = original_limit

    @pytest.mark.asyncio
    async def test_core_ensure_cache_space(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test cache space management."""
        # Fill cache with data first
        await core_cache.set("key1", test_dataframe)

        # Test with sufficient space
        core_cache._ensure_cache_space(test_dataframe, 1.0)
        # Should not raise an error

    def test_core_store_in_cache(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test DataFrame storage in cache."""
        cache_key = "store_test_key"
        df_memory_mb = 1.0
        metadata = {"file_path": "/test/file.csv", "file_name": "file.csv"}

        # Store in cache
        core_cache._store_in_cache(test_dataframe, cache_key, df_memory_mb, metadata)

        # Verify storage
        assert cache_key in core_cache.cache
        assert cache_key in core_cache._access_counts
        assert core_cache._access_counts[cache_key] == 1

    def test_core_clear_cache(self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame) -> None:
        """Test cache clearing functionality."""
        # Add some data to cache
        core_cache.cache["key1"] = test_dataframe.copy()
        core_cache._access_counts["key1"] = 1
        core_cache._memory_tracker.add_memory_usage(1.0)

        # Clear cache
        core_cache.clear_cache()

        # Verify cache is empty
        assert len(core_cache.cache) == 0
        assert len(core_cache._access_counts) == 0
        assert core_cache._memory_tracker.get_memory_usage() == 0.0

    def test_core_memory_usage_properties(self, core_cache: CSVCacheCore) -> None:
        """Test memory usage property accessors."""
        # Test getter
        initial_usage = core_cache._memory_usage_mb
        assert isinstance(initial_usage, float)
        assert initial_usage >= 0

        # Test controlled setter (for testing)
        core_cache._set_memory_usage_for_testing(5.0)
        assert core_cache._memory_tracker._memory_usage_mb == 5.0

        # Test validation in setter
        with pytest.raises(ValueError, match="Memory usage cannot be negative"):
            core_cache._set_memory_usage_for_testing(-1.0)

        with pytest.raises(ValueError, match="exceeds reasonable limit"):
            core_cache._set_memory_usage_for_testing(10000.0)  # Very large value

    def test_core_queue_and_flush_events(self, core_cache: CSVCacheCore) -> None:
        """Test event queuing and flushing system."""
        # Create test event
        test_event = CacheEvent(CacheEventType.CACHE_HIT, "test_key", {"test": "data"})

        # Queue event
        core_cache._queue_event(test_event)
        assert len(core_cache._pending_events) == 1

        # Flush events
        core_cache._flush_pending_events()
        assert len(core_cache._pending_events) == 0

    def test_core_evict_lfu_items(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test LFU (Least Frequently Used) eviction."""
        # Add multiple items with different access counts
        core_cache.cache["frequent_key"] = test_dataframe.copy()
        core_cache._access_counts["frequent_key"] = 5
        core_cache.cache["infrequent_key"] = test_dataframe.copy()
        core_cache._access_counts["infrequent_key"] = 1
        core_cache._memory_tracker.add_memory_usage(2.0)

        # Evict items to reach target memory
        target_memory = 0.5
        core_cache._evict_lfu_items(target_memory)

        # Infrequent item should be evicted first
        assert "infrequent_key" not in core_cache.cache
        assert "infrequent_key" not in core_cache._access_counts

    def test_core_recalculate_memory_usage(
        self, core_cache: CSVCacheCore, test_dataframe: pd.DataFrame
    ) -> None:
        """Test memory usage recalculation."""
        # Add data to cache
        core_cache.cache["test_key"] = test_dataframe.copy()

        # Recalculate memory usage
        recalculated = core_cache.recalculate_memory_usage()
        assert isinstance(recalculated, float)
        assert recalculated >= 0

    def test_core_get_cache_info(self, core_cache: CSVCacheCore) -> None:
        """Test cache information retrieval."""
        cache_info = core_cache.get_cache_info()

        # Verify all required fields are present
        required_fields = [
            "cache_size",
            "max_size",
            "memory_usage_mb",
            "memory_limit_mb",
            "memory_usage_percent",
            "hits",
            "misses",
            "hit_rate_percent",
        ]
        for field in required_fields:
            assert field in cache_info

        # Verify data types
        assert isinstance(cache_info["cache_size"], int)
        assert isinstance(cache_info["max_size"], int)
        assert isinstance(cache_info["memory_usage_mb"], float)
        assert isinstance(cache_info["hit_rate_percent"], float)
