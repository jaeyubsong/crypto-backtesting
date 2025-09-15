"""
Position and Trade domain models.
Enhanced with Decimal precision for financial calculations.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import ValidationError
from src.core.types.financial import (
    ZERO,
    calculate_pnl,
    round_amount,
    round_price,
    to_decimal,
)


@dataclass
class Position:
    """Represents a trading position with precise financial calculations.

    Uses Decimal types for precise financial calculations to avoid
    floating-point precision issues in trading operations.
    """

    symbol: Symbol
    size: Decimal
    entry_price: Decimal
    leverage: Decimal
    timestamp: datetime
    position_type: PositionType
    margin_used: Decimal

    def __post_init__(self) -> None:
        """Validate and convert position data after initialization."""
        # Convert all financial values to Decimal for precision
        self.size = to_decimal(self.size)
        self.entry_price = round_price(to_decimal(self.entry_price))
        self.leverage = to_decimal(self.leverage)
        self.margin_used = round_amount(to_decimal(self.margin_used))

        # Validate position data
        if self.entry_price <= ZERO:
            raise ValidationError(f"Entry price must be positive, got {self.entry_price}")
        if self.leverage <= ZERO:
            raise ValidationError(f"Leverage must be positive, got {self.leverage}")
        if self.margin_used < ZERO:
            raise ValidationError(f"Margin used must be non-negative, got {self.margin_used}")

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL based on position type with precision.

        Args:
            current_price: Current market price

        Returns:
            Unrealized PnL as Decimal for precise calculation
        """
        if self.size == ZERO:
            return ZERO

        current_price_decimal = round_price(to_decimal(current_price))

        return calculate_pnl(
            entry_price=self.entry_price,
            exit_price=current_price_decimal,
            amount=self.size,
            position_type=self.position_type.value,
        )

    def is_liquidation_risk(self, current_price: Decimal, maintenance_margin_rate: Decimal) -> bool:
        """Check if position is at risk of liquidation with precise calculations.

        Args:
            current_price: Current market price
            maintenance_margin_rate: Maintenance margin rate (e.g., 0.05 for 5%)

        Returns:
            True if position is at liquidation risk
        """
        if self.size == ZERO:
            return False

        # Convert to Decimal for precise calculations
        current_price_decimal = round_price(to_decimal(current_price))
        margin_rate = to_decimal(maintenance_margin_rate)

        # Calculate unrealized PnL with precision
        unrealized_pnl = self.unrealized_pnl(current_price_decimal)

        # Position value at entry with precise calculation
        position_value = abs(float(self.size)) * float(self.entry_price)

        # Maintenance margin requirement
        maintenance_margin = round_amount(to_decimal(position_value) * margin_rate)

        # Available margin before liquidation
        available_margin = to_decimal(self.margin_used) - maintenance_margin

        # Check if losses exceed available margin
        # Liquidation occurs when losses reduce equity below maintenance margin
        return unrealized_pnl <= -available_margin

    def position_value(self, current_price: Decimal) -> Decimal:
        """Calculate current position value at given price with precision.

        Args:
            current_price: Current market price

        Returns:
            Position value as Decimal
        """
        current_price_decimal = round_price(to_decimal(current_price))
        return round_amount(to_decimal(abs(float(self.size))) * current_price_decimal)

    @classmethod
    def create_long(
        cls,
        symbol: Symbol,
        size: Decimal,
        entry_price: Decimal,
        leverage: Decimal = Decimal("1.0"),
        timestamp: datetime | None = None,
        trading_mode: TradingMode = TradingMode.SPOT,
    ) -> "Position":
        """Factory method to create a long position.

        Args:
            symbol: Trading symbol
            size: Position size (should be positive)
            entry_price: Entry price for the position
            leverage: Leverage multiplier (default 1.0)
            timestamp: Position creation time (default now)
            trading_mode: Trading mode for margin calculation

        Returns:
            New long Position instance
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Ensure positive size for long position
        position_size = abs(size)

        # Calculate margin used based on trading mode
        margin_used = cls._calculate_margin_used(
            float(position_size), float(entry_price), float(leverage), trading_mode
        )

        return cls(
            symbol=symbol,
            size=position_size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            position_type=PositionType.LONG,
            margin_used=to_decimal(margin_used),
        )

    @classmethod
    def create_short(
        cls,
        symbol: Symbol,
        size: Decimal,
        entry_price: Decimal,
        leverage: Decimal = Decimal("1.0"),
        timestamp: datetime | None = None,
        trading_mode: TradingMode = TradingMode.FUTURES,
    ) -> "Position":
        """Factory method to create a short position.

        Args:
            symbol: Trading symbol
            size: Position size (will be made negative)
            entry_price: Entry price for the position
            leverage: Leverage multiplier (default 1.0)
            timestamp: Position creation time (default now)
            trading_mode: Trading mode for margin calculation

        Returns:
            New short Position instance

        Raises:
            ValidationError: If trying to create short position in SPOT mode
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Validate short positions are allowed
        if trading_mode == TradingMode.SPOT:
            raise ValidationError("Short positions not allowed in SPOT trading mode")

        # Ensure negative size for short position
        position_size = -abs(size)

        # Calculate margin used based on trading mode
        margin_used = cls._calculate_margin_used(
            float(abs(size)), float(entry_price), float(leverage), trading_mode
        )

        return cls(
            symbol=symbol,
            size=to_decimal(position_size),
            entry_price=to_decimal(entry_price),
            leverage=to_decimal(leverage),
            timestamp=timestamp,
            position_type=PositionType.SHORT,
            margin_used=to_decimal(margin_used),
        )

    @classmethod
    def create_from_trade(
        cls,
        trade: "Trade",
        trading_mode: TradingMode = TradingMode.SPOT,
    ) -> "Position":
        """Factory method to create a position from a trade.

        Args:
            trade: Trade to convert to position
            trading_mode: Trading mode for margin calculation

        Returns:
            New Position instance based on trade
        """
        # Determine position type and size based on trade action
        if trade.action == ActionType.BUY:
            return cls.create_long(
                symbol=trade.symbol,
                size=to_decimal(trade.quantity),
                entry_price=to_decimal(trade.price),
                leverage=to_decimal(trade.leverage),
                timestamp=trade.timestamp,
                trading_mode=trading_mode,
            )
        else:  # SELL
            # Only create short position if not in SPOT mode
            if trading_mode == TradingMode.SPOT:
                raise ValidationError("Cannot create short position from SELL in SPOT mode")
            return cls.create_short(
                symbol=trade.symbol,
                size=to_decimal(trade.quantity),
                entry_price=to_decimal(trade.price),
                leverage=to_decimal(trade.leverage),
                timestamp=trade.timestamp,
                trading_mode=trading_mode,
            )

    @classmethod
    def _calculate_margin_used(
        cls, size: float, price: float, leverage: float, trading_mode: TradingMode
    ) -> float:
        """Calculate margin required for a position.

        Args:
            size: Position size (positive)
            price: Entry price
            leverage: Leverage multiplier
            trading_mode: Trading mode

        Returns:
            Margin amount required
        """
        notional_value = size * price

        if trading_mode == TradingMode.SPOT:
            # SPOT trading: full value is margin (no leverage effect on margin)
            return notional_value
        else:
            # FUTURES/MARGIN trading: margin is reduced by leverage
            return notional_value / leverage


@dataclass
class Trade:
    """Represents an executed trade."""

    timestamp: datetime
    symbol: Symbol
    action: ActionType
    quantity: float
    price: float
    leverage: float
    fee: float
    position_type: PositionType
    pnl: float
    margin_used: float

    def __post_init__(self) -> None:
        """Validate trade data after initialization."""
        if self.quantity <= 0:
            raise ValidationError(f"Quantity must be positive, got {self.quantity}")
        if self.price <= 0:
            raise ValidationError(f"Price must be positive, got {self.price}")
        if self.leverage <= 0:
            raise ValidationError(f"Leverage must be positive, got {self.leverage}")
        if self.fee < 0:
            raise ValidationError(f"Fee must be non-negative, got {self.fee}")
        if self.margin_used < 0:
            raise ValidationError(f"Margin used must be non-negative, got {self.margin_used}")

    def notional_value(self) -> float:
        """Calculate the notional value of the trade."""
        return abs(self.quantity) * self.price
