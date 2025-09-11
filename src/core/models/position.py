"""
Position and Trade domain models.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.enums import ActionType, PositionType, Symbol
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

    def __post_init__(self):
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

    def __post_init__(self):
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
