"""
Core type definitions and protocols.

This module defines shared types and protocols to prevent circular dependencies
between domain models while maintaining type safety.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from src.core.enums import PositionType, Symbol
from src.core.types.financial import AmountFloat, LeverageFloat, PriceFloat


class IPosition(Protocol):
    """Protocol defining the interface for Position objects.

    This protocol breaks the circular dependency between Portfolio and Position
    while maintaining type safety.
    """

    symbol: Symbol
    size: AmountFloat
    entry_price: PriceFloat
    leverage: LeverageFloat
    timestamp: datetime
    position_type: PositionType
    margin_used: AmountFloat

    def unrealized_pnl(self, current_price: PriceFloat) -> Decimal:
        """Calculate unrealized PnL at current price."""
        ...

    def is_liquidation_risk(
        self, current_price: PriceFloat, maintenance_margin_rate: AmountFloat
    ) -> bool:
        """Check if position is at liquidation risk."""
        ...

    def position_value(self, current_price: PriceFloat) -> Decimal:
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
