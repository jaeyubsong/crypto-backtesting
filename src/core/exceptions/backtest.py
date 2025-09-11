"""
Custom exception hierarchy for backtesting platform.

This module defines domain-specific exceptions for better error handling.
"""


class BacktestException(Exception):
    """Base exception for all backtesting-related errors."""

    pass


class ValidationError(BacktestException):
    """Raised when input validation fails."""

    pass


class DataError(BacktestException):
    """Raised when data access or processing fails."""

    pass


class StrategyError(BacktestException):
    """Raised when strategy execution fails."""

    pass


class CalculationError(BacktestException):
    """Raised when mathematical calculations fail."""

    pass


class ConfigurationError(BacktestException):
    """Raised when configuration is invalid."""

    pass


class PortfolioError(BacktestException):
    """Raised when portfolio operations fail."""

    pass


class InsufficientFundsError(PortfolioError):
    """Raised when there are insufficient funds for an operation."""

    def __init__(self, required: float, available: float, operation: str = "operation"):
        self.required = required
        self.available = available
        self.operation = operation
        super().__init__(
            f"Insufficient funds for {operation}: required={required:.2f}, available={available:.2f}"
        )


class PositionNotFoundError(PortfolioError):
    """Raised when trying to operate on a non-existent position."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Position not found for symbol: {symbol}")


class InvalidLeverageError(ValidationError):
    """Raised when leverage is invalid for the trading mode."""

    def __init__(self, leverage: float, mode: str, max_leverage: float):
        self.leverage = leverage
        self.mode = mode
        self.max_leverage = max_leverage
        super().__init__(f"Invalid leverage {leverage} for {mode} mode (max: {max_leverage})")


class LiquidationError(PortfolioError):
    """Raised when a position is liquidated."""

    def __init__(self, symbol: str, loss: float, reason: str = "margin call"):
        self.symbol = symbol
        self.loss = loss
        self.reason = reason
        super().__init__(f"Position liquidated for {symbol}: loss={loss:.2f}, reason={reason}")
