"""
Core type definitions and protocols.

This module defines shared types and protocols to prevent circular dependencies
between domain models while maintaining type safety.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from src.core.enums import PositionType, Symbol


class IPosition(Protocol):
    """Protocol defining the interface for Position objects.

    This protocol breaks the circular dependency between Portfolio and Position
    while maintaining type safety.
    """

    symbol: Symbol
    size: Decimal
    entry_price: Decimal
    leverage: Decimal
    timestamp: datetime
    position_type: PositionType
    margin_used: Decimal

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL at current price."""
        ...

    def is_liquidation_risk(self, current_price: Decimal, maintenance_margin_rate: Decimal) -> bool:
        """Check if position is at liquidation risk."""
        ...

    def position_value(self, current_price: Decimal) -> Decimal:
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
PriceDict = dict[Symbol, Decimal]
PositionDict = dict[Symbol, IPosition]
