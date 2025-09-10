"""
Unit tests for Portfolio domain model.
Following TDD approach - write failing tests first.
"""

from datetime import UTC, datetime

from src.core.models.portfolio import Portfolio
from src.core.models.position import Position, Trade


class TestPortfolio:
    """Test suite for Portfolio domain model."""

    def test_should_create_portfolio_with_initial_capital(self):
        """Test portfolio creation with initial capital."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=10000.0, positions={}, trades=[], portfolio_history=[]
        )

        assert portfolio.initial_capital == 10000.0
        assert portfolio.cash == 10000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.trades) == 0
        assert len(portfolio.portfolio_history) == 0

    def test_should_calculate_total_portfolio_value_with_no_positions(self):
        """Test portfolio value calculation with no positions."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=10000.0, positions={}, trades=[], portfolio_history=[]
        )

        current_prices = {"BTCUSDT": 50000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        assert portfolio_value == 10000.0  # Only cash

    def test_should_calculate_total_portfolio_value_with_positions(self):
        """Test portfolio value calculation with open positions."""
        btc_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=24000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=26000.0,  # 50000 - 24000 margin used
            positions={"BTCUSDT": btc_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {"BTCUSDT": 52000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # Cash + unrealized PnL
        # 26000 + ((52000 - 48000) * 1.0) = 26000 + 4000 = 30000
        assert portfolio_value == 30000.0

    def test_should_calculate_available_margin(self):
        """Test available margin calculation."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=5000.0, positions={}, trades=[], portfolio_history=[]
        )

        available_margin = portfolio.available_margin()
        assert available_margin == 5000.0  # All cash is available when no positions

    def test_should_calculate_used_margin_with_positions(self):
        """Test used margin calculation with open positions."""
        btc_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=50000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=10000.0,
        )

        eth_position = Position(
            symbol="ETHUSDT",
            size=2.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=2000.0,
        )

        portfolio = Portfolio(
            initial_capital=20000.0,
            cash=8000.0,  # 20000 - 10000 - 2000
            positions={"BTCUSDT": btc_position, "ETHUSDT": eth_position},
            trades=[],
            portfolio_history=[],
        )

        used_margin = portfolio.used_margin()
        assert used_margin == 12000.0  # 10000 + 2000

    def test_should_calculate_unrealized_pnl_for_all_positions(self):
        """Test unrealized PnL calculation for all positions."""
        btc_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=24000.0,
        )

        eth_position = Position(
            symbol="ETHUSDT",
            size=-1.0,  # Short position
            entry_price=3200.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type="short",
            margin_used=1067.0,
        )

        portfolio = Portfolio(
            initial_capital=30000.0,
            cash=4933.0,  # 30000 - 24000 - 1067
            positions={"BTCUSDT": btc_position, "ETHUSDT": eth_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {"BTCUSDT": 52000.0, "ETHUSDT": 3000.0}
        unrealized_pnl = portfolio.unrealized_pnl(current_prices)

        # BTC: (52000 - 48000) * 1.0 = 4000 (profit)
        # ETH: (3200 - 3000) * 1.0 = 200 (profit on short)
        # Total: 4000 + 200 = 4200
        assert unrealized_pnl == 4200.0

    def test_should_calculate_realized_pnl_from_trades(self):
        """Test realized PnL calculation from completed trades."""
        trade1 = Trade(
            timestamp=datetime.now(UTC),
            symbol="BTCUSDT",
            action="sell",
            quantity=1.0,
            price=52000.0,
            leverage=2.0,
            fee=26.0,
            position_type="long",
            pnl=1974.0,  # 2000 profit - 26 fee
            margin_used=0.0,
        )

        trade2 = Trade(
            timestamp=datetime.now(UTC),
            symbol="ETHUSDT",
            action="buy",
            quantity=1.0,
            price=2800.0,
            leverage=1.0,
            fee=2.8,
            position_type="short",
            pnl=197.2,  # 200 profit - 2.8 fee
            margin_used=0.0,
        )

        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=12171.2,
            positions={},
            trades=[trade1, trade2],
            portfolio_history=[],
        )

        realized_pnl = portfolio.realized_pnl()
        assert realized_pnl == 2171.2  # 1974 + 197.2

    def test_should_calculate_margin_ratio(self):
        """Test margin ratio calculation."""
        btc_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=50000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=10000.0,
        )

        portfolio = Portfolio(
            initial_capital=20000.0,
            cash=10000.0,
            positions={"BTCUSDT": btc_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {"BTCUSDT": 48000.0}  # Loss position
        margin_ratio = portfolio.margin_ratio(current_prices)

        # Portfolio value = cash + unrealized PnL = 10000 + (-2000) = 8000
        # Used margin = 10000
        # Margin ratio = 8000 / 10000 = 0.8 = 80%
        assert margin_ratio == 0.8

    def test_should_detect_margin_call_risk(self):
        """Test margin call risk detection."""
        btc_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,  # High leverage
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=5000.0,
            positions={"BTCUSDT": btc_position},
            trades=[],
            portfolio_history=[],
        )

        # Safe price - no margin call
        safe_prices = {"BTCUSDT": 49000.0}
        assert not portfolio.is_margin_call(safe_prices, margin_call_threshold=0.5)

        # Dangerous price - margin call risk
        dangerous_prices = {"BTCUSDT": 45000.0}
        assert portfolio.is_margin_call(dangerous_prices, margin_call_threshold=0.5)

    def test_should_add_position_to_portfolio(self):
        """Test adding a new position to portfolio."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=10000.0, positions={}, trades=[], portfolio_history=[]
        )

        position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=25000.0,
        )

        portfolio.add_position(position)

        assert "BTCUSDT" in portfolio.positions
        assert portfolio.positions["BTCUSDT"] == position
        assert portfolio.cash == 10000.0 - 25000.0  # Margin deducted

    def test_should_close_position_from_portfolio(self):
        """Test closing a position and updating portfolio."""
        position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=24000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=26000.0,
            positions={"BTCUSDT": position},
            trades=[],
            portfolio_history=[],
        )

        close_price = 52000.0
        realized_pnl = portfolio.close_position("BTCUSDT", close_price, 26.0)

        # Realized PnL = (52000 - 48000) * 1.0 - 26 = 3974
        assert realized_pnl == 3974.0
        assert "BTCUSDT" not in portfolio.positions
        # Cash = original_cash + margin_released + realized_pnl
        # = 26000 + 24000 + 3974 = 53974
        assert portfolio.cash == 53974.0

    def test_should_handle_portfolio_with_mixed_positions(self):
        """Test portfolio with both long and short positions."""
        long_position = Position(
            symbol="BTCUSDT",
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type="long",
            margin_used=24000.0,
        )

        short_position = Position(
            symbol="ETHUSDT",
            size=-2.0,
            entry_price=3200.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type="short",
            margin_used=2133.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=23867.0,  # 50000 - 24000 - 2133
            positions={"BTCUSDT": long_position, "ETHUSDT": short_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}

        # Long BTC: (50000 - 48000) * 1.0 = 2000 profit
        # Short ETH: (3200 - 3000) * 2.0 = 400 profit
        # Total unrealized PnL = 2400
        assert portfolio.unrealized_pnl(current_prices) == 2400.0

        # Portfolio value = 23867 + 2400 = 26267
        assert portfolio.calculate_portfolio_value(current_prices) == 26267.0
