"""
Strategy interface definition.
To be implemented in Phase 5.
"""

from abc import ABC, abstractmethod

import pandas as pd


class IStrategy(ABC):
    """Abstract interface for trading strategies."""

    @abstractmethod
    def initialize(self):
        """Called once at the start of backtesting."""
        pass

    @abstractmethod
    def on_data(self, data: pd.Series):
        """Called for each new data point."""
        pass
