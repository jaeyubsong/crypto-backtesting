"""
OHLCV data resampling module.

Provides timeframe resampling capabilities for OHLCV market data.
"""

import pandas as pd
from loguru import logger

from src.core.enums.timeframes import Timeframe
from src.core.exceptions.backtest import DataError, ValidationError

from .ohlcv_validator import OHLCVValidator


class OHLCVResampler:
    """
    OHLCV data resampler with timeframe conversion capabilities.

    Features:
    - Timeframe validation
    - Proper OHLCV aggregation (first, max, min, last, sum)
    - Datetime index handling
    - Result validation
    """

    def __init__(self) -> None:
        self._validator = OHLCVValidator()

    def resample_data(self, data: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe.

        Args:
            data: Source OHLCV DataFrame
            target_timeframe: Target timeframe (e.g., "1h", "1d")

        Returns:
            Resampled DataFrame

        Raises:
            ValidationError: If timeframe is invalid
            DataError: If resampling fails
        """
        if data.empty:
            return data

        # Validate target timeframe
        self._validate_target_timeframe(target_timeframe)

        try:
            # Prepare data for resampling
            df_prepared = self._prepare_resampling_data(data)

            # Perform resampling
            resampled = self._perform_resampling(df_prepared, target_timeframe)

            # Finalize and validate result
            result = self._finalize_resampled_data(resampled)

            logger.info(f"Resampled data: {len(data)} -> {len(result)} rows to {target_timeframe}")
            return result

        except Exception as e:
            raise DataError(f"Failed to resample data to {target_timeframe}: {str(e)}") from e

    def _validate_target_timeframe(self, target_timeframe: str) -> None:
        """Validate the target timeframe for resampling."""
        try:
            Timeframe.from_string(target_timeframe)
        except ValueError as e:
            raise ValidationError(str(e)) from e

    def _prepare_resampling_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for resampling by converting to datetime index."""
        df_prepared = data.copy()
        df_prepared["datetime"] = pd.to_datetime(df_prepared["timestamp"], unit="ms", utc=True)
        return df_prepared.set_index("datetime")

    def _perform_resampling(self, df_indexed: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Perform the actual OHLCV resampling."""
        freq = self._get_pandas_freq(target_timeframe)

        return (
            df_indexed.resample(freq)
            .agg(
                {
                    "timestamp": "first",  # Take first timestamp in period
                    "open": "first",  # First price in period
                    "high": "max",  # Maximum price in period
                    "low": "min",  # Minimum price in period
                    "close": "last",  # Last price in period
                    "volume": "sum",  # Total volume in period
                }
            )
            .dropna()
        )

    def _finalize_resampled_data(self, resampled: pd.DataFrame) -> pd.DataFrame:
        """Finalize resampled data with proper formatting and validation."""
        # Reset index and ensure proper column order
        result = resampled.reset_index(drop=True)
        result = result[["timestamp", "open", "high", "low", "close", "volume"]]

        # Convert timestamp back to milliseconds
        result["timestamp"] = result["timestamp"].astype("int64")

        # Validate resampled data
        self._validator.validate_data(result)

        return result

    def _get_pandas_freq(self, timeframe: str) -> str:
        """Convert trading timeframe to pandas frequency string."""
        freq_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W",
        }

        if timeframe not in freq_map:
            raise ValidationError(f"Unsupported timeframe for resampling: {timeframe}")

        return freq_map[timeframe]
