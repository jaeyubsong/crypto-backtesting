"""
Core type definitions and utilities.
"""

# Re-export financial utilities for easy access
from .financial import (
    FINANCIAL_PRECISION,
    ONE,
    PERCENTAGE_PRECISION,
    PRICE_PRECISION,
    ZERO,
    calculate_margin_needed,
    calculate_notional_value,
    calculate_pnl,
    round_amount,
    round_percentage,
    round_price,
    to_decimal,
)

__all__ = [
    # Utility functions
    "to_decimal",
    "round_price",
    "round_amount",
    "round_percentage",
    "calculate_notional_value",
    "calculate_margin_needed",
    "calculate_pnl",
    # Constants
    "FINANCIAL_PRECISION",
    "PERCENTAGE_PRECISION",
    "PRICE_PRECISION",
    "ZERO",
    "ONE",
]
