"""
Position and Trade domain models.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Represents a trading position."""

    symbol: str
    size: float
    entry_price: float
    leverage: float
    timestamp: datetime
    position_type: str
    margin_used: float

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL based on position type."""
        if self.size == 0:
            return 0.0

        if self.position_type == "long":
            return (current_price - self.entry_price) * abs(self.size)
        else:  # short position
            return (self.entry_price - current_price) * abs(self.size)

    def is_liquidation_risk(self, current_price: float, maintenance_margin_rate: float) -> bool:
        """Check if position is at risk of liquidation."""
        if self.size == 0:
            return False

        # Calculate unrealized loss
        unrealized_pnl = self.unrealized_pnl(current_price)

        # For liquidation: unrealized loss approaches initial margin
        # Liquidation occurs when: |unrealized_loss| >= margin_used - maintenance_margin
        position_value = abs(self.size) * self.entry_price
        maintenance_margin = position_value * maintenance_margin_rate

        # Available margin before liquidation
        available_margin = self.margin_used - maintenance_margin

        # Check if losses exceed available margin
        return unrealized_pnl <= -available_margin

    def position_value(self, current_price: float) -> float:
        """Calculate current position value at given price."""
        return abs(self.size) * current_price


@dataclass
class Trade:
    """Represents an executed trade."""

    timestamp: datetime
    symbol: str
    action: str
    quantity: float
    price: float
    leverage: float
    fee: float
    position_type: str
    pnl: float
    margin_used: float

    def notional_value(self) -> float:
        """Calculate the notional value of the trade."""
        return abs(self.quantity) * self.price
