"""
Trade domain model.
Optimized for high-performance backtesting with float operations.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.enums import ActionType, PositionType, Symbol
from src.core.exceptions.backtest import ValidationError


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
