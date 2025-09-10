"""
Portfolio management interfaces.
To be implemented in Phase 4.
"""

from abc import ABC, abstractmethod


class IPortfolio(ABC):
    """Abstract interface for portfolio management."""

    @abstractmethod
    def buy(self, symbol: str, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a buy order."""
        pass

    @abstractmethod
    def sell(self, symbol: str, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order."""
        pass

    @abstractmethod
    def close_position(self, symbol: str, percentage: float = 100.0) -> bool:
        """Close a position."""
        pass


class IOrderExecutor(ABC):
    """Abstract interface for order execution."""

    @abstractmethod
    def execute_order(self, symbol: str, action: str, amount: float, price: float) -> bool:
        """Execute an order."""
        pass
