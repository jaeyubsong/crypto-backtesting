"""
Unit tests for Position factory methods.
Following TDD approach - testing the new factory pattern methods.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import ValidationError
from src.core.models.position import Position
from src.core.models.trade import Trade


class TestPositionFactoryMethods:
    """Test suite for Position factory methods."""

    def test_should_create_long_position_with_factory_method(self) -> None:
        """Test creating a long position using factory method."""
        # Arrange
        symbol = Symbol.BTC
        size = 1.5
        entry_price = 50000.0
        leverage = 2.0
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Act
        position = Position.create_long(
            symbol=symbol,
            size=size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            trading_mode=TradingMode.FUTURES,
        )

        # Assert
        assert position.symbol == symbol
        assert position.size == size  # Should be positive
        assert position.entry_price == entry_price
        assert position.leverage == leverage
        assert position.timestamp == timestamp
        assert position.position_type == PositionType.LONG
        # Margin should be notional_value / leverage for futures
        assert position.margin_used == (size * entry_price) / leverage

    def test_should_create_long_position_with_default_timestamp(self) -> None:
        """Test factory method uses current time when timestamp not provided."""
        # Act
        position = Position.create_long(
            symbol=Symbol.ETH,
            size=2.0,
            entry_price=3000.0,
            leverage=1.0,
            trading_mode=TradingMode.SPOT,
        )

        # Assert
        assert position.timestamp is not None
        assert isinstance(position.timestamp, datetime)

    def test_should_create_long_position_handles_negative_size(self) -> None:
        """Test factory method converts negative size to positive for long position."""
        # Act
        position = Position.create_long(
            symbol=Symbol.BTC,
            size=-1.0,  # Negative input
            entry_price=50000.0,
        )

        # Assert
        assert position.size == 1.0  # Should be made positive
        assert position.position_type == PositionType.LONG

    def test_should_create_short_position_with_factory_method(self) -> None:
        """Test creating a short position using factory method."""
        # Arrange
        symbol = Symbol.BTC
        size = 1.5
        entry_price = 50000.0
        leverage = 3.0
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Act
        position = Position.create_short(
            symbol=symbol,
            size=size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            trading_mode=TradingMode.FUTURES,
        )

        # Assert
        assert position.symbol == symbol
        assert position.size == -size  # Should be negative for short
        assert position.entry_price == entry_price
        assert position.leverage == leverage
        assert position.timestamp == timestamp
        assert position.position_type == PositionType.SHORT
        # Margin calculation should use absolute size
        assert position.margin_used == (size * entry_price) / leverage

    def test_should_reject_short_position_in_spot_mode(self) -> None:
        """Test that short position creation fails in SPOT mode."""
        # Act & Assert
        with pytest.raises(
            ValidationError, match="Short positions not allowed in SPOT trading mode"
        ):
            Position.create_short(
                symbol=Symbol.BTC,
                size=1.0,
                entry_price=50000.0,
                trading_mode=TradingMode.SPOT,
            )

    def test_should_create_position_from_buy_trade(self) -> None:
        """Test creating position from a BUY trade."""
        # Arrange
        trade = Trade(
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            symbol=Symbol.ETH,
            action=ActionType.BUY,
            quantity=2.0,
            price=3000.0,
            leverage=2.0,
            fee=12.0,
            position_type=PositionType.LONG,
            pnl=0.0,
            margin_used=3000.0,
        )

        # Act
        position = Position.create_from_trade(trade, TradingMode.FUTURES)

        # Assert
        assert position.symbol == trade.symbol
        assert position.size == trade.quantity  # Positive for long
        assert position.entry_price == trade.price
        assert position.leverage == trade.leverage
        assert position.timestamp == trade.timestamp
        assert position.position_type == PositionType.LONG

    def test_should_create_position_from_sell_trade_futures(self) -> None:
        """Test creating short position from SELL trade in futures mode."""
        # Arrange
        trade = Trade(
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            symbol=Symbol.BTC,
            action=ActionType.SELL,
            quantity=1.0,
            price=50000.0,
            leverage=2.0,
            fee=50.0,
            position_type=PositionType.SHORT,
            pnl=0.0,
            margin_used=25000.0,
        )

        # Act
        position = Position.create_from_trade(trade, TradingMode.FUTURES)

        # Assert
        assert position.symbol == trade.symbol
        assert position.size == -trade.quantity  # Negative for short
        assert position.entry_price == trade.price
        assert position.leverage == trade.leverage
        assert position.timestamp == trade.timestamp
        assert position.position_type == PositionType.SHORT

    def test_should_reject_short_from_sell_trade_in_spot_mode(self) -> None:
        """Test that creating position from SELL trade fails in SPOT mode."""
        # Arrange
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.SELL,
            quantity=1.0,
            price=50000.0,
            leverage=1.0,
            fee=50.0,
            position_type=PositionType.LONG,
            pnl=1000.0,
            margin_used=0.0,
        )

        # Act & Assert
        with pytest.raises(
            ValidationError, match="Cannot create short position from SELL in SPOT mode"
        ):
            Position.create_from_trade(trade, TradingMode.SPOT)

    def test_should_calculate_margin_correctly_for_spot_trading(self) -> None:
        """Test margin calculation for SPOT trading mode."""
        # Act
        position = Position.create_long(
            symbol=Symbol.ETH,
            size=2.0,
            entry_price=3000.0,
            leverage=1.0,  # Leverage ignored in SPOT
            trading_mode=TradingMode.SPOT,
        )

        # Assert
        # In SPOT mode, margin_used = full notional value regardless of leverage
        expected_margin = 2.0 * 3000.0  # size * price
        assert position.margin_used == expected_margin

    def test_should_calculate_margin_correctly_for_futures_trading(self) -> None:
        """Test margin calculation for FUTURES trading mode."""
        # Act
        position = Position.create_long(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=5.0,
            trading_mode=TradingMode.FUTURES,
        )

        # Assert
        # In FUTURES mode, margin_used = notional_value / leverage
        expected_margin = (1.0 * 50000.0) / 5.0  # (size * price) / leverage
        assert position.margin_used == expected_margin

    def test_should_handle_high_leverage_in_margin_calculation(self) -> None:
        """Test margin calculation with high leverage."""
        # Act
        position = Position.create_short(
            symbol=Symbol.BTC,
            size=0.1,
            entry_price=50000.0,
            leverage=100.0,
            trading_mode=TradingMode.FUTURES,
        )

        # Assert
        expected_margin = (0.1 * 50000.0) / 100.0  # Small margin due to high leverage
        assert position.margin_used == expected_margin
        assert position.margin_used == 50.0
