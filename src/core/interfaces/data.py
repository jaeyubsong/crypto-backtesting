"""
Data access interfaces.
To be implemented in Phase 3.
"""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class IDataLoader(ABC):
    """Abstract interface for data loading."""

    @abstractmethod
    async def load_data(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Load OHLCV data for the specified parameters."""
        pass


class IDataProcessor(ABC):
    """Abstract interface for data processing."""

    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate data integrity."""
        pass

    @abstractmethod
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize data."""
        pass

    @abstractmethod
    def resample_data(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample data to different timeframe."""
        pass


class IMetricsCalculator(ABC):
    """Abstract interface for performance metrics calculation."""

    @abstractmethod
    def calculate_returns(self, portfolio_history: pd.DataFrame) -> dict[str, float]:
        """Calculate return metrics."""
        pass

    @abstractmethod
    def calculate_risk_metrics(self, portfolio_history: pd.DataFrame) -> dict[str, float]:
        """Calculate risk-adjusted metrics."""
        pass

    @abstractmethod
    def calculate_trade_metrics(self, trades: pd.DataFrame) -> dict[str, float]:
        """Calculate trade statistics."""
        pass
