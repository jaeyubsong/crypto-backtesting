"""
Core loading strategy tests.

Tests cover MockCSVCache helper, StandardLoadingStrategy,
and ChunkedLoadingStrategy functionality.
"""

import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pandas as pd
import pytest

from src.core.exceptions.backtest import DataError
from src.infrastructure.data.loading_strategies import (
    ChunkedLoadingStrategy,
    StandardLoadingStrategy,
)

if TYPE_CHECKING:
    from src.infrastructure.data.csv_cache import CSVCache


class MockCSVCache:
    """Mock CSV cache for testing loading strategies."""

    def __init__(self) -> None:
        self.files: dict[Path, pd.DataFrame] = {}
        self.load_calls: list[Path] = []

    async def load_single_file(self, file_path: Path) -> pd.DataFrame:
        """Mock file loading that tracks calls."""
        self.load_calls.append(file_path)

        if file_path in self.files:
            return self.files[file_path].copy()
        elif file_path.name.startswith("missing_"):
            raise FileNotFoundError(f"File not found: {file_path}")
        else:
            # Return sample data for non-missing files with unique timestamps per file
            # Extract file index from filename to create unique timestamps
            file_index = 0
            if file_path.name.startswith("file_"):
                try:
                    file_index = int(file_path.name.split("_")[1].split(".")[0])
                except (IndexError, ValueError):
                    file_index = 0
            elif "2025-01-" in file_path.name:
                # Handle date-based filenames like BTCUSDT_1h_2025-01-01.csv
                try:
                    date_part = file_path.name.split("_")[-1].replace(".csv", "")  # 2025-01-01
                    day = int(date_part.split("-")[-1])  # Extract day
                    file_index = day - 1  # Convert to 0-based index
                except (IndexError, ValueError):
                    file_index = 0

            # Create unique timestamps for each file to prevent deduplication
            base_timestamp = 1640995200000 + (file_index * 3 * 3600000)  # 3 hours per file offset
            return pd.DataFrame(
                {
                    "timestamp": [base_timestamp + i * 3600000 for i in range(3)],
                    "open": [46000.0 + i * 100 + file_index * 1000 for i in range(3)],
                    "high": [47000.0 + i * 100 + file_index * 1000 for i in range(3)],
                    "low": [45500.0 + i * 100 + file_index * 1000 for i in range(3)],
                    "close": [46500.0 + i * 100 + file_index * 1000 for i in range(3)],
                    "volume": [100.5 + i * 10 + file_index * 50 for i in range(3)],
                }
            )

    def add_file_data(self, file_path: Path, data: pd.DataFrame) -> None:
        """Add mock file data."""
        self.files[file_path] = data


class TestLoadingStrategiesCore:
    """Test suite for core loading strategies."""

    @pytest.fixture
    def temp_directory(self) -> Generator[Path]:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_cache(self) -> MockCSVCache:
        """Create mock CSV cache."""
        return MockCSVCache()

    @pytest.fixture
    def sample_file_paths(self, temp_directory: Path) -> list[Path]:
        """Create sample file paths for testing."""
        paths = []
        for i in range(5):
            date = datetime(2025, 1, 1) + timedelta(days=i)
            path = temp_directory / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"
            paths.append(path)
        return paths

    @pytest.fixture
    def start_date(self) -> datetime:
        """Test start date."""
        return datetime(2025, 1, 1)

    @pytest.fixture
    def end_date(self) -> datetime:
        """Test end date."""
        return datetime(2025, 1, 5)

    # StandardLoadingStrategy Tests
    async def test_standard_strategy_should_load_all_files(
        self,
        mock_cache: MockCSVCache,
        sample_file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Test standard strategy loads all files."""
        strategy = StandardLoadingStrategy()

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                sample_file_paths,
                start_date,
                end_date,
                cast("CSVCache", mock_cache),
                "BTCUSDT",
                "1h",
            )

        assert not result.empty
        assert len(mock_cache.load_calls) == 5  # All files should be loaded
        assert len(result) == 15  # 3 rows per file × 5 files

    async def test_standard_strategy_should_handle_missing_files(
        self,
        mock_cache: MockCSVCache,
        temp_directory: Path,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Test standard strategy handles missing files gracefully."""
        strategy = StandardLoadingStrategy()

        # Mix of existing and missing files
        file_paths = [
            temp_directory / "BTCUSDT_1h_2025-01-01.csv",
            temp_directory / "missing_BTCUSDT_1h_2025-01-02.csv",
            temp_directory / "BTCUSDT_1h_2025-01-03.csv",
        ]

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        assert not result.empty
        assert len(result) == 6  # 2 files × 3 rows each

    async def test_standard_strategy_should_raise_error_when_no_valid_files(
        self,
        mock_cache: MockCSVCache,
        temp_directory: Path,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Test standard strategy raises error when no valid files found."""
        strategy = StandardLoadingStrategy()

        # All missing files
        file_paths = [
            temp_directory / "missing_BTCUSDT_1h_2025-01-01.csv",
            temp_directory / "missing_BTCUSDT_1h_2025-01-02.csv",
        ]

        with pytest.raises(DataError, match="No valid data files found"):
            await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

    # ChunkedLoadingStrategy Tests
    async def test_chunked_strategy_should_process_in_chunks(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test chunked strategy processes files in chunks."""
        strategy = ChunkedLoadingStrategy(chunk_size=2)

        # Create 5 file paths
        file_paths = [Path(f"file_{i}.csv") for i in range(5)]

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        assert not result.empty
        assert len(mock_cache.load_calls) == 5
        assert len(result) == 15  # 5 files × 3 rows each

    async def test_chunked_strategy_should_handle_mixed_success_failure(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test chunked strategy handles mix of successful and failed loads."""
        strategy = ChunkedLoadingStrategy(chunk_size=2)

        file_paths = [
            Path("file_1.csv"),
            Path("missing_file_2.csv"),  # This will fail
            Path("file_3.csv"),
            Path("missing_file_4.csv"),  # This will fail
            Path("file_5.csv"),
        ]

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        assert not result.empty
        assert len(result) == 9  # 3 successful files × 3 rows each

    async def test_chunked_strategy_should_remove_duplicates(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test chunked strategy removes duplicate timestamps."""
        strategy = ChunkedLoadingStrategy(chunk_size=2)

        # Create duplicate data
        duplicate_df = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640995200000, 1640998800000],  # Duplicate timestamp
                "open": [46000.0, 46000.0, 46500.0],
                "high": [47000.0, 47000.0, 47500.0],
                "low": [45500.0, 45500.0, 46000.0],
                "close": [46500.0, 46500.0, 47000.0],
                "volume": [100.5, 100.5, 150.2],
            }
        )

        file_paths = [Path("file_1.csv"), Path("file_2.csv")]
        mock_cache.add_file_data(file_paths[0], duplicate_df)
        mock_cache.add_file_data(file_paths[1], duplicate_df)

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        # Should have only unique timestamps
        assert result["timestamp"].nunique() == 2  # Only 2 unique timestamps

    async def test_chunked_strategy_should_raise_error_when_no_data(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test chunked strategy raises error when no data found."""
        strategy = ChunkedLoadingStrategy(chunk_size=2)

        file_paths = [Path("missing_file_1.csv"), Path("missing_file_2.csv")]

        with pytest.raises(DataError, match="No valid data found in any chunks"):
            await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )
