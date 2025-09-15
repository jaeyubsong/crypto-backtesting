"""Helper methods for Portfolio to reduce complexity."""

from datetime import UTC, datetime
from decimal import Decimal

from src.core.constants import (
    DEFAULT_TAKER_FEE,
    MAX_POSITIONS_PER_PORTFOLIO,
    MAX_TRADE_SIZE,
    MIN_TRADE_SIZE,
)
from src.core.enums import ActionType, PositionType, Symbol
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.position import Position, Trade
from src.core.types.financial import to_decimal
from src.core.utils.validation import validate_positive, validate_symbol


class PortfolioValidator:
    """Centralized validation helper for portfolio operations.

    Consolidates all portfolio-related validation logic to avoid duplication
    across portfolio_core.py, portfolio_trading.py, and portfolio_risk.py.
    """

    @staticmethod
    def validate_position_for_add(position: Position, position_count: int) -> None:
        """Validate position before adding to portfolio.

        Args:
            position: Position to validate
            position_count: Current number of positions in portfolio

        Raises:
            ValidationError: If position is invalid or limits exceeded
        """
        # Check position limit
        if position_count >= MAX_POSITIONS_PER_PORTFOLIO:
            raise ValidationError(
                f"Maximum positions limit reached ({MAX_POSITIONS_PER_PORTFOLIO})"
            )

        # Validate position instance
        if not isinstance(position, Position):
            raise ValidationError("Position must be a valid Position instance")

        # Validate position attributes
        if not position.symbol or not isinstance(position.symbol, Symbol):
            raise ValidationError("Position symbol must be a valid Symbol enum")

        if position.leverage <= 0:
            raise ValidationError("Position leverage must be positive")

        if position.margin_used < 0:
            raise ValidationError("Position margin_used must be non-negative")

    @staticmethod
    def validate_position_exists(symbol: Symbol, positions: dict) -> None:
        """Validate that position exists for the given symbol.

        Args:
            symbol: Symbol to check
            positions: Portfolio positions dictionary

        Raises:
            ValidationError: If position not found
        """
        if symbol not in positions:
            raise ValidationError(f"Position not found for symbol: {symbol}")

    @staticmethod
    def validate_close_position_params(
        symbol: Symbol, close_price: Decimal, fee: Decimal
    ) -> tuple[Symbol, Decimal, Decimal]:
        """Validate parameters for closing a position.

        Args:
            symbol: Position symbol
            close_price: Closing price
            fee: Trading fee

        Returns:
            Validated parameters

        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(symbol, Symbol):
            raise ValidationError("Symbol must be a valid Symbol enum")

        if close_price <= 0:
            raise ValidationError("Close price must be positive")

        if fee < 0:
            raise ValidationError("Fee must be non-negative")

        return symbol, close_price, fee

    @staticmethod
    def validate_margin_requirement(
        margin_needed: Decimal, available_cash: Decimal, operation: str
    ) -> None:
        """Validate sufficient margin is available.

        Args:
            margin_needed: Required margin amount
            available_cash: Available cash/margin
            operation: Description of operation for error context

        Raises:
            InsufficientFundsError: If insufficient funds
        """
        if margin_needed > available_cash:
            raise InsufficientFundsError(
                required=float(margin_needed),
                available=float(available_cash),
                operation=operation,
            )

    @staticmethod
    def validate_percentage(percentage: float, name: str = "percentage") -> float:
        """Validate percentage is in valid range.

        Args:
            percentage: Percentage to validate (0-100, exclusive of 0)
            name: Name for error messages

        Returns:
            Validated percentage

        Raises:
            ValidationError: If percentage is invalid
        """
        if percentage <= 0 or percentage > 100:
            raise ValidationError(f"{name} must be between 0 and 100, got {percentage}")
        return percentage


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
        amount: Decimal, price: Decimal, leverage: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Calculate notional value and margin needed."""
        notional_value = amount * price
        margin_needed = notional_value / leverage if leverage > 0 else notional_value
        return notional_value, margin_needed

    @staticmethod
    def check_sufficient_funds(margin_needed: Decimal, available: Decimal, operation: str) -> None:
        """Check if sufficient funds available."""
        if margin_needed > available:
            raise InsufficientFundsError(
                required=float(margin_needed),
                available=float(available),
                operation=operation,
            )


class FeeCalculator:
    """Calculates trading fees based on trading mode and type."""

    @staticmethod
    def calculate_fee(
        notional_value: Decimal, fee_rate: Decimal = to_decimal(DEFAULT_TAKER_FEE)
    ) -> Decimal:
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
            size=to_decimal(size),
            entry_price=to_decimal(entry_price),
            leverage=to_decimal(leverage),
            timestamp=datetime.now(UTC),
            position_type=position_type,
            margin_used=to_decimal(margin_used),
        )

    @staticmethod
    def update_position_size(
        position: Position,
        additional_size: Decimal,
        additional_price: Decimal,
        additional_margin: Decimal,
    ) -> None:
        """Update position with additional size."""
        position_size = to_decimal(position.size)
        position_price = to_decimal(position.entry_price)
        position_margin = to_decimal(position.margin_used)

        total_size = position_size + additional_size
        total_value = (position_size * position_price) + (additional_size * additional_price)
        position.entry_price = total_value / total_size
        position.size = total_size
        position.margin_used = position_margin + additional_margin
