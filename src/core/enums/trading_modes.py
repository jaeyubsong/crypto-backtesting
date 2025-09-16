"""
Trading mode enumerations.

This module defines the allowed trading modes for the backtesting platform.
"""

from enum import StrEnum


class TradingMode(StrEnum):
    """
    Allowed trading modes.

    Defines different types of trading with their respective characteristics
    and constraints.
    """

    SPOT = "spot"  # No leverage, actual asset ownership
    FUTURES = "futures"  # Perpetual futures contracts with leverage
    MARGIN = "margin"  # Spot trading with borrowed funds

    @classmethod
    def max_leverage(cls, mode: "TradingMode") -> float:
        """
        Get maximum allowed leverage for a trading mode.

        Args:
            mode: Trading mode enum value

        Returns:
            Maximum leverage as float
        """
        max_leverages = {
            cls.SPOT: 1.0,  # No leverage in spot trading
            cls.FUTURES: 125.0,  # High leverage for futures
            cls.MARGIN: 10.0,  # Moderate leverage for margin
        }
        return max_leverages[mode]

    @classmethod
    def min_leverage(cls, mode: "TradingMode") -> float:
        """
        Get minimum allowed leverage for a trading mode.

        Args:
            mode: Trading mode enum value

        Returns:
            Minimum leverage as float
        """
        # All modes have the same minimum leverage
        _ = mode  # Acknowledge the parameter
        return 1.0  # All modes start at 1x

    @classmethod
    def default_leverage(cls, mode: "TradingMode") -> float:
        """
        Get default leverage for a trading mode.

        Args:
            mode: Trading mode enum value

        Returns:
            Default leverage as float
        """
        defaults = {
            cls.SPOT: 1.0,
            cls.FUTURES: 10.0,  # Common default for futures
            cls.MARGIN: 3.0,  # Conservative default for margin
        }
        return defaults[mode]

    @classmethod
    def requires_margin(cls, mode: "TradingMode") -> bool:
        """
        Check if trading mode requires margin.

        Args:
            mode: Trading mode enum value

        Returns:
            True if margin is required
        """
        return mode in [cls.FUTURES, cls.MARGIN]

    @classmethod
    def validate_leverage(cls, mode: "TradingMode", leverage: float) -> bool:
        """
        Validate if leverage is allowed for a trading mode.

        Args:
            mode: Trading mode enum value
            leverage: Proposed leverage value

        Returns:
            True if leverage is valid for the mode
        """
        return cls.min_leverage(mode) <= leverage <= cls.max_leverage(mode)

    @classmethod
    def default_maintenance_margin_rate(cls, mode: "TradingMode") -> float:
        """
        Get default maintenance margin rate for a trading mode.

        Args:
            mode: Trading mode enum value

        Returns:
            Maintenance margin rate as float
        """
        rates = {
            cls.SPOT: 0.0,  # No margin requirement
            cls.FUTURES: 0.005,  # 0.5% typical for futures
            cls.MARGIN: 0.03,  # 3% typical for margin
        }
        return rates[mode]

    @property
    def allows_short(self) -> bool:
        """Check if trading mode allows short positions."""
        return self in [self.FUTURES, self.MARGIN]

    @property
    def has_liquidation(self) -> bool:
        """Check if trading mode has liquidation risk."""
        return self in [self.FUTURES, self.MARGIN]
