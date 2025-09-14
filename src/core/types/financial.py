"""
Financial data types for precise monetary calculations.

This module provides Decimal-based types to avoid floating-point precision issues
in financial calculations, which is critical for trading applications.
"""

from decimal import ROUND_HALF_UP, Decimal

# Financial precision types
Price = Decimal
Amount = Decimal
Leverage = Decimal
PnL = Decimal
Fee = Decimal
MarginRate = Decimal

# Type alias for backward compatibility during migration
PriceFloat = Price | float
AmountFloat = Amount | float
LeverageFloat = Leverage | float

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


def round_price(price: Decimal | float) -> Decimal:
    """Round price to appropriate precision for trading.

    Args:
        price: Price value to round

    Returns:
        Rounded price as Decimal
    """
    return to_decimal(price).quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)


def round_amount(amount: Decimal | float) -> Decimal:
    """Round amount to appropriate precision for trading.

    Args:
        amount: Amount value to round

    Returns:
        Rounded amount as Decimal
    """
    return to_decimal(amount).quantize(FINANCIAL_PRECISION, rounding=ROUND_HALF_UP)


def round_percentage(percentage: Decimal | float) -> Decimal:
    """Round percentage to appropriate precision.

    Args:
        percentage: Percentage value to round

    Returns:
        Rounded percentage as Decimal
    """
    return to_decimal(percentage).quantize(PERCENTAGE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_notional_value(amount: Decimal | float, price: Decimal | float) -> Decimal:
    """Calculate notional value with proper precision.

    Args:
        amount: Position amount
        price: Asset price

    Returns:
        Notional value as Decimal
    """
    return round_amount(to_decimal(amount) * to_decimal(price))


def calculate_margin_needed(notional_value: Decimal | float, leverage: Decimal | float) -> Decimal:
    """Calculate margin needed with proper precision.

    Args:
        notional_value: Total notional value
        leverage: Leverage multiplier

    Returns:
        Required margin as Decimal
    """
    leverage_decimal = to_decimal(leverage)
    if leverage_decimal <= ZERO:
        raise ValueError(f"Leverage must be positive, got {leverage_decimal}")

    return round_amount(to_decimal(notional_value) / leverage_decimal)


def calculate_pnl(
    entry_price: Decimal | float,
    exit_price: Decimal | float,
    amount: Decimal | float,
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
    entry = to_decimal(entry_price)
    exit = to_decimal(exit_price)
    amt = to_decimal(abs(float(amount)))

    position_type_upper = position_type.upper()

    if position_type_upper == "LONG":
        pnl = (exit - entry) * amt
    elif position_type_upper == "SHORT":
        pnl = (entry - exit) * amt
    else:
        raise ValueError(f"Invalid position type: {position_type}")

    return round_amount(pnl)
