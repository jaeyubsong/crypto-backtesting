"""
Data processor implementation for OHLCV data manipulation.

This module provides data validation, cleaning, and resampling capabilities
for historical market data.
"""

from typing import Any

import pandas as pd
from loguru import logger

from src.core.enums.timeframes import Timeframe
from src.core.exceptions.backtest import DataError, ValidationError
from src.core.interfaces.data import IDataProcessor

from .technical_indicators import create_technical_indicators_calculator


class OHLCVDataProcessor(IDataProcessor):
    """
    OHLCV data processor with validation, cleaning, and resampling capabilities.

    Features:
    - Comprehensive data validation
    - Missing data detection and handling
    - OHLCV relationship validation
    - Timeframe resampling with proper aggregation
    - Data cleaning and normalization
    """

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate OHLCV data integrity.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            True if data is valid

        Raises:
            ValidationError: If data has integrity issues
        """
        if data.empty:
            return True  # Empty data is valid

        # Perform comprehensive validation checks
        self._validate_data_structure(data)
        self._validate_data_types(data)
        self._validate_data_values(data)
        self._validate_ohlc_relationships(data)
        self._validate_data_quality(data)

        return True

    def _validate_data_structure(self, data: pd.DataFrame) -> None:
        """Validate basic data structure requirements."""
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")

        # Check for duplicate timestamps
        if data["timestamp"].duplicated().any():
            raise ValidationError("Duplicate timestamps found in data")

    def _validate_data_types(self, data: pd.DataFrame) -> None:
        """Validate data types for numeric columns."""
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise ValidationError(f"Column {col} must be numeric")

        # Check for NaN values in all required columns
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in required_columns:
            if data[col].isna().any():
                raise ValidationError(f"Column {col} contains NaN values")

    def _validate_data_values(self, data: pd.DataFrame) -> None:
        """Validate value ranges for prices and volume."""
        # Validate price ranges
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            if (data[col] <= 0).any():
                raise ValidationError(f"Column {col} contains non-positive values")

        # Validate volume
        if (data["volume"] < 0).any():
            raise ValidationError("Volume column contains negative values")

    def _validate_ohlc_relationships(self, data: pd.DataFrame) -> None:
        """Validate OHLC price relationships."""
        invalid_ohlc = (
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
        )

        if invalid_ohlc.any():
            invalid_count = invalid_ohlc.sum()
            raise ValidationError(f"Invalid OHLC relationships found in {invalid_count} rows")

    def _validate_data_quality(self, data: pd.DataFrame) -> None:
        """Validate data quality and provide warnings for anomalies."""
        # Check for reasonable price variations
        daily_range = (data["high"] - data["low"]) / data["low"]
        extreme_moves = daily_range > 0.5  # More than 50% daily range

        if extreme_moves.any():
            extreme_count = extreme_moves.sum()
            logger.warning(f"Found {extreme_count} periods with extreme price movements (>50%)")

        # Validate timestamp ordering
        if not data["timestamp"].is_monotonic_increasing:
            logger.warning("Timestamps are not in ascending order")

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize OHLCV data.

        Args:
            data: Raw OHLCV DataFrame

        Returns:
            Cleaned DataFrame

        Raises:
            DataError: If data cannot be cleaned
        """
        if data.empty:
            return data

        try:
            cleaned_data = data.copy()

            # Perform data cleaning steps
            cleaned_data = self._validate_and_prepare_timestamps(cleaned_data)
            cleaned_data = self._remove_duplicates_and_sort(cleaned_data)
            cleaned_data = self._clean_data_values(cleaned_data)
            cleaned_data = self._normalize_precision(cleaned_data)

            # Final validation
            self.validate_data(cleaned_data)
            logger.info(f"Cleaned data: {len(data)} -> {len(cleaned_data)} rows")

            return cleaned_data

        except Exception as e:
            raise DataError(f"Failed to clean data: {str(e)}") from e

    def _validate_and_prepare_timestamps(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate and prepare timestamp data for processing."""
        if not pd.api.types.is_numeric_dtype(data["timestamp"]):
            raise DataError("Timestamp column must be numeric (milliseconds since epoch)")
        return data

    def _remove_duplicates_and_sort(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate timestamps and sort data chronologically."""
        # Remove duplicate timestamps (keep first occurrence)
        duplicate_mask = data["timestamp"].duplicated(keep="first")
        if duplicate_mask.any():
            duplicate_count = duplicate_mask.sum()
            logger.warning(f"Removing {duplicate_count} duplicate timestamps")
            data = data[~duplicate_mask]

        # Sort by timestamp
        return data.sort_values("timestamp").reset_index(drop=True)

    def _clean_data_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and fix data values including missing values and OHLC relationships."""
        # Handle missing values
        data = self._handle_missing_values(data)

        # Fix invalid OHLC relationships
        data = self._fix_ohlc_relationships(data)

        # Ensure volume is non-negative
        data["volume"] = data["volume"].clip(lower=0)

        return data

    def _normalize_precision(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize numerical precision for prices and volume."""
        # Round prices to reasonable precision
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            data[col] = data[col].round(8)

        # Round volume to reasonable precision
        data["volume"] = data["volume"].round(8)

        return data

    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in OHLCV data."""
        if data.empty:
            return data

        # Check for missing values
        price_columns = ["open", "high", "low", "close"]
        missing_prices = data[price_columns].isna()

        if missing_prices.any().any():
            logger.warning("Found missing price values, using forward fill")
            # Forward fill missing prices
            data[price_columns] = data[price_columns].ffill()

            # If still missing (at beginning), use backward fill
            data[price_columns] = data[price_columns].bfill()

        # Handle missing volume
        if data["volume"].isna().any():
            logger.warning("Found missing volume values, filling with 0")
            data["volume"] = data["volume"].fillna(0)

        return data

    def _fix_ohlc_relationships(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fix invalid OHLC relationships."""
        if data.empty:
            return data

        # Ensure high is the maximum of OHLC
        data["high"] = data[["open", "high", "low", "close"]].max(axis=1)

        # Ensure low is the minimum of OHLC
        data["low"] = data[["open", "high", "low", "close"]].min(axis=1)

        return data

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
        self.validate_data(result)

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

    def calculate_basic_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate basic technical indicators using Strategy Pattern.

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with additional indicator columns
        """
        calculator = create_technical_indicators_calculator()
        return calculator.calculate_all_indicators(data)

    def get_data_summary(self, data: pd.DataFrame) -> dict[str, Any]:
        """
        Get summary statistics for OHLCV data.

        Args:
            data: OHLCV DataFrame

        Returns:
            Dictionary with summary statistics
        """
        if data.empty:
            return {"status": "empty", "rows": 0}

        try:
            summary = {
                "status": "valid",
                "rows": len(data),
            }

            # Add time information
            summary.update(self._get_time_statistics(data))

            # Add price statistics
            summary["price_stats"] = self._get_price_statistics(data)

            # Add data quality metrics
            summary["data_quality"] = self._get_data_quality_metrics(data)

            return summary

        except Exception as e:
            return {"status": "error", "error": str(e), "rows": len(data)}

    def _get_time_statistics(self, data: pd.DataFrame) -> dict[str, str]:
        """Extract time-related statistics from data."""
        return {
            "start_time": pd.to_datetime(
                data["timestamp"].iloc[0], unit="ms", utc=True
            ).isoformat(),
            "end_time": pd.to_datetime(data["timestamp"].iloc[-1], unit="ms", utc=True).isoformat(),
        }

    def _get_price_statistics(self, data: pd.DataFrame) -> dict[str, float]:
        """Calculate comprehensive price statistics."""
        price_stats = {
            "min_low": float(data["low"].min()),
            "max_high": float(data["high"].max()),
            "first_open": float(data["open"].iloc[0]),
            "last_close": float(data["close"].iloc[-1]),
            "total_volume": float(data["volume"].sum()),
            "avg_volume": float(data["volume"].mean()),
        }

        # Add price change calculations
        if len(data) > 0:
            price_change = data["close"].iloc[-1] - data["open"].iloc[0]
            price_change_pct = (price_change / data["open"].iloc[0]) * 100
            price_stats["total_change"] = float(price_change)
            price_stats["total_change_pct"] = float(price_change_pct)

        return price_stats

    def _get_data_quality_metrics(self, data: pd.DataFrame) -> dict[str, int]:
        """Calculate data quality metrics."""
        return {
            "missing_values": int(data.isna().sum().sum()),
            "duplicate_timestamps": int(data["timestamp"].duplicated().sum()),
            "zero_volume_periods": int((data["volume"] == 0).sum()),
        }
