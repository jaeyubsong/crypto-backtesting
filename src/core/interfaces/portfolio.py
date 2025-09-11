"""
Portfolio management interfaces.
To be implemented in Phase 4.
"""

from abc import ABC, abstractmethod

from src.core.enums import Symbol


class IPortfolio(ABC):
    """Abstract interface for portfolio management."""

    @abstractmethod
    def buy(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a buy order."""
        pass

    @abstractmethod
    def sell(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order."""
        pass

    @abstractmethod
    def close_position(self, symbol: Symbol, percentage: float = 100.0) -> bool:
        """Close a position."""
        pass

    @abstractmethod
    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value."""
        pass

    @abstractmethod
    def available_margin(self) -> float:
        """Get available margin."""
        pass

    @abstractmethod
    def used_margin(self) -> float:
        """Get used margin."""
        pass

    @abstractmethod
    def margin_ratio(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate margin ratio."""
        pass

    @abstractmethod
    def check_liquidation(self, current_prices: dict[Symbol, float]) -> list[Symbol]:
        """Check and return symbols at risk of liquidation."""
        pass


class IOrderExecutor(ABC):
    """Abstract interface for order execution."""

    @abstractmethod
    def execute_order(self, symbol: str, action: str, amount: float, price: float) -> bool:
        """Execute an order."""
        pass

    @abstractmethod
    def validate_order(self, symbol: str, action: str, amount: float, leverage: float) -> bool:
        """Validate order parameters."""
        pass

    @abstractmethod
    def calculate_fees(self, notional_value: float, trading_mode: str) -> float:
        """Calculate trading fees."""
        pass
