"""
Validation utilities for core domain models.

Provides consistent validation across the application.
"""

from typing import Any

from src.core.enums import Symbol
from src.core.exceptions.backtest import ValidationError


def validate_symbol(symbol: Any, param_name: str = "symbol") -> Symbol:
    """Validate that a value is a Symbol enum.

    Args:
        symbol: Value to validate
        param_name: Parameter name for error messages

    Returns:
        The validated Symbol

    Raises:
        TypeError: If symbol is not a Symbol enum
    """
    if not isinstance(symbol, Symbol):
        raise TypeError(f"{param_name} must be Symbol enum, got {type(symbol).__name__}")
    return symbol


def validate_positive(value: float, param_name: str) -> float:
    """Validate that a numeric value is positive.

    Args:
        value: Value to validate
        param_name: Parameter name for error messages

    Returns:
        The validated value

    Raises:
        ValidationError: If value is not positive
    """
    if value <= 0:
        raise ValidationError(f"{param_name} must be positive, got {value}")
    return value


def validate_percentage(value: float, param_name: str = "percentage") -> float:
    """Validate that a value is a valid percentage (0-100).

    Args:
        value: Value to validate
        param_name: Parameter name for error messages

    Returns:
        The validated percentage

    Raises:
        ValidationError: If value is not between 0 and 100
    """
    if value <= 0 or value > 100:
        raise ValidationError(f"{param_name} must be between 0 and 100, got {value}")
    return value


def validate_margin_rate(rate: float, param_name: str = "margin_rate") -> float:
    """Validate that a margin rate is reasonable (0-1).

    Args:
        rate: Rate to validate
        param_name: Parameter name for error messages

    Returns:
        The validated rate

    Raises:
        ValidationError: If rate is not between 0 and 1
    """
    if rate < 0 or rate > 1:
        raise ValidationError(f"{param_name} must be between 0 and 1, got {rate}")
    return rate
