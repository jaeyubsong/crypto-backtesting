"""
Data processor implementation for OHLCV data manipulation.

This module provides a unified interface for OHLCV data processing using
specialized components for validation, cleaning, resampling, and summarization.
"""

from typing import Any

import pandas as pd

from src.core.interfaces.data import IDataProcessor

from .ohlcv_cleaner import OHLCVCleaner
from .ohlcv_resampler import OHLCVResampler
from .ohlcv_summary_generator import OHLCVSummaryGenerator
from .ohlcv_validator import OHLCVValidator
from .technical_indicators import create_technical_indicators_calculator


class OHLCVDataProcessor(IDataProcessor):
    """
    OHLCV data processor with validation, cleaning, and resampling capabilities.

    Uses specialized components following Single Responsibility Principle:
    - OHLCVValidator: Data validation and integrity checks
    - OHLCVCleaner: Data cleaning and normalization
    - OHLCVResampler: Timeframe resampling
    - OHLCVSummaryGenerator: Summary statistics generation
    """

    def __init__(self) -> None:
        self._validator = OHLCVValidator()
        self._cleaner = OHLCVCleaner()
        self._resampler = OHLCVResampler()
        self._summary_generator = OHLCVSummaryGenerator()

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
        return self._validator.validate_data(data)

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
        return self._cleaner.clean_data(data)

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
        return self._resampler.resample_data(data, target_timeframe)

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
        return self._summary_generator.get_data_summary(data)
