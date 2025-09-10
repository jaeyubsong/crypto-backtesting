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
