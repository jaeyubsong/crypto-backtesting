"""Helper methods for Portfolio to reduce complexity."""

from datetime import UTC, datetime

from src.core.constants import DEFAULT_TAKER_FEE, MAX_TRADE_SIZE, MIN_TRADE_SIZE
from src.core.enums import ActionType, PositionType, Symbol
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.position import Position, Trade
from src.core.utils.validation import validate_positive, validate_symbol


class OrderValidator:
    """Validates order parameters."""

    @staticmethod
    def validate_order(
        symbol: Symbol, amount: float, price: float, leverage: float
    ) -> tuple[Symbol, float, float, float]:
        """Validate and return order parameters."""
        symbol = validate_symbol(symbol)
        price = validate_positive(price, "price")
        amount = validate_positive(amount, "amount")
        leverage = validate_positive(leverage, "leverage")

        # Check trade size limits
        if amount < MIN_TRADE_SIZE:
            raise ValidationError(f"Trade size too small: {amount} < {MIN_TRADE_SIZE}")
        if amount > MAX_TRADE_SIZE:
            raise ValidationError(f"Trade size too large: {amount} > {MAX_TRADE_SIZE}")

        return symbol, amount, price, leverage

    @staticmethod
    def calculate_margin_needed(
        amount: float, price: float, leverage: float
    ) -> tuple[float, float]:
        """Calculate notional value and margin needed."""
        notional_value = amount * price
        margin_needed = notional_value / leverage if leverage > 0 else notional_value
        return notional_value, margin_needed

    @staticmethod
    def check_sufficient_funds(margin_needed: float, available: float, operation: str) -> None:
        """Check if sufficient funds available."""
        if margin_needed > available:
            raise InsufficientFundsError(
                required=margin_needed,
                available=available,
                operation=operation,
            )


class FeeCalculator:
    """Calculates trading fees based on trading mode and type."""

    @staticmethod
    def calculate_fee(notional_value: float, fee_rate: float = DEFAULT_TAKER_FEE) -> float:
        """Calculate trading fee."""
        return notional_value * fee_rate


class TradeRecorder:
    """Records trades to history."""

    @staticmethod
    def create_trade(
        symbol: Symbol,
        action: ActionType,
        quantity: float,
        price: float,
        leverage: float,
        fee: float,
        position_type: PositionType,
        pnl: float,
        margin_used: float,
    ) -> Trade:
        """Create a trade record."""
        return Trade(
            timestamp=datetime.now(UTC),
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            leverage=leverage,
            fee=fee,
            position_type=position_type,
            pnl=pnl,
            margin_used=margin_used,
        )


class PositionManager:
    """Manages position lifecycle."""

    @staticmethod
    def create_position(
        symbol: Symbol,
        size: float,
        entry_price: float,
        leverage: float,
        position_type: PositionType,
        margin_used: float,
    ) -> Position:
        """Create a new position."""
        return Position(
            symbol=symbol,
            size=size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=datetime.now(UTC),
            position_type=position_type,
            margin_used=margin_used,
        )

    @staticmethod
    def update_position_size(
        position: Position,
        additional_size: float,
        additional_price: float,
        additional_margin: float,
    ) -> None:
        """Update position with additional size."""
        total_size = position.size + additional_size
        total_value = (position.size * position.entry_price) + (additional_size * additional_price)
        position.entry_price = total_value / total_size
        position.size = total_size
        position.margin_used += additional_margin
