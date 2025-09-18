"""
Data Loading Strategies using Strategy Pattern.

This module implements different strategies for loading OHLCV data from CSV files,
providing flexibility and extensibility for various loading scenarios.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import DataError

from .csv_utils import CSVUtils

if TYPE_CHECKING:
    from .csv_cache import CSVCache


class DataLoadingStrategy(ABC):
    """Abstract base class for data loading strategies."""

    @abstractmethod
    async def load_data(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        cache_manager: "CSVCache",
        symbol: str = "",
        timeframe: str = "",
    ) -> pd.DataFrame:
        """Load data using the specific strategy."""


class StandardLoadingStrategy(DataLoadingStrategy):
    """
    Standard in-memory loading strategy for smaller datasets.

    This strategy loads all files into memory simultaneously and is optimal
    for datasets with a reasonable number of files (typically < 30).
    """

    async def load_data(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        cache_manager: "CSVCache",
        symbol: str = "",
        timeframe: str = "",
    ) -> pd.DataFrame:
        """Load data using standard in-memory processing."""
        dataframes = []
        missing_files = []

        logger.debug(f"Using standard loading strategy for {len(file_paths)} files")

        for file_path in file_paths:
            try:
                df = await cache_manager.load_single_file(file_path)
                if not df.empty:
                    dataframes.append(df)
            except FileNotFoundError:
                missing_files.append(file_path)
                logger.warning(f"Missing data file: {file_path}")

        if not dataframes:
            raise DataError(f"No valid data files found for {symbol} {timeframe}")

        # Concatenate and filter by date range
        combined_df = pd.concat(dataframes, ignore_index=True)
        combined_df = CSVUtils.filter_by_date_range(combined_df, start_date, end_date)

        logger.info(
            f"Standard loading: {len(combined_df)} rows from {len(dataframes)} files ({len(missing_files)} missing)"
        )

        return combined_df


class ChunkedLoadingStrategy(DataLoadingStrategy):
    """
    Memory-efficient chunked loading strategy for large datasets.

    This strategy processes files in chunks to optimize memory usage
    and is ideal for large datasets (typically >= 30 files).
    """

    def __init__(self, chunk_size: int = 10):
        """Initialize chunked strategy with configurable chunk size."""
        self.chunk_size = chunk_size

    async def load_data(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        cache_manager: "CSVCache",
        symbol: str = "",  # noqa: ARG002
        timeframe: str = "",  # noqa: ARG002
    ) -> pd.DataFrame:
        """Load data using memory-efficient chunked processing."""
        all_data = []
        missing_count = 0

        logger.info(f"Using chunked loading strategy for {len(file_paths)} files")

        # Process files in chunks
        for i in range(0, len(file_paths), self.chunk_size):
            chunk_paths = file_paths[i : i + self.chunk_size]
            chunk_data, chunk_missing = await self._process_chunk_files(
                chunk_paths, start_date, end_date, cache_manager
            )

            if chunk_data is not None:
                all_data.append(chunk_data)
            missing_count += chunk_missing

            # Log chunk progress
            total_chunks = (len(file_paths) + self.chunk_size - 1) // self.chunk_size
            logger.debug(f"Processed chunk {i // self.chunk_size + 1}/{total_chunks}")

        return self._finalize_chunked_data(all_data, file_paths, missing_count)

    async def _process_chunk_files(
        self,
        chunk_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        cache_manager: "CSVCache",
    ) -> tuple[pd.DataFrame | None, int]:
        """Process files in a single chunk and return concatenated data."""
        chunk_dataframes = []
        missing_count = 0

        for file_path in chunk_paths:
            try:
                df = await cache_manager.load_single_file(file_path)
                if not df.empty:
                    # Filter data immediately to reduce memory usage
                    df = CSVUtils.filter_by_date_range(df, start_date, end_date)
                    if not df.empty:
                        chunk_dataframes.append(df)
            except FileNotFoundError:
                missing_count += 1
                logger.warning(f"Missing data file: {file_path}")

        # Concatenate chunk files if any data found
        chunk_data = None
        if chunk_dataframes:
            chunk_data = pd.concat(chunk_dataframes, ignore_index=True)

        return chunk_data, missing_count

    def _finalize_chunked_data(
        self, all_data: list[pd.DataFrame], file_paths: list[Path], missing_count: int
    ) -> pd.DataFrame:
        """Finalize chunked data processing with concatenation and cleanup."""
        if not all_data:
            raise DataError("No valid data found in any chunks")

        # Final concatenation of all chunks
        combined_df = pd.concat(all_data, ignore_index=True)

        # Sort by timestamp and remove duplicates
        combined_df = combined_df.sort_values("timestamp").drop_duplicates(
            subset=["timestamp"], keep="first"
        )

        logger.info(
            f"Chunked loading complete: {len(combined_df)} rows from {len(file_paths)} files ({missing_count} missing)"
        )

        return combined_df


class StreamingLoadingStrategy(DataLoadingStrategy):
    """
    Streaming loading strategy for very large datasets.

    This strategy processes files one at a time in a streaming fashion,
    minimizing memory usage for extremely large datasets.
    """

    async def load_data(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        cache_manager: "CSVCache",
        symbol: str = "",
        timeframe: str = "",
    ) -> pd.DataFrame:
        """Load data using streaming processing."""
        combined_data = []
        missing_count = 0

        logger.info(f"Using streaming loading strategy for {len(file_paths)} files")

        for i, file_path in enumerate(file_paths, 1):
            try:
                df = await cache_manager.load_single_file(file_path)
                if not df.empty:
                    # Filter and process immediately
                    df = CSVUtils.filter_by_date_range(df, start_date, end_date)
                    if not df.empty:
                        combined_data.append(df)

                # Log progress for large datasets
                if i % 50 == 0:
                    logger.debug(f"Streaming progress: {i}/{len(file_paths)} files processed")

            except FileNotFoundError:
                missing_count += 1
                logger.warning(f"Missing data file: {file_path}")

        if not combined_data:
            raise DataError(f"No valid data files found for {symbol} {timeframe}")

        # Final concatenation
        result = pd.concat(combined_data, ignore_index=True)
        result = result.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="first")

        logger.info(
            f"Streaming loading complete: {len(result)} rows from {len(combined_data)} files ({missing_count} missing)"
        )

        return result


class LoadingStrategySelector:
    """
    Strategy selector that chooses the appropriate loading strategy
    based on dataset characteristics and user preferences.
    """

    def __init__(
        self,
        chunk_threshold: int = 30,
        streaming_threshold: int = 100,
        default_chunk_size: int = 10,
    ):
        """
        Initialize strategy selector with configurable thresholds.

        Args:
            chunk_threshold: File count threshold for switching to chunked loading
            streaming_threshold: File count threshold for switching to streaming loading
            default_chunk_size: Default chunk size for chunked loading
        """
        self.chunk_threshold = chunk_threshold
        self.streaming_threshold = streaming_threshold
        self.default_chunk_size = default_chunk_size

        # Available strategies
        self._strategies = {
            "standard": StandardLoadingStrategy(),
            "chunked": ChunkedLoadingStrategy(default_chunk_size),
            "streaming": StreamingLoadingStrategy(),
        }

    def select_strategy(
        self, file_count: int, strategy_hint: str | None = None
    ) -> DataLoadingStrategy:
        """
        Select the most appropriate loading strategy.

        Args:
            file_count: Number of files to load
            strategy_hint: Optional hint for strategy selection ("standard", "chunked", "streaming")

        Returns:
            Selected loading strategy instance
        """
        # Use explicit hint if provided and valid
        if strategy_hint and strategy_hint in self._strategies:
            logger.debug(f"Using explicit strategy hint: {strategy_hint}")
            return self._strategies[strategy_hint]

        # Auto-select based on file count
        if file_count >= self.streaming_threshold:
            logger.debug(f"Auto-selected streaming strategy for {file_count} files")
            return self._strategies["streaming"]
        elif file_count >= self.chunk_threshold:
            logger.debug(f"Auto-selected chunked strategy for {file_count} files")
            return self._strategies["chunked"]
        else:
            logger.debug(f"Auto-selected standard strategy for {file_count} files")
            return self._strategies["standard"]

    def get_available_strategies(self) -> list[str]:
        """Get list of available strategy names."""
        return list(self._strategies.keys())

    def add_custom_strategy(self, name: str, strategy: DataLoadingStrategy) -> None:
        """Add a custom loading strategy."""
        self._strategies[name] = strategy

    def remove_strategy(self, name: str) -> None:
        """Remove a loading strategy."""
        if name in ["standard", "chunked", "streaming"]:
            raise ValueError(f"Cannot remove built-in strategy: {name}")
        self._strategies.pop(name, None)


# Factory function for easy instantiation
def create_loading_strategy_selector(
    chunk_threshold: int = 30, streaming_threshold: int = 100, default_chunk_size: int = 10
) -> LoadingStrategySelector:
    """Factory function to create a loading strategy selector with default configuration."""
    return LoadingStrategySelector(chunk_threshold, streaming_threshold, default_chunk_size)
