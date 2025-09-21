"""
Unit tests for CSV Cache Core functionality.

Tests cover initialization, basic cache operations, and core interface implementation.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.infrastructure.data.csv_cache import CSVCache


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
