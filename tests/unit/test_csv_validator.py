"""
Unit tests for CSV Validator.

Tests cover security validation, data structure validation, and path safety
for the CSVValidator class.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError, ValidationError
from src.infrastructure.data.csv_validator import CSVValidator


class TestCSVValidator:
    """Test suite for CSVValidator."""

    # Path Component Sanitization Tests
    def test_should_sanitize_valid_path_components(self) -> None:
        """Test sanitization of valid path components."""
        assert CSVValidator.sanitize_path_component("BTCUSDT", "symbol") == "BTCUSDT"
        assert CSVValidator.sanitize_path_component("1h", "timeframe") == "1h"
        assert CSVValidator.sanitize_path_component("futures", "trading_mode") == "futures"

    def test_should_reject_path_traversal_attempts(self) -> None:
        """Test rejection of path traversal attempts."""
        with pytest.raises(ValidationError, match="Invalid symbol: contains path traversal"):
            CSVValidator.sanitize_path_component("../../../etc/passwd", "symbol")

        with pytest.raises(ValidationError, match="Invalid timeframe: contains path traversal"):
            CSVValidator.sanitize_path_component("..\\windows\\system32", "timeframe")

        with pytest.raises(ValidationError, match="Invalid trading_mode: contains path traversal"):
            CSVValidator.sanitize_path_component("./../../secret", "trading_mode")

    def test_should_reject_absolute_paths(self) -> None:
        """Test rejection of absolute paths."""
        with pytest.raises(
            ValidationError, match="Invalid symbol: contains path traversal characters"
        ):
            CSVValidator.sanitize_path_component("/etc/passwd", "symbol")

        with pytest.raises(
            ValidationError, match="Invalid timeframe: contains path traversal characters"
        ):
            CSVValidator.sanitize_path_component("C:\\Windows\\System32", "timeframe")

    def test_should_reject_empty_components(self) -> None:
        """Test rejection of empty path components."""
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            CSVValidator.sanitize_path_component("", "symbol")

        with pytest.raises(ValidationError, match="Invalid timeframe.*contains invalid characters"):
            CSVValidator.sanitize_path_component("   ", "timeframe")

    def test_should_reject_oversized_components(self) -> None:
        """Test rejection of oversized path components."""
        long_name = "A" * 256  # Exceeds typical filesystem limits

        with pytest.raises(ValidationError, match="Symbol too long: maximum 50 characters"):
            CSVValidator.sanitize_path_component(long_name, "symbol")

    def test_should_reject_invalid_characters(self) -> None:
        """Test rejection of invalid characters in path components."""
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "\x00"]

        for char in invalid_chars:
            with pytest.raises(
                ValidationError, match="Invalid symbol.*contains invalid characters"
            ):
                CSVValidator.sanitize_path_component(f"BTC{char}USDT", "symbol")

        # Test newline/carriage return separately since they may be handled differently
        for char in ["\n", "\r"]:
            with pytest.raises(ValidationError):
                CSVValidator.sanitize_path_component(f"BTC{char}USDT", "symbol")

    def test_should_allow_valid_crypto_symbols(self) -> None:
        """Test validation of valid cryptocurrency symbols."""
        valid_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "ADAUSDT",
            "DOTUSDT",
            "LINKUSDT",
            "BTC-USDT",
            "ETH_USDT",
            "1INCHUSDT",
            "AVAX-EUR",
        ]

        for symbol in valid_symbols:
            # Should not raise exception
            result = CSVValidator.sanitize_path_component(symbol, "symbol")
            assert result == symbol

    # Path Safety Validation Tests
    def test_should_validate_safe_paths(self) -> None:
        """Test validation of safe paths within data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            safe_path = data_dir / "binance" / "futures" / "BTCUSDT" / "1h"

            # Should not raise exception
            CSVValidator.validate_path_safety(safe_path, data_dir)

    def test_should_reject_paths_outside_data_directory(self) -> None:
        """Test rejection of paths outside data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            unsafe_path = Path("/etc/passwd")

            with pytest.raises(ValidationError, match="Path traversal attempt detected"):
                CSVValidator.validate_path_safety(unsafe_path, data_dir)

    def test_should_reject_relative_path_escapes(self) -> None:
        """Test rejection of relative path escapes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            unsafe_path = data_dir / ".." / ".." / "etc" / "passwd"

            with pytest.raises(ValidationError, match="Path traversal attempt detected"):
                CSVValidator.validate_path_safety(unsafe_path, data_dir)

    # CSV Structure Validation Tests
    def test_should_validate_correct_csv_structure(self) -> None:
        """Test validation of correctly structured CSV data."""
        valid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception
            CSVValidator.validate_csv_structure(valid_df, file_path)

    def test_should_reject_missing_required_columns(self) -> None:
        """Test rejection of CSV with missing required columns."""
        # Missing 'volume' column
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [46000.0],
                "high": [47000.0],
                "low": [45500.0],
                "close": [46500.0],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="missing columns.*volume"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    def test_should_accept_extra_columns(self) -> None:
        """Test that CSV with extra columns is accepted (implementation allows extra columns)."""
        df_with_extra = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [46000.0],
                "high": [47000.0],
                "low": [45500.0],
                "close": [46500.0],
                "volume": [100.5],
                "unexpected_column": ["extra_data"],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception - implementation allows extra columns
            CSVValidator.validate_csv_structure(df_with_extra, file_path)

    def test_should_handle_empty_dataframe(self) -> None:
        """Test handling of empty DataFrame (implementation returns early for empty)."""
        empty_df = pd.DataFrame()

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception - implementation returns early for empty DataFrames
            CSVValidator.validate_csv_structure(empty_df, file_path)

    # Data Type Validation Tests
    def test_should_validate_correct_data_types(self) -> None:
        """Test validation of correct data types."""
        valid_df = pd.DataFrame(
            {
                "timestamp": pd.Series([1640995200000, 1640998800000], dtype="int64"),
                "open": pd.Series([46000.0, 46500.0], dtype="float64"),
                "high": pd.Series([47000.0, 47500.0], dtype="float64"),
                "low": pd.Series([45500.0, 46000.0], dtype="float64"),
                "close": pd.Series([46500.0, 47000.0], dtype="float64"),
                "volume": pd.Series([100.5, 150.2], dtype="float64"),
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception
            CSVValidator.validate_csv_structure(valid_df, file_path)

    def test_should_accept_various_timestamp_types(self) -> None:
        """Test that various timestamp types are accepted (implementation doesn't validate types)."""
        df_with_string_timestamps = pd.DataFrame(
            {
                "timestamp": ["2025-01-01", "2025-01-02"],  # String instead of int64
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception - implementation doesn't validate data types
            CSVValidator.validate_csv_structure(df_with_string_timestamps, file_path)

    def test_should_reject_non_numeric_price_types(self) -> None:
        """Test rejection of non-numeric price types (causes comparison error)."""
        df_with_string_prices = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": ["46000", "46500"],  # String instead of float64
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should raise exception due to string comparison with numbers
            with pytest.raises(DataError):
                CSVValidator.validate_csv_structure(df_with_string_prices, file_path)

    # Data Value Validation Tests
    def test_should_validate_positive_prices_and_volume(self) -> None:
        """Test validation of positive prices and volume."""
        valid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception
            CSVValidator.validate_csv_structure(valid_df, file_path)

    def test_should_reject_negative_prices(self) -> None:
        """Test rejection of negative prices."""
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [-46000.0, 46500.0],  # Negative price
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="non-positive values"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    def test_should_reject_negative_volume(self) -> None:
        """Test rejection of negative volume."""
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [-100.5, 150.2],  # Negative volume
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="negative volume values"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    def test_should_reject_zero_prices(self) -> None:
        """Test rejection of zero prices."""
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [0.0, 46500.0],  # Zero price
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="non-positive values"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    # OHLC Relationship Validation Tests
    def test_should_validate_correct_ohlc_relationships(self) -> None:
        """Test validation of correct OHLC relationships."""
        valid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],  # High >= Open, Close, Low
                "low": [45500.0, 46000.0],  # Low <= Open, Close, High
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception
            CSVValidator.validate_csv_structure(valid_df, file_path)

    def test_should_reject_invalid_ohlc_high_relationships(self) -> None:
        """Test rejection of invalid OHLC relationships where high is too low."""
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [45000.0, 47500.0],  # High < Open (invalid)
                "low": [44000.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="Invalid OHLC relationships"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    def test_should_reject_invalid_ohlc_low_relationships(self) -> None:
        """Test rejection of invalid OHLC relationships where low is too high."""
        invalid_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [47500.0, 46000.0],  # Low > High (invalid)
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            with pytest.raises(DataError, match="Invalid OHLC relationships"):
                CSVValidator.validate_csv_structure(invalid_df, file_path)

    # Load Parameters Validation Tests
    def test_should_validate_correct_load_parameters(self) -> None:
        """Test validation of correct load parameters."""
        from datetime import datetime

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)

        # Should not raise exception
        CSVValidator.validate_load_params("BTCUSDT", "1h", start_date, end_date, "futures")

    def test_should_reject_invalid_date_range(self) -> None:
        """Test rejection of invalid date range."""
        from datetime import datetime

        start_date = datetime(2025, 1, 31)
        end_date = datetime(2025, 1, 1)  # End before start

        with pytest.raises(ValidationError, match="start_date must be before or equal to end_date"):
            CSVValidator.validate_load_params("BTCUSDT", "1h", start_date, end_date, "futures")

    def test_should_accept_future_dates(self) -> None:
        """Test that future dates are accepted (implementation doesn't validate future dates)."""
        from datetime import datetime, timedelta

        future_date = datetime.now() + timedelta(days=365)
        start_date = datetime(2025, 1, 1)

        # Should not raise exception - implementation doesn't check for future dates
        CSVValidator.validate_load_params("BTCUSDT", "1h", start_date, future_date, "futures")

    def test_should_reject_invalid_timeframes(self) -> None:
        """Test rejection of invalid timeframes."""
        from datetime import datetime

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)

        with pytest.raises(ValidationError, match="Unsupported timeframe"):
            CSVValidator.validate_load_params(
                "BTCUSDT", "invalid_timeframe", start_date, end_date, "futures"
            )

    def test_should_reject_invalid_trading_modes(self) -> None:
        """Test rejection of invalid trading modes."""
        from datetime import datetime

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)

        with pytest.raises(ValidationError, match="Invalid trading mode"):
            CSVValidator.validate_load_params("BTCUSDT", "1h", start_date, end_date, "invalid_mode")

    # NaN and Infinity Validation Tests
    def test_should_accept_nan_values(self) -> None:
        """Test that NaN values are accepted (implementation doesn't validate NaN)."""
        import numpy as np

        df_with_nan = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, np.nan],  # NaN value
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, 150.2],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception - implementation doesn't validate NaN values
            CSVValidator.validate_csv_structure(df_with_nan, file_path)

    def test_should_accept_infinite_values(self) -> None:
        """Test that infinite values are accepted (implementation doesn't validate infinity)."""
        import numpy as np

        df_with_inf = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [46000.0, 46500.0],
                "high": [47000.0, 47500.0],
                "low": [45500.0, 46000.0],
                "close": [46500.0, 47000.0],
                "volume": [100.5, np.inf],  # Infinite value
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception - implementation doesn't validate infinite values
            CSVValidator.validate_csv_structure(df_with_inf, file_path)

    # Edge Cases Tests
    def test_should_handle_single_row_dataframe(self) -> None:
        """Test validation of single-row DataFrame."""
        single_row_df = pd.DataFrame(
            {
                "timestamp": [1640995200000],
                "open": [46000.0],
                "high": [47000.0],
                "low": [45500.0],
                "close": [46500.0],
                "volume": [100.5],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception
            CSVValidator.validate_csv_structure(single_row_df, file_path)

    def test_should_handle_very_large_numbers(self) -> None:
        """Test validation with very large but valid numbers."""
        large_numbers_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000],
                "open": [1e10, 1e10],  # Very large prices
                "high": [1.1e10, 1.1e10],
                "low": [0.9e10, 0.9e10],
                "close": [1.05e10, 1.05e10],
                "volume": [1e6, 1e6],  # Large volume
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv") as temp_file:
            file_path = Path(temp_file.name)
            # Should not raise exception for large but valid numbers
            CSVValidator.validate_csv_structure(large_numbers_df, file_path)
