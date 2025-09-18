"""
CSV Data Validation utilities.

This module provides security and data integrity validation for CSV data loading.
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.enums.timeframes import Timeframe
from src.core.exceptions.backtest import DataError, ValidationError


class CSVValidator:
    """Handles validation of CSV data and loading parameters."""

    @staticmethod
    def validate_load_params(
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

    @staticmethod
    def sanitize_path_component(component: str, component_name: str) -> str:
        """Sanitize path components to prevent traversal attacks."""
        if not component:
            raise ValidationError(f"{component_name.capitalize()} cannot be empty")

        # Remove dangerous characters and sequences
        if ".." in component or "/" in component or "\\" in component:
            raise ValidationError(f"Invalid {component_name}: contains path traversal characters")

        # Allow only alphanumeric, underscore, dash, and dot for valid filenames
        safe_component = re.sub(r"[^a-zA-Z0-9_.-]", "", component)

        if not safe_component or safe_component != component:
            raise ValidationError(
                f"Invalid {component_name}: '{component}' contains invalid characters. "
                f"Only alphanumeric, underscore, dash, and dot are allowed."
            )

        # Additional length check
        if len(safe_component) > 50:
            raise ValidationError(f"{component_name.capitalize()} too long: maximum 50 characters")

        return safe_component

    @staticmethod
    def validate_path_safety(path: Path, data_dir: Path) -> None:
        """Validate that the constructed path is safe and within data directory."""
        try:
            # Resolve the path to detect any traversal attempts
            resolved_path = path.resolve()
            data_dir_resolved = data_dir.resolve()

            # Check if the path is within the data directory
            if not str(resolved_path).startswith(str(data_dir_resolved)):
                raise ValidationError("Path traversal attempt detected")

        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path construction: {str(e)}") from e

    @staticmethod
    def validate_csv_structure(df: pd.DataFrame, file_path: Path) -> None:
        """Validate CSV file has expected structure."""
        if df.empty:
            return  # Empty files are handled separately

        # Perform comprehensive CSV validation
        CSVValidator._validate_csv_columns(df, file_path)
        CSVValidator._validate_csv_data_integrity(df, file_path)

    @staticmethod
    def _validate_csv_columns(df: pd.DataFrame, file_path: Path) -> None:
        """Validate CSV file has required columns."""
        expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = set(expected_columns) - set(df.columns)
        if missing_columns:
            raise DataError(f"CSV file {file_path} missing columns: {missing_columns}")

    @staticmethod
    def _validate_csv_data_integrity(df: pd.DataFrame, file_path: Path) -> None:
        """Validate CSV data integrity and value ranges."""
        if len(df) == 0:
            return

        # Validate price ranges
        CSVValidator._validate_csv_price_ranges(df, file_path)

        # Validate volume data
        try:
            if (df["volume"] < 0).any():
                raise DataError(f"Invalid volume data in {file_path}: negative volume values")
        except (TypeError, ValueError) as e:
            raise DataError(f"Invalid volume data in {file_path}: invalid data type") from e

        # Validate OHLC relationships
        CSVValidator._validate_csv_ohlc_relationships(df, file_path)

    @staticmethod
    def _validate_csv_price_ranges(df: pd.DataFrame, file_path: Path) -> None:
        """Validate price columns have positive values."""
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            try:
                if (df[col] <= 0).any():
                    raise DataError(
                        f"Invalid price data in {file_path}: {col} has non-positive values"
                    )
            except (TypeError, ValueError) as e:
                raise DataError(
                    f"Invalid price data in {file_path}: {col} has invalid data type"
                ) from e

    @staticmethod
    def _validate_csv_ohlc_relationships(df: pd.DataFrame, file_path: Path) -> None:
        """Validate OHLC price relationships are logically consistent."""
        try:
            invalid_ohlc = (
                (df["high"] < df["low"])
                | (df["high"] < df["open"])
                | (df["high"] < df["close"])
                | (df["low"] > df["open"])
                | (df["low"] > df["close"])
            )

            if invalid_ohlc.any():
                raise DataError(f"Invalid OHLC relationships in {file_path}")
        except (TypeError, ValueError) as e:
            raise DataError(f"Invalid OHLC data in {file_path}: invalid data types") from e
