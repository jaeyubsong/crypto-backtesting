"""
Financial data types for precise monetary calculations.

This module provides Decimal-based types to avoid floating-point precision issues
in financial calculations, which is critical for trading applications.
"""

from decimal import ROUND_HALF_UP, Decimal

# All financial calculations use Decimal directly for precision
# No custom type aliases - Decimal is clear and sufficient

# Financial calculation constants
FINANCIAL_PRECISION = Decimal("0.00000001")  # 8 decimal places (crypto standard)
PERCENTAGE_PRECISION = Decimal("0.0001")  # 4 decimal places for percentages
PRICE_PRECISION = Decimal("0.01")  # 2 decimal places for USD prices

# Common financial values as Decimal constants
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def to_decimal(value: str | int | float | Decimal) -> Decimal:
    """Convert various numeric types to Decimal with proper precision.

    Args:
        value: Numeric value to convert

    Returns:
        Decimal representation of the value

    Examples:
        >>> to_decimal(50000.0)
        Decimal('50000.00')
        >>> to_decimal('1.5')
        Decimal('1.5')
    """
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_price(price: Decimal) -> Decimal:
    """Round price to appropriate precision for trading.

    Args:
        price: Price value to round

    Returns:
        Rounded price as Decimal
    """
    return price.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)


def round_amount(amount: Decimal) -> Decimal:
    """Round amount to appropriate precision for trading.

    Args:
        amount: Amount value to round

    Returns:
        Rounded amount as Decimal
    """
    return amount.quantize(FINANCIAL_PRECISION, rounding=ROUND_HALF_UP)


def round_percentage(percentage: Decimal) -> Decimal:
    """Round percentage to appropriate precision.

    Args:
        percentage: Percentage value to round

    Returns:
        Rounded percentage as Decimal
    """
    return percentage.quantize(PERCENTAGE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_notional_value(amount: Decimal, price: Decimal) -> Decimal:
    """Calculate notional value with proper precision.

    Args:
        amount: Position amount
        price: Asset price

    Returns:
        Notional value as Decimal
    """
    return round_amount(amount * price)


def calculate_margin_needed(notional_value: Decimal, leverage: Decimal) -> Decimal:
    """Calculate margin needed with proper precision.

    Args:
        notional_value: Total notional value
        leverage: Leverage multiplier

    Returns:
        Required margin as Decimal
    """
    if leverage <= ZERO:
        raise ValueError(f"Leverage must be positive, got {leverage}")

    return round_amount(notional_value / leverage)


def calculate_pnl(
    entry_price: Decimal,
    exit_price: Decimal,
    amount: Decimal,
    position_type: str,
) -> Decimal:
    """Calculate PnL with proper precision.

    Args:
        entry_price: Entry price of position
        exit_price: Exit price of position
        amount: Position amount (absolute value)
        position_type: 'LONG' or 'SHORT'

    Returns:
        PnL as Decimal
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
