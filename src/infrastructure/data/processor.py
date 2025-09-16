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

        # Check required columns
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")

        # Check for duplicates
        if data["timestamp"].duplicated().any():
            raise ValidationError("Duplicate timestamps found in data")

        # Validate data types
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise ValidationError(f"Column {col} must be numeric")

        # Check for NaN values
        for col in required_columns:
            if data[col].isna().any():
                raise ValidationError(f"Column {col} contains NaN values")

        # Validate price ranges
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            if (data[col] <= 0).any():
                raise ValidationError(f"Column {col} contains non-positive values")

        # Validate volume
        if (data["volume"] < 0).any():
            raise ValidationError("Volume column contains negative values")

        # Validate OHLC relationships
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

        # Check for reasonable price variations
        daily_range = (data["high"] - data["low"]) / data["low"]
        extreme_moves = daily_range > 0.5  # More than 50% daily range

        if extreme_moves.any():
            extreme_count = extreme_moves.sum()
            logger.warning(f"Found {extreme_count} periods with extreme price movements (>50%)")

        # Validate timestamp ordering
        if not data["timestamp"].is_monotonic_increasing:
            logger.warning("Timestamps are not in ascending order")

        return True

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

        cleaned_data = data.copy()

        try:
            # Validate timestamp data type first
            if not pd.api.types.is_numeric_dtype(cleaned_data["timestamp"]):
                raise DataError("Timestamp column must be numeric (milliseconds since epoch)")

            # Remove duplicate timestamps (keep first occurrence)
            duplicate_mask = cleaned_data["timestamp"].duplicated(keep="first")
            if duplicate_mask.any():
                duplicate_count = duplicate_mask.sum()
                logger.warning(f"Removing {duplicate_count} duplicate timestamps")
                cleaned_data = cleaned_data[~duplicate_mask]

            # Sort by timestamp
            cleaned_data = cleaned_data.sort_values("timestamp").reset_index(drop=True)

            # Handle missing values
            cleaned_data = self._handle_missing_values(cleaned_data)

            # Fix invalid OHLC relationships
            cleaned_data = self._fix_ohlc_relationships(cleaned_data)

            # Ensure volume is non-negative
            cleaned_data["volume"] = cleaned_data["volume"].clip(lower=0)

            # Round prices to reasonable precision
            price_columns = ["open", "high", "low", "close"]
            for col in price_columns:
                cleaned_data[col] = cleaned_data[col].round(8)

            # Round volume to reasonable precision
            cleaned_data["volume"] = cleaned_data["volume"].round(8)

            # Final validation
            self.validate_data(cleaned_data)

            logger.info(f"Cleaned data: {len(data)} -> {len(cleaned_data)} rows")

            return cleaned_data

        except Exception as e:
            raise DataError(f"Failed to clean data: {str(e)}") from e

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
        try:
            Timeframe.from_string(target_timeframe)
        except ValueError as e:
            raise ValidationError(str(e)) from e

        try:
            # Convert timestamp to datetime index
            df_resampled = data.copy()
            df_resampled["datetime"] = pd.to_datetime(
                df_resampled["timestamp"], unit="ms", utc=True
            )
            df_resampled = df_resampled.set_index("datetime")

            # Define resampling rule
            freq = self._get_pandas_freq(target_timeframe)

            # Resample OHLCV data
            resampled = (
                df_resampled.resample(freq)
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

            # Reset index and ensure proper column order
            result = resampled.reset_index(drop=True)
            result = result[["timestamp", "open", "high", "low", "close", "volume"]]

            # Convert timestamp back to milliseconds
            result["timestamp"] = result["timestamp"].astype("int64")

            # Validate resampled data
            self.validate_data(result)

            logger.info(f"Resampled data: {len(data)} -> {len(result)} rows to {target_timeframe}")

            return result

        except Exception as e:
            raise DataError(f"Failed to resample data to {target_timeframe}: {str(e)}") from e

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
        Calculate basic technical indicators.

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with additional indicator columns
        """
        if data.empty:
            return data

        result = data.copy()

        try:
            # Simple moving averages
            result["sma_20"] = result["close"].rolling(window=20).mean()
            result["sma_50"] = result["close"].rolling(window=50).mean()

            # Exponential moving averages
            result["ema_12"] = result["close"].ewm(span=12).mean()
            result["ema_26"] = result["close"].ewm(span=26).mean()

            # MACD
            result["macd"] = result["ema_12"] - result["ema_26"]
            result["macd_signal"] = result["macd"].ewm(span=9).mean()
            result["macd_histogram"] = result["macd"] - result["macd_signal"]

            # RSI
            delta = result["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta).where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            result["rsi"] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            bb_middle = result["close"].rolling(window=20).mean()
            bb_std = result["close"].rolling(window=20).std()
            result["bb_upper"] = bb_middle + (2 * bb_std)
            result["bb_lower"] = bb_middle - (2 * bb_std)
            result["bb_middle"] = bb_middle

            # Volume-weighted average price (VWAP)
            vwap_num = (result["close"] * result["volume"]).cumsum()
            vwap_den = result["volume"].cumsum()
            result["vwap"] = vwap_num / vwap_den

            logger.info(f"Calculated basic indicators for {len(result)} rows")

            return result

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {str(e)}")
            return data  # Return original data if indicator calculation fails

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
                "start_time": pd.to_datetime(
                    data["timestamp"].iloc[0], unit="ms", utc=True
                ).isoformat(),
                "end_time": pd.to_datetime(
                    data["timestamp"].iloc[-1], unit="ms", utc=True
                ).isoformat(),
                "price_stats": {
                    "min_low": float(data["low"].min()),
                    "max_high": float(data["high"].max()),
                    "first_open": float(data["open"].iloc[0]),
                    "last_close": float(data["close"].iloc[-1]),
                    "total_volume": float(data["volume"].sum()),
                    "avg_volume": float(data["volume"].mean()),
                },
                "data_quality": {
                    "missing_values": int(data.isna().sum().sum()),
                    "duplicate_timestamps": int(data["timestamp"].duplicated().sum()),
                    "zero_volume_periods": int((data["volume"] == 0).sum()),
                },
            }

            # Calculate price change
            if len(data) > 0:
                price_change = data["close"].iloc[-1] - data["open"].iloc[0]
                price_change_pct = (price_change / data["open"].iloc[0]) * 100
                summary["price_stats"]["total_change"] = float(price_change)
                summary["price_stats"]["total_change_pct"] = float(price_change_pct)

            return summary

        except Exception as e:
            return {"status": "error", "error": str(e), "rows": len(data)}
