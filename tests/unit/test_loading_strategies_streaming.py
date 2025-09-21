"""
Streaming loading strategy tests.

Tests cover StreamingLoadingStrategy functionality including
sequential processing, progress logging, and data handling.
"""

import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pandas as pd
import pytest

from src.infrastructure.data.loading_strategies import StreamingLoadingStrategy

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
            file_index = 0
            # Extract file index from filename (BTCUSDT_1h_2025-01-XX.csv format)
            if "_" in file_path.name:
                try:
                    # Get the date part and extract day number
                    date_part = file_path.name.split("_")[-1].replace(".csv", "")
                    if "-" in date_part:
                        day = int(date_part.split("-")[-1])
                        file_index = day - 1  # Make it 0-based
                except (IndexError, ValueError):
                    file_index = len(self.load_calls) % 5  # Fallback based on call count

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


class TestStreamingLoadingStrategy:
    """Test suite for streaming loading strategy."""

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

    async def test_streaming_strategy_should_process_files_sequentially(
        self,
        mock_cache: MockCSVCache,
        sample_file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Test streaming strategy processes files one by one."""
        strategy = StreamingLoadingStrategy()

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
        assert len(mock_cache.load_calls) == 5
        assert len(result) == 15  # 5 files × 3 rows each

    async def test_streaming_strategy_should_handle_large_file_count(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test streaming strategy with large file count (progress logging)."""
        strategy = StreamingLoadingStrategy()

        # Create 100 file paths to trigger progress logging
        file_paths = [Path(f"file_{i}.csv") for i in range(100)]

        with (
            patch(
                "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
                side_effect=lambda df, *_: df,
            ),
            patch("src.infrastructure.data.loading_strategies.logger") as mock_logger,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        assert not result.empty
        # Should have logged progress at file 50 and 100
        progress_calls = [
            call for call in mock_logger.debug.call_args_list if "progress" in str(call)
        ]
        assert len(progress_calls) >= 2  # At least 2 progress log entries

    async def test_streaming_strategy_should_sort_and_deduplicate(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test streaming strategy sorts by timestamp and removes duplicates."""
        strategy = StreamingLoadingStrategy()

        # Create out-of-order data with duplicates
        df1 = pd.DataFrame(
            {
                "timestamp": [1640998800000, 1640995200000],  # Out of order
                "open": [46500.0, 46000.0],
                "high": [47500.0, 47000.0],
                "low": [46000.0, 45500.0],
                "close": [47000.0, 46500.0],
                "volume": [150.2, 100.5],
            }
        )

        df2 = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1641002400000],  # Duplicate timestamp
                "open": [46000.0, 47000.0],
                "high": [47000.0, 48000.0],
                "low": [45500.0, 46800.0],
                "close": [46500.0, 47800.0],
                "volume": [100.5, 200.1],
            }
        )

        file_paths = [Path("file_1.csv"), Path("file_2.csv")]
        mock_cache.add_file_data(file_paths[0], df1)
        mock_cache.add_file_data(file_paths[1], df2)

        with patch(
            "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
            side_effect=lambda df, *_: df,
        ):
            result = await strategy.load_data(
                file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
            )

        # Should be sorted by timestamp
        assert result["timestamp"].is_monotonic_increasing
        # Should have unique timestamps only
        assert result["timestamp"].nunique() == len(result)
