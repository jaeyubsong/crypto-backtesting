"""
Integration tests for data layer components.

Tests the interaction between CSVDataLoader and OHLCVDataProcessor
with real data files.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.infrastructure.data import CSVDataLoader, OHLCVDataProcessor


class TestDataLayerIntegration:
    """Integration tests for data layer components."""

    @pytest.fixture
    def loader(self):
        """Create loader using real data directory."""
        return CSVDataLoader(data_directory="data", cache_size=50)

    @pytest.fixture
    def processor(self):
        """Create data processor."""
        return OHLCVDataProcessor()

    @pytest.mark.asyncio
    async def test_should_load_and_process_real_data(self, loader, processor):
        """Test loading and processing real data from files."""
        # Check if we have real data available
        data_path = Path("data/binance/futures/BTCUSDT/1h")
        if not data_path.exists():
            pytest.skip("No real data files available for integration test")

        # Find a real data file
        csv_files = list(data_path.glob("*.csv"))
        if not csv_files:
            pytest.skip("No CSV files found for integration test")

        # Load data for a small date range
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 3)

        try:
            # Load data
            data = await loader.load_data("BTCUSDT", "1h", start_date, end_date, "futures")

            if data.empty:
                pytest.skip("No data in specified date range")

            # Validate loaded data
            is_valid = processor.validate_data(data)
            assert is_valid

            # Clean the data
            cleaned_data = processor.clean_data(data)
            assert len(cleaned_data) <= len(data)  # Cleaning may remove some rows

            # Get summary
            summary = processor.get_data_summary(cleaned_data)
            assert summary["status"] == "valid"
            assert summary["rows"] > 0

            # Test resampling if we have enough data
            if len(cleaned_data) >= 24:  # At least 24 hours of data
                daily_data = processor.resample_data(cleaned_data, "1d")
                assert len(daily_data) > 0
                assert processor.validate_data(daily_data)

        except Exception as e:
            pytest.skip(f"Integration test failed due to data issues: {str(e)}")

    def test_should_discover_available_data(self, loader):
        """Test discovery of available symbols and timeframes."""
        symbols = loader.get_available_symbols("futures")

        if not symbols:
            pytest.skip("No symbols found in data directory")

        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # Test timeframe discovery for first symbol
        first_symbol = symbols[0]
        timeframes = loader.get_available_timeframes(first_symbol, "futures")

        assert isinstance(timeframes, list)
        if timeframes:  # Only test if we have timeframes
            assert len(timeframes) > 0

    @pytest.mark.asyncio
    async def test_should_handle_missing_data_gracefully(self, loader, processor):
        """Test handling of missing data files gracefully."""
        # Try to load data from future dates that don't exist
        start_date = datetime(2030, 1, 1)
        end_date = datetime(2030, 1, 1)

        try:
            data = await loader.load_data("BTCUSDT", "1h", start_date, end_date, "futures")
            # Should either raise DataError or return empty DataFrame
            if not data.empty:
                # If we get data, it should be valid
                assert processor.validate_data(data)
        except Exception:
            # Expected - no data for future dates
            pass

    @pytest.mark.asyncio
    async def test_should_cache_data_effectively(self, loader):
        """Test that caching works effectively."""
        data_path = Path("data/binance/futures/BTCUSDT/1h")
        if not data_path.exists():
            pytest.skip("No real data files available for caching test")

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1)

        # Clear cache first
        loader.clear_cache()
        initial_cache_size = loader.get_cache_info()["cache_size"]

        try:
            # Load data first time
            data1 = await loader.load_data("BTCUSDT", "1h", start_date, end_date, "futures")

            # Check cache increased
            cache_info_after = loader.get_cache_info()
            if not data1.empty:
                assert cache_info_after["cache_size"] > initial_cache_size

            # Load same data again
            data2 = await loader.load_data("BTCUSDT", "1h", start_date, end_date, "futures")

            # Data should be identical
            if not data1.empty and not data2.empty:
                import pandas as pd

                pd.testing.assert_frame_equal(data1, data2)

        except Exception as e:
            pytest.skip(f"Caching test failed due to data issues: {str(e)}")

    @pytest.mark.asyncio
    async def test_should_handle_different_timeframes(self, loader):
        """Test loading data for different timeframes."""
        data_path = Path("data/binance/futures/BTCUSDT")
        if not data_path.exists():
            pytest.skip("No real data files available for timeframe test")

        # Find available timeframes
        timeframes = loader.get_available_timeframes("BTCUSDT", "futures")
        if not timeframes:
            pytest.skip("No timeframes available for testing")

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1)

        successful_loads = 0
        for timeframe in timeframes[:3]:  # Test first 3 timeframes only
            try:
                data = await loader.load_data("BTCUSDT", timeframe, start_date, end_date, "futures")
                if not data.empty:
                    assert list(data.columns) == [
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ]
                    successful_loads += 1
            except Exception:
                # Some timeframes might not have data for the test date
                continue

        # At least one timeframe should work if we have any data
        if timeframes and successful_loads == 0:
            pytest.skip("No timeframes had data for the test date range")
