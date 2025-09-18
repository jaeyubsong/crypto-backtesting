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
from .loading_strategies import create_loading_strategy_selector


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

    # Configuration constants
    DEFAULT_CACHE_SIZE = 100
    CHUNK_THRESHOLD = 30  # Process in chunks if more than 30 files
    DEFAULT_CHUNK_SIZE = 10

    def __init__(
        self,
        data_directory: str = "data",
        cache_size: int = DEFAULT_CACHE_SIZE,
        strategy_hint: str | None = None,
    ):
        """
        Initialize the CSV data loader.

        Args:
            data_directory: Root directory containing market data
            cache_size: Maximum number of cached DataFrames
            strategy_hint: Optional loading strategy hint ("standard", "chunked", "streaming")
        """
        self.data_dir = Path(data_directory)
        self.cache_manager = CSVCache(cache_size)
        self.strategy_selector = create_loading_strategy_selector(
            chunk_threshold=self.CHUNK_THRESHOLD, default_chunk_size=self.DEFAULT_CHUNK_SIZE
        )
        self.strategy_hint = strategy_hint
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

        except (ValidationError, DataError):
            raise
        except FileNotFoundError as e:
            logger.error(f"Required data files not found for {symbol} {timeframe}")
            raise DataError(f"No data files found for {symbol} {timeframe}") from e
        except PermissionError as e:
            logger.error(f"Permission denied accessing data for {symbol} {timeframe}")
            raise DataError(f"Permission denied accessing data for {symbol} {timeframe}") from e
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
        """Execute appropriate loading strategy using Strategy Pattern."""
        strategy = self.strategy_selector.select_strategy(len(file_paths), self.strategy_hint)
        return await strategy.load_data(
            file_paths, start_date, end_date, self.cache_manager, symbol, timeframe
        )

    def set_strategy_hint(self, strategy_hint: str | None) -> None:
        """Set the loading strategy hint for future operations."""
        self.strategy_hint = strategy_hint

    def get_available_strategies(self) -> list[str]:
        """Get list of available loading strategies."""
        return self.strategy_selector.get_available_strategies()

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

    def get_available_symbols(self, trading_mode: str = "futures") -> list[str]:
        """Get list of available symbols."""
        return CSVUtils.get_available_symbols(self.data_dir, trading_mode)

    def get_available_timeframes(self, symbol: str, trading_mode: str = "futures") -> list[str]:
        """Get list of available timeframes for a symbol."""
        return CSVUtils.get_available_timeframes(self.data_dir, symbol, trading_mode)

    def clear_cache(self) -> None:
        """Clear the data cache (thread-safe)."""
        self.cache_manager.clear_cache()

    def get_cache_info(self) -> dict[str, int | float]:
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
