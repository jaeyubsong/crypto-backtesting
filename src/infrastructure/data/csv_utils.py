"""
CSV Data Utility functions.

This module provides utility functions for directory operations and data filtering.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.exceptions.backtest import DataError


class CSVUtils:
    """Utility functions for CSV data operations."""

    @staticmethod
    def validate_data_directory(data_dir: Path) -> None:
        """Validate that the data directory exists and has expected structure."""
        if not data_dir.exists():
            raise DataError(f"Data directory not found: {data_dir}")

        binance_dir = data_dir / "binance"
        if not binance_dir.exists():
            raise DataError(f"Binance data directory not found: {binance_dir}")

    @staticmethod
    def get_available_symbols(data_dir: Path, trading_mode: str = "futures") -> list[str]:
        """Get list of available symbols."""
        binance_dir = data_dir / "binance" / trading_mode
        if not binance_dir.exists():
            return []

        symbols = []
        for symbol_dir in binance_dir.iterdir():
            if symbol_dir.is_dir():
                symbols.append(symbol_dir.name)

        return sorted(symbols)

    @staticmethod
    def get_available_timeframes(
        data_dir: Path, symbol: str, trading_mode: str = "futures"
    ) -> list[str]:
        """Get list of available timeframes for a symbol."""
        symbol_dir = data_dir / "binance" / trading_mode / symbol
        if not symbol_dir.exists():
            return []

        timeframes = []
        for tf_dir in symbol_dir.iterdir():
            if tf_dir.is_dir():
                timeframes.append(tf_dir.name)

        return sorted(timeframes)

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame, start_date: datetime, end_date: datetime
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
