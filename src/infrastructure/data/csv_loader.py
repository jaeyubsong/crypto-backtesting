"""
CSV Data Loader implementation.

This module provides efficient loading of historical OHLCV data from daily CSV files
with caching, validation, and memory optimization.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import DataError, ValidationError
from src.core.interfaces.data import IDataLoader

from .csv_cache import CSVCache
from .csv_utils import CSVUtils
from .csv_validator import CSVValidator


class CSVDataLoader(IDataLoader):
    """
    CSV-based data loader with caching and performance optimization.

    Features:
    - Efficient loading of daily CSV files
    - LRU caching for frequently accessed data
    - Memory-efficient date range queries
    - Graceful handling of missing files
    - Data validation and integrity checks
    """

    def __init__(self, data_directory: str = "data", cache_size: int = 100):
        """
        Initialize the CSV data loader.

        Args:
            data_directory: Root directory containing market data
            cache_size: Maximum number of cached DataFrames
        """
        self.data_dir = Path(data_directory)
        self.cache_manager = CSVCache(cache_size)
        CSVUtils.validate_data_directory(self.data_dir)

    async def load_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        trading_mode: str = "futures",
    ) -> pd.DataFrame:
        """
        Load OHLCV data for the specified parameters.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Data timeframe (e.g., "1h", "1d")
            start_date: Start date for data range
            end_date: End date for data range
            trading_mode: Trading mode ("spot" or "futures")

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            ValidationError: If parameters are invalid
            DataError: If data cannot be loaded
        """
        try:
            # Validate and sanitize input parameters
            safe_params = self._validate_and_sanitize_params(
                symbol, timeframe, start_date, end_date, trading_mode
            )

            # Generate and validate file paths
            file_paths = self._generate_file_paths(*safe_params)
            self._validate_file_paths_exist(file_paths, symbol, timeframe, start_date, end_date)

            # Load data using appropriate strategy
            return await self._execute_loading_strategy(
                file_paths, start_date, end_date, symbol, timeframe
            )

        except Exception as e:
            return self._handle_loading_error(e, symbol, timeframe)

    def _validate_and_sanitize_params(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        trading_mode: str,
    ) -> tuple[str, str, datetime, datetime, str]:
        """Validate and sanitize input parameters."""
        safe_trading_mode = CSVValidator.sanitize_path_component(trading_mode, "trading_mode")
        safe_symbol = CSVValidator.sanitize_path_component(symbol, "symbol")
        safe_timeframe = CSVValidator.sanitize_path_component(timeframe, "timeframe")

        CSVValidator.validate_load_params(
            safe_symbol, safe_timeframe, start_date, end_date, safe_trading_mode
        )

        return safe_symbol, safe_timeframe, start_date, end_date, safe_trading_mode

    def _validate_file_paths_exist(
        self,
        file_paths: list[Path],
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Validate that file paths were generated successfully."""
        if not file_paths:
            raise DataError(
                f"No data files found for {symbol} {timeframe} from {start_date.date()} to {end_date.date()}"
            )

    async def _execute_loading_strategy(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        symbol: str = "",
        timeframe: str = "",
    ) -> pd.DataFrame:
        """Execute appropriate loading strategy based on dataset size."""
        chunk_threshold = 30

        if len(file_paths) > chunk_threshold:
            return await self._load_chunked_dataset(file_paths, start_date, end_date)
        else:
            return await self._load_standard_dataset(
                file_paths, start_date, end_date, symbol, timeframe
            )

    async def _load_chunked_dataset(
        self, file_paths: list[Path], start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Load large datasets using chunked processing."""
        logger.info(f"Using chunked processing for {len(file_paths)} files")
        return await self._load_files_chunked(file_paths, start_date, end_date, chunk_size=10)

    async def _load_standard_dataset(
        self,
        file_paths: list[Path],
        start_date: datetime,
        end_date: datetime,
        symbol: str = "",
        timeframe: str = "",
    ) -> pd.DataFrame:
        """Load smaller datasets using standard in-memory processing."""
        dataframes = []
        missing_files = []

        for file_path in file_paths:
            try:
                df = await self.cache_manager.load_single_file(file_path)
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
            f"Loaded {len(combined_df)} rows from {len(dataframes)} files ({len(missing_files)} missing)"
        )

        return combined_df

    def _handle_loading_error(self, error: Exception, symbol: str, timeframe: str) -> pd.DataFrame:
        """Handle loading errors with proper exception chaining."""
        if isinstance(error, DataError | ValidationError):
            raise

        logger.error(f"Data loading failed for {symbol} {timeframe}", exc_info=True)
        raise DataError(f"Failed to load data for {symbol} {timeframe}") from error

    def _generate_file_paths(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        trading_mode: str,
    ) -> list[Path]:
        """Generate list of file paths for the specified date range."""
        # Assume parameters are already sanitized by caller
        file_paths = []

        # Base directory path
        base_dir = self.data_dir / "binance" / trading_mode / symbol / timeframe

        # Validate the constructed path is within data directory
        CSVValidator.validate_path_safety(base_dir, self.data_dir)

        # Generate daily file paths
        current_date = start_date.date()
        end_date_date = end_date.date()

        while current_date <= end_date_date:
            file_name = f"{symbol}_{timeframe}_{current_date.strftime('%Y-%m-%d')}.csv"
            file_path = base_dir / file_name
            file_paths.append(file_path)
            current_date += timedelta(days=1)

        return file_paths

    async def _load_files_chunked(
        self, file_paths: list[Path], start_date: datetime, end_date: datetime, chunk_size: int = 10
    ) -> pd.DataFrame:
        """Load files in chunks to optimize memory usage for large datasets."""
        all_data = []
        missing_count = 0

        # Process files in chunks
        for i in range(0, len(file_paths), chunk_size):
            chunk_paths = file_paths[i : i + chunk_size]
            chunk_data, chunk_missing = await self._process_chunk_files(
                chunk_paths, start_date, end_date
            )

            if chunk_data is not None:
                all_data.append(chunk_data)
            missing_count += chunk_missing

            # Log chunk progress
            total_chunks = (len(file_paths) + chunk_size - 1) // chunk_size
            logger.debug(f"Processed chunk {i // chunk_size + 1}/{total_chunks}")

        return self._finalize_chunked_data(all_data, file_paths, missing_count)

    async def _process_chunk_files(
        self, chunk_paths: list[Path], start_date: datetime, end_date: datetime
    ) -> tuple[pd.DataFrame | None, int]:
        """Process files in a single chunk and return concatenated data."""
        chunk_dataframes = []
        missing_count = 0

        for file_path in chunk_paths:
            try:
                df = await self.cache_manager.load_single_file(file_path)
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

    def get_available_symbols(self, trading_mode: str = "futures") -> list[str]:
        """Get list of available symbols."""
        return CSVUtils.get_available_symbols(self.data_dir, trading_mode)

    def get_available_timeframes(self, symbol: str, trading_mode: str = "futures") -> list[str]:
        """Get list of available timeframes for a symbol."""
        return CSVUtils.get_available_timeframes(self.data_dir, symbol, trading_mode)

    def clear_cache(self) -> None:
        """Clear the data cache (thread-safe)."""
        self.cache_manager.clear_cache()

    def get_cache_info(self) -> dict[str, int]:
        """Get cache statistics (thread-safe)."""
        return self.cache_manager.get_cache_info()

    async def close(self) -> None:
        """Clean up resources and close the data loader."""
        logger.info("Closing CSV data loader")

        # Clear cache to free memory
        self.clear_cache()

        # Log cleanup completion
        logger.info("CSV data loader closed successfully")

    async def __aenter__(self) -> "CSVDataLoader":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Async context manager exit with cleanup."""
        await self.close()
