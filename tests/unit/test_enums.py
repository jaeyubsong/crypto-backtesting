"""
Unit tests for enum types.
Testing all enum methods and properties.
"""

import pytest

from src.core.enums import (
    ActionType,
    PositionType,
    Symbol,
    Timeframe,
    TradingMode,
)


class TestSymbolEnum:
    """Tests for Symbol enum."""

    def test_should_have_correct_values(self) -> None:
        """Test that Symbol enum has correct values."""
        assert Symbol.BTC.value == "BTCUSDT"
        assert Symbol.ETH.value == "ETHUSDT"

    def test_should_convert_from_string_case_insensitive(self) -> None:
        """Test from_string method with various cases."""
        assert Symbol.from_string("BTC") == Symbol.BTC
        assert Symbol.from_string("btc") == Symbol.BTC
        assert Symbol.from_string("BTCUSDT") == Symbol.BTC
        assert Symbol.from_string("btcusdt") == Symbol.BTC

        assert Symbol.from_string("ETH") == Symbol.ETH
        assert Symbol.from_string("eth") == Symbol.ETH
        assert Symbol.from_string("ETHUSDT") == Symbol.ETH
        assert Symbol.from_string("ethusdt") == Symbol.ETH

    def test_should_raise_error_for_invalid_symbol(self) -> None:
        """Test that from_string raises error for invalid symbols."""
        with pytest.raises(ValueError, match="Unsupported symbol"):
            Symbol.from_string("DOGE")

        with pytest.raises(ValueError, match="Unsupported symbol"):
            Symbol.from_string("")

        with pytest.raises(ValueError, match="Unsupported symbol"):
            Symbol.from_string("XRP")

    def test_should_get_base_currency(self) -> None:
        """Test getting base currency from symbol."""
        assert Symbol.get_base_currency(Symbol.BTC) == "BTC"
        assert Symbol.get_base_currency(Symbol.ETH) == "ETH"

    def test_should_get_quote_currency(self) -> None:
        """Test getting quote currency from symbol."""
        assert Symbol.get_quote_currency(Symbol.BTC) == "USDT"
        assert Symbol.get_quote_currency(Symbol.ETH) == "USDT"


class TestTimeframeEnum:
    """Tests for Timeframe enum."""

    def test_should_have_correct_values(self) -> None:
        """Test that Timeframe enum has correct values."""
        assert Timeframe.M1.value == "1m"
        assert Timeframe.M5.value == "5m"
        assert Timeframe.H1.value == "1h"
        assert Timeframe.D1.value == "1d"
        assert Timeframe.W1.value == "1w"

    def test_should_convert_to_seconds(self) -> None:
        """Test conversion to seconds."""
        assert Timeframe.to_seconds(Timeframe.M1) == 60
        assert Timeframe.to_seconds(Timeframe.M5) == 300
        assert Timeframe.to_seconds(Timeframe.M15) == 900
        assert Timeframe.to_seconds(Timeframe.M30) == 1800
        assert Timeframe.to_seconds(Timeframe.H1) == 3600
        assert Timeframe.to_seconds(Timeframe.H4) == 14400
        assert Timeframe.to_seconds(Timeframe.D1) == 86400
        assert Timeframe.to_seconds(Timeframe.W1) == 604800

    def test_should_convert_to_minutes(self) -> None:
        """Test conversion to minutes."""
        assert Timeframe.to_minutes(Timeframe.M1) == 1
        assert Timeframe.to_minutes(Timeframe.M5) == 5
        assert Timeframe.to_minutes(Timeframe.M15) == 15
        assert Timeframe.to_minutes(Timeframe.M30) == 30
        assert Timeframe.to_minutes(Timeframe.H1) == 60
        assert Timeframe.to_minutes(Timeframe.H4) == 240
        assert Timeframe.to_minutes(Timeframe.D1) == 1440
        assert Timeframe.to_minutes(Timeframe.W1) == 10080

    def test_should_convert_from_string(self) -> None:
        """Test from_string method."""
        assert Timeframe.from_string("1m") == Timeframe.M1
        assert Timeframe.from_string("5m") == Timeframe.M5
        assert Timeframe.from_string("1h") == Timeframe.H1
        assert Timeframe.from_string("1d") == Timeframe.D1
        assert Timeframe.from_string("1w") == Timeframe.W1

    def test_should_raise_error_for_invalid_timeframe(self) -> None:
        """Test that from_string raises error for invalid timeframes."""
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            Timeframe.from_string("2m")

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            Timeframe.from_string("10s")

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            Timeframe.from_string("")

    def test_should_check_if_intraday(self) -> None:
        """Test is_intraday property."""
        assert Timeframe.M1.is_intraday is True
        assert Timeframe.M5.is_intraday is True
        assert Timeframe.M15.is_intraday is True
        assert Timeframe.M30.is_intraday is True
        assert Timeframe.H1.is_intraday is True
        assert Timeframe.H4.is_intraday is True
        assert Timeframe.D1.is_intraday is False
        assert Timeframe.W1.is_intraday is False


