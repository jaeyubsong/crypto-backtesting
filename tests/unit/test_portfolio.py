"""
Unit tests for Portfolio domain model.
Following TDD approach - write failing tests first.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import (
    InsufficientFundsError,
    PositionNotFoundError,
)
from src.core.models.portfolio import Portfolio
from src.core.models.position import Position


class TestPortfolioBasics:
    """Basic portfolio functionality tests (mode-agnostic)."""

    def test_should_create_portfolio_with_initial_capital(self) -> None:
        """Test portfolio creation with initial capital."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("10000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        assert portfolio.initial_capital == float("10000.0")
        assert float(portfolio.cash) == 10000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.trades) == 0
        assert len(portfolio.portfolio_history) == 0
        assert portfolio.trading_mode == TradingMode.SPOT

    def test_should_calculate_available_margin(self) -> None:
        """Test available margin calculation."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("5000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        available_margin = portfolio.available_margin()
        assert available_margin == 5000.0  # All cash is available when no positions

    def test_should_calculate_used_margin_with_positions(self) -> None:
        """Test used margin calculation with open positions."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("50000.0"),
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("25000.0"),
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("10000.0"),
        )

        portfolio = Portfolio(
            initial_capital=float("50000.0"),
            cash=15000.0,
            positions={Symbol.BTC: btc_position, Symbol.ETH: eth_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        used_margin = portfolio.used_margin()
        assert used_margin == 35000.0  # 25000 + 10000

    def test_should_calculate_realized_pnl_from_trades(self) -> None:
        """Test realized PnL calculation from completed trades."""
        # Simplified test - would need actual trades in deque for real calculation

        portfolio = Portfolio(
            initial_capital=float("50000.0"),
            cash=float("52459.5"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        realized_pnl = portfolio.realized_pnl()
        assert realized_pnl == 0.0  # No trades in deque

    def test_should_add_position_to_portfolio(self) -> None:
        """Test adding a new position to portfolio."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("10000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        btc_position = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=float("50000.0"),
            leverage=5.0,  # Higher leverage to reduce margin requirement
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),  # 0.5 * 50000 / 5
        )

        portfolio.add_position(btc_position)

        assert Symbol.BTC in portfolio.positions
        assert float(portfolio.cash) == 5000.0  # 10000 - 5000
        assert portfolio.positions[Symbol.BTC] == btc_position

    def test_should_raise_error_on_insufficient_funds(self) -> None:
        """Test that insufficient funds error is raised."""
        portfolio = Portfolio(
            initial_capital=1000.0,
            cash=1000.0,
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("50000.0"),
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("25000.0"),
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            portfolio.add_position(btc_position)

        assert exc_info.value.required == 25000.0
        assert exc_info.value.available == 1000.0

    def test_should_raise_error_when_closing_nonexistent_position(self) -> None:
        """Test error when closing position that doesn't exist."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("10000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(PositionNotFoundError) as exc_info:
            portfolio.close_position_at_price(Symbol.BTC, 55000.0, 27.5)

        assert exc_info.value.symbol == "BTCUSDT"


class TestPortfolioSpotMode:
    """Tests specific to SPOT trading mode."""

    def test_should_calculate_portfolio_value_with_no_positions(self) -> None:
        """Test SPOT portfolio value with no positions (just cash)."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("10000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        current_prices = {Symbol.BTC: 50000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        assert float(portfolio_value) == 10000.0  # Only cash

    def test_should_calculate_portfolio_value_with_positions(self) -> None:
        """Test SPOT portfolio value = Cash + Asset Values."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("48000.0"),
            leverage=1.0,  # No leverage in spot
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("48000.0"),  # Full amount in spot
        )

        portfolio = Portfolio(
            initial_capital=float("50000.0"),
            cash=2000.0,  # 50000 - 48000
            positions={Symbol.BTC: btc_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        current_prices = {Symbol.BTC: 52000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # SPOT: Cash + position value
        # 2000 + (1.0 * 52000) = 2000 + 52000 = 54000
        assert portfolio_value == 54000.0

    def test_should_calculate_portfolio_value_with_multiple_assets(self) -> None:
        """Test SPOT portfolio with multiple assets."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=float("50000.0"),
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("25000.0"),
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("30000.0"),
        )

        portfolio = Portfolio(
            initial_capital=60000.0,
            cash=float("5000.0"),  # 60000 - 25000 - 30000
            positions={Symbol.BTC: btc_position, Symbol.ETH: eth_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.SPOT,
        )

        current_prices = {Symbol.BTC: 52000.0, Symbol.ETH: 3200.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # SPOT: Cash + all asset values
        # 5000 + (0.5 * 52000) + (10 * 3200)
        # 5000 + 26000 + 32000 = 63000
        assert portfolio_value == 63000.0


class TestPortfolioFuturesMode:
    """Tests specific to FUTURES trading mode."""

    def test_should_calculate_portfolio_value_with_no_positions(self) -> None:
        """Test FUTURES portfolio value with no positions (just equity)."""
        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("10000.0"),
            positions={},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        current_prices = {Symbol.BTC: 50000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # FUTURES with no positions: equity = cash
        assert portfolio_value == 10000.0

    def test_should_calculate_portfolio_value_with_long_position(self) -> None:
        """Test FUTURES portfolio value = Cash + Unrealized PnL."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("48000.0"),
            leverage=10.0,  # High leverage common in futures
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("4800.0"),  # 48000 / 10
        )

        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=5200.0,  # 10000 - 4800 margin
            positions={Symbol.BTC: btc_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        current_prices = {Symbol.BTC: 52000.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # FUTURES: Cash + unrealized PnL
        # Unrealized PnL = (52000 - 48000) * 1.0 = 4000
        # Equity = 5200 + 4000 = 9200
        assert portfolio_value == 9200.0

    def test_should_calculate_portfolio_value_with_short_position(self) -> None:
        """Test FUTURES portfolio value with short position."""
        eth_position = Position(
            symbol=Symbol.ETH,
            size=10.0,  # Short 10 ETH
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=float("6000.0"),  # (10 * 3000) / 5
        )

        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=4000.0,  # 10000 - 6000 margin
            positions={Symbol.ETH: eth_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        current_prices = {Symbol.ETH: 2800.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # FUTURES: Cash + unrealized PnL
        # Short PnL = (3000 - 2800) * 10 = 2000 profit
        # Equity = 4000 + 2000 = 6000
        assert portfolio_value == 6000.0

    def test_should_calculate_portfolio_value_with_mixed_positions(self) -> None:
        """Test FUTURES portfolio with both long and short positions."""
        btc_long = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=float("50000.0"),
            leverage=20.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("1250.0"),  # (0.5 * 50000) / 20
        )

        eth_short = Position(
            symbol=Symbol.ETH,
            size=5.0,
            entry_price=3000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=float("1500.0"),  # (5 * 3000) / 10
        )

        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("7250.0"),  # 10000 - 1250 - 1500
            positions={Symbol.BTC: btc_long, Symbol.ETH: eth_short},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        current_prices = {Symbol.BTC: 52000.0, Symbol.ETH: 2800.0}
        portfolio_value = portfolio.calculate_portfolio_value(current_prices)

        # FUTURES: Cash + total unrealized PnL
        # BTC long: (52000 - 50000) * 0.5 = 1000 profit
        # ETH short: (3000 - 2800) * 5 = 1000 profit
        # Equity = 7250 + 1000 + 1000 = 9250
        assert portfolio_value == 9250.0

    def test_should_calculate_unrealized_pnl_for_futures_positions(self) -> None:
        """Test unrealized PnL calculation for futures positions."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,  # Long 1 BTC
            entry_price=float("50000.0"),
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=5.0,  # Short 5 ETH
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=float("3000.0"),
        )

        portfolio = Portfolio(
            initial_capital=float("50000.0"),
            cash=float("42000.0"),
            positions={Symbol.BTC: btc_position, Symbol.ETH: eth_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        current_prices = {Symbol.BTC: 52000.0, Symbol.ETH: 2900.0}
        unrealized_pnl = portfolio.unrealized_pnl(current_prices)

        # BTC: (52000 - 50000) * 1.0 = 2000 profit
        # ETH: (3000 - 2900) * 5.0 = 500 profit (short position)
        # Total: 2000 + 500 = 2500
        assert unrealized_pnl == 2500.0

    def test_should_calculate_margin_ratio_for_futures(self) -> None:
        """Test margin ratio calculation in futures mode."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("50000.0"),
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),
        )

        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("5000.0"),
            positions={Symbol.BTC: btc_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        # Price drops to 48000 (loss of 2000)
        current_prices = {Symbol.BTC: 48000.0}
        margin_ratio = portfolio.margin_ratio(current_prices)

        # Equity = cash + unrealized_pnl = 5000 + (-2000) = 3000
        # Used margin = 5000
        # Ratio = 3000 / 5000 = 0.6
        assert margin_ratio == 0.6

    def test_should_detect_margin_call_risk_in_futures(self) -> None:
        """Test margin call detection in futures trading."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("50000.0"),
            leverage=20.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("2500.0"),
        )

        portfolio = Portfolio(
            initial_capital=float("5000.0"),
            cash=float("2500.0"),
            positions={Symbol.BTC: btc_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        # Small price drop should be safe
        safe_prices = {Symbol.BTC: 49000.0}
        assert not portfolio.is_margin_call(safe_prices, margin_call_threshold=0.5)

        # Large price drop triggers margin call
        danger_prices = {Symbol.BTC: 46000.0}
        assert portfolio.is_margin_call(danger_prices, margin_call_threshold=0.5)

    def test_should_close_futures_position_with_realized_pnl(self) -> None:
        """Test closing a futures position and calculating realized PnL."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=float("50000.0"),
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),
        )

        portfolio = Portfolio(
            initial_capital=float("10000.0"),
            cash=float("5000.0"),
            positions={Symbol.BTC: btc_position},
            trades=None,
            portfolio_history=None,
            trading_mode=TradingMode.FUTURES,
        )

        realized_pnl = portfolio.close_position_at_price(Symbol.BTC, 55000.0, 27.5)

        # PnL = (55000 - 50000) * 1.0 - 27.5 = 5000 - 27.5 = 4972.5
        assert float(realized_pnl) == 4972.5
        assert Symbol.BTC not in portfolio.positions
        assert float(portfolio.cash) == 14972.5  # 5000 + 5000 (margin) + 4972.5 (pnl)
