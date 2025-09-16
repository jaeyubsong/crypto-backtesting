"""
Trading timeframe enumerations.

This module defines the allowed timeframes for candlestick data.
"""

from enum import StrEnum


class Timeframe(StrEnum):
    """
    Allowed trading timeframes.

    Following standard trading conventions for candlestick intervals.
    Supports minute, hour, day, and week timeframes.
    """

    # Minute intervals
    M1 = "1m"  # 1 minute
    M5 = "5m"  # 5 minutes
    M15 = "15m"  # 15 minutes
    M30 = "30m"  # 30 minutes

    # Hour intervals
    H1 = "1h"  # 1 hour
    H4 = "4h"  # 4 hours

    # Day/Week intervals
    D1 = "1d"  # 1 day
    W1 = "1w"  # 1 week

    @classmethod
    def to_seconds(cls, timeframe: "Timeframe") -> int:
        """
        Convert timeframe to seconds.

        Args:
            timeframe: Timeframe enum value

        Returns:
            Number of seconds in the timeframe
        """
        conversions = {
            cls.M1: 60,
            cls.M5: 300,
            cls.M15: 900,
            cls.M30: 1800,
            cls.H1: 3600,
            cls.H4: 14400,
            cls.D1: 86400,
            cls.W1: 604800,
        }
        return conversions[timeframe]

    @classmethod
    def to_minutes(cls, timeframe: "Timeframe") -> int:
        """
        Convert timeframe to minutes.

        Args:
            timeframe: Timeframe enum value

        Returns:
            Number of minutes in the timeframe
        """
        return cls.to_seconds(timeframe) // 60

    @classmethod
    def from_string(cls, value: str) -> "Timeframe":
        """
        Convert string to Timeframe enum.

        Args:
            value: String representation of timeframe

        Returns:
            Corresponding Timeframe enum value

        Raises:
            ValueError: If timeframe is not supported
        """
        value_lower = value.lower()

        # Try direct match
        for tf in cls:
            if tf.value == value_lower:
                return tf

        raise ValueError(
            f"Unsupported timeframe: {value}. "
            f"Supported timeframes: {', '.join([tf.value for tf in cls])}"
        )

    @property
    def is_intraday(self) -> bool:
        """Check if timeframe is intraday (less than 1 day)."""
        return self in [self.M1, self.M5, self.M15, self.M30, self.H1, self.H4]
