"""
Unit tests for OHLCV data processor.

Tests cover data validation, cleaning, resampling, and indicator calculation
for the OHLCVDataProcessor class.
"""

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError, ValidationError
from src.infrastructure.data.processor import OHLCVDataProcessor


class TestOHLCVDataProcessor:
    """Test suite for OHLCVDataProcessor."""

    @pytest.fixture
    def processor(self):
        """Create OHLCVDataProcessor instance."""
        return OHLCVDataProcessor()

    @pytest.fixture
    def valid_data(self):
        """Create valid OHLCV data for testing."""
        timestamps = [1640995200000 + i * 3600000 for i in range(24)]  # 24 hours
        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": [50000 + i * 10 for i in range(24)],
                "high": [50050 + i * 10 for i in range(24)],
                "low": [49950 + i * 10 for i in range(24)],
                "close": [50025 + i * 10 for i in range(24)],
                "volume": [100 + i * 5 for i in range(24)],
            }
        )

    @pytest.fixture
    def invalid_ohlc_data(self):
        """Create data with invalid OHLC relationships."""
        return pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [50000, 51000],
                "high": [49900, 50800],  # High less than open/close (invalid)
                "low": [50100, 51200],  # Low greater than open/close (invalid)
                "close": [50050, 51050],
                "volume": [100, 120],
            }
        )

    def test_should_validate_empty_data(self, processor):
        """Test validation of empty DataFrame."""
        empty_data = pd.DataFrame()
        result = processor.validate_data(empty_data)
        assert result is True

    def test_should_validate_correct_data(self, processor, valid_data):
        """Test validation of correct OHLCV data."""
        result = processor.validate_data(valid_data)
        assert result is True

    def test_should_reject_missing_columns(self, processor):
        """Test validation rejects data with missing columns."""
        incomplete_data = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [50000],
                # Missing high, low, close, volume
            }
        )

        with pytest.raises(ValidationError, match="Missing required columns"):
            processor.validate_data(incomplete_data)

    def test_should_reject_duplicate_timestamps(self, processor):
        """Test validation rejects duplicate timestamps."""
        duplicate_data = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640995200000],  # Duplicate
                "open": [50000, 51000],
                "high": [50100, 51100],
                "low": [49900, 50900],
                "close": [50050, 51050],
                "volume": [100, 120],
            }
        )

        with pytest.raises(ValidationError, match="Duplicate timestamps"):
            processor.validate_data(duplicate_data)

    def test_should_reject_non_positive_prices(self, processor):
        """Test validation rejects non-positive prices."""
        invalid_price_data = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [-50000],  # Negative price
                "high": [0],  # Zero price
                "low": [49900],
                "close": [50050],
                "volume": [100],
            }
        )

        with pytest.raises(ValidationError, match="non-positive values"):
            processor.validate_data(invalid_price_data)

    def test_should_reject_negative_volume(self, processor):
        """Test validation rejects negative volume."""
        negative_volume_data = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50050],
                "volume": [-100],  # Negative volume
            }
        )

        with pytest.raises(ValidationError, match="negative values"):
            processor.validate_data(negative_volume_data)

    def test_should_reject_invalid_ohlc_relationships(self, processor, invalid_ohlc_data):
        """Test validation rejects invalid OHLC relationships."""
        with pytest.raises(ValidationError, match="Invalid OHLC relationships"):
            processor.validate_data(invalid_ohlc_data)

    def test_should_reject_nan_values(self, processor):
        """Test validation rejects NaN values."""
        nan_data = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [np.nan],  # NaN value
                "high": [50100],
                "low": [49900],
                "close": [50050],
                "volume": [100],
            }
        )

        with pytest.raises(ValidationError, match="NaN values"):
            processor.validate_data(nan_data)

    def test_should_clean_empty_data(self, processor):
        """Test cleaning of empty DataFrame."""
        empty_data = pd.DataFrame()
        result = processor.clean_data(empty_data)
        assert result.empty

    def test_should_remove_duplicate_timestamps_in_cleaning(self, processor):
        """Test cleaning removes duplicate timestamps."""
        duplicate_data = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640995200000, 1640998800000],
                "open": [50000, 51000, 52000],
                "high": [50100, 51100, 52100],
                "low": [49900, 50900, 51900],
                "close": [50050, 51050, 52050],
                "volume": [100, 120, 140],
            }
        )

        cleaned = processor.clean_data(duplicate_data)

        assert len(cleaned) == 2  # One duplicate removed
        assert cleaned["timestamp"].duplicated().sum() == 0

    def test_should_sort_by_timestamp_in_cleaning(self, processor):
        """Test cleaning sorts data by timestamp."""
        unsorted_data = pd.DataFrame(
            {
                "timestamp": [1640998800000, 1640995200000, 1641002400000],  # Out of order
                "open": [51000, 50000, 52000],
                "high": [51100, 50100, 52100],
                "low": [50900, 49900, 51900],
                "close": [51050, 50050, 52050],
                "volume": [120, 100, 140],
            }
        )

        cleaned = processor.clean_data(unsorted_data)

        assert cleaned["timestamp"].is_monotonic_increasing
        assert cleaned["timestamp"].iloc[0] == 1640995200000  # First timestamp

    def test_should_fix_ohlc_relationships_in_cleaning(self, processor, invalid_ohlc_data):
        """Test cleaning fixes invalid OHLC relationships."""
        cleaned = processor.clean_data(invalid_ohlc_data)

        # High should be max of OHLC
        for i in range(len(cleaned)):
            row_values = [
                cleaned["open"].iloc[i],
                cleaned["high"].iloc[i],
                cleaned["low"].iloc[i],
                cleaned["close"].iloc[i],
            ]
            assert cleaned["high"].iloc[i] == max(row_values)

        # Low should be min of OHLC
        for i in range(len(cleaned)):
            row_values = [
                cleaned["open"].iloc[i],
                cleaned["high"].iloc[i],
                cleaned["low"].iloc[i],
                cleaned["close"].iloc[i],
            ]
            assert cleaned["low"].iloc[i] == min(row_values)

    def test_should_handle_missing_values_in_cleaning(self, processor):
        """Test cleaning handles missing values."""
        missing_data = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000, 1641002400000],
                "open": [50000, np.nan, 52000],  # Missing middle value
                "high": [50100, 51100, np.nan],  # Missing last value
                "low": [49900, 50900, 51900],
                "close": [50050, 51050, 52050],
                "volume": [100, np.nan, 140],  # Missing volume
            }
        )

        cleaned = processor.clean_data(missing_data)

        # Should have no NaN values in prices
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            assert not cleaned[col].isna().any()

        # Volume NaN should be filled with 0
        assert cleaned["volume"].iloc[1] == 0

    def test_should_resample_empty_data(self, processor):
        """Test resampling of empty DataFrame."""
        empty_data = pd.DataFrame()
        result = processor.resample_data(empty_data, "1d")
        assert result.empty

    def test_should_resample_to_higher_timeframe(self, processor):
        """Test resampling from 1h to 1d timeframe."""
        # Create hourly data for 2 days (48 hours)
        timestamps = [1640995200000 + i * 3600000 for i in range(48)]
        hourly_data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": [50000 + i for i in range(48)],
                "high": [50100 + i for i in range(48)],
                "low": [49900 + i for i in range(48)],
                "close": [50050 + i for i in range(48)],
                "volume": [100 for _ in range(48)],
            }
        )

        resampled = processor.resample_data(hourly_data, "1d")

        assert len(resampled) == 2  # 2 days
        assert list(resampled.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

        # First day checks
        assert resampled["open"].iloc[0] == 50000  # First open of day
        assert resampled["high"].iloc[0] == 50123  # Max high of day
        assert resampled["low"].iloc[0] == 49900  # Min low of day
        assert resampled["close"].iloc[0] == 50073  # Last close of day
        assert resampled["volume"].iloc[0] == 2400  # Sum of volumes (24 * 100)

    def test_should_reject_invalid_timeframe_in_resampling(self, processor, valid_data):
        """Test resampling rejects invalid timeframes."""
        with pytest.raises(ValidationError, match="Unsupported timeframe"):
            processor.resample_data(valid_data, "invalid_timeframe")

    def test_should_calculate_basic_indicators(self, processor):
        """Test calculation of basic technical indicators."""
        # Create enough data for indicators (need at least 50 periods for SMA50)
        timestamps = [1640995200000 + i * 3600000 for i in range(100)]
        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": [50000 + i for i in range(100)],
                "high": [50100 + i for i in range(100)],
                "low": [49900 + i for i in range(100)],
                "close": [50000 + i * 2 for i in range(100)],  # Trending up
                "volume": [100 + i for i in range(100)],
            }
        )

        result = processor.calculate_basic_indicators(data)

        # Check that indicator columns are added
        expected_indicators = [
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "macd",
            "macd_signal",
            "macd_histogram",
            "rsi",
            "bb_upper",
            "bb_lower",
            "bb_middle",
            "vwap",
        ]

        for indicator in expected_indicators:
            assert indicator in result.columns

        # Check SMA20 calculation for last row (should be average of last 20 closes)
        last_20_closes = data["close"].iloc[-20:].mean()
        assert abs(result["sma_20"].iloc[-1] - last_20_closes) < 0.001

        # Check RSI is in valid range [0, 100]
        rsi_values = result["rsi"].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()

    def test_should_handle_insufficient_data_for_indicators(self, processor, valid_data):
        """Test indicator calculation with insufficient data."""
        # Use small dataset (24 rows) - not enough for some indicators
        result = processor.calculate_basic_indicators(valid_data)

        # Should still return DataFrame with indicator columns
        assert "sma_20" in result.columns
        assert "rsi" in result.columns

        # Early values should be NaN due to insufficient history
        assert pd.isna(result["sma_20"].iloc[0])
        assert pd.isna(result["sma_50"].iloc[0])

    def test_should_get_data_summary_for_valid_data(self, processor, valid_data):
        """Test data summary generation for valid data."""
        summary = processor.get_data_summary(valid_data)

        assert summary["status"] == "valid"
        assert summary["rows"] == 24
        assert "start_time" in summary
        assert "end_time" in summary
        assert "price_stats" in summary
        assert "data_quality" in summary

        # Check price stats
        price_stats = summary["price_stats"]
        assert price_stats["min_low"] == 49950
        assert price_stats["max_high"] == 50280  # 50050 + 23 * 10
        assert price_stats["first_open"] == 50000
        assert price_stats["last_close"] == 50255  # 50025 + 23 * 10

        # Check data quality
        data_quality = summary["data_quality"]
        assert data_quality["missing_values"] == 0
        assert data_quality["duplicate_timestamps"] == 0

    def test_should_get_data_summary_for_empty_data(self, processor):
        """Test data summary for empty DataFrame."""
        empty_data = pd.DataFrame()
        summary = processor.get_data_summary(empty_data)

        assert summary["status"] == "empty"
        assert summary["rows"] == 0

    def test_should_handle_data_summary_errors_gracefully(self, processor):
        """Test data summary handles errors gracefully."""
        # Create invalid data that might cause summary calculation errors
        invalid_data = pd.DataFrame({"invalid_column": [1, 2, 3]})

        summary = processor.get_data_summary(invalid_data)

        assert summary["status"] == "error"
        assert "error" in summary
        assert summary["rows"] == 3

    def test_should_calculate_price_change_in_summary(self, processor, valid_data):
        """Test price change calculation in data summary."""
        summary = processor.get_data_summary(valid_data)

        price_stats = summary["price_stats"]
        expected_change = 50255 - 50000  # last_close - first_open
        expected_change_pct = (expected_change / 50000) * 100

        assert abs(price_stats["total_change"] - expected_change) < 0.001
        assert abs(price_stats["total_change_pct"] - expected_change_pct) < 0.001

    def test_should_handle_cleaning_errors_gracefully(self, processor):
        """Test that cleaning handles errors gracefully."""
        # Create problematic data that might cause cleaning to fail
        problematic_data = pd.DataFrame(
            {
                "timestamp": ["invalid", "timestamps"],
                "open": [50000, 51000],
                "high": [50100, 51100],
                "low": [49900, 50900],
                "close": [50050, 51050],
                "volume": [100, 120],
            }
        )

        with pytest.raises(DataError, match="Failed to clean data"):
            processor.clean_data(problematic_data)

    def test_should_handle_resampling_errors_gracefully(self, processor, valid_data):
        """Test that resampling handles errors gracefully."""
        # Try to resample with invalid frequency
        with pytest.raises(ValidationError, match="Unsupported timeframe"):
            processor.resample_data(valid_data, "2h")  # Not in our supported list

    def test_should_maintain_data_types_after_processing(self, processor, valid_data):
        """Test that data types are maintained after processing."""
        cleaned = processor.clean_data(valid_data)

        # Check data types
        assert pd.api.types.is_integer_dtype(cleaned["timestamp"])
        for col in ["open", "high", "low", "close", "volume"]:
            assert pd.api.types.is_numeric_dtype(cleaned[col])

    def test_should_handle_large_dataset_efficiently(self, processor):
        """Test processing efficiency with large datasets."""
        # Create large dataset (10,000 rows)
        n_rows = 10000
        timestamps = [1640995200000 + i * 60000 for i in range(n_rows)]  # 1-minute data
        large_data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": [50000 + np.sin(i / 100) * 100 for i in range(n_rows)],
                "high": [50100 + np.sin(i / 100) * 100 for i in range(n_rows)],
                "low": [49900 + np.sin(i / 100) * 100 for i in range(n_rows)],
                "close": [50050 + np.sin(i / 100) * 100 for i in range(n_rows)],
                "volume": [100 + i % 1000 for i in range(n_rows)],
            }
        )

        import time

        # Test validation performance
        start_time = time.time()
        is_valid = processor.validate_data(large_data)
        validation_time = time.time() - start_time

        assert is_valid
        assert validation_time < 5.0  # Should validate in under 5 seconds

        # Test cleaning performance
        start_time = time.time()
        cleaned = processor.clean_data(large_data)
        cleaning_time = time.time() - start_time

        assert len(cleaned) == n_rows
        assert cleaning_time < 10.0  # Should clean in under 10 seconds
