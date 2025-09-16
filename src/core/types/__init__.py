"""
Core type definitions and utilities.
"""

# Re-export financial utilities for easy access
from .financial import (
    FINANCIAL_DECIMALS,
    ONE,
    PERCENTAGE_DECIMALS,
    PRICE_DECIMALS,
    ZERO,
    calculate_margin_needed,
    calculate_notional_value,
    calculate_pnl,
    round_amount,
    round_percentage,
    round_price,
    safe_float_comparison,
    to_float,
    validate_safe_float_range,
)

__all__ = [
    # Utility functions
    "to_float",
    "round_price",
    "round_amount",
    "round_percentage",
    "calculate_notional_value",
    "calculate_margin_needed",
    "calculate_pnl",
    "safe_float_comparison",
    "validate_safe_float_range",
    # Constants
    "FINANCIAL_DECIMALS",
    "PERCENTAGE_DECIMALS",
    "PRICE_DECIMALS",
    "ZERO",
    "ONE",
]
