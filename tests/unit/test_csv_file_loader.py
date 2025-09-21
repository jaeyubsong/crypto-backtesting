"""
Unit tests for CSV File Loader functionality.

Tests cover file loading operations, validation, error handling, and caching integration.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError
from src.infrastructure.data.csv_cache_core import CSVCacheCore
from src.infrastructure.data.csv_file_loader import CSVCache, CSVFileLoader


class TestCSVFileLoader:
    """Test suite for CSVFileLoader class."""

    @pytest.fixture
    def cache_core(self) -> CSVCacheCore:
        """Create CSVCacheCore instance for testing."""
        return CSVCacheCore(cache_size=5, enable_observers=False)

    @pytest.fixture
    def file_loader(self, cache_core: CSVCacheCore) -> CSVFileLoader:
        """Create CSVFileLoader instance for testing."""
        return CSVFileLoader(cache_core)

    @pytest.fixture
    def temp_csv_file(self) -> Generator[Path]:
        """Create temporary CSV file with valid OHLCV data."""
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
        """Create empty CSV file for testing empty file handling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Write only headers or leave completely empty
            pass
        file_path = Path(f.name)

        try:
            yield file_path
        finally:
            if file_path.exists():
                file_path.unlink()

    @pytest.fixture
    def invalid_csv_file(self) -> Generator[Path]:
        """Create invalid CSV file for testing error handling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("invalid,csv,content\n")
            f.write("not,numeric,data\n")
            file_path = Path(f.name)

        try:
            yield file_path
        finally:
            if file_path.exists():
                file_path.unlink()

    def test_file_loader_initialization(self, cache_core: CSVCacheCore) -> None:
        """Test CSVFileLoader initialization."""
        loader = CSVFileLoader(cache_core)
        assert loader.cache_core is cache_core

    @pytest.mark.asyncio
    async def test_load_single_file_success(
        self, file_loader: CSVFileLoader, temp_csv_file: Path
    ) -> None:
        """Test successful loading of a single CSV file."""
        result = await file_loader.load_single_file(temp_csv_file)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert result.iloc[0]["close"] == 46500.0
        assert result.iloc[1]["close"] == 47000.0
        assert result.iloc[2]["close"] == 47800.0

    @pytest.mark.asyncio
    async def test_load_single_file_with_caching(
        self, file_loader: CSVFileLoader, temp_csv_file: Path
    ) -> None:
        """Test file loading with cache hit on second load."""
        # First load - should read from disk
        result1 = await file_loader.load_single_file(temp_csv_file)
        assert len(result1) == 3

        # Second load - should hit cache
        result2 = await file_loader.load_single_file(temp_csv_file)
        assert len(result2) == 3

        # Results should be equal but not the same object (due to copy())
        pd.testing.assert_frame_equal(result1, result2)
        assert result1 is not result2

    @pytest.mark.asyncio
    async def test_load_single_file_not_found(self, file_loader: CSVFileLoader) -> None:
        """Test loading non-existent file raises FileNotFoundError."""
        nonexistent_file = Path("/path/that/does/not/exist.csv")

        with pytest.raises(FileNotFoundError, match="Data file not found"):
            await file_loader.load_single_file(nonexistent_file)

    @pytest.mark.asyncio
    async def test_load_single_file_empty_file(
        self, file_loader: CSVFileLoader, empty_csv_file: Path
    ) -> None:
        """Test loading empty CSV file returns empty DataFrame with correct columns."""
        result = await file_loader.load_single_file(empty_csv_file)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    @pytest.mark.asyncio
    async def test_load_single_file_csv_read_error(
        self, file_loader: CSVFileLoader, invalid_csv_file: Path
    ) -> None:
        """Test handling of CSV reading errors."""
        with pytest.raises(DataError, match="Failed to load CSV file"):
            await file_loader.load_single_file(invalid_csv_file)

    @pytest.mark.asyncio
    async def test_load_csv_from_disk(
        self, file_loader: CSVFileLoader, temp_csv_file: Path
    ) -> None:
        """Test direct CSV loading from disk."""
        result = await file_loader._load_csv_from_disk(temp_csv_file)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # Verify data types are correct
        assert result["timestamp"].dtype == "int64"
        assert result["open"].dtype == "float64"
        assert result["high"].dtype == "float64"
        assert result["low"].dtype == "float64"
        assert result["close"].dtype == "float64"
        assert result["volume"].dtype == "float64"

    def test_validate_and_cache_result(
        self, file_loader: CSVFileLoader, temp_csv_file: Path
    ) -> None:
        """Test DataFrame validation and caching."""
        # Create test DataFrame
        test_df = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [46000.0],
                "high": [47000.0],
                "low": [45500.0],
                "close": [46500.0],
                "volume": [100.5],
            }
        )

        cache_key = "test_validation_key"

        result = file_loader._validate_and_cache_result(test_df, cache_key, temp_csv_file)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert cache_key in file_loader.cache_core.cache

    def test_handle_empty_file(self, file_loader: CSVFileLoader) -> None:
        """Test empty file handling returns correct empty DataFrame."""
        result = file_loader._handle_empty_file()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_handle_loading_error(self, file_loader: CSVFileLoader, temp_csv_file: Path) -> None:
        """Test error handling for loading failures."""
        test_error = ValueError("Test error")

        with pytest.raises(DataError, match="Failed to load CSV file"):
            file_loader._handle_loading_error(test_error, temp_csv_file)

    @pytest.mark.asyncio
    async def test_os_error_handling(self, file_loader: CSVFileLoader) -> None:
        """Test OS error handling during file operations."""
        # Create a file path that will trigger FileNotFoundError (which maps to OS error handling)
        nonexistent_path = Path("/nonexistent/directory/file.csv")

        with pytest.raises(FileNotFoundError, match="Data file not found"):
            await file_loader.load_single_file(nonexistent_path)


class TestCSVCacheWrapper:
    """Test suite for CSVCache wrapper class functionality."""

    @pytest.fixture
    def csv_cache(self) -> CSVCache:
        """Create CSVCache instance for testing."""
        return CSVCache(cache_size=5, enable_observers=False)

    @pytest.fixture
    def temp_csv_file(self) -> Generator[Path]:
        """Create temporary CSV file with valid OHLCV data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("timestamp,open,high,low,close,volume\n")
            f.write("1640995200000,46000.0,47000.0,45500.0,46500.0,100.5\n")
            f.write("1640998800000,46500.0,47500.0,46000.0,47000.0,150.2\n")
            file_path = Path(f.name)

        try:
            yield file_path
        finally:
            if file_path.exists():
                file_path.unlink()

    def test_csv_cache_initialization(self) -> None:
        """Test CSVCache wrapper initialization."""
        cache = CSVCache()
        assert cache.cache.maxsize == CSVCache.DEFAULT_CACHE_SIZE
        assert hasattr(cache, "file_loader")
        assert isinstance(cache.file_loader, CSVFileLoader)

    def test_csv_cache_initialization_with_params(self) -> None:
        """Test CSVCache initialization with custom parameters."""
        cache = CSVCache(cache_size=25, enable_observers=True)
        assert cache.cache.maxsize == 25
        assert hasattr(cache, "file_loader")

    @pytest.mark.asyncio
    async def test_csv_cache_load_single_file_delegation(
        self, csv_cache: CSVCache, temp_csv_file: Path
    ) -> None:
        """Test that CSVCache delegates load_single_file to file_loader."""
        result = await csv_cache.load_single_file(temp_csv_file)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_csv_cache_inheritance(self) -> None:
        """Test that CSVCache properly inherits from CSVCacheCore."""
        cache = CSVCache()

        # Should have CSVCacheCore methods and attributes
        assert hasattr(cache, "cache")
        assert hasattr(cache, "_statistics")
        assert hasattr(cache, "_memory_tracker")
        assert hasattr(cache, "get_cache_info")
        assert hasattr(cache, "clear_cache")

        # Should also have file loading capability
        assert hasattr(cache, "file_loader")
        assert hasattr(cache, "load_single_file")

    @pytest.mark.asyncio
    async def test_csv_cache_backward_compatibility(
        self, csv_cache: CSVCache, temp_csv_file: Path
    ) -> None:
        """Test backward compatibility of CSVCache interface."""
        # Test that it can be used as both cache and file loader

        # Use as cache (ICacheManager interface)
        test_df = pd.DataFrame({"col": [1, 2, 3]})
        await csv_cache.set("test_key", test_df)
        cached_result = await csv_cache.get("test_key")
        assert cached_result is not None
        assert len(cached_result) == 3

        # Use as file loader
        file_result = await csv_cache.load_single_file(temp_csv_file)
        assert isinstance(file_result, pd.DataFrame)
        assert len(file_result) == 2

        # Get statistics
        stats = csv_cache.get_stats()
        assert isinstance(stats, dict)
        assert "cache_size" in stats
