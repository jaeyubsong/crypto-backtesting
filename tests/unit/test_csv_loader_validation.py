"""
Validation and security tests for CSV data loader.

Tests cover input validation, CSV structure validation,
security checks, and error handling.
"""

import shutil
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError, ValidationError
from src.infrastructure.data.csv_loader import CSVDataLoader


class TestCSVDataLoaderValidation:
    """Validation and security test suite for CSVDataLoader."""

    @pytest.fixture
    def temp_data_dir(self) -> Generator[Path]:
        """Create temporary data directory."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create basic directory structure
            binance_dir = temp_dir / "binance" / "futures" / "BTCUSDT" / "1h"
            binance_dir.mkdir(parents=True)

            yield temp_dir

        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def loader(self, temp_data_dir: Path) -> CSVDataLoader:
        """Create CSVDataLoader instance with test data directory."""
        return CSVDataLoader(data_directory=str(temp_data_dir), cache_size=10)

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
