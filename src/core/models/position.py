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
        # To be implemented in Phase 2
        pass

    def is_liquidation_risk(self, current_price: float, maintenance_margin_rate: float) -> bool:
        """Check if position is at risk of liquidation."""
        # To be implemented in Phase 2
        pass


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
