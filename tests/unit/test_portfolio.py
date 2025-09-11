"""
Unit tests for Portfolio domain model.
Following TDD approach - write failing tests first.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import ActionType, PositionType, Symbol
from src.core.exceptions.backtest import (
    InsufficientFundsError,
    PositionNotFoundError,
)
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

        current_prices = {Symbol.BTC: 50000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        assert portfolio_value == 10000.0  # Only cash

    def test_should_calculate_total_portfolio_value_with_positions(self):
        """Test portfolio value calculation with open positions."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=24000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=26000.0,  # 50000 - 24000 margin used
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {Symbol.BTC: 52000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # Cash + position value
        # 26000 + (1.0 * 52000) = 26000 + 52000 = 78000
        assert portfolio_value == 78000.0

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
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=10000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=15000.0,
            positions={Symbol.BTC: btc_position, Symbol.ETH: eth_position},
            trades=[],
            portfolio_history=[],
        )

        used_margin = portfolio.used_margin()
        assert used_margin == 35000.0  # 25000 + 10000

    def test_should_calculate_unrealized_pnl_for_all_positions(self):
        """Test unrealized PnL calculation for multiple positions."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,  # Long 1 BTC
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=-5.0,  # Short 5 ETH
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=20000.0,
            positions={Symbol.BTC: btc_position, Symbol.ETH: eth_position},
            trades=[],
            portfolio_history=[],
        )

        current_prices = {Symbol.BTC: 52000.0, Symbol.ETH: 2900.0}
        unrealized_pnl = portfolio.unrealized_pnl(current_prices)

        # BTC: (52000 - 50000) * 1.0 = 2000 profit
        # ETH: (3000 - 2900) * 5.0 = 500 profit (short position)
        # Total: 2000 + 500 = 2500
        assert unrealized_pnl == 2500.0

    def test_should_calculate_realized_pnl_from_trades(self):
        """Test realized PnL calculation from completed trades."""
        trade1 = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.SELL,
            quantity=1.0,
            price=52000.0,
            leverage=2.0,
            fee=26.0,
            position_type=PositionType.LONG,
            pnl=1974.0,  # After fees
            margin_used=0.0,
        )

        trade2 = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.ETH,
            action=ActionType.BUY,
            quantity=5.0,
            price=2900.0,
            leverage=3.0,
            fee=14.5,
            position_type=PositionType.SHORT,
            pnl=485.5,  # After fees
            margin_used=0.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=52459.5,
            positions={},
            trades=[trade1, trade2],
            portfolio_history=[],
        )

        realized_pnl = portfolio.realized_pnl()
        assert realized_pnl == 2459.5  # 1974 + 485.5

    def test_should_calculate_margin_ratio(self):
        """Test margin ratio calculation."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=5000.0,
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
        )

        # Price drops to 48000 (loss of 2000)
        current_prices = {Symbol.BTC: 48000.0}
        margin_ratio = portfolio.margin_ratio(current_prices)

        # Equity = cash + unrealized_pnl = 5000 + (-2000) = 3000
        # Used margin = 5000
        # Ratio = 3000 / 5000 = 0.6
        assert margin_ratio == 0.6

    def test_should_detect_margin_call_risk(self):
        """Test margin call detection."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=20.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=2500.0,
        )

        portfolio = Portfolio(
            initial_capital=5000.0,
            cash=2500.0,
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
        )

        # Small price drop should be safe
        safe_prices = {Symbol.BTC: 49000.0}
        assert not portfolio.is_margin_call(safe_prices, margin_call_threshold=0.5)

        # Large price drop triggers margin call
        danger_prices = {Symbol.BTC: 46000.0}
        assert portfolio.is_margin_call(danger_prices, margin_call_threshold=0.5)

    def test_should_add_position_to_portfolio(self):
        """Test adding a new position to portfolio."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=10000.0, positions={}, trades=[], portfolio_history=[]
        )

        btc_position = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=50000.0,
            leverage=5.0,  # Higher leverage to reduce margin requirement
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,  # 0.5 * 50000 / 5
        )

        portfolio.add_position(btc_position)

        assert Symbol.BTC in portfolio.positions
        assert portfolio.cash == 5000.0  # 10000 - 5000
        assert portfolio.positions[Symbol.BTC] == btc_position

    def test_should_raise_error_on_insufficient_funds(self):
        """Test that insufficient funds error is raised."""
        portfolio = Portfolio(
            initial_capital=1000.0, cash=1000.0, positions={}, trades=[], portfolio_history=[]
        )

        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            portfolio.add_position(btc_position)

        assert exc_info.value.required == 25000.0
        assert exc_info.value.available == 1000.0

    def test_should_close_position_from_portfolio(self):
        """Test closing a position and calculating realized PnL."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        portfolio = Portfolio(
            initial_capital=50000.0,
            cash=25000.0,
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
        )

        realized_pnl = portfolio.close_position(Symbol.BTC, 55000.0, 27.5)

        # PnL = (55000 - 50000) * 1.0 - 27.5 = 5000 - 27.5 = 4972.5
        assert realized_pnl == 4972.5
        assert Symbol.BTC not in portfolio.positions
        assert portfolio.cash == 54972.5  # 25000 + 25000 (margin) + 4972.5 (pnl)

    def test_should_raise_error_when_closing_nonexistent_position(self):
        """Test error when closing position that doesn't exist."""
        portfolio = Portfolio(
            initial_capital=10000.0, cash=10000.0, positions={}, trades=[], portfolio_history=[]
        )

        with pytest.raises(PositionNotFoundError) as exc_info:
            portfolio.close_position(Symbol.BTC, 55000.0, 27.5)

        assert exc_info.value.symbol == "BTCUSDT"

    def test_should_handle_portfolio_with_mixed_positions(self):
        """Test portfolio with both long and short positions."""
        btc_long = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=50000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=8333.33,
        )

        eth_short = Position(
            symbol=Symbol.ETH,
            size=-2.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=1200.0,
        )

        portfolio = Portfolio(
            initial_capital=20000.0,
            cash=10466.67,
            positions={Symbol.BTC: btc_long, Symbol.ETH: eth_short},
            trades=[],
            portfolio_history=[],
        )

        assert Symbol.BTC in portfolio.positions
        assert Symbol.ETH in portfolio.positions

        current_prices = {
            Symbol.BTC: 52000.0,  # BTC price increased
            Symbol.ETH: 2800.0,  # ETH price decreased
        }

        # BTC long: (52000 - 50000) * 0.5 = 1000 profit
        # ETH short: (3000 - 2800) * 2.0 = 400 profit
        unrealized_pnl = portfolio.unrealized_pnl(current_prices)
        assert unrealized_pnl == 1400.0

        # Cash + position values
        # 10466.67 + (0.5 * 52000) + (2.0 * 2800) = 10466.67 + 26000 + 5600 = 42066.67
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)
        assert abs(portfolio_value - 42066.67) < 0.01  # Float precision
