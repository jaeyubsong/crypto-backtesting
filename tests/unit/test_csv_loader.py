"""
Unit tests for CSV data loader.

Tests cover data loading, caching, validation, and error handling
for the CSVDataLoader class.
"""

import asyncio
import shutil
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError, ValidationError
from src.infrastructure.data.csv_loader import CSVDataLoader


class TestCSVDataLoader:
    """Test suite for CSVDataLoader."""

    @pytest.fixture
    def temp_data_dir(self) -> Generator[Path]:
        """Create temporary data directory with sample files."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create directory structure
            binance_dir = temp_dir / "binance" / "futures" / "BTCUSDT" / "1h"
            binance_dir.mkdir(parents=True)

            # Create sample CSV files for 3 consecutive days
            base_date = datetime(2025, 1, 1)
            for i in range(3):
                date = base_date + timedelta(days=i)
                file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

                # Create sample OHLCV data for 24 hours (1 row per hour)
                timestamps = []
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []

                # Convert date to UTC timestamp
                import calendar

                base_timestamp = int(calendar.timegm(date.timetuple()) * 1000)
                base_price = 50000 + i * 1000  # Different price for each day

                for hour in range(24):
                    timestamp = base_timestamp + (hour * 3600 * 1000)
                    open_price = base_price + hour * 10
                    high_price = open_price + 50
                    low_price = open_price - 30
                    close_price = open_price + 20
                    volume = 100 + hour * 5

                    timestamps.append(timestamp)
                    opens.append(open_price)
                    highs.append(high_price)
                    lows.append(low_price)
                    closes.append(close_price)
                    volumes.append(volume)

                # Create DataFrame and save to CSV
                df = pd.DataFrame(
                    {
                        "timestamp": timestamps,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                    }
                )
                df.to_csv(file_path, index=False)

            yield temp_dir

        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def loader(self, temp_data_dir: Path) -> CSVDataLoader:
        """Create CSVDataLoader instance with test data directory."""
        return CSVDataLoader(data_directory=str(temp_data_dir), cache_size=10)

    def test_should_initialize_with_valid_directory(self, temp_data_dir: Path) -> None:
        """Test loader initializes with valid data directory."""
        loader = CSVDataLoader(data_directory=str(temp_data_dir))
        assert loader.data_dir == temp_data_dir
        assert loader.cache_manager.cache.maxsize == 100  # default cache size

    def test_should_raise_error_for_invalid_directory(self) -> None:
        """Test loader raises error for non-existent directory."""
        with pytest.raises(DataError, match="Data directory not found"):
            CSVDataLoader(data_directory="/nonexistent/path")

    def test_should_raise_error_for_missing_binance_directory(self, temp_data_dir: Path) -> None:
        """Test loader raises error when binance directory is missing."""
        # Remove binance directory
        binance_dir = temp_data_dir / "binance"
        shutil.rmtree(binance_dir)

        with pytest.raises(DataError, match="Binance data directory not found"):
            CSVDataLoader(data_directory=str(temp_data_dir))

    @pytest.mark.asyncio
    async def test_should_load_data_for_single_day(self, loader: CSVDataLoader) -> None:
        """Test loading data for a single day."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 1, 23, 59, 59, tzinfo=UTC)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 24  # 24 hours of data
        assert list(data.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert data["open"].iloc[0] == 50000  # First price
        assert data["volume"].iloc[0] == 100  # First volume

    @pytest.mark.asyncio
    async def test_should_load_data_for_multiple_days(self, loader: CSVDataLoader) -> None:
        """Test loading data across multiple days."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 3, 23, 59, 59, tzinfo=UTC)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        assert len(data) == 72  # 3 days * 24 hours
        assert data["timestamp"].is_monotonic_increasing  # Should be sorted

        # Check first and last rows
        assert data["open"].iloc[0] == 50000  # Day 1 first price
        assert data["open"].iloc[24] == 51000  # Day 2 first price
        assert data["open"].iloc[48] == 52000  # Day 3 first price

    @pytest.mark.asyncio
    async def test_should_filter_by_exact_date_range(self, loader: CSVDataLoader) -> None:
        """Test data is filtered to exact date range."""
        # Request only first 12 hours of first day
        start_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2025, 1, 1, 11, 59, 59, tzinfo=UTC)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        assert len(data) == 12  # Only first 12 hours

        # Verify timestamp range
        first_ts = pd.to_datetime(data["timestamp"].iloc[0], unit="ms")
        last_ts = pd.to_datetime(data["timestamp"].iloc[-1], unit="ms")

        # Convert timestamps to UTC aware for comparison
        first_ts_utc = first_ts.tz_localize("UTC") if first_ts.tz is None else first_ts
        last_ts_utc = last_ts.tz_localize("UTC") if last_ts.tz is None else last_ts

        assert first_ts_utc >= start_date
        assert last_ts_utc <= end_date

    @pytest.mark.asyncio
    async def test_should_handle_missing_files_gracefully(self, loader: CSVDataLoader) -> None:
        """Test loader handles missing files without crashing."""
        # Request data that includes missing days
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 10)  # Includes missing days 4-10

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Should return data for available days only (days 1-3)
        assert len(data) == 72  # 3 days of available data
        assert not data.empty

    @pytest.mark.asyncio
    async def test_should_cache_loaded_files(self, loader: CSVDataLoader) -> None:
        """Test that loaded files are cached for performance."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        # Load data twice
        data1 = await loader.load_data("BTCUSDT", "1h", start_date, end_date)
        data2 = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Should be identical
        pd.testing.assert_frame_equal(data1, data2)

        # Check cache has entries
        cache_info = loader.get_cache_info()
        assert cache_info["cache_size"] > 0

    @pytest.mark.asyncio
    async def test_should_validate_input_parameters(self, loader: CSVDataLoader) -> None:
        """Test input parameter validation."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)

        # Empty symbol
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            await loader.load_data("", "1h", start_date, end_date)

        # Empty timeframe
        with pytest.raises(ValidationError, match="Timeframe cannot be empty"):
            await loader.load_data("BTCUSDT", "", start_date, end_date)

        # Invalid date range
        with pytest.raises(ValidationError, match="start_date must be before or equal to end_date"):
            await loader.load_data("BTCUSDT", "1h", end_date, start_date)

        # Invalid timeframe
        with pytest.raises(ValidationError, match="Unsupported timeframe"):
            await loader.load_data("BTCUSDT", "invalid", start_date, end_date)

        # Invalid trading mode
        with pytest.raises(ValidationError, match="Invalid trading mode"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date, "invalid")

    @pytest.mark.asyncio
    async def test_should_validate_csv_structure(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test CSV structure validation."""
        # Create invalid CSV file
        invalid_file = (
            temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h" / "BTCUSDT_1h_2025-01-10.csv"
        )

        # CSV missing required columns
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                # missing high, low, close, volume
            }
        )
        invalid_df.to_csv(invalid_file, index=False)

        start_date = datetime(2025, 1, 10)
        end_date = datetime(2025, 1, 10)

        with pytest.raises(DataError, match="Failed to load CSV file"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    @pytest.mark.asyncio
    async def test_should_validate_ohlc_relationships(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test OHLC relationship validation."""
        # Create CSV with invalid OHLC relationships
        invalid_file = (
            temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h" / "BTCUSDT_1h_2025-01-11.csv"
        )

        invalid_df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                "high": [49000],  # High less than open (invalid)
                "low": [51000],  # Low greater than open (invalid)
                "close": [50500],
                "volume": [100],
            }
        )
        invalid_df.to_csv(invalid_file, index=False)

        start_date = datetime(2025, 1, 11)
        end_date = datetime(2025, 1, 11)

        with pytest.raises(DataError, match="Failed to load CSV file"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    @pytest.mark.asyncio
    async def test_should_handle_empty_csv_files(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test handling of empty CSV files."""
        # Create empty CSV file
        empty_file = (
            temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h" / "BTCUSDT_1h_2025-01-12.csv"
        )
        empty_file.write_text("timestamp,open,high,low,close,volume\n")  # Header only

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 12)

        # Should load successfully, ignoring empty file
        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Should have data from available days (1-3)
        assert len(data) == 72

    def test_should_get_available_symbols(self, loader: CSVDataLoader) -> None:
        """Test getting available symbols."""
        symbols = loader.get_available_symbols("futures")
        assert "BTCUSDT" in symbols

    def test_should_get_available_timeframes(self, loader: CSVDataLoader) -> None:
        """Test getting available timeframes."""
        timeframes = loader.get_available_timeframes("BTCUSDT", "futures")
        assert "1h" in timeframes

    def test_should_clear_cache(self, loader: CSVDataLoader) -> None:
        """Test cache clearing."""
        # Add something to cache first
        loader.cache_manager.cache["test"] = "value"
        assert loader.get_cache_info()["cache_size"] == 1

        loader.clear_cache()
        assert loader.get_cache_info()["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_should_raise_error_when_no_files_found(self, loader: CSVDataLoader) -> None:
        """Test error when no data files are found."""
        start_date = datetime(2030, 1, 1)  # Future date
        end_date = datetime(2030, 1, 2)  # Next day

        with pytest.raises(DataError, match="No valid data files found"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_loading(self, loader: CSVDataLoader) -> None:
        """Test concurrent data loading."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        # Load same data concurrently
        tasks = []
        for _ in range(5):
            task = loader.load_data("BTCUSDT", "1h", start_date, end_date)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All results should be identical
        for result in results[1:]:
            pd.testing.assert_frame_equal(results[0], result)

    @pytest.mark.asyncio
    async def test_should_perform_efficiently_with_large_date_range(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test performance with larger date ranges."""
        # Create additional test files for performance test
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"

        # Add 10 more days of data
        base_date = datetime(2025, 1, 4)
        for i in range(10):
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            # Minimal data for performance
            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(24)],
                    "open": [50000] * 24,
                    "high": [50100] * 24,
                    "low": [49900] * 24,
                    "close": [50000] * 24,
                    "volume": [100] * 24,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 13, 23, 59, 59)  # Include full last day

        import time

        start_time = time.time()
        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)
        load_time = time.time() - start_time

        assert len(data) == 24 * 13  # 13 days of data
        assert load_time < 5.0  # Should load in under 5 seconds

    async def test_should_use_chunked_processing_for_large_datasets(
        self, temp_data_dir: Path
    ) -> None:
        """Test chunked processing is triggered for large datasets."""
        loader = CSVDataLoader(str(temp_data_dir))

        # Create binance directory structure
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        # Create 35 files to trigger chunked processing (threshold is 30)
        base_date = datetime(2025, 1, 1)
        for i in range(35):
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(4)],
                    "open": [50000] * 4,
                    "high": [50100] * 4,
                    "low": [49900] * 4,
                    "close": [50000] * 4,
                    "volume": [100] * 4,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range to trigger chunked processing
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 2, 4, 23, 59, 59)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Verify data was loaded correctly through chunked processing
        assert len(data) > 0
        assert data["timestamp"].is_monotonic_increasing

    async def test_should_reject_path_traversal_in_symbol(self, temp_data_dir: Path) -> None:
        """Test path traversal protection in symbol parameter."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 2, 0, 0, 0)

        # Test various path traversal attempts in symbol
        with pytest.raises(ValidationError, match="contains path traversal characters"):
            await loader.load_data("../../../etc/passwd", "1h", start_date, end_date)

        with pytest.raises(ValidationError, match="contains path traversal characters"):
            await loader.load_data("..\\..\\windows\\system32", "1h", start_date, end_date)

    async def test_should_reject_path_traversal_in_timeframe(self, temp_data_dir: Path) -> None:
        """Test path traversal protection in timeframe parameter."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 2, 0, 0, 0)

        # Test path traversal in timeframe
        with pytest.raises(ValidationError, match="contains path traversal characters"):
            await loader.load_data("BTCUSDT", "../secrets", start_date, end_date)

    async def test_should_reject_invalid_characters_in_paths(self, temp_data_dir: Path) -> None:
        """Test rejection of invalid characters in path components."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 2, 0, 0, 0)

        # Test invalid characters
        with pytest.raises(ValidationError, match="contains invalid characters"):
            await loader.load_data("BTC<>USDT", "1h", start_date, end_date)

        with pytest.raises(ValidationError, match="contains invalid characters"):
            await loader.load_data("BTCUSDT", "1h|dangerous", start_date, end_date)

    async def test_should_reject_empty_path_components(self, temp_data_dir: Path) -> None:
        """Test rejection of empty path components."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 2, 0, 0, 0)

        # Test empty components
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            await loader.load_data("", "1h", start_date, end_date)

        with pytest.raises(ValidationError, match="Timeframe cannot be empty"):
            await loader.load_data("BTCUSDT", "", start_date, end_date)

    async def test_should_reject_oversized_path_components(self, temp_data_dir: Path) -> None:
        """Test rejection of oversized path components."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 2, 0, 0, 0)

        # Test oversized components (>50 characters)
        long_symbol = "A" * 51
        with pytest.raises(ValidationError, match="Symbol too long"):
            await loader.load_data(long_symbol, "1h", start_date, end_date)

    async def test_should_validate_csv_columns_separately(self, temp_data_dir: Path) -> None:
        """Test CSV column validation as separate method."""
        loader = CSVDataLoader(str(temp_data_dir))

        # Create CSV with missing columns
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                # Missing required columns: high, low, close, volume
            }
        )
        df.to_csv(file_path, index=False)

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        with pytest.raises(DataError, match="Failed to load CSV file"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    async def test_should_validate_csv_price_ranges_separately(self, temp_data_dir: Path) -> None:
        """Test CSV price range validation as separate method."""
        loader = CSVDataLoader(str(temp_data_dir))

        # Create CSV with invalid price ranges
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [-50000],  # Invalid negative price
                "high": [50100],
                "low": [49900],
                "close": [50000],
                "volume": [100],
            }
        )
        df.to_csv(file_path, index=False)

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        with pytest.raises(DataError, match="Failed to load CSV file"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    async def test_should_validate_csv_ohlc_relationships_separately(
        self, temp_data_dir: Path
    ) -> None:
        """Test CSV OHLC relationship validation as separate method."""
        loader = CSVDataLoader(str(temp_data_dir))

        # Create CSV with invalid OHLC relationships
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                "high": [49000],  # High less than open (invalid)
                "low": [49900],
                "close": [50000],
                "volume": [100],
            }
        )
        df.to_csv(file_path, index=False)

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        with pytest.raises(DataError, match="Failed to load CSV file"):
            await loader.load_data("BTCUSDT", "1h", start_date, end_date)

    async def test_should_handle_chunked_processing_with_missing_files(
        self, temp_data_dir: Path
    ) -> None:
        """Test chunked processing handles missing files gracefully."""
        loader = CSVDataLoader(str(temp_data_dir))

        # Create binance directory structure
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        # Create only some files to trigger chunked processing with missing files
        base_date = datetime(2025, 1, 1)
        created_files = [0, 2, 4, 10, 15, 20, 25, 30, 35, 40]  # Sparse file creation

        for i in created_files:
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(2)],
                    "open": [50000] * 2,
                    "high": [50100] * 2,
                    "low": [49900] * 2,
                    "close": [50000] * 2,
                    "volume": [100] * 2,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range to trigger chunked processing with missing files
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 2, 15, 23, 59, 59)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Should still load available data
        assert len(data) > 0
        # Data should include rows from created files (some may span date range boundaries)
        assert len(data) >= len(created_files) * 2  # At least 2 rows per created file

    async def test_should_be_thread_safe_for_concurrent_cache_access(
        self, temp_data_dir: Path
    ) -> None:
        """Test thread safety of cache operations."""
        import asyncio

        loader = CSVDataLoader(str(temp_data_dir))

        # Create test data
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50000],
                "volume": [100],
            }
        )
        df.to_csv(file_path, index=False)

        # Test concurrent access
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        async def load_data_task() -> pd.DataFrame:
            return await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Run multiple concurrent operations
        tasks = [load_data_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return same data
        assert all(len(result) == 1 for result in results)
        assert all(result.iloc[0]["open"] == 50000 for result in results)

    async def test_should_support_async_context_manager(self, temp_data_dir: Path) -> None:
        """Test async context manager functionality."""
        # Test context manager usage
        async with CSVDataLoader(str(temp_data_dir)) as loader:
            # Should be able to use loader normally
            symbols = loader.get_available_symbols()
            assert isinstance(symbols, list)

        # Context manager should handle cleanup automatically

    async def test_should_cleanup_resources_on_close(self, temp_data_dir: Path) -> None:
        """Test resource cleanup functionality."""
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

    async def test_should_sanitize_error_messages(self, temp_data_dir: Path) -> None:
        """Test that error messages don't expose sensitive information."""
        loader = CSVDataLoader(str(temp_data_dir))

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        # Try to load non-existent data
        with pytest.raises(DataError) as exc_info:
            await loader.load_data("NONEXISTENT", "1h", start_date, end_date)

        error_message = str(exc_info.value)
        # Error message should not contain full file paths or sensitive details
        assert "Users" not in error_message  # No user directory paths
        assert "Library" not in error_message  # No system paths
        assert "Mobile Documents" not in error_message  # No iCloud paths
        # Should only contain sanitized information
        assert "NONEXISTENT" in error_message or "Failed to load data" in error_message
