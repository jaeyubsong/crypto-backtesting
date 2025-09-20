"""
Unit tests for Position domain model.
Following TDD approach - write failing tests first.
Enhanced to test float precision for financial calculations.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import ActionType, PositionType, Symbol
from src.core.exceptions.backtest import ValidationError
from src.core.models.position import Position
from src.core.models.trade import Trade


class TestPosition:
    """Test suite for Position domain model."""

    def test_should_create_long_position_when_size_positive(self) -> None:
        """Test creation of long position with positive size."""
        timestamp = datetime.now(UTC)
        position = Position(
            symbol=Symbol.BTC,
            size=1.5,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=timestamp,
            position_type=PositionType.LONG,
            margin_used=37500.0,  # 1.5 * 50000 / 2
        )

        assert position.symbol == Symbol.BTC
        assert position.size == 1.5
        assert position.entry_price == 50000.0
        assert position.leverage == 2.0
        assert position.timestamp == timestamp
        assert position.position_type == PositionType.LONG
        assert position.margin_used == 37500.0

    def test_should_create_short_position_when_size_negative(self) -> None:
        """Test creation of short position with negative size."""
        timestamp = datetime.now(UTC)
        position = Position(
            symbol=Symbol.ETH,
            size=-2.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=timestamp,
            position_type=PositionType.SHORT,
            margin_used=2000.0,  # abs(-2.0 * 3000) / 3
        )

        assert position.symbol == Symbol.ETH
        assert position.size == -2.0
        assert position.entry_price == 3000.0
        assert position.leverage == 3.0
        assert position.position_type == PositionType.SHORT
        assert position.margin_used == 2000.0

    def test_should_calculate_unrealized_pnl_for_long_position(self) -> None:
        """Test unrealized PnL calculation for long position."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        # Price increases - profit for long
        unrealized_pnl = position.unrealized_pnl(52000.0)
        assert unrealized_pnl == float("2000.00000000")  # (52000 - 50000) * 1.0

        # Price decreases - loss for long
        unrealized_pnl = position.unrealized_pnl(48000.0)
        assert unrealized_pnl == float("-2000.00000000")  # (48000 - 50000) * 1.0

    def test_should_calculate_unrealized_pnl_for_short_position(self) -> None:
        """Test unrealized PnL calculation for short position."""
        position = Position(
            symbol=Symbol.ETH,
            size=-1.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=1000.0,
        )

        # Price decreases - profit for short
        unrealized_pnl = position.unrealized_pnl(2800.0)
        assert unrealized_pnl == float("200.00000000")  # (3000 - 2800) * abs(-1.0)

        # Price increases - loss for short
        unrealized_pnl = position.unrealized_pnl(3200.0)
        assert unrealized_pnl == float("-200.00000000")  # (3000 - 3200) * abs(-1.0)

    def test_should_detect_liquidation_risk_for_long_position(self) -> None:
        """Test liquidation risk detection for long position."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,  # High leverage
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,  # 50000 / 10
        )

        maintenance_margin_rate = 0.005  # 0.5%

        # Safe price - no liquidation risk
        assert not position.is_liquidation_risk(49000.0, maintenance_margin_rate)

        # Dangerous price - liquidation risk
        # Liquidation price ≈ entry_price * (1 - 1/leverage + maintenance_margin_rate)
        # ≈ 50000 * (1 - 0.1 + 0.005) = 50000 * 0.905 = 45250
        assert position.is_liquidation_risk(45000.0, maintenance_margin_rate)

    def test_should_detect_liquidation_risk_for_short_position(self) -> None:
        """Test liquidation risk detection for short position."""
        position = Position(
            symbol=Symbol.ETH,
            size=-1.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=600.0,  # 3000 / 5
        )

        maintenance_margin_rate = 0.01  # 1%

        # Safe price - no liquidation risk
        assert not position.is_liquidation_risk(2800.0, maintenance_margin_rate)

        # Dangerous price - liquidation risk
        # For short: liquidation when price increases too much
        # Liquidation price ≈ entry_price * (1 + 1/leverage - maintenance_margin_rate)
        # ≈ 3000 * (1 + 0.2 - 0.01) = 3000 * 1.19 = 3570
        assert position.is_liquidation_risk(3600.0, maintenance_margin_rate)

    def test_should_calculate_position_value_correctly(self) -> None:
        """Test position value calculation at different prices."""
        position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=1.0,  # No leverage for simplicity
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=100000.0,
        )

        # Position value at current price
        current_value = position.position_value(55000.0)
        assert current_value == 110000.0  # 2.0 * 55000

    def test_should_handle_zero_size_position(self) -> None:
        """Test handling of zero size position (no position)."""
        position = Position(
            symbol=Symbol.BTC,
            size=0.0,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=0.0,
        )

        assert position.unrealized_pnl(52000.0) == 0.0
        assert not position.is_liquidation_risk(45000.0, 0.005)


class TestTrade:
    """Test suite for Trade domain model."""

    def test_should_create_buy_trade_correctly(self) -> None:
        """Test creation of buy trade."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.BTC,
            action=ActionType.BUY,
            quantity=1.0,
            price=50000.0,
            leverage=2.0,
            fee=25.0,  # 0.05% of notional
            position_type=PositionType.LONG,
            pnl=0.0,  # No PnL on opening trade
            margin_used=25000.0,
        )

        assert trade.timestamp == timestamp
        assert trade.symbol == Symbol.BTC
        assert trade.action == ActionType.BUY
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.leverage == 2.0
        assert trade.fee == 25.0
        assert trade.position_type == PositionType.LONG
        assert trade.pnl == 0.0
        assert trade.margin_used == 25000.0

    def test_should_create_sell_trade_with_pnl(self) -> None:
        """Test creation of sell trade with realized PnL."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.ETH,
            action=ActionType.SELL,
            quantity=2.0,
            price=3200.0,
            leverage=1.0,
            fee=6.4,  # 0.1% of notional for spot
            position_type=PositionType.LONG,
            pnl=400.0,  # Profit from closing position
            margin_used=0.0,  # Closing trade
        )

        assert trade.action == ActionType.SELL
        assert trade.pnl == 400.0
        assert trade.margin_used == 0.0

    def test_should_create_liquidation_trade(self) -> None:
        """Test creation of liquidation trade."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.BTC,
            action=ActionType.LIQUIDATION,
            quantity=1.0,
            price=45000.0,
            leverage=10.0,
            fee=45.0,  # Higher liquidation fee
            position_type=PositionType.LONG,
            pnl=-5000.0,  # Loss from liquidation
            margin_used=0.0,  # Position closed
        )

        assert trade.action == ActionType.LIQUIDATION
        assert trade.pnl < 0  # Liquidation should result in loss
        assert trade.margin_used == 0.0

    def test_should_calculate_notional_value(self) -> None:
        """Test notional value calculation."""
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.BUY,
            quantity=1.5,
            price=50000.0,
            leverage=2.0,
            fee=37.5,
            position_type=PositionType.LONG,
            pnl=0.0,
            margin_used=37500.0,
        )

        notional_value = trade.notional_value()
        assert notional_value == 75000.0  # 1.5 * 50000

    def test_should_validate_position_inputs(self) -> None:
        """Test that Position validates inputs correctly."""
        # Invalid entry price
        with pytest.raises(ValidationError, match="Entry price must be positive"):
            Position(
                symbol=Symbol.BTC,
                size=1.0,
                entry_price=-50000.0,  # Invalid
                leverage=2.0,
                timestamp=datetime.now(UTC),
                position_type=PositionType.LONG,
                margin_used=25000.0,
            )

        # Invalid leverage
        with pytest.raises(ValidationError, match="Leverage must be positive"):
            Position(
                symbol=Symbol.BTC,
                size=1.0,
                entry_price=50000.0,
                leverage=0.0,  # Invalid
                timestamp=datetime.now(UTC),
                position_type=PositionType.LONG,
                margin_used=25000.0,
            )

    def test_should_validate_trade_inputs(self) -> None:
        """Test that Trade validates inputs correctly."""
        # Invalid quantity
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            Trade(
                timestamp=datetime.now(UTC),
                symbol=Symbol.BTC,
                action=ActionType.BUY,
                quantity=0.0,  # Invalid
                price=50000.0,
                leverage=2.0,
                fee=25.0,
                position_type=PositionType.LONG,
                pnl=0.0,
                margin_used=25000.0,
            )

        # Invalid price
        with pytest.raises(ValidationError, match="Price must be positive"):
            Trade(
                timestamp=datetime.now(UTC),
                symbol=Symbol.BTC,
                action=ActionType.BUY,
                quantity=1.0,
                price=-50000.0,  # Invalid
                leverage=2.0,
                fee=25.0,
                position_type=PositionType.LONG,
                pnl=0.0,
                margin_used=25000.0,
            )
