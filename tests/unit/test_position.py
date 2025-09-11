"""
Unit tests for Position domain model.
Following TDD approach - write failing tests first.
"""

from datetime import UTC, datetime

from src.core.enums import Symbol
from src.core.models.position import Position, Trade


class TestPosition:
    """Test suite for Position domain model."""

    def test_should_create_long_position_when_size_positive(self):
        """Test creation of long position with positive size."""
        timestamp = datetime.now(UTC)
        position = Position(
            symbol=Symbol.BTC,
            size=1.5,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=timestamp,
            position_type="long",
            margin_used=37500.0,  # 1.5 * 50000 / 2
        )

        assert position.symbol == Symbol.BTC
        assert position.size == 1.5
        assert position.entry_price == 50000.0
        assert position.leverage == 2.0
        assert position.timestamp == timestamp
        assert position.position_type == "long"
        assert position.margin_used == 37500.0

    def test_should_create_short_position_when_size_negative(self):
        """Test creation of short position with negative size."""
        timestamp = datetime.now(UTC)
        position = Position(
            symbol=Symbol.ETH,
            size=-2.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=timestamp,
            position_type="short",
            margin_used=2000.0,  # abs(-2.0 * 3000) / 3
        )

        assert position.symbol == Symbol.ETH
        assert position.size == -2.0
        assert position.entry_price == 3000.0
        assert position.leverage == 3.0
        assert position.position_type == "short"
        assert position.margin_used == 2000.0

    def test_should_calculate_unrealized_pnl_for_long_position(self):
        """Test unrealized PnL calculation for long position."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=25000.0,
        )

        # Price increases - profit for long
        unrealized_pnl = position.unrealized_pnl(52000.0)
        assert unrealized_pnl == 2000.0  # (52000 - 50000) * 1.0

        # Price decreases - loss for long
        unrealized_pnl = position.unrealized_pnl(48000.0)
        assert unrealized_pnl == -2000.0  # (48000 - 50000) * 1.0

    def test_should_calculate_unrealized_pnl_for_short_position(self):
        """Test unrealized PnL calculation for short position."""
        position = Position(
            symbol=Symbol.ETH,
            size=-1.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type="short",
            margin_used=1000.0,
        )

        # Price decreases - profit for short
        unrealized_pnl = position.unrealized_pnl(2800.0)
        assert unrealized_pnl == 200.0  # (3000 - 2800) * abs(-1.0)

        # Price increases - loss for short
        unrealized_pnl = position.unrealized_pnl(3200.0)
        assert unrealized_pnl == -200.0  # (3000 - 3200) * abs(-1.0)

    def test_should_detect_liquidation_risk_for_long_position(self):
        """Test liquidation risk detection for long position."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,  # High leverage
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=5000.0,  # 50000 / 10
        )

        maintenance_margin_rate = 0.005  # 0.5%

        # Safe price - no liquidation risk
        assert not position.is_liquidation_risk(49000.0, maintenance_margin_rate)

        # Dangerous price - liquidation risk
        # Liquidation price ≈ entry_price * (1 - 1/leverage + maintenance_margin_rate)
        # ≈ 50000 * (1 - 0.1 + 0.005) = 50000 * 0.905 = 45250
        assert position.is_liquidation_risk(45000.0, maintenance_margin_rate)

    def test_should_detect_liquidation_risk_for_short_position(self):
        """Test liquidation risk detection for short position."""
        position = Position(
            symbol=Symbol.ETH,
            size=-1.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type="short",
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

    def test_should_calculate_position_value_correctly(self):
        """Test position value calculation at different prices."""
        position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=1.0,  # No leverage for simplicity
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=100000.0,
        )

        # Position value at current price
        current_value = position.position_value(55000.0)
        assert current_value == 110000.0  # 2.0 * 55000

    def test_should_handle_zero_size_position(self):
        """Test handling of zero size position (no position)."""
        position = Position(
            symbol=Symbol.BTC,
            size=0.0,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=0.0,
        )

        assert position.unrealized_pnl(52000.0) == 0.0
        assert not position.is_liquidation_risk(45000.0, 0.005)


class TestTrade:
    """Test suite for Trade domain model."""

    def test_should_create_buy_trade_correctly(self):
        """Test creation of buy trade."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.BTC,
            action="buy",
            quantity=1.0,
            price=50000.0,
            leverage=2.0,
            fee=25.0,  # 0.05% of notional
            position_type="long",
            pnl=0.0,  # No PnL on opening trade
            margin_used=25000.0,
        )

        assert trade.timestamp == timestamp
        assert trade.symbol == Symbol.BTC
        assert trade.action == "buy"
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.leverage == 2.0
        assert trade.fee == 25.0
        assert trade.position_type == "long"
        assert trade.pnl == 0.0
        assert trade.margin_used == 25000.0

    def test_should_create_sell_trade_with_pnl(self):
        """Test creation of sell trade with realized PnL."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.ETH,
            action="sell",
            quantity=2.0,
            price=3200.0,
            leverage=1.0,
            fee=6.4,  # 0.1% of notional for spot
            position_type="long",
            pnl=400.0,  # Profit from closing position
            margin_used=0.0,  # Closing trade
        )

        assert trade.action == "sell"
        assert trade.pnl == 400.0
        assert trade.margin_used == 0.0

    def test_should_create_liquidation_trade(self):
        """Test creation of liquidation trade."""
        timestamp = datetime.now(UTC)
        trade = Trade(
            timestamp=timestamp,
            symbol=Symbol.BTC,
            action="liquidation",
            quantity=1.0,
            price=45000.0,
            leverage=10.0,
            fee=45.0,  # Higher liquidation fee
            position_type="long",
            pnl=-5000.0,  # Loss from liquidation
            margin_used=0.0,  # Position closed
        )

        assert trade.action == "liquidation"
        assert trade.pnl < 0  # Liquidation should result in loss
        assert trade.margin_used == 0.0

    def test_should_calculate_notional_value(self):
        """Test notional value calculation."""
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action="buy",
            quantity=1.5,
            price=50000.0,
            leverage=2.0,
            fee=37.5,
            position_type="long",
            pnl=0.0,
            margin_used=37500.0,
        )

        notional_value = trade.notional_value()
        assert notional_value == 75000.0  # 1.5 * 50000
