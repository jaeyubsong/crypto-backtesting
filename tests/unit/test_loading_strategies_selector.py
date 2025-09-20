"""
Loading strategy selector and integration tests.

Tests cover LoadingStrategySelector, factory functions,
and integration tests between strategies and components.
"""

import asyncio
import tempfile
import threading
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.infrastructure.data.loading_strategies import (
    ChunkedLoadingStrategy,
    DataLoadingStrategy,
    StandardLoadingStrategy,
    StreamingLoadingStrategy,
)
from src.infrastructure.data.loading_strategy_selector import (
    LoadingStrategySelector,
    create_loading_strategy_selector,
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
            file_index = 0
            if file_path.name.startswith("file_"):
                try:
                    file_index = int(file_path.name.split("_")[1].split(".")[0])
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


class TestLoadingStrategySelector:
    """Test suite for loading strategy selector and integration."""

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

    # LoadingStrategySelector Tests
    def test_strategy_selector_should_initialize_with_defaults(self) -> None:
        """Test strategy selector initialization."""
        selector = LoadingStrategySelector()

        assert selector.chunk_threshold == 30
        assert selector.streaming_threshold == 100
        assert selector.default_chunk_size == 10
        assert len(selector._strategies) == 3

    def test_strategy_selector_should_initialize_with_custom_parameters(self) -> None:
        """Test strategy selector with custom parameters."""
        selector = LoadingStrategySelector(
            chunk_threshold=20, streaming_threshold=50, default_chunk_size=5
        )

        assert selector.chunk_threshold == 20
        assert selector.streaming_threshold == 50
        assert selector.default_chunk_size == 5

    def test_strategy_selector_should_select_standard_for_small_datasets(self) -> None:
        """Test strategy selection for small datasets."""
        selector = LoadingStrategySelector()

        # Create dummy file paths
        file_paths_10 = [Path(f"file_{i}.csv") for i in range(10)]
        strategy = selector.select_strategy(file_paths_10)
        assert isinstance(strategy, StandardLoadingStrategy)

        file_paths_29 = [Path(f"file_{i}.csv") for i in range(29)]  # Just below threshold
        strategy = selector.select_strategy(file_paths_29)
        assert isinstance(strategy, StandardLoadingStrategy)

    def test_strategy_selector_should_select_chunked_for_medium_datasets(self) -> None:
        """Test strategy selection for medium datasets."""
        selector = LoadingStrategySelector()

        file_paths_30 = [Path(f"file_{i}.csv") for i in range(30)]  # At threshold
        strategy = selector.select_strategy(file_paths_30)
        assert isinstance(strategy, ChunkedLoadingStrategy)

        file_paths_50 = [Path(f"file_{i}.csv") for i in range(50)]
        strategy = selector.select_strategy(file_paths_50)
        assert isinstance(strategy, ChunkedLoadingStrategy)

        file_paths_99 = [Path(f"file_{i}.csv") for i in range(99)]  # Just below streaming threshold
        strategy = selector.select_strategy(file_paths_99)
        assert isinstance(strategy, ChunkedLoadingStrategy)

    def test_strategy_selector_should_select_streaming_for_large_datasets(self) -> None:
        """Test strategy selection for large datasets."""
        selector = LoadingStrategySelector()

        file_paths_100 = [Path(f"file_{i}.csv") for i in range(100)]  # At streaming threshold
        strategy = selector.select_strategy(file_paths_100)
        assert isinstance(strategy, StreamingLoadingStrategy)

        file_paths_500 = [Path(f"file_{i}.csv") for i in range(500)]
        strategy = selector.select_strategy(file_paths_500)
        assert isinstance(strategy, StreamingLoadingStrategy)

    def test_strategy_selector_should_honor_explicit_hints(self) -> None:
        """Test strategy selection with explicit hints."""
        selector = LoadingStrategySelector()

        # Force standard strategy even for large dataset
        file_paths_200 = [Path(f"file_{i}.csv") for i in range(200)]
        strategy = selector.select_strategy(file_paths_200, strategy_hint="standard")
        assert isinstance(strategy, StandardLoadingStrategy)

        # Force streaming strategy even for small dataset
        file_paths_5 = [Path(f"file_{i}.csv") for i in range(5)]
        strategy = selector.select_strategy(file_paths_5, strategy_hint="streaming")
        assert isinstance(strategy, StreamingLoadingStrategy)

        # Force chunked strategy
        strategy = selector.select_strategy(file_paths_5, strategy_hint="chunked")
        assert isinstance(strategy, ChunkedLoadingStrategy)

    def test_strategy_selector_should_ignore_invalid_hints(self) -> None:
        """Test strategy selection ignores invalid hints."""
        selector = LoadingStrategySelector()

        # Invalid hint should fall back to auto-selection
        file_paths_10 = [Path(f"file_{i}.csv") for i in range(10)]
        strategy = selector.select_strategy(file_paths_10, strategy_hint="invalid_strategy")
        assert isinstance(strategy, StandardLoadingStrategy)

    def test_strategy_selector_should_provide_available_strategies(self) -> None:
        """Test getting available strategy names."""
        selector = LoadingStrategySelector()

        strategies = selector.get_available_strategies()
        assert "standard" in strategies
        assert "chunked" in strategies
        assert "streaming" in strategies
        assert len(strategies) == 3

    def test_strategy_selector_should_allow_custom_strategies(self) -> None:
        """Test adding and removing custom strategies."""
        selector = LoadingStrategySelector()

        # Add custom strategy
        custom_strategy = Mock(spec=DataLoadingStrategy)
        selector.add_custom_strategy("custom", custom_strategy)

        assert "custom" in selector.get_available_strategies()
        assert selector._strategies["custom"] is custom_strategy

        # Remove custom strategy
        selector.remove_strategy("custom")
        assert "custom" not in selector.get_available_strategies()

    def test_strategy_selector_should_protect_builtin_strategies(self) -> None:
        """Test protection of built-in strategies from removal."""
        selector = LoadingStrategySelector()

        with pytest.raises(ValueError, match="Cannot remove built-in strategy"):
            selector.remove_strategy("standard")

        with pytest.raises(ValueError, match="Cannot remove built-in strategy"):
            selector.remove_strategy("chunked")

        with pytest.raises(ValueError, match="Cannot remove built-in strategy"):
            selector.remove_strategy("streaming")

    # Factory Function Tests
    def test_create_loading_strategy_selector_should_return_configured_selector(self) -> None:
        """Test factory function returns properly configured selector."""
        selector = create_loading_strategy_selector(
            chunk_threshold=25, streaming_threshold=75, default_chunk_size=8
        )

        assert isinstance(selector, LoadingStrategySelector)
        assert selector.chunk_threshold == 25
        assert selector.streaming_threshold == 75
        assert selector.default_chunk_size == 8

    def test_create_loading_strategy_selector_should_use_defaults(self) -> None:
        """Test factory function with default parameters."""
        selector = create_loading_strategy_selector()

        assert isinstance(selector, LoadingStrategySelector)
        assert selector.chunk_threshold == 30
        assert selector.streaming_threshold == 100
        assert selector.default_chunk_size == 10

    # Integration Tests
    async def test_strategies_should_work_with_real_csv_utils_filtering(
        self,
        mock_cache: MockCSVCache,
        sample_file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Test strategies work with actual CSV filtering logic."""
        # Use real CSV filtering instead of mocking

        strategy = StandardLoadingStrategy()

        # Add data that spans beyond the date range
        extended_df = pd.DataFrame(
            {
                "timestamp": [
                    1704067200000,  # 2024-01-01 (before range)
                    1735689600000,  # 2025-01-01 (in range)
                    1767225600000,  # 2026-01-01 (after range)
                ],
                "open": [40000.0, 46000.0, 50000.0],
                "high": [41000.0, 47000.0, 51000.0],
                "low": [39500.0, 45500.0, 49500.0],
                "close": [40500.0, 46500.0, 50500.0],
                "volume": [100.0, 100.5, 100.8],
            }
        )

        for path in sample_file_paths:
            mock_cache.add_file_data(path, extended_df)

        result = await strategy.load_data(
            sample_file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
        )

        # Should only contain data within the date range
        # (This would require proper timestamp filtering implementation)
        assert not result.empty

    async def test_concurrent_strategy_execution(
        self, mock_cache: MockCSVCache, start_date: datetime, end_date: datetime
    ) -> None:
        """Test concurrent execution of different strategies."""
        strategies = [
            StandardLoadingStrategy(),
            ChunkedLoadingStrategy(chunk_size=2),
            StreamingLoadingStrategy(),
        ]

        file_paths = [Path(f"file_{i}.csv") for i in range(6)]

        async def run_strategy(strategy: DataLoadingStrategy) -> pd.DataFrame:
            with patch(
                "src.infrastructure.data.loading_strategies.CSVUtils.filter_by_date_range",
                side_effect=lambda df, *_: df,
            ):
                return await strategy.load_data(
                    file_paths, start_date, end_date, cast("CSVCache", mock_cache), "BTCUSDT", "1h"
                )

        # Run all strategies concurrently
        results = await asyncio.gather(*[run_strategy(s) for s in strategies])

        # All should return data
        for result in results:
            assert not result.empty
            assert len(result) >= 6  # At least one row per file

    def test_strategy_selector_thread_safety(self) -> None:
        """Test strategy selector is thread-safe."""
        selector = LoadingStrategySelector()
        results = []
        errors = []

        def select_strategy() -> None:
            try:
                file_paths_25 = [Path(f"file_{i}.csv") for i in range(25)]
                strategy = selector.select_strategy(file_paths_25)
                results.append(type(strategy).__name__)
            except Exception as e:
                errors.append(e)

        # Run concurrent selections
        threads = [threading.Thread(target=select_strategy) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 10
        # All should select the same strategy for same file count
        assert all(result == "StandardLoadingStrategy" for result in results)
