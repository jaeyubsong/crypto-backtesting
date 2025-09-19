"""
OHLCV data cleaning module.

Provides data cleaning and normalization capabilities for OHLCV market data.
"""

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import DataError

from .ohlcv_validator import OHLCVValidator


class OHLCVCleaner:
    """
    OHLCV data cleaner with comprehensive cleaning capabilities.

    Features:
    - Duplicate removal and chronological sorting
    - Missing value handling with forward/backward fill
    - OHLC relationship fixing
    - Data precision normalization
    - Comprehensive validation after cleaning
    """

    def __init__(self) -> None:
        self._validator = OHLCVValidator()

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
            self._validator.validate_data(cleaned_data)
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
