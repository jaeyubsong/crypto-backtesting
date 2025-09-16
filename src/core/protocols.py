"""
Core type definitions and protocols.

This module defines shared types and protocols to prevent circular dependencies
between domain models while maintaining type safety.
"""

from datetime import datetime
from typing import Protocol

from src.core.enums import PositionType, Symbol


class IPosition(Protocol):
    """Protocol defining the interface for Position objects.

    This protocol breaks the circular dependency between Portfolio and Position
    while maintaining type safety.
    """

    symbol: Symbol
    size: float
    entry_price: float
    leverage: float
    timestamp: datetime
    position_type: PositionType
    margin_used: float

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL at current price."""
        ...

    def is_liquidation_risk(self, current_price: float, maintenance_margin_rate: float) -> bool:
        """Check if position is at liquidation risk."""
        ...

    def position_value(self, current_price: float) -> float:
        """Calculate position value at current price."""
        ...


class ITrade(Protocol):
    """Protocol defining the interface for Trade objects.

    This protocol provides type safety for Trade objects without
    creating circular dependencies.
    """

    timestamp: datetime
    symbol: Symbol
    quantity: float
    price: float
    leverage: float
    fee: float
    pnl: float
    margin_used: float

    def notional_value(self) -> float:
        """Calculate notional value of the trade."""
        ...


# Type aliases for commonly used types
PriceDict = dict[Symbol, float]
PositionDict = dict[Symbol, IPosition]
