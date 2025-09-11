"""
Position and action type enumerations.

This module defines the allowed position types and trade actions.
"""

from enum import StrEnum


class PositionType(StrEnum):
    """
    Allowed position types.

    Defines whether a position is long or short.
    """

    LONG = "long"
    SHORT = "short"

    @property
    def is_long(self) -> bool:
        """Check if position type is long."""
        return self == self.LONG

    @property
    def is_short(self) -> bool:
        """Check if position type is short."""
        return self == self.SHORT

    def opposite(self) -> "PositionType":
        """Get the opposite position type."""
        return self.SHORT if self.is_long else self.LONG  # type: ignore[return-value]


class ActionType(StrEnum):
    """
    Allowed trade actions.

    Defines the type of trade action executed.
    """

    BUY = "buy"
    SELL = "sell"
    LIQUIDATION = "liquidation"

    @property
    def is_opening(self) -> bool:
        """Check if action opens a new position."""
        return self in [self.BUY, self.SELL]

    @property
    def is_closing(self) -> bool:
        """Check if action closes a position."""
        return self in [self.SELL, self.BUY, self.LIQUIDATION]

    @property
    def is_forced(self) -> bool:
        """Check if action is forced (liquidation)."""
        return self == self.LIQUIDATION

    def creates_position_type(self) -> PositionType | None:
        """Get the position type created by this action."""
        if self == self.BUY:
            return PositionType.LONG
        elif self == self.SELL:
            return PositionType.SHORT
        return None  # Liquidation doesn't create positions
