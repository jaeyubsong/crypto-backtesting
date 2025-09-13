"""
Position and Trade domain models.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import ValidationError


@dataclass
class Position:
    """Represents a trading position."""

    symbol: Symbol
    size: float
    entry_price: float
    leverage: float
    timestamp: datetime
    position_type: PositionType
    margin_used: float

    def __post_init__(self) -> None:
        """Validate position data after initialization."""
        if self.entry_price <= 0:
            raise ValidationError(f"Entry price must be positive, got {self.entry_price}")
        if self.leverage <= 0:
            raise ValidationError(f"Leverage must be positive, got {self.leverage}")
        if self.margin_used < 0:
            raise ValidationError(f"Margin used must be non-negative, got {self.margin_used}")

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL based on position type."""
        if self.size == 0:
            return 0.0

        if self.position_type == PositionType.LONG:
            return (current_price - self.entry_price) * abs(self.size)
        else:  # short position
            return (self.entry_price - current_price) * abs(self.size)

    def is_liquidation_risk(self, current_price: float, maintenance_margin_rate: float) -> bool:
        """Check if position is at risk of liquidation."""
        if self.size == 0:
            return False

        # Calculate unrealized loss
        unrealized_pnl = self.unrealized_pnl(current_price)

        # Position value at entry
        position_value = abs(self.size) * self.entry_price

        # Maintenance margin requirement
        maintenance_margin = position_value * maintenance_margin_rate

        # Available margin before liquidation
        available_margin = self.margin_used - maintenance_margin

        # Check if losses exceed available margin
        # Liquidation occurs when losses reduce equity below maintenance margin
        return unrealized_pnl <= -available_margin

    def position_value(self, current_price: float) -> float:
        """Calculate current position value at given price."""
        return abs(self.size) * current_price

    @classmethod
    def create_long(
        cls,
        symbol: Symbol,
        size: float,
        entry_price: float,
        leverage: float = 1.0,
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
        margin_used = cls._calculate_margin_used(position_size, entry_price, leverage, trading_mode)

        return cls(
            symbol=symbol,
            size=position_size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            position_type=PositionType.LONG,
            margin_used=margin_used,
        )

    @classmethod
    def create_short(
        cls,
        symbol: Symbol,
        size: float,
        entry_price: float,
        leverage: float = 1.0,
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
        margin_used = cls._calculate_margin_used(abs(size), entry_price, leverage, trading_mode)

        return cls(
            symbol=symbol,
            size=position_size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            position_type=PositionType.SHORT,
            margin_used=margin_used,
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
                size=trade.quantity,
                entry_price=trade.price,
                leverage=trade.leverage,
                timestamp=trade.timestamp,
                trading_mode=trading_mode,
            )
        else:  # SELL
            # Only create short position if not in SPOT mode
            if trading_mode == TradingMode.SPOT:
                raise ValidationError("Cannot create short position from SELL in SPOT mode")
            return cls.create_short(
                symbol=trade.symbol,
                size=trade.quantity,
                entry_price=trade.price,
                leverage=trade.leverage,
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
