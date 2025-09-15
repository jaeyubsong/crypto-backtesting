"""
Financial data types for high-performance backtesting calculations.

This module provides float-based types optimized for speed in backtesting scenarios.
While float has minor precision limitations, it offers 10-100x performance improvement
over Decimal, which is crucial for processing large historical datasets.

IMPORTANT PRECISION CONSIDERATIONS:
- Float64 provides ~15-16 significant decimal digits
- Suitable for backtesting historical data where performance > precision
- NOT suitable for production trading (use Decimal for real money operations)
- Cumulative rounding errors may occur over many operations
- Always use the provided rounding functions for consistent precision

Precision Trade-offs:
✅ 10-100x faster calculations
✅ 4x memory reduction
✅ Native NumPy/Pandas compatibility
⚠️  ~1e-15 relative precision vs infinite precision Decimal
⚠️  Potential accumulation of rounding errors in long simulations
"""

# Financial calculation precision (number of decimal places)
FINANCIAL_DECIMALS = 8  # 8 decimal places (crypto standard)
PERCENTAGE_DECIMALS = 4  # 4 decimal places for percentages
PRICE_DECIMALS = 2  # 2 decimal places for USD prices

# Common financial values as float constants
ZERO = 0.0
ONE = 1.0
HUNDRED = 100.0


def to_float(value: str | int | float) -> float:
    """Convert various numeric types to float.

    Args:
        value: Numeric value to convert

    Returns:
        Float representation of the value

    Examples:
        >>> to_float(50000)
        50000.0
        >>> to_float('1.5')
        1.5
    """
    if isinstance(value, float):
        return value
    return float(value)


def round_price(price: float) -> float:
    """Round price to appropriate precision for trading.

    Args:
        price: Price value to round

    Returns:
        Rounded price as float
    """
    return round(price, PRICE_DECIMALS)


def round_amount(amount: float) -> float:
    """Round amount to appropriate precision for trading.

    Args:
        amount: Amount value to round

    Returns:
        Rounded amount as float
    """
    return round(amount, FINANCIAL_DECIMALS)


def round_percentage(percentage: float) -> float:
    """Round percentage to appropriate precision.

    Args:
        percentage: Percentage value to round

    Returns:
        Rounded percentage as float
    """
    return round(percentage, PERCENTAGE_DECIMALS)


def calculate_notional_value(amount: float, price: float) -> float:
    """Calculate notional value with proper precision.

    Args:
        amount: Position amount
        price: Asset price

    Returns:
        Notional value as float
    """
    return round_amount(amount * price)


def calculate_margin_needed(notional_value: float, leverage: float) -> float:
    """Calculate margin needed with proper precision.

    Args:
        notional_value: Total notional value
        leverage: Leverage multiplier

    Returns:
        Required margin as float
    """
    if leverage <= ZERO:
        raise ValueError(f"Leverage must be positive, got {leverage}")

    return round_amount(notional_value / leverage)


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    amount: float,
    position_type: str,
) -> float:
    """Calculate PnL with proper precision.

    Args:
        entry_price: Entry price of position
        exit_price: Exit price of position
        amount: Position amount (absolute value)
        position_type: 'LONG' or 'SHORT'

    Returns:
        PnL as float
    """
    amt = abs(amount)
    position_type_upper = position_type.upper()

    if position_type_upper == "LONG":
        pnl = (exit_price - entry_price) * amt
    elif position_type_upper == "SHORT":
        pnl = (entry_price - exit_price) * amt
    else:
        raise ValueError(f"Invalid position type: {position_type}")

    return round_amount(pnl)


def safe_float_comparison(a: float, b: float, tolerance: float = 1e-9) -> bool:
    """Compare floats with tolerance for precision issues.

    Args:
        a: First float to compare
        b: Second float to compare
        tolerance: Acceptable difference (default: 1e-9)

    Returns:
        True if floats are equal within tolerance

    Examples:
        >>> safe_float_comparison(0.1 + 0.2, 0.3)
        True
        >>> safe_float_comparison(1000000.1, 1000000.2, 0.01)
        False
    """
    return abs(a - b) < tolerance


def validate_safe_float_range(value: float, operation: str = "calculation") -> float:
    """Validate that a float is within safe calculation range.

    Args:
        value: Float value to validate
        operation: Description of the operation for error messages

    Returns:
        The validated float value

    Raises:
        ValueError: If value exceeds safe float range
    """
    from src.core.constants import MAX_SAFE_FLOAT, MIN_SAFE_FLOAT

    if not (MIN_SAFE_FLOAT <= value <= MAX_SAFE_FLOAT):
        raise ValueError(
            f"Value {value} exceeds safe float range for {operation}. "
            f"Range: {MIN_SAFE_FLOAT} to {MAX_SAFE_FLOAT}"
        )

    return value