class TestTradingModeEnum:
    """Tests for TradingMode enum."""

    def test_should_have_correct_values(self) -> None:
        """Test that TradingMode enum has correct values."""
        assert TradingMode.SPOT.value == "spot"
        assert TradingMode.FUTURES.value == "futures"
        assert TradingMode.MARGIN.value == "margin"

    def test_should_validate_leverage_for_spot(self) -> None:
        """Test leverage validation for SPOT mode."""
        assert TradingMode.validate_leverage(TradingMode.SPOT, 1.0) is True
        assert TradingMode.validate_leverage(TradingMode.SPOT, 2.0) is False
        assert TradingMode.validate_leverage(TradingMode.SPOT, 0.5) is False
        assert TradingMode.validate_leverage(TradingMode.SPOT, 10.0) is False

    def test_should_validate_leverage_for_futures(self) -> None:
        """Test leverage validation for FUTURES mode."""
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 1.0) is True
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 10.0) is True
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 125.0) is True
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 0.5) is False
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 126.0) is False
        assert TradingMode.validate_leverage(TradingMode.FUTURES, 200.0) is False

    def test_should_validate_leverage_for_margin(self) -> None:
        """Test leverage validation for MARGIN mode."""
        assert TradingMode.validate_leverage(TradingMode.MARGIN, 1.0) is True
        assert TradingMode.validate_leverage(TradingMode.MARGIN, 5.0) is True
        assert TradingMode.validate_leverage(TradingMode.MARGIN, 10.0) is True
        assert TradingMode.validate_leverage(TradingMode.MARGIN, 0.5) is False
        assert TradingMode.validate_leverage(TradingMode.MARGIN, 11.0) is False

    def test_should_get_default_leverage(self) -> None:
        """Test getting default leverage for each mode."""
        assert TradingMode.default_leverage(TradingMode.SPOT) == 1.0
        assert TradingMode.default_leverage(TradingMode.FUTURES) == 10.0
        assert TradingMode.default_leverage(TradingMode.MARGIN) == 3.0

    def test_should_get_max_leverage(self) -> None:
        """Test getting max leverage for each mode."""
        assert TradingMode.max_leverage(TradingMode.SPOT) == 1.0
        assert TradingMode.max_leverage(TradingMode.FUTURES) == 125.0
        assert TradingMode.max_leverage(TradingMode.MARGIN) == 10.0

    def test_should_check_if_requires_margin(self) -> None:
        """Test if trading mode requires margin."""
        assert TradingMode.requires_margin(TradingMode.SPOT) is False
        assert TradingMode.requires_margin(TradingMode.FUTURES) is True
        assert TradingMode.requires_margin(TradingMode.MARGIN) is True

    def test_should_get_default_maintenance_margin_rate(self) -> None:
        """Test getting default maintenance margin rate."""
        assert TradingMode.default_maintenance_margin_rate(TradingMode.SPOT) == 0.0
        assert TradingMode.default_maintenance_margin_rate(TradingMode.FUTURES) == 0.005  # 0.5%
        assert TradingMode.default_maintenance_margin_rate(TradingMode.MARGIN) == 0.03  # 3%


class TestPositionTypeEnum:
    """Tests for PositionType enum."""

    def test_should_have_correct_values(self) -> None:
        """Test that PositionType enum has correct values."""
        assert PositionType.LONG.value == "long"
        assert PositionType.SHORT.value == "short"

    def test_should_check_if_long(self) -> None:
        """Test is_long property."""
        assert PositionType.LONG.is_long is True
        assert PositionType.SHORT.is_long is False

    def test_should_check_if_short(self) -> None:
        """Test is_short property."""
        assert PositionType.LONG.is_short is False
        assert PositionType.SHORT.is_short is True

    def test_should_get_opposite_position_type(self) -> None:
        """Test opposite method."""
        assert PositionType.LONG.opposite() == PositionType.SHORT
        assert PositionType.SHORT.opposite() == PositionType.LONG


class TestActionTypeEnum:
    """Tests for ActionType enum."""

    def test_should_have_correct_values(self) -> None:
        """Test that ActionType enum has correct values."""
        assert ActionType.BUY.value == "buy"
        assert ActionType.SELL.value == "sell"
        assert ActionType.LIQUIDATION.value == "liquidation"

    def test_should_check_if_opening(self) -> None:
        """Test is_opening property."""
        assert ActionType.BUY.is_opening is True
        assert ActionType.SELL.is_opening is True
        assert ActionType.LIQUIDATION.is_opening is False

    def test_should_check_if_closing(self) -> None:
        """Test is_closing property."""
        assert ActionType.BUY.is_closing is True
        assert ActionType.SELL.is_closing is True
        assert ActionType.LIQUIDATION.is_closing is True

    def test_should_check_if_forced(self) -> None:
        """Test is_forced property."""
        assert ActionType.BUY.is_forced is False
        assert ActionType.SELL.is_forced is False
        assert ActionType.LIQUIDATION.is_forced is True

    def test_should_get_created_position_type(self) -> None:
        """Test creates_position_type method."""
        assert ActionType.BUY.creates_position_type() == PositionType.LONG
        assert ActionType.SELL.creates_position_type() == PositionType.SHORT
        assert ActionType.LIQUIDATION.creates_position_type() is None
