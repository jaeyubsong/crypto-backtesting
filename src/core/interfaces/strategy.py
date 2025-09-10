"""
Strategy interface definition.
To be implemented in Phase 5.
"""

from abc import ABC, abstractmethod

import pandas as pd


class IStrategy(ABC):
    """Abstract interface for trading strategies."""

    @abstractmethod
    def initialize(self) -> None:
        """Called once at the start of backtesting."""
        pass

    @abstractmethod
    def on_data(self, data: pd.Series) -> None:
        """Called for each new data point."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate strategy configuration."""
        pass

    @abstractmethod
    def get_required_indicators(self) -> list[str]:
        """Get list of required technical indicators."""
        pass
