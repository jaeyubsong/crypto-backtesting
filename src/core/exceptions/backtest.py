"""
Backtest domain exceptions.
"""


class BacktestException(Exception):
    """Base exception for backtesting errors."""

    pass


class ValidationError(BacktestException):
    """Invalid input validation errors."""

    pass


class DataError(BacktestException):
    """Data access/processing errors."""

    pass


class StrategyError(BacktestException):
    """Strategy execution errors."""

    pass


class CalculationError(BacktestException):
    """Metrics/calculation errors."""

    pass


class ConfigurationError(BacktestException):
    """Configuration/setup errors."""

    pass
