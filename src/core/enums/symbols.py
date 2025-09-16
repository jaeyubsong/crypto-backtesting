"""
Trading symbol enumerations.

This module defines the allowed trading symbols for the backtesting platform.
"""

from enum import StrEnum


class Symbol(StrEnum):
    """
    Allowed trading symbols.

    Following the Binance convention of base+quote currency pairs.
    Currently supporting major cryptocurrencies against USDT.
    """

    # Major cryptocurrencies
    BTC = "BTCUSDT"
    ETH = "ETHUSDT"

    @classmethod
    def get_base_currency(cls, symbol: "Symbol") -> str:
        """
        Extract base currency from symbol.

        Args:
            symbol: Trading symbol enum value

        Returns:
            Base currency code (e.g., "BTC", "ETH")
        """
        return symbol.value[:-4]  # Remove USDT suffix

    @classmethod
    def get_quote_currency(cls, symbol: "Symbol") -> str:
        """
        Extract quote currency from symbol.

        Args:
            symbol: Trading symbol enum value

        Returns:
            Quote currency code (currently always "USDT")
        """
        return symbol.value[-4:]  # Last 4 characters (USDT)

    @classmethod
    def from_string(cls, value: str) -> "Symbol":
        """
        Convert string to Symbol enum, with case-insensitive matching.

        Args:
            value: String representation of symbol

        Returns:
            Corresponding Symbol enum value

        Raises:
            ValueError: If symbol is not supported
        """
        value_upper = value.upper()

        # Handle both short form (BTC) and full form (BTCUSDT)
        if value_upper in ["BTC", "BTCUSDT"]:
            return cls.BTC
        elif value_upper in ["ETH", "ETHUSDT"]:
            return cls.ETH
        else:
            raise ValueError(
                f"Unsupported symbol: {value}. "
                f"Supported symbols: {', '.join([s.value for s in cls])}"
            )
