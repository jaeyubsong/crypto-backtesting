"""
OHLCV data validation module.

Provides comprehensive validation for OHLCV market data including structure,
data types, value ranges, and relationship validation.
"""

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import ValidationError


class OHLCVValidator:
    """
    OHLCV data validator with comprehensive validation capabilities.

    Features:
    - Data structure validation (required columns, duplicates)
    - Data type validation for numeric columns
    - Value range validation (positive prices, non-negative volume)
    - OHLC relationship validation
    - Data quality checks with warnings
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
