"""
Advanced functionality tests for CSV data loader.

Tests cover resource management, async context managers,
cleanup operations, and advanced error handling.
"""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from src.infrastructure.data.csv_loader import CSVDataLoader


class TestCSVDataLoaderAdvanced:
    """Advanced functionality test suite for CSVDataLoader."""

    @pytest.fixture
    def temp_data_dir(self) -> Generator[Path]:
        """Create temporary data directory."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            yield temp_dir

        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def loader(self, temp_data_dir: Path) -> CSVDataLoader:
        """Create CSVDataLoader instance with test data directory."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)
        return CSVDataLoader(data_directory=str(temp_data_dir), cache_size=10)

    async def test_should_support_async_context_manager(self, temp_data_dir: Path) -> None:
        """Test async context manager functionality."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)

        # Test context manager usage
        async with CSVDataLoader(str(temp_data_dir)) as loader:
            # Should be able to use loader normally
            symbols = loader.get_available_symbols()
            assert isinstance(symbols, list)

        # Context manager should handle cleanup automatically

    async def test_should_cleanup_resources_on_close(self, temp_data_dir: Path) -> None:
        """Test resource cleanup functionality."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)

        loader = CSVDataLoader(str(temp_data_dir))

        # Add something to cache first
        cache_info_before = loader.get_cache_info()
        assert cache_info_before["cache_size"] == 0

        # Manually add to cache for testing
        with loader.cache_manager._cache_lock:
            loader.cache_manager.cache["test_key"] = pd.DataFrame({"test": [1, 2, 3]})

        # Verify cache has data
        cache_info_after = loader.get_cache_info()
        assert cache_info_after["cache_size"] == 1

        # Close should clear cache
        await loader.close()

        # Verify cache is cleared
        cache_info_final = loader.get_cache_info()
        assert cache_info_final["cache_size"] == 0
