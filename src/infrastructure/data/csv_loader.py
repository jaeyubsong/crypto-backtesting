"""
CSV Data Loader implementation.

This module provides efficient loading of historical OHLCV data from daily CSV files
with caching, validation, and memory optimization.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from cachetools import LRUCache
from loguru import logger

from src.core.enums.timeframes import Timeframe
from src.core.exceptions.backtest import DataError, ValidationError
from src.core.interfaces.data import IDataLoader


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
        self.cache: LRUCache = LRUCache(maxsize=cache_size)
        self._validate_data_directory()

    def _validate_data_directory(self) -> None:
        """Validate that the data directory exists and has expected structure."""
        if not self.data_dir.exists():
            raise DataError(f"Data directory not found: {self.data_dir}")

        binance_dir = self.data_dir / "binance"
        if not binance_dir.exists():
            raise DataError(f"Binance data directory not found: {binance_dir}")

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
        # Validate inputs
        self._validate_load_params(symbol, timeframe, start_date, end_date, trading_mode)

        try:
            # Generate file paths for date range
            file_paths = self._generate_file_paths(
                symbol, timeframe, start_date, end_date, trading_mode
            )

            if not file_paths:
                raise DataError(
                    f"No data files found for {symbol} {timeframe} from {start_date.date()} to {end_date.date()}"
                )

            # Determine processing strategy based on dataset size
            chunk_threshold = 30  # Process in chunks if more than 30 files
            missing_files = []

            if len(file_paths) > chunk_threshold:
                # Memory-efficient chunked processing for large datasets
                logger.info(f"Using chunked processing for {len(file_paths)} files")
                combined_df = await self._load_files_chunked(
                    file_paths, start_date, end_date, chunk_size=10
                )
            else:
                # Standard in-memory processing for smaller datasets
                dataframes = []

                for file_path in file_paths:
                    try:
                        df = await self._load_single_file(file_path)
                        if not df.empty:
                            dataframes.append(df)
                    except FileNotFoundError:
                        missing_files.append(file_path)
                        logger.warning(f"Missing data file: {file_path}")

                if not dataframes:
                    raise DataError(f"No valid data files found for {symbol} {timeframe}")

                # Concatenate and filter by date range
                combined_df = pd.concat(dataframes, ignore_index=True)
                combined_df = self._filter_by_date_range(combined_df, start_date, end_date)

            # Log statistics
            logger.info(
                f"Loaded {len(combined_df)} rows for {symbol} {timeframe} "
                f"from {len(dataframes)} files ({len(missing_files)} missing)"
            )

            return combined_df

        except Exception as e:
            if isinstance(e, DataError | ValidationError):
                raise
            raise DataError(f"Failed to load data for {symbol} {timeframe}: {str(e)}") from e

    def _validate_load_params(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        trading_mode: str,
    ) -> None:
        """Validate data loading parameters."""
        if not symbol:
            raise ValidationError("Symbol cannot be empty")

        if not timeframe:
            raise ValidationError("Timeframe cannot be empty")

        if start_date > end_date:
            raise ValidationError("start_date must be before or equal to end_date")

        # Validate timeframe is supported
        try:
            Timeframe(timeframe)
        except ValueError as e:
            raise ValidationError(f"Unsupported timeframe: {timeframe}") from e

        if trading_mode not in ["spot", "futures"]:
            raise ValidationError(f"Invalid trading mode: {trading_mode}")

    def _generate_file_paths(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        trading_mode: str,
    ) -> list[Path]:
        """Generate list of file paths for the specified date range."""
        file_paths = []

        # Base directory path
        base_dir = self.data_dir / "binance" / trading_mode / symbol / timeframe

        # Generate daily file paths
        current_date = start_date.date()
        end_date_date = end_date.date()

        while current_date <= end_date_date:
            file_name = f"{symbol}_{timeframe}_{current_date.strftime('%Y-%m-%d')}.csv"
            file_path = base_dir / file_name
            file_paths.append(file_path)
            current_date += timedelta(days=1)

        return file_paths

    async def _load_single_file(self, file_path: Path) -> pd.DataFrame:
        """Load a single CSV file with caching."""
        # Include file modification time in cache key to handle file updates
        if file_path.exists():
            stat = file_path.stat()
            cache_key = f"{file_path}:{stat.st_mtime_ns}"
        else:
            # File doesn't exist, will raise error below
            cache_key = str(file_path)

        # Check cache first
        if cache_key in self.cache:
            logger.debug(f"Cache hit for {file_path}")
            return self.cache[cache_key].copy()

        # Load from disk
        logger.debug(f"Loading file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            # Run file I/O in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: pd.read_csv(
                    file_path,
                    dtype={
                        "timestamp": "int64",
                        "open": "float64",
                        "high": "float64",
                        "low": "float64",
                        "close": "float64",
                        "volume": "float64",
                    },
                ),
            )

            # Basic validation
            self._validate_csv_structure(df, file_path)

            # Cache the result (without datetime column for consistency)
            self.cache[cache_key] = df.copy()

            return df

        except pd.errors.EmptyDataError:
            logger.warning(f"Empty data file: {file_path}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            raise DataError(f"Failed to load CSV file {file_path}: {str(e)}") from e

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

            if chunk_data:
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
                df = await self._load_single_file(file_path)
                if not df.empty:
                    # Filter data immediately to reduce memory usage
                    df = self._filter_by_date_range(df, start_date, end_date)
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

    def _validate_csv_structure(self, df: pd.DataFrame, file_path: Path) -> None:
        """Validate CSV file has expected structure."""
        expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]

        if df.empty:
            return  # Empty files are handled separately

        missing_columns = set(expected_columns) - set(df.columns)
        if missing_columns:
            raise DataError(f"CSV file {file_path} missing columns: {missing_columns}")

        # Validate data types and ranges
        if len(df) > 0:
            # Check for reasonable price ranges
            price_columns = ["open", "high", "low", "close"]
            for col in price_columns:
                if (df[col] <= 0).any():
                    raise DataError(
                        f"Invalid price data in {file_path}: {col} has non-positive values"
                    )

            # Check volume is non-negative
            if (df["volume"] < 0).any():
                raise DataError(f"Invalid volume data in {file_path}: negative volume values")

            # Check OHLC relationships
            if (
                (df["high"] < df["low"])
                | (df["high"] < df["open"])
                | (df["high"] < df["close"])
                | (df["low"] > df["open"])
                | (df["low"] > df["close"])
            ).any():
                raise DataError(f"Invalid OHLC relationships in {file_path}")

    def _filter_by_date_range(
        self, df: pd.DataFrame, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Filter DataFrame to exact date range and sort by timestamp."""
        if df.empty:
            return df

        # Convert to timestamps in milliseconds for direct comparison
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        # Filter by timestamp range directly
        mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
        filtered_df = df[mask].copy()

        # Sort by timestamp and reset index
        filtered_df = filtered_df.sort_values("timestamp").reset_index(drop=True)

        return filtered_df

    def get_available_symbols(self, trading_mode: str = "futures") -> list[str]:
        """Get list of available symbols."""
        binance_dir = self.data_dir / "binance" / trading_mode
        if not binance_dir.exists():
            return []

        symbols = []
        for symbol_dir in binance_dir.iterdir():
            if symbol_dir.is_dir():
                symbols.append(symbol_dir.name)

        return sorted(symbols)

    def get_available_timeframes(self, symbol: str, trading_mode: str = "futures") -> list[str]:
        """Get list of available timeframes for a symbol."""
        symbol_dir = self.data_dir / "binance" / trading_mode / symbol
        if not symbol_dir.exists():
            return []

        timeframes = []
        for tf_dir in symbol_dir.iterdir():
            if tf_dir.is_dir():
                timeframes.append(tf_dir.name)

        return sorted(timeframes)

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self.cache.clear()
        logger.info("Data cache cleared")

    def get_cache_info(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "max_size": int(self.cache.maxsize) if self.cache.maxsize else 0,
            "hits": getattr(self.cache, "hits", 0),
            "misses": getattr(self.cache, "misses", 0),
        }
